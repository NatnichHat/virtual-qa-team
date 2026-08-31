# virtual-qa-team

A multi-agent QA pipeline that turns **human-written user stories** into reviewed test cases (CSV),
a traceability matrix with provable specification coverage, Robot Framework automation portable
across local/sit/uat, and an evidence-backed verdict about what is actually broken.

Adapted from the `virtual-team-skeleton` A-Team, with one decisive difference: **that pipeline owns
its own source code; this one does not.** Everything below follows from that.

## What changes when you don't own the system under test

| | build pipeline | this pipeline |
|---|---|---|
| Coverage | line coverage of instrumented code | **specification coverage** — AC, rules, boundaries, transitions, exceptions |
| The oracle | the architecture you just wrote | `docs/test_basis.md`, reconstructed from someone else's docs and **confirmed by their team** |
| A red test means | the code I just wrote is wrong | one of **five** things — see `.claude/refs/triage-protocol.md` |
| The hard stop | architecture approval | **test basis** confirmation, and **denominator** ratification |

## Getting started

```bash
make help              # every command, with what it is for
/init                  # writes test_stack.md, env_matrix.md, test_strategy.md
```

Then put your stories in `docs/stories/REQ001_<name>/US001_<story>.md` — **you write these; no agent
ever edits them** — and run `/phase1 REQ001`.

## The flow

```
/init
/phase1 <REQ>   → G0 /approve-basis      🛑  the SUT team confirms the oracle
                → G1 /approve-story      🛑  BA/PO — zero blocking testability defects
/phase2 <REQ>   → G2 /approve-approach   🛑  ratify the coverage denominators, before any case exists
/phase3 <REQ>   → G4 /approve-test-case  🛑  cases, TCM, CSV  (+ writes .expected.lock)
/phase4         → G5 /approve-script     🛑  human code review of the automation
/phase5 <ENV>   → G6 environment readiness   seed, then 3 rounds green
/phase6 <run>   → G7 /approve-triage     🛑  who owns each failure
                → G8 /signoff            🛑
```

## Three ideas worth understanding before you use this

**1 — The denominator is ratified before the numerator exists.**
A specification-coverage percentage is only as honest as its denominator, and the denominator is
produced by the same pipeline that is graded on it. Forgetting two boundary values raises the score;
none of it looks like cheating from the inside. The control is *sequence*: G2 fixes and freezes the
denominators before a single test case is written, and `test-manager` compares them again at sign-off
to catch one that shrank once the score was known. See `.claude/refs/coverage-model.md`.

**2 — Every expected result cites an oracle.**
The `Basis_Ref` column is not decorative traceability. It is what makes a *wrong expectation*
mechanically detectable: when a test fails, the first question is whether the system's actual
behaviour matches the cited basis. If yes, our expectation was wrong (D3). If no, it is a real defect
(D1). Without the citation, that question has no answer and every failure becomes an argument.

**3 — No agent may change an expected result to make a test pass.**
Self-healing is the failure mode that destroys a test suite silently: every run stays green while the
suite gradually stops asserting anything. `make expected-lock` snapshots the approved expected
results at G4; `expected-drift.py` fails the build on any later change without a classified,
cited revision entry. *"The system behaves differently"* is never a valid justification — a test case
binds to the specification, not the implementation.

## The two-tier gate rule

A human gate never runs on an artifact that has not passed its own machine checks. `make validate`,
`make coverage`, and `make gate-scripts` bounce incomplete work straight back to the producing agent.
Reviewers only ever see internally consistent artifacts, so they can spend their attention on the
question no script can ask: **is this actually right?**

## Layout

```
docs/test_stack.md          single source of truth — commands, conventions, thresholds
docs/test_basis.md          the oracle: SUT contract with per-row confidence
docs/test_strategy.md       scope, levels, entry/exit criteria, risk scale
docs/env_matrix.md          what local/sit/uat can and cannot do
docs/stories/               your stories (input) + analysis, approach, impact
docs/test_cases/            design notes, CSV, TCM, coverage, reports + TEST_BASELINE.md
docs/defects/               triage records
tests/e2e/                  Robot Framework — one shared suite, per-feature keywords
.claude/{agents,commands,refs}/
```

`CLAUDE.md` is the orchestrator contract. `.claude/refs/` holds the reasoning behind every rule —
read those before changing how anything works, because most of the rules exist to close a specific
failure mode rather than to impose a style.

## A note on Robot Framework

The automation track is Robot-only by design, not by configuration. The conventions, the `output.xml`
zero-skip enforcement in `scripts/e2e/run-e2e.py`, and the `[Tags]`-based traceability are all written
against it. Switching to Playwright or Cypress is a fork-level change to those files and scripts, not
a value you can type into `test_stack.md`.
