#!/usr/bin/env python3
"""Render test_cases.xlsx — the PRESENTATION view — from the generated CSVs.

Pipeline position (see .claude/refs/csv-schema.md):

    design_notes.md ──(make testcases)──▶ test_cases.csv        ← working artifact (tracked)
                                          test_cases_index.csv
                                              │
                                              └──(make xlsx-view)──▶ test_cases.xlsx
                                                                     presentation view (gitignored)

The xlsx is a downstream PHOTOGRAPH of the CSVs: it adds merge cells and colour, which a CSV
cannot carry, and it is never read by a gate, a script, or an agent — those read the CSVs,
which stay token-cheap and diffable. Being a photograph, it is gitignored: an xlsx is a zip
whose bytes embed timestamps, so committing it would trip drift guards on identical content
and produce meaningless binary diffs. Regenerate on demand; the CSVs are the truth.

STYLE IS POLICY, NOT CODE. Every merge/styling decision lives in xlsx_style.toml beside this
script: which columns are step-level (never merged), the value palettes, the colour scope,
widths, the 2-tier matrix banner. Edit the TOML and re-render — never fork the script to
try a colour.

Sheets:
  Test Cases — one row per step (from test_cases.csv). Case-level columns and the coverage
               X-matrix block are merged across each case's step rows; the matrix block gets
               a 2-tier grouped banner header (one merged banner per dimension group); freeze
               panes keep the header rows and Test_Case_ID visible.
  Case Index — one row per case (from test_cases_index.csv), flat and filterable — the
               sorting/counting view that merged cells deliberately do not support.
  Legend     — what every colour means, rendered from the active palettes.

Usage:
  build-xlsx.py                 # every story under docs/test_cases/
  build-xlsx.py --story <dir>   # one story directory (e.g. docs/drafts/REQ001_preview)
  build-xlsx.py --preview       # ALSO write xlsx_style_preview.xlsx: a small sample rendered
                                # under all three colour scopes, one sheet each, so the scope
                                # decision is made by looking at Excel rather than at chat.

Requires openpyxl — `make xlsx-deps` provisions it (scripts/requirements.txt).
"""
import argparse
import csv
import os
import sys
import tomllib

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.formatting.rule import FormulaRule
except ImportError:
    print("build-xlsx: openpyxl is not installed — run `make xlsx-deps` "
          "(pins scripts/requirements.txt).", file=sys.stderr)
    sys.exit(3)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TEST_CASES_ROOT = os.path.join(REPO_ROOT, "docs", "test_cases")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "xlsx_style.toml")

# Matrix column names are "<GROUP> · <value>" (csv-schema.md §Format) — the prefix before
# the first ' ·' is the banner group. Anything without the separator is not a matrix column.
GROUP_SEP = " · "


def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        print(f"build-xlsx: ERROR style config {path} not found.", file=sys.stderr)
        sys.exit(2)
    with open(path, "rb") as fh:
        cfg = tomllib.load(fh)
    # color_scope must be a TOP-LEVEL key, written above every [table] header — in TOML a
    # scalar after a header silently joins that table. Fail loudly instead of defaulting:
    # a scope that quietly stopped applying is worse than no render.
    scope = cfg.get("color_scope")
    if scope is None:
        print("build-xlsx: ERROR xlsx_style.toml has no top-level `color_scope` key. It must "
              "appear ABOVE the first [table] header (TOML scoping rule).", file=sys.stderr)
        sys.exit(2)
    if scope not in ("cell_tint", "row_tint", "banding"):
        print(f"build-xlsx: ERROR color_scope {scope!r} in xlsx_style.toml — expected "
              f"cell_tint | row_tint | banding.", file=sys.stderr)
        sys.exit(2)
    return cfg


def fill(rgb):
    return PatternFill("solid", fgColor=rgb.upper())


