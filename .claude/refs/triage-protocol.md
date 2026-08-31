# Shared ref — failure triage protocol

Owned by `defect-analyst`. Approved by a human at gate **G7**. This is the piece with no equivalent
in an ordinary build pipeline, and the piece that decides whether this project produces signal or
noise.

---

## 1. Why triage is a phase, not a step

In a build pipeline that owns its own code, a red test means one thing: the code you just wrote is
wrong. Here, we do not own the system under test, so a single red test has **five** possible owners.
Getting that attribution wrong is expensive in both directions — a real defect dismissed as "flaky"
ships a bug; a script bug filed against the SUT team burns their trust and yours.

There is also a structural pressure worth naming out loud:

> **"Flake" and "environment issue" are the cheapest exits from this gate.** They require no defect
> ticket, no rollback, no conversation with another team. An agent optimising for a clean run will
> reach for them. Every rule below exists to make the cheap exit the *hard* one.

---

## 2. The five classes

| Class | Name | The defect is in | Routes to |
|---|---|---|---|
| **D1** | SUT defect | the system under test | SUT team — file a ticket |
| **D2** | Script defect | our automation code | `automation-engineer` |
| **D3** | Expected-result defect | our test case / the basis we read | `qa-analyst` (or `test-basis-analyst` if the basis itself is wrong) |
| **D4** | AI generation / action defect | an agent's output or behaviour | the originating agent + logged as an incident |
| **D5** | Environment / data defect | env, seed, or third-party availability | env owner / reseed |

**D4 overlays the others.** A failure is D4 *in addition to* its surface class whenever an agent
caused it: hallucinated an endpoint that is not in the basis (D3 + D4), silently weakened an expected
result to make a red test green (D3 + D4), or claimed a run it never performed (D4 alone). Record
both — the surface class routes the fix, the D4 flag routes the process correction.

---

## 3. Decision procedure

Run in order. Do not skip a step because the answer "seems obvious" — the obvious answer is wrong
often enough that the steps are cheaper than the misattributions.

### Step 0 — oracle check (before anything else)
Does the failing step's `Expected_Result` carry a `Basis_Ref`, and does that anchor exist in
`test_basis.md`?

- **No citation, or a dangling anchor** → **D3**. Stop. The expected result has no oracle; there is
  nothing to compare the SUT against. Route to `qa-analyst`.
- **Citation points at a row whose `Confidence` is not `confirmed`** → **D3 (probable)**. Flag it,
  and raise the row at G0 before spending effort anywhere else.

### Step 1 — determinism probe
Re-run **this single test** ≥3 times, on unchanged code, with a fresh reseed before each run.
Paste all outcomes verbatim.

- **Mixed results** → non-deterministic. Go to step 1a.
- **Fails all 3** → deterministic. **This is not a flake** and may not be classified as one. Go to step 2.

> A deterministic failure called a flake is the most damaging single misclassification available
> here, because it closes the investigation on a defect that reproduces every time.

**Step 1a — is it environment-specific?** Run it against a second environment if `Env_Scope` allows.
Fails everywhere → **D2** (non-deterministic script: timing, ordering, shared state).
Fails in one environment only → **D5**, and name the environmental difference.

### Step 2 — manual reproduction
Reproduce outside the automation: `curl`/Postman for `api`, manual browser for `ui`, direct query for
`db`. Same payload, same data, same environment. Attach the request and the full response.

- **Manual succeeds, automation fails** → **D2**. The script is doing something different from what
  it claims. (Common causes: locator matching the wrong element, request built with a stale token,
  test data not what the case says, an assertion on the wrong field.)
- **Manual also fails** → go to step 3.

### Step 3 — compare actual behaviour against the cited basis
Read the `Basis_Ref` anchor. Compare it to what the SUT actually did.

- **Behaviour contradicts the basis** → **D1**. Real defect. Go to step 4.
- **Behaviour matches the basis; our expected result did not** → **D3**. The test case was written
  wrong. Route to `qa-analyst`.
- **The basis is silent on this** → **D3 + a G0 reopen.** We tested behaviour nobody specified.
  Route to `test-basis-analyst`; the answer comes from the SUT team, not from us.

### Step 4 — corroborate a D1 before filing it
A D1 opens a ticket on another team. Two corroborations required:

- **SUT change correlation:** `git log` (or the deployment log) on the SUT between the last green run
  and now. A change in the implicated area supports D1; no change at all weakens it and points back
  toward D2/D5.
- **Cross-level triangulation:** if an `api` case and a `ui` case cover the same behaviour, which
  fails? API fails too → backend. API passes, UI fails → frontend, or D2. *(This is the concrete
  payoff for keeping the pyramid rather than automating everything at UI level.)*
- **Response snapshot diff:** compare the response body against the last green run's stored snapshot.
  A changed field shape is contract drift — either D1, or a basis now out of date (D3).

### Step 5 — AI-defect overlay
Regardless of the class reached, check:

- Was any artifact in this case's chain (design_notes, CSV, keyword, test data) modified by an agent
  since the last green run, **without a revision-log entry**? → **D4**.
