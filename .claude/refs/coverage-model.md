# Shared ref — the coverage model

How ">90% coverage" is defined, computed, and kept honest in a project that does **not** own the
system under test and therefore has no code coverage to measure.

Consumed by `qa-analyst` (computes it), `test-planner` (proposes the denominators), the G2 human
gate (ratifies them), `scripts/gate/coverage-report.py` (enforces it), and `test-manager` (signs off).

---

## 1. Why this file exists

Line coverage answers "did a test execute this code?" We cannot ask that question — the code is
someone else's. So coverage here is **specification coverage**: did a test exercise this *stated
behaviour*?

That substitution introduces one serious problem, and this file is mostly about containing it:

> **A specification-coverage percentage is only as honest as its denominator, and the denominator is
> produced by the same agent that is graded on it.**

Forgetting two boundary values raises the score. Declaring a decision rule infeasible raises the
score. Marking a basis row `assumed` and quietly excluding it raises the score. None of these look
like cheating from the inside; all of them produce a number that means nothing.

Three controls contain it. All three are mandatory:

1. **The denominator is derived, not chosen.** Every dimension below counts rows in a named table in
   `test_basis.md` or `tcm.md` — a reviewer can recount it from the source in minutes.
2. **The denominator is ratified by a human at G2, before any case is written.** Lock the
   denominator, *then* count the numerator. An agent that discovers the denominator after learning
   its score is being graded is in a different situation entirely.
3. **Every exclusion is recorded in `## Spec non-compliance`** with the reason and the covering case.
   An empty non-compliance table on a story that clearly pushed cases down a level is itself a finding.

---

## 2. The dimensions

| # | Dimension | Numerator | Denominator (the named source table) | Threshold |
|---|---|---|---|---|
| 1 | **AC coverage** | `AC ·` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `AC ·` columns in `test_cases.csv`'s matrix block | **1.00** |
| 2 | **Endpoint × status** | `END ·` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `END ·` columns in `test_cases.csv`'s matrix block | 0.90 |
| 3 | **Validation rule** | `RULE ·` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `RULE ·` columns in `test_cases.csv`'s matrix block | 0.90 |
| 4 | **Boundary** | `BVA ·` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `BVA ·` columns in `test_cases.csv`'s matrix block | 0.90 |
| 5 | **Decision rule** | `DT (...) ·` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `DT (...) ·` columns in `test_cases.csv`'s matrix block | 0.90 |
| 6 | **State transition** | `ST ·` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `ST ·` columns in `test_cases.csv`'s matrix block — **both** `(valid)` and `(invalid — must be rejected)` | 0.90 |
| 7 | **Exception** | `EXC ...` columns in `test_cases.csv`'s matrix block with ≥1 `x` | `EXC ...` columns in `test_cases.csv`'s matrix block | 0.90 |
| 8 | **Automation** | cases with `Automatable=Y` that have a passing `Automation_ID` | cases with `Automatable=Y` | per `test_stack.md` |

**AC coverage is 1.00, not 0.90.** An uncovered acceptance criterion is not a rounding error — it is
a requirement nobody tested. The 90% bands exist for derived dimensions where the denominator is
large and the tail is genuinely low-value; acceptance criteria have no such tail.

