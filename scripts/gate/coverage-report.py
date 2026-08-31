#!/usr/bin/env python3
"""Compute and enforce specification coverage.

There is no code coverage here — we do not own the system under test. Coverage is specification
coverage: did a test exercise this *stated behaviour*? See .claude/refs/coverage-model.md.

The denominators come from test_approach.md, ratified by a human at G2 BEFORE any case was written.
This script re-checks that the tcm.md numbers still use those denominators — a denominator that
shrank once the score was known is not a measurement, and it is the easiest way to fake this number.

Usage:
  coverage-report.py                # every story
  coverage-report.py --story <dir>
"""
import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_CASES_ROOT = os.path.join(REPO_ROOT, "docs", "test_cases")
STORIES_ROOT = os.path.join(REPO_ROOT, "docs", "stories")
TECH_STACK = os.path.join(REPO_ROOT, "docs", "test_stack.md")

DEFAULT_THRESHOLDS = {
    "ac": 1.00,
    "endpoint × status": 0.90,
    "validation rule": 0.90,
    "boundary": 0.90,
    "decision rule": 0.90,
    "state transition": 0.90,
    "exception": 0.90,
    "automation": 0.70,
}
THRESHOLD_KEYS = {
    "ac_coverage_min": "ac",
    "endpoint_status_coverage_min": "endpoint × status",
    "validation_rule_coverage_min": "validation rule",
    "boundary_coverage_min": "boundary",
    "rule_coverage_min": "decision rule",
    "transition_coverage_min": "state transition",
    "exception_coverage_min": "exception",
    "automation_coverage_min": "automation",
}
NUM = re.compile(r"(\d+)\s*/\s*(\d+)")


def load_thresholds():
    t = dict(DEFAULT_THRESHOLDS)
    if not os.path.exists(TECH_STACK):
        return t
    for line in open(TECH_STACK, encoding="utf-8"):
        for key, dim in THRESHOLD_KEYS.items():
            if line.strip().startswith(f"- {key}:"):
                m = re.search(r"(\d*\.?\d+)", line.split(":", 1)[1])
                if m:
                    t[dim] = float(m.group(1))
    return t


def table_rows(text, heading):
    """Rows of the markdown table under `heading`, as lists of stripped cells."""
    idx = text.find(heading)
    if idx == -1:
        return []
    rows = []
    for line in text[idx + len(heading):].splitlines():
        s = line.strip()
        if s.startswith("##"):
            break
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows


def parse_coverage(tcm_text):
    """{dimension: (covered, total)} from tcm.md's `## Coverage ratios` table."""
    out = {}
    for cells in table_rows(tcm_text, "## Coverage ratios"):
        if not cells:
            continue
        dim = cells[0].lower().strip("* ")
        if dim in ("dimension", ""):
            continue
        # The template uses separate Covered / Total columns; a "12/12" cell is also accepted
        # because that is how people naturally write it when editing by hand.
        m = NUM.search(" ".join(cells[1:]))
        if m:
            out[dim] = (int(m.group(1)), int(m.group(2)))
        elif len(cells) >= 3 and cells[1].isdigit() and cells[2].isdigit():
            out[dim] = (int(cells[1]), int(cells[2]))
    return out


def parse_denominators(approach_text):
    """{dimension: total} from test_approach.md's frozen denominator table."""
    out = {}
    for cells in table_rows(approach_text, "## Coverage denominators"):
        if len(cells) < 2:
            continue
        dim = cells[0].lower().strip("* ")
        m = re.search(r"\d+", cells[1])
        if dim and dim != "dimension" and m:
            out[dim] = int(m.group(0))
    return out


def noncompliance_dims(tcm_text):
    """Dimensions that have at least one recorded `## Spec non-compliance` row."""
    rows = table_rows(tcm_text, "## Spec non-compliance")
    text = " ".join(" ".join(r) for r in rows).lower()
    if "none" in text and len(rows) <= 2:
        return set()
    return {d for d in DEFAULT_THRESHOLDS if d.split()[0] in text}


def find_approach(story_dir):
    """test_approach.md lives beside the stories, not the test cases — match on REQ id."""
    req = os.path.basename(os.path.dirname(story_dir))
    if not os.path.isdir(STORIES_ROOT):
        return None
    req_id = req.split("_")[0]
    for entry in os.listdir(STORIES_ROOT):
        if entry.startswith(req_id):
            path = os.path.join(STORIES_ROOT, entry, "test_approach.md")
            if os.path.exists(path):
                return path
    return None


def story_dirs(only=None):
    if only:
        return [os.path.abspath(only)]
    found = []
    if not os.path.isdir(TEST_CASES_ROOT):
        return found
    for req in sorted(os.listdir(TEST_CASES_ROOT)):
        rp = os.path.join(TEST_CASES_ROOT, req)
        if not (os.path.isdir(rp) and req.startswith("REQ")):
            continue
        for us in sorted(os.listdir(rp)):
            up = os.path.join(rp, us)
            if os.path.isdir(up) and os.path.exists(os.path.join(up, "tcm.md")):
                found.append(up)
    return found


def report(story, thresholds):
    """Print one story's table. Returns (failed_dims, findings)."""
    rel = os.path.relpath(story, REPO_ROOT)
    tcm = open(os.path.join(story, "tcm.md"), encoding="utf-8").read()
    ratios = parse_coverage(tcm)
    recorded = noncompliance_dims(tcm)
    findings, failed = [], []

    if not ratios:
        return ["<no ratios>"], [f"{rel}: tcm.md has no parseable `## Coverage ratios` table"]

    approach_path = find_approach(story)
    frozen = parse_denominators(open(approach_path, encoding="utf-8").read()) if approach_path else {}

    print(f"\n{rel}")
    print(f"  {'dimension':<22}{'covered/total':>16}{'ratio':>9}{'min':>8}   status")
    print("  " + "─" * 66)
    for dim, (cov, total) in sorted(ratios.items()):
        thr = thresholds.get(dim)
        ratio = (cov / total) if total else 0.0
        ok = thr is None or ratio >= thr - 1e-9
        status = "PASS" if ok else "FAIL"
        if not ok:
            failed.append(dim)
            if dim not in recorded:
                findings.append(
                    f"{rel}: {dim} at {ratio:.2f} < {thr:.2f} and the shortfall is NOT recorded in "
                    "`## Spec non-compliance` — an unrecorded shortfall is an omission, not a decision"
                )
        print(f"  {dim:<22}{f'{cov}/{total}':>16}{ratio:>9.2f}"
              f"{(f'{thr:.2f}' if thr is not None else '—'):>8}   {status}")

        if dim in frozen and total != frozen[dim]:
            findings.append(
                f"{rel}: {dim} denominator is {total} but test_approach.md froze it at "
                f"{frozen[dim]} at G2. A denominator that moved after the score was known is not a "
                "measurement — this needs a G2 reopen with a recorded reason."
            )
    return failed, findings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", help="one story directory")
    args = ap.parse_args()

    thresholds = load_thresholds()
    dirs = story_dirs(args.story)
    if not dirs:
        print("coverage: no stories with a tcm.md — nothing to measure")
        return 0

    all_findings, any_failed = [], False
    for story in dirs:
        failed, findings = report(story, thresholds)
        any_failed = any_failed or bool(failed)
        all_findings.extend(findings)

    print()
    if all_findings:
        for f in all_findings:
            print(f"  ! {f}", file=sys.stderr)
        print()
    if any_failed or all_findings:
        print("QA GATE: FAIL — coverage")
        return 1
    print("QA GATE: PASS — coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
