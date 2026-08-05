# Business rules

Rules the plant actually operates by. Where these differ from the obvious implementation, the
difference is the point.

---

## 1. Despatch priority is two-dimensional

The obvious implementation is `ORDER BY use_by_date`. **It gives despatch the wrong answer for the
first half of every working day.**

Two independent things determine what gets loaded next:

| Dimension | Meaning |
|---|---|
| **Chasing** | The order is being actively chased: flagged in the plan comments, due out on the early cut-off, worked from the start of shift |
| **Days to expiry** | How soon the stock spoils — the FEFO dimension |

**Chasing outranks days to expiry.** An order that must be on the early van beats a batch that
expires a day sooner but ships on the later van, because missing the early van means missing the
customer's delivery window entirely, whereas the sooner-expiring batch is still perfectly saleable
tomorrow. A one-dimensional expiry sort inverts this every morning and then silently becomes correct
after the early cut-off, which is exactly the pattern that makes people quietly stop trusting a
screen without ever filing a bug.

Implemented in `src/dfi/modules/despatch/service.py` as `priority_key()`. The sort key, in order:

1. **Chasing before non-chasing**, but only while the early cut-off is still ahead. After the
   cut-off passes, a chasing flag no longer confers priority — the van has gone, and continuing to
   pin it to the top of the list actively misleads.
2. **Sooner use-by date first.**
3. **Standard shelf life before extended shelf life** on an equal use-by date. Two products sharing
   a use-by date do not share the same remaining margin for error: the one with the shorter shelf
   life was packed more recently and has less slack downstream.
4. **A stable tie-break** (product code, then location) so the list does not reshuffle between
   refreshes. An order that changes when nothing changed reads as a bug and destroys trust in the
   screen.

Timing values are configuration, not literals in the sort — sites and seasons differ.

## 2. Stock with no use-by date is excluded, and counted

A row with a NULL use-by date cannot be placed in an expiry ordering. Dropping it silently means the
list quietly under-reports stock and nobody knows by how much.

**Exclude it from the ordering and return the count**, so the UI can say "N items excluded — no
use-by date" and someone can go and fix the underlying records. `rank()` returns both the ordered
list and the excluded count for this reason. Silent exclusion is the failure mode this rule exists
to prevent.

## 3. The same batch in two locations is two rows

Stock in the coldstore and stock already staged for despatch are not interchangeable — one requires
a picker to go and get it, the other does not. They are listed separately, per location, and sorted
independently.

## 4. Shelf life: standard vs extended

| Class | Life remaining at packing |
|---|---|
| Standard | 9–10 days |
| Extended (superchilled) | 11–12 days |

**An earlier version of this document said the two classes differ "by roughly a week", and two other
documents put standard at +7 days. Both were wrong** — the real separation is one to three days. The
class boundary is unaffected: 11 days still divides them, which is what `DFI_EXTENDED_SHELF_LIFE_DAYS`
encodes.

The urgency bands are affected. With the amber boundary at 7 days remaining, a standard batch is
GREEN for only the first two or three days of its life. That may be correct — but it is not derived
from these figures and must not be. The bands have to match the existing stock tracker's exactly
(Oracle 2, [`oracles.md`](oracles.md)), and that check has not been run. Treat the current boundaries
as provisional until it has.

The longer class must not be despatched ahead of the shorter one when both are available and
otherwise equally urgent (rule 1, tie-break 3).

These are what **remains at packing**, not a grant made at packing. The clock started at harvest and
processing has already spent part of it (§5).

The class has been treated as a property of the product, not of the batch — **and §5's fixed 18-day
window puts that in doubt** (C1). On a fixed total, the difference between 9–10 and 11–12 days
remaining is time in process, which is a property of the batch. Do not build on the class until that
is settled.

Either way, do not infer the class from the observed gap between pack date and use-by date on a
single batch — a concession can extend that gap past the class default (§5), so a conceded standard
batch reads as an extended one. Inferring the class from the gap misclassifies exactly the batches
that most need correct handling.

## 5. The harvest clock, and the concession at the end of it

**The shelf-life clock starts at harvest, not at packing.** For salmon, harvest to use-by is
**always 18 days** — a constant, not a per-product figure. Everything the plant does happens inside
it.

```
harvest ├──────────────────── 18 days, fixed ────────────────────┤ use-by
        │                                    │
        └── intake → filleting → chopping ───┴── packing
                                                ≥ 9 days must remain,
                                                so pack by harvest + 9
```

Two dates fall straight out of that constant, and neither exists in DFI today:

```
use_by_date  = harvest_date + 18
pack_by_date = harvest_date + 9     -- past this, packing needs a concession
```

So every day a lot spends in process is a day off the finished pack's life. Slow movement upstream
does not show up as a delay — it shows up as a shorter date on a pack downstream, which is a much
harder thing to notice and a much more expensive one.

**At packing, at least 9 days must remain. Below that, a concession is taken, and the concession
extends the shelf life.** Product beyond the window is not automatically scrap — it is a decision,
taken by tasting, and recorded.