def read_csv(path):
    """(fieldnames, rows) or a clear error — the CSVs are build artifacts, so a missing one
    means `make testcases` has not run, never "write the xlsx anyway"."""
    if not os.path.exists(path):
        shown = (os.path.relpath(path, REPO_ROOT)
                 if path.startswith(REPO_ROOT + os.sep) else path)
        print(f"build-xlsx: ERROR {shown} not found — "
              f"run `make testcases` first (the xlsx is rendered FROM the CSVs).",
              file=sys.stderr)
        sys.exit(2)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames or [], list(reader)


def case_spans(rows):
    """[(first_row_index, last_row_index)] over `rows` (0-based) grouped by contiguous
    Test_Case_ID. Rows of one case are contiguous by construction (csv-schema.md §Row
    granularity); a repeated non-contiguous ID is a build-csv bug and would render here as
    two blocks — acceptable, since this script never silently reorders rows."""
    spans, start = [], 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or rows[i]["Test_Case_ID"] != rows[start]["Test_Case_ID"]:
            spans.append((start, i - 1))
            start = i
    return spans


def group_ranges(columns, matrix_start):
    """[(group_name, first_col, last_col)] for matrix columns — banner merge targets."""
    groups, cur, first = [], None, None
    for c in range(matrix_start, len(columns)):
        g = columns[c].split(GROUP_SEP, 1)[0].strip()
        if g != cur:
            if cur is not None:
                groups.append((cur, first, c - 1))
            cur, first = g, c
    if cur is not None:
        groups.append((cur, first, len(columns) - 1))
    return groups


