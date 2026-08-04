# What already exists on site

The most valuable output of the environment survey was a shorter scope. Roughly half of what DFI
originally planned to build is already running, already trusted, and already used daily.

**Rebuilding a trusted calculation is not neutral.** It produces a second screen that will
eventually disagree with the first, and when that happens the plant does not adjudicate — it stops
trusting both. Every item below is something to read from, reconcile against, and defer to.

---

## Stock tracker — shelf life is already solved

An existing web application, in daily use, already:

- computes remaining shelf life in days per batch
- colour-bands it across several thresholds, down to same-day
- refreshes automatically on a short timer
- drills down to per-case batch detail

**What it cannot do:** it takes **one product code at a time**. There is no cross-product,
cross-area view.

That single limitation is why the coldstore walk still happens. Somebody wanting to know "what
expires soonest across everything" cannot ask this tool — they have to either query it once per
product, or walk the store. The walk takes about fifteen minutes.

**Therefore:** DFI does not compute shelf life differently, present it differently, or band it
differently. DFI provides **the aggregation across products and areas that this tool structurally
cannot give**, using bands that match the existing ones so the two screens agree on any single
product. Where they disagree, the existing tracker is right until proven otherwise — see
[`oracles.md`](oracles.md).

## Yield report — yield is already solved

An existing SSRS report gives, per production run:

- input kg and output kg
- unit counts
- the computed yield percentage
- **`Next Run` and `Previous Run`**

Two things follow.

**First, do not rebuild the yield calculation.** It exists, staff read it, and the numbers are
already in circulation. DFI reconciles against it (`oracles.md`) rather than producing a competing
figure.

**Second, `Next Run` / `Previous Run` is a traceability edge list** that nobody has recognised as
one. It is the raw material for batch genealogy, and it is already there — no new data capture
required. See [`data-model.md`](data-model.md) §4. This is the highest-leverage thing in the survey:
a capability the plant does not know it already has the data for.

The same report also makes certification misallocation visible — runs where certified and
uncertified input material both fed the same output. It exposes the problem; it does not quantify
the cost or trend it. That quantification is genuine new value.

---

## So what is actually missing

| Gap | Status | Phase |
|---|---|---|
| Cross-product, cross-area despatch priority | **Nothing provides this.** The tracker is per-product | 1 |
| Quality data in queryable form | On paper. Hand-transcribed | 3 |
| End-of-run checkweigher summary, trended | Read off a display, copied by hand, filed | 3 |
| Certification misallocation quantified in £ and trended | Visible per-run; never aggregated | 2 |
| Batch genealogy traversable in both directions | Edge data exists, unused as a graph | 4 |
| Recall drill measured in elapsed time | Not measured | 4 |

Everything in that table is aggregation, transcription, or graph traversal. **None of it is a
recalculation of something the plant already computes.** If a proposed feature does not fit that
description, check this document before building it.

---

## The rule this document exists to enforce

> Before building a screen, find out whether it already exists.

Two systems that disagree about the same number is a worse outcome than the missing screen, because
it costs the credibility that would have made the missing screen worth building.
