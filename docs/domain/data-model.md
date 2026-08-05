# Data model — the traps

Four facts about the source data that are not visible from a schema listing, and each of which
produces plausible-looking wrong answers if you miss it.

---

## 1. `batch_code` is two different identifiers wearing one name

The same column name carries two incompatible identifier types depending on where in the process you
are standing.

| Stage | Shape | Example shape | What it identifies |
|---|---|---|---|
| Raw material intake | Alphanumeric, letter-prefixed, short | `A1234B` | A supplier consignment / lot |
| Finished case label | All-numeric, six digits, zero-padded | `035366` | A **production run**, not a lot |

The finished-goods label does not carry the raw-material lot code at all — it carries the run
number. Finished product goes into baskets or boxes, and **OCM — the same system that mints the run
number — generates the barcode label applied to each one**; that is how the run number gets onto
the case, and SI scans it from there onward. So this join:

```sql
-- WRONG. Silently returns almost nothing, or worse, coincidental matches.
FROM raw_material rm JOIN finished_goods fg ON rm.batch_code = fg.batch_code
```

...is not a join between a lot and its output. It is a comparison between two unrelated
namespaces that happen to share a column name. It will not error. It will return a small,
plausible, wrong result set — the worst failure mode available.

**Model them as distinct, differently-named columns**: `material_lot_code` and `run_number`. A trap
inside the trap: run numbers are **zero-padded** — `035366` is what screens and labels carry, and
the source system stores the column as a string, so the leading zero is significant in any match
against a label. Keep `run_number` a fixed-width six-digit string that must *parse* as an integer
(or store an integer and zero-pad every render); never let `35366` and `035366` become two
different runs. Never reconstruct one column from the other by string matching. The
relationship between them is a real relationship in the data — it is the genealogy edge list in §4
— and it must be traversed, not guessed.

**Guard:** a lot code that parses cleanly as an integer, or a run number that does not, is a signal
that the two namespaces have been mixed somewhere upstream. Reject on ingest rather than carrying it
forward.

---

## 2. Mixed batches arrive packed into a single field

When a run consumes material from more than one lot, the source does not produce multiple rows. It
concatenates the lot codes into one string field using a **`|s|` delimiter**, with a secondary
grouping that uses a bare `|`:

```
A1234B|s|A1234E|A1235B
```

The mixing is not random: OCM **scan-back** returns re-enter production next day in tier-3 runs —
marinade, simply (business-rules §8) — so composites concentrate in the lowest-value products.
The true lot is still resolvable, but only via the split below.

Consequences:

- Any `GROUP BY batch_code` over this field counts each distinct *combination* as its own batch.
  Yield per batch computed this way is wrong in a way that gets worse the more mixing happens — so
  it is most wrong exactly when material provenance matters most.
- Any equality filter (`WHERE batch_code = 'A1234B'`) misses every mixed batch that contains it.
- Any traceability query built on this field under-reports scope. In a recall, that is the failure
  that matters.

**Split on ingest, in the bronze→silver step, and never carry the composite downstream.** One row
per (run, contributing lot). Where a proportional split of input mass is needed and the source does
not give per-lot quantities, record the split as **unknown** rather than dividing evenly — an even
split is a fabricated number that looks like a measured one.

Keep the original composite string in the bronze layer, unparsed, so the parse can be re-run when a
new delimiter case appears. It will.

---

## 3. Certification is asserted in three places, and they can disagree

The same product's certification status is stated in three independent places:

| Source | Form | Notes |
|---|---|---|
| Product description text | Certification named inline in a free-text description | Human-entered; the least reliable, the most readable |
| A dedicated branding/certification field | A scheme code, sometimes with a chain-of-custody number appended | This is the string printed on the pack |
| The paper quality-control document for the run | An approval box completed per run | Authoritative for the run, but on paper — not queryable today |

The schemes in play are three: **GlobalG.A.P.** (a GGN / chain-of-custody number, farmed salmon),
**RSPCA Assured** (welfare, also farmed salmon), and **MSC** (a certificate registration code,
wild-caught cod, haddock and hake) — observed in the branding field as `GGap-CoC 4059883971576`,
`RSPCA-A`, and `MSC-C-50147`. GlobalG.A.P. and RSPCA salmon run as separate material streams (run
descriptions distinguish `GG SALMON` from `RSPCA SALMON`), so a certification claim is also a
**segregation constraint on raw material**, not just a printed string. The constraint is asymmetric
(business-rules §8): premium material may fill a standard order — a costed downgrade worth
detecting — but standard material may never fill a certified claim.