That last point is the one with teeth for DFI, because it means **a use-by date is not always a
derivation.** For a conceded batch it is a decision — and on the finished pack, the two are
indistinguishable.

### What this forces into the model

- **Harvest date is a required field, and DFI does not currently have it anywhere.** `StockItem`
  carries a use-by date and nothing upstream of it. Two batches sharing a use-by date can be
  different ages, and a customer specifying maximum days-from-harvest will accept one and reject the
  other. Use-by alone cannot express that.
- **18 is a constant, so it is configuration, not a product attribute** — with the unit in the name,
  like every other threshold in this document. Cheaper than the product dimension an earlier version
  of this section called for, and it is the whole of what `use_by` and `pack_by` need.
- **Days-in-process is derivable** once harvest date and pack date are both present — and it is the
  measure that explains a short-dated pack, so it is worth having for its own sake.

### Implications for anything DFI reports

- **A concession is an event with an owner and a timestamp**, not a status flag. "Approved" without
  who and when is not an audit trail. That matters more once the concession is what set the use-by
  date somebody is despatching against.
- **An extended use-by must carry its provenance.** A date a rule produced and a date a human chose
  have to be distinguishable in the model, or nobody can answer "why does this batch have twelve
  days" under audit. Observed: the concession today is a **paper form** filed with the run
  paperwork — the decision, its signer and its date exist in no queryable form, so provenance (and
  the trending below) starts from zero.
- **Concession rate is a quality metric worth trending.** A rising rate means material is arriving
  older or moving slower, and it is visible in the data long before it is visible in a complaint.

### Observed

An intake label on a crate of Scottish salmon carries a letter-prefixed alphanumeric lot code, a
harvest date and a use-by date **exactly eighteen days apart**. That is the constant above, seen in
the wild — and it is also §1's intake namespace in use, since the code is alphanumeric rather than
the six-digit run number a finished case carries.

