---
description: "Phase 1 — Intake. Spawns story-analyst (normalise the human-supplied stories) and test-basis-analyst (reconstruct the SUT contract) in parallel, then stops at gates G1 and G0."
argument-hint: <REQ_ID>
---

# /phase1 — intake

You are the orchestrator. See `CLAUDE.md`.

## Input

`$ARGUMENTS` is `<REQ_ID>`. If missing, ask once and wait.

## Pre-checks (abort with a clear message on any failure)

1. `docs/test_stack.md` exists. If not: "stack not initialised — run `/init` first."
2. `docs/stories/REQ[ID]_*/` resolves to exactly one folder.
3. At least one `US[ID]_*.md` story file exists in it. **Stories are human-supplied** — if the folder
   is empty, stop and ask the human to add them. Do not write stories yourself, and do not spawn an
   agent to write them.

## Steps

1. **Spawn `story-analyst` and `test-basis-analyst` in parallel** — one message, two `Agent` calls,
   `subagent_type` set explicitly on each. Brief both with the REQ folder path.
   - `story-analyst`: normalise AC into atomic assertions, produce the testability defect list and
     the numbered open-questions list. It cannot ask the human — you will.
   - `test-basis-analyst`: reconstruct `docs/test_basis.md` from available documentation, mark every
     row's `Confidence`, and produce the open-questions list for the SUT team.
2. **Collect both reports.**
3. **Relay `story-analyst`'s open questions to the human** via `AskUserQuestion` — this is the first
   grill pass. Record each confirmed answer in the REQ `README.md`'s
   `## Decisions confirmed by the user (locked)` section, G-numbered. Do not proceed while a BLOCKING
   testability defect is unresolved.
4. **Run the full grill at the basis stop.** Invoke the `grill-me` skill and drive adversarial
   `AskUserQuestion` rounds over every unresolved dimension — the draft basis has surfaced the
   concrete, load-bearing decisions (error taxonomy, idempotency, permission model, boundary
   semantics). Append each resolution to the locked-decisions section.
5. **HARD STOP ×2.** Present both summaries and stop:
   - `test-basis-analyst` reports `BASIS_PENDING_CONFIRMATION` → the human runs `/approve-basis <REQ_ID>`
     after the **SUT team** has confirmed the rows. This is not a formality: an unconfirmed basis
     means every downstream test case is a guess wearing a citation.
   - `story-analyst` reports its analysis → the human runs `/approve-story <REQ_ID>`.
6. **Do NOT begin Phase 2.** Both gates are separate human-triggered commands.

## Reporting back

- REQ ID and folder path
- stories analysed, atomic AC count, BLOCKING testability defect count
- basis: confirmed / inferred / assumed row counts, and open-questions count
- next commands: `/approve-basis <REQ_ID>` and `/approve-story <REQ_ID>`
