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
coverage shortfall rather than false confidence.

## Approval

**Confirmed-by:** —
**Confirmed-at:** —
**Confirmed rows:** — / —
**Status:** `pending_confirmation`

---

## Endpoints

For each endpoint: method, path, auth, request schema, response schema **per status code**, and the
error envelope. Every field typed. This is the level of precision a test case needs — anything
vaguer and the expected result becomes an opinion.

### `POST /orch/api/v1/dipchip`  <a id="post-dipchip-v3"></a>

| | |
|---|---|
| **Confidence** | `inferred` |
| **Source** | `docs/env_matrix.md` §SIT Endpoints §2 (path & URL); Confluence EPTEAM page 6190366768 via Rovo 2026-09-07 (endpoint identity, D17); EKC-8204 description; QA grill 2026-09-06 (D2, D5, D8, D9, D14); Rovo 2026-09-07 (D17–D30) |
| **Auth** | Required — `x-devops-key` header (DevOps API key) (Rovo 2026-09-07, D18/D30; refines D14). Credential value still to be obtained from EKYC team before phase 5 |
| **Idempotent** | `inferred` no — evidence photo is stored/updated on success (side effect); a second submission for the same record updates the stored photo |

**SIT URLs** (`docs/env_matrix.md` §2):
- Internal: `https://10.249.78.180:443/orch/api/v1/dipchip`
- External/Gateway: not documented for orchestrator in `docs/env_matrix.md` — ask SUT team at G0
- Robot alias: `dipchip_orchestrator`

**Request**
```json
{
  "information": {
    "evidencePhoto":  "string (conditional/optional) — base64-encoded image data, nested at information.evidencePhoto (Rovo 2026-09-07, D19). Mandatory only for specific channels (e.g. AIS); optional for BaaS (corroborates D5). When present, validated per VAL-evidence-001 and VAL-evidence-002. Absent/null/empty does NOT trigger 104001 (QA grill 2026-09-06, D5 — flag for SUT verification at G0)."
  },
  "/* other fields */":  "unknown — full dipchip V3 request schema not documented in EKC-8204 (BQ1). Channel/source is transported via headers, not body fields (D18 — V1 differs: channel/product are body fields)."
}
```

**Transport constraints** — an API contract is more than its body. Headers, parameters, and
payload limits all produce testable behaviour; omitting them here pushes them into "opinion".

| Kind | Name | Constraint | Confidence |
|---|---|---|---|
| header | `Content-Type` | `application/json`, required | `inferred` |
| header | `x-devops-key` | DevOps API key — required for auth (Rovo 2026-09-07, D18/D30; refines D14). Credential value still to be obtained. | `inferred` |
| header | `x-channel` | Channel identifier; value `BAAS` for BaaS flow (Rovo 2026-09-07, D18/D30) | `inferred` |
| header | `x-devops-src` | Source identifier; value `BAAS` (also VB/ATM/EDC for other channels) (Rovo 2026-09-07, D30) | `inferred` |
| header | `x-product` | Product identifier (Rovo 2026-09-07, D18/D30) | `inferred` |
| header | `x-devops-dest` | Destination; value `ekyc` (Rovo 2026-09-07, D18/D30) | `inferred` |
| network | VPN | Bank VPN required for SIT (`docs/env_matrix.md` §Critical prerequisite) | `inferred` |
| payload limit | evidencePhoto | ≤ 500 KB (decoded image bytes — D4) | `inferred` |
| payload limit | total body size | NOT defined in API docs — governed by API gateway / Kong (typically 10–20 MB). Exact limit unconfirmed (Rovo 2026-09-07, D25) | `assumed` |

**Responses**
- **Success** — HTTP 200 (Rovo 2026-09-07, D24; V3 is asynchronous)
  ```json
  {
    "code": "0000",
    "message": "Transaction Success",
    "description": "",
    "data": {
      "refId": "<uuid>"
    }
  }
  ```
