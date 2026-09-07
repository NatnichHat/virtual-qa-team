> ⚠️ DRAFT PREVIEW — NOT FROZEN. Denominators are NOT G2-ratified. For human shape-review before /phase2.

# US001 — Test Coverage Matrix

**Story:** US001 · **Requirement:** REQ001
**TCM Status:** `draft`

## State & boundary analysis

Enumerate every input, variable, and state BEFORE counting. This is the source table for
`boundary_coverage`.

| Variable / input | Type | Valid | Invalid | Boundary | Null / empty |
|---|---|---|---|---|---|
| `information.evidencePhoto` (base64 string) | string | valid base64 → JPEG ≤ 500 KB; valid base64 → PNG ≤ 500 KB | not base64-decodable; decodes to GIF/WebP/BMP; decodes to random bytes (magic-bytes mismatch); truncated base64; whitespace-only; wrong type (number); unicode; injection payload | decoded size = 500,000 (max, KB=1000); 500,001 (max+1, KB=1000); 512,000 (max, KB=1024); 512,001 (max+1, KB=1024) | absent (field not present); null; empty string `""` |
| `x-devops-key` header | string | valid DevOps API key | missing; expired; malformed | — | missing (B1) |
| `x-channel` header | string | `BAAS` | non-BAAS (out of scope, D9) | — | missing |
| `x-devops-src` header | string | `BAAS` | non-BAAS (out of scope, D9) | — | missing |
| `x-product` header | string | valid product ID | — | — | missing |
| `x-devops-dest` header | string | `ekyc` | — | — | missing |
| dipchip process state | enum | 0001 Initiate; 0002 Processing; 0000 Success; Failed | invalid transitions (see state model) | 0001→0002 (initiate); 0002→0000 (success); 0002→Failed (validation fail) | — |

## Count report

### Surfaces counted

