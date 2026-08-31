# Shared ref — gate runbook

What each gate runs, what its verdict means, and the rule that keeps human attention worth spending.

---

## The two-tier rule

> **A human gate never runs on an artifact that has not passed its own machine checks.**

Every human gate has an **automated pre-check**. If the pre-check fails, the artifact bounces back to
the agent that produced it — automatically, without consuming a reviewer's time or a gate cycle.

This is the difference between eight gates that work and eight gates that get rubber-stamped. A
reviewer asked to check arithmetic, missing fields, and dangling references will eventually stop
reading carefully; a reviewer who only ever sees artifacts that are already internally consistent can
spend their attention on the thing no script can check — **is this actually right?**

| | Automated (script decides) | Human (judgement required) |
|---|---|---|
| Does every AC have a case? | ✅ | |
| Does the arithmetic close? | ✅ | |
| Is every `Expected_Result` non-empty and cited? | ✅ | |
| Does every `Automation_ID` exist as a `[Tags]` entry? | ✅ | |
| **Is this expected result actually correct?** | | ✅ |
| **Is this assertion strong enough to catch the bug?** | | ✅ |
| **Does the basis match the real system?** | | ✅ |
| **Is this failure really the SUT's fault?** | | ✅ |

---

## Gate index

| Gate | After | Kind | Pre-check | Approver | Command |
|---|---|---|---|---|---|
| **G0** | test-basis-analyst | HARD | basis rows have Confidence + sources; no `assumed` row blocking a planned case | SUT team + QA Lead | `/approve-basis` |
| **G1** | story-analyst | HARD | atomic AC table populated; zero open BLOCKING testability defects | BA + PO | `/approve-story` |
| **G2** | test-planner + impact-analyst | HARD | denominators computed; risk rating on every AC; impact identities close | QA Lead | `/approve-approach` |
| **G3** | (folded into G2) | — | — | — | — |
| **G4** | qa-analyst | HARD | `make validate` + `make coverage` + `make testcases-check` all PASS | QA Lead + BA | `/approve-test-case` |
| **G5** | automation-engineer + script-reviewer | HARD | `robot --dryrun` clean; `run-gate.sh scripts` PASS; every baseline entry `scripts_approved` | Automation Lead | `/approve-script` |
| **G6** | before execution | SOFT | env reachable; seed output captured; `Env_Scope` vs `env_matrix.md` consistent; no `destructive` on a shared env | QA Lead + env owner | inside `/phase5` |
| **G7** | defect-analyst | HARD | every failure has a Triage Record with a class and ≥2 evidence items | QA Lead | `/approve-triage` |
| **G8** | test-manager | HARD | every exit criterion in `test_strategy.md` met; report SHA == HEAD | PO / Test Manager | `/signoff` |

**HARD** = the pipeline stops. **SOFT** = may be waived by the approver with a recorded reason, once
the team's numbers are stable.

---

## The artifact gate — `make validate`

`scripts/gate/validate-artifacts.py`. Runs before G2, G4, and G8. Checks:

- every atomic AC has ≥1 test case (`ac_coverage == 1.00`)
- the Count Report has `actual >= minimum` in every category
- every coverage ratio meets its threshold, or the shortfall appears in `## Spec non-compliance`
- `test_cases.csv` parses; every row has a non-empty `Expected_Result` and a `Basis_Ref`
- every `Expected_Result` is ≥15 characters and does not match a known-vague pattern
- every `Basis_Ref` resolves to an existing anchor in `test_basis.md` or an AC in the story
- every case with `Automatable=Y` has an `Automation_ID` that exists as a `[Tags]` entry in the suite
- every `Env_Scope` value is a real environment, and its capabilities support the case's level
- the impact analysis's two identities close
- no `<TBD>` / `TODO` / `[...]` placeholder remains in any artifact for this REQ
- `expected-drift.py` is clean

Exit `0` = PASS (emits `QA GATE: PASS`) · `1` = a check failed · `2` = bad invocation or missing tool.