- **Error: invalid image** — HTTP 400 Bad Request (Rovo 2026-09-07, D23; corroborates QA grill D2; source: EPTEAM page 3740667625 + EKC-8208 DONE)
  ```json
  {
    "code": "104001",
    "message": "Request is invalid format",
    "description": "image is invalid format"
  }
  ```
- **Error: size exceeded** — HTTP 400 Bad Request (Rovo 2026-09-07, D23; corroborates QA grill D2; source: EPTEAM page 3740667625 + EKC-8208 DONE)
  ```json
  {
    "code": "104010",
    "message": "Image size exceeded",
    "description": "evidencePhoto size exceeded"
  }
  ```

**Side effects** — rows written/updated/deleted, events published, files created. This is what a
`level:db` test asserts on.

| Kind | Where | What happens | Confidence |
|---|---|---|---|
| object storage | GCS bucket `dipchip-image-ktbgov-uat` (Rovo 2026-09-07, D28) | On success (state 0000): evidence photo is uploaded to the bucket | `inferred` |
| relational DB | `tb_dipchip_info` (active) | On success: record written with metadata + `imagePath` reference (never raw base64) | `inferred` |
| relational DB | `tb_dipchip_info_history` (history) | On success: history record written | `inferred` |
| Master Vault | trusted-source flag | On success: trusted-source flag set for the citizen | `inferred` |
| Kafka | topic `cdi.dipchip.maintain.req` | On success: event emitted | `inferred` |
| object storage | GCS bucket `dipchip-image-ktbgov-uat` | On validation failure (104001): previously stored evidence photo is **NOT overwritten** (EKC-8204 AC-2, Main Flow step 4; Rovo D28) | `inferred` |
| object storage | GCS bucket `dipchip-image-ktbgov-uat` | On size-exceeded failure (104010): previously stored evidence photo is **NOT overwritten** — same guarantee as 104001 (QA grill 2026-09-06, D10; Rovo D28) | `inferred` |
| relational DB | `tb_dipchip_info` | On any failure: previous timestamps and `imagePath` remain untouched (Rovo 2026-09-07, D29) | `inferred` |

**Related endpoints** (documented in `docs/env_matrix.md` or Rovo-retrieved Confluence):

| Endpoint | Path | Role | Confidence |
|---|---|---|---|
| `POST /api/registration/v1/dipchip-service/dipchip` <a id="post-dipchip-v1"></a> | `https://10.249.78.250:443/api/registration/v1/dipchip-service/dipchip` | Dipchip **V1** endpoint — no `evidencePhoto` field. Not the V3 endpoint under test (Rovo 2026-09-07, D17). | `inferred` |
| `POST /orch/api/v1/dipchip-inquiry` <a id="post-dipchip-inquiry-v3"></a> | (SIT URL not in `docs/env_matrix.md` — ask SUT team) | **Inquiry by citizenId or refId** — used for AC-2c black-box non-overwrite verification (Rovo 2026-09-07, D29). Alternative path: `/customer/v1/dipchip/inquiry`. | `inferred` |
| `POST /customer/v1/biometric/trusted-source-image/inquiry` <a id="post-trusted-source-inquiry"></a> | (SIT URL not in `docs/env_matrix.md` — ask SUT team) | **Active vault image inquiry** — used for AC-2c black-box non-overwrite verification (Rovo 2026-09-07, D29). | `inferred` |
| `POST /dipichip/v2/inquiry` <a id="post-dipchip-inquiry"></a> | `https://10.249.78.250:443/dipichip/v2/inquiry` | V2 inquiry (query, not submission). Not exercised by REQ001 evidence-photo validation. | `inferred` |

---

## Error envelope

The shape every error response shares. If the SUT is inconsistent here, **say so** — an inconsistent
error envelope is itself a finding worth raising with the SUT team, and it changes how many
exception cases you need.

Error envelope for dipchip V3 evidence-photo validation errors, as documented in EKC-8204:

```json
{ "code": "string (enum)", "message": "string", "description": "string" }
```

