#!/usr/bin/env python3
"""Run the E2E suite and enforce the gate's zero-skip rule.

Robot Framework's own exit code counts FAILED tests only — a skipped test exits 0 and
looks green. `.claude/refs/gate-runbook.md` requires the opposite: "a skipped test is a
failure, never a neutral no-op" — 100% green means every summary line shows zero skipped
alongside zero failed. Nothing enforced that until this script; it re-reads output.xml
after the run and fails on skips as well as failures.

Output goes to a date/time-nested directory under tests/e2e/test_results/ so no run ever
overwrites another's trio (output.xml / log.html / report.html).

Exit codes:
  0  every test passed — zero failed AND zero skipped
  1  at least one test failed or was skipped (a real gate FAIL)
  2  the run could not produce a clear verdict — robot missing, bad data, no tests
     matched, no output.xml. This is `blocked_gate` territory, not a code defect.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
E2E_ROOT = os.path.join(REPO_ROOT, "tests", "e2e")
RESULTS_ROOT = os.path.join(E2E_ROOT, "test_results")

# Robot's documented exit codes: 0 = all passed, 1..250 = that many failed tests,
# 251+ = the run itself did not complete (bad CLI data, no tests matched, internal error).
ROBOT_RUN_BROKEN = 251


def die(msg: str) -> int:
    print(f"run-e2e: {msg}", file=sys.stderr)
    return 2


def parse_totals(output_xml: str):
    """-> (pass, fail, skip) from output.xml's <statistics><total> stat row."""
    try:
        root = ET.parse(output_xml).getroot()
    except (ET.ParseError, OSError) as e:
        raise RuntimeError(f"cannot read {output_xml}: {e}") from e

    stat = root.find("./statistics/total/stat")
    if stat is None:
        raise RuntimeError(f"{output_xml} has no <statistics><total><stat> row")

    # `skip` exists from Robot Framework 4.0 on. Its ABSENCE is not "zero skips" — it means
    # this Robot cannot report skips at all, so the zero-skip rule is unenforceable and the
    # run cannot be trusted as green. Signal that with None rather than silently reading 0,
    # which would turn a broken gate into a passing one.
    raw_skip = stat.get("skip")
    return (
        int(stat.get("pass", 0)),
        int(stat.get("fail", 0)),
        int(raw_skip) if raw_skip is not None else None,
    )


def list_skipped(output_xml: str) -> list[str]:
    """Names of the skipped tests, so the report says WHICH ones — not just how many."""
    try:
        root = ET.parse(output_xml).getroot()
    except (ET.ParseError, OSError):
        return []
    names = []
    for test in root.iter("test"):
        status = test.find("status")
        if status is not None and status.get("status") == "SKIP":
            name = test.get("name", "<unnamed>")
            msg = (status.text or "").strip().splitlines()
            names.append(f"{name}" + (f" — {msg[0]}" if msg else ""))
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default=os.environ.get("ENV", "local"),
                    help="target environment: local (default) | sit | uat")
    ap.add_argument("--include", default=os.environ.get("INCLUDE", ""),
                    help="optional Robot tag to select by (e.g. US001 or an E2E-* ID); empty = whole suite")
    ap.add_argument("--suite-root", default=E2E_ROOT)
    ap.add_argument("--results-root", default=RESULTS_ROOT)
    args = ap.parse_args()

    if shutil.which("robot") is None:
        return die("`robot` is not installed or not on PATH — the gate cannot reach a PASS/FAIL verdict")
    if not os.path.isdir(args.suite_root):
        return die(f"e2e root {os.path.relpath(args.suite_root, REPO_ROOT)} does not exist")

    now = dt.datetime.now()
    outdir = os.path.join(args.results_root, now.strftime("%Y-%m-%d"), now.strftime("%H-%M-%S"))
    os.makedirs(outdir, exist_ok=True)

    cmd = ["robot", "--variable", f"ENV:{args.env}", "--outputdir", outdir]
    if args.include:
        cmd += ["--include", args.include]
    cmd.append(args.suite_root)

    rel_out = os.path.relpath(outdir, REPO_ROOT)
    print(f"run-e2e: ENV={args.env}" + (f" INCLUDE={args.include}" if args.include else ""))
    print(f"run-e2e: {' '.join(cmd)}")
    print(f"run-e2e: results -> {rel_out}\n")

    robot_rc = subprocess.run(cmd).returncode

    output_xml = os.path.join(outdir, "output.xml")
    if not os.path.isfile(output_xml):
        return die(f"robot exited {robot_rc} without writing output.xml — the run did not complete")
    if robot_rc >= ROBOT_RUN_BROKEN:
        return die(f"robot exited {robot_rc} — the run itself failed (bad data / no tests matched), "
                   "not a test result")

    try:
        passed, failed, skipped = parse_totals(output_xml)
    except RuntimeError as e:
        return die(str(e))

    if skipped is None:
        return die(
            f"{os.path.relpath(output_xml, REPO_ROOT)} reports no `skip` count — this Robot "
            "predates 4.0 and cannot report skipped tests, so the zero-skip gate rule is "
            "unenforceable. Treat as a broken gate (upgrade Robot Framework), never as a pass."
        )

    total = passed + failed + skipped
    # The verbatim line agents are required to paste as run evidence.
    print(f"\n{total} tests, {passed} passed, {failed} failed, {skipped} skipped")
    print(f"Output:  {rel_out}/output.xml")
    print(f"Log:     {rel_out}/log.html")
    print(f"Report:  {rel_out}/report.html")

    if total == 0:
        return die("no tests ran — an empty run is not a pass")

    if skipped:
        print(f"\nGATE FAIL: {skipped} test(s) skipped. A skipped test is a gate FAILURE, never a "
              f"neutral no-op (see .claude/refs/gate-runbook.md).", file=sys.stderr)
        for name in list_skipped(output_xml):
            print(f"  - {name}", file=sys.stderr)
        print("Fix the test for real, or delete it with a documented reason — never leave it "
              "tagged as skipped/quarantined.", file=sys.stderr)

    if failed:
        print(f"\nGATE FAIL: {failed} test(s) failed. See {rel_out}/log.html", file=sys.stderr)

    return 1 if (failed or skipped) else 0


if __name__ == "__main__":
    sys.exit(main())