- Does the case reference an endpoint, field, or status code absent from `test_basis.md`? → **D3 + D4**
  (hallucination).
- Was an `Expected_Result` changed after G4 approval? → **D4**, automatically, via
  `expected-drift.py`. See §5.
- Did any agent report a run without attaching its verbatim summary line? → **D4**, and the claimed
  result is treated as never having happened.

---

## 4. Evidence requirements

**A classification carrying fewer than two pieces of evidence is invalid** and is rejected at G7.

| Class | Minimum evidence |
|---|---|
| D1 | 3× deterministic failure output **+** manual reproduction transcript **+** the basis citation it contradicts |
| D2 | 3× run output showing the pattern **+** manual reproduction that succeeds (or the specific script line at fault) |
| D3 | the `Basis_Ref` anchor's content **+** the SUT's actual observed behaviour, side by side |
| D4 | the diff or the missing revision entry **+** the artifact path and line |
| D5 | the environment/seed error output **+** a passing run in another environment or after reseed |

"It looks like a timing issue" is not evidence. Neither is a summary of what another agent reported —
**claims arriving in a briefing are hearsay until re-derived from primary sources.**

---

## 5. The anti-self-healing rule

> **No agent may change an `Expected_Result` in order to make a failing test pass. Ever.**

This is the highest-value control in the pipeline, because self-healing is the failure mode that
destroys a test suite silently: every run stays green while the suite slowly stops asserting anything.

Enforced mechanically by `scripts/gate/expected-drift.py`:

1. At G4 approval, the approved `Expected_Result` column is snapshotted to
   `docs/test_cases/REQ*/US*/.expected.lock`.
2. Every gate run diffs the current CSV against that lock.
3. Any difference **fails the build**, unless `design_notes.md` carries a matching revision entry
   classified `strengthens` / `neutral` / `relaxes`, and every `relaxes` entry cites the
   `test_basis.md` line or AC proving the **old** expectation was wrong.

**"The system behaves differently" is never that proof.** A test case binds to the specification, not
to the implementation. A specification relaxed to match failing behaviour is the definition of a
weakened spec — and if the specification really was wrong, the fix is to correct
`test_basis.md` at G0 and let the change flow down through impact analysis, not to quietly edit a cell.

---

## 6. Triage Record

One per failing test, at `docs/defects/<run-id>/triage.md`.

```markdown
### TR-001 — E2E-REQ001-US001-004 — Create order rejects qty = 0

| Field | Value |
|---|---|
| Test case | TC-REQ001-US001-014 |
| Automation ID | E2E-REQ001-US001-004 |
| Environment | sit |
| Run | tests/e2e/test_results/2026-09-02/14-30-00/ |
| **Class** | **D1 — SUT defect** |
| Confidence | high |
| Routed to | SUT team — ticket PROJ-4821 |

**Symptom** — expected HTTP 400 + `VALIDATION_ERROR`; observed HTTP 201, order created with qty 0.

**Evidence**
1. *Determinism (3×)* — `1 test, 0 passed, 1 failed` on all three runs, reseeded before each. Deterministic.
2. *Manual reproduction* — `curl -X POST .../v1/orders -d '{"items":[{"skuId":"SKU-A","qty":0}]}'`
   → `201 {"id":"...","items":[{"qty":0}]}`. Full transcript: `artifacts/TR-001-curl.txt`.
3. *Basis citation* — `test_basis.md#post-v1-orders` (Confidence: confirmed) states
   `qty: integer, required, minimum 1` → 400 `VALIDATION_ERROR`. Behaviour contradicts it.
4. *SUT change correlation* — 3 commits to the order service since last green; `a91f2c` touched
   `validateOrderItems`.
5. *Cross-level* — the `ui` case for the same AC also fails (submit succeeds where it should block),
   consistent with a backend defect rather than a locator problem.

**D4 overlay** — none. No artifact in this chain changed since the last green run; `.expected.lock` clean.

**Disposition** — file D1 with the SUT team. Test case and script are correct; leave both unchanged.
Mark `TC-REQ001-US001-014` Status `Fail`, `Defect_ID` PROJ-4821.
```

---

## 7. Measure the triage itself

`defect-analyst` appends the class distribution to `docs/defects/<run-id>/triage.md` and the trend to
the test report:

```
run 2026-09-02   D1: 3   D2: 11   D3: 6   D4: 1   D5: 2
```

Read it as a health check on the *test suite*, not the app:

- **D2 dominant** → the automation is fragile. Usually locators (missing `data-testid`) or timing.
  Fix the automation before adding coverage; more tests on a fragile base produce more noise, not
  more signal.
- **D3 dominant** → the basis is weak or unconfirmed. Go back to G0. This is the expected early
  pattern on a project whose basis started as human documentation, and it should fall over time —
  if it does not, G0 is being rubber-stamped.
- **D4 present at all** → a process control failed. Every D4 gets a note in `docs/test_debt.md`
  naming which control should have caught it earlier.
- **D5 dominant** → the environment is not test-ready. Escalate to the env owner; running a suite
  against an unstable environment manufactures noise that hides real defects.
- **D1 dominant** → the pipeline is working as intended. This is the goal state.