> **Note:** This shape uses `description`, not the `fields` object shown in the generic template.
> The `description` field is being **added** as part of EKC-8204 — AC-3 notes the AS-IS 104010
> response had no `description` field; the TO-BE adds `"description": "evidencePhoto size exceeded"`.
> The error JSON is the **complete HTTP response body**, not nested in a larger object (QA grill
> 2026-09-06, D8; Rovo D22 corroborates) — exact-match assertions are writable. HTTP 400 for both
> 104001 and 104010 is now corroborated by Confluence (Rovo 2026-09-07, D23; source: EPTEAM page
> 3740667625 + EKC-8208 DONE), not just QA assertion. Whether all dipchip errors share this
> envelope or only the evidence-photo validation errors do remains unconfirmed at G0. The AS-IS →
> TO-BE change to 104010 is an impact-analysis trigger for any existing test that asserts on the
> 104010 response shape.

| Rule ID | Code | HTTP status | When | Confidence |
|---|---|---|---|---|
| `ERR-104001` | `104001` | 400 (Rovo 2026-09-07, D23; corroborates QA grill D2; source: EPTEAM page 3740667625 + EKC-8208 DONE) | `evidencePhoto` cannot be decoded from base64 OR decoded bytes do not match an accepted format's magic bytes (JPEG/PNG only — VAL-evidence-001 fails) | `inferred` |
| `ERR-104010` | `104010` | 400 (Rovo 2026-09-07, D23; corroborates QA grill D2; source: EPTEAM page 3740667625 + EKC-8208 DONE) | `evidencePhoto` size > 500 KB (VAL-evidence-002 fails) | `inferred` |

`Rule ID` is the citeable anchor: a test case writes `Basis_Ref: ERR-104001`, never a prose
description. IDs never change meaning — retire them, don't recycle them.

---

## Validation rules

**One row per RULE, not per field.** A field requiring both `required` and `maxLength` contributes
two rows. This table is the denominator for `validation_rule_coverage`.

| Rule ID | Field | Condition / context | Rule / constraint | HTTP status | Error code | Expected description | Confidence |
|---|---|---|---|---|---|---|---|
| `VAL-evidence-001` | `information.evidencePhoto` | only when channel = BaaS (QA grill 2026-09-06, D9; Rovo D22) | Must be decodable from base64 AND the decoded bytes must match an accepted format's **magic bytes**: **JPEG and PNG only** via the eKYC central common image-validation module; GIF/WebP/BMP and all others rejected (QA grill 2026-09-06, D6; Rovo 2026-09-07, D27). Failure → 104001. | 400 (Rovo 2026-09-07, D23) | `104001` | `image is invalid format` | `inferred` |
| `VAL-evidence-002` | `information.evidencePhoto` | only when channel = BaaS (QA grill 2026-09-06, D9; Rovo D22) | Size ≤ 500 KB (measured on **decoded image bytes**, not base64 string length — QA grill 2026-09-06, D4). Exactly 500 KB is **accepted** (QA grill 2026-09-06, D3). Byte unit unconfirmed: KB = 1,000 or 1,024 bytes? (BQ3 remains open — D26). Size is checked **before** decoding/format validation to avoid memory overhead — an image both oversized AND undecodable returns 104010 (QA grill 2026-09-06, D7; Rovo 2026-09-07, D27). Failure → 104010. | 400 (Rovo 2026-09-07, D23) | `104010` | `evidencePhoto size exceeded` | `inferred` |
| `VAL-order-001` | (validation pipeline) | channel = BaaS | **Validation order (fail-fast):** header & required-schema check → image size (104010, checked BEFORE decoding) → base64 decodability + magic-bytes/format (JPEG+PNG only; 104001) → DOPA (Rovo 2026-09-07, D27). First failing check determines the error returned. | — | — | — | `inferred` |

- **Rule ID** — the citeable anchor. A test case writes `Basis_Ref: VAL-evidence-001`, never a
  prose description. IDs never change meaning — retire them, don't recycle them.
- **Condition / context** — rules that fire only under specific inputs (channel, flow version,
  flag state) MUST say so here; a rule without its context is tested in the wrong place.
- **HTTP status** — business-error codes that travel on HTTP 200 and those on HTTP 4xx are
  different behaviours and are tested differently.

