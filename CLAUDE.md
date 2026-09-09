# virtual-qa-team — a QA-first multi-agent pipeline

This project runs as a virtual QA team of Claude Code subagents that turn **human-written user
stories** into reviewed test cases, a traceability matrix, executable automation, and a defensible
verdict about what is actually broken.

**We do not own the system under test.** That single fact reshapes everything. A build pipeline that
writes its own code can treat a red test as "the code I just wrote is wrong"; here a red test has
five possible owners, coverage cannot be measured by instrumenting code, and the correctness of every
expected result depends on a contract someone else's team controls. The design consequences of that
are spelled out in the refs, and they are the reason this is not simply a testing phase bolted onto a
development pipeline.

The concrete stack, commands, thresholds, and conventions live in `docs/test_stack.md` — agents read
it at runtime rather than assuming anything.

## The team

| Agent | Role | Model | Phase | Reads | Writes |
|---|---|---|---|---|---|
| `test-stack-init` | Stack initialiser | sonnet | `/init` | repo signals + human answers | `docs/test_stack.md`, `env_matrix.md`, `test_strategy.md` |
| `story-analyst` | Story analyst | opus | 1 | human-written stories | `story_analysis.md` — atomic AC, testability defects, open questions |
| `test-basis-analyst` | Test basis analyst | opus | 1 | SUT docs, screens, observed behaviour | `docs/test_basis.md` — the oracle, with per-row confidence |
| `test-planner` | Test planner | opus | 2 | basis + story analysis | `test_approach.md` — risk, levels, **frozen coverage denominators** |
| `impact-analyst` | Impact analyst | opus | 2 | baseline + basis change log | `impact_analysis.md` — 3 layers + reconciliation + regression scope |
| `qa-analyst` | QA analyst | opus | 3 | approach + basis + stories | `design_notes.md`, `test_cases.csv`, `tcm.md`, baseline merge |
| `automation-engineer` | Automation engineer | sonnet | 4 | `TEST_BASELINE.md` | Robot suite, keywords, page objects, test data |
| `script-reviewer` | Script reviewer | opus | 4 | baseline + scripts | findings; flips confirmed baseline states |
| `defect-analyst` | Defect analyst | opus | 6 | run artifacts + code + basis | `docs/defects/<run-id>/triage.md` — D1–D5 with evidence |
| `test-manager` | Test manager | opus | 6 | everything | sign-off verdict |

Agent definitions live in `.claude/agents/`. Shared refs in `.claude/refs/`.

## Shared refs — read these before changing how anything works

| Ref | What it settles |
|---|---|
| `test-design-techniques.md` | which techniques are mandatory at which risk rating, and the Mandatory Counting Protocol |
| `coverage-model.md` | how ">90%" is defined when there is no code coverage, and the three controls that keep it honest |
| `exception-catalog.md` | the mandatory failure-mode checklist, and declined-vs-deferred |
| `csv-schema.md` | the CSV contract, and why `Basis_Ref` is load-bearing rather than decorative |
| `triage-protocol.md` | D1–D5, the decision procedure, the evidence table, and the anti-self-healing rule |
| `qa-templates.md` | every markdown artifact's template |
| `gate-runbook.md` | what each gate runs, and the two-tier rule |
| `e2e-api-conventions.md` · `e2e-test-data-conventions.md` | Robot layout and data conventions |
| `circuit-breaker.md` | the 3-strike rule |

## On-disk contract

