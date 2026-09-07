# US001 — Story analysis

**Story:** `docs/stories/REQ001_dipchip_v3_image_validation/US001_dipchip_v3_image_validation.md` (human-supplied — never edited by an agent)
**Requirement:** REQ001
**Status:** `pending_approval`

## Atomic acceptance criteria

Each row is ONE testable assertion. A criterion containing "and", "or", or two outcomes is split
until each row can be proven true or false on its own. **This table is the denominator for
`ac_coverage`** — splitting badly here distorts every downstream number.

| AC ID | Given | When | Then | Observable at | Risk |
|---|---|---|---|---|---|
| AC-1 | a dipchip V3 request from source BaaS containing an evidencePhoto that decodes from base64 AND converts back into a valid image | the dipchip process runs | processing continues and the Dip Chip is considered successful (non-error response) | api | P2 |
| AC-2a | a dipchip V3 request whose evidencePhoto cannot be decoded from base64 | the dipchip process runs | the response is Dip Chip Fail with exactly `{ "code": "104001", "message": "Request is invalid format", "description": "image is invalid format" }` | api | P1 |
| AC-2b | a dipchip V3 request whose evidencePhoto decodes from base64 but cannot be converted back into an image | the dipchip process runs | the response is Dip Chip Fail with exactly `{ "code": "104001", "message": "Request is invalid format", "description": "image is invalid format" }` | api | P1 |
| AC-2c | a dipchip V3 request whose evidencePhoto fails image validation (cannot decode OR cannot convert) AND a previously stored evidence photo exists for the same record | the dipchip process runs | the previously stored image is NOT overwritten | db | P1 |
| AC-3a | a dipchip V3 request whose evidencePhoto size is greater than 500 KB | the dipchip process runs | the response contains exactly `{ "code": "104010", "message": "Image size exceeded", "description": "evidencePhoto size exceeded" }` | api | P2 |

- **Observable at** — the lowest level where this outcome is genuinely visible. `test-planner` uses
  it to assign levels; getting it wrong pushes cases up the pyramid where they are slow and fragile.
- **Risk** — proposed by `story-analyst`, confirmed by `test-planner`, ratified at G2.

**Split rationale.** AC-2 was split on the "or" joining two distinct failure conditions (cannot
decode vs cannot convert) because they exercise different code paths (base64 decode vs image-format
detection) and are independently provable. The "NOT overwritten" outcome was split from the error
response because it is a different observable (db/storage vs api) with a different precondition
(an existing stored image must exist). AC-3 was not split — it has one outcome. AC-1 was not split
— the two Given conditions (decodes AND converts) are preconditions for one success outcome.

## Testability defects

Every reason a criterion cannot yet be turned into a test with a concrete expected result.
**G1 does not pass while any BLOCKING row is open.**

