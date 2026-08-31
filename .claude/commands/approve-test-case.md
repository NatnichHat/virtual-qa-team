---
description: "Gate G4 — human approval of the test cases, TCM, and CSV. Loops on change request; can cancel the round. Snapshots the approved expected results for drift detection. Pre-requisite for /phase4."
argument-hint: "[approver name]"
---

# /approve-test-case — gate G4

You are the orchestrator running the human approval of this round's test cases.

**What only a human can check here:** the machine already proved every AC has a case, the arithmetic
closes, and every expected result is non-empty and cited. What it cannot check is whether the
expected results are **right** and whether the assertions are **strong enough to catch the bug**.
That is this gate's whole job — spend the attention there, not on re-checking the counts.

## Pre-checks

1. `TEST_BASELINE.md` shows `Test case Approval: pending_approval`. If `approved` or `Canceled`, say
   so and stop. If `—`, abort: run `/phase3` first.
2. `make validate`, `make coverage`, and `make testcases-check` all pass. **If any fails, do not
   present to the human** — route back to `qa-analyst` and re-run. A human gate never runs on an
   artifact that has not passed its own machine checks.

## Steps

1. **Loop until Approved or Cancel:**
   1. **Present via `AskUserQuestion`:** the REQ, per story the artifact paths and count report,
      coverage ratios against the ratified denominators, the `## Spec non-compliance` rows, the
      declined/deferred exception rows, and which baseline entries were added / modified / removed
      with their States. Offer **Approved** · **Change request** · **Cancel this round**.
   2. **Change request** → capture the feedback, re-spawn `qa-analyst` (revision mode) with driver
      `"G4 human review pass N"`, wait, append a `### Test case Revision N` log entry, re-run the
      validator, and loop with the updated summary. `Test case Approval` stays `pending_approval`.
   3. **Cancel this round** → capture a reason, set `Test case Approval: Canceled`, log it, and stop.
2. **On Approved:**
   1. Set `Test case Approval: approved` and stamp `Test case Approved-by` / `Test case Approved-at`.
   2. **Snapshot the approved expected results:** run `make expected-lock`, which writes
      `docs/test_cases/REQ*/US*/.expected.lock`. **This is the anti-self-healing baseline** — from
      here on, any change to an `Expected_Result` without a matching classified revision entry fails
      the build. Do not skip it: without the lock, `expected-drift.py` has nothing to compare against
      and the strongest control in the pipeline is silently inert.
   3. Append a `### Test case Revision N — driver: human approval` log entry.
3. **Report:** approval status, lock file paths, next command `/phase4`.

## Rules

- This command is the **only** way `Test case Approval` is set to `approved` or `Canceled`.
- **Never approve without writing the expected-result lock.**
- Ask about assertion strength explicitly — "would this case actually fail if the system were wrong?"
  is the question the machine cannot ask.
