#!/usr/bin/env python3
"""Artifact validator — the automated pre-check every human gate runs behind.

The rule this enforces (see .claude/refs/gate-runbook.md): a human gate never runs on an artifact
that has not passed its own machine checks. A reviewer asked to check arithmetic, missing fields and
dangling references will eventually stop reading carefully; a reviewer who only ever sees internally
consistent artifacts can spend their attention on the thing no script can check — is this actually
right?

Exit codes:
  0  PASS  (prints `QA GATE: PASS`)
  1  a check failed
  2  the gate could not reach a verdict (missing tool, unreadable file) — this is NOT an artifact
     failure; it routes to whoever owns the tooling, never back to the agent whose work was never
     actually checked.

Usage:
  validate-artifacts.py [--req REQ001] [--story <dir>]
"""
import argparse
import csv
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_CASES_ROOT = os.path.join(REPO_ROOT, "docs", "test_cases")
STORIES_ROOT = os.path.join(REPO_ROOT, "docs", "stories")
BASIS = os.path.join(REPO_ROOT, "docs", "test_basis.md")
SUITE = os.path.join(REPO_ROOT, "tests", "e2e", "test_suites", "e2e_baseline.robot")
ENV_YAML = os.path.join(REPO_ROOT, "tests", "e2e", "config", "environment.yaml")

VAGUE = re.compile(
    r"^\s*(should\s+(fail|work|pass|succeed)|error(\s+is)?\s+displayed|works?\s+correctly|"
    r"responds?\s+correctly|as\s+expected|ok|success|correct|no\s+error)\s*\.?\s*$",
    re.I,
)
PLACEHOLDER = re.compile(r"<TBD|TODO:|FIXME|\[\.\.\.\]|xxx", re.I)
AC_ROW = re.compile(r"^\|\s*(AC-\d+)\s*\|")
ANCHOR = re.compile(r'<a\s+id="([^"]+)"|^#{1,6}\s+(.+)$', re.M)
BASIS_REF = re.compile(r"^(?:(?P<file>[\w./-]+\.md)#(?P<anchor>[\w-]+)|(?P<us>US\d+)#(?P<ac>AC-\d+))$")
IDENTITY = re.compile(r"\|([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|")


class Findings:
    def __init__(self):
        self.items = []

    def add(self, where, msg):
        self.items.append((where, msg))

    def __bool__(self):
        return bool(self.items)


def slugify(heading):
    s = heading.strip().lower()
    s = re.sub(r"[`*_]", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s]+", "-", s).strip("-")


def basis_anchors():
    """Explicit <a id> anchors plus GitHub-style heading slugs."""
    if not os.path.exists(BASIS):
        return None
    text = open(BASIS, encoding="utf-8").read()
    out = set()
    for m in ANCHOR.finditer(text):
        if m.group(1):
            out.add(m.group(1))
        elif m.group(2):
            out.add(slugify(m.group(2)))
    return out


def suite_tags():
    if not os.path.exists(SUITE):
        return None
    tags = set()
    for line in open(SUITE, encoding="utf-8"):
        s = line.strip()
        if s.startswith("[Tags]"):
            tags.update(t.strip() for t in re.split(r"\s{2,}|\t", s[len("[Tags]"):]) if t.strip())
    return tags


def known_envs():
    if not os.path.exists(ENV_YAML):
        return {"local", "sit", "uat"}
    text = open(ENV_YAML, encoding="utf-8").read()
    found = {m for m in re.findall(r"^\s{2,4}(\w+):\s*$", text, re.M)}
    return found or {"local", "sit", "uat"}


def atomic_acs(req_dir):
    """AC IDs from every story_analysis.md under a REQ."""
    acs = set()
    for entry in os.listdir(req_dir):
        if entry.endswith("story_analysis.md") or entry == "story_analysis.md":
            for line in open(os.path.join(req_dir, entry), encoding="utf-8"):
                m = AC_ROW.match(line.strip())
                if m:
                    acs.add(m.group(1))
    return acs


def check_csv(story, f, anchors, tags, envs):
    rel = os.path.relpath(story, REPO_ROOT)
    path = os.path.join(story, "test_cases.csv")
    if not os.path.exists(path):
        f.add(rel, "test_cases.csv missing — run `make testcases`")
        return set(), set()

    covered_acs, case_ids = set(), set()
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for n, row in enumerate(csv.DictReader(fh), start=2):
            cid = row.get("Test_Case_ID", "").strip()
            where = f"{rel}/test_cases.csv:{n}"
            if not cid:
                f.add(where, "row has no Test_Case_ID")
                continue
            case_ids.add(cid)
            for ac in re.findall(r"AC-\d+", row.get("AC_Ref", "")):
                covered_acs.add(ac)

            exp = (row.get("Expected_Result") or "").strip()
            if not exp:
                f.add(where, f"{cid} step {row.get('Step_No')} has an empty Expected_Result")
            elif len(exp) < 15 or VAGUE.match(exp):
                f.add(where, f"{cid} step {row.get('Step_No')}: Expected_Result is vague — {exp!r}. "
                             "Name the status, the fields, the values")

            ref = (row.get("Basis_Ref") or "").strip().strip("`")
            if not ref:
                f.add(where, f"{cid}: no Basis_Ref. An expected result with no oracle is D3 by default")
            else:
                m = BASIS_REF.match(ref)
                if not m:
                    f.add(where, f"{cid}: malformed Basis_Ref {ref!r} — "
                                 "expected `test_basis.md#anchor` or `US001#AC-3`")
                elif m.group("anchor") and anchors is not None and m.group("anchor") not in anchors:
                    f.add(where, f"{cid}: Basis_Ref anchor #{m.group('anchor')} not found in test_basis.md")

            if (row.get("Automatable") or "").strip().upper() == "Y":
                aid = (row.get("Automation_ID") or "").strip()
                if not aid:
                    f.add(where, f"{cid}: Automatable=Y with no Automation_ID")
                elif tags is not None and aid not in tags:
                    f.add(where, f"{cid}: Automation_ID {aid} is not a [Tags] entry in the suite — "
                                 "`--include` filters by tag alone, so this case cannot be selected")

            scope = [s.strip() for s in (row.get("Env_Scope") or "").split(";") if s.strip()]
            if not scope:
                f.add(where, f"{cid}: empty Env_Scope")
            for env in scope:
                if env not in envs:
                    f.add(where, f"{cid}: Env_Scope names unknown environment {env!r}")
    return covered_acs, case_ids