They are not guaranteed to agree, and the interesting cases are exactly the disagreements: a run
whose input material is certified but whose output is not is a real, costly event, and it is
detectable only by comparing sources rather than trusting one.

**Resolve to a single derived `certification` column in the silver layer, and keep all three
sources alongside it plus a `certification_source` column recording which one won.** A resolved
value with no provenance cannot be audited, and this is precisely the field someone will eventually
be asked to justify to an auditor.

Precedence, most to least authoritative: the run's quality document, then the branding field, then
the description text. Where the description text is the only source, mark confidence as low rather
than treating it as equal to the others.

---

## 4. Batch genealogy is a graph, and the edge list already exists

The existing yield report exposes `Next Run` and `Previous Run` fields per run. That is a
parent/child edge list — the traceability graph is already in the source data, unrecognised as such.

Model it as an **immutable edge table**: `(parent_run_number, child_run_number, observed_at)`, append
only.

**The graph is two levels, not three.** There is no separate case-pack identifier — the finished case
carries the *run number* as its printed "Batch Code" (§1). So:

```
material_lot ──► run_number ──► customer despatch
                     │
                     └──► onward run (trimming, rework)
```

**Two levels of identifier, but many runs deep.** Each department opens its own run — tempering /
defrost, filleting / portioning, curing / smoking where the product has it, then retail packing
opens new runs again — and each accounts its own yield per run. A lot's path to despatch is
therefore normally a *chain* of runs, and the edge between two runs is made physically by container
scans: OCM prints a barcode per basket or box, with its tare weight held in OCM; filling it books
the net weight into the producing run's **output**, and scanning it at the next line books it into
the consuming run's **input** (observed: 36 packs to a basket, 2.25 kg tare, 16 baskets to a
pallet — and a wrong tare assumption once biased yield by 14 kg per pallet, so tares are
configuration worth guarding). An edge is a pair of scans, and it carries a weight on both sides —
which is exactly what §5's mass balance needs (D3 still requires confirming this in the tables, and
where WIP sits between the two scans).

**Traversal is directed and two-phase, not an undirected flood.** Both directions do *not* fall out
of one query:

- **Backward trace** — given a finished case, every lot that contributed to it. The
  complaint-investigation question.
- **Forward trace** — given a lot, every run and despatch it reached. The recall question.
- **A recall is both, in sequence:** trace *back* from the affected case to its lots, then *forward*
  from those lots to catch every **sibling** case made from the same material. Sibling cases are the
  entire point of a recall, and they sit on runs the affected case never touched.

A single query joining `ON t.node = g.parent OR t.node = g.child` looks like it does both at once.
It does not. It returns the whole connected component — which, where runs share raw material, can be
a month of production — and with `UNION ALL` **it does not terminate**. Verified: on a four-row
table that query ran for two minutes before being killed. Directed recursion with a visited-path
guard answered the same question in 17.5 ms.

```sql
-- backward; mirror it (parent_batch <-> child_batch) for forward
WITH RECURSIVE up(node, depth, path) AS (
  SELECT ?, 0, [?]
  UNION ALL
  SELECT g.parent_batch, u.depth + 1, list_append(u.path, g.parent_batch)
  FROM genealogy g
  JOIN up u ON g.child_batch = u.node
  WHERE u.depth < 20                                  -- bounded
    AND NOT list_contains(u.path, g.parent_batch)     -- cycle guard
)
SELECT DISTINCT node FROM up WHERE depth > 0;
```

Two cautions:

- **Cycles.** Rework and reprocessing can produce a run that appears both upstream and downstream of
  another. Observed practice cuts both ways: same-shift rework re-enters the **same run** — no edge
  at all, just material crossing the line twice inside one run's balance — while held-over rework
  opens its own later run (OCM run descriptions like `…280G (REWORK)` exist). So an edge-level cycle
  is rare but real. A recursive CTE without a visited-set will not terminate. Track visited nodes and cap
  depth; a query that hangs during a recall is worse than one that returns a bounded partial answer
  with a warning.
