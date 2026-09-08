> ⚠️ DRAFT PREVIEW — NOT FROZEN. Denominators are NOT G2-ratified. For human shape-review before /phase2.

# US001 — Test design notes

**Story:** US001 — [BaaS] Enhance dipchip V3 validation logic: check image evidence photo base 64
**Requirement:** REQ001
**Risk rating:** P1 (highest AC risk in the story; AC-2a/AC-2b/AC-2c are P1, AC-1/AC-3a are P2 — the story is treated at P1 depth)
**Techniques applied:** EP, BVA, DT, ST, EG

## Derivation

Show the work. A reviewer must be able to see WHY these cases and not others.

### Equivalence classes

**Rule** cites the `test_basis.md` → Validation rules anchor each class exercises — see
`csv-schema.md` and `coverage-model.md` §2 dimension 3. A row's Valid and Invalid classes can sit
under different rules (or no rule at all), so IC/VC pairs that differ are split across rows here —
the blank Field/Valid/Invalid cells are continuations of the row above, same as before.

| Field | Rule | Valid classes | Invalid classes | Cases |
|---|---|---|---|---|
| `information.evidencePhoto` (base64 string) | VAL-evidence-001 | VC1: valid base64 → valid JPEG ≤ 500 KB | IC1: not base64-decodable | TC-001 (VC1), TC-003 (IC1) |
| | VAL-evidence-001 | VC2: valid base64 → valid PNG ≤ 500 KB | IC2: valid base64 → GIF bytes | TC-002 (VC2), TC-004 (IC2) |
| | — | VC3: absent / null / empty (optional for BaaS — D5) | | TC-014/015/016 (VC3) |
| | VAL-evidence-001 | | IC3: valid base64 → WebP bytes | TC-005 (IC3) |
| | VAL-evidence-001 | | IC4: valid base64 → BMP bytes | TC-006 (IC4) |
| | VAL-evidence-001 | | IC5: valid base64 → random bytes (magic-bytes mismatch, D27) | TC-007 (IC5) |
| | VAL-evidence-001 | | IC6: truncated base64 (missing padding) | TC-012 (IC6) |
| | VAL-evidence-001 | | IC7: whitespace-only string | TC-020 (IC7) |
| | — | | IC8: wrong type (number instead of string — schema-level shape, BQ1, not documented under VAL-evidence-001) | TC-021 (IC8) |
| | VAL-evidence-001 | | IC9: unicode/emoji in base64 field | TC-022 (IC9) |
| | VAL-evidence-001 | | IC10: injection payload | TC-023 (IC10) |
| `x-devops-key` header | — | VC4: valid DevOps API key | | |
| | — | | IC11: missing | TC-024 (IC11) |
| | — | | IC12: expired | TC-025 (IC12) |
| | — | | IC13: malformed | TC-026 (IC13) |

### Boundary analysis

**This table is the denominator for `boundary_coverage`.** A boundary you fail to list here does not
merely go untested — it silently raises the score.

The primary boundary is the 500 KB size limit on decoded image bytes (D4). The byte unit (1,000 vs
1,024) is unresolved (BQ3/D26), so BOTH thresholds are boundary-tested.

| Field | Type | min−1 | min | max | max+1 | Cases |
|---|---|---|---|---|---|---|
| `evidencePhoto` decoded size (KB=1000) | integer (bytes) | — | — | 500,000 (accepted, D3) | 500,001 (rejected) | TC-008 (max), TC-009 (max+1) |
| `evidencePhoto` decoded size (KB=1024) | integer (bytes) | — | — | 512,000 (accepted, D3) | 512,001 (rejected) | TC-010 (max), TC-011 (max+1) |
| `evidencePhoto` base64 string | string | — | — | truncated (missing padding) | — | TC-012 |
| `evidencePhoto` presence | enum | absent | null | empty `""` | whitespace `"   "` | TC-014, TC-015, TC-016, TC-020 |

**Note on 500,000 vs 512,000:** 500,000 bytes is accepted under both interpretations (it is under
both thresholds). 512,001 bytes is rejected under both. Only 500,001 and 512,000 are
interpretation-sensitive — those two cases are PENDING-G0 (BQ3).

### Decision table — evidencePhoto validation outcome

