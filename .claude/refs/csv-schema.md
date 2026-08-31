# Shared ref — test_cases.csv schema

The primary human-facing deliverable. Consumed by `scripts/tc/build-csv.py` (writes it),
`scripts/gate/validate-artifacts.py` and `scripts/gate/expected-drift.py` (check it), and the G4
human gate (approves it).

**Destination: Excel, read by people.** Not a tracker import. That frees the schema from any tool's
column requirements, so it is optimised for a reviewer reading it — which is the only audience.

---

## The generation rule

> `design_notes.md` is written by a human-reviewable agent and reviewed by a human.
> `test_cases.csv` is **generated from it** and never edited by hand.

Both files exist because they serve different readers: the markdown carries the *derivation* (which
technique produced this case, what the boundary table looked like), the CSV carries the *cases* in a
form you can filter and sort. If both were hand-written they would disagree within two requirements —
that is not a prediction, it is what always happens to duplicated state.

`make testcases-check` regenerates to a temp file and diffs. A difference means someone edited the
CSV directly, and it fails the gate.

---

## Row granularity

**One row per step.** Case-level fields repeat on every row of that case. This is slightly redundant
and entirely deliberate: it makes the file trivially filterable and pivotable in Excel, which is what
the audience will actually do with it. A single row carrying `1. do this\n2. do that` in one cell
looks tidier and is much worse to work with.

Rows for one case are contiguous and ordered by `Step_No`.

---

## Format

- **Encoding:** UTF-8 **with BOM** (`utf-8-sig`). Without the BOM, Excel on Windows renders Thai as
  mojibake — the single most common way this deliverable arrives broken.
- **Delimiter:** `,` — RFC 4180 quoting. Fields containing `,`, `"`, or a newline are quoted;
  embedded `"` is doubled.
- **Line ending:** `\r\n`.
- **Header:** exactly one row, exactly the columns below, in this order.

---

## Columns

| # | Column | Level | Required | Content |
|---|---|---|---|---|
| 1 | `Test_Case_ID` | case | yes | `TC-REQ{nnn}-US{nnn}-{nnn}` — globally unique, never reused |
| 2 | `REQ_ID` | case | yes | `REQ001` |
| 3 | `US_ID` | case | yes | `US001` |
| 4 | `AC_Ref` | case | yes | the acceptance criterion this proves — `AC-3`. Semicolon-separated if several |
| 5 | `Test_Level` | case | yes | `api` \| `ui` \| `db` \| `integration` \| `e2e` |
| 6 | `Test_Type` | case | yes | `positive` \| `negative` \| `boundary` \| `exception` \| `security` \| `regression` |
| 7 | `Design_Technique` | case | yes | `EP` \| `BVA` \| `DT` \| `ST` \| `Pairwise` \| `EG` \| `UseCase` \| `CRUD` |
| 8 | `Priority` | case | yes | `P1` \| `P2` \| `P3` — inherited from the AC's risk rating |
| 9 | `Test_Description` | case | yes | one sentence, what this proves. Not "test the endpoint" |
| 10 | `Preconditions` | case | yes | state the test assumes. Seed data is named, never created by the test |
| 11 | `Test_Data` | case | yes | the concrete input values. `-` if none |
| 12 | `Step_No` | step | yes | `1`, `2`, … |
| 13 | `Test_Step` | step | yes | one concrete action. Imperative, specific enough to execute by hand |
| 14 | `Expected_Result` | step | yes | **concrete and checkable.** See below |
| 15 | `Postcondition` | case | yes | state after the case, incl. cleanup. `-` if none |
| 16 | `Automatable` | case | yes | `Y` \| `N` |
| 17 | `Automation_ID` | case | if `Y` | `E2E-REQ{nnn}-US{nnn}-{nnn}` — must exist as a `[Tags]` entry |
| 18 | `Env_Scope` | case | yes | `local;sit;uat` — semicolon-separated. See `docs/env_matrix.md` |
| 19 | `Basis_Ref` | step | yes | **`test_basis.md#anchor` or `US001#AC-3`.** See below |
| 20 | `Status` | case | yes | `Not Run` \| `Pass` \| `Fail` \| `Blocked` \| `Skipped` |
| 21 | `Defect_ID` | case | no | tracker ID once a D1 is raised |
| 22 | `Notes` | case | no | free text |

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

```csv
Test_Case_ID,REQ_ID,US_ID,AC_Ref,Test_Level,Test_Type,Design_Technique,Priority,Test_Description,Preconditions,Test_Data,Step_No,Test_Step,Expected_Result,Postcondition,Automatable,Automation_ID,Env_Scope,Basis_Ref,Status,Defect_ID,Notes
TC-REQ001-US001-014,REQ001,US001,AC-3,api,boundary,BVA,P1,"ปฏิเสธการสร้าง order เมื่อ qty = 0 (ขอบล่าง − 1)","customer CUST-001 มีอยู่ในระบบจาก make e2e-seed","qty=0; skuId=SKU-A",1,"POST /v1/orders body {""customerId"":""CUST-001"",""items"":[{""skuId"":""SKU-A"",""qty"":0}]}","HTTP 400; body.code == ""VALIDATION_ERROR""; body.fields.qty == ""must be >= 1""","ไม่มีแถวใหม่ในตาราง orders",Y,E2E-REQ001-US001-004,local;sit;uat,test_basis.md#post-v1-orders,Not Run,,
TC-REQ001-US001-015,REQ001,US001,AC-3,api,boundary,BVA,P1,"ยอมรับ order เมื่อ qty = 1 (ขอบล่าง)","customer CUST-001 มีอยู่ในระบบจาก make e2e-seed","qty=1; skuId=SKU-A",1,"POST /v1/orders body {""customerId"":""CUST-001"",""items"":[{""skuId"":""SKU-A"",""qty"":1}]}","HTTP 201; body.status == ""created""; body.items[0].qty == 1","order ถูกสร้าง — ลบใน teardown",Y,E2E-REQ001-US001-005,local;sit;uat,test_basis.md#post-v1-orders,Not Run,,
```

---

## Index file

`build-csv.py` also emits `test_cases_index.csv` — **one row per case**, dropping `Step_No`,
`Test_Step`, and `Expected_Result`. It is for counting and reporting, not for execution. Regenerated
from the same source, so the two can never disagree.
