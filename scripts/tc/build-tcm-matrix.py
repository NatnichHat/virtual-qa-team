#!/usr/bin/env python3
"""Generate tcm_matrix.csv — the wide X-mapping Coverage Matrix — from design_notes.md.

tcm.md no longer hand-authors an "AC -> test traceability" narrative table. Instead, the
Derivation tables that design_notes.md already writes (Equivalence classes, Boundary analysis,
Decision table(s), State transitions, Exception coverage) already record, per row, which
Test_Case_ID(s) cover it. This script inverts that: one dimension-value per column, one
Test_Case_ID per row, lowercase 'x' where that case's derivation cites that dimension-value.

Control this preserves from coverage-model.md #1 ("the denominator is derived, not chosen"): the
matrix is never hand-typed. A dimension that never appears in a Derivation table cannot silently
gain an 'x', and a case that was never linked to a dimension in the derivation cannot silently gain
one either — the count report's "Actual" column is exactly what this script counts.

Usage:
  build-tcm-matrix.py --story docs/test_cases/REQ001_x/US001
  build-tcm-matrix.py --story docs/drafts/REQ001_preview --ac docs/stories/REQ001_x/story_analysis.md
"""
import argparse
import csv
import glob
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TC_ID_FULL = re.compile(r"TC-REQ\d+-US\d+-\d+")
# Derivation tables cite cases by short form ("TC-001", "TC-014/015/016") since the
# REQ/US prefix is constant within one story — expand against the story's own prefix.
TC_ID_SHORT = re.compile(r"TC-(\d{3}(?:/\d{3})*)")

CASE_ID_PREFIX = None  # set by build() before any parse_* runs


def cases_in(text):
    ids = set(TC_ID_FULL.findall(text))
    if CASE_ID_PREFIX:
        for m in TC_ID_SHORT.finditer(text):
            for n in m.group(1).split("/"):
                ids.add(f"{CASE_ID_PREFIX}{n}")
    return sorted(ids)


TAGGED_PAIR = re.compile(
    r"(TC-REQ\d+-US\d+-\d+|TC-\d{3}(?:/\d{3})*)\s*\(([^)]*)\)")


def tagged_cases(text):
    """Every 'TC-xxx (tag)' occurrence in `text` as (ids, tag) — the only reliable way to tell
    which case a Cases-column entry belongs to when a cell lists more than one case. A fixed-width
    text window around the parenthesis is not safe: two adjacent 'TC-001 (VC1), TC-003 (IC1)'
    entries sit close enough together that a window built around the second tag can still contain
    the first case's ID."""
    out = []
    for m in TAGGED_PAIR.finditer(text):
        ids = cases_in(m.group(1))
        if ids:
            out.append((ids, m.group(2).strip()))
    return out


def cases_for_tag(text, tag):
    """Cases whose parenthetical tag exactly equals `tag` (e.g. 'VC1', 'max+1')."""
    for ids, t in tagged_cases(text):
        if t == tag:
            return ids
    return []


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        return fh.readlines()


def table_rows(lines, start, header_prefix="|"):
    """From `start` (0-indexed, pointing at a '| heading |' row), yield split cell lists for
    every following table row, stopping at the first non-table line. Skips the separator row."""
    i = start
    rows = []
    # header
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    i += 1
    if i < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
        i += 1
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        rows.append(cells)
        i += 1
    return header, rows, i


def find_section(lines, heading_re):
    for idx, line in enumerate(lines):
        if heading_re.match(line.strip()):
            return idx
    return None


def find_next_table(lines, from_idx):
    for idx in range(from_idx, len(lines)):
        if lines[idx].strip().startswith("|"):
            return idx
    return None


