# Shared ref — test report template

Written by the **orchestrator** in `/phase6`, at `docs/test_cases/REQ[ID]_*/US[ID]/test_report.md`.

The report must be **self-contained**: a reviewer opens one file and sees every result, every failure
detail, and every artifact path — without chasing logs across the repo. A report that requires the
reader to go find things is a report nobody reads.

````markdown
# US[ID] — Test report

**Timestamp:** <ISO 8601>
**Commit:** <sha>            ← must equal `git rev-parse HEAD` at sign-off; a mismatch is an automatic changes_requested
**Environment:** local | sit | uat
**Run artefacts:** `tests/e2e/test_results/<date>/<time>/`

---

## Executive summary

Read this first. Everything below is supporting detail.

### Verdict
**<X>/<Y> passed · <Z> failed · <W> skipped · <N>/3 rounds green**

### Coverage
| Dimension | Ratio | Threshold | Status |
|---|---|---|---|
| AC | 12/12 = 1.00 | 1.00 | PASS |
| endpoint × status | 31/33 = 0.94 | 0.90 | PASS |
| boundary | 44/52 = 0.85 | 0.90 | **FAIL** |

### Flake check — 3 rounds
| Test ID | Scenario | R1 | R2 | R3 |
|---|---|---|---|---|
| E2E-REQ001-US001-001 | Create order happy path | PASS | PASS | PASS |

Reseeded before every round. Summary lines verbatim in the appendix.

### Regression
| REQ | Test IDs re-run | R1 | R2 | R3 |
|---|---|---|---|---|
| REQ001 | E2E-REQ001-US001-001..007 | PASS | PASS | PASS |

Selection command: `make e2e-run INCLUDE=feature:orders`

### Failures by triage class
| Class | Count | Routed to |
|---|---|---|
| D1 SUT defect | 3 | SUT team — PROJ-4821, PROJ-4822, PROJ-4830 |
| D2 script defect | 1 | automation-engineer |
| D3 expected wrong | 0 | — |
| D4 AI defect | 0 | — |
| D5 environment | 0 | — |

---

## Results by level

### API
| Test case | Automation ID | Status | Duration | Defect |
|---|---|---|---|---|

### UI · DB · Integration
*(same shape)*

## Failure detail

One block per failure, each linking to its Triage Record.

**TC-REQ001-US001-014 — reject qty = 0**
- **Triage:** `docs/defects/2026-09-02-1430/triage.md#TR-001` — **D1**
- **Expected:** `HTTP 400, body.code == "VALIDATION_ERROR"` (`test_basis.md#post-v1-orders`)
- **Actual:** `HTTP 201, order created with qty 0`
```
<verbatim error output>
```
- **Screenshot:** `tests/e2e/test_results/2026-09-02/14-30-00/...png` (UI cases)

## Skipped tests

**A skip is a failure, not a neutral.** Every skipped test is named here with a reason and a route.
An empty section is the expected state.

| Test ID | Reason | Routed to |
|---|---|---|

## Seed chain-probe

Verbatim `make e2e-seed` output. A seed failure that goes unnoticed makes every result below it
unreliable, so it is captured rather than assumed.

<details><summary>seed output</summary>

```
<verbatim>
```
</details>

## Artifacts
| Artifact | Path |
|---|---|
| Robot output.xml / log.html / report.html | `tests/e2e/test_results/<date>/<time>/` |
| Test cases (CSV) | `docs/test_cases/REQ*/US*/test_cases.csv` |
| Coverage report | `docs/test_cases/REQ*/US*/coverage.md` |
| Triage records | `docs/defects/<run-id>/triage.md` |

## Sign-off checklist

Each acceptance criterion mapped to the cases that prove it. This is what the PO actually reads.

| AC | Proven by | Result |
|---|---|---|
| AC-1 | TC-…-001, TC-…-002, E2E-…-001 | PASS |

## Raw output

<details><summary>3 rounds — verbatim summary lines</summary>

```
Round 1: 78 tests, 78 passed, 0 failed, 0 skipped
Round 2: 78 tests, 78 passed, 0 failed, 0 skipped
Round 3: 78 tests, 78 passed, 0 failed, 0 skipped
```
</details>
````
