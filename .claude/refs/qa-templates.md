# Shared ref — artifact templates

Authoritative templates for every markdown artifact the pipeline produces. Read the relevant section
on demand, right before writing that file — do not preload all of them.

Single source of truth. Do not re-inline these into an agent definition; link here.

---

## `story_analysis.md` template — written by `story-analyst`, per story

```markdown
# US[ID] — Story analysis

**Story:** `docs/stories/REQ[ID]_[name]/US[ID]_[story_name].md` (human-supplied — never edited by an agent)
**Requirement:** REQ[ID]
**Status:** `draft` | `pending_approval` | `changes_requested` | `approved`

## Atomic acceptance criteria

Each row is ONE testable assertion. A criterion containing "and", "or", or two outcomes is split
until each row can be proven true or false on its own. **This table is the denominator for
`ac_coverage`** — splitting badly here distorts every downstream number.

| AC ID | Given | When | Then | Observable at | Risk |
|---|---|---|---|---|---|
| AC-1 | | | | api / ui / db / integration | P1 / P2 / P3 |

- **Observable at** — the lowest level where this outcome is genuinely visible. `test-planner` uses
  it to assign levels; getting it wrong pushes cases up the pyramid where they are slow and fragile.
- **Risk** — proposed by `story-analyst`, confirmed by `test-planner`, ratified at G2.

## Testability defects

Every reason a criterion cannot yet be turned into a test with a concrete expected result.
**G1 does not pass while any BLOCKING row is open.**

| # | AC | Defect | Severity | Question for BA/PO | Resolution |
|---|---|---|---|---|---|
| T1 | AC-2 | "ระบบต้องตอบเร็ว" — no threshold given | BLOCKING | เร็วคือกี่มิลลิวินาที และวัดที่ percentile ไหน | |
| T2 | AC-4 | two outcomes in one criterion | ADVISORY | | split into AC-4a / AC-4b |

Common defect kinds, all of which produce untestable cases if let through:
ambiguous quantities ("fast", "many", "recent") · missing error behaviour (happy path only) ·
no oracle (nothing states the correct value) · unstated preconditions · conflicts with another AC ·
behaviour the basis does not cover · implied but unstated permissions.

## Domain terms

Terms whose meaning must be pinned before anyone writes an expected result.

| Term | Meaning as used here | Source |
|---|---|---|

## Out of scope for this story
- [explicit non-goals — a reader must not have to infer these]

## Open questions for BA/PO
Numbered, highest-risk first. **The orchestrator asks the human — subagents cannot.**
Answers are recorded in the REQ README's `## Decisions confirmed by the user (locked)` section, G-numbered.

1.
```

---

## `impact_analysis.md` template — written by `impact-analyst`, per REQ, **before any per-story design**

```markdown
# REQ[ID] — Impact analysis

**Requirement:** REQ[ID] — [name]
**Catalog:** `tests/e2e/FEATURES.md`
**Baseline:** `docs/test_cases/TEST_BASELINE.md`
**Basis change log reviewed:** [date / "no changes"]

## Layer 1 — Requirement impact

Which existing capabilities this change touches. Regression blindness starts here: a REQ treated as
"only new tests" always misses the cases it silently invalidated.

| Feature | New / Changed / Unaffected | What changes | Stories |
|---|---|---|---|

**Proposed new features** (require human ratification in `FEATURES.md` — never invent a folder or tag):

| Proposed feature | Scope | Why the existing catalog does not cover it |
|---|---|---|

## Layer 2 — Test asset impact

Every existing test case that must be added, modified, removed, or re-run. All levels, not just e2e.

| Test ID | Feature | Level | ADD / MODIFY / REMOVE / RE-RUN | Reason | Basis anchor |
|---|---|---|---|---|---|

### Coverage reconciliation — must close the math

| Feature | Existing | Kept as-is | Modified | Removed | Net-new | Target total | Closes? |
|---|---|---|---|---|---|---|---|
| _example_ | 6 | 2 | 3 | 1 | 5 | 10 | ✅ (2+3+5=10; 6−1=2+3) |

Both identities must hold, per feature:

    Kept + Modified + Net-new  ==  Target total
    Existing − Removed         ==  Kept + Modified

No test may be counted as both Modified and Net-new. **If either identity fails, the analysis is
incomplete — block, do not proceed to design.** The arithmetic is the whole value of this table: it
is what turns "we thought about regression" into something a reviewer can check in thirty seconds.

## Layer 3 — Automation impact

| Asset | Path | Impact | Shared? | Blast radius |
|---|---|---|---|---|
| keyword | `keyword/orders/create_order.resource` | signature change | **yes — 4 features** | E2E-...-002, -007, -011 |
| test data | `test_data/e2e_baseline.yaml` | new keys | yes — project-wide | re-read before editing |
| env config | `config/environment.yaml` | new session alias | yes — all envs | add placeholder for sit/uat |

