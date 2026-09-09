.PHONY: help validate coverage testcases testcases-check xlsx-view xlsx-preview xlsx-deps expected-lock expected-drift gate gate-scripts gate-artifacts \
        e2e-deps e2e-seed e2e-seed-down e2e-run e2e-dryrun e2e-up e2e-down start-local baseline baseline-check

# ENV selects the target for anything that talks to a running system.
# local is the only environment this repo might bring up itself; sit and uat are already-deployed,
# persistently-running environments reached only via seed / run / seed-down.
ENV ?= local
INCLUDE ?=

help:
	@echo "Artifacts"
	@echo "  make testcases        generate test_cases.csv (cases + coverage X-matrix block) from design_notes.md; STORY=<dir>"
	@echo "  make testcases-check  fail if a CSV was hand-edited (drift guard)"
	@echo "  make xlsx-view        render test_cases.xlsx (presentation: merge+colour) FROM the CSVs; gitignored; STORY=<dir>"
	@echo "  make xlsx-preview     ALSO render the colour-scope comparison workbook (pick cell_tint/row_tint/banding in Excel, set scripts/tc/xlsx_style.toml)"
	@echo "  make xlsx-deps        one-time install of the tooling deps (scripts/requirements.txt → openpyxl)"
	@echo "  make validate         artifact validator — the pre-check behind every human gate"
	@echo "  make coverage         specification coverage against the G2-ratified denominators"
	@echo "  make expected-lock    snapshot approved expected results (G4 approval only)"
	@echo "  make expected-drift   anti-self-healing check"
	@echo "  make baseline-check   read-only drift guard on TEST_BASELINE.md"
	@echo ""
	@echo "Gates"
	@echo "  make gate-scripts     automation code gate (dryrun + forbidden patterns + tags)"
	@echo "  make gate-artifacts   artifact gate (validator + drift + coverage)"
	@echo "  make gate             both"
	@echo ""
	@echo "Execution      (ENV=local|sit|uat, default local)"
	@echo "  make e2e-deps         one-time host provisioning — NOT part of seed/run"
	@echo "  make e2e-seed         load fixtures (idempotent — reseed before EVERY round)"
	@echo "  make e2e-run          run the suite; INCLUDE=<tag> to select"
	@echo "  make e2e-dryrun       parse check only, no stack needed"
	@echo "  make e2e-seed-down    remove seeded fixtures (the sit/uat-safe teardown)"

# ── Artifacts ──────────────────────────────────────────────────────────────
# test_cases.csv is one file with two blocks: the case columns (left) and the wide X-mapping
# Coverage Matrix (right — `AC ·` … `EXC` columns), derived from design_notes.md's Derivation
# tables (never hand-typed — see .claude/refs/csv-schema.md and coverage-model.md). The retired
# `tcm-matrix` target's standalone tcm_matrix.csv is now this matrix block. STORY=<dir> is
# optional; without it every story under docs/test_cases/ is built.
testcases:
	@python3 scripts/tc/build-csv.py $(if $(STORY),--story $(STORY),)

testcases-check:
	@python3 scripts/tc/build-csv.py --check $(if $(STORY),--story $(STORY),)

# Presentation view: test_cases.xlsx (merge cells + colour) rendered FROM the CSVs, for humans
# opening Excel — never read by a gate, script, or agent (those read the token-cheap CSVs).
# Gitignored on purpose: an xlsx is a zip embedding timestamps, so committing it would trip
# byte-diff guards on identical content. The CSVs are the truth; this is a photograph of them.
xlsx-view:
	@$(XLSX_PY) scripts/tc/build-xlsx.py $(if $(STORY),--story $(STORY),)

# Colour-scope decision aid: renders xlsx_style_preview.xlsx beside test_cases.xlsx — the same
# small automatic case subset under all three scopes (cell_tint / row_tint / banding), one sheet
# each. Open it in Excel, pick, set color_scope in scripts/tc/xlsx_style.toml, re-run xlsx-view.
xlsx-preview:
	@$(XLSX_PY) scripts/tc/build-xlsx.py --preview $(if $(STORY),--story $(STORY),)