```
virtual-qa-team/
├── docs/
│   ├── test_stack.md              ← SINGLE SOURCE OF TRUTH: commands, conventions, thresholds
│   ├── test_strategy.md           ← scope, levels, entry/exit criteria, risk scale
│   ├── env_matrix.md              ← what local/sit/uat can and cannot do
│   ├── test_basis.md              ← THE ORACLE — living SUT contract, per-row confidence
│   ├── test_debt.md               ← deferred coverage, approved by a reviewer
│   ├── stories/REQ001_<name>/
│   │   ├── README.md              ← incl. ## Decisions confirmed by the user (locked)
│   │   ├── US001_<story>.md       ← INPUT, human-written — no agent ever edits this
│   │   ├── story_analysis.md      ← story-analyst
│   │   ├── test_approach.md       ← test-planner — the frozen denominators
│   │   └── impact_analysis.md     ← impact-analyst
│   ├── test_cases/
│   │   ├── TEST_BASELINE.md       ← 1 project = 1 baseline, all levels
│   │   └── REQ001_<name>/US001/
│   │       ├── design_notes.md    ← qa-analyst — the reviewable SOURCE
│   │       ├── test_cases.csv     ← GENERATED (make testcases) — never hand-edited; cases left,
│   │       │                          coverage X-matrix block (`AC ·`…`EXC`) right, same rows
│   │       ├── test_cases_index.csv ← one row per case + the same matrix block
│   │       ├── test_cases.xlsx    ← PRESENTATION ONLY (make xlsx-view) — gitignored, rendered
│   │       │                          from the CSVs, never read by a gate/script/agent
│   │       ├── .expected.lock     ← anti-self-healing snapshot, written at G4
│   │       ├── tcm.md             ← counts, ratios, traceability, non-compliance
│   │       ├── coverage.md        ← make coverage
│   │       └── test_report.md     ← orchestrator, /phase6
│   └── defects/<run-id>/
│       ├── triage.md              ← defect-analyst — one record per failure
│       └── artifacts/             ← gitignored evidence captures
├── tests/e2e/
│   ├── FEATURES.md                ← human-ratified feature catalog (~6–10)
│   ├── config/{import.resource, environment.yaml, auth/, extend_scripts/, wiremock/}
│   ├── keyword/<feature>/         ← per feature, one level deep
│   ├── page/<feature>/            ← per feature, UI only
│   ├── test_data/e2e_baseline.yaml   ← SINGLE project-wide file
│   ├── test_suites/e2e_baseline.robot ← SINGLE project-wide file
│   └── test_results/<date>/<time>/   ← gitignored
├── scripts/{tc,gate,e2e}/
└── .claude/{agents,commands,refs,skills}/
```

**Naming.** `REQ[ID]` and `US[ID]` are zero-padded 3-digit; `US[ID]` is globally unique across all
requirements. Test case IDs are `TC-REQ{nnn}-US{nnn}-{nnn}`; automation IDs are
`E2E-REQ{nnn}-US{nnn}-{nnn}`.

**Two files carry state that everything else depends on.** `docs/test_basis.md` is the oracle;
`docs/test_cases/TEST_BASELINE.md` is the inventory. Both are single project-wide files, and both
are edited surgically — re-read immediately before editing, never regenerate.

## Phased workflow

The **main session is the orchestrator**. It does not write test cases, scripts, or a basis — it
routes work, runs validators, captures evidence, and surfaces gates to the human.

```
/init
  ↓
/phase1 <REQ>     story-analyst ∥ test-basis-analyst
  ↓  🛑 G0 /approve-basis     (SUT team confirms the oracle)
  ↓  🛑 G1 /approve-story     (BA/PO — zero BLOCKING testability defects)
/phase2 <REQ>     test-planner ∥ impact-analyst
  ↓  🛑 G2 /approve-approach  (ratify the coverage DENOMINATORS, before any case exists)
/phase3 <REQ>     qa-analyst → make validate/coverage/testcases-check
  ↓  🛑 G4 /approve-test-case (+ make expected-lock)
/phase4           automation-engineer → script-reviewer
  ↓  🛑 G5 /approve-script    (human code review)
/phase5 <ENV>     G6 env readiness → seed → 3 rounds green
  ↓
/phase6 <run-id>  defect-analyst → 🛑 G7 /approve-triage → report → test-manager
  ↓  🛑 G8 /signoff
```

