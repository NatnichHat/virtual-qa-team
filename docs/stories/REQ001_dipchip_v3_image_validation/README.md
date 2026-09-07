# REQ001 — [BaaS] Enhance dipchip V3 validation logic: check image evidence photo base 64

**Summary:** Enhance the dipchip V3 validation logic (BaaS channel) to check the evidence photo
before accepting it: the photo must decode from base64 and convert back into a valid image, and
oversized photos (>500 KB) get a clearer error description. Failed validation must fail the
dipchip process without overwriting the previously stored image. Continues the image-validation
work from EKC-8138. Source: [EKC-8204](https://ktbinnovation.atlassian.net/browse/EKC-8204).

## Stories
- [US001](US001_dipchip_v3_image_validation.md) — [BaaS] Enhance dipchip V3 validation logic: check image evidence photo base 64

## Decisions confirmed by the user (locked)

Confirmed by Natnicha (QA) on 2026-09-04 during the /phase1 grill pass:

- **D1 (Q1 — non-overwrite observability):** ~~request DB read-only access~~ **CORRECTED by D15:**
  request **object-storage read access** from the EKYC platform team to prove "stored image NOT
  overwritten" (AC-2c) — the evidence photo lives in object storage, not a DB table. Pending —
  until granted, AC-2c cannot be tested at any level.
- **D2 (Q2 — HTTP status):** error codes 104001 and 104010 return **HTTP 400 Bad Request**.
- **D3 (Q3 — 500 KB boundary):** exactly 500 KB is **accepted** (rule is size ≤ 500 KB passes).
  Byte-unit (1,000 vs 1,024) still needs SUT confirmation — folded into BQ3.
- **D4 (Q4 — size measurement):** size is measured on **decoded image bytes**, not the base64
  string length.
- **D5 (Q5 — missing/null/empty evidencePhoto):** the field is **optional** — absent / null /
  empty string does NOT follow the 104001 error path; the request is processed without a photo.
  (QA to confirm this against the SUT implementation at G0 — it is a behaviour claim, BQ6.)
- **D6 (Q6 — supported image formats):** **JPEG and PNG only.** WebP/GIF/BMP and other formats
  are rejected as "cannot convert back into an image" (104001).
- **D7 (Q7 — validation precedence):** size is checked **first** — an image that is BOTH
  oversized (>500 KB) and undecodable returns **104010**, not 104001.
- **D8 (Q8 — error response shape):** the error JSON `{code, message, description}` **is the
  complete HTTP response body** — not nested inside a larger object. "Exactly" assertions may
  be written against the body.
- **D9 (Q9 — source scope):** the evidence-photo validation applies to **source BaaS only**.
  dipchip V1/V2 flows and non-BaaS channels are out of scope for REQ001.
- **D10 (Q10 — non-overwrite on 104010):** the "do NOT overwrite the stored image" guarantee
  applies to the **size-exceeded path too** — both failure paths preserve the existing photo.
- **D11 (Q11 — assertion strength):** all error-response assertions are **exact body matches**
  (every field, no subset matching) for both 104001 and 104010.
- **D12 (Q12 — success response shape):** PENDING — QA has the answer and will supply the
  success HTTP status + response body; fold into test_basis.md (BQ11) on receipt.
- **D13 (BQ3 — byte unit of "500 KB"):** UNRESOLVED — deferred to the SUT team at G0
  (500,000 vs 512,000 bytes). Blocks boundary test-data construction for AC-3a.
- **D14 (BQ13 — authentication):** the dipchip API on SIT uses a **Bearer token / API key**.
  QA must obtain the SIT credential from the EKYC platform team before /phase5.
- **D15 (BQ15 — storage location):** the evidence photo is stored in **object storage, not a
  database**. The access request in D1 is therefore for object-storage read access; `level:db`
  cases for AC-2c become `level:integration`-style storage assertions (mechanism to be confirmed
  with the SUT team — which bucket/service, and how QA reads it).
- **D16 (BQ14 — feature flag):** **no feature flag** — the EKC-8204 validation logic is always
  active once deployed. (Note: the ticket status is UNRELEASE; QA must confirm with the SUT team
  that the build under test in SIT actually contains EKC-8204 before /phase5, or every new-path
  test fails as D5.)

Confluence facts retrieved via Atlassian Rovo on 2026-09-07 (sources: EPTEAM pages 6190366768,
4605837537, 3702784282; Jira EKC-8204/8208/8138/8209/8216/8217). These are DOCUMENTATION-backed
but still `inferred` — Rovo is not the SUT team; the Wednesday sync (G0) must confirm each one.

- **D17 (endpoint identity — CORRECTION):** Dipchip **V3 = `POST /orch/api/v1/dipchip`**
  (orchestrator). `/api/registration/v1/dipchip-service/dipchip` is **V1** and has no
  evidencePhoto field. The basis originally anchored the wrong endpoint — corrected 2026-09-07.
- **D18 (channel/source transport):** V3 identifies the channel via **request headers** —
  `x-channel: BAAS` (and/or `x-devops-src: BAAS`), plus `x-product`, `x-devops-dest: ekyc`.
  Auth header is **`x-devops-key`** (DevOps API key) — refines D14; the SIT credential VALUE is
  still to be obtained. (V1 differs: `channel`/`product` are body fields.)
- **D19 (photo field location):** evidencePhoto is **nested at `information.evidencePhoto`**
  (base64 string), conditional/optional — mandatory only for specific channels (e.g. AIS),
  optional for BaaS. Corroborates D5.
- **D20 (success response — partial):** HTTP 200 with `code: "0000"`. Two documented shapes
  (V1-sync full data object; async `{code, message, description, data:{refId}}`) — **which one
  V3/BaaS returns is unresolved** → Wednesday question; happy-path expectations stay PENDING.
  (Supersedes the "QA will supply" note in D12 with documented candidates.)
- **D21 (storage architecture — BQ15 closed on architecture):** images live in **Object Storage
  (GCS bucket / "Image Vault")**; the relational DB stores only an `imagePath` reference.
  AC-2c verification therefore needs **both** object-storage read access **and** read-only DB
  access (to prove imagePath unchanged) — updates the D1 access request.
- **D22 (corroborations of earlier decisions):** size-check-first fail-fast (D7 ✓ Confluence),
  JPEG+PNG only via standard eKYC image-validation library (D6 ✓), BaaS/V3-only scope (D9 ✓),
  never overwrite stored image on any failure (D10 ✓), flat exact error JSON (D8 ✓).
  Still open: HTTP status for 104001/104010 (Confluence silent — D2 remains QA-asserted),
  500 KB byte unit (BQ3), Kong/gateway total body limit (BQ1), exact x-channel vs x-devops-src
  requirement (BQ12 reframed).

Second Rovo batch retrieved 2026-09-07 (additional sources: EPTEAM pages 3740667625 "Response Code
for DOPA & Dipchip", 3769696998 "Dip Chip (V2) Overview", 3676995762 "CID Dipchip Service",
3731357957 "Welfare Registration"; GoofyDisco page 5633901389; Jira EKC-8208 DONE). This closes
most of D22's "still open" list. Same rule: DOCUMENTATION-backed, still `inferred` until G0.

- **D23 (HTTP status — RESOLVED by docs):** 104001 AND 104010 both return **HTTP 400 Bad
  Request**. Corroborates D2; source is the Response Code page + EKC-8208 (DONE), not QA assertion
  anymore. G0 ratifies.
- **D24 (V3 success shape — RESOLVED by docs):** Dipchip **V3 is asynchronous** — HTTP 200 with
  `{ "code": "0000", "message": "Transaction Success", "description": "", "data": { "refId":
  "<uuid>" } }`. The V1-style sync full-data object is NOT what V3 returns. Resolves D20's open
  point; AC-1's expected result can now be written concretely (still G0-pending).
- **D25 (total payload limit):** evidencePhoto ≤ 500 KB; the total request body limit is **not
  defined in the API document** — governed by the API gateway / Kong (typically 10–20 MB). Any
  total-body-limit boundary case stays `assumed` until G0.
- **D26 (BQ3 byte unit — narrowed, NOT closed):** docs indicate common validation libraries compute
  1 KB = 1,024 bytes (**512,000 bytes**) on the decoded binary stream or base64 length × 3/4.
  Rovo's recommendation: **boundary-test BOTH 500,000 and 512,000 bytes** until the SUT team
  confirms which. D13/BQ3 stays open for G0 with a concrete test strategy attached.
- **D27 (validation order — full detail):** header & required-schema check → **image size
  (fail-fast, checked BEFORE decoding to avoid memory overhead → 104010)** → base64 decodability +
  **magic bytes** / format check (JPEG+PNG only via the eKYC central common image-validation
  module; GIF, WebP, BMP rejected → 104001) → DOPA. Corroborates D7; pins "convert back into an
  image" = magic-bytes/format detection for AC-2b.
- **D28 (BQ16 lifecycle states — RESOLVED by docs):** `0001 Initiate` (refId generated) →
  `0002 Processing` (image validation + DOPA) → `0000 Success` (record written to
  `tb_dipchip_info`; photo uploaded to bucket `dipchip-image-ktbgov-uat`; Master Vault
  trusted-source flag set; Kafka event `cdi.dipchip.maintain.req` emitted) OR
  `104xxx/102xxx/105xxx Failed` (error returned; existing images in Storage/Vault NEVER
  overwritten). Supersedes the basis's minimal inferred 3-state model.
- **D29 (AC-2c observation channels — MAJOR UNBLOCK):** non-overwrite is observable **black-box
  via API**: `POST /orch/api/v1/dipchip-inquiry` (or `/customer/v1/dipchip/inquiry`) by citizenId
  or refId, and `POST /customer/v1/biometric/trusted-source-image/inquiry` for the active vault
  image. Object-storage/DB access is therefore NO LONGER A HARD BLOCKER for AC-2c. White-box
  alternative: query `tb_dipchip_info` by `citizen_id_hashed` — negative tests must show previous
  timestamps and `imagePath` completely untouched. Tables: `tb_dipchip_info` (active),
  `tb_dipchip_info_history` (history); DB stores only metadata + `imagePath`, never binary.
- **D30 (headers — detail):** `x-devops-src: BAAS` (also VB/ATM/EDC) is documented alongside
  `x-channel: BAAS`, plus `x-product`, `x-devops-dest: ekyc`, auth `x-devops-key`. The exact
  mandatory combination for BaaS still needs G0 confirmation.
