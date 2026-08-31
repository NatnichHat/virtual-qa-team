---
description: "Phase 2 — Approach and impact. Spawns test-planner (risk, levels, and the frozen coverage denominators) and impact-analyst (three-layer impact + regression scope) in parallel. Ends at gate G2."
argument-hint: <REQ_ID>
---

# /phase2 — approach and impact

You are the orchestrator. See `CLAUDE.md`.

## Input

`$ARGUMENTS` is `<REQ_ID>`. If missing, ask once and wait.

**One REQ per round.** `TEST_BASELINE.md` is a single project-wide file, and the execution gate runs
the whole suite unscoped. If a round merged a second REQ's cases into the baseline before that REQ's
own automation existed, the first REQ's execution gate would run them and fail against behaviour
nobody has built or verified yet — for reasons that have nothing to do with the REQ under test.

## Pre-checks (abort with a clear message on any failure)

1. **Round sequencing.** Read `docs/test_cases/TEST_BASELINE.md`'s `## Approval` section:
   - `Test case Approval: pending_approval` → "a round is awaiting test-case approval — run `/approve-test-case`."
   - `Test case Approval: approved` and `Script Approval: pending_approval` → "run `/approve-script`."
   - Otherwise (`—`, `Canceled`, or both `approved`) the slot is free.
2. `docs/test_basis.md` has `Status: confirmed`. If not: "run `/approve-basis <REQ_ID>`."
3. Every `story_analysis.md` for this REQ has `Status: approved`. If not: "run `/approve-story <REQ_ID>`."

## Steps

1. **Spawn `test-planner` and `impact-analyst` in parallel** — one message, two `Agent` calls, each
   with `subagent_type` set explicitly, both briefed with the REQ folder path.
   - `test-planner`: confirm risk ratings, assign levels, and **compute and itemise the coverage
     denominators**. Remind it to count `confirmed` basis rows only, and that every denominator must
     be itemised — a human cannot ratify a number they cannot recount.
   - `impact-analyst`: three-layer impact, the reconciliation arithmetic, the regression selection
     command, and the pending baseline state updates. Remind it to grep `Basis_Ref` for every changed
     basis anchor before reasoning, and that an empty regression table needs its reasoning stated.
2. **Collect both reports.**
3. **Handle blockers, in priority order:**
   - **`BASIS_GAP_FOUND` / `BASIS_NOT_CONFIRMED`** → halt. Re-spawn `test-basis-analyst` with the gap,
     then tell the human to re-run `/approve-basis <REQ_ID>` and `/phase2 <REQ_ID>`. Do not continue
     inside this invocation — re-confirmation is a human gate.
   - **Reconciliation arithmetic does not close** → halt and report exactly which identity failed and
     by how much. A near-miss is a miss.
   - **Untestable AC surfaced late** → route to `story-analyst`, tell the human to re-run
     `/approve-story` then `/phase2`.
4. **Spot-check:**
   - every denominator in `test_approach.md` is itemised, not a bare number
   - every AC has a risk rating, and every P1/P3 has one line of reasoning
   - the impact reconciliation closes for every touched feature
   - the regression selection command is concrete and names its case count
   - any proposed `FEATURES.md` addition is flagged for ratification, not already created
5. **Set `Status: pending_approval`** in `test_approach.md`.

## Reporting back

- the denominator table (this is what the human ratifies)
- risk-rating distribution and the P1/P3 reasoning
- impact counts per action + "reconciliation closes ✅" or the exact failure
- the regression selection command
- next command: `/approve-approach`
