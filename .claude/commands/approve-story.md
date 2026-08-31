---
description: "Gate G1 — human approval of story_analysis.md by BA/PO. Requires zero open BLOCKING testability defects. Pre-requisite for /phase2."
argument-hint: "<REQ_ID> [approver name]"
---

# /approve-story — gate G1

You are the orchestrator running the BA/PO approval of the story analysis.

**Why this gate is a hard stop:** an ambiguous acceptance criterion is the cheapest defect in the
pipeline to fix here and the most expensive to fix later, where it surfaces as a D3 during execution
and looks like a testing problem rather than a requirements problem.

## Steps

1. **Read every `story_analysis.md` under `docs/stories/REQ[ID]_*/`.** Confirm at least one is
   `pending_approval`.
2. **Check the BLOCKING defects.** If any row is still open, present them via `AskUserQuestion` and
   **do not offer Approve.** Options are:
   - **Answer now** — capture the human's resolution, re-spawn `story-analyst` (revision mode) to fold
     it in, then loop.
   - **Amend the story** — the human edits the story file; re-spawn `story-analyst` and loop.
   A BLOCKING defect resolved by an agent's assumption is exactly the failure this gate prevents.
3. **Once zero BLOCKING defects remain**, present via `AskUserQuestion`: the atomic AC count per
   story, the proposed risk ratings, the `Observable at` assignment, and any ADVISORY defects. Offer:
   - **Approved**
   - **Change request** → capture the feedback, re-spawn `story-analyst` (revision mode), loop
4. **On Approved:** set `Status: approved` in each `story_analysis.md` and stamp `Approved-by` /
   `Approved-at`. Record any decisions in the REQ `README.md` locked-decisions section.
5. **Report:** stories approved, atomic AC totals, and the next command — `/phase2 <REQ_ID>` (once
   `/approve-basis` has also passed).

## Rules

- This command is the **only** way `Status: approved` is set on a story analysis.
- **Never approve with an open BLOCKING defect**, and never let an agent downgrade one to unblock a
  round. If the pipeline is stuck on a vague requirement, the requirement is what has to move.
- Never edit the human's story file yourself.