Flag every **shared** asset explicitly. `test_suites/e2e_baseline.robot` and
`test_data/e2e_baseline.yaml` are project-wide single files — an edit there can break a story nobody
in this round is thinking about.

## Regression selection

The **exact command** for this REQ's regression run. Scope is computed here, not guessed at execution time.

```
make e2e-run INCLUDE=feature:orders
make e2e-run INCLUDE=US045
```

| Selection | Cases | Why included |
|---|---|---|

## Baseline state updates

Every `TEST_BASELINE.md` entry whose State changes. All transitions are **pending** —
`script-reviewer` confirms them later.

| Feature | Test ID | Old state | New state (pending) | Reason |
|---|---|---|---|---|
| orders | E2E-REQ001-US001-001 | active | modify_pending_REQ002 | response shape changed |
| orders | E2E-REQ012-US045-001 | _(new)_ | planned | net-new |

**Rule:** every ADD → `planned`; every MODIFY → `modify_pending_REQ[N]`; every REMOVE →
`remove_pending_REQ[N]`. Never jump straight to a confirmed state here.
```

---

## `design_notes.md` template — written by `qa-analyst`, per story

The human-reviewable source. `test_cases.csv` is generated from it — see `.claude/refs/csv-schema.md`.

```markdown
# US[ID] — Test design notes

**Story:** US[ID] — [name] · **Requirement:** REQ[ID]
**Risk rating:** P1 | P2 | P3 (ratified at G2)
**Techniques applied:** EP, BVA, DT, ST, EG, UseCase, CRUD

## Derivation

Show the work. A reviewer must be able to see WHY these cases and not others — the cases alone do
not carry that, and without it the review degenerates into reading a list.

### Equivalence classes
**`Rule` is the source for `validation_rule` coverage** (`coverage-model.md` dimension 3) — the
named rule in `test_basis.md` → Validation rules this class exercises (e.g. `VAL-evidence-001`).
Leave it `—` only when the class checks something `test_basis.md` has no named rule for (e.g. a
bare type/shape check with no documented business rule behind it) — an empty `Rule` column excludes
that row from the dimension entirely, so don't leave it blank out of habit.

| Field | Rule | Valid classes | Invalid classes | Cases |
|---|---|---|---|---|

### Boundary analysis
**This table is the denominator for `boundary_coverage`.** A boundary you fail to list here does not
merely go untested — it silently raises the score.

| Field | Type | min−1 | min | max | max+1 | Cases |
|---|---|---|---|---|---|---|

### Decision table — [rule name]
| Conditions | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| condition A | Y | Y | N | N |
| condition B | Y | N | Y | N |
| **outcome** | | | | |
| **case** | TC-…-001 | TC-…-002 | TC-…-003 | TC-…-004 |

**Infeasible rules removed:** [rule + why it cannot occur in reality — or "none"]

### State transitions — [entity]
| From \ To | StateA | StateB | Case |
|---|---|---|---|

### Exception coverage
Every applicable row of `.claude/refs/exception-catalog.md`. See that file for the
declined-vs-deferred distinction — they are not the same and must not be recorded alike.

| # | Scenario | Applicable | Covered by | Declined — reason |
|---|---|---|---|---|

## Test cases

One block per case. `build-csv.py` parses these — keep the field names and order exactly.

**These fields are copied into a CSV cell verbatim — write plain text, not markdown:**
- No backtick code-spans in `Preconditions`, `Test data`, a step's action line, or `Postcondition`.
  Backticks have no meaning to a reviewer reading the CSV in Excel, and `build-csv.py` does not
  strip them — they leak into the cell as literal `` ` `` characters. (`` `Basis ref:` `` and the
  per-step `` `Basis:` `` line, and a step's optional `` `[verification]` `` tag, ARE backtick-
  wrapped in the examples below — that backtick is part of the syntax the parser matches on, not
  a style choice; nowhere else.)
- An exact-body JSON assertion in `Expected [CPn]:` is **compact** (`{"code":"0000",...}`, no
  inserted spaces) — it is a byte-exact assertion, and pretty-printing invites a mismatch between
  what is written here and what automation actually compares.
- A citation like `(D24)` or `(BQ3/D26 — ...)` never lives inside `Expected [CPn]:` — that pollutes
  the checkable assertion with derivation commentary. Put it in `Notes` instead.

### TC-REQ001-US001-001 — [name]
- **AC:** AC-1
- **Level:** api · **Type:** positive · **Technique:** EP · **Priority:** P1
- **Basis ref:** `test_basis.md#post-v1-orders`
- **Preconditions:** [state the test assumes; seed data named, never created by the test]
- **Test data:** [concrete values]
- **Steps:**

  1. [action]

     **Expected [CP1]:** [concrete, checkable outcome]

     **Basis:** `test_basis.md#anchor-for-this-step`

  2. [action] `[verification]`

     **Expected [CP2]:** [...]

     **Basis:** `test_basis.md#anchor-for-this-step`

