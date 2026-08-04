# Domain knowledge

What a session of reading the real environment taught us. Read this before writing a query against
the source system — several of these facts will cost you a day if you discover them by debugging.

| File | Read it when |
|---|---|
| [`data-model.md`](data-model.md) | Before joining anything. Two separate identifiers share the name `batch_code`, and one field packs multiple values into one string |
| [`business-rules.md`](business-rules.md) | Before sorting, filtering, or thresholding anything the plant acts on |
| [`existing-systems.md`](existing-systems.md) | Before building a screen. Some of it already exists and is trusted |
| [`oracles.md`](oracles.md) | Before showing a number to anyone on site |

## De-identification rule

**This repository records rules, field names and data shapes. It does not record who the client is.**

Excluded, permanently, regardless of how convenient it would be:

- the client's company or site name
- site approval codes, certification numbers, and other regulator-issued identifiers
- supplier names, and batch or run numbers traceable to a real consignment
- prices, margins, and volumes attributable to a named counterparty

Where a real value would otherwise appear, describe its **shape** instead — "a six-character
alphanumeric lot code", "a two-letter country prefix followed by five digits". The shape is what the
code needs. The value is what a leak needs.

This matters more than usual here: the licence question is unresolved (`ROADMAP.md`, blocker B01),
so nobody can yet say who is entitled to read this repository. Git history is not editable in
practice once pushed — the cheap moment to leave a detail out is before the first commit that
contains it.

## Why this lives in the repo

An earlier version of this plan put these findings in a machine-local assistant memory directory.
That was the wrong home. Memory is per-machine and per-environment: it does not survive a fresh
clone, it is invisible in code review, it cannot be corrected by a colleague who finds a mistake,
and it does not appear in the diff when a rule it documents is violated.

Domain knowledge that constrains code belongs next to the code, under version control, in the same
review path.
