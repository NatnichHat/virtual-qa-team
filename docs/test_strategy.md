# Test Strategy

> **Project-supplied.** `/init` drafts it from your answers; a human owns it thereafter.
> Every agent reads this to know what is in scope and what "done" means.
> Anything not stated here is NOT in scope — silence is a decision, not an omission.

## Mission

Provide independent, evidence-based verification that the **Dip Chip eKYC** system correctly
implements the business requirements (Dip Chip registration, DOPA integration, biometric checks,
AML screening, customer flag management) — protecting the bank from onboarding fraudulent customers
through the eKYC channel. The test effort exists for the **EKYC platform team** (system owner) and
the **QA function** (independent verification). We do not build the system; we prove whether it
behaves as specified, and file defects when it does not.

## System under test
- **Name / owner team:** **Dip Chip eKYC** / EKYC platform team
- **We do NOT own its source code.** Failures are triaged, not fixed here — see `.claude/refs/triage-protocol.md`.
- **Documentation available:**
  - Business Requirements (Dip Chip, DOPA, Biometric, AML, CustFlag):
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/3702784282/Business+Requirements
  - KYC Score Calculation Guide + e-KYC overview:
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/5795578000/KYC+Score+Calculation+Guide+New+KYC+V3+and+Overview+of+e-KYC+System
  - Dip Chip V2 Overview (architecture & flow):
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/3769696998/Dip+Chip+V2+Overview
  - Response Codes for DOPA Dipchip:
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/3740667625/Response+Code+for+DOPA+Dipchip
  - Dip Chip V1 API spec (POST /api/registration/v1/dipchip-service/dipchip):
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/6190366768/Dipchip+V1
  - Biometric & Face API specs:
    https://ktbinnovation.atlassian.net/wiki/spaces/IP2/pages/3112274426/ekyc-biometrics-face-api
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/5514855214/Public+Spec+Inquiry+Result+orch+api+v1+biometric+face+compare+result
    https://ktbinnovation.atlassian.net/wiki/spaces/EPTEAM/pages/5514855196/Public+spec+of+orch+api+v1+channel+biometric+face+get+live-type
  - Source code (PENDING access): GitLab https://gitdev.devops.krungthai.com/ — holds service source
    + Swagger/OpenAPI YAML. QA does not yet have access to Kustomize/service configurations; can be
    requested from the platform lead. Useful for D1 triage corroboration, not blocking for test design.
- **Access:** SIT only, via bank VPN (https://vpn.krungthai.com/staff). No local compose stack;
  `local` points at the SIT deployment. UAT access not yet granted. See `docs/env_matrix.md`.

## Levels in scope
| Level | In scope | Owner | Notes |
|---|---|---|---|
| API / Backend | **yes** | automation-engineer | RequestsLibrary, per-endpoint keywords. Primary test level — Dip Chip is API-centric. |
| UI / Browser | **no — out of scope** | — | System is API-only for this effort; no web UI for testers to cover. |
| DB verification | **yes (pending DB credentials)** | automation-engineer | Read-only assertions on side effects. Blocked until EKYC platform team provides read-only DB access for SIT. |
| Integration / third-party | **yes** | automation-engineer | Real third parties only (no WireMock — no local stack). DOPA, biometric, AML integrations. |
| Kafka verification | **no — deferred to test debt** | — | SIT Kafka topics exist (ccd.dipchipinfo.maintain.req.sit / .res.sit) but no observation tool is available. Deferred until tooling is provisioned. |
| Performance | **no — out of scope** | — | Not part of this QA effort. |
| Security | **no — out of scope** | — | Not part of this QA effort. |
| Accessibility | **no — out of scope** | — | Not part of this QA effort. |

## Test design approach
- Techniques are mandatory per `.claude/refs/test-design-techniques.md`, applied to a depth set by
  the story's **risk rating** (P1 = full technique set; P2 = EP + BVA + exception; P3 = happy path +
  primary negatives).
- Every exception category in `.claude/refs/exception-catalog.md` is either covered or explicitly
  declined with a recorded reason. Silence is not a decline.

## Coverage targets
See `docs/test_stack.md` → Coverage thresholds. In summary: **AC coverage 100%**, every other
dimension ≥90%, **automation coverage 90%** (of P1+P2 cases), measured against denominators a human
ratified at G2 *before* cases were written.

## Entry criteria (before test design starts)
- [ ] `docs/test_basis.md` exists and its rows for this REQ are `Confidence: confirmed` (G0 passed)
- [ ] User story provided with acceptance criteria; `story_analysis.md` has zero open testability defects (G1 passed)
- [ ] Environment reachable and credentials provisioned for at least one environment
- [ ] Bank VPN connection established (https://vpn.krungthai.com/staff) — hard prerequisite for SIT access

## Exit criteria (before sign-off)
- [ ] Every coverage dimension meets its threshold
- [ ] Zero test cases in `Not Run`; zero skipped tests in the run (a skip is a failure, never a neutral)
- [ ] 3 consecutive green rounds with a reseed before each
- [ ] Every failure has a Triage Record with a class and ≥2 pieces of evidence, approved at G7
- [ ] Every D1 has a defect ticket raised in Jira project **EKC** with the SUT team
- [ ] Test report's commit SHA equals current HEAD
- [ ] No `<TBD>` or placeholder text left in any artifact for this REQ

## Risk rating scale
| Rating | Meaning | Technique depth |
|---|---|---|
| P1 | money, data loss, auth/authz, regulatory, or irreversible action — eKYC-specific: identity fraud, AML bypass, DOPA mismatch, biometric spoofing | full technique set, all exception categories |
| P2 | core business flow, high usage — e.g. successful dip chip registration, inquiry response | EP + BVA + decision table + exception catalog |
| P3 | supporting/rare flow, cosmetic — e.g. edge-case response codes, logging behaviour | happy path + primary negatives |

## Out of scope

The following are **explicitly not part of this test effort**. They are as load-bearing as the goals —
if a stakeholder asks "why didn't you test X?", the answer is "it is in the out-of-scope list in
`test_strategy.md`":

- **UI / Browser testing** — the system under test for this effort is API-only; no web UI is in scope
  for the QA team to cover. If a UI is later introduced, this strategy must be reopened.
- **Performance / load / stress testing** — not part of this QA effort. Separate tooling and scope.
- **Security / penetration testing** — not part of this QA effort. Handled by the bank's security team.
- **Accessibility testing** — not applicable to an API-only system.
- **Kafka verification** — SIT Kafka topics exist but no observation tool is currently available.
  Deferred to test debt until tooling (Kafka UI, kcat, or Confluent Control Center) is provisioned.
- **UAT environment** — no access currently. UAT testing is deferred until access is granted by the
  EKYC platform team.
- **Direct database writes / seed infrastructure** — no seed infrastructure exists; destructive cases
  are blocked on all environments (shared infrastructure).
- **Local compose stack** — no local stack exists. `local` points at the SIT deployment.
- **Source code review** — QA does not currently have access to Kustomize/service configurations on
  GitLab. Test basis comes from Confluence documentation. Source code access is pending and useful
  only for D1 triage corroboration, not for test design.
