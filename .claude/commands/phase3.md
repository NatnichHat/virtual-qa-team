---
description: "Phase 3 — Test case design. Spawns qa-analyst to derive cases by technique, run the counting protocol, generate test_cases.csv, and merge into TEST_BASELINE.md. Runs the artifact validator. Ends at gate G4."
argument-hint: <REQ_ID>
---

# /phase3 — test case design

You are the orchestrator. See `CLAUDE.md`.

## Pre-checks (abort on any failure)

1. `docs/test_basis.md` has `Status: confirmed`.
2. `test_approach.md` has `Status: approved` (G2 ratified the denominators).
3. Every `story_analysis.md` for this REQ has `Status: approved` and zero open BLOCKING defects.
4. `impact_analysis.md` exists and its reconciliation closes.

## Steps

1. **Spawn `qa-analyst`** (author mode, `subagent_type: "qa-analyst"`) with the REQ folder path.
   Brief it with the reminders that matter:
   - state & boundary analysis **first**, then the Counting Protocol, then cases — never cases first
   - every `Expected_Result` needs a `Basis_Ref`; no oracle, no case
   - walk the full exception catalog and record declined vs deferred distinctly
   - `test_cases.csv` is **generated** (`make testcases`), never hand-written
   - measure ratios against the **frozen G2 denominators**, and record every shortfall in
     `## Spec non-compliance`
   - merge every automatable case into `TEST_BASELINE.md` as a **full-detail** block with its pending
     State — automation cannot start without it
2. **Collect the report.** Handle blockers:
   - **`BASIS_GAP_FOUND`** → halt, re-spawn `test-basis-analyst`, route the human back through
     `/approve-basis` then `/phase3`.
   - **`PRECONDITION_NOT_MET`** → report which and stop.
3. **Run the validator yourself:** `make validate`, `make coverage`, `make testcases-check`. All must
   pass before a human sees anything. If any fails, route it straight back to `qa-analyst` — this
   costs a spawn and saves a gate cycle, which is the whole point of the two-tier rule in
   `.claude/refs/gate-runbook.md`.
4. **Spot-check** (verify, do not trust the report):
   - `design_notes.md`, `test_cases.csv`, and `tcm.md` exist per story
   - the Count Report shows `actual >= minimum` in every category
   - every coverage ratio meets its threshold, or the shortfall is in `## Spec non-compliance`
   - the boundary table in `tcm.md` is populated — an empty one silently inflates every ratio
   - baseline entries were merged with pending States matching `impact_analysis.md`
5. **Close the round.** In `TEST_BASELINE.md`'s `## Approval`: set
   `Test case Approval: pending_approval`, clear its approver/timestamp, **reset
   `Script Approval: —`** and clear its approver/timestamp (new pending entries invalidate the prior
   script approval — the two approvals are a chain, not independent), bump `Round`, set
   `Round started`, and record the REQ. Append a `### Test case Revision N` log entry.

## Reporting back

- per story: count report (actual vs minimum), coverage ratios vs thresholds
- baseline entries merged, with States
- validator output (verbatim `QA GATE:` line)
- next command: `/approve-test-case`
