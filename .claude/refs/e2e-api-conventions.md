# Shared ref — E2E / Robot Framework API conventions

Detailed how-to for the POM-style layout, the keyword-per-endpoint pattern, and the shared
assertion/seed conventions referenced by `docs/test_stack.md`'s `## Automation` fields. Read
directly by both **automation-engineer** (authoring/revising the scripts) and **script-reviewer**
(verifying them firsthand before G5) — same precedent as `.claude/refs/qa-templates.md`: this is
a shared reference doc, read via `Read`, not a `.claude/skills/` entry (subagents have no `Skill`
tool).

Adapted selectively from a real Robot Framework API project — the "Adopted vs rejected" section at
the bottom records what was deliberately left behind, so it doesn't get reintroduced later by
someone copying that project's habits.

## 1. Folder layout (POM-style, one deliberate single-file exception)

```
tests/e2e/
├── FEATURES.md                        ← catalog: feature names + `common` (reserved)
├── config/
│   ├── import.resource                ← single root Settings import — see §2
│   ├── environment.yaml               ← non-secret per-env config (local/sit/uat) — see §2
│   ├── auth/                          ← gitignored per-env secrets (.env.<env>) — see §2
│   ├── extend_scripts/                ← seed/cleanup scripts — see §6
│   └── wiremock/
│       └── mappings/                  ← WireMock stub mappings — see §7
├── keyword/
│   ├── common/                        ← reserved — cross-cutting keywords, one shared file
│   │   └── commons_keyword.resource   ← Prepare Test Data (§3) + assertions (§5), in sections
│   └── <feature>/                     ← per-feature, human-ratified via FEATURES.md
│       └── <feature>.resource
├── page/                               ← UI (Browser) projects only, same per-feature shape
│   ├── common/
│   └── <feature>/
├── test_data/
│   └── e2e_baseline.yaml              ← SINGLE file, project-wide (see §3 and the note below)
├── test_suites/
│   └── e2e_baseline.robot             ← SINGLE file, project-wide (see the note below)
└── test_results/
    └── <date>/
        └── <time>/                    ← gitignored Robot output trio per run
```

`keyword/<feature>/` and `page/<feature>/` are physically per-feature, exactly like the project's
existing "organize by feature" principle. `test_data/` and `test_suites/` are the **one deliberate
exception**: both are single project-wide files because they are direct 1:1 instantiations of
`docs/test_cases/TEST_BASELINE.md`, which is itself already the single project-wide index. Feature
identity inside those two files is a `feature:<name>` tag, not a folder.

## 2. `config/import.resource` — the single root import

Every file in `test_suites/e2e_baseline.robot` (and any keyword/page resource) gets its libraries,
variables, and keyword resources from one place:

```robot
*** Settings ***
Library      RequestsLibrary
Library      Browser         # only if this project has a UI surface
Variables    environment.yaml

*** Variables ***
${ENV}              local
${WEB_BASE_URL}      ${Environment}[${ENV}][web_base_url]

*** Settings ***
Resource    ../keyword/common/commons_keyword.resource
Resource    ../keyword/orders/orders.resource
Resource    ../keyword/auth/auth.resource
# ... one Resource line per keyword/<feature>/ actually in use
Variables   ../test_data/e2e_baseline.yaml
```

`test_suites/e2e_baseline.robot`'s own Settings section stays almost as short — one `Resource` line,
a `Suite Setup` that creates the API sessions once (below), and the existing `Test Setup` line that
wires in test data (§3):

```robot
*** Settings ***
Resource      ../config/import.resource
Suite Setup   common.Prepare Session API
Test Setup    common.Prepare Test Data
```

Adding a new feature's keyword resource means adding one `Resource` line to `import.resource` —
that file is the one place that "wires everything together," same role as the reference project's
own `config/import.resource`.

### `environment.yaml` and the `Prepare Session API` session-alias mechanism

`config/environment.yaml` is the one non-secret, per-environment config file, loaded above as a
`Variables` file (Robot Framework parses YAML natively — its root key `Environment:` becomes the
Robot variable `${Environment}`, a nested dict addressed as `${Environment}[<env>][...]`):

