---
description: "Gate G2 — human ratification of the coverage denominators, risk ratings, and impact scope, BEFORE any test case exists. Pre-requisite for /phase3."
argument-hint: "[approver name]"
---

# /approve-approach — gate G2

You are the orchestrator running the ratification of the test approach.

**Why this gate exists and why it is here rather than later:** a specification-coverage percentage is
only as honest as its denominator, and the denominator is produced by the same pipeline that is
graded on it. The control is **sequence** — the denominator is fixed and ratified *before* a single
test case exists. Ratifying it afterwards, once the score is known, would not be a control at all.

## Steps

1. **Read `docs/stories/REQ[ID]_*/test_approach.md`** and `impact_analysis.md`. Confirm
   `Status: pending_approval`.
2. **Present via `AskUserQuestion`:**
   - the **denominator table**, itemised — this is the substance of the gate
   - the risk-rating distribution and the reasoning for every P1 and every P3
   - the level assignment, and the justification for each `ui`/`e2e` assignment
   - **excluded rows** (basis `Confidence != confirmed`) and what they would have contributed
   - **declined exception categories** and why each cannot occur
   - the impact reconciliation and the regression selection command

   Offer: **Ratified** · **Change request** · **Cancel this round**
3. **Change request** → capture the feedback, re-spawn `test-planner` and/or `impact-analyst` scoped
   to it, append an `## Approval log` entry, and loop back to step 2.
4. **Cancel this round** → capture a reason, record it, and stop.
5. **On Ratified:** set `Status: approved` in `test_approach.md`, stamp `Ratified-by` /
   `Ratified-at`, and **freeze the denominators** — record them verbatim in the approval log so a
   later shrink is visible by diff.
6. **Report:** ratified denominators, and the next command — `/phase3 <REQ_ID>`.

## Rules

- This command is the **only** way `test_approach.md` reaches `approved`.
- **The ratified denominators are frozen.** A later correction is a G2 reopen with a recorded reason,
  never a quiet edit. `test-manager` compares `tcm.md` against this file at sign-off precisely to
  catch a denominator that shrank once the score was known.
- Ask the awkward question here rather than at G4: *what is missing from these lists?* A denominator
  is wrong by omission far more often than by arithmetic.