def parse_equivalence_classes(lines):
    """| Field | Rule | Valid classes | Invalid classes | Cases |

    Also the source of coverage-model.md dimension 3 (validation rule): the `Rule` column names
    the test_basis.md rule each class exercises. Rules recur across many rows/classes (one named
    rule is usually proven by several classes), so their case-ids are accumulated across the whole
    table and emitted as one `RULE ·` column per distinct rule, not one per row.
    """
    idx = find_section(lines, re.compile(r"^###\s+Equivalence classes"))
    if idx is None:
        return []
    tstart = find_next_table(lines, idx)
    if tstart is None:
        return []
    header, rows, _ = table_rows(lines, tstart)
    cols = []
    rule_ids = {}
    field, rule = "", ""
    for r in rows:
        if len(r) < 5:
            continue
        if r[0]:
            field = r[0].strip("`")
        if r[1]:
            rule = r[1].strip("`")
        for kind, cell in (("valid", r[2]), ("invalid", r[3])):
            label = cell.strip()
            if not label:
                continue
            tag_match = re.match(r"([A-Z]+\d+):\s*(.*)", label)
            tag = tag_match.group(1) if tag_match else None
            desc = tag_match.group(2) if tag_match else label
            ids = cases_for_tag(r[4], tag) if tag else []
            if not ids:
                ids = cases_in(r[4])
            colname = f"EP · {field} = {desc}"
            cols.append((colname, ids))
            if rule and rule not in ("—", "-"):
                rule_ids.setdefault(rule, set()).update(ids)
    cols += [(f"RULE · {r}", sorted(ids)) for r, ids in sorted(rule_ids.items())]
    return cols


def parse_boundary_analysis(lines):
    """| Field | Type | min-1 | min | max | max+1 | Cases |"""
    idx = find_section(lines, re.compile(r"^###\s+Boundary analysis"))
    if idx is None:
        return []
    tstart = find_next_table(lines, idx)
    if tstart is None:
        return []
    header, rows, _ = table_rows(lines, tstart)
    labels = ["min-1", "min", "max", "max+1"]
    cols = []
    for r in rows:
        if len(r) < 7:
            continue
        field = r[0].strip("`")
        cases_cell = r[6]
        active = [(li, label, r[2 + li].strip()) for li, label in enumerate(labels)
                  if r[2 + li].strip() and r[2 + li].strip() != "—"]
        tagged = tagged_cases(cases_cell)
        if tagged:
            for li, label, val in active:
                ids = cases_for_tag(cases_cell, label)
                cols.append((f"BVA · {field} {label} = {val}", ids))
        else:
            # No per-value tags in the Cases cell — the only safe assumption is that the
            # author listed case IDs left-to-right in the same order as the boundary columns.
            all_ids = cases_in(cases_cell)
            if len(all_ids) == len(active):
                for (li, label, val), cid in zip(active, all_ids):
                    cols.append((f"BVA · {field} {label} = {val}", [cid]))
            else:
                # counts don't line up 1:1 — do not guess which value each case belongs to
                cols.append((f"BVA · {field} (untagged Cases cell, needs a (label) per case — "
                              f"see design_notes.md)", all_ids))
    return cols


def parse_decision_tables(lines):
    """### Decision table - [name]  |Conditions|R1|R2|...|  ... | **case** | TC-...-001 | ... |"""
    cols = []
    for idx, line in enumerate(lines):
        if not line.strip().startswith("### Decision table"):
            continue
        name = line.strip()[len("### Decision table"):].strip(" -—")
        tstart = find_next_table(lines, idx)
        if tstart is None:
            continue
        header, rows, _ = table_rows(lines, tstart)
        rule_names = header[1:]
        outcome_row = next((r for r in rows if r[0].strip("*").strip().lower() == "outcome"), None)
        case_row = next((r for r in rows if r[0].strip("*").strip().lower() == "case"), None)
        if case_row is None:
            continue
        for ri, rule in enumerate(rule_names, start=1):
            cell = case_row[ri] if ri < len(case_row) else ""
            ids = cases_in(cell)
            if not ids:
                continue
            outcome = outcome_row[ri].strip() if outcome_row and ri < len(outcome_row) else ""
            label = f"DT ({name}) · {rule}" + (f" = {outcome}" if outcome else "")
            cols.append((label, ids))
    return cols