```yaml
Environment:
  local:
    api_config:
      api:
        name: local_api
        url: http://localhost:8080
        headers:
          Content-Type: application/json
    web_base_url: http://localhost:3000
    database:
      host: localhost
      port: 5432
      name: app_db
  sit:
    api_config:
      api:
        name: sit_api
        url: https://api-sit.example.internal
        headers:
          Content-Type: application/json
    web_base_url: https://app-sit.example.internal
    database:
      host: sit-db.example.internal
      port: 5432
      name: app_db
  uat:
    api_config:
      api:
        name: uat_api
        url: https://api-uat.example.internal
        headers:
          Content-Type: application/json
    web_base_url: https://app-uat.example.internal
    database:
      host: uat-db.example.internal
      port: 5432
      name: app_db
```

`${ENV}` (declared in `import.resource`, default `local`) picks which top-level key resolves. There
are two equivalent ways to point the whole suite at `sit`/`uat` — **neither ever touches a keyword,
page, or test-case file**:
- Pass `ENV=<env>` to `make e2e-seed`/`make e2e-run` (recommended — both commands take the same
  argument; `make e2e-run` forwards it as `robot --variable ENV:<env>`, which overrides the
  `${ENV}    local` default above).
- Hand-edit that one default line, for a bare `robot tests/e2e/` invocation without `make`.

One backend session alias per entry under `api_config` (`api` above; add more entries — `orders`,
`billing`, whatever — only if the project actually has multiple backend surfaces to call). A
`Prepare Session API` keyword, added to `keyword/common/commons_keyword.resource` and run once via
`Suite Setup` on `test_suites/e2e_baseline.robot`, turns each entry into a live `RequestsLibrary`
session:

```robot
# keyword/common/commons_keyword.resource
*** Keywords ***
Prepare Session API
    FOR    ${alias}    ${config}    IN    &{Environment}[${ENV}][api_config]
        Create Session    alias=${config}[name]    url=${config}[url]    headers=${config}[headers]
    END
```

Every endpoint keyword then calls `POST On Session    <alias>    /path    ...` (§4) — **never a raw
URL.** The alias (e.g. `api`) is a constant string across every environment; only the *session's*
underlying URL changes, resolved from `environment.yaml` via `${ENV}`. That's the whole mechanism
that makes keyword/test-case files identical across `local`/`sit`/`uat` — adapted directly from the
reference project's `Prepare Session API`/`${Api_Config}` pattern (§11).

**Secrets never go in this tracked file.** Sensitive header values (API keys) and DB credentials
load separately from a gitignored `tests/e2e/config/auth/.env.<env>` (already covered by the repo's
`.env.*` gitignore rule) — `environment.yaml` only ever holds URLs, session alias names, non-secret
header names, and DB host/port/name.

## 3. Test data — YAML via `Prepare Test Data`

Test data lives in **one project-wide YAML file**, `test_data/e2e_baseline.yaml` — the same
single-file exception as `test_suites/e2e_baseline.robot` (both are 1:1 instantiations of
`TEST_BASELINE.md`). One top-level key per test case name.

**The full data shape — `input_data`/`expected_data`, the `{core_feature}/{sub_feature}` nesting,
and the per-surface API/UI/database/bucket sections — is documented in the sibling file
`.claude/refs/e2e-test-data-conventions.md`.** This section only covers the lookup *mechanism*,
which is shape-agnostic: `config/import.resource` loads the YAML as a `Variables` file (Robot
Framework parses YAML natively — every top-level key becomes a variable), then the single suite
file's `Test Setup` (§2) calls this keyword before every test case:

```robot
# keyword/common/commons_keyword.resource — test-data section
*** Keywords ***
Prepare Test Data
    [Documentation]    Looks up this test's own block in test_data/e2e_baseline.yaml by matching
    ...                ${TEST_NAME} against the YAML's top-level keys (`${${TEST_NAME}}` is
    ...                Robot's nested-variable dereference: "the variable named by whatever
    ...                ${TEST_NAME} currently is"), then exposes it as ${Test_Data} for the rest
    ...                of the test.
    ${Test_Data}    Set Variable    ${${TEST_NAME}}
    Set Test Variable    ${Test_Data}
```

(The assertion keywords in §5 live in this same shared file, in their own section below this one.)

**Every test case name needs an exact-matching top-level key in the YAML.** `Test Setup` runs
unconditionally for every test case in the (single, project-wide) suite file — a missing key fails
that test with a variable-not-found error, not a silent skip.

**Access is bracket notation only, always: `${Test_Data}[key][subkey]...`** — never dot notation,
even though Robot's YAML-loaded dicts support both; one consistent style avoids the reader
wondering which applies where.