class SheetWriter:
    """Writes one sheet's rows under one colour scope. All styling policy comes from cfg."""

    def __init__(self, ws, cfg, columns, matrix_start, scope=None):
        self.ws, self.cfg, self.columns = ws, cfg, columns
        self.matrix_start = matrix_start          # 0-based index of first matrix column
        self.scope = scope or cfg["color_scope"]
        self.step_columns = set(cfg["merge"]["step_columns"])
        self.widths = cfg["widths"]
        self.wrap = set(cfg["wrap"]["columns"])
        # Status is deliberately NOT here: preferred_style.xlsx §7 wants real conditional-
        # formatting rules on Test Result, not a fill baked in at write time — see
        # style_status_column(), applied once after the body is written.
        self.palettes = {
            "Test_Type": {k: tuple(v) for k, v in cfg["colors"]["test_type"].items()},
            "Priority":  {k: tuple(v) for k, v in cfg["colors"]["priority"].items()},
        }
        self.unknown = set()

    # ── header ──────────────────────────────────────────────────────────────────
    # Colour tiers follow preferred_style.xlsx's semantic hierarchy: the case-level
    # (left-hand, descriptive) columns are the dark-navy MAIN header; the matrix banner
    # row is the "Level 1 — main matrix group" colour; the matrix value/leaf row is the
    # "matrix leaf" colour, rotated 90° for narrow columns. Our CSV only carries two
    # matrix tiers (group, value), so no L2/L3 mid-tier is invented for a third colour.
    def write_header(self):
        hdr = self.cfg["header"]
        banner = hdr.get("matrix_banner", False) and self.matrix_start < len(self.columns)
        tiers = 2 if banner else 1
        ws = self.ws
        thin = Side(style="thin", color="000000")
        border = Border(top=thin, left=thin, right=thin, bottom=thin)

        for c, name in enumerate(self.columns, 1):
            is_matrix = (c - 1) >= self.matrix_start
            # With a banner the group name is already on tier 1, so tier 2 carries just the
            # value name. Without one, the header must carry the FULL CSV column name — a
            # lone "AC-3" under no banner loses the group, and the flat sheet's whole job is
            # to mirror the CSV header exactly (filter dropdowns read these names).
            short = (name.split(GROUP_SEP, 1)[1]
                     if is_matrix and tiers == 2 and GROUP_SEP in name else name)
            rot = hdr.get("matrix_header_rotation", 90) if (is_matrix and tiers == 2) else 0
            # Non-matrix columns live on row 1 and merge DOWN across both tiers — a merged
            # range only displays its top-left cell, so the value must sit on row 1.
            # Matrix value names live on the bottom tier, under their banner.
            value_row = tiers if is_matrix else 1
            cell = ws.cell(row=value_row, column=c, value=short)
            if is_matrix and tiers == 2:
                cell.fill = fill(hdr.get("leaf_fill", hdr["header_fill"]))
                cell.font = Font(name="Calibri", bold=False,
                                 color=hdr.get("leaf_font", "000000"), size=10)
            else:
                cell.fill = fill(hdr["header_fill"])
                cell.font = Font(name="Calibri", bold=True, color=hdr["header_font"], size=10)
            cell.alignment = Alignment(wrap_text=True, vertical="center",
                                       horizontal="center", textRotation=rot)
            cell.border = border
            if tiers == 2 and not is_matrix:
                ws.merge_cells(start_row=1, start_column=c, end_row=2, end_column=c)
                tail = ws.cell(row=2, column=c)
                tail.fill = fill(hdr["header_fill"])
                tail.border = border

        if banner:
            for name, c1, c2 in group_ranges(self.columns, self.matrix_start):
                # A single-column group needs no merge — a 1x1 merged range is inert junk in
                # the XML (openpyxl even normalises it away on re-read).
                if c2 > c1:
                    ws.merge_cells(start_row=1, start_column=c1 + 1, end_row=1, end_column=c2 + 1)
                cell = ws.cell(row=1, column=c1 + 1, value=name)
                cell.fill = fill(hdr.get("banner_fill", hdr["header_fill"]))
                cell.font = Font(name="Calibri", bold=True, color=hdr.get("banner_font", "000000"),
                                 size=10)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border
                for cc in range(c1 + 2, c2 + 2):
                    tcell = ws.cell(row=1, column=cc)
                    tcell.fill = fill(hdr.get("banner_fill", hdr["header_fill"]))
                    tcell.border = border
            ws.row_dimensions[1].height = hdr.get("banner_height", 18)
            ws.row_dimensions[2].height = hdr.get("value_header_height", 90)
        else:
            ws.row_dimensions[1].height = hdr.get("value_header_height", 90)
        return tiers

    # ── body ────────────────────────────────────────────────────────────────────
    def write_body(self, rows, spans, merge):
        ws = self.ws
        # Uniform thin black grid throughout (preferred_style §4/§11) — no medium grey
        # case-boundary separator; that "#808080 top border on every row" is the
        # documented anti-pattern.
        thin = Side(style="thin", color="000000")
        border = Border(top=thin, left=thin, right=thin, bottom=thin)
        mark = self.cfg["colors"]["matrix_mark"]
        washes = {k: v.upper() for k, v in self.cfg.get("row_tint", {}).get("wash", {}).items()}
        band = self.cfg.get("banding", {})
        header_rows = 2 if (self.cfg["header"].get("matrix_banner", False)
                            and self.matrix_start < len(self.columns)) else 1

        for span_i, (s, e) in enumerate(spans):
            band_fill = (band.get("odd_fill") if span_i % 2 else band.get("even_fill")
                         ) if self.scope == "banding" else None
            row_wash = None
            if self.scope == "row_tint":
                ttype = (rows[s].get("Test_Type") or "").strip().lower()
                row_wash = washes.get(ttype)
            for i in range(s, e + 1):
                row, r = rows[i], header_rows + 1 + i
                for c, name in enumerate(self.columns, 1):
                    value = row.get(name, "")
                    cell = ws.cell(row=r, column=c, value=value)
                    is_step = name in self.step_columns
                    cell.border = border
                    cell.font = Font(name="Calibri", size=10, color="000000")
                    cell.fill = fill("FFFFFF")
                    cell.alignment = Alignment(
                        wrap_text=name in self.wrap,
                        vertical="top" if is_step else "center",
                        horizontal="left" if name in self.wrap else "center")
                    # base layer: row wash / case banding (scope-dependent, beneath value fills)
                    if self.scope == "row_tint" and row_wash and not is_step:
                        cell.fill = fill(row_wash)
                    elif self.scope == "banding" and band_fill:
                        cell.fill = fill(band_fill)
                    # value layer: palettes on their own columns, always win over the base
                    if name in self.palettes:
                        self._style_value(cell, self.palettes[name], name)
                    elif (c - 1) >= self.matrix_start and value.strip().lower() == "x":
                        # plain black 'x' on white, centred — preferred_style §6; NOT
                        # bold, NOT navy, NOT light-blue-filled.
                        cell.value = "x"
                        cell.fill = fill(mark["fill"])
                        cell.font = Font(name="Calibri", size=10, color=mark["font"], bold=False)
                        cell.alignment = Alignment(horizontal="center", vertical="center")

        merges = 0
        if merge:
            for s, e in spans:
                if e == s:
                    continue  # single-step case — nothing to merge
                r1, r2 = header_rows + 1 + s, header_rows + 1 + e
                for c, name in enumerate(self.columns, 1):
                    if name not in self.step_columns:
                        ws.merge_cells(start_row=r1, start_column=c, end_row=r2, end_column=c)
                        merges += 1
        return merges

    def _style_value(self, cell, palette, kind):
        key = str(cell.value or "").strip().lower()
        if not key:
            return
        if key in palette:
            f, font = palette[key]
            cell.fill = fill(f)
            cell.font = Font(color=font, bold=True, size=10)
        else:
            self.unknown.add((kind, str(cell.value)))

    def set_widths(self):
        default = self.widths.get("default", 14)
        matrix_w = self.widths.get("matrix", 4.5)
        for c, name in enumerate(self.columns, 1):
            w = (self.widths.get(name)
                 if (c - 1) < self.matrix_start else matrix_w) or default
            self.ws.column_dimensions[get_column_letter(c)].width = w