# One-time provisioning for the tooling scripts — same tier as e2e-deps, deliberately NOT
# auto-invoked by xlsx-view. Tooling deps live in scripts/requirements.txt, separate from the
# Robot runner's tests/e2e/requirements.txt. Installs into a project-local venv (.venv/tools,
# gitignored) rather than the system site-packages: PEP 668 guards Homebrew/Debian Python
# against exactly that, and this repo never silently overrides the guard (deps.sh precedent).
XLSX_PY := $(if $(wildcard .venv/tools/bin/python3),.venv/tools/bin/python3,python3)
xlsx-deps:
	@python3 -m venv .venv/tools && .venv/tools/bin/python3 -m pip install --quiet -r scripts/requirements.txt && echo "xlsx-deps: openpyxl installed into .venv/tools — make xlsx-view will use it"

validate:
	@python3 scripts/gate/validate-artifacts.py

coverage:
	@python3 scripts/gate/coverage-report.py

# Run ONLY as part of /approve-test-case. This snapshot is what expected-drift.py compares against;
# without it the anti-self-healing guard has no baseline and is silently inert.
expected-lock:
	@python3 scripts/gate/expected-drift.py --lock

expected-drift:
	@python3 scripts/gate/expected-drift.py

# Read-only audit of TEST_BASELINE.md against the actual suite. It never flips a State and never
# rewrites qa-analyst's prose — only script-reviewer confirms a state, on a scripts_approved verdict.
# CI guard: `make baseline-check` must pass; a drift alarm is never routine.
baseline:
	@python3 scripts/e2e/baseline-drift.py

baseline-check:
	@python3 scripts/e2e/baseline-drift.py --check

# ── Gates ──────────────────────────────────────────────────────────────────
gate-scripts:
	@scripts/gate/run-gate.sh scripts

gate-artifacts:
	@scripts/gate/run-gate.sh artifacts

gate:
	@scripts/gate/run-gate.sh all

# ── Execution ──────────────────────────────────────────────────────────────
# One-time host provisioning. Deliberately NOT part of the seed/run chain — same precedent as a
# container runtime never being auto-installed. Run once per machine or CI image.
e2e-deps:
	@scripts/e2e/deps.sh

# Idempotent: clears its own previously-inserted fixtures before inserting, so it is safe to rerun
# against a persistent database. That is required by the 3-round flake check, which reseeds before
# every round against the same DB with no teardown in between.
e2e-seed:
	@scripts/e2e/stack.sh seed $(ENV)

# Cleanup-only mode. On sit/uat this is the ONLY teardown available — there is no stack to bring
# down, only seeded data to remove after a session in a shared environment.
e2e-seed-down:
	@scripts/e2e/stack.sh seed-down $(ENV)

# Wraps scripts/e2e/run-e2e.py, which re-reads output.xml to enforce the zero-skip rule: Robot's own
# exit code counts failures only, so a skipped test exits 0 and looks green. Writes the output trio
# to tests/e2e/test_results/<date>/<time>/ — never a fixed path a later run would overwrite.
e2e-run:
	@python3 scripts/e2e/run-e2e.py --env $(ENV) $(if $(INCLUDE),--include $(INCLUDE),)

e2e-dryrun:
	@robot --dryrun --output NONE --log NONE --report NONE tests/e2e/

# local-only: sit and uat are deployed by a CD pipeline this repo does not own, so "bring the stack
# up" is not an operation that applies there. Configure start_local_cmd in docs/test_stack.md.
start-local:
	@scripts/e2e/stack.sh start-local $(ENV)

e2e-up:
	@scripts/e2e/stack.sh up $(ENV)

e2e-down:
	@scripts/e2e/stack.sh down $(ENV)