---

## State model

For every entity with a lifecycle. The transition table is the denominator for `transition_coverage`
— **including the invalid transitions**, which is where most missed defects live.

**Entity:** `dipchip process` · **States:** `0001 Initiate`, `0002 Processing`, `0000 Success`, `Failed (104xxx/102xxx/105xxx)`

> Full lifecycle from Rovo 2026-09-07, D28 (Confluence EPTEAM pages). `0001 Initiate` generates
> `refId`; `0002 Processing` runs image validation + DOPA; `0000 Success` writes to `tb_dipchip_info`,
> uploads photo to GCS bucket `dipchip-image-ktbgov-uat`, sets Master Vault trusted-source flag, emits
> Kafka event `cdi.dipchip.maintain.req`; `Failed` returns error code and NEVER overwrites existing
> images in Storage/Vault. Transitions marked **invalid** are expected to be rejected; testing them
> confirms the SUT guards against them.

| From \ To | 0001 Initiate | 0002 Processing | 0000 Success | Failed |
|---|---|---|---|---|
| **0001 Initiate** | — | valid (refId generated; request accepted into processing) | **invalid** → cannot skip processing | **invalid** → cannot skip processing |
| **0002 Processing** | **invalid** → cannot re-initiate mid-process | — | valid (VAL-evidence-001 + VAL-evidence-002 pass; DOPA passes; AC-1) | valid (VAL-evidence-001 fails → 104001, or VAL-evidence-002 fails → 104010, or DOPA fails → 102xxx/105xxx; AC-2/AC-3) |
| **0000 Success** | **invalid** → expect error (cannot re-initiate without a new request) | **invalid** → expect error (cannot re-process without a new request) | — | **invalid** → expect error (cannot fail after success without a new request) |
| **Failed** | **invalid** → expect error (cannot re-initiate without a new request) | **invalid** → expect error (cannot re-process without a new request) | **invalid** → expect error (cannot succeed after failure without a new request) | — |

---

## UI surface

Only for `level:ui` cases.

**Not applicable.** `docs/test_strategy.md` §Levels in scope: "UI / Browser — **no — out of scope**".
The system under test for this effort is API-only. No `data-testid` contract is needed for REQ001.

---

## Data model (for `level:db` verification)

> Evidence photo lives in **Object Storage (GCS bucket `dipchip-image-ktbgov-uat`)** — NOT in a DB
> table (QA grill 2026-09-06, D15; Rovo 2026-09-07, D21/D28). The relational DB stores only metadata
> + an `imagePath` reference, never raw base64. PII is hashed/encrypted (`citizen_id_hashed`).
> AC-2c verification is now observable **black-box via API** (D29): `POST /orch/api/v1/dipchip-inquiry`
> by citizenId/refId, and `POST /customer/v1/biometric/trusted-source-image/inquiry` for the active
> vault image. White-box: query `tb_dipchip_info` by `citizen_id_hashed` — on failure paths, previous
> timestamps and `imagePath` must remain untouched. Object-storage read access is still needed for
> direct binary verification (D1 access request stands).

| Store | Path / key | Type | Constraint | Notes |
|---|---|---|---|---|
| GCS bucket `dipchip-image-ktbgov-uat` | imagePath reference | binary (decoded image) | — | Written on success (state 0000); NOT overwritten on any failure (104001 — AC-2; 104010 — D10; Rovo D28). |
| `tb_dipchip_info` (active) | row by `citizen_id_hashed` | metadata + `imagePath` | `citizen_id_hashed` (hashed PII) | Written on success; on failure, previous timestamps + `imagePath` untouched (Rovo D29). |
| `tb_dipchip_info_history` (history) | row by `citizen_id_hashed` | metadata + `imagePath` | — | History record written on success (Rovo D28). |

Object-storage constraints are the denominator contribution for constraint testing — and they can
only be proven at API or storage level, never through the UI.

---

## Configurations & feature flags

Behaviour that depends on a flag or env var is TWO contracts, not one. Record the current target
value per environment — a test run against the wrong flag value produces a D5, not a D1, and only
this table tells them apart.

