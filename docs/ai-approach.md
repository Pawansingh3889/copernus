# How AI gets used in Copernus

> **Doc ref:** COP-AI-01 · **Date:** 11 August 2026 · **Status:** for approval of approach
> **Companion deck:** "Where AI earns its place, and where it is banned"
> **Related:** ARCHITECTURE.md §8 (the pipeline), COP-HW-01 (the machine it runs on)

This paper states how a language model is used in this system, what it is
never allowed to touch, and what has to be true before anyone on site is
shown an answer it produced. It asks for agreement on the approach. It does
not ask for spend; the hardware is costed separately in COP-HW-01 so the two
decisions can be taken on their own merits.

## 1. The starting position: half the work is already done, by someone else

The most useful finding of the environment survey was a shorter scope. A
stock tracker already computes remaining shelf life per batch, bands it by
colour and refreshes on a timer, and staff use it daily. A yield report
already gives input kilos, output kilos and a computed yield per run, and
those numbers are already in circulation.

Rebuilding either would not be neutral. It would produce a second screen
that eventually disagrees with the first, and when two screens disagree the
plant does not adjudicate between them. It stops trusting both.

So the rule that governs this project is: **before building a screen, find
out whether it already exists.** What is genuinely missing is aggregation
(the tracker answers one product code at a time, which is why the fifteen
minute coldstore walk still happens) and the records that live on paper.

## 2. The same rule, applied to models

The interesting move is applying that rule to AI rather than only to
screens. Most proposals put a model in front of every question. This one
routes operational questions away from the model entirely.

**A model is never asked:** how many days a batch has left, what a run
yielded, what should be loaded next, whether the mass balance holds, or what
a batch's parents and children are. Every one of those has a right answer
that a query can produce, and most of them are already produced by a system
the plant trusts. They are answered by ordinary code, and the request never
reaches a model.

**A model is asked** to do language work: read regulations and answer from
them with citations, turn a written narrative into structured fields, move
between languages, and draft a document that a person will check and sign.

The distinction is not stylistic. A model that is asked for a shelf-life
figure is a model that can be wrong about a shelf-life figure. Keeping it
away from those questions is cheaper and more durable than trying to make it
reliable at them.

## 3. What is on paper today

Six records exist in no queryable form. They are the actual scope.

| Record | Cadence | State today |
|---|---|---|
| Metal detection, three apertures in mm | Hourly | Handwritten. A failure puts everything since the last good test on hold |
| Product temperature against an upper limit | Hourly | Handwritten. Excursions are the metric; an average hides the one that matters |
| Label verification: allergen, barcode, site approval, certification, region of capture | Start of run, every reel change, end of run | Handwritten |
| End-of-run checkweigher summary | Per run | Read off a display and copied by hand onto a form that is then filed, while the same numbers sit in the factory database |
| Shelf-life concession | Per occurrence | Paper form in the run pack. The signer, the date and the reason are not queryable, so the concession rate cannot be trended |
| Incidents and near misses | Per occurrence | Paper, often written by people whose first language is not English, then typed up by someone else |

Every hand-copy is an opportunity to introduce an error into the one record
that would be produced under regulatory challenge.

## 4. The three jobs

**Answer regulatory questions, with citations that resolve.** A corpus of
legislation, agency guidance and the site's own procedures is built first,
in Phase 8, with every chunk carrying its source, its version and its
licence tier. The assistant answers from that corpus and names what it used.
An answer whose citation does not resolve to a real stored chunk is rejected
by code before anyone reads it. There is no configuration in which an
uncited answer is displayed.

**Turn an incident into a structured record and a draft.** A narrative
becomes fields, then a severity, then where the law requires it a RIDDOR
draft with a written rationale. Severity is decided three times
independently and the disagreements are surfaced rather than averaged. The
reviewer receives a proposal with its reasoning attached, so they can
disagree with the reasoning rather than only with the conclusion. A named
person files it. The system never does.

**Capture in any language, record in English.** People write in the language
they think in. Both the original text and the English record are stored, so
nothing is quietly lost and the original remains available if a translation
is ever questioned.

None of the three competes with a screen that exists. Each replaces a form
currently filled in by hand.

## 5. The chain around the model

The pipeline has five stages, and only two of them involve a model.

1. **Router** (code). Classifies the request. Operational questions exit here
   and are answered deterministically.
2. **Chain** (model). Small gated steps rather than one large request.
   Independent steps run in parallel; consequence-bearing steps run several
   times and are compared.
