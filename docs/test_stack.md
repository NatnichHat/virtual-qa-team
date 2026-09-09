# Test Stack — single source of truth for all QA-Team agents
# Agents READ this; only `/init` (via `test-stack-init`) WRITES it.
# Precedence: on any conflict, this file wins over an agent's built-in default.

## Project type
- SUT ownership:                 external — this repo does NOT contain the system under test
- Test basis source:             human documentation (Confluence / screens / walkthroughs) — NOT machine-readable
- Test levels in scope:          API, DB verification, Integration (third-party) — UI/Browser is out of scope
- Primary deliverable:           `docs/test_cases/REQ*/US*/test_cases.csv` (Excel-readable, for humans)

## Test basis
- test_basis_doc:                `docs/test_basis.md` — the living contract. Authored by `test-basis-analyst`
                                 from the human documentation, then **confirmed by the SUT team at G0**.
                                 Everything downstream cites it via `Basis_Ref`.
- basis_ref_format:              `test_basis.md#<anchor>` (e.g. `test_basis.md#post-v1-orders-400`)
                                 or `US[ID]#AC-<n>` for behaviour stated only in the story.
- basis_confidence:              every contract row carries `Confidence: confirmed | inferred | assumed`.
                                 `inferred`/`assumed` rows are the D3 risk surface — G0 must convert
                                 them to `confirmed` or the coverage denominator excludes them.

## Test case authoring
- design_notes:                  `docs/test_cases/REQ[ID]_*/US[ID]/design_notes.md` — the human-reviewable
                                 source of truth for HOW cases were derived. Written by `qa-analyst`.
- csv_output:                    `docs/test_cases/REQ[ID]_*/US[ID]/test_cases.csv` — **generated, never hand-written**
- csv_schema:                    `.claude/refs/csv-schema.md`
- csv_encoding:                  UTF-8 **with BOM** (Excel on Windows mis-renders Thai without it)
- csv_delimiter:                 `,` — fields containing `,` `"` or newline are quoted per RFC 4180
- csv_build_cmd:                 `make testcases` → `python3 scripts/tc/build-csv.py`
- csv_check_cmd:                 `make testcases-check` → build to a temp file and diff; a difference is drift
- xlsx_view_cmd:                 `make xlsx-view` → `python3 scripts/tc/build-xlsx.py` — renders
                                 `test_cases.xlsx` (merge + colour) FROM the CSVs; presentation
                                 only, gitignored, never read by a gate/script/agent. See
                                 `.claude/refs/csv-schema.md` §The presentation view.
- xlsx_preview_cmd:              `make xlsx-preview` → ALSO renders `xlsx_style_preview.xlsx` — the
                                 same contiguous case slice under all three colour scopes
                                 (cell_tint / row_tint / banding), one sheet each. Decide in Excel,
                                 then set `color_scope` in the style config.
- xlsx_style_config:             `scripts/tc/xlsx_style.toml` — presentation policy ONLY (merge set,
                                 header shape, freeze pane, palettes, widths, colour scope). Never
                                 affects CSV content; edit freely and re-render.
- xlsx_deps_cmd:                 `make xlsx-deps` → one-time install of `scripts/requirements.txt`
                                 (openpyxl) into `.venv/tools`; tooling deps, separate from
                                 `tests/e2e/requirements.txt`
- techniques_ref:                `.claude/refs/test-design-techniques.md`
- exception_catalog_ref:         `.claude/refs/exception-catalog.md`
- coverage_model_ref:            `.claude/refs/coverage-model.md`
- tcm_template_ref:              `.claude/refs/qa-templates.md`

## Coverage thresholds
- ac_coverage_min:               1.00  (100% — every acceptance criterion has at least one test case)
- rule_coverage_min:             0.90
- boundary_coverage_min:         0.90
- transition_coverage_min:       0.90
- exception_coverage_min:        0.90
- endpoint_status_coverage_min:  0.90
- validation_rule_coverage_min:  0.90
- automation_coverage_min:       0.90  (90% of P1+P2 cases — user explicitly chose 90% over the 0.70 default)
- coverage_cmd:                  `make coverage` → `python3 scripts/gate/coverage-report.py`
- **The denominators are ratified by a human at G2 before any case is written.** See `coverage-model.md`.

