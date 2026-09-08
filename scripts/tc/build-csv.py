#!/usr/bin/env python3
"""Generate test_cases.csv from design_notes.md.

design_notes.md is the human-reviewable source of truth; the CSV is a build artifact. If both
were hand-written they would disagree within two requirements — that is not a prediction, it is
what always happens to duplicated state. `make testcases-check` regenerates to a temp file and
diffs, so a hand-edited CSV fails the gate.

Emits, per story directory:
  test_cases.csv        one row per STEP, case-level fields repeated (filterable in Excel)
  test_cases_index.csv  one row per CASE, for counting and reporting

Encoding is utf-8-sig on purpose: without the BOM, Excel on Windows renders Thai as mojibake,
which is the single most common way this deliverable arrives broken.

Usage:
  build-csv.py                    # every story under docs/test_cases/
  build-csv.py --story <dir>      # one story directory
  build-csv.py --check            # build to temp, diff against committed; non-zero on drift
"""
import argparse
import csv
import io
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEST_CASES_ROOT = os.path.join(REPO_ROOT, "docs", "test_cases")

COLUMNS = [
    "Test_Case_ID", "REQ_ID", "US_ID", "AC_Ref", "Test_Level", "Test_Type",
    "Design_Technique", "Priority", "Test_Description", "Preconditions", "Test_Data",
    "Step_No", "Test_Step", "Expected_Result", "Postcondition", "Automatable",
    "Automation_ID", "Env_Scope", "Basis_Ref", "Status", "Defect_ID", "Notes",
]
INDEX_COLUMNS = [c for c in COLUMNS if c not in ("Step_No", "Test_Step", "Expected_Result")]

CASE_HEADING = re.compile(r"^###\s+(TC-REQ\d+-US\d+-\d+)\s*[—-]\s*(.+?)\s*$")
FIELD = re.compile(r"^-\s+\*\*(?P<key>[^*]+?):\*\*\s*(?P<val>.*)$")
# A step is three lines: a numbered action, a blank line, "**Expected [CPn]:** ..." on its own
# line, a blank line, "**Basis:** `anchor`" on its own line — see qa-templates.md's "Steps,
# checkpoints, and basis" note for why each of those is its own line rather than one long one.
STEP_NO = re.compile(r"^\s*(?P<no>\d+)\.\s+(?P<action>.+?)\s*$")
STEP_EXPECTED = re.compile(r"^\s*\*\*Expected\s*\[CP(?P<cp>\d+)\]:\*\*\s*(?P<exp>.+?)\s*$")
STEP_BASIS = re.compile(r"^\s*\*\*Basis:\*\*\s*`(?P<basis>[^`]+)`\s*$")
VERIFICATION_TAG = re.compile(r"`\[verification\]`\s*$")
ID_PARTS = re.compile(r"^TC-(REQ\d+)-(US\d+)-\d+$")


class ParseError(Exception):
    pass


def _split_inline(value):
    """`Level: api · Type: positive · Technique: EP · Priority: P1` -> dict."""
    out = {}
    for chunk in re.split(r"\s+·\s+|\s+\|\s+", value):
        if ":" in chunk:
            k, v = chunk.split(":", 1)
            # Segments after the first still carry their markdown emphasis: the FIELD regex
            # consumed only the leading `- **Key:**`, so `**Type:** boundary` arrives intact.
            k = k.strip().strip("*").strip().lower()
            out[k] = v.strip().strip("*").strip()
    return out


def parse_design_notes(path):
    """Return a list of case dicts. Raises ParseError with a line number on malformed input."""
    cases = []
    current = None
    in_cases = False
    in_steps = False

    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()

    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")

        if line.startswith("## "):
            in_cases = line.strip().lower().startswith("## test cases")
            if not in_cases and current:
                cases.append(current)
                current = None
            in_steps = False
            continue
        if not in_cases:
            continue

        m = CASE_HEADING.match(line)
        if m:
            if current:
                cases.append(current)
            current = {
                "Test_Case_ID": m.group(1),
                "Test_Description": m.group(2).strip(),
                "steps": [],
                "_line": lineno,
            }
            parts = ID_PARTS.match(m.group(1))
            if not parts:
                raise ParseError(f"{path}:{lineno}: malformed test case ID {m.group(1)!r}")
            current["REQ_ID"], current["US_ID"] = parts.group(1), parts.group(2)
            in_steps = False
            continue

        if current is None:
            continue

        m = FIELD.match(line)
        if m:
            key, val = m.group("key").strip().lower(), m.group("val").strip()
            in_steps = (key == "steps")
            if key == "ac":
                current["AC_Ref"] = val
            elif key == "basis ref":
                current["Basis_Ref"] = val.strip("`")
            elif key == "preconditions":
                current["Preconditions"] = val
            elif key == "test data":
                current["Test_Data"] = val
            elif key == "postcondition":
                current["Postcondition"] = val
            elif key == "notes":
                current["Notes"] = val
            elif key == "steps":
                pass  # steps follow as numbered blocks, handled below
            else:
                inline = _split_inline(f"{m.group('key').strip()}: {val}")
                mapping = {
                    "level": "Test_Level", "type": "Test_Type",
                    "technique": "Design_Technique", "priority": "Priority",
                    "automatable": "Automatable", "automation id": "Automation_ID",
                    "env scope": "Env_Scope",
                }
                for k, v in inline.items():
                    if k in mapping:
                        current[mapping[k]] = v.strip("`")
            continue

        if not in_steps or not line.strip():
            continue

        m = STEP_NO.match(line)
        if m:
            action = VERIFICATION_TAG.sub("[verification]", m.group("action").strip())
            current["steps"].append({
                "Step_No": m.group("no"),
                "Test_Step": action,
                "Expected_Result": "",
            })
            continue

        m = STEP_EXPECTED.match(line)
        if m and current["steps"]:
            current["steps"][-1]["Expected_Result"] = f"[CP{m.group('cp')}] {m.group('exp').strip()}"
            continue

        m = STEP_BASIS.match(line)
        if m and current["steps"]:
            current["steps"][-1]["Basis_Ref"] = m.group("basis").strip()
            continue

    if current:
        cases.append(current)
    return cases


