---
description: "Gate G7 — human approval of the failure classifications. Required before any D1 is filed against the SUT team. Loops on change request."
argument-hint: "[approver name]"
---

# /approve-triage — gate G7

You are the orchestrator running the human approval of this run's triage.

**Why a human signs this:** classifying a failure decides who gets the work. A D1 opens a ticket on
another team — wrongly filed, it burns their trust and, next time, they read your reports less
carefully. A wrongly dismissed D1 ships a bug. And "flake" or "environment issue" are the cheapest
exits from triage: no ticket, no rollback, no conversation. That asymmetry is exactly what this gate
is auditing.

## Steps

1. **Read `docs/defects/<run-id>/triage.md`.** Confirm every failure has a Triage Record.
2. **Pre-check, mechanically:** every record has a class and **≥2 pieces of evidence** matching its
   row in the protocol's evidence table. Any record short of that goes straight back to
   `defect-analyst` — do not present an unsupported classification to a human.
3. **Present via `AskUserQuestion`:**
   - the class distribution, with the previous run's for comparison
   - each **D1** with its symptom, its evidence, and the proposed ticket
   - each **D2 / D3** with its route
   - each **D4** with the control that should have caught it earlier
   - **every failure classified as flake or environment, with its determinism-probe output** — call
     these out explicitly rather than folding them into a summary line. They are the ones worth a
     second pair of eyes.

   Offer **Approved** · **Re-triage** (per finding) · **Reclassify** (the human overrides a class).
4. **Re-triage** → re-spawn `defect-analyst` scoped to the disputed records with the human's reasoning
   and what additional evidence to gather. Loop.
5. **Reclassify** → record the human's class **and their reasoning** in the Triage Record as an
   override, distinguishable from the analyst's original. Both belong in the record: an override with
   no trail is indistinguishable from an analyst who got it right the first time, and the D4 trend
   depends on telling those apart.
6. **On Approved:** stamp the triage file with approver and timestamp. **Now** the D1 tickets may be
   raised — filing a defect against another team is an outward-facing action and needs this approval.
7. **Report:** approved classifications, D1 tickets to raise, and the routes taken.

## Rules

- **Never present a classification with fewer than 2 pieces of evidence.**
- **Never let a deterministic failure stand as a flake.** Three failures out of three on unchanged
  code with fresh data is a defect; if a record claims otherwise, send it back.
- **Never raise a D1 ticket before this gate passes.**
