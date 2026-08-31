# Test Basis — living contract of the system under test

> **This is the oracle.** Every `Expected_Result` in every test case cites a row in this file via
> `Basis_Ref`. An expected result with no citation has no oracle, and is classified **D3** by default
> when its test fails (see `.claude/refs/triage-protocol.md`).
>
> **We do not own the SUT.** This document is *reconstructed* by `test-basis-analyst` from human
> documentation, screens, and observed behaviour — then **confirmed by the SUT team at gate G0**.
> That confirmation is the whole point: an unconfirmed basis means every test case built on it is a
> guess wearing a citation.

**Owner:** `test-basis-analyst` (authors) · SUT team (confirms) · `/approve-basis` (records approval)

## Confidence levels — read this before using any row

| Level | Meaning | May a test case cite it? |
|---|---|---|
| `confirmed` | The SUT team explicitly verified this row at G0 | **yes** |
| `inferred` | Derived from documentation or observed responses, not yet verified | only with a `## Open questions` entry naming it |
| `assumed` | We guessed to keep moving | **no** — blocks G0 |

Rows that are not `confirmed` are **excluded from the coverage denominator** (see
`.claude/refs/coverage-model.md`). This is deliberate: it makes an unconfirmed basis show up as a
coverage shortfall rather than as false confidence.

## Approval

**Confirmed-by:** —
**Confirmed-at:** —
**Confirmed rows:** — / —
**Status:** `draft` | `pending_confirmation` | `confirmed` | `changes_requested`

---

## Endpoints

For each endpoint: method, path, auth, request schema, response schema **per status code**, and the
error envelope. Every field typed. This is the level of precision a test case needs — anything
vaguer and the expected result becomes an opinion.

### `<METHOD> /<path>`  <a id="method-path"></a>
| | |
|---|---|
| **Confidence** | `assumed` |
| **Source** | [Confluence page / screen / observed response / SUT team conversation] |
| **Auth** | [Bearer JWT / API key / none] |
| **Idempotent** | [yes / no / conditional] |

**Request**
```json
{ "field": "type, constraints (required, length, range, enum, format)" }
```

**Responses**
- **200 OK**
  ```json
  { "field": "type" }
  ```
- **400 Bad Request**
  ```json
  { "code": "VALIDATION_ERROR", "message": "string", "fields": { "field": "reason" } }
  ```
- **401 / 403 / 404 / 409 / 500** — [one block per status the endpoint can actually return]

**Side effects** — [rows written/updated/deleted, events published, files created. This is what a
`level:db` test asserts on.]

---

## Error envelope

The shape every error response shares. If the SUT is inconsistent here, **say so** — an inconsistent
error envelope is itself a finding worth raising with the SUT team, and it changes how many
exception cases you need.

```json
{ "code": "string (enum)", "message": "string", "fields": { "<field>": "string" } }
```

| Code | HTTP status | When | Confidence |
|---|---|---|---|
| | | | |

---

## Validation rules

**One row per RULE, not per field.** A field requiring both `required` and `maxLength` contributes
two rows. This table is the denominator for `validation_rule_coverage`.

| Field | Rule | Constraint | Error code | Confidence |
|---|---|---|---|---|
| | required | | | |
| | maxLength | 50 | | |

---

## State model

For every entity with a lifecycle. The transition table is the denominator for `transition_coverage`
— **including the invalid transitions**, which is where most missed defects live.

**Entity:** `<name>` · **States:** `<list>`

| From \ To | StateA | StateB | StateC |
|---|---|---|---|
| **StateA** | — | valid (`<action>`) | **invalid** → expect [error] |
| **StateB** | invalid → expect [error] | — | valid (`<action>`) |

---

## UI surface

Only for `level:ui` cases.

| Screen / route | Purpose | Entry point |
|---|---|---|
| | | |

### `data-testid` contract

**This is a risk register, not a wish list.** Automation binds to these. A screen with no
`data-testid` forces fragile locators, which produce D2 noise that drowns real D1 defects.

| Screen | Element | `data-testid` | Exists in SUT? | If missing |
|---|---|---|---|---|
| | | | `no` | [negotiate with SUT team / accept fragile locator / push coverage to API level] |

---

## Data model (for `level:db` verification)

| Table | Column | Type | Constraint | Notes |
|---|---|---|---|---|
| | | | UNIQUE / FK / NOT NULL / CHECK | |

DDL-enforced constraints are the denominator contribution for constraint testing — and they can only
be proven at API or DB level, never through the UI.

---

## Third-party integrations

| Service | Called by | Protocol | Local stub | Real in |
|---|---|---|---|---|
| | | | `wiremock/mappings/<service>-<scenario>.json` | sit, uat |

---

## Open questions for the SUT team

Every `inferred` or `assumed` row above needs a line here. **G0 does not pass while this table has
rows that block a planned test case.**

| # | Question | Blocks | Asked on | Answer | Resolved |
|---|---|---|---|---|---|
| Q1 | | | | | |

---

## Change log

| Date | REQ | What changed | Impact on existing test cases |
|---|---|---|---|
| | | | |

> A change here is an **impact-analysis trigger**: every test case citing a changed anchor must be
> re-examined. `impact-analyst` reads this table.
