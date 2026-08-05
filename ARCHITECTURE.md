# Copernus — Architecture

> **Last updated:** 5 August 2026
> **Update rule:** updated with every structural change (§7.8, mechanised by
> `scripts/check_doc_freshness.py`).

## 1. Helicopter view

Copernus is a **monolith with enforced seams**. One FastAPI process, one
Postgres, two thin adapters (JSON and HTML) over one set of services, an
in-process event engine wiring independent modules together. The seams are
contracts in `pyproject.toml` checked by `make gate`, not conventions — so the
monolith can be split later along lines that provably held.

It exists to **end the paperwork** at a chilled-fish plant: capture QC data at
source, make it traceable and trendable, and put an auditable assistant over
the top. The domain knowledge lives in `docs/domain/` — read it before
touching anything that mentions a batch, a date, or a certification.

```
                    ┌──────────────────────────────────────────┐
                    │  copernus.app  (composition root)        │
                    └───────┬──────────────────────┬───────────┘
                    ┌───────▼───────┐      ┌───────▼───────┐
                    │ copernus.api  │      │ copernus.ui   │   two adapters,
                    │ JSON, /api/v1 │      │ HTMX + Jinja2 │   never importing
                    └───────┬───────┘      └───────┬───────┘   each other
                            └──────────┬───────────┘
                                ┌──────▼──────┐
                                │   engine    │  <100 lines: route, permit,
                                └──────┬──────┘  audit, isolate (C-09)
                    ┌──────────┬───────┴──────┬──────────────┐
              ┌─────▼────┐ ┌───▼─────┐ ┌─────▼────┐   later: qcheck,
              │   auth   │ │identity │ │  audit   │   checklist, assistant…
              └─────┬────┘ └───┬─────┘ └─────┬────┘
                    └──────────┴──────┬──────┘
                                ┌─────▼─────┐
                                │  common   │  types, errors, logging, db
                                └───────────┘
```

## 2. The two-adapter rule

Every capability is exposed twice from one service: a JSON route under
`/api/v1` and an HTML route rendered server-side with HTMX. Both call
`engine.dispatch()`; neither holds logic. The HTML adapter is the product
today (gloved hands, wet tablet, shop floor); the JSON adapter is the same
product for any future consumer. Deleting `ui/` must never require touching a
module.

## 3. Module contract

One module = one business capability, four files:

```
modules/<name>/
├── __init__.py    handle(event, state) -> Result; PERMISSIONS dict
├── contract.py    typed dataclasses; no secrets (guarded)
├── service.py     pure rules; no I/O (lint-imports enforced)
└── repository.py  all I/O; owns its tables on the shared metadata
```

| Module   | Owns | Notes |
|---|---|---|
| auth     | user_account, session | Session-cookie auth: server-side token hash, HttpOnly. Roles: participant → analyst → manager → admin |
| identity | person, person_identity | C-12. See §5 |
| audit    | audit_log | C-03. Sink runs in its own transaction — a rolled-back request still leaves its row |

## 4. The engine

Async in-process event bus, <100 lines (guarded). Routes `<module>.<action>`
events, checks the permission the module declared, appends to the audit trail
(in memory and through the sink), and isolates module crashes: an unhandled
exception marks the module degraded and returns `Result.err` instead of
unwinding anyone else's stack (C-09).

## 5. Identity is severable (C-12)

Injury and incident records are special-category data under UK GDPR; the
audit log is immutable (C-03). Both hold at once because **identity is a
reference, not a value**: every table stores a meaningless `person_id`; the
mapping to a name lives in `person_identity` — the only table in the system
that erasure may touch. Deleting the mapping row severs the identity; the
person row, the audit chain and every future H&S record stay intact and
render a pseudonym. Decided before the first row existed, because it cannot
be retrofitted.

## 6. The audit log is append-only (C-03)

