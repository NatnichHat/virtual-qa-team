---
name: grill-me
description: "Relentless requirement interrogation for the QA pipeline. Use BEFORE the basis/story HARD STOPs — when story-analyst or test-basis-analyst surfaces open questions (the orchestrator relays them as a numbered list), and most importantly at the basis HARD STOP in /phase1 (orchestrator runs the full grill via AskUserQuestion before G0). Drives every acceptance criterion down to a testable assertion with zero material unknowns and records the resolved decisions as a locked artifact."
---

# Grill-Me — requirement interrogation

A raw requirement is a **hypothesis, not a spec**. Before any test case is designed against it,
the requirement and its oracle are **interrogated** with the user until there are **zero material
unknowns** — every acceptance criterion can be written as a testable assertion with no `TODO`, no
"TBD", and no silent assumption. Covering the checklist below — not "the user seemed clear" — is
the exit condition.

## The hard constraint (read this first)

**Subagents cannot ask the user questions.** In this harness, the interactive question tool
(`AskUserQuestion`) only works from the **main orchestrator session**. So the agents that are
*supposed* to grill (`story-analyst`, `test-basis-analyst`) are exactly the agents that **cannot
talk to the user**. Therefore:

- **story-analyst and test-basis-analyst (and any subagent) READ this checklist and follow it, but
  they do not interrogate the user.** They surface their open questions back up to the orchestrator
  as a numbered list (`story_analysis.md` → Open questions; `test_basis.md` → Open questions).
- **The orchestrator performs the actual interrogation** via `AskUserQuestion`, relaying the
  agents' open questions and then driving the full grill.
- **The best moment to grill is the basis HARD STOP in /phase1** (after `test-basis-analyst`
  drafts `docs/test_basis.md`, before G0). Nothing downstream has started yet, and the draft
  surfaces concrete, load-bearing decisions a pure-text intake would miss (per-row `inferred`
  assumptions, status codes nobody documented, state transitions the docs leave implicit,
  validation rules with no stated threshold). The second moment is the story stop before G1 —
  every BLOCKING testability defect is a grill question.

## How to run the grill (orchestrator)

- **Question in rounds.** Each round asks the 1–4 highest-uncertainty / highest-risk questions
  first (a wrong guess there is the most expensive). Use the answers to go deeper.
- **Be adversarial, not passive.** Propose the awkward edge case and ask what should happen.
  Challenge vague answers ("usually", "it should just work", "obviously") down to a concrete rule.
  Surface every assumption *explicitly* and make the user confirm or reject it.
- **Offer a recommended default** as the first option, but never let a default stand in for an
  answer on anything load-bearing.
- **Stop only when** each AC is a testable assertion with no TBD and no silent assumption, and no
  `inferred`/`assumed` basis row that a planned case will cite remains unconfirmed.
- **Record the catch.** Every resolved ambiguity and every confirmed assumption goes into a
  durable artifact — the REQ `README.md`'s `## Decisions confirmed by the user (locked)` section.
  Number them (G1, G2, … for grill-round decisions) and cite them in story ACs and basis rows so
  downstream agents inherit a hardened spec.
- **Route confirmed contract facts back down:** an answer that settles a behaviour the SUT is
  expected to have belongs in `test_basis.md` (confidence upgraded at G0), not only in the
  locked-decisions list.

## The grill checklist (cover every dimension; don't stop at the happy path)

1. **Problem & success** — what problem does the story solve, really? Who hurts today? What's
   "done" measurably? What happens if we DON'T build it? What's explicitly a non-goal?
2. **Actors & permissions** — who uses it; roles; what each role may/never do; owner-only vs
   any-authenticated; unauthenticated behavior.
3. **Scope boundary** — what is explicitly OUT? Which tempting adjacent things are NOT included.
4. **Happy path + every unhappy path** — main flow, then empty/zero state, invalid input,
   not-found, unauthorized, conflict, timeout, partial failure, retried/duplicate request,
   concurrent actors, external dependency down or slow.
5. **Data & contracts** — exact field shapes, types, units, formats; required vs optional; source
   of truth; validation rules; persisted vs derived; migration/back-compat. (These become the
   `test_basis.md` rows — pin the exact status codes and error envelopes.)
6. **Edge cases & limits** — zero/one/many; max sizes & boundary values; duplicates; ordering;
   idempotency; race conditions.
7. **Non-functionals** — security (authz, secrets/PII, injection, audit), performance & scale,
   availability, observability. Which are in-scope to *test* now? (Anything not testable at our
   levels gets recorded as out of scope in `test_strategy.md`, not silently dropped.)
8. **External dependencies & failure modes** — which third-party services; exact behaviour when
   each errors, throttles, or is unreachable; credential handling. (These decide which WireMock
   stubs the local run needs.)
9. **UI / UX** (user-facing) — entry point; loading/empty/error/success states; confirmation for
   destructive actions; feedback (toasts/banners); no hidden-control / URL-param workarounds.
   (Also: which elements have `data-testid` — the testid risk register lives in `test_basis.md`.)
10. **Acceptance criteria** — pin each AC to a concrete, observable, testable assertion, and
    settle its observable level (api / ui / db / integration).
11. **Conflicts** — flag anything that conflicts with `docs/test_strategy.md`, the test basis, or
    another requirement, and resolve it with the user before locking.

## The locked-decisions artifact

Write resolved ambiguities and confirmed assumptions into the REQ `README.md`:

```markdown
## Decisions confirmed by the user (locked)
- **G1** — [question that was open] → [the concrete, testable rule the user confirmed].
- **G2** — [assumption surfaced] → [confirmed | rejected, with the rule].
```

Downstream agents (test-planner, qa-analyst, automation-engineer) treat these as hard constraints
and may cite them by ID (e.g. `Implements: G2`).

## Anti-patterns to forbid

- Proceeding while any checklist dimension is unresolved.
- Accepting "obviously / usually / it should just work" as an answer.
- Burying an assumption in the basis or the story instead of confirming it.
- Asking one polite clarifying question and moving on (that is not a grill).
- Expecting a subagent to interrogate the user — it structurally cannot; route through the
  orchestrator.
- An agent resolving an ambiguity by choosing an interpretation — that is the grill's job, and
  only the human's answer counts.