The first date is the **harvest/kill date** (confirmed): use-by = harvest + 18, so days-from-harvest
is computable. That answers C3. Also confirmed: superchilling is decided **per customer order** and
applied on site — an order attribute, not a product property (bears on C1/C2's classing).

A second observed intake tag — fresh Norwegian salmon this time, lot `F6160B` — carries 11.06.26
and 29.06.26: the same eighteen days, to the day, across a different supplier and origin. Two
origins on otherwise identical tags is also §6's region-of-capture row seen from the intake side:
region travels with the batch.

The lot code itself decodes — `F`·`6`·`160`·`B`: **F** for fresh, **6** for 2026, **160** the
Julian day of year, **B** the second batch of that day. But day 160 of 2026 is **9 June**, two
days before the 11.06 harvest/kill date on the same tag (use-by − 18 lands on 11.06 exactly). So
the code and the printed dates anchor two events two days apart — the shape of the wellboat-transit
lag the original C3 worried about. Likeliest reading: the lot is opened when the wellboat loads,
and the kill happens on arrival two days later; but that is unverified. Until it is, the printed
dates are authoritative and the code stays an **opaque identifier** — parse it for sanity checks if
ever needed, never for a date the tag states explicitly.

**All answered (2026-08-04):**

| # | Answer | Consequence |
|---|---|---|
| C1 | **Superchilling separates the classes** — a per-customer-order process decision, not a product attribute | `STANDARD`/`EXTENDED` must live on the *order*, not the product; build it that way here |
| C2 | **No — the total stays 18** for superchilled and standard alike | No second total to model |
| C3 | **Anchored on the harvest/kill date** | Days-from-harvest is computable; customer clauses written in it are enforceable |
| C4 | **Concession is capped at pack date + 10**; superchilled packing itself needs none | A conceded batch cannot outrank a superchilled one |
| C5 | **Minimum life remaining at packing** — the pack-by floor, not a maximum material age | The `DFI_HARVEST_WINDOW_DAYS` name (dora-factory) is wrong; name it as the floor when it is ported |

The window length is configuration. It differs by product and it changes.

## 6. Quality checks that currently live on paper

The per-run quality control document carries data that exists in no queryable form. It is the second
half of this project's scope: not new analysis, but ending the transcription.

The boundary of that claim matters: **units and weights already live in SI**, the site's factory
system — baskets in, cases out, every transaction carrying a count and a weight in kg. The paper
record even cross-checks itself against it ("does SI match the product basket count?"). What exists
in no queryable form is the rest of this section: the checks themselves.

| Check | Cadence | Notes |
|---|---|---|
| Metal detection | Hourly | Three sensitivity thresholds — ferrous, stainless, non-ferrous — each a different aperture size in mm. Stainless is the least sensitive and therefore the binding constraint (observed: Fe 2.5, SS 4.0, NF 3.0). A failed test reports to Engineers & QA, and everything since the last good test goes on hold for re-checks |
| Product temperature | Hourly | A single upper limit, low single-digit °C (observed target: < 4 °C, QA notified above it). Excursions are the metric, not averages — an average is guaranteed to hide the excursion that matters |
| Label verification | Start of run, every reel change, end of run | Confirms the printed label matches the intended product, including certification claims. The control unit is the **reel** (label roll), not the individual label — see below |
| Clean-down times | Per changeover | Start and end, inspected and released by a team leader. Allergen changeover integrity depends on these |
| Allergen declaration | Per run | Drives changeover requirements |
| Region of capture | Per batch code | Regulatory requirement on the finished pack. Arrives on the supplier's trace tag, keyed in at goods-in; the retail traceability sheet lists it per batch code, and the run paperwork is filled from that sheet — model it on the batch, let runs inherit it |

**Everything here is hand-written and then hand-copied.** Each transcription is an opportunity to
introduce an error into the one record that would be produced under regulatory challenge.

### Label control is reel reconciliation

Labels arrive on rolls of 1,500 or 2,000 — the paperwork calls them **reels**. A reel is **issued**
to a run and **returned** at the end of it, and both movements are recorded by count *and* by
weight — weight is the practical cross-check, because nobody hand-counts the labels remaining on a
part-used reel. The issue and return movements are recorded in **SI** — reels are stock items like
film and boards — so the reconciliation's inputs are already digital; what exists only on paper is
the verification events. Every pack passes through sealing and then labelling from the reel on the
machine, so verifying the reel once verifies every pack behind it.

The packing record verifies the reel at three moments — first-reel check at start of run, a check at
**every reel change**, and an end-of-run label check. Each check carries the operative, the time,
the reel batch number, and a machine vision verification (Dimaco) recorded as PASS/FAIL with its job
number; a sample label from each reel is physically attached to the record. The fields checked
against the approved specification: allergen declaration, barcode, site approval number,
GGN / MSC / ASC certification number, and region of capture.

The reconciliation is the actual control: issued minus returned is the number of labels used, and
that figure is reconciled against **all packs labelled — accepted, reworked and wasted alike — plus
any damaged labels**. The checkweigher's accepted count is not the denominator: a pack that was
reworked or wasted still consumed a label. A gap is a label whose destination is unknown — and an
unaccounted-for label is exactly how a wrong allergen declaration or certification claim ends up on
a pack, which is what the checks above exist to prevent.

For the model this means the reel, not the printed label, is the natural entity: an issue record and
a return record, each carrying count and weight, plus the verification events — start, each change,
end — bracketing the run they served.

The **case barcode is a different artifact** and must not be conflated with the pack label: finished
product goes into baskets or boxes whose barcode labels OCM generates, and the packing record
attaches and checks those case labels in their own section.

## 7. The end-of-run checkweigher summary

At the end of every run, the checkweigher displays a summary. It is **read off the screen and copied
onto the paper form by hand** — even though the same numbers land in the SI database. The hand-copy
runs in parallel with data that is already digital. The fields:

| Field | Why it matters |
|---|---|
| Packs accepted | Denominator for everything else |
| Packs reworked | Recoverable loss |
| Packs wasted | Unrecoverable loss |
| Mean weight | Against target, this is the giveaway measure |
| Tolerance band percentages | Weight distribution — the shape of the giveaway, not just its size. On the form this is "T1–T2 %", against the T1/T2 settings declared in the run header |

Giveaway is the gap between mean weight and target weight, multiplied across every pack. It is
individually trivial and collectively expensive, and it is currently invisible between runs because
nobody is going to trend a number that lives on a clipboard.

**This is the single highest-value transcription to eliminate, and it is a read, not a build**: a
fixed, small, well-defined set of numbers, produced at a predictable moment, already sitting in the
SI database (the `SI_DTI_ARCHIVE_Weigher` tables are the candidates) — currently copied by hand into
a form that is then filed rather than analysed. Locate the table, confirm it populated, and the
transcription is over.

---

## 8. Product tiers and the allocation ladder

**Value tiers off the chopper.** Cut highest-value-first; the switch point is manual. Cod: loins
(260 g, belly) → fillets (250 g, sides) → simply (2–10 pieces, tail/trim), cutter switched once
the loins target is met. Salmon: 140 g → 120 g → 110 g → simply. Nothing records whether a
different switch point would pay better, or which supplier's fish cuts more loins.

**The certification ladder.** RSPCA Assured sits above GlobalG.A.P. / standard, asymmetrically:
premium material may fill a standard order — a silent, untracked margin loss — but standard
material may never fill a certified claim. A downgrade is a cost; an upgrade is a breach.

---

## Rules that are configuration, not code

Every threshold above belongs in configuration with the units named. None of them should appear as a
literal in a query or a service function:

- early despatch cut-off time, and shift start
- urgency band boundaries in days
- shelf-life class boundary in days
- harvest window in days
- temperature limit in °C
- metal detection apertures in mm, per metal type
- giveaway alert threshold in grams

A threshold hardcoded in a query is a threshold that will be wrong at the next site, the next
season, or the next audit — and that nobody will find.