def freeze(ws, cfg, header_rows):
    # preferred_style.xlsx §12: freeze the header ROWS only — no column lock unless
    # explicitly requested via freeze_first_column.
    letter = "B" if cfg["freeze"].get("freeze_first_column", False) else "A"
    ws.freeze_panes = f"{letter}{header_rows + 1}"


def apply_page_setup(ws, cfg):
    """preferred_style.xlsx §14: landscape, zero margins, ~100% zoom, dense wide view."""
    page = cfg.get("page", {})
    ws.page_setup.orientation = page.get("orientation", "landscape")
    m = page.get("margins", 0.0)
    ws.page_margins.left = ws.page_margins.right = m
    ws.page_margins.top = ws.page_margins.bottom = m
    ws.page_margins.header = ws.page_margins.footer = m
    ws.sheet_view.zoomScale = page.get("zoom", 100)


def style_status_column(ws, columns, header_rows, n_rows, cfg):
    """Data-validation dropdown + real conditional-formatting rules on the Status column
    (preferred_style.xlsx §7) — colour comes from the cell VALUE at open time, not from a
    fill baked in when the sheet was generated."""
    if "Status" not in columns:
        return
    col = get_column_letter(columns.index("Status") + 1)
    first, last = header_rows + 1, header_rows + n_rows
    if n_rows <= 0:
        return
    rng = f"{col}{first}:{col}{last}"

    statuses = cfg["colors"]["status"]
    dv = DataValidation(type="list", allow_blank=True, showDropDown=False,
                        formula1='"' + ",".join(v.title() for v in statuses) + '"')
    dv.add(rng)
    ws.add_data_validation(dv)

    for value, (bg, font) in statuses.items():
        rule = FormulaRule(formula=[f'LOWER(${col}{first})="{value}"'],
                           fill=fill(bg), font=Font(name="Calibri", size=10, color=font))
        ws.conditional_formatting.add(rng, rule)