Conditions:
- C1: evidencePhoto present (non-null, non-empty)?
- C2: decoded size > 500 KB?
- C3: base64-decodable?
- C4: decoded bytes match JPEG/PNG magic bytes?

Validation order (VAL-order-001, D27): header/schema → size (104010, before decoding) → base64 + magic-bytes (104001) → DOPA.

| Conditions | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|
| C1 (present?) | N | Y | Y | Y | Y |
| C2 (size > 500KB?) | — | Y | N | N | N |
| C3 (base64 decodable?) | — | — | N | Y | Y |
| C4 (valid magic bytes?) | — | — | — | N | Y |
| **outcome** | processed without photo (D5) | 104010 | 104001 (decode fail) | 104001 (format fail) | success → DOPA |
| **case** | TC-014 | TC-009 | TC-003 | TC-004 | TC-001 |

**Infeasible rules removed:**
- C1=N with C2/C3/C4 specified: cannot evaluate size/decodability/format of a non-existent field.
- C2=Y with C3/C4 specified: size is checked BEFORE decoding (D7/D27); if size exceeds, decode/format
  are never reached. The combined oversized+undecodable case (TC-013) confirms this — it expects 104010,
  not 104001.
- C3=N with C4 specified: cannot check magic bytes of undecodable input.

Total feasible rules: 5 (R1–R5).

### State transitions — dipchip process lifecycle

From `test_basis.md` State model (D28):

| From \ To | 0001 Initiate | 0002 Processing | 0000 Success | Failed | Case |
|---|---|---|---|---|---|
| **0001 Initiate** | — | valid | invalid | invalid | TC-017 (0001→0002) |
| **0002 Processing** | invalid | — | valid | valid | TC-017 (→0000), TC-018 (→Failed 104001), TC-019 (→Failed 104010) |
| **0000 Success** | invalid | invalid | — | invalid | (lifecycle-level — not directly exercisable by evidence-photo tests alone) |
| **Failed** | invalid | invalid | invalid | — | (lifecycle-level — not directly exercisable by evidence-photo tests alone) |

Valid transitions directly exercised by REQ001: 3 (0001→0002, 0002→0000, 0002→Failed).
Reachable-invalid transitions: 9 (full matrix per basis). The 6 invalid transitions from
0000-Success and Failed states are lifecycle-level — they require a new request to test and are
outside the evidence-photo validation scope. They are counted in the denominator but noted as
requiring separate lifecycle stories for full coverage.

### Exception coverage

Every applicable row of `.claude/refs/exception-catalog.md`. See that file for the
declined-vs-deferred distinction — they are not the same and must not be recorded alike.

| # | Scenario | Applicable | Covered by | Declined — reason |
|---|---|---|---|---|
| A1 | null / field absent | yes | TC-014, TC-015 | |
| A2 | empty string `""` | yes | TC-016 | |
| A3 | whitespace only `"   "` | yes | TC-020 | |
| A4 | over max length | yes | TC-009, TC-011 | |
| A5 | wrong type (number for string) | yes | TC-021 | |
| A6 | wrong format (not base64) | yes | TC-003 | |
| A7 | number out of range | no | — | evidencePhoto is a string field, not numeric — `test_basis.md#post-dipchip-v3` |
| A8 | precision overflow | no | — | not a numeric field |
| A9 | unicode, emoji, RTL | yes | TC-022 | |
| A10 | Thai text specifics | no | — | evidencePhoto is base64-encoded binary, not Thai text |
| A11 | injection payloads | yes | TC-023 | |
| A12 | leading zeros, +/- prefixes | no | — | not a numeric-as-string field |
| A13 | oversized payload | yes | TC-011 | |
| A14 | duplicate keys / conflicting fields | no | — | full request schema unknown (BQ1); cannot construct |
| B1 | no token / no session | yes | TC-024 | |
| B2 | expired token | yes | TC-025 | |
| B3 | malformed token | yes | TC-026 | |
| B4 | insufficient role | no | — | no role model documented for dipchip API (BQ13) |
| B5 | cross-tenant / cross-user | no | — | cross-citizen access is outside REQ001 scope (D9) |
| B6 | token valid for different audience | no | — | not documented |
| B7 | session expiry mid-journey | no | — | API-only, no UI journey (UI out of scope) |
| C1 | operate on deleted/cancelled entity | no | — | outside evidence-photo validation scope |
| C2 | duplicate submit | no | — | endpoint idempotency is outside REQ001 scope |
| C3 | invalid state transition | yes | TC-032 | |
| C4 | concurrent update | no | — | outside evidence-photo validation scope |
| C5 | out-of-order operations | no | — | outside evidence-photo validation scope |
| C6 | entity owned by someone else | no | — | see B5 decline |
| C7 | replay of stale request | no | — | outside evidence-photo validation scope |
| D1–D7 | dependency exceptions | no | — | REQ001 targets only evidence-photo validation; DOPA/Biometric/AML are downstream and not directly exercised — `test_basis.md` Third-party integrations |
| E1 | UNIQUE violation | no | — | no unique constraint on evidence photo |
| E2 | FK violation | no | — | no FK directly relevant to evidence-photo validation |
| E3 | NOT NULL violation | no | — | evidencePhoto is optional (D5) |
| E4 | CHECK constraint | no | — | no CHECK constraint documented |
| E5 | referenced row deleted | no | — | not applicable to validation step |
| E6 | cascade on delete | no | — | not applicable to validation step |
| F1 | limit / quota exceeded | yes | TC-009, TC-011 | |
| F2 | insufficient balance / stock | no | — | not applicable |
| F3 | outside permitted window | no | — | not applicable |
| F4 | entity in blocked/suspended condition | no | — | not applicable to evidence-photo validation |
| G1–G7 | UI-observable exceptions | no | — | UI out of scope — `test_basis.md` UI surface |

