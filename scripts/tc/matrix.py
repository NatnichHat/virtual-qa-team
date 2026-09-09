#!/usr/bin/env python3
"""Derive the coverage X-matrix columns for test_cases.csv's right-hand block.

Imported by build-csv.py — the standalone tcm_matrix.csv and its generator are retired. Cases and
their X-mapping now share one file and one row, the layout of the team's reference sheet
("docs/references/example of relation for test case and metrix.csv"): case columns left,
dimension columns right.

The matrix is never hand-typed (coverage-model.md control #1, "derived, not chosen"): every column
comes from inverting the Derivation tables design_notes.md already writes (Equivalence classes,
Boundary analysis, Decision table(s), State transitions, Exception coverage) plus `AC_Ref` and the
step/expected-result pairs. A dimension-value that never appears in a Derivation table's "Cases"
column cannot silently gain an `x`, and neither can a case never linked to it there.

Group order in the emitted block is fixed — see .claude/refs/csv-schema.md:
  AC · → END · → EP · → RULE · → BVA · → DT (…) · → ST · → EXC n ·
"""
import re

TC_ID_FULL = re.compile(r"TC-REQ\d+-US\d+-\d+")
# Derivation tables cite cases by short form ("TC-001", "TC-014/015/016") since the
# REQ/US prefix is constant within one story — expand against the story's own prefix.
TC_ID_SHORT = re.compile(r"TC-(\d{3}(?:/\d{3})*)")
TAGGED_PAIR = re.compile(
    r"(TC-REQ\d+-US\d+-\d+|TC-\d{3}(?:/\d{3})*)\s*\(([^)]*)\)")
ENDPOINT = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)")
STATUS = re.compile(r"\bHTTP\s+(\d{3})\b")
RULE_REF = re.compile(r"\bVAL-[\w-]+")


def cases_in(text, prefix):
    ids = set(TC_ID_FULL.findall(text))
    if prefix:
        for m in TC_ID_SHORT.finditer(text):
            for n in m.group(1).split("/"):
                ids.add(f"{prefix}{n}")
    return sorted(ids)


def tagged_cases(text, prefix):
    """Every 'TC-xxx (tag)' occurrence in `text` as (ids, tag) — the only reliable way to tell
    which case a Cases-column entry belongs to when a cell lists more than one case."""
    out = []
    for m in TAGGED_PAIR.finditer(text):
        ids = cases_in(m.group(1), prefix)
        if ids:
            out.append((ids, m.group(2).strip()))
    return out


def cases_for_tag(text, tag, prefix):
    """Cases whose parenthetical tag exactly equals `tag` (e.g. 'VC1', 'max+1')."""
    for ids, t in tagged_cases(text, prefix):
        if t == tag:
            return ids
    return []


def table_rows(lines, start):
    """From `start` (0-indexed, pointing at a '| heading |' row), return (header, rows, next_idx)."""
    i = start
    rows = []
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    i += 1
    if i < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i].strip()):
        i += 1
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
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


def parse_equivalence_classes(lines, prefix):
    """| Field | Rule | Valid classes | Invalid classes | Cases |

    Also the source of dimension 3 (validation rule): the `Rule` column names the test_basis.md
    rule each class exercises. Rules recur across rows/classes, so their case-ids are accumulated
    across the whole table and emitted as one `RULE ·` column per distinct rule, not one per row.
    """
    idx = find_section(lines, re.compile(r"^###\s+Equivalence classes"))
    if idx is None:
        return [], {}
    tstart = find_next_table(lines, idx)
    if tstart is None:
        return [], {}
    _, rows, _ = table_rows(lines, tstart)
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
        for cell in (r[2], r[3]):
            label = cell.strip()
            if not label:
                continue
            tag_match = re.match(r"([A-Z]+\d+):\s*(.*)", label)
            tag = tag_match.group(1) if tag_match else None
            desc = tag_match.group(2) if tag_match else label
            ids = cases_for_tag(r[4], tag, prefix) if tag else []
            if not ids:
                ids = cases_in(r[4], prefix)
            cols.append((f"EP · {field} = {desc}", ids))
            if rule and rule not in ("—", "-"):
                rule_ids.setdefault(rule, set()).update(ids)
    return cols, rule_ids


def parse_boundary_analysis(lines, prefix):
    """| Field | Type | min-1 | min | max | max+1 | Cases |"""
    idx = find_section(lines, re.compile(r"^###\s+Boundary analysis"))
    if idx is None:
        return []
    tstart = find_next_table(lines, idx)
    if tstart is None:
        return []
    _, rows, _ = table_rows(lines, tstart)
    labels = ["min-1", "min", "max", "max+1"]
    cols = []
    for r in rows:
        if len(r) < 7:
            continue
        field = r[0].strip("`")
        cases_cell = r[6]
        active = [(label, r[2 + li].strip()) for li, label in enumerate(labels)
                  if r[2 + li].strip() and r[2 + li].strip() != "—"]
        tagged = tagged_cases(cases_cell, prefix)
        if tagged:
            for label, val in active:
                ids = cases_for_tag(cases_cell, label, prefix)
                cols.append((f"BVA · {field} {label} = {val}", ids))
        else:
            # No per-value tags in the Cases cell — the only safe assumption is that the
            # author listed case IDs left-to-right in the same order as the boundary columns.
            all_ids = cases_in(cases_cell, prefix)
            if len(all_ids) == len(active):
                for (label, val), cid in zip(active, all_ids):
                    cols.append((f"BVA · {field} {label} = {val}", [cid]))
            else:
                cols.append((f"BVA · {field} (untagged Cases cell, needs a (label) per case — "
                             f"see design_notes.md)", all_ids))
    return cols


