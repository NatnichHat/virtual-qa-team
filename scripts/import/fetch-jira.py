#!/usr/bin/env python3
"""Import one Jira issue into a story file this pipeline can read.

This is a MECHANICAL TRANSCRIPTION TOOL, not an agent. It does not interpret, invent, or judge —
it moves text from Jira's fields into the story file's sections and leaves everything else for a
human to finish. That distinction matters: CLAUDE.md's rule that "stories are human-supplied, no
agent ever edits them" holds here because a human wrote the content in Jira; this script only
changes its container.

Consequences of that:
  - Acceptance-criteria extraction is regex/heading-based, never inferred. If Jira doesn't clearly
    mark an AC section, the script leaves `## Acceptance criteria` EMPTY with a comment telling you
    to split it yourself from the raw imported text. It never guesses Given/When/Then out of prose.
  - Every field it could not confidently place goes under `## Needs human review`, not silently
    dropped and not silently reformatted into something that looks more complete than it is.
  - The story is written with `Status: draft` — story-analyst and G1 still apply in full. Importing
    from Jira does not skip testability review; if anything it makes it MORE necessary, since Jira
    tickets are usually written for a dev audience, not a test-design audience.

Jira wiki-markup -> Markdown conversion (best effort, not exhaustive):
  h1./h2./h3.  -> #/##/###        {code}...{code}     -> ``` fences
  *  bullet    -> - bullet         {quote}...{quote}   -> > blockquote
  #  numbered  -> 1. numbered      [text|url]          -> [text](url)
  *bold*       -> **bold**

Usage:
  # 1. copy .env.example to .env at the repo root and fill in JIRA_SITE / JIRA_EMAIL / JIRA_API_TOKEN
  # 2. dry run against the real API first — nothing is written to disk:
  python3 scripts/import/fetch-jira.py PROJ-123 --dry-run

  # 3. write it for real:
  python3 scripts/import/fetch-jira.py PROJ-123

  # offline / no network / no credentials yet — test against a saved issue JSON instead:
  python3 scripts/import/fetch-jira.py PROJ-123 --from-json fixtures/PROJ-123.json --dry-run

  # override auto-numbering / naming:
  python3 scripts/import/fetch-jira.py PROJ-123 --req REQ001 --name order_management
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORIES_ROOT = os.path.join(REPO_ROOT, "docs", "stories")
DOTENV = os.path.join(REPO_ROOT, ".env")


# ── credentials ──────────────────────────────────────────────────────────────
def load_dotenv(path):
    """Minimal KEY=VALUE parser. No third-party dependency for something this small."""
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def resolve_credentials(args):
    env = {**load_dotenv(DOTENV), **os.environ}
    site = args.site or env.get("JIRA_SITE")
    email = args.email or env.get("JIRA_EMAIL")
    token = args.token or env.get("JIRA_API_TOKEN")
    missing = [n for n, v in (("JIRA_SITE", site), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)) if not v]
    return site, email, token, missing


# ── Jira fetch ───────────────────────────────────────────────────────────────
def fetch_issue(site, email, token, issue_key):
    """GET /rest/api/2/issue/{key}. v2, not v3 — v2 returns description as a plain wiki-markup
    string on Jira Cloud; v3 returns Atlassian Document Format (nested JSON) which would need a
    much heavier converter for no benefit here."""
    site = site.rstrip("/")
    url = f"{site}/rest/api/2/issue/{issue_key}"
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 401:
            raise SystemExit(f"fetch-jira: 401 Unauthorized — check JIRA_EMAIL / JIRA_API_TOKEN.\n{body}")
        if e.code == 404:
            raise SystemExit(f"fetch-jira: 404 — issue {issue_key!r} not found (or you lack permission).")
        raise SystemExit(f"fetch-jira: HTTP {e.code} from Jira:\n{body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"fetch-jira: could not reach {site} — {e.reason}")


# ── wiki markup -> markdown (best effort) ──────────────────────────────────
HEADING = re.compile(r"^h([1-6])\.\s*(.*)$")
BULLET = re.compile(r"^(\*{1,3})\s+(.*)$")
NUMBERED = re.compile(r"^#{1,3}\s+(.*)$")
LINK = re.compile(r"\[([^|\]]+)\|([^\]]+)\]")
BOLD = re.compile(r"(?<!\*)\*([^\s*][^*]*?)\*(?!\*)")


def wiki_to_markdown(text):
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    out, in_code = [], False
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("{code"):
            in_code = not in_code
            out.append("```" if not in_code else "```")  # toggled below correctly
            continue
        if in_code:
            out.append(line)
            continue

        if stripped.startswith("{quote}") or stripped.startswith("{quote"):
            continue  # markers only; content lines around it read fine without special handling

        m = HEADING.match(stripped)
        if m:
            out.append(f"{'#' * int(m.group(1))} {m.group(2)}")
            continue

        m = BULLET.match(line)
        if m:
            depth = len(m.group(1)) - 1
            out.append(f"{'  ' * depth}- {m.group(2)}")
            continue

        m = NUMBERED.match(line)
        if m:
            out.append(f"1. {m.group(1)}")
            continue

        line = LINK.sub(r"[\1](\2)", line)
        line = BOLD.sub(r"**\1**", line)
        out.append(line)

    # fix the {code} toggle: opening emits ``` , closing should too but without re-toggling text
    fixed = []
    depth = 0
    for l in out:
        if l == "```":
            depth = 1 - depth
        fixed.append(l)
    return "\n".join(fixed)


# ── AC extraction — mechanical only, never inferred ────────────────────────
AC_HEADING = re.compile(
    r"^#{0,3}\s*(acceptance criteria|ac|เกณฑ์การยอมรับ|เงื่อนไขการยอมรับ)\s*:?\s*$", re.I
)
NEXT_HEADING = re.compile(r"^#{1,6}\s+\S")


def split_ac_block(markdown_text):
    """Return (ac_block_or_None, remaining_text). Looks for a heading literally naming
    'Acceptance Criteria' (English or Thai) and takes everything until the next heading or EOF.
    This is pattern matching, not comprehension — a section titled anything else is left alone."""
    lines = markdown_text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if AC_HEADING.match(line.strip()):
            start = i
            break
    if start is None:
        return None, markdown_text

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if NEXT_HEADING.match(lines[j]) and not AC_HEADING.match(lines[j].strip()):
            end = j
            break

    ac_block = "\n".join(lines[start + 1:end]).strip("\n")
    remaining = "\n".join(lines[:start] + lines[end:]).strip("\n")
    return (ac_block or None), remaining


# ── ID allocation ────────────────────────────────────────────────────────────
def next_req_id():
    if not os.path.isdir(STORIES_ROOT):
        return "REQ001"
    nums = [int(m.group(1)) for d in os.listdir(STORIES_ROOT)
            if (m := re.match(r"REQ(\d{3})_", d))]
    return f"REQ{(max(nums) + 1) if nums else 1:03d}"


def next_us_id():
    """Globally unique across ALL requirements, per CLAUDE.md's naming rule."""
    nums = []
    if os.path.isdir(STORIES_ROOT):
        for req_dir in os.listdir(STORIES_ROOT):
            full = os.path.join(STORIES_ROOT, req_dir)
            if not os.path.isdir(full):
                continue
            for f in os.listdir(full):
                m = re.match(r"US(\d{3})_", f)
                if m:
                    nums.append(int(m.group(1)))
    return f"US{(max(nums) + 1) if nums else 1:03d}"