**Applicable exception rows: 14** (A1, A2, A3, A4, A5, A6, A9, A11, A13, B1, B2, B3, C3, F1)
**Declined: 30** (with recorded reasons above)
**Deferred: 0**

## Test cases

One block per case. `build-csv.py` parses these — keep the field names and order exactly.

### TC-REQ001-US001-001 — Valid JPEG evidencePhoto, nominal size, success
- **AC:** AC-1
- **Level:** api · **Type:** positive · **Technique:** EP · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers (x-channel: BAAS, x-devops-src: BAAS, x-product, x-devops-dest: ekyc, x-devops-key). SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size ~100 KB
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** refId generated; photo stored to GCS bucket; tb_dipchip_info record written
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-001 · **Env scope:** sit
- **Notes:** D24; D8

### TC-REQ001-US001-002 — Valid PNG evidencePhoto, nominal size, success
- **AC:** AC-1
- **Level:** api · **Type:** positive · **Technique:** EP · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid PNG, decoded size ~100 KB
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** refId generated; photo stored to GCS bucket
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-002 · **Env scope:** sit
- **Notes:** D24

### TC-REQ001-US001-003 — Not valid base64 string, 104001
- **AC:** AC-2a
- **Level:** api · **Type:** negative · **Technique:** EP · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = "!!!not-valid-base64!!!" (not base64-decodable)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-003 · **Env scope:** sit
- **Notes:** D8; D11; D23

### TC-REQ001-US001-004 — Valid base64 of GIF bytes, 104001 (rejected format)
- **AC:** AC-2b
- **Level:** api · **Type:** negative · **Technique:** EP · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid GIF image (decoded size < 500 KB)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-004 · **Env scope:** sit
- **Notes:** D6; D8; D11; D23

### TC-REQ001-US001-005 — Valid base64 of WebP bytes, 104001 (rejected format)
- **AC:** AC-2b
- **Level:** api · **Type:** negative · **Technique:** EP · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid WebP image (decoded size < 500 KB)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-005 · **Env scope:** sit
- **Notes:** D6; D8; D11; D23

### TC-REQ001-US001-006 — Valid base64 of BMP bytes, 104001 (rejected format)
- **AC:** AC-2b
- **Level:** api · **Type:** negative · **Technique:** EP · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid BMP image (decoded size < 500 KB)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-006 · **Env scope:** sit
- **Notes:** D6; D8; D11; D23

### TC-REQ001-US001-007 — Valid base64 of random bytes (magic-bytes mismatch), 104001
- **AC:** AC-2b
- **Level:** api · **Type:** negative · **Technique:** EP · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded 1000 random bytes (decodes but no valid image magic bytes — D27)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-007 · **Env scope:** sit
- **Notes:** D27; D8; D11; D23

