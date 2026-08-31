#!/usr/bin/env python3
"""Anti-self-healing guard: no agent may change an Expected_Result to make a test pass.

Self-healing is the failure mode that destroys a test suite silently — every run stays green while
the suite slowly stops asserting anything. Nobody notices, because the dashboard never changes.

Mechanism:
  1. At G4 approval, `--lock` snapshots each case's approved Expected_Result to `.expected.lock`.
  2. Every gate run diffs the current CSV against that lock.
  3. Any difference FAILS, unless design_notes.md's `## Spec change log` carries a matching revision
     entry classified `strengthens` / `neutral` / `relaxes`, and every `relaxes` cites the
     test_basis.md line or AC proving the OLD expectation was wrong.

"The system behaves differently" is never that proof. A test case binds to the specification, not to
the implementation. If the specification was wrong, that is a G0 correction to test_basis.md flowing
down through impact analysis — not a quiet edit to a cell.

Usage:
  expected-drift.py            # check every story
  expected-drift.py --lock     # snapshot current expected results (G4 approval only)
  expected-drift.py --story <dir>
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_CASES_ROOT = os.path.join(REPO_ROOT, "docs", "test_cases")

LOCK_NAME = ".expected.lock"
REVISION = re.compile(r"^###\s+Revision\s+(\d+)\s*[—-]", re.M)
CHANGE_LINE = re.compile(
    r"^-\s+(?P<verb>added|changed|removed)\s+(?P<id>TC-REQ\d+-US\d+-\d+)"
    r"(?:\s*\((?P<cls>strengthens|neutral|relaxes)\))?\s*[—-]\s*(?P<why>.+)$",
    re.I,
)
CITATION = re.compile(r"test_basis\.md#[\w-]+|US\d+#AC-\d+")


def read_expected(csv_path):
    """{Test_Case_ID: {Step_No: sha256(Expected_Result)}} — hashed so the lock stays small and
    diffing it in review shows *that* something changed without reproducing the text twice."""
    out = {}
    if not os.path.exists(csv_path):
        return out
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            cid = row.get("Test_Case_ID", "")
            step = row.get("Step_No", "")
            exp = (row.get("Expected_Result") or "").strip()
            if cid:
                out.setdefault(cid, {})[step] = hashlib.sha256(exp.encode()).hexdigest()[:16]
    return out


def parse_change_log(notes_path):
    """{Test_Case_ID: [(classification, justification_text)]} from the latest revision block."""
    if not os.path.exists(notes_path):
        return {}
    text = open(notes_path, encoding="utf-8").read()
    idx = text.find("## Spec change log")
    if idx == -1:
        return {}
    out = {}
    for line in text[idx:].splitlines():
        m = CHANGE_LINE.match(line.strip())
        if m:
            out.setdefault(m.group("id"), []).append(
                ((m.group("cls") or "").lower(), m.group("why"))
            )
    return out


def story_dirs(only=None):
    if only:
        return [os.path.abspath(only)]
    found = []
    if not os.path.isdir(TEST_CASES_ROOT):
        return found
    for req in sorted(os.listdir(TEST_CASES_ROOT)):
        req_path = os.path.join(TEST_CASES_ROOT, req)
        if not (os.path.isdir(req_path) and req.startswith("REQ")):
            continue
        for us in sorted(os.listdir(req_path)):
            us_path = os.path.join(req_path, us)
            if os.path.isdir(us_path) and os.path.exists(os.path.join(us_path, "test_cases.csv")):
                found.append(us_path)
    return found


def check_story(story):
    """Return a list of finding strings (empty means clean)."""
    findings = []
    rel = os.path.relpath(story, REPO_ROOT)
    lock_path = os.path.join(story, LOCK_NAME)
    current = read_expected(os.path.join(story, "test_cases.csv"))

    if not os.path.exists(lock_path):
        findings.append(
            f"{rel}: no {LOCK_NAME} — expected results were never locked at G4. "
            "Run `make expected-lock` as part of /approve-test-case; without it this guard is inert."
        )
        return findings

    locked = json.load(open(lock_path, encoding="utf-8"))
    changes = parse_change_log(os.path.join(story, "design_notes.md"))

    for cid, steps in locked.items():
        if cid not in current:
            if not any(c[0] for c in changes.get(cid, [])):
                findings.append(f"{rel}: {cid} was REMOVED with no classified `## Spec change log` entry")
            continue
        for step, digest in steps.items():
            now = current[cid].get(step)
            if now is None:
                if not changes.get(cid):
                    findings.append(f"{rel}: {cid} step {step} disappeared with no change-log entry")
                continue
            if now != digest:
                entries = changes.get(cid, [])
                if not entries:
                    findings.append(
                        f"{rel}: {cid} step {step} — Expected_Result CHANGED since G4 approval "
                        "with no `## Spec change log` entry. This is the anti-self-healing rule; "
                        "a silent change here is a D4 incident."
                    )
                    continue
                for cls, why in entries:
                    if not cls:
                        findings.append(
                            f"{rel}: {cid} — change-log entry is not classified "
                            "(strengthens | neutral | relaxes)"
                        )
                    elif cls == "relaxes" and not CITATION.search(why):
                        findings.append(
                            f"{rel}: {cid} — `relaxes` with no basis/AC citation proving the OLD "
                            f"expectation was wrong: {why!r}. "
                            "A spec relaxed to match observed behaviour is a weakened spec."
                        )
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lock", action="store_true", help="snapshot current expected results (G4 only)")
    ap.add_argument("--story", help="one story directory")
    args = ap.parse_args()

    dirs = story_dirs(args.story)
    if not dirs:
        print("expected-drift: no stories with a test_cases.csv — nothing to check")
        return 0

    if args.lock:
        for story in dirs:
            data = read_expected(os.path.join(story, "test_cases.csv"))
            with open(os.path.join(story, LOCK_NAME), "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
                fh.write("\n")
            print(f"expected-drift: locked {len(data)} cases in "
                  f"{os.path.relpath(story, REPO_ROOT)}/{LOCK_NAME}")
        return 0

    findings = []
    for story in dirs:
        findings.extend(check_story(story))

    if findings:
        print("expected-drift: FAIL\n", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        print("\nAn Expected_Result may never be changed to make a failing test pass. If the "
              "specification really was wrong, correct docs/test_basis.md at G0 and let the change "
              "flow down through impact analysis.", file=sys.stderr)
        return 1

    print(f"expected-drift: clean — {len(dirs)} story/stories, no unjustified expected-result changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
