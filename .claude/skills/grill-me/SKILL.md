---
name: grill-me
description: "Relentless requirement interrogation. Use BEFORE locking a design — at po-ba intake (subagent reads the checklist to produce its open-questions list) and, most importantly, at the architecture HARD STOP (orchestrator runs the full grill via AskUserQuestion before approval). Drives every acceptance criterion down to a testable assertion with zero material unknowns and records the resolved decisions as a locked artifact."
---

# Grill-Me — requirement interrogation

A raw requirement is a **hypothesis, not a spec**. Before writing a single story, design, or line of
code, the requirement is **interrogated** with the user until there are **zero material unknowns** —
every acceptance criterion can be written as a testable assertion with no `TODO`, no "TBD", and no
silent assumption. Covering the checklist below — not "the user seemed clear" — is the exit condition.

## The hard constraint (read this first)

**Subagents cannot ask the user questions.** In this harness, the interactive question tool
(`AskUserQuestion`) only works from the **main orchestrator session**. So the agent that is *supposed*
to grill (po-ba) is the one agent that **cannot talk to the user**. Therefore:

- **po-ba (and any subagent) READ this checklist and follow it, but they do not interrogate the user.**
  po-ba surfaces its open questions back up to the orchestrator as a numbered list.
- **The orchestrator performs the actual interrogation** via `AskUserQuestion`, relaying po-ba's open
  questions and then driving the full grill.
- **The best moment to grill is the architecture HARD STOP** (after a draft `architecture.md` exists,
  before approval / Phase 2). Nothing downstream has started, and the draft surfaces concrete,
  load-bearing decisions a pure-text intake would miss (migration data-loss, encryption posture, error
  taxonomy, duplicate/idempotency rules, etc.).

## How to run the grill (orchestrator)

- **Question in rounds.** Each round asks the 1–4 highest-uncertainty / highest-risk questions first
  (a wrong guess there is the most expensive). Use the answers to go deeper.
- **Be adversarial, not passive.** Propose the awkward edge case and ask what should happen. Challenge
  vague answers ("usually", "it should just work", "obviously") down to a concrete rule. Surface every
  assumption *explicitly* and make the user confirm or reject it.
- **Offer a recommended default** as the first option, but never let a default stand in for an answer
  on anything load-bearing.
- **Stop only when** each AC is a testable assertion with no TBD and no silent assumption.
- **Record the catch.** Every resolved ambiguity and every confirmed assumption goes into a durable
  artifact — a `## Decisions confirmed by the user (locked)` section in the REQ `README.md` (and/or the
  affected stories). Number them (G1, G2, … for grill-round decisions; D1, D2, … if you prefer one
  scheme) and cite them in story ACs so downstream agents inherit a hardened spec.

## The grill checklist (cover every dimension; don't stop at the happy path)

1. **Problem & success** — what problem, really? Who hurts today? What's "done" measurably? What
   happens if we DON'T build it? What's explicitly a non-goal?
2. **Actors & permissions** — who uses it; roles; what each role may/never do; owner-only vs
   any-authenticated; unauthenticated behavior.
3. **Scope boundary** — what is explicitly OUT? Which tempting adjacent things are NOT included.
4. **Happy path + every unhappy path** — main flow, then empty/zero state, invalid input, not-found,
   unauthorized, conflict, timeout, partial failure, retried/duplicate request, concurrent actors,
   external dependency down or slow.
5. **Data & contracts** — exact field shapes, types, units, formats; required vs optional; source of
   truth; validation rules; persisted vs derived; migration/back-compat.
6. **Edge cases & limits** — zero/one/many; max sizes & boundary values; duplicates; ordering;
   idempotency; race conditions.
7. **Non-functionals** — security (authz, secrets/PII, injection, audit), performance & scale,
   availability, observability. Which are in-scope to *enforce now*?
8. **External dependencies & failure modes** — which services/SDKs; exact behavior when each errors,
   throttles, or is unreachable; credential handling.
9. **UI / UX** (user-facing) — entry point; loading/empty/error/success states; confirmation for
   destructive actions; feedback (toasts/banners); no hidden-control / URL-param workarounds.
10. **Acceptance criteria** — pin each AC to a concrete, observable, testable assertion.
11. **Conflicts & vision fit** — flag anything that conflicts with the product vision
    (`docs/product_vision.md`, if present) or another requirement, and resolve it with the user before
    locking.

## The locked-decisions artifact

Write resolved ambiguities and confirmed assumptions into the REQ `README.md`:

```markdown
## Decisions confirmed by the user (locked)
- **G1** — [question that was open] → [the concrete, testable rule the user confirmed].
- **G2** — [assumption surfaced] → [confirmed | rejected, with the rule].
```

Downstream agents (system-architect, qa-analyst, devs) treat these as hard constraints and may cite
them by ID (e.g. `Implements: G2`).

## Anti-patterns to forbid

- Proceeding while any checklist dimension is unresolved.
- Accepting "obviously / usually / it should just work" as an answer.
- Burying an assumption in the spec instead of confirming it.
- Asking one polite clarifying question and moving on (that is not a grill).
- Expecting a subagent to interrogate the user — it structurally cannot; route through the orchestrator.
