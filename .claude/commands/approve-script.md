---
description: "Gate G5 — human code review of the automation scripts, after script-reviewer's automated pass. Loops on change request. No cancel option. Pre-requisite for /phase5."
argument-hint: "[approver name]"
---

# /approve-script — gate G5

You are the orchestrator running the human code review of this round's automation.

**Why a human reviews code that already passed an automated review:** a bad script does not announce
itself. It passes, quietly proving less than it claims, and its failures later surface as D2 noise
that drowns out real defects. The automated pass catches convention violations; a human catches "this
test would pass even if the feature were broken."

## Pre-checks

1. `TEST_BASELINE.md` shows `Script Approval: pending_approval`. If `approved`, say so and stop. If
   `—`, abort: run `/phase4` first.
2. Every entry in the round is `scripts_approved` by `script-reviewer`. If not, `/phase4` is not
   finished — do not present.

## Steps

1. **Loop until Approved:**
   1. **Present via `AskUserQuestion`:** case counts per story, files touched, feature folders,
      `script-reviewer`'s verbatim ID-coverage output and dryrun, plus anything worth a second look —
      new shared keywords, WireMock mappings, `requirements.txt` additions, and any scaffold files
      created this round. Offer **Approved** · **Change request**.
   2. **Change request** → capture the feedback, re-spawn `automation-engineer` (revision mode) scoped
      to it, then re-run `script-reviewer` on the re-touched entries. Append a `### Script Revision N`
      log entry and loop. `Script Approval` stays `pending_approval`.
2. **On Approved:** set `Script Approval: approved`, stamp approver and timestamp. The round is now
   closed — the next `/phase2` may start.
3. **Report:** approval status, and the next command — `/phase5 <ENV>`.

## Rules

- This command is the **only** way `Script Approval` is set to `approved`.
- **No cancel option** — test cases are approved and the scripts already passed automated review. The
  only paths forward are Approved or another revision cycle.
- Point the reviewer at the questions the machine could not answer: does this assertion match the
  cited basis? Would this test fail if the feature were broken? Is this locator going to survive a
  UI change?