def rows_for(cases, source):
    """Flatten cases to step-level rows. Raises ParseError on a case with no steps."""
    rows = []
    for case in cases:
        if not case["steps"]:
            raise ParseError(
                f"{source}:{case['_line']}: {case['Test_Case_ID']} has no steps — every case "
                "needs at least one numbered action followed by an `**Expected [CPn]:**` line"
            )
        for step in case["steps"]:
            if not step["Expected_Result"]:
                raise ParseError(
                    f"{source}:{case['_line']}: {case['Test_Case_ID']} step {step['Step_No']} "
                    "has no `**Expected [CPn]:**` line — every numbered step needs one"
                )
            row = {c: "" for c in COLUMNS}
            for k, v in case.items():
                if k in row:
                    row[k] = v
            row.update(step)
            row.setdefault("Status", "")
            if not row["Status"]:
                row["Status"] = "Not Run"
            row["Env_Scope"] = row["Env_Scope"].replace(", ", ";").replace(",", ";")
            rows.append(row)
    return rows


def index_rows(rows):
    seen, out = set(), []
    for row in rows:
        cid = row["Test_Case_ID"]
        if cid in seen:
            continue
        seen.add(cid)
        out.append({c: row.get(c, "") for c in INDEX_COLUMNS})
    return out


def render(rows, columns):
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\r\n",
                            quoting=csv.QUOTE_MINIMAL, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def story_dirs(only=None):
    if only:
        return [os.path.abspath(only)]
    found = []
    for req in sorted(os.listdir(TEST_CASES_ROOT)) if os.path.isdir(TEST_CASES_ROOT) else []:
        req_path = os.path.join(TEST_CASES_ROOT, req)
        if not os.path.isdir(req_path) or not req.startswith("REQ"):
            continue
        for us in sorted(os.listdir(req_path)):
            us_path = os.path.join(req_path, us)
            if os.path.isdir(us_path) and os.path.exists(os.path.join(us_path, "design_notes.md")):
                found.append(us_path)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", help="one story directory")
    ap.add_argument("--check", action="store_true",
                    help="verify committed CSVs match what the source would generate")
    args = ap.parse_args()

    dirs = story_dirs(args.story)
    if not dirs:
        print("build-csv: no story directories with design_notes.md found — nothing to do")
        return 0

    drift, errors = [], []
    for story in dirs:
        src = os.path.join(story, "design_notes.md")
        try:
            cases = parse_design_notes(src)
            rows = rows_for(cases, src)
        except ParseError as exc:
            errors.append(str(exc))
            continue

        if not rows:
            errors.append(f"{src}: parsed 0 test cases — check the `## Test cases` section format")
            continue

        for name, payload in (
            ("test_cases.csv", render(rows, COLUMNS)),
            ("test_cases_index.csv", render(index_rows(rows), INDEX_COLUMNS)),
        ):
            dest = os.path.join(story, name)
            if args.check:
                existing = ""
                if os.path.exists(dest):
                    with open(dest, encoding="utf-8-sig", newline="") as fh:
                        existing = fh.read()
                if existing != payload:
                    drift.append(dest)
            else:
                with open(dest, "w", encoding="utf-8-sig", newline="") as fh:
                    fh.write(payload)
                rel = os.path.relpath(dest, REPO_ROOT)
                print(f"build-csv: wrote {rel} ({len(rows) if name.endswith('cases.csv') else len(index_rows(rows))} rows)")

    if errors:
        for e in errors:
            print(f"build-csv: ERROR {e}", file=sys.stderr)
        return 2

    if args.check:
        if drift:
            print("build-csv: DRIFT — these CSVs do not match design_notes.md:", file=sys.stderr)
            for d in drift:
                print(f"  {os.path.relpath(d, REPO_ROOT)}", file=sys.stderr)
            print("\nA CSV is a build artifact. Edit design_notes.md and run `make testcases`.",
                  file=sys.stderr)
            return 1
        print("build-csv: no drift — every CSV matches its design_notes.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