## Automation
- Framework:                     Robot Framework — `RequestsLibrary` (API), `Browser` (UI),
                                 `DatabaseLibrary` (DB verification). Testing is done entirely through
                                 Robot Framework, never a separate standalone tool.
- e2e_root:                      `tests/e2e/`
- e2e_organization:              POM-style, type-first. `keyword/<feature>/` + `page/<feature>/` are
                                 per-feature (one level deep, names ratified in `tests/e2e/FEATURES.md`);
                                 `test_suites/e2e_baseline.robot` and `test_data/e2e_baseline.yaml` are
                                 **single project-wide files** where feature identity is a `feature:<name>` tag.
                                 See `.claude/refs/e2e-api-conventions.md`.
- e2e_file_convention:           keyword-per-endpoint; the keyword builds the request, asserts status AND
                                 body via the shared assertion keywords, and `RETURN`s the parsed response.
                                 Test cases never inline an HTTP call or a raw assertion.
- e2e_assertion_helper:          `tests/e2e/keyword/common/commons_keyword.resource` — generic status keyword
                                 + recursive deep-diff response keyword (dotted-path mismatch reporting,
                                 continue-on-failure, `__Verify Not Empty__` sentinel for unpinned fields)
- e2e_test_data_prep:            `tests/e2e/keyword/common/commons_keyword.resource` — `Prepare Test Data`
                                 resolves `${${TEST_NAME}}` from `test_data/e2e_baseline.yaml` into `${Test_Data}`,
                                 wired as `Test Setup`. Bracket notation only (`${Test_Data}[a][b]`).
- e2e_features_catalog:          `tests/e2e/FEATURES.md` — coarse (~6–10) catalog; additions are human-ratified
- e2e_baseline:                  `docs/test_cases/TEST_BASELINE.md` — 1 project = 1 baseline
- container_runtime:             not applicable — no local stack exists; `local` points at the SIT deployment
                                 (same URLs as SIT). WireMock is not available anywhere; destructive cases
                                 are blocked on all environments (shared). Drive any future container via
                                 Makefile targets, never directly.
- e2e_external_mock:             WireMock — `tests/e2e/config/wiremock/mappings/<service>-<scenario>.json`.
                                 **Local-only** — sit/uat talk to the real third party, same as production.
- db_verification:               `DatabaseLibrary` via `environment.yaml`'s `database` block +
                                 `config/auth/.env.<env>`. Read-only assertions inside the endpoint keyword;
                                 writes belong to the seed script, never to a test.

## Environments
- environments:                  `local`, `sit`, `uat` — see `docs/env_matrix.md` for what each can do
- e2e_environment_config:        `tests/e2e/config/environment.yaml` — non-secret per-env config:
                                 `Environment.<env>.api_config.<alias>.{name, url, headers}`,
                                 `Environment.<env>.web_base_url`, `Environment.<env>.database.{host,port,name}`.
                                 **No secrets** — those load from the gitignored `config/auth/.env.<env>`.
- e2e_env_select:                `${ENV}` — declared once in `config/import.resource`, default `local`.
                                 Pass `ENV=<env>` to `make e2e-seed` / `make e2e-run`.
                                 Must exactly match a key under `environment.yaml`'s `Environment:` root.
                                 **No keyword / page / test-case file ever changes between environments.**
- e2e_deps_cmd:                  `make e2e-deps` — one-time host provisioning from `tests/e2e/requirements.txt`
                                 (+ `rfbrowser init`). NOT part of seed/run/dryrun — run once per machine or CI image.