### TC-REQ001-US001-008 — Decoded size exactly 500,000 bytes, accepted (boundary max, KB=1000)
- **AC:** AC-3a;AC-1
- **Level:** api · **Type:** boundary · **Technique:** BVA · **Priority:** P2
- **Basis ref:** `test_basis.md#VAL-evidence-002`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size exactly 500,000 bytes
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#VAL-evidence-002`

- **Postcondition:** refId generated; photo stored
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-008 · **Env scope:** sit
- **Notes:** D3; D24 — 500,000 under both thresholds

### TC-REQ001-US001-009 — Decoded size 500,001 bytes, rejected (boundary max+1, KB=1000)
- **AC:** AC-3a
- **Level:** api · **Type:** boundary · **Technique:** BVA · **Priority:** P2
- **Basis ref:** `test_basis.md#ERR-104010`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size exactly 500,001 bytes
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104010","message":"Image size exceeded","description":"evidencePhoto size exceeded"}

     **Basis:** `test_basis.md#ERR-104010`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten (D10)
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-009 · **Env scope:** sit
- **Notes:** BQ3/D26 — if KB=1024, 500,001 is accepted

### TC-REQ001-US001-010 — Decoded size exactly 512,000 bytes, accepted (boundary max, KB=1024)
- **AC:** AC-3a;AC-1
- **Level:** api · **Type:** boundary · **Technique:** BVA · **Priority:** P2
- **Basis ref:** `test_basis.md#VAL-evidence-002`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size exactly 512,000 bytes
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#VAL-evidence-002`

- **Postcondition:** refId generated; photo stored
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-010 · **Env scope:** sit
- **Notes:** BQ3/D26 — if KB=1000, 512,000 is rejected

### TC-REQ001-US001-011 — Decoded size 512,001 bytes, rejected (boundary max+1, KB=1024)
- **AC:** AC-3a
- **Level:** api · **Type:** boundary · **Technique:** BVA · **Priority:** P2
- **Basis ref:** `test_basis.md#ERR-104010`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size exactly 512,001 bytes
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104010","message":"Image size exceeded","description":"evidencePhoto size exceeded"}

     **Basis:** `test_basis.md#ERR-104010`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten (D10)
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-011 · **Env scope:** sit
- **Notes:** D4; D8; D11; D23 — 512,001 over both thresholds

### TC-REQ001-US001-012 — Truncated base64 (missing padding), 104001
- **AC:** AC-2a
- **Level:** api · **Type:** negative · **Technique:** BVA · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = "iVBORw0KGgo" (valid PNG base64 prefix, missing == padding)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-012 · **Env scope:** sit
- **Notes:** D8; D11; D23

### TC-REQ001-US001-013 — Oversized AND undecodable, 104010 (size checked first)
- **AC:** AC-3a;AC-2a
- **Level:** api · **Type:** negative · **Technique:** DT · **Priority:** P1
- **Basis ref:** `test_basis.md#VAL-order-001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = string of 700,000 random characters (not valid base64, would exceed 500 KB if decoded)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104010","message":"Image size exceeded","description":"evidencePhoto size exceeded"}

     **Basis:** `test_basis.md#VAL-order-001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten (D10)
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-013 · **Env scope:** sit
- **Notes:** D7; D27; D8; D11; D23

### TC-REQ001-US001-014 — evidencePhoto absent, processed without photo (optional for BaaS)
- **AC:** AC-1
- **Level:** api · **Type:** exception · **Technique:** DT · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** Request body with information object but NO evidencePhoto field present
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers, no evidencePhoto field

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** refId generated; no photo uploaded (none provided)
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-014 · **Env scope:** sit
- **Notes:** BQ6/D5 — BaaS-optional behaviour needs SUT confirmation

### TC-REQ001-US001-015 — evidencePhoto null, processed without photo
- **AC:** AC-1
- **Level:** api · **Type:** exception · **Technique:** DT · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = null
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto=null

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** refId generated; no photo uploaded
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-015 · **Env scope:** sit
- **Notes:** BQ6/D5