**One REQ per round.** `TEST_BASELINE.md` is a single project-wide file and the execution gate runs
the whole suite unscoped. A round that merged a second REQ's cases into the baseline before that
REQ's automation existed would make the first REQ's gate fail against behaviour nobody has built —
for reasons unrelated to the REQ under test. `/phase2` refuses to open a round while the current one
is unclosed.

### Where the gates are, and why each one is there

`.claude/refs/gate-runbook.md` has the full table. The reasoning, in one line each:

- **G0 basis** — every expected result cites this file. Wrong here means 100% rework, and no script
  can check a document against a system it cannot read.
- **G1 story** — an ambiguous AC is cheapest to fix here and most expensive to fix during execution,
  where it arrives disguised as a testing problem.
- **G2 approach** — ⭐ the gate that makes ">90%" mean something. The denominator is fixed and
  ratified **before any case exists**; ratifying it afterwards, once the score is known, would not be
  a control at all.
- **G4 test cases** — the machine already proved the arithmetic closes and every expected result is
  cited. Only a human can ask whether they are *right* and whether the assertions are strong enough
  to catch the bug.
- **G5 scripts** — a bad script does not announce itself. It passes, proving less than it claims, and
  its failures later surface as D2 noise that drowns real defects.
- **G6 environment** — running a destructive suite against shared data cannot be undone.
- **G7 triage** — classification decides who gets the work, and "flake" is the cheapest exit.
- **G8 sign-off** — the last place a weakened spec or a silent skip can still be caught.

### The two-tier rule

> **A human gate never runs on an artifact that has not passed its own machine checks.**

Every gate has an automated pre-check (`make validate`, `make coverage`, `make gate-scripts`). A
failure bounces straight back to the producing agent without consuming a human's attention. This is
the difference between eight gates that work and eight gates that get rubber-stamped: a reviewer
asked to re-check arithmetic will eventually stop reading carefully.

## Status state machine

```
test_basis.md:   draft → pending_confirmation ⇄ changes_requested → confirmed
                                 └── /approve-basis is the only writer (SUT team confirms rows)

story_analysis:  draft → pending_approval ⇄ changes_requested → approved
                                 └── /approve-story; BLOCKING defects block approval

test_approach:   draft → pending_approval ⇄ changes_requested → approved  [DENOMINATORS FROZEN]
                                 └── /approve-approach is the only writer

Test case Approval:  — → pending_approval ⇄ (revision loop) → approved | Canceled
                                 └── /approve-test-case; approval also writes .expected.lock

Script Approval:     — → pending_approval ⇄ (revision loop) → approved
                                 └── /approve-script; no Cancel option

Baseline entry:  planned → active                  (NEW)
                 modify_pending_REQ[N] → modified_by_REQ[N]   (MODIFY)
                 remove_pending_REQ[N] → removed_by_REQ[N]    (REMOVE)
                                 └── qa-analyst sets pending; ONLY script-reviewer confirms

Story:           draft → in_analysis → in_design → in_automation → in_execution
                       → in_signoff ⇄ changes_requested → done
                                 └── /signoff is the only writer of `done`
```

## Circuit breaker

Three consecutive **non-improving** `changes_requested` verdicts on the same artifact trip it. See
`.claude/refs/circuit-breaker.md`. The reviewing agent does not issue a third — it sets
`blocked_circuit_breaker`, records a hypothesis, and stops. **The orchestrator pauses the pipeline
for that REQ and never overrides the breaker.** A pass that reduces the blocking finding count is
improving and resets the streak.

## Orchestrator cheat sheet

1. **Delegate.** Never write a basis, a test case, a script, or a triage verdict yourself.
2. **Always set `subagent_type` explicitly** on every `Agent` call.
3. **Parallelise where the design allows it and nowhere else.** Phase 1 and Phase 2 spawn two agents
   in one message. **Phase 4 spawns exactly one `automation-engineer` and one `script-reviewer`** —
   they write to single shared files, so parallel invocations would clobber each other and could not
   see each other's work to reuse it.
4. **Run the validators yourself before every human gate.** `make validate`, `make coverage`,
   `make testcases-check`, `make gate-scripts`. A failure routes back to the agent, not to the human.
