---
description: "Phase 6 — Triage, report, sign-off. Spawns defect-analyst to classify every failure with evidence (gate G7), writes the test report, then spawns test-manager for final sign-off (gate G8)."
argument-hint: <run-id>
---

# /phase6 — triage, report, sign-off

You are the orchestrator. See `CLAUDE.md`.

## Input

`$ARGUMENTS` is `<run-id>` from `/phase5`. If missing, use the most recent run directory and say
which you chose.

## Steps

### 1. Triage (gate G7)

1. **If there were failures, spawn `defect-analyst`** (`subagent_type: "defect-analyst"`) with the run
   directory and the failing test IDs. Brief it with the reminders that matter:
   - follow `.claude/refs/triage-protocol.md` §3 **in order** — no skipping a step because the answer
     seems obvious
   - the determinism probe is ≥3 runs on unchanged code with a fresh reseed each time
   - a deterministic failure is **never** a flake
   - ≥2 pieces of evidence per classification, per the protocol's evidence table
   - a D1 needs both corroborations before it is filed against another team
2. **Collect the report.** Then run `/approve-triage` — the human confirms the classifications,
   because a D1 opens a ticket on another team and "flake" is the cheapest exit from this gate.

### 2. Test report

Write `docs/test_cases/REQ[ID]_*/US[ID]/test_report.md` per
`.claude/refs/test-report-template.md`. It must be **self-contained** — one file, every result, every
failure detail, every artifact path. A report that sends the reader hunting is a report nobody reads.

Include: executive summary with the verdict, the coverage table, the 3-round flake table, the
regression section with its selection command, the failure-class distribution, results per level,
failure detail with triage links, **skipped tests named explicitly**, the verbatim seed output, the
artifacts table, and the AC sign-off checklist.

Record the commit SHA — `test-manager` verifies it equals HEAD and treats a mismatch as an automatic
`changes_requested`.

### 3. Sign-off (gate G8)

1. **Spawn `test-manager`** (`subagent_type: "test-manager"`) with the story path.
2. **Collect the verdict:**
   - **`APPROVED`** → the story is `done`. Run `/signoff` to record it.
   - **`CHANGES_REQUESTED`** → route per the sign-off log:
     - coverage shortfall / weak case → `qa-analyst` (revision), then re-run the validator
     - script defect → `automation-engineer` (revision) → `script-reviewer`
     - basis wrong → `test-basis-analyst`; **reopens G0** — the human re-runs `/approve-basis`
     - AC wrong → the BA/PO via `story-analyst`; **reopens G1**, and the REQ re-enters `/phase2`
     - misclassified failure → `defect-analyst`; **reopens G7**
   - **`CIRCUIT_BREAKER_TRIPPED`** → halt the pipeline for this REQ and surface it to the human per
     `.claude/refs/circuit-breaker.md`. Never override it.
3. **After any revision that reopens an approval field**, set that field back to `pending_approval` in
   `TEST_BASELINE.md` and tell the human which gate command to re-run. Phase 6 does not resume for
   this REQ until it passes again.

### 4. Baseline drift check

Run `make baseline-check`. A drift alarm means the baseline no longer matches the suite — fix it
before the next REQ starts. It is an audit, never a routine regeneration.

## Reporting back

- failure counts per triage class, and every D1 with its ticket
- the test report path
- the sign-off verdict, and any routing
- baseline drift status
