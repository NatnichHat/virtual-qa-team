.PHONY: help validate coverage testcases testcases-check expected-lock expected-drift gate gate-scripts gate-artifacts \
        e2e-deps e2e-seed e2e-seed-down e2e-run e2e-dryrun e2e-up e2e-down start-local baseline baseline-check

# ENV selects the target for anything that talks to a running system.
# local is the only environment this repo might bring up itself; sit and uat are already-deployed,
# persistently-running environments reached only via seed / run / seed-down.
ENV ?= local
INCLUDE ?=

help:
	@echo "Artifacts"
	@echo "  make testcases        generate test_cases.csv from design_notes.md"
	@echo "  make testcases-check  fail if a CSV was hand-edited (drift guard)"
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
testcases:
	@python3 scripts/tc/build-csv.py

testcases-check:
	@python3 scripts/tc/build-csv.py --check

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
