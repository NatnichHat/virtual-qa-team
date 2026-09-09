# Shared ref — test_cases.csv schema

The primary human-facing deliverable. Consumed by `scripts/tc/build-csv.py` (writes it),
`scripts/gate/validate-artifacts.py` and `scripts/gate/expected-drift.py` (check it), and the G4
human gate (approves it).

**Destination: Excel, read by people.** Not a tracker import. That frees the schema from any tool's
column requirements, so it is optimised for a reviewer reading it — which is the only audience.

**One file, two blocks.** `test_cases.csv` carries the test cases (left block, columns 1–22) *and*
the coverage X-matrix (right block, `AC ·` … `EXC` columns) side by side on the same row — the
layout of the team's reference sheet (`docs/references/example of relation for test case and metrix.csv`): a
reviewer reads a case and sees, without switching files, exactly which dimension-values it proves.
The standalone `tcm_matrix.csv` is **retired**; `make testcases` generates both blocks in one pass.

---

## The generation rule

> `design_notes.md` is written by a human-reviewable agent and reviewed by a human.
> `test_cases.csv` — **both blocks** — is generated from it and never edited by hand.

Both files exist because they serve different readers: the markdown carries the *derivation* (which
technique produced this case, what the boundary table looked like), the CSV carries the *cases* in a
form you can filter and sort. If both were hand-written they would disagree within two requirements —
that is not a prediction, it is what always happens to duplicated state.