**Test cases extract and pass values explicitly — keywords never default their own arguments to
`${Test_Data}[...]`.** A test case reads e.g. `${Test_Data}[input_data][orders][create_order]
[body][customer_id]` (see `.claude/refs/e2e-test-data-conventions.md` for the exact nesting) and
passes it as a named argument to the keyword call (see §4); the keyword itself only ever sees
plain arguments, never reaches into `${Test_Data}` on its own. This keeps keywords data-agnostic
and matches the explicit `RETURN`-plus-argument philosophy below — a keyword's signature should
never be coupled to `${Test_Data}`'s exact shape.

## 4. Keyword-per-endpoint pattern

One keyword per API endpoint. It takes arguments to build the request body, calls the two
`e2e_assertion_helper` keywords (§5) internally — **both status and, when given expected data, the
full body diff** — and `RETURN`s the parsed response. Callers never call `POST On Session`/assert
status/assert body directly in a test case; verification lives entirely inside the keyword.

```robot
# keyword/orders/orders.resource
*** Keywords ***
Create Order
    [Documentation]    POST /v1/orders (session alias: api — see §2's Prepare Session API)
    [Arguments]    ${customer_id}    ${items}    ${expected_status}=201    ${expected_body}=${NONE}
    &{body}    Create Dictionary    customerId=${customer_id}    items=${items}
    ${response}    POST On Session    api    /v1/orders    json=${body}    expected_status=any
    common.Verify Http Status Code    ${response.status_code}    ${expected_status}
    IF    $expected_body is not None
        common.Verify Deep Response Matches Expected    ${response.json()}    ${expected_body}
    END
    RETURN    ${response}

Cleanup Order
    [Arguments]    ${order_id}
    DELETE On Session    api    /v1/orders/${order_id}    expected_status=any
```

`api` here is a session alias, not a literal endpoint host — it resolves to whichever URL
`Prepare Session API` created it with for the current `${ENV}` (§2). This keyword file never
changes between `local`/`sit`/`uat`.

Used from the single test-suite file, pulling both the request and the expected response straight
out of `${Test_Data}` (§3):

```robot
# test_suites/e2e_baseline.robot
*** Test Cases ***
E2E-REQ012-US045-001 Create Order Happy Path
    [Documentation]    E2E-REQ012-US045-001 — authenticated customer creates an order with 2 items
    [Tags]    E2E-REQ012-US045-001    US045    feature:orders    smoke
    ${response}    orders.Create Order
    ...    customer_id=${Test_Data}[input_data][orders][create_order][body][customer_id]
    ...    items=${Test_Data}[input_data][orders][create_order][body][items]
    ...    expected_body=${Test_Data}[expected_data][orders][create_order][api][response]
    [Teardown]    orders.Cleanup Order    ${response.json()}[id]
```

A scenario expecting a non-default status (e.g. a 400 error path) passes
`expected_status=${Test_Data}[expected_data][orders][create_order][api][http_status]` the same
way — no reason to hard-code it in the `.robot` file when it's already sitting in the YAML. See
`.claude/refs/e2e-test-data-conventions.md` for why `orders`/`create_order` (the always-present
`{core_feature}/{sub_feature}` pair) and `api` (the surface key) are there even for this
single-endpoint scenario.

**Data passing:** the test case captures `${response}` and passes it explicitly to the next call —
never a suite/global variable. A `Set Suite Variable`/`Set Global Variable` is allowed only with a
comment justifying genuine necessity (e.g. an expensive-to-fetch auth token shared across many
otherwise-independent cases in the same file) — never as the default way to thread state between
keywords or between test cases. Every `E2E-*` test case must remain independently runnable via
`robot --include E2E-REQ012-US045-001 tests/e2e/` without depending on a prior case having run.

## 5. The two generic assertion keywords (`e2e_assertion_helper`)

`keyword/common/commons_keyword.resource` — assertions section (shares this file with `Prepare
Test Data`, §3):

```robot
*** Keywords ***
Verify Http Status Code
    [Arguments]    ${actual_status}    ${expected_status}
    Should Be Equal As Integers    ${actual_status}    ${expected_status}

Verify Deep Response Matches Expected
    [Documentation]    Recursive dict/list/primitive diff. Reports every mismatch by dotted
    ...                path (not just the first). Two sentinel values in `expected` change the
    ...                usual equality check for that field: ${NONE}/`__ANY__` skips it entirely
    ...                ("don't care about this value"); `__Verify Not Empty__` requires the key
    ...                to be present and hold a non-empty value without pinning it to anything
    ...                specific (for generated UUIDs/timestamps with no way to predict the exact
    ...                value). Any other value is an exact/deep match.
    [Arguments]    ${actual}    ${expected}    ${allow_extra_keys}=${True}
    # implementation: walk both structures in parallel, Run Keyword And Continue On Failure
    # per leaf so multiple mismatches surface in one run instead of stopping at the first
```

