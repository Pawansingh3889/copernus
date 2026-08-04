# Ground-truth oracles

Two existing systems produce numbers the plant already trusts. They are the reference against which
DFI's equivalents are checked.

**These checks cannot be run from a development environment.** They require read access to the live
source system and sight of the existing reports. They are gate conditions on Phases 1 and 2, and
until they have been run and recorded, no number DFI produces should be shown to anyone on site.

---

## Why an oracle, and not a unit test

Unit tests prove the code does what the developer intended. They cannot detect the failure that
actually sinks a project like this one: **the developer's understanding of the business rule was
wrong, and the code faithfully implements the misunderstanding.**

Only a comparison against a system the plant already relies on catches that. And the comparison has
to be against the trusted system rather than against the raw tables, because the trusted system
embeds years of accumulated corrections that are nowhere written down.

---

## Oracle 1 — Yield

**Reference:** the existing SSRS yield report, "Yield By Run Number (Details)".

**Check:** pick three historical runs spanning different products and different lines. For each,
compare DFI's `output_kg / input_kg` against the report's yield figure.

**Tolerance:** within 0.1%.

Anything wider is not a rounding difference — it means the two are including different things.
Common causes, in the order worth checking:

- rework counted as output in one and not the other
- a mixed-batch input not split (see `data-model.md` §2), so input mass is attributed to the wrong run
- different treatment of a run that spans a shift boundary or a date change
- one figure net of waste, the other gross

**Record the result** — run identifiers, both figures, the delta — in `docs/validation/`. A
reconciliation nobody wrote down has to be re-argued every time somebody new asks.

## Oracle 2 — Shelf life

**Reference:** the existing stock tracker's remaining-days figure.

**Check:** pick five batches spanning both shelf-life classes and more than one storage area. For
each, compare DFI's days-to-expiry and its urgency band against the tracker's.

**Tolerance: exact.** Not "within a day".

A one-day discrepancy is not a small error here — it is a date-boundary or timezone bug, and it will
land on precisely the batches nearest expiry, which are the only ones anyone is looking at. The
likely causes:

- one system counting inclusive of today and the other exclusive
- a UTC-vs-local mismatch that inverts across midnight
- a planned use-by date used where an actual one was required (constraint C-07)

Band boundaries must match the tracker's too. Agreeing on the number and disagreeing on the colour
is still two screens that contradict each other.

---

## Oracle 3 — Recall drill (Phase 4)

**Reference:** a hand-traced recall, performed the way it is performed today.

**Check:** take a known historical intake lot. Trace it forward by hand to every finished run and
every customer despatch. Then run the same trace through DFI's genealogy graph.

**Two things are measured:**

1. **Correctness** — the graph answer contains every despatch the hand trace found. A trace that
   misses a destination is worse than no trace at all: it produces false confidence during exactly
   the event where confidence must be earned.
2. **Elapsed time** — how long each method takes. This is the business case, and it is the number
   the end-of-project report needs.

If the graph finds destinations the hand trace missed, **do not assume the graph is right.**
Investigate each one. It is equally likely to be a mixed-batch split that over-attributed (see
`data-model.md` §2), and an over-broad recall has real costs.

---

## Running these

1. Confirm read-only access to the source system, and sight of both existing reports.
2. Pick the samples **before** looking at DFI's output. Choosing samples after seeing the results is
   how a reconciliation gets talked into passing.
3. Record every comparison in `docs/validation/`, including the ones that matched — a passing check
   is only evidence if the failing ones would also have been written down.
4. Any discrepancy outside tolerance blocks the phase gate. Fix the cause, do not widen the
   tolerance.

Point 4 is the one that gets negotiated under time pressure. It is also the whole point: the reason
to have an oracle is that it is allowed to say no.