5. **Verify, don't trust.** Spot-check the files an agent claims to have written. A report is a
   courtesy signal; the artifact on disk is the fact.
6. **Never paraphrase a run result.** Capture verbatim summary lines. A claim without its machine
   output counts as not run.
7. **Honour every gate.** No auto-approval, ever — not the basis, not the denominators, not the test
   cases, not the triage.
8. **Write `.expected.lock` at G4.** Without it the anti-self-healing guard has no baseline and is
   silently inert — the strongest control in the pipeline, switched off by omission.
9. **Reopen gates honestly.** If a revision invalidates an approved artifact, set that approval field
   back to `pending_approval` and tell the human which command to re-run.

## Anti-patterns

**Structural**
- Omitting `subagent_type` on an `Agent` call.
- The orchestrator writing artifacts, or changing a status without a corresponding agent verdict.
- Auto-approving any gate, or presenting an artifact to a human before its validator passes.
- `/phase2` opening a round while the current one is unclosed; batching multiple REQs into one round.
- `/phase4` spawning more than one `automation-engineer` or `script-reviewer`.

**Basis and stories**
- Any agent editing a human-written story file.
- Marking a basis row `confirmed` without the SUT team's confirmation.
- Citing an `inferred`/`assumed` basis row from a test case, or counting one into a denominator.
- `story-analyst` resolving an ambiguity by choosing an interpretation, or downgrading a BLOCKING
  testability defect to unblock a round.

**Coverage**
- Computing the denominator after the cases exist, or lowering a G2-frozen denominator without a
  recorded reopen. A denominator that moves once the score is known is not a measurement.
- A coverage shortfall that appears nowhere — an omission and a decision must never look alike.
- Counting `screens × states` instead of summing `ui_states` across screens.
- Treating "not applicable" as the universal solvent: declined leaves the denominator, deferred stays
  in it and lowers the score.
- An empty boundary table — it silently inflates every ratio that depends on it.

**Test cases**
- A case with no `Basis_Ref`. No oracle, no case.
- A vague `Expected_Result` ("should fail", "error is displayed") — a 500 satisfies both.
- Hand-editing `test_cases.csv` instead of editing `design_notes.md` and regenerating.
- Reading or hand-editing `test_cases.xlsx` — it is a gitignored presentation photograph of the
  CSVs (`make xlsx-view`); a hand-edit there is silently destroyed by the next render and the
  CSVs remain the only artifact a gate, script, or agent may consume.
- **Changing an `Expected_Result` to make a failing test pass.** The single worst thing that can
  happen in this pipeline, and a D4 incident. `relaxes` requires a citation proving the OLD
  expectation was wrong; "the system behaves differently" is never that proof.

**Automation**
- `Sleep`, forced clicks, DOM manipulation to bypass a broken UI, fragile locators, raw URLs,
  hard-coded data, `expected_status=any` without an allowed set.
- An `E2E-*` ID that is not in `[Tags]` — `--include` filters by tag alone.
- Regenerating a shared file wholesale, or creating a per-US/per-REQ folder.
- Inventing a feature folder or tag that `tests/e2e/FEATURES.md` does not list.
- Bumping an existing pin in `requirements.txt` (appending a new one is fine).
- A `[Setup]` keyword doing HTTP or DB seeding — seeding is out of Robot.

**Execution and triage**
- Skipping the reseed between flake rounds — it produces deterministic failures that look exactly
  like flake, and misdiagnosing it teaches the team to distrust the flake check itself.
- Treating a skipped test as neutral. A skip is a failure.
- Excluding tests from a gate round by tag without arithmetic reconciliation.
- **Calling a deterministic failure a flake.** Three failures out of three on unchanged code with
  fresh data is a defect.
- Classifying from another agent's report instead of re-deriving from the run artifacts.
- Filing a D1 without both corroborations, or before G7 approves it.
- `defect-analyst` fixing anything — fixing as you go destroys the evidence for the classification.