The matrix block obeys the same "derived, not chosen" control (`coverage-model.md` #1): every `x`
comes from inverting the Derivation tables' "Cases" columns in `design_notes.md` — a dimension-value
that never appears there cannot silently gain an `x`, and neither can a case that was never linked
to it. See the `tcm.md` template in `qa-templates.md` for how the Derivation tables must cite cases.

`make testcases-check` regenerates to a temp file and diffs. A difference means someone edited the
CSV directly, and it fails the gate.

---

## The presentation view — `test_cases.xlsx`

The CSV cannot merge cells or carry colour, and the team's reference sheet does both. Rather than
bend the CSV schema to Excel cosmetics, the pipeline splits the two jobs:

```
design_notes.md ──(make testcases)──▶ test_cases.csv          ← WORKING artifact: gates, scripts,
                                      test_cases_index.csv       and agents read these (tracked,
                                          │                      diffable, token-cheap)
                                          └──(make xlsx-view)──▶ test_cases.xlsx   ← PRESENTATION
                                                                  view: humans open this in Excel
```

Rules, all of them load-bearing:

- **The xlsx is rendered FROM the CSVs, downstream, never upstream.** `scripts/tc/build-xlsx.py`
  only reads `test_cases.csv` + `test_cases_index.csv`; it never reads `design_notes.md` and never
  writes a CSV. Anything that can disagree with the CSVs is not a view of them.
- **No gate, script, or agent ever reads the xlsx.** Validators keep reading the CSVs. An agent
  that reads the xlsx instead pays binary-zip token cost for information the CSV already carries —
  and could not cite line numbers in it if it tried.
- **The xlsx is gitignored** (`*.xlsx`). An xlsx is a ZIP whose bytes embed timestamps: committing
  it would make byte-diff drift guards fire on identical content and produce diffs nobody can
  review. The CSVs are the tracked truth; the xlsx is a photograph of them, regenerated on demand.
- **Never hand-edit the xlsx.** The edit would be silently destroyed by the next `make xlsx-view`,
  and worse, would look like it survived. Edit `design_notes.md`, regenerate both.

Sheets: **Test Cases** (one row per step; case-level columns and the matrix block merged across
each case's step rows; freeze panes keep the header and `Test_Case_ID` visible), **Case Index**
(one row per case from `test_cases_index.csv` — flat, auto-filterable, un-merged in the body,
because merged cells and sorting are mutually exclusive in Excel and both views are needed),
**Legend** (what every colour means). An unknown value is left uncoloured and warned on stderr — a
new status must show up as unstyled, never silently wear a colour that already means something else.

**Style is configuration, not code.** Every cosmetic decision — which columns merge, the header
shape, freeze pane, colour palettes, row heights, column widths — lives in
`scripts/tc/xlsx_style.toml`, read by `build-xlsx.py` at render time. Tweaking the look never
touches Python and never touches the CSVs. The one TOML trap is encoded in the file itself: the
top-level `color_scope` key must sit ABOVE every `[table]` header, or TOML silently absorbs it
into that table (this already happened once; `load_config` now fails loud if the key is missing).

Header shape: a **2-tier grouped banner** when `matrix_banner = true` — row 1 carries one merged
banner per matrix group (`AC`, `END`, `EP`, `RULE`, `BVA`, `DT (…)`, `ST`, `EXC <n>`), row 2 the
value names under it; non-matrix column names are merged vertically across both rows. This
restores, visually, exactly the hierarchy the CSV must flatten into `GROUP · value` names — and it
is why the Case Index sheet keeps the FULL CSV column names in its header (a flat sheet has no
banner to supply the group, and its filter dropdowns must read like the CSV).

**Colour scope** (`color_scope`) governs how much of the Test Cases sheet wears colour, and is the
one style decision made by looking rather than reading: `make xlsx-preview` renders
`xlsx_style_preview.xlsx` — the same contiguous slice of real cases, once per scope
(`cell_tint` / `row_tint` / `banding`), one sheet each — so the team picks in Excel and then sets
the key. Preview case selection is automatic and contiguous (the narrowest window covering every
`Test_Type`, `Priority`, `Status`, plus a multi-step case to show merging); if no window within
`max_cases` covers everything, the best-coverage window renders and stderr names the values left
out. Colour semantics in all scopes: `Test_Type`, `Priority`, `Status`, and shaded `x` marks.

Dependencies live in `scripts/requirements.txt` (openpyxl), installed by `make xlsx-deps` — a
one-time host step, deliberately not auto-invoked, same precedent as `make e2e-deps`.

---

## Row granularity

**One row per step.** Case-level fields repeat on every row of that case. This is slightly redundant
and entirely deliberate: it makes the file trivially filterable and pivotable in Excel, which is what
the audience will actually do with it. A single row carrying `1. do this\n2. do that` in one cell
looks tidier and is much worse to work with.

Rows for one case are contiguous and ordered by `Step_No`.

The matrix columns are **case-level**: the same `x` pattern repeats on every step-row of the case
that proves that dimension-value (the reference sheet is one row per case because it has no
step-granularity; we keep step rows and repeat, exactly like every other case-level column).
Coverage counts *columns with ≥1 `x`*, so the repetition never inflates a ratio.

---

## Format

- **Encoding:** UTF-8 **with BOM** (`utf-8-sig`). Without the BOM, Excel on Windows renders Thai as
  mojibake — the single most common way this deliverable arrives broken.
- **Delimiter:** `,` — RFC 4180 quoting. Fields containing `,`, `"`, or a newline are quoted;
  embedded `"` is doubled.
- **Line ending:** `\r\n`.
- **Header:** exactly **one** row, exactly the columns below, in this order — case block first, then
  matrix block. The reference sheet stacks its matrix header over several merged rows (Input Data →
  Field / Validate Input Data / Validation Logic → x-channel → …); a CSV consumed by scripts cannot.
  The group prefix in each column name (`AC ·`, `END ·`, `EP ·`, `RULE ·`, `BVA ·`, `DT (…) ·`,
  `ST ·`, `EXC n ·`) **is** that hierarchy, flattened — Excel users can group/filter by prefix and
  see the same blocks the reference sheet shows visually.
- **Matrix cell values:** lowercase `x` or empty. Never `X`, `✓`, `1`, or free text.

---

## Columns — left block: the cases

Column order follows the reference sheet: the columns that have a counterpart there come first, in
its row-1 order (`No TC.` → `Data Prep` → `Test Description` → `Test Step` → `Test Expected` →
`Test Result` → `Automate` → `Positive/Negative` → `Defect Link` → `Remark`); columns it has no
counterpart for are appended after them (14–22). Either way the case block is columns 1–22 and the
matrix block starts at column 23.

| # | Column | Level | Required | Ref-sheet counterpart | Content |
|---|---|---|---|---|---|
| 1 | `Test_Case_ID` | case | yes | `No TC.` | `TC-REQ{nnn}-US{nnn}-{nnn}` — globally unique, never reused |
| 2 | `Preconditions` | case | yes | `Data Prep` | state the test assumes. Seed data is named, never created by the test |
| 3 | `Test_Data` | case | yes | `Data Prep` | the concrete input values. `-` if none |
| 4 | `Test_Description` | case | yes | `Test Description` | one sentence, what this proves. Not "test the endpoint" |
| 5 | `Step_No` | step | yes | `Test Step` | `1`, `2`, … |
| 6 | `Test_Step` | step | yes | `Test Step` | one concrete action. Imperative, specific enough to execute by hand |
| 7 | `Expected_Result` | step | yes | `Test Expected` | **concrete and checkable.** See below |
| 8 | `Status` | case | yes | `Test Result` / `Tester` | `Not Run` \| `Pass` \| `Fail` \| `Blocked` \| `Skipped` (execution is written by the run, not by design) |
| 9 | `Automatable` | case | yes | `Automate` | `Y` \| `N` |
| 10 | `Automation_ID` | case | if `Y` | `Manual/Automate` | `E2E-REQ{nnn}-US{nnn}-{nnn}` — must exist as a `[Tags]` entry |
| 11 | `Test_Type` | case | yes | `Positive/Negative` | `positive` \| `negative` \| `boundary` \| `exception` \| `security` \| `regression` |
| 12 | `Defect_ID` | case | no | `Defect Link` | tracker ID once a D1 is raised |
| 13 | `Notes` | case | no | `Remark` | free text |
| 14 | `REQ_ID` | case | yes | — | `REQ001` |
| 15 | `US_ID` | case | yes | — | `US001` |
| 16 | `AC_Ref` | case | yes | — | the acceptance criterion this proves — `AC-3`. Semicolon-separated if several |
| 17 | `Test_Level` | case | yes | — | `api` \| `ui` \| `db` \| `integration` \| `e2e` |
| 18 | `Design_Technique` | case | yes | — | `EP` \| `BVA` \| `DT` \| `ST` \| `Pairwise` \| `EG` \| `UseCase` \| `CRUD` |
| 19 | `Priority` | case | yes | — | `P1` \| `P2` \| `P3` — inherited from the AC's risk rating |
| 20 | `Postcondition` | case | yes | — | state after the case, incl. cleanup. `-` if none |
| 21 | `Env_Scope` | case | yes | — | `local;sit;uat` — semicolon-separated. See `docs/env_matrix.md` |
| 22 | `Basis_Ref` | step | yes | — | **`test_basis.md#anchor` or `US001#AC-3`.** See below |

The reference sheet's `Error Handling` column has no case-block counterpart on purpose — it maps to
the `EXC n ·` matrix columns in the right block. Its second `Tester` and second `Remark` columns are
manual-entry duplicates; both fold into `Status` and `Notes`.

---

## Columns — right block: the coverage X-matrix

Dimension columns, appended after column 22, in this fixed group order. Each column is one
dimension-value; its name is the value itself, group-prefixed. Generated from `design_notes.md`'s
Derivation tables + `AC_Ref` + the step/expected-result pairs — see `coverage-model.md` §2 for what
each dimension counts and which derivations feed it.

| Group prefix | One column per… | Derived from |
|---|---|---|
| `AC · <ac-id>` | acceptance criterion | `AC_Ref` |
| `END · <METHOD> <path> -> HTTP <code>` | endpoint × status pair | steps (excluding `[verification]` steps and `exception`-type cases) |
| `EP · <field> = <class>` | equivalence class | Equivalence classes table |
| `RULE · <rule-id>` | named validation rule | Equivalence classes `Rule` column + `VAL-*` citations in `Basis_Ref`/`Notes` |
| `BVA · <field> <min−1\|min\|max\|max+1> = <value>` | boundary value | Boundary analysis table |
| `DT (<table>) · <rule>` | decision-table rule | Decision table `**case**` row |
| `ST · <from> -> <to> (valid \| invalid — must be rejected)` | state transition | State transitions table |
| `EXC <n> · <scenario>` | applicable exception-catalog row | Exception coverage table |

Rules:

- A matrix column with **zero `x`** is a real, visible shortfall — the generator warns on stderr,
  and the shortfall must be recorded in `tcm.md`'s `## Spec non-compliance`. Never delete the column
  to make the warning go away.
- The matrix block's column set is **per story** — it is exactly that story's derivations, so two
  stories' CSVs will have different matrix widths. That is correct; the G2-frozen denominators are
  per story too.
- `EP ·` columns are derivation detail, not one of the 8 coverage dimensions on their own
  (`coverage-model.md` §2) — they stay in the block because a reviewer filtering the sheet wants to
  see class-level coverage the same way the reference sheet shows its "Validate Input Data" columns.

---

## The two columns that do the real work

### `Expected_Result` — concrete, not descriptive

A test case is only as good as this cell. Vague expected results are the mechanism by which a suite
appears to pass while proving nothing.

| Bad | Why | Good |
|---|---|---|
| "should fail" | proves nothing — a 500 passes this | `HTTP 400, body.code == "VALIDATION_ERROR", body.fields.qty == "must be >= 1"` |
| "error is displayed" | which error, where? | `inline message under [data-testid=qty-input] reads "จำนวนต้องมากกว่า 0"` |
| "order is created" | with what values? | `HTTP 201, body.status == "created"; row in orders with status='created', customer_id='CUST-001'` |
| "responds correctly" | correctly by whose definition? | cite the basis and name the fields |

`validate-artifacts.py` rejects an `Expected_Result` shorter than 15 characters or matching known
vague phrasings. That check catches the laziest cases; **G4 catches the rest, because assertion
strength is a judgement no script can make.**

### `Basis_Ref` — the independent oracle

Every expected result must trace to something outside the agent that wrote it: a row in
`test_basis.md`, or an acceptance criterion in the story.

This is not decorative traceability. It is the mechanism that makes **D3 (wrong expected result)
mechanically detectable** — see `triage-protocol.md`:

- **At authoring time:** a case with no `Basis_Ref` fails the validator. You cannot ship an expected
  result you cannot source.
- **At triage time:** when a test fails, the first question is "does the SUT's actual behaviour match
  the cited basis?" If yes, the expected result is wrong (D3). If no, it is a real defect (D1). Without
  the citation that question has no answer and every failure becomes an argument.
- **At impact time:** when a basis anchor changes, `impact-analyst` greps this column to find every
  affected case in seconds.

A `Basis_Ref` pointing at a row whose `Confidence` is not `confirmed` is a validator **warning**, and
the case is excluded from the coverage denominator (`coverage-model.md` §4).

---

## Example

(Matrix columns abbreviated to four for width; a real file carries every dimension-value of the
story, in the fixed group order.)

```csv
Test_Case_ID,Preconditions,Test_Data,Test_Description,Step_No,Test_Step,Expected_Result,Status,Automatable,Automation_ID,Test_Type,Defect_ID,Notes,REQ_ID,US_ID,AC_Ref,Test_Level,Design_Technique,Priority,Postcondition,Env_Scope,Basis_Ref,AC · AC-3,END · POST /v1/orders -> HTTP 400,BVA · qty min−1 = 0,RULE · VAL-order-qty
TC-REQ001-US001-014,"customer CUST-001 มีอยู่ในระบบจาก make e2e-seed","qty=0; skuId=SKU-A","ปฏิเสธการสร้าง order เมื่อ qty = 0 (ขอบล่าง − 1)",1,"POST /v1/orders body {""customerId"":""CUST-001"",""items"":[{""skuId"":""SKU-A"",""qty"":0}]}","HTTP 400; body.code == ""VALIDATION_ERROR""; body.fields.qty == ""must be >= 1""",Not Run,Y,E2E-REQ001-US001-004,boundary,,,REQ001,US001,AC-3,api,BVA,P1,"ไม่มีแถวใหม่ในตาราง orders",local;sit;uat,test_basis.md#post-v1-orders,x,x,x,
TC-REQ001-US001-015,"customer CUST-001 มีอยู่ในระบบจาก make e2e-seed","qty=1; skuId=SKU-A","ยอมรับ order เมื่อ qty = 1 (ขอบล่าง)",1,"POST /v1/orders body {""customerId"":""CUST-001"",""items"":[{""skuId"":""SKU-A"",""qty"":1}]}","HTTP 201; body.status == ""created""; body.items[0].qty == 1",Not Run,Y,E2E-REQ001-US001-005,boundary,,,REQ001,US001,AC-3,api,BVA,P1,"order ถูกสร้าง — ลบใน teardown",local;sit;uat,test_basis.md#post-v1-orders,x,,,
```

---

## Index file

`build-csv.py` also emits `test_cases_index.csv` — **one row per case**, dropping `Step_No`,
`Test_Step`, and `Expected_Result`. This is the view closest to the reference sheet: one row per
case, case columns, then the full matrix block. It is for counting and reporting, not for
execution. Regenerated from the same source, so the two can never disagree.
