---
description: "Gate G8 — final sign-off. Records the test-manager's approved verdict, marks the story done, and closes the REQ."
argument-hint: "<REQ_ID> [approver name]"
---

# /signoff — gate G8

You are the orchestrator recording the final sign-off.

## Pre-checks

1. `test-manager` returned `APPROVED` for every story in the REQ. If any returned
   `CHANGES_REQUESTED`, abort and name what is outstanding.
2. `test_report.md` exists per story and its commit SHA equals `git rev-parse HEAD`.

## Steps

1. **Present the exit criteria from `docs/test_strategy.md` via `AskUserQuestion`**, each with its
   evidence:
   - every coverage dimension meets threshold, against the **G2-ratified** denominators
   - zero cases in `Not Run`; **zero skipped tests** in the run
   - 3 consecutive green rounds with a reseed before each
   - every failure has an approved Triage Record; every D1 has a ticket
   - report SHA equals HEAD
   - no `<TBD>` or placeholder left in any artifact for this REQ

   Offer **Signed off** · **Not yet** (with what is missing).
2. **On Signed off:** append a `### Sign-off pass N — verdict: approved` entry to each story's
   `## Sign-off log` with the approver and timestamp. Set each story's `Status: done`.
3. **Close the REQ:**
   - run `make baseline-check` — a drift alarm must be resolved before the next REQ starts
   - confirm every `TEST_BASELINE.md` entry for this REQ is in a **confirmed** State; a lingering
     `*_pending_REQ[N]` means something was never verified
   - record the failure-class distribution in the REQ `README.md` for trend tracking
4. **Report:** stories signed off, the REQ's coverage summary, the class distribution and its trend,
   any test debt logged, and the next command — `/phase2 <next REQ_ID>`.

## Rules

- This command is the **only** way a story reaches `Status: done`.
- **Never sign off with an open skip, an unapproved triage record, or a stale report SHA.**
- If the coverage denominators in `tcm.md` differ from `test_approach.md`, stop and surface it. A
  denominator that shrank after the score was known is not a measurement, whatever the reason given.