### TC-REQ001-US001-016 — evidencePhoto empty string, processed without photo
- **AC:** AC-1
- **Level:** api · **Type:** exception · **Technique:** DT · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = "" (empty string)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto=""

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** refId generated; no photo uploaded
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-016 · **Env scope:** sit
- **Notes:** BQ6/D5

### TC-REQ001-US001-017 — State transition: 0001 Initiate -> 0002 Processing -> 0000 Success
- **AC:** AC-1
- **Level:** api · **Type:** positive · **Technique:** ST · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. No existing record for the test citizen.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size ~100 KB
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

  2. POST /orch/api/v1/dipchip-inquiry by refId from step 1 `[verification]`

     **Expected [CP2]:** HTTP 200; response shows dipchip record in state 0000 (Success) with imagePath populated

     **Basis:** `test_basis.md#post-dipchip-inquiry-v3`

- **Postcondition:** record in tb_dipchip_info with state 0000; photo in GCS bucket
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-017 · **Env scope:** sit
- **Notes:** D24; D28

### TC-REQ001-US001-018 — State transition: 0001 Initiate -> 0002 Processing -> Failed (104001)
- **AC:** AC-2a
- **Level:** api · **Type:** negative · **Technique:** ST · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = "!!!not-valid-base64!!!"
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** process in Failed state; no photo uploaded; existing photo not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-018 · **Env scope:** sit
- **Notes:** D28; D8; D11; D23

### TC-REQ001-US001-019 — State transition: 0001 Initiate -> 0002 Processing -> Failed (104010)
- **AC:** AC-3a
- **Level:** api · **Type:** negative · **Technique:** ST · **Priority:** P2
- **Basis ref:** `test_basis.md#ERR-104010`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size 512,001 bytes
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104010","message":"Image size exceeded","description":"evidencePhoto size exceeded"}

     **Basis:** `test_basis.md#ERR-104010`

- **Postcondition:** process in Failed state; no photo uploaded; existing photo not overwritten (D10)
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-019 · **Env scope:** sit
- **Notes:** D28; D8; D11; D23

### TC-REQ001-US001-020 — Whitespace-only evidencePhoto, 104001
- **AC:** AC-2a
- **Level:** api · **Type:** exception · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = "   " (three spaces — not empty, not valid base64)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; existing photo (if any) not overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-020 · **Env scope:** sit
- **Notes:** D8; D11; D23

### TC-REQ001-US001-021 — Wrong type: evidencePhoto as number, 400
- **AC:** AC-2a
- **Level:** api · **Type:** exception · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = 12345 (number, not string)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto=12345

     **Expected [CP1]:** HTTP 400; response body contains code "104001" or schema-validation error

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** no photo uploaded
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-021 · **Env scope:** sit
- **Notes:** HTTP 400 concrete; exact body depends on BQ1

### TC-REQ001-US001-022 — Unicode in evidencePhoto field, 104001
- **AC:** AC-2a
- **Level:** api · **Type:** exception · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = emoji string (not valid base64)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-022 · **Env scope:** sit
- **Notes:** D8; D11; D23

### TC-REQ001-US001-023 — SQL injection payload in evidencePhoto, 104001 or safely handled
- **AC:** AC-2a
- **Level:** api · **Type:** security · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#ERR-104001`
- **Preconditions:** Valid BaaS headers. SIT VPN connected.
- **Test data:** information.evidencePhoto = SQL injection string (not valid base64)
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

- **Postcondition:** no photo uploaded; tb_dipchip_info intact
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-023 · **Env scope:** sit
- **Notes:** D8; D11; D23 — rejected, never executed

### TC-REQ001-US001-024 — Missing x-devops-key header, 401
- **AC:** AC-1
- **Level:** api · **Type:** exception · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** BaaS headers WITHOUT x-devops-key. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG ~100 KB
- **Steps:**

  1. POST /orch/api/v1/dipchip with BaaS headers but no x-devops-key

     **Expected [CP1]:** HTTP 401 (auth failure)

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** no request processed
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-024 · **Env scope:** sit
- **Notes:** B1

### TC-REQ001-US001-025 — Expired x-devops-key, 401
- **AC:** AC-1
- **Level:** api · **Type:** exception · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** BaaS headers with an expired x-devops-key value. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG ~100 KB; x-devops-key = expired credential
- **Steps:**

  1. POST /orch/api/v1/dipchip with expired x-devops-key

     **Expected [CP1]:** HTTP 401 (auth failure, distinct from B1)

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** no request processed
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-025 · **Env scope:** sit
- **Notes:** B2