| Config / flag name | Default | Target value (SIT / UAT) | Controlled behaviour | Confidence |
|---|---|---|---|---|
| none (QA grill 2026-09-06, D16) | n/a | always active | No feature flag — evidence-photo validation logic is always active. **Caveat:** EKC-8204 ticket is UNRELEASE — QA must confirm the SIT build contains EKC-8204 before execution. | `inferred` |

---

## Test data preconditions

Data states a test run assumes to exist BEFORE it starts. Tests never create these — seeding is
out of Robot (see `.claude/refs/e2e-test-data-conventions.md`). This table tells whoever seeds
exactly what "ready" means.

| State | Entity | Required attributes | Needed by (AC / test area) |
|---|---|---|---|
| Pre-existing evidence photo | dipchip record for the same customer/transaction | A previously stored evidence photo must exist before the test sends an invalid/oversized image | AC-2c (non-overwrite verification); EKC-8204 Dependencies |
| Valid BaaS channel | dipchip V3 request headers | `x-channel: BAAS` and/or `x-devops-src: BAAS` (Rovo 2026-09-07, D18/D30). Exact mandatory header combination still open (G0). | All ACs — only BaaS is in scope per Main Flow step 1 (BQ9) |
| Valid evidence photo | `evidencePhoto` field | Base64 string that decodes to a valid **JPEG or PNG** image ≤ 500 KB (measured on decoded bytes; exactly 500 KB accepted — QA grill 2026-09-06, D3/D4/D6; byte unit still open — BQ3) | AC-1 (happy path) |

---

## Third-party integrations

| Service | Called by | Protocol | Local stub | Real in |
|---|---|---|---|---|
| DOPA | dipchip process | HTTP | `wiremock/mappings/dopa-<scenario>.json` (not available — no local stack) | sit |
| Biometric | dipchip process | HTTP | `wiremock/mappings/biometric-<scenario>.json` (not available — no local stack) | sit |
| AML screening | dipchip process | HTTP | `wiremock/mappings/aml-<scenario>.json` (not available — no local stack) | sit |

> These integrations are part of the broader dipchip flow but are **not directly exercised by
> REQ001**, which targets only the evidence-photo validation step. They are listed for completeness;
> test cases for REQ001 should not assert on their behaviour unless validation passes and processing
> continues (AC-1), at which point downstream calls may occur. No WireMock is available in any
> environment (`docs/env_matrix.md` §Capability matrix).

---

## Anchors

Every citeable rule lives behind an ID so a test case's `Basis_Ref` is a stable reference, not a
quote. Convention: `VAL-<entity>-<nnn>` for validation rules, `ERR-<code>` for error codes,
`SE-<target>-<nnn>` for side effects, plus the `<a id="...">` anchor on each endpoint heading.

| ID | Points to |
|---|---|
| `post-dipchip-v3` | `POST /orch/api/v1/dipchip` — dipchip V3 endpoint (orchestrator). Corrected 2026-09-07 from V1 path (D17). |
| `post-dipchip-v1` | `POST /api/registration/v1/dipchip-service/dipchip` — dipchip V1 endpoint (related; no evidencePhoto field). |
| `post-dipchip-orch` | **Retired** — superseded by `post-dipchip-v3` (the orchestrator IS the V3 endpoint, D17). |
| `post-dipchip-inquiry-v3` | `POST /orch/api/v1/dipchip-inquiry` (or `/customer/v1/dipchip/inquiry`) — V3 inquiry by citizenId/refId; AC-2c black-box verification (D29). |
| `post-trusted-source-inquiry` | `POST /customer/v1/biometric/trusted-source-image/inquiry` — active vault image inquiry; AC-2c black-box verification (D29). |
| `post-dipchip-inquiry` | `POST /dipichip/v2/inquiry` — V2 inquiry endpoint (related, not exercised by REQ001). |
| `ERR-104001` | Error: invalid image format (code `104001`, message `Request is invalid format`, description `image is invalid format`, HTTP 400) |
| `ERR-104010` | Error: image size exceeded (code `104010`, message `Image size exceeded`, description `evidencePhoto size exceeded`, HTTP 400) |
| `VAL-evidence-001` | Validation: `information.evidencePhoto` must decode from base64 and match JPEG/PNG magic bytes |
| `VAL-evidence-002` | Validation: `information.evidencePhoto` size ≤ 500 KB (decoded bytes) |
| `VAL-order-001` | Validation order: header/schema → size (104010, before decoding) → base64+format (104001) → DOPA |
| `SE-evidence-001` | Side effect: evidence photo uploaded to GCS bucket `dipchip-image-ktbgov-uat` on success |
| `SE-evidence-002` | Side effect: previously stored evidence photo NOT overwritten on validation failure (104001) |
| `SE-evidence-003` | Side effect: previously stored evidence photo NOT overwritten on size-exceeded failure (104010) |
| `SE-evidence-004` | Side effect: `tb_dipchip_info` record written on success; `imagePath` + timestamps untouched on failure |
| `SE-evidence-005` | Side effect: Kafka event `cdi.dipchip.maintain.req` emitted on success |
| `SE-evidence-006` | Side effect: Master Vault trusted-source flag set on success |