Enforced twice in the database, not in Python: a trigger raises on UPDATE and
DELETE for every role, and the `copernus_app` role never receives those
grants at all. The migration is the source of truth; `make gate` proves the
application-level half, and the pg-marked probes prove the database half.

## 7. Rules and their mechanisms

| # | Rule | Enforced by |
|---|---|---|
| 7.1 | No module imports a sibling | `lint-imports` independence contract |
| 7.2 | No I/O in service.py | `lint-imports` forbidden contract (`anthropic` is already on the list for Phase 8) |
| 7.3 | No request without audit | engine + sink; test proves survival across a crashing handler |
| 7.4 | No secret in contract.py | `scripts/check_no_secrets_in_contracts.py` |
| 7.5 | No module >300 lines, engine <100 | `scripts/check_module_size.py` |
| 7.6 | Fixtures over literals in tests | review |
| 7.7 | No silent failure; errors carry a code and an actionable message | `Result.err` requires a message; ruff catches bare except |
| 7.8 | This file updated with every structural change | `scripts/check_doc_freshness.py` |

Every gate is proven to reject a planted violation (`tests/test_gates.py`).
A gate never observed to fail is decoration.

## 8. The LLM pipeline (decided now, built Phases 8–10)

The assistant is a staged pipeline in a future `modules/assistant/`,
four-file like everything else — LLM calls are I/O and live in repository.py.

```
request → ROUTER → operational?  → deterministic service (NO LLM — the
        │                          existing-systems rule applied to models)
        ├→ qa_regulatory → RAG chain
        ├→ incident      → extraction chain (fields → severity → RIDDOR draft)
        └→ audit_pack    → orchestrator-workers
              ↓  each chain: prompt-chained stages, gated between steps;
                 parallel where independent (sectioning; 3× voting on RIDDOR)
        VERIFIER   deterministic code on EVERY output: strict schemas,
                   citations resolve, dates/enums/bounds
        JUDGE      second LLM, fresh context, adversarial prompt — only on
                   consequence-bearing outputs; calibrated against human
                   labels before it gates anything (oracle discipline)
        SIGN-OFF   a named human, timestamped (C-11). The pipeline never
                   files anything.
```

Every stage stores a reasoning trace — adaptive thinking summary plus a
structured rationale field — with the record, for the approver and the
auditor. Model: `claude-opus-5` at every stage until the Phase 9 eval
harness justifies anything cheaper.

Three more decisions, recorded now because none of them retrofits cleanly:

- **Prompts are code.** Every prompt lives in the assistant's source tree,
  versioned like any other file, and every prompt change reruns the Phase 9
  eval set before it merges — the same gate a model upgrade gets. No prompt
  in application config, ever.
- **Captured text is data, never instructions.** Incident narratives,
  multilingual capture and every other shop-floor free text enter prompts as
  delimited, quoted data; nothing a user types can address the model. Prompt
  isolation is architecture, not an add-on — decided here for the same
  reason C-12 was decided before the first row existed.
- **Every assistant record carries its economics.** Model id, prompt
  version, token counts and cost land on the record at write time, and the
  stable regulatory corpus is served through prompt caching from day one. A
  cost question answered by grepping logs is answered too late.

## 9. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg | The team's default stack; async end to end |
| Database | Postgres 16 (podman compose, host port 5433 — 5432 is taken by glance) | C-03 and C-12 are grants and triggers, which SQLite cannot express |
| Frontend | Jinja2 + HTMX (vendored), no build step | Forms on gloved tablets; the JSON API keeps the React door open |
| Auth | bcrypt + server-side sessions, HttpOnly cookie | Revocable instantly; nothing stored client-side but the token |
| Migrations | Alembic (async) | Hand-written where DDL carries policy (triggers, grants) |
| Tests | pytest, SQLite in-memory for logic, pg-marked probes for grants | Fast by default, honest where the database is the mechanism |
| CI | GitHub Actions running `make gate` | Same command locally and in CI |
