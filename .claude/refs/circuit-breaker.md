# Shared ref — circuit breaker (3 strikes)

Applies to **tech-lead-reviewer** (per task, counting `### Review pass N` entries) and **po-ba** (per story, counting `### Sign-off pass N` entries). Three consecutive **non-improving** `changes_requested` verdicts on the same task or story trip the breaker.

## Rule

Before issuing a `changes_requested` verdict, compare the new finding set with prior same-artifact `changes_requested` log entries.

Track at minimum:
- total blocking finding count,
- recurring finding identifiers/themes,
- whether the current pass reduced, changed, or increased the blocking set.

A pass is **improving** when the blocking finding count decreases or the recurring blocker is actually resolved, even if new smaller findings remain. Improvement resets the non-improving streak to zero.

If this would be the **3rd consecutive non-improving `changes_requested`** (the artifact has already failed twice without the blocking set shrinking and is failing again):

1. **DO NOT** issue a 3rd `changes_requested`.
2. Set the artifact to `Status: blocked_circuit_breaker`.
3. Append a final log entry titled `CIRCUIT BREAKER TRIPPED` listing:
   - the recurring issue(s) across the three passes,
   - what was tried each time,
   - your hypothesis for why the loop is stuck (architecture wrong? spec wrong? requirement/AC wrong? skill gap?).
4. **Stop. Report `CIRCUIT_BREAKER_TRIPPED`** to the orchestrator with the artifact path.

## Reset

A non-improving streak resets to zero on an `approved` pass **or** on a `changes_requested` pass whose blocking finding count decreases / recurring blocker is resolved. If you approve and a *later* round of rework comes back, the counter starts fresh.

## Non-negotiable

Never bypass the breaker. Even if you think the fix is one small change away, say so in your report — but still trip the breaker so a human decides. The orchestrator pauses the whole pipeline for that requirement and surfaces the three failed passes + your hypothesis to the human via `AskUserQuestion`; resume only on explicit human direction. **The orchestrator must never override the breaker.**