def parse_state_transitions(lines):
    """| From \\ To | S1 | S2 | ... | Case |  rows: | **From** | valid/invalid | ... | Case text |"""
    cols = []
    for idx, line in enumerate(lines):
        if not line.strip().startswith("### State transitions"):
            continue
        tstart = find_next_table(lines, idx)
        if tstart is None:
            continue
        header, rows, _ = table_rows(lines, tstart)
        to_states = header[1:-1]  # drop leading "From \ To" and trailing "Case"
        for r in rows:
            if len(r) < 3:
                continue
            frm = r[0].strip("*").strip()
            case_cell = r[-1]
            for ti, to in enumerate(to_states, start=1):
                if ti >= len(r) - 1:
                    continue
                verdict = r[ti].strip().lower()
                if verdict == "—" or verdict == "-":
                    continue  # self-transition, not a real edge
                if verdict == "valid":
                    # find TC ids annotated with an arrow mentioning this To state
                    tagged = tagged_cases(case_cell)
                    ids = []
                    for pair_ids, tag in tagged:
                        if to.split()[0] in tag:
                            ids.extend(pair_ids)
                    if not tagged:
                        # single untagged transition per row — every listed case applies
                        ids = cases_in(case_cell)
                    cols.append((f"ST · {frm} -> {to} (valid)", sorted(set(ids))))
                else:
                    # coverage-model.md's State transition denominator is "valid +
                    # reachable-invalid" — an invalid edge still needs a column so an
                    # unexercised one shows up as a real shortfall, not a silent omission.
                    cols.append((f"ST · {frm} -> {to} (invalid — must be rejected)", []))
    return cols


def parse_exception_coverage(lines):
    idx = find_section(lines, re.compile(r"^###\s+Exception coverage"))
    if idx is None:
        return []
    tstart = find_next_table(lines, idx)
    if tstart is None:
        return []
    header, rows, _ = table_rows(lines, tstart)
    cols = []
    for r in rows:
        if len(r) < 5:
            continue
        num, scenario, applicable = r[0], r[1], r[2].strip().lower()
        if applicable != "yes":
            continue
        ids = cases_in(r[3])
        if not ids:
            continue
        cols.append((f"EXC {num} · {scenario}", ids))
    return cols


ENDPOINT = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)")
STATUS = re.compile(r"\bHTTP\s+(\d{3})\b")


def parse_endpoint_status(story_dir):
    """coverage-model.md dimension 2: (endpoint, status) pairs with >=1 case. Derived from every
    step's Test_Step (endpoint) and Expected_Result (status) in the generated test_cases.csv —
    the same file the CSV schema already treats as the per-step source of truth.

    Two exclusions keep this matched to what a human means by "endpoint x status", not just
    "every HTTP call anywhere in the suite":
    - A step tagged `[verification]` (see qa-templates.md) exists only to confirm a side effect,
      not to exercise the endpoint's own behaviour — it stays a real, checked step, just not one
      that counts toward this dimension's denominator.
    - A case whose Test_Type is `exception` is already counted under the `exception` dimension
      (auth failures, replay, etc.) — counting its status code here too would double-count the
      same test intent under two denominators.
    """
    csv_path = os.path.join(story_dir, "test_cases.csv")
    if not os.path.exists(csv_path):
        return []
    pairs = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if "[verification]" in row.get("Test_Step", ""):
                continue
            if row.get("Test_Type", "").strip().lower() == "exception":
                continue
            m_ep = ENDPOINT.search(row.get("Test_Step", ""))
            m_st = STATUS.search(row.get("Expected_Result", ""))
            if not m_ep or not m_st:
                continue
            key = f"{m_ep.group(1)} {m_ep.group(2)} -> HTTP {m_st.group(1)}"
            pairs.setdefault(key, set()).add(row["Test_Case_ID"])
    return [(f"END · {k}", sorted(v)) for k, v in sorted(pairs.items())]


RULE_REF = re.compile(r"\bVAL-[\w-]+")