3. **Verifier** (code). Runs on every single output. Strict schemas,
   citations must resolve, dates and enumerations and numeric bounds
   checked. No model judgement at this stage.
4. **Judge** (model). A second model from a different developer, given fresh
   context and told to attack the answer. Runs only on outputs that carry
   consequences. It is calibrated against human labels first, and until it
   agrees with people it is not permitted to gate anything.
5. **Sign-off** (person). Named, timestamped, written to the append-only
   audit log. Constraint C-11: no model output stands as a regulatory
   determination without this.

Two further decisions are taken now because neither retrofits cleanly.

**What people type is data, never instructions.** Narratives and shop-floor
free text enter the model as quoted, delimited data. Nothing a person types
can address the model or alter what it was told to do. Adding this later
would mean auditing every prompt already written.

**Prompts are code.** Every prompt lives in the source tree and is versioned
like any other file. Changing a prompt reruns the full evaluation set before
it can merge, exactly as changing the model does. A prompt sitting in a
settings box is an untracked change to a regulated process.

## 6. On-premise, without exception

Both models run on one machine on site. There is no external service in the
path and no account with a model provider.

Three reasons, any one of which would be sufficient. Incident narratives
describe injuries, which is special-category personal data. The line cannot
depend on an internet connection being up mid-shift. And an air-gapped
estate is site policy regardless.

The pair is `Qwen3.6-27B` as the workhorse and `gpt-oss-20b` as the judge,
both under permissive licences, served by vLLM behind a standard interface
so that replacing either is a configuration change plus an evaluation rerun.
The judge comes from a different developer on purpose: a model asked to
check its own sibling's work tends to agree with it.

There is a middle path this paper deliberately does not take. Because
identity is severable in this system, narratives could in principle be
stripped of personal detail and sent to a larger external model. A stripping
step that misses one name is a data breach, so that door stays shut unless a
written data protection assessment opens it.

## 7. How it is proved before anyone trusts it

This project already checks its calculations against systems the plant
trusts, to exact tolerance, before showing anyone a number. A one-day
discrepancy in a shelf-life figure is not a rounding difference; it is a
date-boundary bug that will land on precisely the batches nearest expiry,
which are the only ones anyone is looking at.

Models are held to the equivalent standard.

- A fixed evaluation set of real questions with known good answers, run on
  every prompt change and every model change. A failure blocks the change.
- Polish, Romanian, Lithuanian and Latvian samples in that set from the
  first day, not added after a complaint. Smaller models are weakest exactly
  where the shop floor is strongest.
- The judge calibrated against human labels before it gates anything.
- Every output storing the reasoning behind it, for the approver at the time
  and the auditor two years later.
- An audit log that cannot be updated or deleted by anyone, including the
  database owner, enforced by the database rather than by policy.

## 8. What this will not do

- It will not compute shelf life, yield or despatch priority.
- It will not decide a concession. That is a tasting decision made by
  people; the system records who made it and when.
- It will not file a RIDDOR report, sign off a run, or release a hold.
- It will not answer from memory. Where the corpus does not support an
  answer, it says so rather than producing a plausible one.
- It will not replace a QA judgement. It removes the transcription around
  that judgement.

Each of these is enforced by the architecture rather than by instructions to
the model, which is why it can be stated this plainly.

## 9. Sequence

| Phase | Builds | Gate |
|---|---|---|
| 8 | Corpus: source register with licence tiers, fetchers, versioned store, site procedures | Every chunk carries source, version and licence tier |
| 9 | Grounded assistant: router, chains, verifier, judge, sign-off, multilingual capture, evaluation harness | Evaluation set passes; zero uncited answers |
| 10 | Health and safety: incident and near-miss capture, corrective actions, RIDDOR drafting, registers | Erasing a person severs identity without breaking the audit chain, demonstrated |

This chain is independent of the traceability work, so it can move right
without touching the paperwork story if time runs short.

## 10. What is being asked

Agreement on four points, so that Phase 8 can begin and the hardware
conversation can proceed separately.

1. Models are used for language work only. Operational numbers stay with
   deterministic code and the systems that already own them.
2. Everything runs on site. No assistant data leaves the estate, and no
   external path is opened without a written assessment first.
3. Every consequence-bearing output carries a named human approver and a
   timestamp before it counts as anything.
4. The evaluation set gates prompt changes and model changes alike, and a
   failure blocks the change.

Two things are needed from the site in return: **who owns the data
protection assessment**, and **sight of the health and safety paperwork that
exists today**. Both are Phase 2 discovery items and both block Phase 10.