### TC-REQ001-US001-026 — Malformed x-devops-key, 401
- **AC:** AC-1
- **Level:** api · **Type:** exception · **Technique:** EG · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** BaaS headers with a malformed x-devops-key value. SIT VPN connected.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG ~100 KB; x-devops-key = "not-a-real-key-!!!"
- **Steps:**

  1. POST /orch/api/v1/dipchip with malformed x-devops-key

     **Expected [CP1]:** HTTP 401 (auth failure, never 500)

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** no request processed
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-026 · **Env scope:** sit
- **Notes:** B3 — never 500

### TC-REQ001-US001-027 — Valid photo success, verify side effects (GCS + DB)
- **AC:** AC-1
- **Level:** db · **Type:** positive · **Technique:** ST · **Priority:** P2
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. No existing record for the test citizen.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG ~100 KB
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers and evidencePhoto

     **Expected [CP1]:** HTTP 200; response body exactly {"code":"0000","message":"Transaction Success","description":"","data":{"refId":"<uuid>"}}

     **Basis:** `test_basis.md#post-dipchip-v3`

  2. POST /orch/api/v1/dipchip-inquiry by refId from step 1 `[verification]`

     **Expected [CP2]:** HTTP 200; response shows record with imagePath populated (photo in GCS bucket dipchip-image-ktbgov-uat, tb_dipchip_info row written)

     **Basis:** `test_basis.md#SE-evidence-001`

- **Postcondition:** record in tb_dipchip_info with imagePath; photo in GCS bucket
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-027 · **Env scope:** sit
- **Notes:** SE-evidence-001; SE-evidence-004; D29

### TC-REQ001-US001-028 — Non-overwrite: pre-existing photo, invalid base64, original preserved (black-box)
- **AC:** AC-2c
- **Level:** db · **Type:** negative · **Technique:** ST · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-inquiry-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. A previously stored evidence photo EXISTS for the test citizen.
- **Test data:** information.evidencePhoto = "!!!not-valid-base64!!!"; pre-existing photo citizenId known
- **Steps:**

  1. POST /orch/api/v1/dipchip-inquiry by citizenId `[verification]`

     **Expected [CP1]:** HTTP 200; capture the existing imagePath/photo reference

     **Basis:** `test_basis.md#post-dipchip-inquiry-v3`

  2. POST /orch/api/v1/dipchip with valid BaaS headers and invalid evidencePhoto

     **Expected [CP2]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

  3. POST /orch/api/v1/dipchip-inquiry by citizenId `[verification]`

     **Expected [CP3]:** HTTP 200; response shows the SAME imagePath as step 1 — NOT overwritten

     **Basis:** `test_basis.md#SE-evidence-002`

  4. POST /customer/v1/biometric/trusted-source-image/inquiry by citizenId `[verification]`

     **Expected [CP4]:** HTTP 200; response shows the SAME active vault image as before step 2 — NOT overwritten

     **Basis:** `test_basis.md#post-trusted-source-inquiry`

- **Postcondition:** original photo preserved in GCS bucket and vault
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-028 · **Env scope:** sit
- **Notes:** SE-evidence-002; D29

### TC-REQ001-US001-029 — Non-overwrite: pre-existing photo, wrong format (GIF), original preserved (black-box)
- **AC:** AC-2c;AC-2b
- **Level:** db · **Type:** negative · **Technique:** ST · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-inquiry-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. A previously stored evidence photo EXISTS for the test citizen.
- **Test data:** information.evidencePhoto = base64-encoded valid GIF < 500 KB; pre-existing photo citizenId known
- **Steps:**

  1. POST /orch/api/v1/dipchip-inquiry by citizenId `[verification]`

     **Expected [CP1]:** HTTP 200; capture existing imagePath

     **Basis:** `test_basis.md#post-dipchip-inquiry-v3`

  2. POST /orch/api/v1/dipchip with valid BaaS headers and GIF evidencePhoto

     **Expected [CP2]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

  3. POST /orch/api/v1/dipchip-inquiry by citizenId `[verification]`

     **Expected [CP3]:** HTTP 200; response shows SAME imagePath as step 1 — NOT overwritten

     **Basis:** `test_basis.md#SE-evidence-002`

