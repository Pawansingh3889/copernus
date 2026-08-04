# Copernus

> End the paperwork. QC capture at source, traceability, and an auditable
> assistant for a chilled-fish plant — BRCGS-ready data instead of a
> clipboard and a second team leader to carry it.

## Quick start

```bash
# Prerequisites: uv, podman + podman-compose
git clone <private remote> && cd copernus
make setup          # uv sync
cp .env.example .env
make db-up          # Postgres 16 on localhost:5433 (5432 is taken by glance)
make migrate        # schema + C-03 trigger/grants + copernus_app role
make serve          # http://localhost:8010  (JSON API under /api/v1, docs at /docs)
```

```bash
make test           # 65 tests, SQLite in-memory — no daemon needed
make gate           # lint, import contracts, guards, coverage floors, gate proofs
```

## What this is

A monolith with enforced seams. Read **[ARCHITECTURE.md](ARCHITECTURE.md)**
first — the two-adapter rule, the four-file module pattern, and why identity
severance (C-12) and the append-only audit log (C-03) are database mechanisms
rather than promises. The build plan is **[ROADMAP.md](ROADMAP.md)**: twelve
phases to a demo. Domain knowledge — the batch-code trap, the `|s|`
delimiter, the harvest+18 clock — is in **[docs/domain/](docs/domain/)** and
is the most valuable thing in the repo.

## Layout

```
src/copernus/
├── app.py            composition root — the only place both adapters meet
├── engine.py         async event bus, <100 lines, guarded
├── config.py         COP_-prefixed settings, units in names
├── common/           types, errors, logging, db plumbing
├── modules/          auth · identity · audit   (four files each)
├── api/              JSON adapter (/api/v1)
└── ui/               HTML adapter (Jinja2 + HTMX, vendored)
migrations/           alembic; 0001 carries the C-03 trigger + grants
scripts/              guard scripts — every one proven to fail in tests/test_gates.py
docs/domain/          ported from dora-factory @24803d9 — read before querying anything
```

## Rules that will bite you if you skip them

- `service.py` never touches I/O — `lint-imports` will fail the gate.
- No module imports a sibling — go through `engine.dispatch()`.
- The audit log cannot be updated or deleted, even by the owner role.
- Erasing a person deletes exactly one row (`person_identity`) — everything
  else keeps working against the pseudonym.
- ARCHITECTURE.md and ROADMAP.md must be updated with structural changes —
  a guard compares their header dates against git history.

## Licence

Unresolved, deliberately — this began inside a client engagement. Until
resolved in writing: **all rights reserved**, no redistribution.
