# Environment Matrix

> Which environment can do what. `test-stack-init` drafts it at `/init`; a human owns it.
> **The G6 gate reads this file.** A test case whose `Env_Scope` includes an environment that
> cannot support its capability is a finding, caught before anything runs.

## The single mechanism that makes one script run everywhere

No keyword, page object, or test case file ever changes between environments. Three things do the work:

1. `tests/e2e/config/environment.yaml` — non-secret config per environment (tracked in git)
2. `tests/e2e/config/auth/.env.<env>` — secrets per environment (**gitignored**)
3. `${ENV}` — one Robot variable, default `local`, selected with `make e2e-run ENV=sit`

Every request goes through a **session alias** (`POST On Session  <alias>  ...`) created once by
`Prepare Session API`, which loops `${Environment}[${ENV}][api_config]`. The alias resolves to a
different URL per environment; the keyword never sees a URL. **A raw URL anywhere in a keyword is a
gate failure** — it is the one thing that would break portability.

## Critical prerequisite: Bank VPN

**All testing requires bank VPN connection**: https://vpn.krungthai.com/staff

Without VPN, none of the SIT endpoints are reachable. This is a hard blocker for any test execution.

## Capability matrix

| Capability | local | sit | uat | Notes |
|---|---|---|---|---|
| SUT reachable | yes (same as SIT) | yes | **no access** | `local` points at SIT deployment — no separate local stack |
| Bring stack up / tear down | **no** | **no** | **no** | no local compose stack; SIT/UAT are persistently deployed by EKYC platform team |
| WireMock (third-party stubs) | **no** | **no** | **no** | no local stack exists; all environments call real third parties |
| Direct DB access (verification) | **unknown** | **unknown** | **unknown** | DB credentials not provided; ask EKYC platform team |
| Seed / cleanup data | **no** | **no** | **no** | no seed infrastructure; destructive cases blocked on all shared environments |
| Destructive test cases | **blocked** | **blocked** | **blocked** | shared environments; `destructive`-tagged cases cannot run anywhere |
| Full regression run | yes | yes | **no** | UAT has no access; SIT is the primary regression target |
| Log/evidence access | yes (OpenSearch non-PRD) | yes (OpenSearch non-PRD) | **unknown** | OpenSearch non-PRD: https://logging-nonprd.gcp.ktbapp.tech/ |

## How "local" works when we do not own the SUT

