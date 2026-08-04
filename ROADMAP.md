# Copernus — Roadmap

> **Last updated:** 4 August 2026
> **Owner:** Pawansingh3889
> **Horizon:** 12 phases, ~2 weeks each, demo at the end.
> **Headline:** end the paperwork — BRCGS readiness and the second team
> leader's clipboard, captured at source instead of transcribed.

Site data access arrives early in Phase 2 — discovery happens against the
real estate, and the synthetic data in Phase 3 mirrors the actual schema.

```
P1  Foundation ────────── gate: make gate green in CI; C-12 schema decided     ✅
P2  Discovery ─────────── gate: task 1.0 + D1–D3 + S1–S4 answered, in writing
P3  Synthetic estate ──── gate: seed reproduces every documented trap
P4  Capture engine ────── gate: version-in-force answerable for any past date
P5  QC vertical slice ─── gate: one run's paperwork end-to-end, no paper
P6  Ingest + reconcile ── gate: mass balance holds; Oracles 1–2 recorded
P7  Traceability ──────── gate: recall drill beats hand-trace, terminates on cycles
P8  Corpus ────────────── gate: every chunk carries source, version, licence tier
P9  Grounded assistant ── gate: eval set passes; zero uncited answers
P10 H&S module ────────── gate: identity severable without breaking audit chain
P11 Dashboards + alerts ─ gate: excursion trend + audit view from captured data
P12 Hardening + demo ──── gate: cold-start demo by someone who didn't build it
```

| # | Phase | Builds | Gate |
|---|---|---|---|
| 1 | **Foundation** | This repo: engine, gates, auth (session cookie), identity (severable, C-12), audit (append-only, C-03), both adapters, CI | Gates green; every guard proven to reject a planted violation; C-12 decided before any person-shaped row existed |
| 2 | **Discovery** | Schema map of the estate; where the stock tracker's shelf-life logic lives; GRN→supplier; OCM transfer tables; WIP quantities; weigher archives. On site: what H&S paper exists, duty holder, QC form ownership, DPIA | Every question answered with one of its named outcomes, recorded in `docs/`. Nothing assumed |
| 3 | **Synthetic estate** | Seed generator mirroring the real schema: `\|s\|` composites, dual batch_code namespaces, harvest+18 clock, concessions, NULL use-bys, genealogy edges with quantities, 60 days with planted excursions | A test asserts each documented trap is present. A seed without the traps is a demo that lies |
| 4 | **Capture engine** | Checklist module: immutable published template versions, per-run instances, sign-off as event (owner + timestamp), HTMX forms rendered from templates | "Which version of this form was in force on date X" answerable by query |
| 5 | **QC vertical slice** | Metal detection (3 apertures, mm), hourly temperature (excursions, never averages), clean-down start/end, allergen declaration, label verification incl. certification, region of capture, end-of-run checkweigher summary; live supervisor board | One run's full QC record captured at source on a tablet, readable back as an audit view |
| 6 | **Ingest + reconciliation** | Extract → artefact, atomic swap, stale banner; mass-balance gate; despatch priority (recovered tracker logic + chasing rule) | In = out + WIP within tolerance; shelf life matches the tracker exactly (Oracle 2); discrepancy blocks — fix the cause, never widen the tolerance |
| 7 | **Traceability** | Genealogy edge table (append-only, quantity per edge), directed two-phase traversal with depth cap and visited guard, trace UI with lineage + balance together | Recall drill vs hand-trace: same set including siblings, faster, terminates on the cyclic fixture |
| 8 | **Corpus** | Source register (licence tiers: OGL / free-copyrighted / paid-never-in-repo), fetchers for legislation.gov.uk, FSA, HSE; versioned store; site SOPs via the capture engine | Every chunk carries source, version, licence tier; no tier-3 text anywhere in the repo |
| 9 | **Grounded assistant** | The pipeline in ARCHITECTURE.md §8: routing, chained stages, parallel voting, verifier, judge, sign-off; multilingual capture → English record; eval harness | Eval passes; zero uncited answers; judge calibrated against human labels before it gates |
| 10 | **H&S module** | Incident + near-miss capture on the Phase-1 identity schema; corrective actions with owners; RIDDOR draft (reasoning shown, human files); registers via the capture engine; toolbox talks from own near-misses | Erasing a person severs identity without breaking the audit chain — demonstrated, not asserted |
| 11 | **Dashboards + alerts** | Temperature excursions, giveaway from checkweigher summaries, concession rate, near-miss rate; alert dedupe, acknowledge, rate-limit; React island only if a page earns it | Trends render from captured data only; acknowledged alerts don't re-fire |
| 12 | **Hardening + demo** | Oracle re-run recorded; demo script on the headline; de-identified demo pack; dry runs; business impact in headcount and BRCGS-readiness terms | Someone who didn't build it drives the demo cold from the README |

**Dependency spine:** 4→5→10 (engine before forms before H&S) · 6→7
(quantities before trace) · 8→9 (corpus before assistant) · 2→3 (schema
before seed). Phases 6–7 and 8–9 are independent chains — if time runs
short, corpus/assistant slip right without touching the paperwork story.

## Constraints carried from dora-factory

C-01 never write to the production SQL Server · C-03 never delete from the
audit log · C-06 never query the vendor server outside the nightly window ·
C-07 never use planned use-by dates · C-09 one module's crash never takes
another down · C-11 no LLM output stands as a regulatory determination
without a named human approver and a timestamp · C-12 personal identity is
severable without breaking the audit chain.

## Open blockers

| # | Blocker | Owner |
|---|---|---|
| B01 | Licence — deliberately out of scope for this repo until resolved in writing. All rights reserved meanwhile | Pawan + client contact |