| # | AC | Defect | Severity | Question for BA/PO | Resolution |
|---|---|---|---|---|---|
| T1 | AC-2c | "Previously stored image is NOT overwritten" is not observable via API. `docs/test_strategy.md` states DB verification is "yes (pending DB credentials)" — read-only DB access is not yet provisioned. No retrieval endpoint (GET evidence photo) is documented in the story or basis. A test cannot prove non-overwrite without either DB/object-storage access or a retrieval endpoint. | BLOCKING | Q1 | |
| T2 | AC-2a, AC-2b, AC-3a | HTTP status code for the 104001 and 104010 error bodies is not stated. The JSON body is given but the HTTP status (400 Bad Request vs 200 with business-error code) is unknown. Every error test case's expected result is incomplete without it. [Story open point 2] | BLOCKING | Q2 | |
| T3 | AC-3a | The 500 KB boundary is undefined: is a photo of exactly 500 KB accepted or rejected? Additionally, "KB" is ambiguous — 1,000 bytes (decimal) or 1,024 bytes (binary), i.e. is the threshold 500,000 or 512,000 bytes? Boundary values cannot be determined. [Story open point 1] | BLOCKING | Q3 | |
| T4 | AC-2a | Behavior for missing/null/empty evidencePhoto is undefined. When the field is absent, `null`, or `""` (empty string), does the request follow the AC-2 error path (104001) or is the field optional and processed without it? [Story open point 3] | BLOCKING | Q5 | |
| T5 | AC-2b | "Convert back into an image" is undefined — which image formats are accepted (JPEG, PNG, WebP, GIF, BMP, any)? A test cannot construct a valid or invalid image without knowing the accepted formats. [Story open point 4] | BLOCKING | Q6 | |
| T6 | AC-3a | "evidencePhoto size" measurement basis is ambiguous. Is size measured as the length of the base64 string or the byte length of the decoded image? These differ by ~33% (base64 encoding overhead). A 500 KB limit produces different test data depending on which is measured. | BLOCKING | Q4 | |
| T7 | AC-2a, AC-3a | Validation precedence is unstated. When an evidencePhoto is BOTH invalid (cannot decode/convert) AND larger than 500 KB, which error is returned — 104001 (invalid format) or 104010 (size exceeded)? The expected result for a combined-failure input is unknown. | BLOCKING | Q7 | |
| T8 | AC-2a, AC-2b, AC-3a | Response shape is ambiguous. AC-2 says "the response is Dip Chip Fail with exactly { json }" — "Dip Chip Fail" implies a status field exists in the response, while "exactly" implies no other fields. Is the error JSON the complete HTTP response body, or is it nested inside a larger response object (e.g., `{ "status": "Fail", "error": { ... } }`)? An "exactly" assertion cannot be written without knowing the full shape. | BLOCKING | Q8 | |
| T9 | AC-2a, AC-2b, AC-2c, AC-3a | Source channel scope is ambiguous. AC-1 specifies "source BaaS" in its Given, but AC-2 and AC-3 do not. The Main Flow says "Source: รองรับ BaaS" (supports BaaS). Does the evidence-photo validation apply only to BaaS or to all source channels? The story's own Out-of-scope section flags this for BA/PO confirmation. | BLOCKING | Q9 | |
| T10 | AC-3a | The "NOT overwritten" guarantee is stated in AC-2 but omitted from AC-3. On the size-exceeded failure path, is the previously stored image also preserved, or does the size-exceeded path behave differently? The expected side-effect behavior is unstated for a failure path. | BLOCKING | Q10 | |
| T11 | AC-3a | Inconsistent assertion strength between ACs. AC-3 says the response "contains exactly" the 104010 JSON, while AC-2 says the response "is ... with exactly" the 104001 JSON. "Contains" is a weaker assertion (subset match) than "is" (exact match). It is unclear whether this is intentional. | MAJOR | Q11 | |
| T12 | AC-1 | The success outcome is not observable. "Processing continues and the Dip Chip is considered successful" does not specify what HTTP status or response body indicates success. A test cannot assert a concrete expected success response. | MAJOR | Q12 | |

Common defect kinds, all of which produce untestable cases if let through:
ambiguous quantities ("fast", "many", "recent") · missing error behaviour (happy path only) ·
no oracle (nothing states the correct value) · unstated preconditions · conflicts with another AC ·
behaviour the basis does not cover · implied but unstated permissions.

## Domain terms

Terms whose meaning must be pinned before anyone writes an expected result.

| Term | Meaning as used here | Source |
|---|---|---|
| evidencePhoto | The base64-encoded image field in the dipchip V3 request body (BaaS channel) | Story AC-1, Main Flow step 2 |
| decode from base64 | The evidencePhoto string can be successfully base64-decoded to a byte sequence | Story Main Flow step 2 |
| convert back into an image | The decoded bytes form a valid image in an accepted format (formats undefined — see T5) | Story Main Flow step 2; open question Q6 |
| Dip Chip Fail | The dipchip process outcome indicating failure; exact response shape ambiguous (see T8) | Story AC-2 |
| 500 KB | The maximum allowed evidencePhoto size; boundary and byte-unit definition undefined (see T3) | Story AC-3; open question Q3 |
| BaaS channel | The source channel for the dipchip V3 request; the only source named in scope | Story Main Flow step 1, AC-1 Given |
| previously stored image | The evidence photo already stored from a prior successful dipchip submission for the same record; required as a precondition for AC-2c | Story AC-2, Dependencies |

