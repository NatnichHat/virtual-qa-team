# Shared ref — circuit breaker (3 strikes)

Applies to **every review loop in this pipeline that can issue a `changes_requested` verdict**:

| Review loop | Reviewer | Artifact under review | Where passes are counted |
|---|---|---|---|
| Script review (phase 4) | `script-reviewer` | automation-engineer's scripts + scaffold | its findings reports, per round |
| Sign-off (phase 6) | `test-manager` | test report, coverage, triage records | `### Sign-off pass N` entries in the report |
| Human gates G0 / G1 / G2 / G4 / G5 / G7 / G8 | the human approver | the gate's artifact | the orchestrator counts revision passes (e.g. the `G4 human review pass N` driver in `design_notes.md`'s Spec change log) |

Three consecutive **non-improving** `changes_requested` verdicts on the same artifact trip the
breaker.

## Rule

Before issuing a `changes_requested` verdict, compare the new finding set with prior same-artifact
`changes_requested` passes.

Track at minimum:
- total blocking finding count,
- recurring finding identifiers/themes,
- whether the current pass reduced, changed, or increased the blocking set.

A pass is **improving** when the blocking finding count decreases or the recurring blocker is
actually resolved, even if new smaller findings remain. Improvement resets the non-improving
streak to zero.

If this would be the **3rd consecutive non-improving `changes_requested`** (the artifact has
already failed twice without the blocking set shrinking and is failing again):

1. **DO NOT** issue a 3rd `changes_requested`.
2. Set the artifact's status to `blocked_circuit_breaker`.
3. Append a final entry titled `CIRCUIT BREAKER TRIPPED` listing:
   - the recurring issue(s) across the three passes,
   - what was tried each time,
   - your hypothesis for why the loop is stuck (basis wrong? story AC wrong? approach/denominators
     wrong? agent misreading a convention?).
4. **Stop. Report `CIRCUIT_BREAKER_TRIPPED`** to the orchestrator with the artifact path.

For a **human gate**, the reviewing agent does not issue the verdict — the orchestrator is the one
that sees the third rejected pass, and it is the orchestrator that marks the artifact
`blocked_circuit_breaker` and stops routing it back for another attempt.

## Reset

A non-improving streak resets to zero on an `approved` pass **or** on a `changes_requested` pass
whose blocking finding count decreases / recurring blocker is resolved. If you approve and a
*later* round of rework comes back, the counter starts fresh.

## Non-negotiable

Never bypass the breaker. Even if you think the fix is one small change away, say so in your
report — but still trip the breaker so a human decides. The orchestrator pauses the pipeline for
that requirement and surfaces the three failed passes + the hypothesis to the human via
`AskUserQuestion`; resume only on explicit human direction. **The orchestrator must never override
the breaker.**