---

## Open questions for the SUT team

Every `inferred` or `assumed` row above needs a line here. **G0 does not pass while this table has
rows that block a planned test case.**

> Numbered BQ1..BQ16 for the SUT team. The orchestrator relays these. Each maps to one or more
> testability defects in `story_analysis.md` (T1..T12) where noted. Confluence documentation was
> retrieved via Atlassian Rovo on 2026-09-07 (EPTEAM pages 6190366768, 4605837537, 3702784282,
> 3740667625, 3769696998, 3676995762, 3731357957; GoofyDisco 5633901389; Jira EKC-8204/8208).
> QA grill 2026-09-06 (Natnicha) answered 12 of 16 BQs (D2–D16); Rovo 2026-09-07 (D17–D30)
> resolved or narrowed the remainder. **Rows remain `inferred` — only G0 with the SUT team
> resolves them.** Resolved = `yes (docs)` or `yes (grill)` means the question is answered by
> documentation or QA grill; G0 still ratifies. `partial` = narrowed but not fully closed.

| # | Question | Blocks | Maps to story_analysis | Asked on | Answer | Resolved |
|---|---|---|---|---|---|---|
| BQ1 | Full dipchip V3 request schema — what fields exist beyond `information.evidencePhoto`? Is `evidencePhoto` required or optional? What is the total body size limit? | Endpoint request schema; test data construction | — | 2026-09-04 | `evidencePhoto` is at `information.evidencePhoto`, conditional/optional (D19). Total body limit NOT in API docs — governed by Kong/gateway (D25, `assumed`). Full field list still unknown. | `partial` |
| BQ2 | HTTP status code for 104001 and 104010 error responses — HTTP 400 (Bad Request) or HTTP 200 with business-error code in body? | ERR-104001, ERR-104010, VAL-evidence-001, VAL-evidence-002; all error test cases | T2 | 2026-09-04 | HTTP 400 Bad Request for both 104001 and 104010 (Rovo 2026-09-07, D23; corroborates QA grill D2; source: EPTEAM page 3740667625 + EKC-8208 DONE) | `yes (docs)` |
| BQ3 | 500 KB boundary — is an evidencePhoto of exactly 500 KB accepted or rejected? Is "KB" 1,000 bytes (decimal) or 1,024 bytes (binary), i.e. is the threshold 500,000 or 512,000 bytes? | VAL-evidence-002; boundary value analysis for AC-3a | T3 | 2026-09-04 | Exactly 500 KB is **accepted** (D3). Docs indicate 1 KB = 1,024 bytes (512,000) on decoded stream or base64 length×3/4 (D26). **Boundary-test BOTH 500,000 and 512,000** until SUT confirms. Still open for G0. | `partial` |
| BQ4 | Size measurement basis — is "evidencePhoto size" measured as the length of the base64 string or the byte length of the decoded image? These differ by ~33%. | VAL-evidence-002; test data construction for size boundary | T6 | 2026-09-04 | Measured on **decoded image bytes**, not base64 string length (QA grill 2026-09-06, D4) | `yes (grill)` |
| BQ5 | Validation precedence — when evidencePhoto is BOTH invalid (cannot decode/convert) AND larger than 500 KB, which error is returned (104001 or 104010)? What is the validation order? | Combined-failure test cases; decision table | T7 | 2026-09-04 | Full order (fail-fast): header/schema → size (104010, before decoding) → base64+magic-bytes/format (104001) → DOPA (Rovo 2026-09-07, D27; corroborates D7). Oversized + undecodable returns **104010**. | `yes (docs)` |
| BQ6 | Missing/null/empty evidencePhoto — when the field is absent, `null`, or `""` (empty string), does the request follow the 104001 error path or is the field optional and processed without it? | VAL-evidence-001; exception cases for missing/null/empty | T4 | 2026-09-04 | **Optional** for BaaS — absent/null/empty does NOT trigger 104001 (QA grill D5; Rovo D19 corroborates: mandatory only for channels like AIS). **SUT confirmation at G0 still needed** for BaaS-optional behaviour. | `partial` |
| BQ7 | Supported image formats — which formats are accepted as "convertible back into an image" (JPEG, PNG, WebP, GIF, BMP, any)? Which are rejected? | VAL-evidence-001; test data construction for valid/invalid images | T5 | 2026-09-04 | **JPEG and PNG only** via eKYC central common image-validation module; GIF/WebP/BMP and all others rejected via 104001 (QA grill D6; Rovo D22/D27 corroborates) | `yes (docs)` |
| BQ8 | Error response shape — is the error JSON `{ "code", "message", "description" }` the complete HTTP response body, or is it nested inside a larger response object? | ERR-104001, ERR-104010; all error test case expected results | T8 | 2026-09-04 | Error JSON is the **complete HTTP response body**, not nested (QA grill D8; Rovo D22 corroborates) | `yes (docs)` |
| BQ9 | Source channel scope — does the evidence-photo validation apply only to requests from source BaaS, or to all source channels? Are dipchip V1/V2 flows in scope? | VAL-evidence-001, VAL-evidence-002 context; test scope | T9 | 2026-09-04 | Validation applies to **source BaaS only**; V1/V2 and other channels out of scope (QA grill D9; Rovo D22 corroborates) | `yes (docs)` |
| BQ10 | Non-overwrite on size-exceeded path — on the 104010 failure path, is the previously stored evidence photo also NOT overwritten (same guarantee as 104001), or does it behave differently? | SE-evidence-003; side-effect verification for AC-3a | T10 | 2026-09-04 | Non-overwrite guarantee applies to the **104010 path too** (QA grill D10; Rovo D22/D28 corroborates) | `yes (docs)` |
| BQ11 | Success response shape — what HTTP status and response body indicates a successful dipchip? | AC-1 happy path test case expected result | T12 | 2026-09-04 | V3 is **asynchronous**: HTTP 200 `{ "code": "0000", "message": "Transaction Success", "description": "", "data": { "refId": "<uuid>" } }` (Rovo 2026-09-07, D24). V1-style sync full-data object is NOT V3's shape. | `yes (docs)` |
| BQ12 | Exact JSON field name for the source/channel parameter — is it `source`, `channel`, `sourceType`, or something else? | Request schema; test data construction | — | 2026-09-04 | **Not a body field** — channel/source is transported via **request headers** `x-channel: BAAS` and/or `x-devops-src: BAAS` (Rovo 2026-09-07, D18/D30). V1 differs: channel/product are body fields. **Exact mandatory header combination still open at G0** (D30). | `partial` |
| BQ13 | Authentication mechanism for the dipchip API — Bearer JWT, API key, mTLS, or other? What header(s) are required? | Transport constraints; all test cases (auth setup) | — | 2026-09-04 | **`x-devops-key`** header (DevOps API key) (Rovo 2026-09-07, D18/D30; refines D14). Credential value still to be obtained from EKYC team. | `yes (docs)` |
| BQ14 | Feature flags — is the evidence-photo validation logic (EKC-8204 enhancement) gated by a feature flag, or is it always active? If flagged, what is the flag name and target value in SIT? | Configurations; test execution in SIT | — | 2026-09-04 | **No feature flag**; validation always active (QA grill D16). Caveat: ticket is UNRELEASE — **confirm SIT build contains EKC-8204** before execution (open for G0). | `partial` |
| BQ15 | Evidence photo storage location — what DB table or object-storage bucket/path stores the evidence photo? | Data model; `level:db` verification for AC-2c | T1 | 2026-09-04 | **GCS bucket `dipchip-image-ktbgov-uat`** (Rovo D28). DB tables `tb_dipchip_info` (active) + `tb_dipchip_info_history` (history) store metadata + `imagePath` only, PII hashed (`citizen_id_hashed`). AC-2c now observable black-box via inquiry APIs (D29). Object-storage read access still needed for direct binary verification. | `partial` |
| BQ16 | Dipchip process state model — what are the full set of states and transitions in the dipchip lifecycle (beyond the evidence validation step)? | State model; transition coverage denominator | — | 2026-09-04 | `0001 Initiate` (refId generated) → `0002 Processing` (validation + DOPA) → `0000 Success` (record to `tb_dipchip_info`; photo to GCS; Master Vault flag; Kafka event) OR `104xxx/102xxx/105xxx Failed` (error returned; existing images NEVER overwritten) (Rovo 2026-09-07, D28). | `yes (docs)` |

