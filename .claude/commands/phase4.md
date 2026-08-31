---
description: "Phase 4 — Automation. Spawns ONE automation-engineer covering every pending baseline entry, then script-reviewer, looping until every entry is scripts_approved. Ends at gate G5."
argument-hint: (none)
---

# /phase4 — automation

You are the orchestrator. See `CLAUDE.md`.

## Pre-checks

1. `docs/test_cases/TEST_BASELINE.md` shows `Test case Approval: approved`. If not: "run
   `/approve-test-case` first."
2. At least one baseline entry is pending.

## Steps

1. **Spawn exactly ONE `automation-engineer`** (author mode, `subagent_type: "automation-engineer"`),
   briefed with **every** currently pending entry across the round.

   **Never spawn more than one.** It writes to the single shared `test_suites/e2e_baseline.robot` and
   `test_data/e2e_baseline.yaml`, and it is expected to build reusable keywords across cases —
   parallel invocations would clobber each other's edits to the same files and could not see each
   other's work to reuse it. One invocation working the batch sequentially avoids both problems.
2. **Spawn ONE `script-reviewer`** over everything it touched. Same single-invocation rule.
   - Entries coming back `changes_requested` → re-spawn `automation-engineer` (revision mode) scoped
     to just those, then re-run `script-reviewer` on the re-touched entries. Repeat until every entry
     is `scripts_approved`.
   - `script-reviewer` flips each approved entry's pending State to confirmed. Nothing else may.
   - **`SPEC_GAP_FOUND`** → the spec is wrong, not the script. Route to `qa-analyst` (revision mode).
     If that reopens an approved `Test case Approval`, say so — the human must re-run
     `/approve-test-case` before this REQ proceeds.
3. **Spot-check** (verify, do not trust the reports):
   - every case lives in the single shared suite; no per-US or per-REQ folders were created
   - every `E2E-*` ID appears in `[Tags]`, not only in the case name or `[Documentation]`
   - keyword and page resources sit under folders listed in `tests/e2e/FEATURES.md` (or `common`)
   - the regression edits from `impact_analysis.md` were actually applied; REMOVEs were **deleted**,
     not commented out
   - **first round only:** the scaffold files appear in the engineer's report as a separate list, and
     `script-reviewer` covered them. On later rounds they must **not** reappear as newly created.
   - any `requirements.txt` change is an **appended** exact-pinned line, never a bumped version
4. **Close the round.** Set `Script Approval: pending_approval` in `TEST_BASELINE.md`, clear its
   approver/timestamp, and append a `### Script Revision N` log entry.

## Reporting back

- case count per story, feature folders touched, files touched
- `script-reviewer`'s verbatim ID-coverage output and verbatim clean dryrun
- next command: `/approve-script`
