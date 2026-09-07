# US001 — [BaaS] Enhance dipchip V3 validation logic: check image evidence photo base 64

**Requirement:** REQ001
**Status:** draft
**Source:** [EKC-8204](https://ktbinnovation.atlassian.net/browse/EKC-8204) — fetched 2026-09-04T08:36:01Z — Jira status at fetch time: EKC UNRELEASE — reporter: Jirasak Pipatwarakul

> Imported by `scripts/import/fetch-jira.py`, a mechanical transcription tool — not an agent.
> Nothing below was invented. Sections the tool could not confidently place are under
> `## Needs human review`. **This file is still human-owned from here — edit it freely, and it
> still goes through `story-analyst` and gate G1 like any other story.**

## Story
As the **eKYC Platform team**, I want the dipchip V3 process to validate the **evidence photo**
received from the BaaS channel — the photo must decode from base64 and convert back into a valid
image — so that when the image validation is incomplete, the dipchip process is marked as
unsuccessful instead of being accepted with a broken image.

## Acceptance criteria

- **AC-1** (happy path): **Given** a dipchip V3 request from source BaaS containing an
  evidencePhoto that decodes from base64 and converts back into an image, **When** the dipchip
  process runs, **Then** processing continues and the Dip Chip is considered successful.
- **AC-2** (invalid image): **Given** a dipchip V3 request whose evidencePhoto cannot be decoded
  from base64 or cannot be converted back into an image, **When** the dipchip process runs,
  **Then** the response is Dip Chip Fail with exactly
  `{ "code": "104001", "message": "Request is invalid format", "description": "image is invalid format" }`,
  **And** the previously stored image is NOT overwritten.
- **AC-3** (size exceeded): **Given** a dipchip V3 request whose evidencePhoto size is greater
  than 500 KB, **When** the dipchip process runs, **Then** the response contains exactly the
  TO-BE payload (the AS-IS response had no `description` field):
  ```json
  {
    "code": "104010",
    "message": "Image size exceeded",
    "description": "evidencePhoto size exceeded"
  }
  ```

## Out of scope
- Not stated in EKC-8204 — confirm with the BA/PO whether dipchip V1/V2 flows and non-BaaS
  sources are explicitly excluded, at G1.

## Dependencies
- **EKC-8138** ([KTB][Incident] Enhance dipchip image validation logic: check image) — the
  predecessor ticket that surfaced the evidence-photo gap in dipchip V3.
- **BaaS channel** — the only source in scope per Main Flow step 1.
- Existing stored evidence photo — AC-2 requires the original image to survive a failed
  validation, so a pre-existing record is a precondition for that path.

## Open points to clarify (flagged during import — for BA/PO, do NOT guess)

Raised in pre-analysis review; to be resolved via story-analyst's open questions at G1:

1. **500 KB boundary** — is exactly 500 KB accepted or rejected? Is "KB" 1,000 bytes or 1,024
   bytes (500,000 vs 512,000)?
2. **HTTP status codes** — do the 104001 / 104010 bodies come with HTTP 400, or HTTP 200 with a
   business-error code?
3. **Missing vs malformed evidencePhoto** — does an absent key, `null`, or `""` (empty string)
   follow the AC-2 error path (104001), or is the field optional?
4. **Supported image formats** — which formats count as "convertible back into an image"
   (JPEG / PNG / WebP / any)?

## Story (imported)
Raw text from the Jira description, converted from wiki markup to Markdown. This is the source
material for every section above — kept here in full so nothing from the original ticket is lost.

**As a** eKYC Platform,
**I want to** enhance dipchip V3 additional validation logic to check image evidence photo,
**So that** if validation image incomplete, the dipchip process will be marked as unsuccessful.

----

+**Objective:**+ 

- ต่อเนื่องจาก [https://ktbinnovation.atlassian.net/browse/EKC-8138|https://ktbinnovation.atlassian.net/browse/EKC-8138|smart-link]  พบว่า dipchip V3 สามารถส่งรูป evidence photo ได้จึงเพิ่มการตรวจสอบรูปที่ส่งมาจาก evidence photo 



+**Main Flow:**+

1. Source: รองรับ *BaaS*
1. เพิ่มการตรวจสอบรูป *evidence photo*  ต้องสามารถ decode base 64 ได้ + สามารถ convert กลับมาเป็น Image ได้
1. กรณีตรวจสอบสำเร็จ : ให้ทำงานต่อ ถือว่า Dip Chip สำเร็จ
1. กรณีตรวจสอบ+ไม่+สำเร็จ : Response Dip Chip Fail และไม่ Save รูปทับรูปเดิม
{noformat}{
 "code": "104001",
 "message": "Request is invalid format",
 "description": "image is invalid format"
}{noformat}
1. กรณีที่ evidencePhoto size มากกว่า 500 KB (เพิ่ม description เพื่อให้สื่อขึ้น)
{color:#ff5630}**AS-IS:**{color}    { code: "104010", message: "Image size exceeded" }
{color:#36b37e}**TO-BE:** {color}  { code: "104010", message: "Image size exceeded", description: "evidencePhoto size exceeded" }  



**Acceptance Criteria: ​**

- รูป evidence photo ที่ไม่สามารถ decode base 64 หรือ ไม่สามารถ convert กลับมาเป็น Imageได้ จะถูกตี Error และไม่ Save รูปทับรูปเดิม