---

## Change log

| Date | REQ | What changed | Impact on existing test cases |
|---|---|---|---|
| 2026-09-04 | REQ001 | Initial basis drafted for EKC-8204 (dipchip V3 evidence photo validation). All rows `inferred` from EKC-8204 Jira description and `docs/env_matrix.md` — Confluence documentation was not accessible (bank auth). 16 open questions (BQ1..BQ16) raised for SUT team confirmation at G0. | None — no existing test cases yet. |
| 2026-09-06 | REQ001 | QA grill answers D2–D16 folded in (12 BQs answered/partially answered; rows remain `inferred` pending G0). | None — no existing test cases yet. |
| 2026-09-07 | REQ001 | Rovo-retrieved Confluence facts D17–D30 folded in. **Endpoint corrected:** V3 = `POST /orch/api/v1/dipchip` (was V1 path `/api/registration/v1/dipchip-service/dipchip` — D17). **Headers:** V3 uses `x-channel`/`x-devops-src`/`x-product`/`x-devops-dest`/`x-devops-key` (D18/D30). **Request:** `evidencePhoto` nested at `information.evidencePhoto`, conditional/optional (D19). **Success:** async HTTP 200 `{code:"0000",data:{refId}}` (D24). **Errors:** HTTP 400 corroborated by docs for 104001/104010 (D23). **Validation order:** header/schema → size (before decoding) → base64+magic-bytes → DOPA (D27). **State model:** replaced 3-state with full lifecycle 0001→0002→0000/Failed (D28). **Storage:** GCS bucket `dipchip-image-ktbgov-uat` + `tb_dipchip_info`/`tb_dipchip_info_history` (D21/D28). **AC-2c unblocked:** inquiry endpoints added for black-box non-overwrite verification (D29). **Payload:** total body limit `assumed` (Kong/gateway — D25). New anchors: `post-dipchip-v1`, `post-dipchip-inquiry-v3`, `post-trusted-source-inquiry`, `VAL-order-001`, `SE-evidence-004`/`005`/`006`. `post-dipchip-orch` retired (superseded by `post-dipchip-v3`). Sources: EPTEAM pages 6190366768, 4605837537, 3702784282, 3740667625, 3769696998, 3676995762, 3731357957; GoofyDisco 5633901389; Jira EKC-8204/8208. | None — no existing test cases yet. All rows remain `inferred` (or `assumed` for Kong limit) pending G0. |

> A change here is an **impact-analysis trigger**: every test case citing a changed anchor must be
> re-examined. `impact-analyst` reads this table.