- **Edges are observations, not truths.** An edge asserts what the ERP recorded, which is not
  necessarily what physically happened. Keep `observed_at` so a trace can be reproduced as it stood
  at the time it was run — a recall trace that silently changes when re-run later is not evidence.

---

## 5. Finding the links is table stakes; reconciling the quantities is the test

A traceability exercise that returns a list of related codes has done the easy half. The standard
requires **quantity reconciliation** — mass balance — and that is the part no document-shuffling
process can do at all, because you cannot sum kilograms per lot when two lots share one field (§2).

Every edge carries a quantity, so the check is arithmetic on the edge table:

```
In    300.0 kg   lot, from intake
Out   178.2 kg   finished run
       29.3 kg   onward run (trimming)
       31.5 kg   rework
WIP    61.0 kg   still in process
                 ------
                 300.0 kg  balanced
Yield  178.2 / 300.0 = 59.4%
```

Two things this makes possible that a link-list cannot: an **unexplained variance** becomes a
number rather than a feeling, and the reconciliation is reproducible from the edge table at the
`observed_at` it was run.

Design consequences: quantity belongs **on the edge**, not derived later; WIP must be representable
or every in-progress lot looks like a loss; and a tolerance band is required, because measurement
noise is not the same as unaccounted product.

---

## 6. Supplier attribution is unproven — treat as discovery, not design

Showing the supplier inline next to a lot is the most persuasive thing a trace can do, and it is
currently the least evidenced. In the yield report the `Supplier` column is **blank on every
observed row**.

The most likely source is `GRN` + `IntakeDate` on the run table — a goods-received note reference
plus its intake date, which together should resolve to a consignment and therefore a supplier. That
is a hypothesis, not a known join.

**Phase 0 discovery task, not a Phase 1 assumption.** Confirm whether `GRN` is populated, whether it
resolves to a supplier in a reachable table, and what fraction of lots carry one. Three outcomes,
each with a different plan:

- Populated and resolvable → surface it inline as designed.
- Populated but resolves only in intake paperwork → document the gap; supplier is a manual lookup
  and the trace shows `GRN` instead of a name.
- Sparsely populated → the field is unreliable and must never be presented as authoritative.

**Answered (2026-08-04): sparse and unreliable.** Supplier is never presented as authoritative; a
trace shows `GRN` where present, nothing more.

---

## 7. One server, many databases — not two source systems

The weigh-terminal data is **not** a separate source system requiring its own connector. `SI_OCM`
and its shards (`SI_OCM_01` … `SI_OCM_23`) are databases on the *same* SQL Server instance as the
core `SI` database, alongside `SI_Pricing`, `SI_QA` and the rest. The terminals write into that
server over TDS.

So one ingest mechanism reads all of it — the same `sql_database` source, pointed at additional
database names. No second connector, no file-drop reader.

What *is* true and does need work: the estate is 40+ databases, OCM is sharded, and the tables
holding transfer and return history have to be **located** before anything can be promised from
them. That is discovery of the same kind as §6 — a specific named table, confirmed populated — not
an architectural change.

---

## Ingest checklist

Everything above collapses into five ingest-time rules:

1. Split `|s|`-delimited lot fields into one row per contributing lot. Never propagate the composite.
2. Keep lot codes and run numbers in separate, differently-typed columns. Never join them by name.
3. Resolve certification to one column, retain all three sources and record which won.
4. Build the genealogy edge table from `Next Run` / `Previous Run`, append-only, with a timestamp
   **and a quantity on every edge** — mass balance (§5) is arithmetic on those quantities, and an
   edge without one cannot be reconciled.
5. Preserve the raw source values in bronze so every parse above can be re-run when — not if — an
   unhandled case appears.
6. Read every database on the one server through the same source (§7). Adding `SI_OCM_*` or
   `SI_Pricing` is a configuration change, not a new connector.

## Open questions blocking design

| # | Question | Blocks |
|---|---|---|
| D1 | ~~Is `GRN` populated, and does it resolve to a supplier?~~ **Answered: sparse/unreliable — never authoritative** (§6) | Supplier attribution in any trace |
| D2 | Which `SI_OCM_*` tables hold transfer and return history? (§7) | Transfer/return audit |
| D3 | Do quantities exist on both sides of every edge, and where is WIP held? (§5) | Mass balance |

Each is a named-table-confirmed-populated check, answerable in a session with database access.
None should be assumed in a demo.