def legend_sheet(ws, cfg, scope_note=""):
    palettes = [("Test_Type", cfg["colors"]["test_type"]),
                ("Priority", cfg["colors"]["priority"]),
                ("Status", cfg["colors"]["status"])]
    gloss = {
        "positive": "happy path / valid class", "negative": "invalid input, error expected",
        "boundary": "BVA value (min/max ±1)", "exception": "exception-catalog row (A/B/C/F…)",
        "security": "injection / abuse payload",
        "p1": "highest risk — money, data loss, auth, regulatory",
        "p2": "core business flow", "p3": "supporting / rare flow",
        "not run": "never executed", "passed": "executed, all checkpoints green",
        "failed": "executed, at least one checkpoint red",
        "blocked": "cannot execute (env/data/dependency)",
        "skipped": "a skip IS a failure — see CLAUDE.md anti-patterns",
    }
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 64
    title = ws.cell(row=1, column=1,
                    value="Legend — this workbook is GENERATED (make xlsx-view) from the CSVs; "
                          "never hand-edit it. The CSVs are the truth. Style policy lives in "
                          "scripts/tc/xlsx_style.toml." + (f" {scope_note}" if scope_note else ""))
    title.font = Font(bold=True, size=11)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2)
    r = 3
    for kind, palette in palettes:
        head = ws.cell(row=r, column=1, value=kind)
        head.font = Font(bold=True)
        r += 1
        for key, (f, font) in palette.items():
            swatch = ws.cell(row=r, column=1, value=key)
            swatch.fill = fill(f)
            swatch.font = Font(color=font, bold=True)
            ws.cell(row=r, column=2, value=gloss.get(key, ""))
            r += 1
        r += 1
    note = ws.cell(row=r, column=1,
                   value="matrix block: a shaded bold `x` marks one dimension-value this case "
                         "proves (derived from design_notes.md). Colour scope of this workbook: "
                         f"{cfg['color_scope']}.")
    note.font = Font(italic=True)


def build(story_dir, cfg, preview=False):
    columns, rows = read_csv(os.path.join(story_dir, "test_cases.csv"))
    idx_columns, idx_rows = read_csv(os.path.join(story_dir, "test_cases_index.csv"))
    if not rows:
        print(f"build-xlsx: ERROR {story_dir}/test_cases.csv has no data rows.",
              file=sys.stderr)
        return 2
    matrix_start = columns.index("Basis_Ref") + 1 if "Basis_Ref" in columns else len(columns)
    idx_matrix_start = (idx_columns.index("Basis_Ref") + 1
                        if "Basis_Ref" in idx_columns else len(idx_columns))
    spans = case_spans(rows)

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Cases"
    w = SheetWriter(ws, cfg, columns, matrix_start)
    tiers = w.write_header()
    merges = w.write_body(rows, spans, merge=True)
    w.set_widths()
    freeze(ws, cfg, tiers)
    apply_page_setup(ws, cfg)
    style_status_column(ws, columns, tiers, len(rows), cfg)
    ws.auto_filter.ref = f"A{tiers}:{get_column_letter(len(columns))}{tiers + len(rows)}"

    ws2 = wb.create_sheet("Case Index")
    w2 = SheetWriter(ws2, cfg, idx_columns, idx_matrix_start)
    tiers2 = w2.write_header()
    idx_spans = [(i, i) for i in range(len(idx_rows))]
    w2.write_body(idx_rows, idx_spans, merge=False)
    w2.set_widths()
    freeze(ws2, cfg, tiers2)
    apply_page_setup(ws2, cfg)
    style_status_column(ws2, idx_columns, tiers2, len(idx_rows), cfg)
    if idx_rows:
        ws2.auto_filter.ref = f"A{tiers2}:{get_column_letter(len(idx_columns))}{tiers2 + len(idx_rows)}"

    legend_sheet(wb.create_sheet("Legend"), cfg)
    unknown = w.unknown | w2.unknown

    dest = os.path.join(story_dir, "test_cases.xlsx")
    wb.save(dest)
    problems = verify(dest, rows, idx_rows, merges)
    if problems:
        for p in problems:
            print(f"build-xlsx: VERIFY FAILED — {p}", file=sys.stderr)
        return 2
    for kind, value in sorted(unknown):
        print(f"build-xlsx: WARNING unknown {kind} {value!r} — left uncoloured. If it is "
              f"legitimate, add it to xlsx_style.toml.", file=sys.stderr)
    rel = os.path.relpath(dest, REPO_ROOT)
    print(f"build-xlsx: wrote {rel} ({len(rows)} step rows, {len(idx_rows)} cases, "
          f"{merges} merged ranges, scope={cfg['color_scope']}) — presentation only; "
          f"CSVs remain the source.")

    if preview:
        build_preview(story_dir, cfg, columns, rows, spans, matrix_start)
    return 0


