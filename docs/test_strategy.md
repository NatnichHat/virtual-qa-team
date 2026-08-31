# Test Strategy

> **Project-supplied.** `/init` drafts it from your answers; a human owns it thereafter.
> Every agent reads this to know what is in scope and what "done" means.
> Anything not stated here is NOT in scope — silence is a decision, not an omission.

## Mission
[What this test effort exists to prove, and for whom.]

## System under test
- **Name / owner team:** [who builds it, who you file defects to]
- **We do NOT own its source code.** Failures are triaged, not fixed here — see `.claude/refs/triage-protocol.md`.
- **Documentation available:** [Confluence spaces, screen walkthroughs, whatever exists]
- **Access:** [how we reach it per environment — see `docs/env_matrix.md`]

## Levels in scope
| Level | In scope | Owner | Notes |
|---|---|---|---|
| API / Backend | yes | automation-engineer | RequestsLibrary, per-endpoint keywords |
| UI / Browser | yes | automation-engineer | Browser library, `data-testid` locators required |
| DB verification | yes | automation-engineer | read-only assertions on side effects |
| Integration / third-party | yes | automation-engineer | WireMock stubs, local only |
| Performance | [no — out of scope] | — | state it explicitly either way |
| Security | [no — out of scope] | — | state it explicitly either way |
| Accessibility | [no — out of scope] | — | state it explicitly either way |

## Test design approach
- Techniques are mandatory per `.claude/refs/test-design-techniques.md`, applied to a depth set by
  the story's **risk rating** (P1 = full technique set; P2 = EP + BVA + exception; P3 = happy path +
  primary negatives).
- Every exception category in `.claude/refs/exception-catalog.md` is either covered or explicitly
  declined with a recorded reason. Silence is not a decline.

## Coverage targets
See `docs/test_stack.md` → Coverage thresholds. In summary: **AC coverage 100%**, every other
dimension ≥90%, measured against denominators a human ratified at G2 *before* cases were written.

## Entry criteria (before test design starts)
- [ ] `docs/test_basis.md` exists and its rows for this REQ are `Confidence: confirmed` (G0 passed)
- [ ] User story provided with acceptance criteria; `story_analysis.md` has zero open testability defects (G1 passed)
- [ ] Environment reachable and credentials provisioned for at least one environment

## Exit criteria (before sign-off)
- [ ] Every coverage dimension meets its threshold
- [ ] Zero test cases in `Not Run`; zero skipped tests in the run (a skip is a failure, never a neutral)
- [ ] 3 consecutive green rounds with a reseed before each
- [ ] Every failure has a Triage Record with a class and ≥2 pieces of evidence, approved at G7
- [ ] Every D1 has a defect ticket raised with the SUT team
- [ ] Test report's commit SHA equals current HEAD
- [ ] No `<TBD>` or placeholder text left in any artifact for this REQ

## Risk rating scale
| Rating | Meaning | Technique depth |
|---|---|---|
| P1 | money, data loss, auth/authz, regulatory, or irreversible action | full technique set, all exception categories |
| P2 | core business flow, high usage | EP + BVA + decision table + exception catalog |
| P3 | supporting/rare flow, cosmetic | happy path + primary negatives |

## Out of scope
- [explicit non-goals — write them down, they are as load-bearing as the goals]
