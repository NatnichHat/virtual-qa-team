---
description: "Gate G0 — human confirmation of docs/test_basis.md by the SUT team. Flips Status to confirmed and promotes row confidence. Pre-requisite for /phase2."
argument-hint: "<REQ_ID> [approver name]"
---

# /approve-basis — gate G0

You are the orchestrator running the human confirmation of the test basis.

**Why this gate is a hard stop:** every `Expected_Result` in every test case cites this file. Rows
that are not `confirmed` are excluded from the coverage denominator, so an unconfirmed basis shows up
as a coverage shortfall rather than as false confidence — but only if this gate is taken seriously
rather than rubber-stamped.

## Steps

1. **Read `docs/test_basis.md`.** Confirm `Status: pending_confirmation`. If already `confirmed`, say
   so and stop. If `draft`, abort — `test-basis-analyst` must submit it first.
2. **Present the `## Open questions` table via `AskUserQuestion`**, plus the confirmed / inferred /
   assumed counts and the 3–5 bullet summary from the analyst. Ask the human to bring the SUT team's
   answers. Offer:
   - **Confirmed** — the SUT team verified the rows
   - **Partially confirmed** — some rows verified; the rest stay `inferred`/`assumed` and are excluded
     from the denominator
   - **Change request** — the basis is wrong; re-spawn `test-basis-analyst` with the corrections
3. **On Confirmed / Partially confirmed:** update each verified row's `Confidence` to `confirmed`,
   record the answers in the `## Open questions` table, set `Status: confirmed`, and stamp
   `Confirmed-by` and `Confirmed-at`. Update the `Confirmed rows: N / M` counter.
4. **On Change request:** re-spawn `test-basis-analyst` (update mode) with the feedback, then loop
   back to step 2 with the revised file.
5. **Warn explicitly** if any row remains `assumed`. An `assumed` row blocks any test case that would
   cite it — name which planned cases are affected so the human sees the cost.
6. **Report:** confirmed row count, remaining open questions, and the next command
   (`/approve-story <REQ_ID>` if not yet done, else `/phase2 <REQ_ID>`).

## Rules

- This command is the **only** way `Status: confirmed` is set. No agent flips it.
- Never mark a row `confirmed` on your own judgement — confirmation is the SUT team's act.