- **Postcondition:** [state afterwards, incl. cleanup]
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-001 · **Env scope:** local, sit, uat
- **Notes:** [free text — D-numbers, BQ references, or other decision citations touching this
  case; `-` if none. Maps straight to the CSV `Notes` column]

**Steps, checkpoints, and basis — the exact contract `build-csv.py` parses:**
- Every step is: a numbered action line, a **blank line**, an `**Expected [CPn]:**` line, a
  **blank line**, a `**Basis:**` line, then a **blank line** before the next numbered step. `CPn`
  numbers count up across the WHOLE case (not reset per step) — they are the checkpoint IDs a
  reviewer or a failing Robot test refers to ("CP2 failed"), and they land as a `[CPn] ` prefix on
  the generated CSV's `Expected_Result` cell.
- `**Basis:**` is **per step** — `Basis_Ref` is declared a `step`-level field in `csv-schema.md`,
  and a multi-step case routinely proves each step against a different part of `test_basis.md` (a
  POST and the inquiry that verifies it are two different endpoints, two different anchors). Give
  every step its own `**Basis:**` line; a step that genuinely shares its parent case's top-level
  `- **Basis ref:**` may omit the line and it is reused as that step's default — but do not rely on
  the default for a step that calls a different endpoint than the case's primary one.
- Append `` `[verification]` `` to a step's action line when that step exists only to confirm a
  side effect (e.g. an inquiry call checking a photo was not overwritten) rather than exercising
  the behaviour this case is designed to prove. This excludes the step from the `endpoint × status`
  coverage dimension (`coverage-model.md` §2) — it keeps the assertion (still a real, checked step)
  without inflating a denominator the step was never meant to count toward.

## Spec change log

Appended on every revision. **Every changed or removed case is classified**, and a `relaxes` entry is
valid only with a citation proving the OLD expectation was wrong.

### Revision N — YYYY-MM-DD — driver: [G4 human review pass N | triage D3 | basis change | impact]
- added TC-…-021 — [name + reason]
- changed TC-…-014 (strengthens|neutral|relaxes) — [what + why; if relaxes: the `test_basis.md` citation]
- removed TC-…-009 (relaxes) — [reason + citation]

> "The system behaves differently" is **never** a valid justification for `relaxes`. A test case binds
> to the specification, not the implementation. If the specification was wrong, fix `test_basis.md`
> at G0 and let the change flow down. See `.claude/refs/triage-protocol.md` §5.
```

---

## `tcm.md` template — written by `qa-analyst`, per story

**Coverage Matrix is generated, not hand-typed.** `make testcases` now emits it as the **right-hand
column block of `test_cases.csv`** (and of `test_cases_index.csv`) — the standalone `tcm_matrix.csv`
is retired. The generator reads the `design_notes.md` Derivation tables you already wrote
(Equivalence classes, Boundary analysis, Decision table(s), State transitions, Exception coverage)
plus `AC_Ref`, and inverts each table's "Cases" column into one column per dimension-value,
lowercase `x` on every step-row of a case whose derivation cites that value. Cases and their
X-mapping now share one row and one file — the layout of the team's reference sheet. See
`.claude/refs/csv-schema.md` for the exact column order and naming. **This is the same "derived, not
chosen" control from `.claude/refs/coverage-model.md` #1** — applied to the X-matrix itself: a
dimension-value that never appears in a Derivation table's "Cases" column cannot silently gain an
`x`, and the script warns on stderr about any dimension column with zero `x` (a real, visible
shortfall — record it in `## Spec non-compliance`, don't just delete the column).

The Derivation tables must cite cases in their "Cases"/"Case"/"Covered by" column for this to work:
- Equivalence classes / Boundary analysis: tag each case against the specific class/value it proves
  — `TC-001 (VC1), TC-003 (IC1)` — not just a bare list. An untagged Boundary "Cases" cell is only
  safe when it lists exactly one case per boundary column, left to right in column order.
- Decision table: the existing `**case**` row already maps one case per rule column — no change.
- State transitions: tag which arrow each case proves when a From-row has more than one valid
  To-state — `TC-018 (→Failed 104001)`.
- Exception coverage: the existing `Covered by` column already lists cases per catalog row.

