#!/usr/bin/env bash
# E2E stack + fixture lifecycle. Driven by the Makefile; not meant to be called directly.
#
#   stack.sh start-local          bring up the full local stack (all services + DB + mocks)
#   stack.sh up                   bring up just the e2e profile
#   stack.sh down                 tear down what `up` brought up
#   stack.sh seed       <env>     load fixtures into <env>'s datastore (idempotent)
#   stack.sh seed-down  <env>     delete those same fixtures, don't reinsert
#
# WHY THIS EXISTS RATHER THAN INLINE MAKEFILE RECIPES: every one of these has a
# prerequisite that may legitimately not exist yet on a fresh skeleton (a compose file, a
# seed script). The one thing a gate target must never do is succeed when it did nothing —
# `make e2e-up && make e2e-seed && make e2e-run` would then run the suite against a stack
# that was never started and report the failures as test defects. So each action
# preflights its prerequisites and exits 2 ("cannot run — broken gate/tooling", matching
# scripts/e2e/run-e2e.py and scripts/gate/run-gate.sh) with the name of whoever owns the
# missing piece. Exit 2 is never a pass.
#
# LOCAL-ONLY vs ENV-AWARE — this split is deliberate, see the Makefile header:
#   start-local / up / down   the application stack as ephemeral containers on a laptop.
#                             sit/uat already run the app as a persistently-deployed
#                             service owned by a separate CD pipeline, so "bring the stack
#                             up" is not an operation that exists there. These refuse a
#                             non-local ENV rather than pretending to honour it.
#   seed / seed-down          same script, same logic, any environment — only the
#                             connection info differs, resolved from environment.yaml.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
E2E_ROOT="$REPO_ROOT/tests/e2e"
ENV_YAML="$E2E_ROOT/config/environment.yaml"
SEED_DIR="$E2E_ROOT/config/extend_scripts"
# Overridable so a project can keep its compose file elsewhere without editing this script.
COMPOSE_FILE="${COMPOSE_FILE:-$REPO_ROOT/compose.yml}"

ACTION="${1:-}"
ENV_NAME="${2:-local}"

die()  { echo "stack.sh: $*" >&2; exit 2; }
note() { echo "stack.sh: $*"; }

# ── preflight helpers ────────────────────────────────────────────────────────

require_podman() {
  # The container runtime is a decision `/init` records (docs/test_stack.md ->
  # container_runtime). This function drives whichever runtime that field settled on; today
  # it checks podman first. It never silently falls back to another runtime — a project
  # that swapped runtimes should say so in test_stack.md, and this function should be
  # updated to match.
  command -v podman-compose &>/dev/null && { COMPOSE=(podman-compose); return; }
  if command -v podman &>/dev/null && podman compose --help &>/dev/null; then
    COMPOSE=(podman compose); return
  fi
  die "neither 'podman-compose' nor 'podman compose' is available — the e2e stack cannot be
     brought up. The container runtime for this project is set in docs/test_stack.md ->
     container_runtime (decided at /init); install that runtime and re-run. This script
     never substitutes a different runtime silently."
}

require_compose_file() {
  [[ -f "$COMPOSE_FILE" ]] || die "no compose file at ${COMPOSE_FILE#"$REPO_ROOT"/}.
     The application stack (backend services + frontend + datastore + external mocks) has no
     compose definition yet — that is the SUT team's deliverable, not something this target
     can synthesise. (If /init decided 'local' points at a shared dev deployment instead of
     composing locally, none of these local-stack targets apply — see docs/env_matrix.md.)
     Until it exists, the local e2e stack cannot start, and any gate that depends on a live
     stack is blocked_gate, not a failing test. Override the path with COMPOSE_FILE=<path>
     if your project keeps it elsewhere."
}

require_local_env() {
  [[ "$ENV_NAME" == "local" ]] || die "'$ACTION' is LOCAL-ONLY and cannot take ENV=$ENV_NAME.
     sit/uat run the application as a persistently-deployed service owned by a separate CD
     pipeline — there is no stack here to bring up or tear down. To clean up fixtures you
     seeded into a shared environment, use: make e2e-seed-down ENV=$ENV_NAME"
}

