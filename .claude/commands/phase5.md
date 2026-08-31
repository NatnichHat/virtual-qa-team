---
description: "Phase 5 — Execution. Checks environment readiness (gate G6), seeds, then runs the suite 3 times with a reseed before each round, capturing all evidence. Does not judge failures — that is /phase6."
argument-hint: <ENV>
---

# /phase5 — execution

You are the orchestrator. See `CLAUDE.md`.

## Input

`$ARGUMENTS` is `<ENV>` — `local`, `sit`, or `uat`. If missing, ask once and wait.

## Pre-checks

1. `TEST_BASELINE.md` shows both `Test case Approval: approved` **and** `Script Approval: approved`,
   and the targeted REQ appears in the most recent `Test case Revision` entry. The approvals are
   round-scoped: a REQ that was not in the approved round must not execute.
2. `<ENV>` is a key in `tests/e2e/config/environment.yaml`.
3. `tests/e2e/config/auth/.env.<ENV>` exists.

## Gate G6 — environment and data readiness

Before running anything, verify and present to the human:

1. **Environment reachable** — a health check or a trivial authenticated request. Capture the output.
2. **Capability match** — read `docs/env_matrix.md`. Every case tagged `env:<ENV>` must be supported
   there. A case needing WireMock tagged `env:sit` is a finding — WireMock exists only locally.
3. **Destructive check** — no case tagged `destructive` is selected on a shared environment without
   explicit approval. **This is the irreversible one:** running a destructive suite against shared
   data cannot be undone, so ask rather than assume.
4. **Dependencies** — `make e2e-deps` has been run on this host (idempotent; run it if unsure).
5. **Seed** — run `make e2e-seed ENV=<ENV>` and **capture the full output verbatim**. A seed failure
   that goes unnoticed makes every result below it unreliable, which is why this is captured rather
   than assumed.

Present the above via `AskUserQuestion` and get a go/no-go. This gate is SOFT — the approver may
waive it with a recorded reason once the numbers are stable — but a destructive-on-shared finding is
never waivable by the orchestrator alone.

## Steps

1. **Run the suite three times**, reseeding before each round:
   ```
   for round in 1 2 3; do
     make e2e-seed ENV=<ENV>
     make e2e-run  ENV=<ENV>
   done
   ```
   **Reseed before every round, not once up front.** Some cases consume fixed-id fixtures via a real
   delete with no API recreation path; skipping the reseed makes rounds 2 and 3 fail deterministically
   against an already-mutated database. That looks exactly like a flake and is a process gap —
   misdiagnosing it teaches the team to distrust the flake check itself.
2. **Capture, verbatim:** all three summary lines, the run directories, the seed output, and for UI
   cases the screenshots. Never paraphrase a run result.
3. **Verify zero skips.** `run-e2e.py` enforces this because Robot's own exit code counts failures
   only — a skipped test exits 0 and looks green. If any test skipped, name it; it is a failure, not
   a neutral.
4. **Do NOT judge failures.** Execution and judgement are deliberately separate phases. Record what
   happened; `/phase6` decides what it means.
5. **Record the run ID** (`<date>-<time>`) — `/phase6` and the triage records key off it.

## Reporting back

- the three verbatim summary lines
- run directory paths and the run ID
- pass / fail / skip counts, and the failing test IDs
- next command: `/phase6 <run-id>` (or, if everything is green across all three rounds, `/phase6`
  still runs — it writes the report and takes sign-off)