def check_placeholders(path, f):
    rel = os.path.relpath(path, REPO_ROOT)
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if PLACEHOLDER.search(line):
            f.add(f"{rel}:{n}", f"unresolved placeholder — {line.strip()[:70]!r}")


def check_impact(req_dir, f):
    path = os.path.join(req_dir, "impact_analysis.md")
    if not os.path.exists(path):
        f.add(os.path.relpath(req_dir, REPO_ROOT), "impact_analysis.md missing")
        return
    rel = os.path.relpath(path, REPO_ROOT)
    text = open(path, encoding="utf-8").read()
    idx = text.find("### Coverage reconciliation")
    if idx == -1:
        f.add(rel, "no `### Coverage reconciliation` table")
        return
    checked = 0
    # skip the heading line itself — it starts with "##" and would trip the break below
    for line in text[idx:].splitlines()[1:]:
        s = line.strip()
        if s.startswith("##"):
            break
        m = IDENTITY.match(s)
        if not m:
            continue
        feature = m.group(1).strip().strip("_*")
        existing, kept, modified, removed, netnew, target = (int(m.group(i)) for i in range(2, 8))
        checked += 1
        if kept + modified + netnew != target:
            f.add(rel, f"reconciliation for {feature!r}: Kept+Modified+Net-new "
                       f"({kept}+{modified}+{netnew}={kept+modified+netnew}) != Target ({target})")
        if existing - removed != kept + modified:
            f.add(rel, f"reconciliation for {feature!r}: Existing−Removed "
                       f"({existing}−{removed}={existing-removed}) != Kept+Modified ({kept+modified})")
    if checked == 0:
        f.add(rel, "reconciliation table has no parseable numeric rows — the arithmetic is the "
                   "whole point of this table")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--req", help="limit to one REQ id, e.g. REQ001")
    ap.add_argument("--story", help="one story directory")
    args = ap.parse_args()

    f = Findings()
    anchors, tags, envs = basis_anchors(), suite_tags(), known_envs()

    if anchors is None:
        print("validate: docs/test_basis.md not found — Basis_Ref anchors cannot be checked",
              file=sys.stderr)
    if tags is None:
        print("validate: e2e suite not found — Automation_ID tags cannot be checked", file=sys.stderr)

    stories = []
    if args.story:
        stories = [os.path.abspath(args.story)]
    elif os.path.isdir(TEST_CASES_ROOT):
        for req in sorted(os.listdir(TEST_CASES_ROOT)):
            if not req.startswith("REQ") or (args.req and not req.startswith(args.req)):
                continue
            rp = os.path.join(TEST_CASES_ROOT, req)
            if not os.path.isdir(rp):
                continue
            for us in sorted(os.listdir(rp)):
                up = os.path.join(rp, us)
                if os.path.isdir(up):
                    stories.append(up)

    if not stories:
        print("validate: no story directories found — nothing to validate")
        print("QA GATE: PASS")
        return 0

    for story in stories:
        covered, _ = check_csv(story, f, anchors, tags, envs)
        for name in ("design_notes.md", "tcm.md"):
            p = os.path.join(story, name)
            if os.path.exists(p):
                check_placeholders(p, f)
            else:
                f.add(os.path.relpath(story, REPO_ROOT), f"{name} missing")

        # AC coverage must be 1.00 — an uncovered criterion is a requirement nobody tested
        req_id = os.path.basename(os.path.dirname(story)).split("_")[0]
        req_dirs = [os.path.join(STORIES_ROOT, e) for e in os.listdir(STORIES_ROOT)
                    if e.startswith(req_id)] if os.path.isdir(STORIES_ROOT) else []
        for rd in req_dirs:
            expected = atomic_acs(rd)
            missing = expected - covered
            if missing:
                f.add(os.path.relpath(story, REPO_ROOT),
                      f"AC coverage is not 1.00 — no test case for {', '.join(sorted(missing))}")

    for rd in {os.path.join(STORIES_ROOT, e) for e in (os.listdir(STORIES_ROOT)
               if os.path.isdir(STORIES_ROOT) else []) if e.startswith("REQ")
               and (not args.req or e.startswith(args.req))}:
        check_impact(rd, f)

    # the anti-self-healing guard is part of this gate, not a separate opt-in step
    drift = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "scripts", "gate", "expected-drift.py")],
        capture_output=True, text=True)
    if drift.returncode == 1:
        f.add("expected-drift", drift.stderr.strip() or "expected-result drift detected")
    elif drift.returncode not in (0, 1):
        print(f"validate: expected-drift.py could not run:\n{drift.stderr}", file=sys.stderr)
        return 2

    if f:
        print("\nvalidate: FAIL\n", file=sys.stderr)
        for where, msg in f.items:
            print(f"  {where}\n      {msg}", file=sys.stderr)
        print(f"\n{len(f.items)} finding(s)", file=sys.stderr)
        print("QA GATE: FAIL")
        return 1

    print(f"validate: {len(stories)} story/stories checked, no findings")
    print("QA GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