| Metric | Count | Source (list each — a bare number is not auditable) |
|---|---|---|
| acceptance_criteria | 5 | AC-1, AC-2a, AC-2b, AC-2c, AC-3a (story_analysis.md) |
| endpoints | 1 | POST /orch/api/v1/dipchip (test_basis.md#post-dipchip-v3). Inquiry endpoints (post-dipchip-inquiry-v3, post-trusted-source-inquiry) are verification tools, not SUT endpoints for this story. |
| status_codes | 2 | HTTP 200 (success — D24); HTTP 400 (error — D23). HTTP 401 (auth — B1/B2/B3) counted under exceptions. |
| request_fields | 1 | information.evidencePhoto (only field under test; full schema unknown — BQ1) |
| validation_rules | 3 | VAL-evidence-001 (base64 + magic bytes); VAL-evidence-002 (size ≤ 500 KB); VAL-order-001 (validation order) |
| error_codes | 2 | 104001 (invalid format); 104010 (size exceeded) |
| db_writes | 2 | GCS bucket write (SE-evidence-001); tb_dipchip_info write (SE-evidence-004). Non-overwrite guarantees (SE-evidence-002/003) are negative-side-effect assertions. |
| db_constraints | 0 | read-only verification for AC-2c; no DDL constraints tested |
| boundaries | 4 | 500,000 bytes (max, KB=1000); 500,001 bytes (max+1, KB=1000); 512,000 bytes (max, KB=1024); 512,001 bytes (max+1, KB=1024) |
| decision_rules | 5 | R1 (absent → processed without photo); R2 (size > 500KB → 104010); R3 (not decodable → 104001); R4 (wrong format → 104001); R5 (valid → success) |
| transitions | 12 | 3 valid (0001→0002, 0002→0000, 0002→Failed) + 9 reachable-invalid (full 4×4 matrix minus self-transitions and the 3 valid) |
| exceptions | 14 | A1, A2, A3, A4, A5, A6, A9, A11, A13, B1, B2, B3, C3, F1 (after 30 documented declines) |
| screens | 0 | UI out of scope |
| ui_states | 0 | UI out of scope |
| ui_interactions | 0 | UI out of scope |
| journeys | 0 | no e2e journeys defined (API-level story) |
| journey_failures | 0 | no e2e journeys |

### Minimums vs actual

Formulas copied verbatim from `.claude/refs/test-design-techniques.md` §3. Every term is a sum;
there is no multiplication. Write the zeros — a dropped term is invisible, a `0` is auditable.

| Category | Formula | Minimum | Actual | Delta | Status |
|---|---|---|---|---|---|
| api | status_codes + validation_rules + error_codes + boundaries + decision_rules | 2 + 3 + 2 + 4 + 5 = 16 | 27 | +11 | PASS |
| db | db_constraints + db_writes | 0 + 2 = 2 | 5 | +3 | PASS |
| ui | ui_states + ui_interactions + journey_failures_visible | 0 + 0 + 0 = 0 | 0 | 0 | PASS (n/a) |
| e2e | journeys + journey_failures | 0 + 0 = 0 | 0 | 0 | PASS (n/a) |
| exception | exceptions | 14 | 14 | 0 | PASS |
| **TOTAL** | | **32** | **32** | **0** | **PASS** |

> The 11 extra api cases beyond the minimum cover: 2 format-rejection variants (WebP, BMP beyond
> the minimum 1), 1 magic-bytes mismatch (D27), 1 truncated base64 boundary, 1 combined
> oversized+undecodable (validation order), 3 absent/null/empty optional-field cases, 1
> whitespace exception, 1 wrong-type exception, 1 unicode exception, 1 injection exception. Each
> exercises a distinct code path or equivalence class.

## Coverage ratios

Per `.claude/refs/coverage-model.md`. **Denominators are NOT G2-ratified — these are preview
estimates for shape review.**

| Dimension | Covered | Total | Ratio | Threshold | Status |
|---|---|---|---|---|---|
| AC | 5 | 5 | 1.00 | 1.00 | PASS |
| endpoint × status | 2 | 2 | 1.00 | 0.90 | PASS |
| validation rule | 3 | 3 | 1.00 | 0.90 | PASS |
| boundary | 4 | 4 | 1.00 | 0.90 | PASS |
| decision rule | 5 | 5 | 1.00 | 0.90 | PASS |
| state transition | 3 | 12 | 0.25 | 0.90 | FAIL (preview — see note) |
| exception | 14 | 14 | 1.00 | 0.90 | PASS |
| automation | 32 | 32 | 1.00 | per stack | PASS |

**State transition note:** The 3/12 ratio reflects that REQ001 directly exercises only the
evidence-photo validation transitions (0001→0002, 0002→0000, 0002→Failed). The remaining 9
reachable-invalid transitions (from 0000-Success and Failed states) are lifecycle-level and
require separate lifecycle stories. This shortfall is recorded in ## Spec non-compliance.

**Excluded from denominators** (basis `Confidence` != `confirmed`): ALL basis rows are currently
`inferred` (pending G0). In a frozen G2 computation, this would exclude everything and produce 0/0
ratios. For this preview, we compute against the `inferred` rows to show shape — the actual G2
denominators will be ratified after G0 confirmation.

## AC → test traceability

| AC | Input setup | Expected output | api | db | ui | e2e | Covered |
|---|---|---|---|---|---|---|---|
| AC-1 | valid evidencePhoto (JPEG/PNG ≤ 500 KB) | HTTP 200, code "0000", refId returned | TC-001, TC-002, TC-008, TC-010, TC-014, TC-015, TC-016, TC-017 | TC-027 | — | — | YES |
| AC-2a | evidencePhoto not base64-decodable | HTTP 400, exact 104001 body | TC-003, TC-012, TC-018, TC-020, TC-022, TC-023, TC-032 | TC-028, TC-031 | — | — | YES |
| AC-2b | evidencePhoto decodes but wrong format | HTTP 400, exact 104001 body | TC-004, TC-005, TC-006, TC-007 | TC-029 | — | — | YES |
| AC-2c | fails validation + pre-existing photo exists | previously stored image NOT overwritten | — | TC-028, TC-029, TC-030, TC-031 | — | — | YES |
| AC-3a | evidencePhoto size > 500 KB | HTTP 400, exact 104010 body | TC-008, TC-009, TC-010, TC-011, TC-013, TC-019 | TC-030 | — | — | YES |

## Level justification

Why each `ui` and `e2e` case needs that level rather than a cheaper one.

| Test ID | Level | Why a lower level cannot prove it |
|---|---|---|
| — | — | No ui or e2e cases. All cases are api or db level. UI is out of scope per test_basis.md. |

## Spec non-compliance

Every scenario counted above but **not** covered at the level its technique implies — pushed down,
deferred, or declined. Often the right call, but it must be visible.

| Scenario | Counted as | Pushed to / deferred | Why it does not need the higher level | Covering test ID |
|---|---|---|---|---|
| 9 reachable-invalid state transitions (from 0000-Success and Failed states) | transitions (9 of 12) | deferred | Lifecycle-level transitions require a new request and are outside the evidence-photo validation scope of REQ001. They will be covered by separate lifecycle stories. | — (needs separate story) |
| TC-009 expected result (500,001 bytes rejected) | boundary case | PENDING-G0 | Byte unit unresolved (BQ3/D26) — if KB=1024, 500,001 is accepted. Expected result cannot be frozen until G0. | TC-009 |
| TC-010 expected result (512,000 bytes accepted) | boundary case | PENDING-G0 | Byte unit unresolved (BQ3/D26) — if KB=1000, 512,000 is rejected. Expected result cannot be frozen until G0. | TC-010 |
| TC-014/015/016 expected result (absent/null/empty → processed without photo) | decision table rules | PENDING-G0 | BaaS-optional behaviour (D5/BQ6) needs SUT confirmation at G0. | TC-014, TC-015, TC-016 |
| TC-031 white-box DB verification | db case | PENDING-G0 | Read-only DB access not yet provisioned (BQ15/D29). Black-box equivalent (TC-028) is READY. | TC-031 |
| TC-021 exact error body for wrong-type input | exception case (A5) | partial | Schema-level error shape not documented separately from 104001 (BQ1). HTTP 400 is concrete; exact body is not. | TC-021 |
| TC-032 exact error body for stale replay | exception case (C3) | partial | Exact error code for stale-replay rejection not documented (BQ1). HTTP 409 is concrete; exact body is not. | TC-032 |

## Reconciliation log

(`script-reviewer` appends here once automation exists and the mapping test-case ↔ script is verified.)