All 8 dimensions are counted from the **matrix block of `test_cases.csv`** — the wide X-mapping
Coverage Matrix columns right of `Basis_Ref` (the case block's last column), which `make testcases` generates from `design_notes.md`'s
own Derivation tables (never hand-typed — see `csv-schema.md` and `qa-templates.md`'s `tcm.md`
template for exactly what each column means and how its `x` marks are derived), except dimension 8
(`automation`), which comes straight from `test_cases.csv`'s own `Automatable`/`Automation_ID`
columns in the same row — it needs no X-mapping, it is already a per-case boolean. The old
standalone `tcm_matrix.csv` is retired; cases and their X-mapping now share one file and one row.
This does not weaken control #1 above; it moves the same rule one layer down — the matrix itself is
derived from a named source (the Derivation tables' "Cases" columns), so a reviewer can recount
either the ratio from the matrix, or the matrix from the derivation, in minutes.

Dimension 3 (`validation rule`)'s `RULE ·` columns come from the Equivalence classes table's `Rule`
column — a rule (e.g. `VAL-evidence-001`) is usually proven by several equivalence classes at once
(a base64-decode-and-magic-bytes rule is exercised by every "wrong format" class), so the generator
(`make testcases`) accumulates every class's cases under its rule and emits one `RULE ·` column
per distinct rule rather than one per class. A class with no named rule behind it (a bare
type/shape check `test_basis.md` never named) leaves `Rule` as `—` and is correctly excluded — it
was never a member of this dimension's denominator.

Dimension 2 (`endpoint × status`)'s `END ·` columns exclude two things a naive "every HTTP call in
the suite" scrape would over-count: a step tagged `[verification]` (confirms a side effect, isn't
exercising the endpoint the case is designed to prove) and any case whose `Test_Type` is
`exception` (already counted under dimension 7 — the same auth-failure or replay assertion should
not inflate two denominators at once). Getting this dimension's scope right is the one place in the
matrix that still needs a human call at authoring time (which steps are "just verification", which
endpoint is "the" one under test) — the tags exist so that call is recorded once, in
`design_notes.md`, instead of re-litigated by whoever reads the coverage report.

---

## 3. The gate

```
PASS  ⇔  ac_coverage == 1.00
    AND  min(dimensions 2–7) >= 0.90
    AND  automation_coverage >= automation_coverage_min
    AND  every shortfall row appears in ## Spec non-compliance
```

`make coverage` computes this and exits non-zero on failure. It is part of `gate_cmd_artifacts` and
runs before the G4 human gate — a human never reviews a story whose own arithmetic does not close.

---

## 4. Unconfirmed basis rows are excluded from the denominator

A row in `test_basis.md` whose `Confidence` is `inferred` or `assumed` is **excluded from every
denominator** and its cases are excluded from every numerator.

This looks generous and is the opposite. It means:

- You cannot raise your score by writing cases against guessed behaviour.
- An unconfirmed basis shows up as a **coverage shortfall**, not as false confidence — the report
  says "72% because 14 endpoint/status pairs are still unconfirmed", which is an accurate statement
  about what you know, and it points at exactly the conversation that needs to happen with the SUT
  team.

The alternative — counting guessed rows — produces a green dashboard on top of a pile of D3 defects
waiting to be discovered during execution. Given that this project's basis starts as human
documentation rather than a machine-readable spec, this is the most likely failure mode of the
entire pipeline, and this rule is the main defence against it.

---

## 5. Declining an exception category

`exception-catalog.md` rows may be declined, but never silently. A decline needs:

- the category and the specific scenario,
- **why it does not apply** to this story (not "low priority" — that is a deferral, which belongs in
  `docs/test_debt.md` with a reviewer's approval, and still counts against coverage),
- a `Basis_Ref` supporting the claim where one exists.

A declined row leaves the denominator. A deferred row stays in it and drags the score down, which is
the honest representation of "we know about this and have not done it".

---

## 6. Reading the report

`make coverage` writes `docs/test_cases/REQ*/US*/coverage.md`:

```
US001 — coverage report                                    commit 3f2a1b9

  dimension              covered / total      ratio    threshold   status
  ────────────────────────────────────────────────────────────────────────
  AC                          12 / 12          1.00       1.00      PASS
  endpoint × status           31 / 33          0.94       0.90      PASS
  validation rule             28 / 30          0.93       0.90      PASS
  boundary                    44 / 52          0.85       0.90      FAIL
  decision rule                9 / 9           1.00       0.90      PASS
  state transition            17 / 19          0.89       0.90      FAIL
  exception                   22 / 24          0.92       0.90      PASS
  automation                  61 / 78          0.78       0.70      PASS

  EXCLUDED (basis Confidence != confirmed):  6 endpoint/status pairs, 3 validation rules
  UNRECORDED SHORTFALL: 8 boundary values, 2 transitions missing from ## Spec non-compliance

  QA GATE: FAIL — 2 dimensions below threshold, 10 shortfalls unrecorded
```

The `UNRECORDED SHORTFALL` line is the one that matters most in review. A shortfall that appears in
`## Spec non-compliance` with a reason is a decision. A shortfall that appears nowhere is an
omission, and the two must never look alike in a report.

---

## 7. What this model deliberately does not claim

Worth stating plainly, because a 90%+ dashboard invites over-reading:

- It does **not** measure how much of the SUT's code was executed. Untested code paths that no
  documented behaviour describes are invisible here — by construction.
- It does **not** measure assertion strength. A case that asserts only a status code counts the same
  as one that asserts the full body. **Assertion strength is a human judgement, checked at G4** —
  this is precisely why G4 is a hard stop and not an automated check.
- It does **not** measure whether the basis itself is right. That is what G0 is for.

Three separate controls, three separate failure modes. Do not let a green coverage number stand in
for any of the other two.