def parse_rule_refs_from_csv(story_dir):
    """Backstop for coverage-model.md dimension 3's `RULE ·` columns: a rule like
    `VAL-order-001` (validation ORDER, not a single field's value) has no natural row in the
    Equivalence classes table `parse_equivalence_classes` reads — it is only visible as a
    `test_basis.md#VAL-order-001` citation on whichever case proves it. Scans both `Basis_Ref` and
    `Notes` (a case-level `Basis_Ref` only holds one anchor — see qa-templates.md — so a case
    proving a second rule often carries that citation in `Notes` instead) and unions with whatever
    `parse_equivalence_classes` already found, deduplicated by rule name."""
    csv_path = os.path.join(story_dir, "test_cases.csv")
    if not os.path.exists(csv_path):
        return {}
    rule_ids = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            text = f"{row.get('Basis_Ref', '')} {row.get('Notes', '')}"
            for m in RULE_REF.finditer(text):
                rule_ids.setdefault(m.group(0), set()).add(row["Test_Case_ID"])
    return rule_ids


def parse_ac_from_index(story_dir):
    idx_path = os.path.join(story_dir, "test_cases_index.csv")
    cols = {}
    if not os.path.exists(idx_path):
        return []
    with open(idx_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            for ac in re.split(r"[;,]\s*", row.get("AC_Ref", "")):
                ac = ac.strip()
                if not ac:
                    continue
                cols.setdefault(ac, []).append(row["Test_Case_ID"])
    return [(f"AC · {ac}", ids) for ac, ids in sorted(cols.items())]


def all_case_ids(story_dir):
    idx_path = os.path.join(story_dir, "test_cases_index.csv")
    if not os.path.exists(idx_path):
        return []
    with open(idx_path, encoding="utf-8-sig", newline="") as fh:
        return [row["Test_Case_ID"] for row in csv.DictReader(fh)]


def build(story_dir, design_notes_path):
    global CASE_ID_PREFIX
    case_ids = all_case_ids(story_dir)
    if case_ids:
        m = re.match(r"(TC-REQ\d+-US\d+-)\d+", case_ids[0])
        CASE_ID_PREFIX = m.group(1) if m else None

    lines = read_lines(design_notes_path)
    columns = []
    columns += parse_ac_from_index(story_dir)
    columns += parse_endpoint_status(story_dir)
    columns += parse_equivalence_classes(lines)
    columns += parse_boundary_analysis(lines)
    columns += parse_decision_tables(lines)
    columns += parse_state_transitions(lines)
    columns += parse_exception_coverage(lines)

    # Merge the Basis_Ref/Notes rule backstop into whatever RULE columns the Equivalence classes
    # table already produced, rather than appending duplicate "RULE · X" columns.
    extra_rule_ids = parse_rule_refs_from_csv(story_dir)
    for i, (name, ids) in enumerate(columns):
        if name.startswith("RULE · "):
            rule = name[len("RULE · "):]
            if rule in extra_rule_ids:
                columns[i] = (name, sorted(set(ids) | extra_rule_ids.pop(rule)))
    columns += [(f"RULE · {r}", sorted(ids)) for r, ids in sorted(extra_rule_ids.items())]

    case_ids = all_case_ids(story_dir)
    if not case_ids:
        # fall back to whatever case IDs appear anywhere in the columns
        seen = []
        for _, ids in columns:
            for i in ids:
                if i not in seen:
                    seen.append(i)
        case_ids = sorted(seen)

    out_path = os.path.join(story_dir, "tcm_matrix.csv")
    with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["Test_Case_ID"] + [c[0] for c in columns])
        for cid in case_ids:
            w.writerow([cid] + ["x" if cid in ids else "" for _, ids in columns])

    empty_cols = [name for name, ids in columns if not any(cid in ids for cid in case_ids)]
    return out_path, len(columns), len(case_ids), empty_cols


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", required=True, help="story dir containing design_notes.md")
    args = ap.parse_args()

    story_dir = os.path.abspath(args.story)
    design_notes_path = os.path.join(story_dir, "design_notes.md")
    if not os.path.exists(design_notes_path):
        print(f"build-tcm-matrix: no design_notes.md in {story_dir}", file=sys.stderr)
        return 2

    out_path, ncols, nrows, empty_cols = build(story_dir, design_notes_path)
    print(f"build-tcm-matrix: wrote {os.path.relpath(out_path, REPO_ROOT)} "
          f"({nrows} cases x {ncols} dimension columns)")
    if empty_cols:
        print("build-tcm-matrix: WARNING — dimension columns with zero 'x' (uncovered):", file=sys.stderr)
        for c in empty_cols:
            print(f"  {c}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