resolve_seed_script() {
  [[ -d "$SEED_DIR" ]] || die "no seed script directory at ${SEED_DIR#"$REPO_ROOT"/}.
     The seed/cleanup script is part of the e2e scaffold, created by automation-engineer on
     the first automation task in the project (see .claude/agents/automation-engineer.md).
     Run /phase4 at least once, or create it by hand following
     .claude/refs/e2e-api-conventions.md section 6."
  # One script, name chosen by the project — test_stack.md's e2e_seed_cmd points at this
  # directory rather than pinning a filename or language.
  local found=()
  while IFS= read -r f; do found+=("$f"); done < <(find "$SEED_DIR" -maxdepth 1 -type f \
      \( -name '*.py' -o -name '*.sh' -o -perm -u+x \) | sort)
  case "${#found[@]}" in
    0) die "${SEED_DIR#"$REPO_ROOT"/} exists but holds no seed script.
     Same owner as above: automation-engineer's scaffold bootstrap." ;;
    1) SEED_SCRIPT="${found[0]}" ;;
    *) die "${SEED_DIR#"$REPO_ROOT"/} holds more than one candidate script:
     $(printf '%s ' "${found[@]##*/}")
     e2e_seed_cmd expects ONE entry point. Keep a single script (it may import others)." ;;
  esac
}

check_env_known() {
  # environment.yaml is authoritative for which environments exist. If it isn't there yet
  # (fresh skeleton, scaffold not bootstrapped) don't block on it — the seed script's own
  # connection lookup will fail loudly enough, and blocking here would be a worse error.
  [[ -f "$ENV_YAML" ]] || { note "warn: ${ENV_YAML#"$REPO_ROOT"/} not found — cannot verify ENV=$ENV_NAME is a known environment"; return; }
  grep -qE "^[[:space:]]+${ENV_NAME}:" "$ENV_YAML" \
    || die "ENV=$ENV_NAME has no entry under Environment: in ${ENV_YAML#"$REPO_ROOT"/}.
     Known environments are the keys defined there (see docs/test_stack.md -> e2e_env_select)."
}

run_seed() {
  local mode_flag="$1"   # "" for seed, "--down" for cleanup-only
  resolve_seed_script
  check_env_known
  local rel="${SEED_SCRIPT#"$REPO_ROOT"/}"
  note "ENV=$ENV_NAME  script=$rel ${mode_flag:+(cleanup-only)}"
  # Pass ENV both ways: as an argument for scripts that parse flags, and in the environment
  # for scripts that read it directly. Costs nothing and removes a whole class of "which
  # convention did this project pick" breakage.
  if [[ "$SEED_SCRIPT" == *.py ]]; then
    ENV="$ENV_NAME" python3 "$SEED_SCRIPT" --env "$ENV_NAME" ${mode_flag:+$mode_flag}
  else
    ENV="$ENV_NAME" bash "$SEED_SCRIPT" --env "$ENV_NAME" ${mode_flag:+$mode_flag}
  fi
}

# ── actions ──────────────────────────────────────────────────────────────────

case "$ACTION" in
  start-local)
    require_local_env; require_podman; require_compose_file
    note "bringing up the full local stack from ${COMPOSE_FILE#"$REPO_ROOT"/}"
    "${COMPOSE[@]}" -f "$COMPOSE_FILE" up -d --build
    ;;
  up)
    require_local_env; require_podman; require_compose_file
    note "bringing up the e2e profile from ${COMPOSE_FILE#"$REPO_ROOT"/}"
    "${COMPOSE[@]}" -f "$COMPOSE_FILE" --profile e2e up -d --build
    ;;
  down)
    require_local_env; require_podman; require_compose_file
    note "tearing down the e2e profile (including volumes)"
    "${COMPOSE[@]}" -f "$COMPOSE_FILE" --profile e2e down -v
    ;;
  seed)      run_seed "" ;;
  seed-down) run_seed "--down" ;;
  *)
    echo "usage: $0 <start-local|up|down|seed|seed-down> [env]" >&2
    exit 2
    ;;
esac