- e2e_seed_cmd:                  `make e2e-seed ENV=<env>` — idempotent (clears its own fixtures before inserting)
- e2e_seed_down_cmd:             `make e2e-seed-down ENV=<env>` — cleanup-only mode; the sit/uat-safe teardown
- e2e_dryrun_cmd:                `robot --dryrun tests/e2e/` — parse-only, environment-agnostic, no stack needed
- e2e_run_cmd:                   `make e2e-run ENV=<env>` — wraps `scripts/e2e/run-e2e.py`, which re-reads
                                 `output.xml` to **enforce the zero-skip rule** (Robot exits 0 on a skip) and
                                 writes the output trio to `tests/e2e/test_results/<date>/<time>/`
- e2e_select_by_tag:             `make e2e-run INCLUDE=<tag>` — select by tag (US ID, `E2E-*` ID, `feature:<name>`,
                                 `env:<env>`), never by folder/filename. Routed through the same runner so a
                                 tag-selected run keeps zero-skip enforcement.
- start_local_cmd:               none — there is no local compose stack. `local` is a pointer at the SIT
                                 deployment (same URLs as SIT, selected via `environment.yaml`). See
                                 `docs/env_matrix.md` for the per-endpoint table and VPN prerequisite.

## Tags (the traceability vocabulary — nothing is traced by path)
- `E2E-REQ{N}-US{N}-{running}`   the automation ID; **MUST be in `[Tags]`**, not only the name/`[Documentation]`
- `US[ID]`                       owning story
- `feature:<name>`               from `tests/e2e/FEATURES.md`
- `env:local` / `env:sit` / `env:uat`   which environments this case is valid in (from CSV `Env_Scope`)
- `destructive`                  mutates shared data irreversibly — blocked on shared envs without G6 approval
- `smoke` / `regression`         run-selection bands
- `level:api` / `level:ui` / `level:db` / `level:integration`

## Quality gates (automation code)
- gate_script:                   `scripts/gate/run-gate.sh`
- gate_cmd_scripts:              `scripts/gate/run-gate.sh scripts` — robot dryrun + tidy/lint + convention scan
- gate_cmd_artifacts:            `scripts/gate/run-gate.sh artifacts` — validate-artifacts + expected-drift + coverage
- pass_sentinel:                 `QA GATE: PASS`
- validator_cmd:                 `make validate` → `python3 scripts/gate/validate-artifacts.py`
- expected_drift_cmd:            `make expected-drift` → `python3 scripts/gate/expected-drift.py`
- flake_rounds:                  3 — every execution gate runs the suite 3× with a reseed before each round

## Defect triage
- triage_protocol_ref:           `.claude/refs/triage-protocol.md`
- triage_output:                 `docs/defects/<run-id>/triage.md` + one Triage Record per failure
- defect_tracker:                Jira project key **EKC** — one project for both stories and defects;
                                 `fetch-jira.py` and G7 ticketing both use EKC.
- severity_scale:                S1 Critical / S2 Major / S3 Minor / S4 Cosmetic
- min_evidence_per_classification: 2   # a classification with fewer than 2 pieces of evidence is invalid

## Forbidden patterns (machine-checkable — enforced by gate_cmd_scripts)
- `Sleep` in any Robot file — use `Wait For Elements State` / explicit waits. Hard ceiling 60s on any timeout.
- `force=True` on a click, or `Evaluate JavaScript` used to manipulate the DOM — never bypass broken UI
- Fragile locators (CSS class, tag name, raw text) where a `data-testid` exists or could exist
- A raw URL in a keyword — every request goes through a `Prepare Session API` session alias
- `expected_status=any` without an exhaustive allowed-set assertion following it
- Hard-coded test data in a test case or keyword — everything comes from `test_data/e2e_baseline.yaml`
- Dot notation on `${Test_Data}` — bracket notation only
- `Set Suite Variable` / `Set Global Variable` without a comment justifying genuine necessity
- A `[Setup]` keyword doing HTTP/DB seeding — seeding is out-of-Robot via `e2e_seed_cmd`
- An `E2E-*` ID that appears in the test case name but not in `[Tags]`
- Editing a CSV by hand instead of regenerating it from `design_notes.md`