**Decision recorded at /init**: `local` is a pointer at the SIT deployment (option (a) from the
skeleton's note). There is **no local compose stack**, no WireMock, and destructive cases are blocked
on all environments.

- `local` and `sit` use the **same URLs** — the only difference is the `${ENV}` variable value
- `environment.yaml` has identical `api_config` entries for both `local` and `sit`
- WireMock is **not available** anywhere — no local stack to run it
- Destructive cases are **blocked** on all environments (shared infrastructure)

## SIT Endpoints

All SIT endpoints require **bank VPN** (https://vpn.krungthai.com/staff).

### 1. Dip Chip Registration API
- **Purpose**: Main API for submitting dip chip registration data and ID card images
- **Method**: POST
- **External/Gateway URL**: https://api-dev.ekyc.nonprod.gcp.ktbcloud/api/registration/v1/dipchip-service/dipchip
- **Internal SIT URL**: https://10.249.78.250:443/api/registration/v1/dipchip-service/dipchip
- **Robot alias**: `dipchip_registration`

### 2. Dip Chip Orchestrator API (orch-dipchip)
- **Purpose**: Orchestration layer for dip chip operations
- **Method**: POST
- **Path**: /orch/api/v1/dipchip
- **Internal SIT URL**: https://10.249.78.180:443/orch/api/v1/dipchip
- **Robot alias**: `dipchip_orchestrator`

### 3. Dip Chip Inquiry API
- **Purpose**: Query dip chip information
- **Method**: POST
- **Paths**: 
  - /dipichip/v2/inquiry (note: typo in path is intentional — matches actual API)
  - /customer/v1/dipchip/inquiry
- **Internal SIT URL**: https://10.249.78.250:443/dipichip/v2/inquiry
- **Robot alias**: `dipchip_inquiry`

### 4. Kafka Topics (Maintain Dip Chip Info)
- **Request topic**: ccd.dipchipinfo.maintain.req.sit
- **Response topic**: ccd.dipchipinfo.maintain.res.sit
- **Status**: **Deferred to test debt** — no observation tool available (no Kafka UI, kcat, or Control Center)
- **Note**: Kafka verification is not covered by automation yet; will be added when tooling is available

## Infrastructure & Monitoring

### ArgoCD (SIT)
- **URL**: https://argocd-ekyc-dev.arisetech.dev/
- **Purpose**: View deployment status, application health

### OpenSearch Logging
- **Non-PRD (SIT/DEV)**: https://logging-nonprd.gcp.ktbapp.tech/
  - **This is the primary log/evidence source for QA triage**
- **PRD GCP**: https://logging-prd.gcp.ktbapp.tech/
- **PRD AWS**: https://logging-prd.aws.clicxapp.tech/app/login

**Usage in triage**: When a test fails, defect-analyst queries OpenSearch non-PRD logs to corroborate
whether the failure is D1 (real defect) vs D2 (test/script issue). Logs are the primary evidence source
since we do not have direct DB access or source code access.

## Per-environment detail

### local
- **Base URLs**: Same as SIT (see SIT Endpoints section above)
- **Credentials**: `tests/e2e/config/auth/.env.local`
- **Data policy**: Shared environment — same restrictions as SIT
- **Third parties**: Real (no WireMock available)
- **Notes**: `local` is just a naming convention; it points at the SIT deployment

### sit
- **Base URLs**: See SIT Endpoints section above
- **Credentials**: `tests/e2e/config/auth/.env.sit`
- **Data policy**: Shared environment — destructive cases blocked; use idempotent operations only
- **Third parties**: Real (no WireMock available)
- **Cleanup**: Manual cleanup via `make e2e-seed-down ENV=sit` (when seed infrastructure exists)
- **VPN required**: Yes — https://vpn.krungthai.com/staff

### uat
- **Base URLs**: <TBD — no UAT access currently>
- **Credentials**: `tests/e2e/config/auth/.env.uat`
- **Data policy**: <TBD — no UAT access currently>
- **Third parties**: <TBD — no UAT access currently>
- **Cleanup**: <TBD — no UAT access currently>
- **Status**: No access — UAT testing deferred until access is granted

## Direct Database Access

**Status**: <TBD — not provided>

DB credentials have not been provided by the EKYC platform team. Direct database verification
(`level:db` test cases) is **blocked** until:
1. DB credentials are provided (host, port, database name, read-only user)
2. Credentials are added to `tests/e2e/config/auth/.env.<env>` (gitignored)
3. `environment.yaml` is updated with the `database` block

**Action required**: Ask EKYC platform team for read-only DB access for SIT.

## Source Code Access

**Status**: PENDING

GitLab repository: https://gitdev.devops.krungthai.com/
- Holds service source code + Swagger/OpenAPI YAML
- QA does **not** currently have access to Kustomize/service configurations
- Access can be requested from the platform lead

**Usage**: Source code access is useful for D1 triage corroboration (understanding implementation
details), but is **not blocking** for test design or execution. Test basis comes from Confluence
documentation, not source code.

## Secrets

`tests/e2e/config/auth/.env.<env>` is gitignored. Commit `tests/e2e/config/auth/.env.example` with
every key present and every value blank, so a new machine knows what to fill in. A credential
inlined in `environment.yaml` is a gate failure, caught at script review (G5).

**Required secrets per environment**:
- API authentication tokens/credentials
- DB credentials (when provided)
- Any service-specific API keys
