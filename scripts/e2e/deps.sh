#!/usr/bin/env bash
# Host Python/Robot Framework provisioning. Driven by the Makefile; not meant to be called
# directly (though nothing stops you — unlike stack.sh's actions, this one needs no
# Makefile-supplied ENV/COMPOSE_FILE).
#
#   deps.sh   install tests/e2e/requirements.txt onto this host, then (only if the Browser
#             library is among those deps) run `rfbrowser init` to fetch its browser binaries
#
# WHY THIS IS A SEPARATE SCRIPT FROM stack.sh: stack.sh's own header scopes it to "E2E stack +
# fixture lifecycle" — container/fixture concerns. This is a different concern entirely: host
# Python tool provisioning. One script per concern, same as run-e2e.py (run + verdict) and
# baseline-drift.py (audit) are each their own file rather than folded into stack.sh.
#
# WHY THIS IS NEVER AUTO-INVOKED BY up/seed/run: it's a one-time (or CI-image-cacheable) setup
# step, not a per-run concern — same precedent as Podman itself never being auto-installed by
# require_podman() in stack.sh. `robot` (and, when in use, its Browser-library binaries) must
# already be on PATH before e2e_dryrun_cmd, e2e_run_cmd, or tester's own Author-mode dryrun
# step ever run — this script is how that precondition gets satisfied, run once per
# machine/CI image, not wired into the up/seed/run chain.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REQS="$REPO_ROOT/tests/e2e/requirements.txt"

die()  { echo "deps.sh: $*" >&2; exit 2; }
note() { echo "deps.sh: $*"; }

# ── preflight ────────────────────────────────────────────────────────────────

[[ -f "$REQS" ]] || die "no requirements file at tests/e2e/requirements.txt.
   This file ships with the skeleton and is tracked in git, so the usual cause is that it was
   deleted locally — recover it with 'git checkout -- tests/e2e/requirements.txt' rather than
   rewriting it, since its exact pins are load-bearing for the Mode 2 flake check.
   On a project that genuinely never had it, 'tester' creates it on the first e2e task (see
   .claude/agents/tester.md -> Author mode step 2b); see that file's own header for the
   pinning and ownership convention."

command -v python3 &>/dev/null || die "python3 is not on PATH — this is a genuine host
   precondition this script does not attempt to fix (same tier as Podman itself, see
   require_podman() in stack.sh). Install Python 3, then re-run: make e2e-deps"

command -v pip3 &>/dev/null || die "pip3 is not on PATH (python3 was found, but its pip
   companion wasn't). Install pip for this Python 3, then re-run: make e2e-deps"

# Browser library's own init step shells out to npm under the hood (see the 'install' section
# below) — checked here, before any pip install runs, so a missing Node/npm fails fast with an
# actionable message instead of a raw Python traceback from deep inside `rfbrowser init`.
# Node/npm is already an assumed host precondition for this repo's frontend track
# (frontend_test_cmd/frontend_lint_cmd in tech_stack.md both shell out to npm) — same tier as
# Podman: never installed by this script, only checked for.
if grep -q '^robotframework-browser' "$REQS" 2>/dev/null; then
  command -v node &>/dev/null && command -v npm &>/dev/null || die "robotframework-browser is
     in tests/e2e/requirements.txt, but node/npm are not on PATH — 'rfbrowser init' shells out
     to npm to fetch its browser binaries and will fail without it. Install Node.js (which
     bundles npm; this repo's frontend track already assumes it's present, see
     frontend_test_cmd in docs/tech_stack.md), then re-run: make e2e-deps"
fi

# ── install ──────────────────────────────────────────────────────────────────

rel="${REQS#"$REPO_ROOT"/}"
note "installing $rel"
# --user, not a bare 'pip3 install': writes to this user's site-packages (e.g. ~/.local/bin
# on PATH) instead of requiring sudo/system-wide access — and, unlike a project-local
# .venv/, resolves identically from the repo root AND from every .worktrees/<task>/
# subdirectory a be-dev/fe-dev task runs in, since worktrees share the host/user, not a
# fresh environment.
#
# An ACTIVE virtualenv is the one case where --user is not just unnecessary but fatal: pip
# refuses it outright ("Can not perform a '--user' install. User site-packages are not
# visible in this virtualenv."), exit 1, every time. The venv IS already the isolated,
# no-sudo, on-PATH destination --user exists to provide, so drop the flag and install into
# it. Detected via $VIRTUAL_ENV, which venv/virtualenv both export on activate.
PIP_ARGS=(install --user)
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  note "active virtualenv detected (${VIRTUAL_ENV}) — installing into it, without --user"
  PIP_ARGS=(install)
fi

# Wrapped (not left to `set -e`'s default propagation) because a bare pip failure exits 1 —
# this repo's convention reserves 1 for a genuine test/behavior failure. An unmet host
# precondition belongs at exit 2, same class as the python3/pip3 checks above.
pip3 "${PIP_ARGS[@]}" -r "$REQS" || die "pip install failed (see pip's own error above).
   The most common cause is PEP 668's 'externally-managed-environment' guard (default on
   recent Debian/Ubuntu/Homebrew Python) — a deliberate host opt-in this script does not
   silently override. Fix it yourself with PIP_BREAK_SYSTEM_PACKAGES=1, or activate a venv
   (this script installs into an active one automatically), then re-run: make e2e-deps"

# A successful --user install does NOT guarantee 'robot' is actually runnable: pip installs
# console scripts into a user-specific bin dir (e.g. ~/.local/bin on Linux,
# ~/Library/Python/<ver>/bin on macOS Framework builds) that is commonly absent from PATH by
# default — pip prints a warning about this, easy to miss in longer output, and otherwise
# exits 0 regardless. Checked explicitly here (not left implicit) because a false "installed"
# claim on an unusable install silently reproduces the exact original bug this script exists
# to fix — worse, on a fork whose requirements.txt has trimmed the Browser library line (see
# that file's own header comment), nothing downstream would ever catch it either, since the
# 'rfbrowser init' step below wouldn't even run.
if ! command -v robot &>/dev/null; then
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    die "pip install reported success, but 'robot' is still not on PATH, even though the
   virtualenv at ${VIRTUAL_ENV} is active. Its bin directory should already be on PATH —
   ${VIRTUAL_ENV}/bin — so this usually means the venv was deactivated or PATH was rewritten
   mid-session. Re-activate it, then re-run: make e2e-deps"
  fi
  die "pip install reported success, but 'robot' is still not on
   PATH. pip installs --user console scripts into a user-specific bin dir that isn't always on
   PATH by default — yours is: $(python3 -m site --user-base)/bin
   Add that directory to PATH (e.g. in your shell profile), then re-run: make e2e-deps"
fi

# Browser library needs a second step beyond `pip install`: it fetches its own browser
# binaries (Playwright-backed). Only run it if the package is actually in requirements.txt —
# grepping the already-resolved file (not re-parsing tech_stack.md's free-text Framework
# field) keeps this decision coupled to one source of truth. The 'robot' PATH check just above
# already proves the --user bin dir is on PATH, so 'rfbrowser' (installed alongside it) will
# resolve too — no separate PATH check needed here.
if grep -q '^robotframework-browser' "$REQS"; then
  note "robotframework-browser is in use — running 'rfbrowser init'"
  rfbrowser init || die "rfbrowser init failed (see its own error above) — robotframework-browser
     installed but its browser binaries did not. Re-run: make e2e-deps"
fi

note "e2e deps installed."