Every per-endpoint keyword calls these two internally instead of re-inventing inline `Should Be
Equal` chains — the body-diff call is conditional on the keyword receiving an `${expected_body}`
argument (§4). This is what lets `design_notes.md`'s concrete Expected outcomes translate
directly into field-precise assertions without hand-rolled per-scenario checks.

`.claude/refs/e2e-test-data-conventions.md` §2 covers scenarios whose action also has a database,
bucket, or other side effect to verify — there's no fixed keyword template for those
(automation-engineer designs the check itself, reusing `Verify Deep Response Matches Expected`
above where it's a plain structural comparison, writing bespoke logic otherwise).

## 6. Seed/cleanup — `config/extend_scripts/`, not a Robot keyword

Since e2e runs against a real dev-environment stack already, seed/cleanup is a plain script (Python
or shell — `scripts/e2e/stack.sh` resolves the single script in this directory), not a Robot keyword:

```
tests/e2e/config/extend_scripts/
└── seed_e2e_data.py   # direct DB/HTTP seed + cleanup; invoked by `make e2e-seed`/`make e2e-seed-down`
```

Tests never seed data via `[Setup]`/`[Teardown]` HTTP calls or DB helpers — they assume the seed
already ran as a prerequisite step (`e2e_seed_cmd`, before `e2e_run_cmd`). This is stricter than R2
in `docs/test_strategy.md` ("no UI-driven setup for seed data") since it isn't Robot-driven at all.

**Same script, every environment.** The script takes `ENV=<local|sit|uat>` (passed through by
`make e2e-seed`/`make e2e-seed-down`) and resolves connection info from `environment.yaml`'s
`database` block plus `config/auth/.env.<env>` for that target — there's no separate script per
environment, exactly like the application code itself is built once and deployed unchanged to
SIT/UAT.

**Traceability:** every fixture the script inserts must carry a comment/tag naming the `E2E-*` ID
and test case name it belongs to (e.g. a `# E2E-REQ012-US045-001 Create Order Happy Path` comment for
Python/YAML/SQL fixtures; a `_test_case` metadata key for a comment-less format like plain JSON) —
so a human reviewing seeded data, especially before/after a manual SIT/UAT smoke run, can trace each
row back to the scenario that needs it. The exact syntax is left to whatever the script's own data
format supports; only the requirement is mandatory.

**Two invocation modes, both idempotent:** the default `e2e_seed_cmd` clears its own previously
inserted fixtures before inserting fresh ones — required already by the REQ Quality Gate's 3-round
reseed against the same persistent local DB (see `.claude/refs/gate-runbook.md`), and equally
necessary against a shared, persistent SIT/UAT DB. `e2e_seed_down_cmd` (`make e2e-seed-down
ENV=<env>`) runs the same script's cleanup-only mode — deletes those same fixtures without
reinserting. On local — if and only if `/init` decides `local` means a compose stack
(`start_local_cmd` in `test_stack.md`) — `make e2e-down` incidentally wipes seeded data too (it
nukes the whole compose stack's DB volume), so `e2e-seed-down` is somewhat redundant there but
still available for consistency; on SIT/UAT — which has no stack to tear down — it's the *only*
cleanup mechanism, so a human doing a manual smoke session runs `make e2e-seed-down ENV=sit`
afterward to avoid leaving clutter in a shared environment. The exact deletion logic (by known ID list, by a tag column, etc.)
is left to the script author.

## 7. External-dependency mocks — `config/wiremock/mappings/`

`docs/env_matrix.md`'s capability matrix requires third-party
externals to be mocked **at the network level** (a mock container), never called for real during
E2E. **WireMock** (`e2e_external_mock` in `test_stack.md`) is the concrete tool: a standalone mock
HTTP server that serves canned responses defined by stub **mapping** JSON files.

```
tests/e2e/config/wiremock/
└── mappings/
    ├── payment-gateway-success.json
    ├── payment-gateway-declined.json
    └── sms-provider-success.json
```

- **Naming: `<external-service>-<scenario>.json`, never `<US-ID>-*.json` or `<feature>-*.json`.**
  A stub describes the *external service's* behavior (e.g. "the payment gateway returns declined"),
  which is typically reused across many different test cases — it isn't owned by whichever story
  first needed it. Same reasoning as `keyword/common/`: shared infrastructure, not per-feature.
- Add a sibling `__files/` directory only if a stub needs to serve a large canned response body
  WireMock references by path rather than inlining.
- **Wiring the actual WireMock container into `start-local`/`compose.yml` is a separate infra task**
  — no compose stack exists yet in this project (`start_local_cmd` in `test_stack.md` is TBD until
  `/init` decides how `local` comes up). This section documents the convention for whenever that
  container exists; `automation-engineer` adds/edits mapping files here when a scenario needs a new
  external call stubbed, same as it would add a `keyword/<feature>/` file — it does not stand up
  the container itself.
- **Local-only, and not a filter or a switch.** WireMock is a container that only ever exists inside
  the local compose stack (`start-local`/`e2e-up`) — SIT/UAT are already-deployed environments this
  repo doesn't compose at all, so there is no WireMock instance reachable from them, and nothing
  "detects localhost" to decide whether to mock. The backend-under-test running in SIT/UAT was
  deployed separately with its third-party client already wired to the real endpoint, same as
  production. Because `e2e_assertion_helper` (§5) only ever asserts on the SUT's own observable
  response/DB state — never on WireMock's internal request log — no Robot script needs any
  environment-conditional logic either way; the same test steps work unmodified against a real third
  party in SIT/UAT.

## 8. Reading cascade — how `automation-engineer` finds a scenario's detail

Three tiers, consulted in order, each only as needed (mirrored in
`.claude/agents/automation-engineer.md`):

1. **`docs/test_cases/TEST_BASELINE.md`** — main/core source, always read first. It's a complete,
   standalone spec per `E2E-*` (not a pointer): Feature, E2E ID, Scenario, US[ID], State, Tags,
   Spec ref, and the full Preconditions/Request/Steps/Expected/Cleanup body.
2. **The originating `design_notes.md`** (reached via the baseline entry's **Spec ref** column) —
   read when the baseline entry's detail isn't enough to implement confidently.
3. **`docs/test_basis.md`** — read if still insufficient (exact JSON/contract specifics not
   already pinned in either of the above; the oracle every expected result cites).

This cascade exists because `TEST_BASELINE.md` serves two audiences at once: the human reviewer at
G5 needs it complete enough to review directly against the `.robot` script without opening per-REQ
files, while `automation-engineer` still benefits from being able to drill into the original design
or the oracle when the baseline entry alone leaves a gap.

## 9. Re-read-before-edit rule

`test_suites/e2e_baseline.robot` and `test_data/e2e_baseline.yaml` are edited by every story in
every REQ — always re-read the current file immediately before editing, and append/edit
surgically (locate the right `*** Test Cases ***` block or YAML top-level key, add or modify in
place). Never regenerate or wholesale-overwrite either file — doing so silently deletes every other
story's already-implemented cases or test data.

**On REMOVE, delete — never comment out.** When a baseline entry's State is `remove_pending_REQ[N]`,
delete that test case from `test_suites/e2e_baseline.robot` entirely. Do not wrap it in a comment
"just in case." `TEST_BASELINE.md`'s own tombstone entry (kept, not deleted, per its own
append-only rule) plus git history already preserve exactly what it used to do — a commented-out
case left in the one shared suite file only accumulates as dead weight, and risks silently
breaking if a keyword or data key it references is later renamed or removed by unrelated work.

## 10. Baseline state model — pending, then confirmed

Every baseline entry's State follows the same two-stage shape, per action:

| Action | Pending (qa-analyst sets, at merge time) | Confirmed (script-reviewer sets, on `scripts_approved`) |
|---|---|---|
| NEW | `planned` | `active` |
| MODIFIES | `modify_pending_REQ[N]` | `modified_by_REQ[N]` |
| REMOVE | `remove_pending_REQ[N]` | `removed_by_REQ[N]` |

- **`automation-engineer` only ever sees pending states** — that's its worklist. It never edits
  the State field itself; its job ends at implementing and reporting back.
- **`script-reviewer` is the only place pending flips to confirmed** — on a `scripts_approved`
  verdict, after verifying a REMOVE case is actually absent and a NEW/MODIFY case is actually
  present and correct. `make baseline` is a read-only drift-guard afterward, never a
  confirmation trigger.
- **Confirmed states persist** — `modified_by_REQ[N]`/`removed_by_REQ[N]` do not revert to
  `active` and do not expire. A later REQ that touches the same entry again simply overwrites the
  State with its own new transition. This is what lets anyone answer "what did REQ[N] touch?" at
  any point in the future by filtering for `modified_by_REQ[N]` state.
- **Append-only ≠ frozen content.** A row is never physically deleted (even `removed_by_REQ[N]`
  keeps its last-known content as a tombstone), and editing an entry never touches another entry's
  block — but a MODIFIES **does** overwrite that entry's own Preconditions/Steps/Expected/Cleanup
  in place, since the baseline must reflect current truth.

## 11. Adopted vs rejected from the reference project

| From the reference project | Adopted? | Notes |
|---|---|---|
| One keyword per API call, parameterized, verifies + returns | **Adopted** | Core of §4 above. |
| Generic status + deep-diff assertion keywords | **Adopted** | §5 above. |
| `config/import.resource` single root import | **Adopted** | §2 above. |
| `${Env}` variable + `Prepare Session API`/`${Api_Config}` session-alias indirection | **Adopted** | §2 above — this is the actual mechanism that lets the same keyword/test-case files target `local`/`sit`/`uat` unmodified, not just the YAML file below. |
| Direct DB/script-based seed (not UI-driven) | **Adopted, stricter** | §6 — a script, not even a Robot keyword. |
| YAML test data + a `Prepare Test Data` keyword doing `${${TEST_NAME}}` dynamic lookup | **Adopted, adapted** | §3 — the reference project keys one YAML per suite; ours is one project-wide `test_data/e2e_baseline.yaml` (still one top-level key per test case name), matching the existing single-file rule for `test_suites/e2e_baseline.robot`. |
| Suite/global variables (`${API_Response}`, `${Database_Result}`) threading state across "continuous case number N" tests | **Rejected as default** | Explicit `RETURN`+argument instead; global allowed only with a justifying comment. Chaining tests via execution order breaks independent tag-based selection (`--include E2E-*`). |
| Keyword arguments defaulting directly to `${Test_Data}[...]` (e.g. `[Arguments] ${x}=${Test_Data}[...]`) | **Rejected as default** | Test cases pass extracted `${Test_Data}[...]` values as explicit named arguments instead (§3/§4) — keeps keywords data-agnostic rather than coupling a keyword's signature to `${Test_Data}`'s exact shape. |
| Trailing `=` on assignment lines (`${var}=    Keyword`) | **Rejected** | Optional RF syntax sugar; dropped for readability throughout this doc's own examples — `${var}    Keyword` reads the same and is less visually noisy. |
| Dot-notation access on YAML-loaded dict variables (`${data.key.subkey}`) | **Rejected** | Bracket notation only (`${Test_Data}[key][subkey]`), consistently, even though Robot's DotDict would allow either — one style avoids the reader wondering which one applies where. |
| Informal `#[CP1]`/`#[CP9]` comment traceability | **Rejected** | Our `US[ID]`/`E2E-*` tag + `[Documentation]` traceability is already machine-filterable; comments aren't. |
| Custom Python CLI wrapper (`RunRobot.py`) replacing direct `robot`/`make` | **Rejected** | `make e2e-*` + `robot --include` is already simpler and sufficient. |
| `JsonValidator`/schema-based assertion (installed but unused in the reference project itself) | **Rejected** | Deep-diff-against-exact-JSON (§5) is the adopted strategy. |
| Secrets committed in a tracked `environment.yaml` | **Adopted, adapted** | §2 above — the reference project commits some API keys directly in its `environment.yaml`; ours splits sensitive header values and DB credentials into a gitignored `config/auth/.env.<env>` instead, keeping only URLs/aliases/non-secret header names/DB host-port-name tracked. |
| Single-file, flat `input:`/`expected:` test-data shape (this doc's original §3) | **Superseded** | Split into its own sibling file, `.claude/refs/e2e-test-data-conventions.md`, with a shared core convention (`input_data`/`expected_data`, always-nested `{core_feature}/{sub_feature}`) plus per-surface sections (`api`, `database`/`bucket`, `ui` reserved) — done ahead of any real UI/DB/bucket work so the shape doesn't need reworking once those tracks land. |