def parse_decision_tables(lines, prefix):
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
            ids = cases_in(cell, prefix)
            if not ids:
                continue
            outcome = outcome_row[ri].strip() if outcome_row and ri < len(outcome_row) else ""
            cols.append((f"DT ({name}) · {rule}" + (f" = {outcome}" if outcome else ""), ids))
    return cols


def parse_state_transitions(lines, prefix):
    """| From \\ To | S1 | S2 | ... | Case | — valid edges get a case, invalid ones an empty
    column so an unexercised edge shows up as a visible shortfall, not a silent omission."""
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
                if verdict in ("—", "-"):
                    continue  # self-transition, not a real edge
                if verdict == "valid":
                    tagged = tagged_cases(case_cell, prefix)
                    ids = []
                    for pair_ids, tag in tagged:
                        if to.split()[0] in tag:
                            ids.extend(pair_ids)
                    if not tagged:
                        ids = cases_in(case_cell, prefix)
                    cols.append((f"ST · {frm} -> {to} (valid)", sorted(set(ids))))
                else:
                    cols.append((f"ST · {frm} -> {to} (invalid — must be rejected)", []))
    return cols


def parse_exception_coverage(lines, prefix):
    idx = find_section(lines, re.compile(r"^###\s+Exception coverage"))
    if idx is None:
        return []
    tstart = find_next_table(lines, idx)
    if tstart is None:
        return []
    _, rows, _ = table_rows(lines, tstart)
    cols = []
    for r in rows:
        if len(r) < 5:
            continue
        num, scenario, applicable = r[0], r[1], r[2].strip().lower()
        if applicable != "yes":
            continue
        ids = cases_in(r[3], prefix)
        if not ids:
            continue
        cols.append((f"EXC {num} · {scenario}", ids))
    return cols


def parse_endpoint_status(rows):
    """Dimension 2: (endpoint, status) pairs with >=1 case, derived from the step rows in memory.

    Two exclusions keep this matched to what a human means by "endpoint x status", not "every HTTP
    call anywhere in the suite":
    - A step tagged `[verification]` exists only to confirm a side effect, not to exercise the
      endpoint's own behaviour.
    - A case whose Test_Type is `exception` is already counted under dimension 7 — counting its
      status code here too would double-count the same intent under two denominators.
    """
    pairs = {}
    for row in rows:
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


def parse_ac(rows):
    cols = {}
    for row in rows:
        for ac in re.split(r"[;,]\s*", row.get("AC_Ref", "")):
            ac = ac.strip()
            if ac and row["Test_Case_ID"] not in cols.setdefault(ac, []):
                cols[ac].append(row["Test_Case_ID"])
    return [(f"AC · {ac}", ids) for ac, ids in sorted(cols.items())]


def rule_backstop(rows):
    """`RULE ·` backstop: a rule like `VAL-order-001` (validation ORDER, not a single field's
    value) has no natural Equivalence-classes row — it is only visible as a citation in
    `Basis_Ref` or `Notes` of whichever case proves it."""
    rule_ids = {}
    for row in rows:
        text = f"{row.get('Basis_Ref', '')} {row.get('Notes', '')}"
        for m in RULE_REF.finditer(text):
            rule_ids.setdefault(m.group(0), set()).add(row["Test_Case_ID"])
    return rule_ids


def build_columns(design_notes_lines, case_ids, step_rows):
    """Return (columns, warnings): columns = [(name, [case_ids])] in the fixed group order,
    warnings = names of columns with zero `x` (a real, visible shortfall — belongs in
    tcm.md's `## Spec non-compliance`, never deleted to silence the warning)."""
    prefix = None
    if case_ids:
        m = re.match(r"(TC-REQ\d+-US\d+-)\d+", case_ids[0])
        prefix = m.group(1) if m else None

    ep_cols, rule_ids = parse_equivalence_classes(design_notes_lines, prefix)
    rule_cols = [(f"RULE · {r}", sorted(ids)) for r, ids in sorted(rule_ids.items())]
    # Merge the Basis_Ref/Notes backstop into the rules the Equivalence classes table produced,
    # rather than appending duplicate "RULE · X" columns.
    extra = rule_backstop(step_rows)
    for i, (name, ids) in enumerate(rule_cols):
        rule = name[len("RULE · "):]
        if rule in extra:
            rule_cols[i] = (name, sorted(set(ids) | extra.pop(rule)))
    rule_cols += [(f"RULE · {r}", sorted(ids)) for r, ids in sorted(extra.items())]

    columns = (
        parse_ac(step_rows)
        + parse_endpoint_status(step_rows)
        + ep_cols
        + rule_cols
        + parse_boundary_analysis(design_notes_lines, prefix)
        + parse_decision_tables(design_notes_lines, prefix)
        + parse_state_transitions(design_notes_lines, prefix)
        + parse_exception_coverage(design_notes_lines, prefix)
    )
    warnings = [name for name, ids in columns
                if not any(cid in ids for cid in case_ids)]
    return columns, warnings