- **Postcondition:** original photo preserved
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-029 · **Env scope:** sit
- **Notes:** SE-evidence-002; D29

### TC-REQ001-US001-030 — Non-overwrite: pre-existing photo, oversized, original preserved (black-box)
- **AC:** AC-2c;AC-3a
- **Level:** db · **Type:** negative · **Technique:** ST · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-inquiry-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. A previously stored evidence photo EXISTS for the test citizen.
- **Test data:** information.evidencePhoto = base64-encoded valid JPEG, decoded size 512,001 bytes; pre-existing photo citizenId known
- **Steps:**

  1. POST /orch/api/v1/dipchip-inquiry by citizenId `[verification]`

     **Expected [CP1]:** HTTP 200; capture existing imagePath

     **Basis:** `test_basis.md#post-dipchip-inquiry-v3`

  2. POST /orch/api/v1/dipchip with valid BaaS headers and oversized evidencePhoto

     **Expected [CP2]:** HTTP 400; response body exactly {"code":"104010","message":"Image size exceeded","description":"evidencePhoto size exceeded"}

     **Basis:** `test_basis.md#ERR-104010`

  3. POST /orch/api/v1/dipchip-inquiry by citizenId `[verification]`

     **Expected [CP3]:** HTTP 200; response shows SAME imagePath as step 1 — NOT overwritten

     **Basis:** `test_basis.md#SE-evidence-003`

- **Postcondition:** original photo preserved
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-030 · **Env scope:** sit
- **Notes:** SE-evidence-003; D10; D29

### TC-REQ001-US001-031 — Non-overwrite: pre-existing photo, invalid, DB imagePath untouched (white-box)
- **AC:** AC-2c
- **Level:** db · **Type:** negative · **Technique:** ST · **Priority:** P1
- **Basis ref:** `test_basis.md#SE-evidence-004`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. A previously stored evidence photo EXISTS. Read-only DB access to tb_dipchip_info provisioned.
- **Test data:** information.evidencePhoto = "!!!not-valid-base64!!!"; pre-existing photo citizenId known
- **Steps:**

  1. Query tb_dipchip_info by citizen_id_hashed `[verification]`

     **Expected [CP1]:** capture existing imagePath and timestamps

     **Basis:** `test_basis.md#SE-evidence-004`

  2. POST /orch/api/v1/dipchip with valid BaaS headers and invalid evidencePhoto

     **Expected [CP2]:** HTTP 400; response body exactly {"code":"104001","message":"Request is invalid format","description":"image is invalid format"}

     **Basis:** `test_basis.md#ERR-104001`

  3. Query tb_dipchip_info by citizen_id_hashed `[verification]`

     **Expected [CP3]:** imagePath and timestamps are IDENTICAL to step 1 — completely untouched

     **Basis:** `test_basis.md#SE-evidence-004`

- **Postcondition:** DB row unchanged
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-031 · **Env scope:** sit
- **Notes:** BQ15/D29 — DB read access not yet provisioned

### TC-REQ001-US001-032 — Invalid state transition: replay stale refId, 409 or error
- **AC:** AC-2a
- **Level:** api · **Type:** exception · **Technique:** ST · **Priority:** P1
- **Basis ref:** `test_basis.md#post-dipchip-v3`
- **Preconditions:** Valid BaaS headers. SIT VPN connected. A previously completed (state 0000) dipchip request with known refId.
- **Test data:** Stale refId from prior successful submission; information.evidencePhoto = base64-encoded valid JPEG ~100 KB
- **Steps:**

  1. POST /orch/api/v1/dipchip with valid BaaS headers, attempting to reuse/replay a stale request context

     **Expected [CP1]:** HTTP 409 or documented error (cannot re-process without a new request)

     **Basis:** `test_basis.md#post-dipchip-v3`

- **Postcondition:** no new record created; no photo overwritten
- **Automatable:** Y · **Automation ID:** E2E-REQ001-US001-032 · **Env scope:** sit
- **Notes:** C3; exact error body depends on BQ1

## Spec change log

No revisions — initial draft preview.
