#!/usr/bin/env bash
# QA gate runner. See .claude/refs/gate-runbook.md.
#
#   run-gate.sh scripts    # automation code: dryrun, forbidden patterns, tag selectability
#   run-gate.sh artifacts  # test artifacts: validator, expected-drift, coverage
#   run-gate.sh all
#
# Exit: 0 pass (prints the sentinel) · 1 a check failed · 2 the gate could not run.
#
# Exit 2 is not an artifact failure. It means the gate never reached a verdict — a missing tool, an
# unreadable file. That routes to whoever owns the tooling, never back to the agent whose work was
# never actually checked. Reporting PASS or FAIL when the gate did not run is the one outcome that
# must never happen.
set -uo pipefail

SENTINEL="QA GATE: PASS"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
E2E="$ROOT/tests/e2e"
SUITE_DIR="$E2E/test_suites"
FAILED=0

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }
step() { printf '\n▸ %s\n' "$*"; }
fail() { red "  FAIL: $*"; FAILED=1; }

need() {
  command -v "$1" >/dev/null 2>&1 || { red "gate cannot run: '$1' not found on PATH"; exit 2; }
}

scan() {
  # scan <description> <grep-pattern> [extra grep args]
  local desc="$1" pattern="$2"; shift 2
  local hits
  hits=$(grep -rInE "$pattern" "$E2E" --include='*.robot' --include='*.resource' "$@" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    fail "$desc"
    printf '%s\n' "$hits" | sed 's/^/      /'
  else
    info "ok: $desc"
  fi
}

gate_scripts() {
  step "e2e dryrun (hard precondition — a file Robot rejects cannot be content-reviewed)"
  need robot
  if [ ! -d "$E2E" ] || [ -z "$(find "$SUITE_DIR" -name '*.robot' 2>/dev/null)" ]; then
    info "no suite yet — skipping script gate (nothing has been automated)"
    return
  fi
  if robot --dryrun --output NONE --log NONE --report NONE "$E2E" >/tmp/qa-dryrun.log 2>&1; then
    info "ok: dryrun parses clean"
  else
    fail "dryrun did not parse"
    sed 's/^/      /' /tmp/qa-dryrun.log | tail -30
    return
  fi

  step "forbidden patterns (docs/test_stack.md)"
  scan "no Sleep — use explicit waits"                 '^[^#]*\bSleep\b'
  scan "no forced clicks"                              'force[[:space:]]*=[[:space:]]*(True|true)'
  scan "no DOM manipulation via JavaScript"            'Evaluate[[:space:]]+JavaScript'
  scan "no raw URLs — use a session alias"             'https?://[^$ ]' --exclude-dir=config
  scan "no open-ended expected_status=any"             'expected_status[[:space:]]*=[[:space:]]*any'
  scan "no dot notation on \${Test_Data}"              '\$\{Test_Data\}\.'
  scan "no keyword defaulting an arg to \${Test_Data}" '\[Arguments\].*=\$\{Test_Data\}'

  step "unjustified suite/global variables"
  local hits
  hits=$(grep -rInE 'Set (Suite|Global) Variable' "$E2E" --include='*.robot' --include='*.resource' 2>/dev/null || true)
  if [ -n "$hits" ]; then
    info "found — each needs a justifying comment; script-reviewer verifies:"
    printf '%s\n' "$hits" | sed 's/^/      /'
  else
    info "ok: none"
  fi

  step "E2E-* IDs are tags, not just names"
  # An ID living only in the test name or [Documentation] cannot be selected with --include,
  # which silently breaks tag-based reporting and the standalone-run guarantee.
  local ids tagged
  ids=$(grep -rhoE 'E2E-REQ[0-9]+-US[0-9]+-[0-9]+' "$SUITE_DIR" 2>/dev/null | sort -u || true)
  tagged=$(grep -rhE '^\s*\[Tags\]' "$SUITE_DIR" 2>/dev/null | grep -oE 'E2E-REQ[0-9]+-US[0-9]+-[0-9]+' | sort -u || true)
  local missing
  missing=$(comm -23 <(printf '%s\n' "$ids") <(printf '%s\n' "$tagged") | grep -v '^$' || true)
  if [ -n "$missing" ]; then
    fail "these E2E IDs appear in the suite but not in any [Tags] line:"
    printf '%s\n' "$missing" | sed 's/^/      /'
  else
    info "ok: every E2E ID is selectable by tag"
  fi

  step "feature folders are ratified in tests/e2e/FEATURES.md"
  local catalog d name
  catalog=$(grep -oE '^\| `?[a-z_][a-z0-9_]*`? ' "$E2E/FEATURES.md" 2>/dev/null | tr -d '|` ' || true)
  for d in "$E2E"/keyword/*/ "$E2E"/page/*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    [ "$name" = "common" ] && continue
    if ! printf '%s\n' "$catalog" | grep -qx "$name"; then
      fail "feature folder '$name' is not listed in tests/e2e/FEATURES.md (additions are human-ratified)"
    fi
  done
  info "ok: feature folders checked"
}

gate_artifacts() {
  need python3
  step "artifact validator"
  python3 "$ROOT/scripts/gate/validate-artifacts.py" || FAILED=1
  step "expected-result drift (anti-self-healing)"
  python3 "$ROOT/scripts/gate/expected-drift.py"      || FAILED=1
  step "coverage"
  python3 "$ROOT/scripts/gate/coverage-report.py"     || FAILED=1
  step "csv drift"
  python3 "$ROOT/scripts/tc/build-csv.py" --check     || FAILED=1
}

case "${1:-all}" in
  scripts)   gate_scripts ;;
  artifacts) gate_artifacts ;;
  all)       gate_scripts; gate_artifacts ;;
  *) echo "usage: run-gate.sh {scripts|artifacts|all}" >&2; exit 2 ;;
esac

echo
if [ "$FAILED" -eq 0 ]; then
  echo "$SENTINEL"
  exit 0
fi
echo "QA GATE: FAIL"
exit 1