```markdown
# US[ID] — Test Coverage Matrix

**Story:** US[ID] · **Requirement:** REQ[ID]
**TCM Status:** `draft` | `reconciled`
**Coverage Matrix:** the matrix block of `test_cases.csv` — columns `AC ·` … `EXC` right of `Basis_Ref`
(generated — `make testcases`, do not hand-edit)

## State & boundary analysis

Enumerate every input, variable, and state BEFORE counting. This is the source table for
`boundary_coverage`, AND the source `design_notes.md` → Boundary analysis cites cases against.

| Variable / input | Type | Valid | Invalid | Boundary | Null / empty |
|---|---|---|---|---|---|

## Count report

### Surfaces counted
| Metric | Count | Source (list each — a bare number is not auditable) |
|---|---|---|
| acceptance_criteria | | story_analysis.md |
| endpoints | | test_basis.md (confirmed rows only) |
| status_codes | | [list each endpoint's codes] |
| request_fields | | [list each] |
| validation_rules | | count of `test_cases.csv`'s matrix-block `RULE ·` columns (one per distinct `Rule` value in the Equivalence classes table — a rule proven by 5 classes is still 1 column) |
| error_codes | | [list each] |
| db_writes | | [list each] |
| db_constraints | | [list each — 0 for read-only stories] |
| boundaries | | count of VALUES in `test_cases.csv`'s matrix-block `BVA ·` columns — every boundary row's min−1/min/max/max+1 cell, not just the field count |
| decision_rules | | count of `test_cases.csv`'s matrix-block `DT (...) ·` columns |
| transitions | | count of `test_cases.csv`'s matrix-block `ST ·` columns — includes BOTH `(valid)` and `(invalid — must be rejected)` |
| exceptions | | count of `test_cases.csv`'s matrix-block `EXC ...` columns |
| screens | | [context only — NOT a term in min_UI] |
| ui_states | | [per screen, then summed — never max, never average] |
| ui_interactions | | [list each] |
| journeys | | [list each] |
| journey_failures | | [list each] |

### Minimums vs actual

Formulas copied verbatim from `.claude/refs/test-design-techniques.md` §3. Every term is a sum;
there is no multiplication. Write the zeros — a dropped term is invisible, a `0` is auditable.

| Category | Formula | Minimum | Actual | Delta | Status |
|---|---|---|---|---|---|
| api | status_codes + validation_rules + error_codes + boundaries + decision_rules | | | | |
| db | db_constraints + db_writes | | | | |
| ui | ui_states + ui_interactions + journey_failures_visible | | | | |
| e2e | journeys + journey_failures | | | | |
| exception | exceptions | | | | |
| **TOTAL** | | | | | |

> `ui_states` is already summed across all screens — **never compute `screens × states`**. On a
> two-screen story with four states each, the wrong formula and the right one both give 8, which is
> exactly why this survives review unless you check the terms rather than the total.

## Coverage ratios

Per `.claude/refs/coverage-model.md`. Denominators ratified at G2 on [date]. For every dimension
except `automation`, Covered/Total = the count of `test_cases.csv` matrix-block columns of that
dimension's prefix group that have ≥1 `x` / the count of columns in that group — **count them from
the file, do not retype a number you didn't just count.**

| Dimension | Covered | Total | Ratio | Threshold | Status | matrix group |
|---|---|---|---|---|---|---|
| AC | | | | 1.00 | | `AC ·` |
| endpoint × status | | | | 0.90 | | `END ·` |
| validation rule | | | | 0.90 | | `RULE ·` |
| boundary | | | | 0.90 | | `BVA ·` |
| decision rule | | | | 0.90 | | `DT (...) ·` |
| state transition | | | | 0.90 | | `ST ·` |
| exception | | | | 0.90 | | `EXC ...` |
| automation | | | | | | _(from `test_cases.csv` `Automatable`/`Automation_ID`, not the matrix)_ |

**Excluded from denominators** (basis `Confidence` != `confirmed`): [list, or "none"]

## Level justification

Why each `ui` and `e2e` case needs that level rather than a cheaper one.

| Test ID | Level | Why a lower level cannot prove it |
|---|---|---|

## Spec non-compliance

Every scenario counted above but **not** covered at the level its technique implies — pushed down,
deferred, or declined. Often the right call, but it must be visible: pushing a case down is the one
move that lowers a minimum without lowering risk.

Write "none" if there are none. An empty table on a story that clearly pushed cases down is itself a
finding at G4.

| Scenario | Counted as | Pushed to / deferred | Why it does not need the higher level | Covering test ID |
|---|---|---|---|---|

## Reconciliation log

(`script-reviewer` appends here once automation exists and the mapping test-case ↔ script is verified.)
```