def pick_preview_cases(rows, spans, cfg):
    """The NARROWEST CONTIGUOUS WINDOW of cases covering every Test_Type, Priority, and
    Status present in the file, including >= min_multi_step multi-step cases. Contiguity is
    the point: the preview renders a real slice of the sheet (merges, banding, borders all
    behave as in the full file), not a scatter-picked collage whose row order would lie.
    Falls back to the whole file when no window within max_cases covers everything — visible
    coverage beats a small sample."""
    pcfg = cfg.get("preview", {})
    max_cases = pcfg.get("max_cases", 8)
    min_multi = pcfg.get("min_multi_step", 1)

    def span_values(s, e):
        types = {(r.get("Test_Type") or "").strip().lower() for r in rows[s:e + 1]} - {""}
        prios = {(r.get("Priority") or "").strip().lower() for r in rows[s:e + 1]} - {""}
        stats = {(r.get("Status") or "").strip().lower() for r in rows[s:e + 1]} - {""}
        return types, prios, stats

    need_t = set().union(*(span_values(s, e)[0] for s, e in spans)) if spans else set()
    need_p = set().union(*(span_values(s, e)[1] for s, e in spans)) if spans else set()
    need_s = set().union(*(span_values(s, e)[2] for s, e in spans)) if spans else set()

    best = None
    n = len(spans)
    for a in range(n):
        got_t, got_p, got_s, multi = set(), set(), set(), 0
        for b in range(a, min(a + max_cases, n)):
            t, p, s = span_values(*spans[b])
            got_t |= t
            got_p |= p
            got_s |= s
            if spans[b][1] > spans[b][0]:
                multi += 1
            if got_t >= need_t and got_p >= need_p and got_s >= need_s and multi >= min_multi:
                width = spans[b][1] - spans[a][0] + 1
                if best is None or width < best[0]:
                    best = (width, a, b)
                break
    if best is not None:
        _, a, b = best
        return spans[a:b + 1]

    # No covering window exists within max_cases (a rare value — e.g. a lone `security` case —
    # sits far from the rest). Falling back to the WHOLE file would defeat the preview's
    # purpose, so pick the window of max_cases with the GREATEST value coverage instead, and
    # name what is missing so the gap is visible rather than silent.
    fallback = None
    for a in range(n):
        b = min(a + max_cases, n) - 1
        got_t, got_p, got_s, multi = set(), set(), set(), 0
        for s, e in spans[a:b + 1]:
            t, p, st = span_values(s, e)
            got_t |= t
            got_p |= p
            got_s |= st
            if e > s:
                multi += 1
        score = (len(got_t) + len(got_p) + len(got_s),
                 1 if multi >= min_multi else 0)
        if fallback is None or score > fallback[0]:
            fallback = (score, a, b)
    _, a, b = fallback
    got_t, got_p, got_s = set(), set(), set()
    for s, e in spans[a:b + 1]:
        t, p, st = span_values(s, e)
        got_t |= t
        got_p |= p
        got_s |= st
    missing = sorted((need_t - got_t) | (need_p - got_p) | (need_s - got_s))
    print("build-xlsx: WARNING no window of <= "
          f"{max_cases} cases covers every Test_Type/Priority/Status — previewing the "
          f"best-coverage window; values not shown: {', '.join(missing)} "
          f"(raise preview.max_cases in xlsx_style.toml to include them)", file=sys.stderr)
    return spans[a:b + 1]


