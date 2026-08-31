#!/usr/bin/env python3
"""Read-only drift-guard for docs/test_cases/TEST_BASELINE.md.

This NEVER writes to the baseline, never flips a State, and never touches an entry's
authored prose. qa-analyst owns all of that (Author mode sets the pending State; Script
review mode flips pending -> confirmed). This script only audits, and reports.

Two audits:

  DRIFT      — a CONFIRMED entry whose reality doesn't match its State:
                 active / modified_by_REQ[N]  -> the test case MUST exist in the suite
                 removed_by_REQ[N]            -> the test case MUST NOT exist
  STALE      — a PENDING entry (planned / modify_pending_* / remove_pending_*) that has
               been left behind:
                 hard  — the round closed (both Approvals `approved`) but the entry was
                         never confirmed; qa-analyst's script review skipped it
                 soft  — the round has been open longer than --stale-days

Exit codes:
  0  clean (or report-only mode with findings, see --check)
  1  findings AND --check was passed
  2  bad invocation / a required input file is unreadable

Usage:
  baseline-drift.py                 # report only, always exit 0   (`make e2e-baseline`)
  baseline-drift.py --check         # exit 1 on any finding  (`make e2e-baseline-check`)
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_BASELINE = os.path.join(REPO_ROOT, "docs", "test_cases", "TEST_BASELINE.md")
DEFAULT_SUITE = os.path.join(REPO_ROOT, "tests", "e2e", "test_suites", "e2e_baseline.robot")

# State vocabulary — see docs/tech_stack.md -> e2e_baseline.
PENDING_STATES = ("planned", "modify_pending_REQ", "remove_pending_REQ")
E2E_ID_RE = re.compile(r"\bE2E-[A-Za-z0-9_-]+\b")

# A full-detail block header: `### E2E-REQ001-US001-001 — scenario name`
ENTRY_HEADER_RE = re.compile(r"^###\s+(E2E-[A-Za-z0-9_-]+)\b(.*)$")
# A `| State | planned |` row inside an entry's field table.
STATE_ROW_RE = re.compile(r"^\|\s*State\s*\|\s*([^|]+?)\s*\|", re.IGNORECASE)
# `**Test case Approval:** approved`
APPROVAL_RE = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*?)\s*$")


def die(msg: str) -> None:
    print(f"baseline-drift: {msg}", file=sys.stderr)
    sys.exit(2)


def strip_fenced_blocks(lines: list[str]) -> list[str]:
    """Blank out fenced code blocks.

    TEST_BASELINE.md carries ```markdown examples (the entry-format sample, the approval-log
    sample). Those contain real-looking E2E IDs and States; parsing them would invent
    entries that don't exist. Lines are blanked rather than dropped so line numbers in
    findings still point at the real file.
    """
    out, in_fence = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return out


def parse_baseline(path: str):
    """-> (entries, approval) where entries = [(e2e_id, state, lineno)]."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().splitlines()
    except OSError as e:
        die(f"cannot read baseline {path}: {e}")

    lines = strip_fenced_blocks(raw)

    approval: dict[str, str] = {}
    for line in lines:
        m = APPROVAL_RE.match(line.strip())
        if m:
            approval[m.group(1).strip()] = m.group(2).strip()

    entries: list[tuple[str, str, int]] = []
    current_id: str | None = None
    current_line = 0
    for i, line in enumerate(lines, start=1):
        hm = ENTRY_HEADER_RE.match(line)
        if hm:
            if current_id:  # previous entry had no State row
                entries.append((current_id, "", current_line))
            current_id, current_line = hm.group(1), i
            continue
        if current_id:
            sm = STATE_ROW_RE.match(line)
            if sm:
                entries.append((current_id, sm.group(1).strip(), current_line))
                current_id = None
    if current_id:
        entries.append((current_id, "", current_line))

    return entries, approval


def parse_suite(path: str) -> set[str]:
    """Collect every E2E-* ID the suite actually declares, from `[Tags]` lines.

    Tags are the authority: Robot's --include filters by tag alone, so an ID that appears
    only in a test case name or [Documentation] is not selectable and does not count as
    implemented (see docs/tech_stack.md -> e2e_organization).
    """
    if not os.path.isfile(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        die(f"cannot read suite {path}: {e}")

    ids: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.lower().startswith("[tags]"):
            ids.update(E2E_ID_RE.findall(stripped))
    return ids


def is_pending(state: str) -> bool:
    return any(state.startswith(p) for p in PENDING_STATES)


def round_age_days(started: str) -> int | None:
    started = started.strip()
    if not started or started in {"—", "-"}:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            when = dt.datetime.strptime(started, fmt)
        except ValueError:
            continue
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        return (now - when).days
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--suite", default=DEFAULT_SUITE)
    ap.add_argument("--check", action="store_true", help="exit 1 when anything is flagged")
    ap.add_argument("--stale-days", type=int, default=14, help="soft-stale threshold for an open round (default 14)")
    args = ap.parse_args()

    entries, approval = parse_baseline(args.baseline)
    implemented = parse_suite(args.suite)

    rel_baseline = os.path.relpath(args.baseline, REPO_ROOT)
    rel_suite = os.path.relpath(args.suite, REPO_ROOT)

    print(f"baseline: {rel_baseline} ({len(entries)} entr{'y' if len(entries) == 1 else 'ies'})")
    if os.path.isfile(args.suite):
        print(f"suite:    {rel_suite} ({len(implemented)} tagged E2E ID{'' if len(implemented) == 1 else 's'})")
    else:
        print(f"suite:    {rel_suite} (does not exist yet)")

    if not entries:
        print("\nNothing to audit — no baseline entries yet. Clean.")
        return 0

    tc_approval = approval.get("Test case Approval", "—")
    script_approval = approval.get("E2E Script Approval", "—")
    round_closed = tc_approval == "approved" and script_approval == "approved"
    age = round_age_days(approval.get("Round started", ""))

    drift: list[str] = []
    stale: list[str] = []

    for e2e_id, state, lineno in entries:
        loc = f"{rel_baseline}:{lineno}"
        if not state:
            drift.append(f"{loc}  {e2e_id}: entry has no `| State | ... |` row — cannot audit")
            continue

        if is_pending(state):
            if round_closed:
                stale.append(
                    f"{loc}  {e2e_id}: State `{state}` is still PENDING but the round is closed "
                    f"(both Approvals `approved`) — qa-analyst's script review never confirmed it"
                )
            elif age is not None and age > args.stale_days:
                stale.append(
                    f"{loc}  {e2e_id}: State `{state}` pending for {age} days "
                    f"(round opened {approval.get('Round started', '?')}, threshold {args.stale_days})"
                )
            continue

        present = e2e_id in implemented
        if state.startswith("removed_by_REQ"):
            if present:
                drift.append(
                    f"{loc}  {e2e_id}: State `{state}` says removed, but the test case is still "
                    f"present in {rel_suite} — delete it (never comment it out)"
                )
        elif state == "active" or state.startswith("modified_by_REQ"):
            if not present:
                drift.append(
                    f"{loc}  {e2e_id}: State `{state}` says implemented, but no test case in "
                    f"{rel_suite} carries `{e2e_id}` in its `[Tags]`"
                )
        else:
            drift.append(f"{loc}  {e2e_id}: unrecognised State `{state}`")

    orphans = sorted(implemented - {e for e, _, _ in entries})
    for orphan in orphans:
        drift.append(
            f"{rel_suite}  {orphan}: test case exists in the suite but has no entry in "
            f"{rel_baseline} — every test traces back to a baseline entry"
        )

    for title, findings in (("DRIFT", drift), ("STALE PENDING", stale)):
        if findings:
            print(f"\n{title} ({len(findings)}):")
            for f in findings:
                print(f"  - {f}")

    total = len(drift) + len(stale)
    if total == 0:
        print("\nClean — no drift, no stale pending entries.")
        return 0

    print(f"\n{total} finding(s). This is an audit: fix the underlying artifact, never edit a State to silence it.")
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