## Out of scope for this story
- dipchip V1/V2 flows — pending BA/PO confirmation (Q9); the story and its Out-of-scope section explicitly defer this
- non-BaaS source channels — pending BA/PO confirmation (Q9); only BaaS is named in the Main Flow
- image content validation (face detection, liveness, biometric quality) — only format decodability and size are in scope per the ACs
- performance/latency of the validation step — `docs/test_strategy.md` excludes performance testing
- concurrent submission handling for the same record — not addressed in the story
- the AS-IS → TO-BE change to the 104010 error description (adding `description` field) — this is an impact-analysis concern for existing tests, not a story-analysis defect

## Open questions for BA/PO
Numbered, highest-risk first. **The orchestrator asks the human — subagents cannot.**
Answers are recorded in the REQ README's `## Decisions confirmed by the user (locked)` section, G-numbered.

1. **[T1 — observability of non-overwrite]** How does a tester observe that the previously stored image was NOT overwritten? Is there a GET/retrieval endpoint that returns the stored evidence photo, or is DB/object-storage read access required? `docs/test_strategy.md` notes DB access is pending credentials. Without an observation path, AC-2c cannot be tested at any level.
2. **[T2 — HTTP status code]** What HTTP status code accompanies the 104001 and 104010 error bodies — HTTP 400 (Bad Request) or HTTP 200 with a business-error code in the body?
3. **[T3 — 500 KB boundary]** Is an evidencePhoto of exactly 500 KB accepted or rejected? And is "KB" 1,000 bytes (decimal) or 1,024 bytes (binary) — i.e., is the threshold 500,000 or 512,000 bytes?
4. **[T6 — size measurement basis]** Is "evidencePhoto size" measured as the length of the base64 string or the byte length of the decoded image? These differ by ~33%.
5. **[T7 — validation precedence]** When an evidencePhoto is BOTH invalid (cannot decode/convert) AND larger than 500 KB, which error takes precedence — 104001 (invalid format) or 104010 (size exceeded)? What is the validation order?
6. **[T4 — missing/null/empty field]** When the evidencePhoto field is absent, `null`, or `""` (empty string), does the request follow the AC-2 error path (104001 "image is invalid format"), or is the field optional and the request processed without it?
7. **[T5 — supported image formats]** Which image formats are accepted as "convertible back into an image" — JPEG, PNG, WebP, GIF, BMP, any? Which formats should be rejected?
8. **[T8 — response shape]** Is the error JSON `{ "code": ..., "message": ..., "description": ... }` the complete HTTP response body, or is it nested inside a larger response object (e.g., with a `"status": "Fail"` field)? What is the exact full response shape for both the 104001 and 104010 error cases?
9. **[T9 — source channel scope]** Does the evidence-photo validation apply only to requests from source BaaS, or to all source channels? AC-1 specifies "source BaaS" but AC-2 and AC-3 do not. Are dipchip V1/V2 flows in scope?
10. **[T10 — non-overwrite for size exceeded]** On the size-exceeded path (AC-3), is the previously stored image also NOT overwritten (same guarantee as AC-2), or does the size-exceeded path behave differently?
11. **[T11 — assertion strength]** AC-3 says the response "contains exactly" the 104010 JSON, while AC-2 says the response "is ... with exactly" the 104001 JSON. Is the assertion strength intentionally different, or should both be "the response body is exactly"?
12. **[T12 — success response shape]** What is the observable success response for AC-1? "Processing continues and the Dip Chip is considered successful" — what HTTP status and response body indicates success?
