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
  days" under audit.
- **Concession rate is a quality metric worth trending.** A rising rate means material is arriving
  older or moving slower, and it is visible in the data long before it is visible in a complaint.

### Observed

An intake label on a crate of Scottish salmon carries a letter-prefixed alphanumeric lot code, a
supply date and a use-by date **exactly eighteen days apart**. That is the constant above, seen in
the wild — and it is also §1's intake namespace in use, since the code is alphanumeric rather than
the six-digit run number a finished case carries.

It is a *supply* date on the label, not a stated harvest date. Whether those are the same field is
C3 below, and it is the question with the most downstream consequence in this section.

**Open — none of this is implementable without these answers:**

| # | Question | Why it cannot be assumed |
|---|---|---|
| C1 | On a fixed 18-day total, what makes one batch 9–10 days at packing and another 11–12? That difference is time in process — a property of the *batch* — yet §4 calls the class a property of the *product*. Both cannot be true | If it is process time, then `DFI_EXTENDED_SHELF_LIFE_DAYS` and the `STANDARD`/`EXTENDED` classes in `contract.py` model a symptom as though it were a product attribute, and rule 1's third tie-break is sorting on the wrong thing |
| C2 | Does superchilled salmon have a total other than 18? | The only other way both figures can hold. Resolves C1 in the opposite direction, and leaves the class model intact |
| C3 | Is the 18 days counted from **harvest**, or from intake/supply as the observed label suggests? | If the anchor is intake, and intake lags harvest by wellboat transit, then every use-by is optimistic by that lag and days-from-harvest cannot be computed at all. A customer clause written in days-from-harvest would be unenforceable against this data |
| C4 | Does a concession extend shelf life *up to* 9 days, or *beyond* it? | Decides whether a conceded batch can outrank an unconceded one in the ordering |
| C5 | Is `DFI_HARVEST_WINDOW_DAYS = 9` the floor on life remaining at packing, rather than a maximum material age as its name says? | If so it is misnamed, and it is the pack-by rule above wearing the wrong label. Two rules on one knob is the failure the last section of this document exists to prevent |

The window length is configuration. It differs by product and it changes.

## 6. Quality checks that currently live on paper

The per-run quality control document carries data that exists in no queryable form. It is the second
half of this project's scope: not new analysis, but ending the transcription.

| Check | Cadence | Notes |
|---|---|---|
| Metal detection | Hourly | Three sensitivity thresholds — ferrous, stainless, non-ferrous — each a different aperture size in mm. Stainless is the least sensitive and therefore the binding constraint |
| Product temperature | Hourly | A single upper limit, low single-digit °C. Excursions are the metric, not averages — an average is guaranteed to hide the excursion that matters |
| Label verification | Per run | Confirms the printed label matches the intended product, including certification claims |
| Clean-down times | Per changeover | Start and end. Allergen changeover integrity depends on these |
| Allergen declaration | Per run | Drives changeover requirements |
| Region of capture | Per run | Regulatory requirement on the finished pack |

**Everything here is hand-written and then hand-copied.** Each transcription is an opportunity to
introduce an error into the one record that would be produced under regulatory challenge.

## 7. The end-of-run checkweigher summary

At the end of every run, the checkweigher displays a summary. It is **read off the screen and copied
onto the paper form by hand.** The fields:

| Field | Why it matters |
|---|---|
| Packs accepted | Denominator for everything else |
| Packs reworked | Recoverable loss |
| Packs wasted | Unrecoverable loss |
| Mean weight | Against target, this is the giveaway measure |
| Tolerance band percentages | Weight distribution — the shape of the giveaway, not just its size |

Giveaway is the gap between mean weight and target weight, multiplied across every pack. It is
individually trivial and collectively expensive, and it is currently invisible between runs because
nobody is going to trend a number that lives on a clipboard.

**Capturing this is the single highest-value transcription to eliminate**: it is a fixed, small,
well-defined set of numbers, produced at a predictable moment, currently copied by hand into a form
that is then filed rather than analysed.

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