**Exit 2 is not a failure of the artifact.** It means the gate could not reach a clear verdict — a
missing tool, an unreadable file, a broken script. That routes to whoever owns the tooling, never
back to the agent whose work was never actually checked. Reporting a PASS or a FAIL when the gate
never ran is the one outcome that must never happen.

---

## The script gate — `run-gate.sh scripts`

Runs before G5, by `automation-engineer` as a self-check and **again firsthand by `script-reviewer`**.

1. `robot --dryrun tests/e2e/` — **a hard precondition, not a checklist item.** A file Robot itself
   rejects cannot be meaningfully content-reviewed; fix the parse error first.
2. Forbidden-pattern scan (from `docs/test_stack.md` → Forbidden patterns): `Sleep`, `force=True`,
   DOM-manipulating `Evaluate JavaScript`, raw URLs, `expected_status=any` without an allowed-set,
   hard-coded data, dot notation on `${Test_Data}`, unjustified suite/global variables.
3. Tag selectability — every `E2E-*` in `TEST_BASELINE.md` resolves to exactly one case via
   `--include`. An ID living only in the test name or `[Documentation]` cannot be selected, which
   silently breaks both tag-based reporting and the independently-runnable guarantee.
4. Feature-folder check — every `keyword/`/`page/` resource sits under a folder listed in
   `tests/e2e/FEATURES.md` (or `common`).
5. Test-data key check — every test case name has an exact-matching top-level key in
   `test_data/e2e_baseline.yaml`. A miss fails that test at `Test Setup` with a variable-not-found
   error, never a graceful skip.

Emits `QA GATE: PASS`. **No substitutions:** pasting individual tool outputs does not replace the
sentinel. The gate bundles the right checks with the right enforcement; running them piecemeal lets
the runner pick which ones to honour.

---

## The execution gate — 3 rounds green

Runs inside `/phase5`, before triage.

```
make e2e-deps                      # once per host, not per run
for round in 1 2 3; do
  make e2e-seed ENV=$ENV           # RESEED BEFORE EVERY ROUND, not once up front
  make e2e-run  ENV=$ENV
done
```

**Reseed before every round.** Some cases consume fixed-id fixtures via a real delete with no
API-level recreation path; skipping the reseed makes rounds 2 and 3 fail deterministically against
an already-mutated database. That looks exactly like a flake and is a process gap — and
misdiagnosing it teaches the team to distrust the flake check itself.

**Zero tolerance:**
- A **skipped test is a failure**, never a neutral no-op. `run-e2e.py` re-reads `output.xml` because
  Robot's own exit code counts failures only — a skipped test exits 0 and looks green.
- **No tag-based exclusion of a class of tests from a gate round.** A test excluded by tag never
  appears in any pass/fail/skip count, so a known-broken case can sit hidden indefinitely. If a tag
  is added that excludes tests, the round requires arithmetic reconciliation
  (`total − excluded == run`) and a spec-level justification for the tag.
- Paste all three summary lines **verbatim**. A claim of "3 clean runs" without them counts as not run.

A failure in any round does **not** fail the REQ by itself — it routes to `/phase6` triage, which
decides what the failure actually was. That is the whole point of separating execution from judgement.

---

## Verdicts

- **`approved`** — every check clean, zero findings of any kind including cosmetic ones.
- **`changes_requested`** — any finding. This is the default for a finding; there is no discretion to
  wave one through as non-blocking. List each with a file:line reference. Do not fix it yourself —
  route it.
- **`blocked_gate`** — the gate or its tooling could not run through to a clear PASS/FAIL. The
  artifact is the tooling, not the work. Route to whoever owns the tooling, never to the agent whose
  work was never checked. Deciding between this and `changes_requested` means reading the actual
  failure output, not rationalising from what would be convenient.

Before issuing a third consecutive `changes_requested` on the same artifact, apply
`.claude/refs/circuit-breaker.md`.