def slugify(text, max_words=6):
    s = re.sub(r"[^\w\s-]", "", text.lower())
    words = re.split(r"[\s_-]+", s.strip())[:max_words]
    return "_".join(w for w in words if w) or "untitled"


# ── render ───────────────────────────────────────────────────────────────────
def render_story(fields, issue_key, site, req_id, us_id, ac_block, remaining_desc):
    summary = fields.get("summary", "").strip()
    status = fields.get("status", {}).get("name", "")
    reporter = (fields.get("reporter") or {}).get("displayName", "unknown")
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{site.rstrip('/')}/browse/{issue_key}"

    ac_section = ""
    if ac_block:
        # A straight copy of what Jira had — no invented scaffolding, no fake Given/When/Then
        # wrapper around a sentence that already says "given X, when Y, then Z" in prose. Adding
        # placeholder structure around real content would look more finished than it is.
        ac_section = (
            "<!-- NOT YET in proper Given/When/Then form — this is a bullet-for-bullet copy of "
            "Jira's \"Acceptance Criteria\" section. Split each line into a real scenario "
            "(separate Given/When/Then, one assertion each) before /phase1; several of these "
            "one-liners likely bundle more than one testable outcome. -->\n\n"
            f"{ac_block}"
        )
    else:
        ac_section = (
            "<!-- fetch-jira found no \"Acceptance Criteria\" heading in this issue. AC was NOT "
            "guessed from the story text below — that would be invention, which this tool refuses "
            "to do. Read \"## Story (imported)\" and write real Given/When/Then scenarios yourself. -->"
        )

    return f"""# {us_id} — {summary or '[untitled]'}

**Requirement:** {req_id}
**Status:** draft
**Source:** [{issue_key}]({url}) — fetched {fetched_at} — Jira status at fetch time: {status or 'unknown'} — reporter: {reporter}

> Imported by `scripts/import/fetch-jira.py`, a mechanical transcription tool — not an agent.
> Nothing below was invented. Sections the tool could not confidently place are under
> `## Needs human review`. **This file is still human-owned from here — edit it freely, and it
> still goes through `story-analyst` and gate G1 like any other story.**

## Story
As a [persona], I want [capability], so that [benefit].

<!-- fetch-jira does not infer the persona/capability/benefit split — Jira summaries and
descriptions are rarely written in this exact shape. Fill this in from "## Story (imported)" below. -->

## Acceptance criteria
{ac_section}

## Out of scope
- [explicit non-goals]

## Dependencies
- [other US IDs, external systems, data]

## Needs human review
- [ ] Rewrite `## Story` in As a/I want/so that form.
- [ ] {'Rewrite the AC scenarios into real Given/When/Then.' if ac_block else 'No AC heading found in Jira — write AC from scratch using "## Story (imported)" below.'}
- [ ] Confirm nothing in "## Story (imported)" describes IMPLEMENTATION rather than BEHAVIOUR — Jira
      tickets often do, and story-analyst needs the latter.
- [ ] Delete this section once resolved.

## Story (imported)
Raw text from the Jira description, converted from wiki markup to Markdown. This is the source
material for every section above — kept here in full so nothing from the original ticket is lost.

{remaining_desc.strip() or '_(Jira description was empty.)_'}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("issue", help="Jira issue key, e.g. PROJ-123")
    ap.add_argument("--req", help="REQ id to file under (default: next available)")
    ap.add_argument("--us", help="US id (default: next available, globally unique)")
    ap.add_argument("--name", help="requirement folder slug (default: derived from summary)")
    ap.add_argument("--dry-run", action="store_true", help="print the story, write nothing")
    ap.add_argument("--from-json", help="read a saved issue JSON instead of calling the API")
    ap.add_argument("--site", help="override JIRA_SITE")
    ap.add_argument("--email", help="override JIRA_EMAIL")
    ap.add_argument("--token", help="override JIRA_API_TOKEN")
    args = ap.parse_args()

    if args.from_json:
        with open(args.from_json, encoding="utf-8") as fh:
            issue = json.load(fh)
        site = args.site or "https://example.atlassian.net"
        print(f"fetch-jira: reading from {args.from_json} (offline mode, no network call made)")
    else:
        site, email, token, missing = resolve_credentials(args)
        if missing:
            print(f"fetch-jira: missing {', '.join(missing)}.", file=sys.stderr)
            print(f"  Copy .env.example to .env at the repo root and fill them in, or pass "
                  f"--site/--email/--token, or use --from-json to test offline.", file=sys.stderr)
            return 2
        issue = fetch_issue(site, email, token, args.issue)

    fields = issue.get("fields", {})
    description_md = wiki_to_markdown(fields.get("description") or "")
    ac_block, remaining_desc = split_ac_block(description_md)

    req_id = args.req or next_req_id()
    us_id = args.us or next_us_id()
    name = args.name or slugify(fields.get("summary", "") or args.issue)

    story = render_story(fields, args.issue, site, req_id, us_id, ac_block, remaining_desc)

    if args.dry_run:
        print(story)
        print(f"\n--- dry run: would write to "
              f"docs/stories/{req_id}_{name}/{us_id}_{name}.md ---")
        return 0

    req_dir = os.path.join(STORIES_ROOT, f"{req_id}_{name}")
    os.makedirs(req_dir, exist_ok=True)
    dest = os.path.join(req_dir, f"{us_id}_{name}.md")
    if os.path.exists(dest):
        print(f"fetch-jira: {os.path.relpath(dest, REPO_ROOT)} already exists — refusing to "
              f"overwrite a human-owned file. Pass --us/--name/--req to choose a different path, "
              f"or edit/delete the existing file yourself.", file=sys.stderr)
        return 1

    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(story)

    readme = os.path.join(req_dir, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write(f"""# {req_id} — {fields.get('summary', '').strip() or '[requirement name]'}

**Summary:** [one paragraph — what this requirement covers and why]

## Stories
- [{us_id}]({us_id}_{name}.md) — {fields.get('summary', '').strip()}

## Decisions confirmed by the user (locked)
_(populated by the orchestrator during the /phase1 grill — nothing here yet)_
""")
        print(f"fetch-jira: also created {os.path.relpath(readme, REPO_ROOT)} (first story in this REQ)")

    print(f"fetch-jira: wrote {os.path.relpath(dest, REPO_ROOT)}")
    print(f"\nNext: open the file and resolve every '## Needs human review' item BEFORE running "
          f"/phase1 {req_id} — story-analyst will otherwise correctly flag the raw import as "
          f"untestable, which is working as intended but costs you a review cycle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