def build_preview(story_dir, cfg, columns, rows, spans, matrix_start):
    """One sheet per colour scope over the same contiguous case window — the decision is
    made by looking at Excel, not at chat. Gitignored like every other xlsx."""
    chosen = pick_preview_cases(rows, spans, cfg)
    first, last = chosen[0][0], chosen[-1][1]
    sub_rows = rows[first:last + 1]
    sub_spans_norm = [(s - first, e - first) for s, e in chosen]

    wb = Workbook()
    wb.remove(wb.active)
    for scope in ("cell_tint", "row_tint", "banding"):
        ws = wb.create_sheet(scope)
        scoped = dict(cfg)
        scoped["color_scope"] = scope
        w = SheetWriter(ws, scoped, columns, matrix_start)
        tiers = w.write_header()
        w.write_body(sub_rows, sub_spans_norm, merge=True)
        w.set_widths()
        freeze(ws, scoped, tiers)
        apply_page_setup(ws, scoped)
        style_status_column(ws, columns, tiers, len(sub_rows), scoped)
    legend_sheet(wb.create_sheet("Legend"), cfg,
                 scope_note="PREVIEW: sheets compare colour scopes — pick one, set "
                            "color_scope in xlsx_style.toml.")
    dest = os.path.join(story_dir, cfg.get("preview", {}).get("output", "xlsx_style_preview.xlsx"))
    wb.save(dest)
    first_id, last_id = rows[first]["Test_Case_ID"], rows[last]["Test_Case_ID"]
    print(f"build-xlsx: wrote {os.path.relpath(dest, REPO_ROOT)} "
          f"(preview, {len(sub_spans_norm)} cases {first_id}…{last_id} × 3 scopes: "
          f"cell_tint / row_tint / banding) — open it, pick a scope, set color_scope in "
          f"scripts/tc/xlsx_style.toml.")


def verify(dest, rows, idx_rows, merges):
    """Read the saved file back — the artifact on disk is the fact, not save()'s exit code."""
    wb = load_workbook(dest)
    tc, ci = wb["Test Cases"], wb["Case Index"]
    problems = []
    # with a 2-tier banner, data starts one row lower; max_row accounts for it
    banner = tc.max_row - len(rows) - 1
    if banner not in (1, 2):
        problems.append(f"Test Cases has {tc.max_row - 1} header+data rows, expected "
                        f"{len(rows)} data rows + 1 or 2 header rows")
    if len(tc.merged_cells.ranges) < merges:
        problems.append(f"merged ranges {len(tc.merged_cells.ranges)} < intended {merges}")
    if ci.max_row - len(idx_rows) not in (1, 2):
        problems.append(f"Case Index has {ci.max_row} rows, expected {len(idx_rows)} "
                        f"data rows + 1 or 2 header rows")
    return problems


def story_dirs(only=None):
    """Mirror build-csv.py's discovery so both tools see the same stories."""
    if only:
        return [os.path.abspath(only)]
    found = []
    for req in sorted(os.listdir(TEST_CASES_ROOT)) if os.path.isdir(TEST_CASES_ROOT) else []:
        req_path = os.path.join(TEST_CASES_ROOT, req)
        if not os.path.isdir(req_path) or not req.startswith("REQ"):
            continue
        for us in sorted(os.listdir(req_path)):
            us_path = os.path.join(req_path, us)
            if os.path.isdir(us_path) and os.path.exists(os.path.join(us_path, "test_cases.csv")):
                found.append(us_path)
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--story", help="one story directory (containing test_cases.csv)")
    ap.add_argument("--preview", action="store_true",
                    help="also render the colour-scope comparison workbook")
    args = ap.parse_args()

    cfg = load_config()
    dirs = story_dirs(args.story)
    if not dirs:
        print("build-xlsx: no story directories with test_cases.csv found — "
              "run `make testcases` first.")
        return 0
    rc = 0
    for story in dirs:
        rc |= build(story, cfg, preview=args.preview)
    return rc


if __name__ == "__main__":
    sys.exit(main())
