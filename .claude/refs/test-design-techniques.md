# Shared ref — test design techniques and the Mandatory Counting Protocol

Authoritative. `qa-analyst` follows this to derive test cases; `test-planner` uses it to set depth;
`test-manager` and the human gates audit against it. Do not re-inline it into an agent definition.

**The core discipline: count before you write.** Produce the numbers first, the cases second. If the
numbers do not add up, the design is provably incomplete — and that is visible to a reviewer in
seconds, which is the entire point. A spec that arrives without its arithmetic is not reviewable, it
is only readable.

---

## 1. Depth is set by risk, not by enthusiasm

`test-planner` assigns each acceptance criterion a rating (see `docs/test_strategy.md`). The rating
decides which techniques are mandatory. This is what makes ≥90% coverage affordable — without it,
every trivial AC gets the same treatment as a payment flow and the effort collapses under its own
weight.

| Rating | Applies to | Mandatory techniques |
|---|---|---|
| **P1** | money, data loss, auth/authz, regulatory, irreversible actions | all of §2, plus every category in `exception-catalog.md` |
| **P2** | core business flows, high-traffic paths | EP, BVA, decision table, state transition, exception catalog |
| **P3** | supporting or rare flows, cosmetic behaviour | EP (valid + primary invalid), happy path, primary negatives |

A P3 rating is a decision with consequences, so it is recorded and reviewable at G2 — not a silent
default an agent reaches for when a story looks boring.

---

## 2. The techniques

### 2.1 Equivalence Partitioning (EP)
**Mandatory for:** every input field, every level.

Split each input's domain into classes where every member is expected to be treated identically.
One representative per class. Classes come from the **basis**, not from intuition: a field's type,
its validation rules, and its business meaning each carve the domain differently.

- One case per **valid** class (there is often more than one — e.g. a discount code that is
  `percentage` or `fixed` are two valid classes, not one).
- One case per **invalid** class.
- Never merge two invalid classes into one case. `qty = -1` and `qty = "abc"` fail for different
  reasons and can mask each other: a handler that rejects everything non-positive would pass a
  combined case while silently accepting `"abc"` as `0`.

### 2.2 Boundary Value Analysis (BVA)
**Mandatory for:** every field with a range, a length, a count, a date window, or a precision limit.

Use the **4-value** form per boundary: `min−1, min, max, max+1`. (Add the nominal value when the
field's behaviour changes in the middle of the range, not as a matter of routine.)

Boundaries hide in places that do not look numeric:
- string **length** (empty, 1 char, max, max+1)
- collection **size** (0 items, 1 item, max items, max+1)
- **dates** (the day before the window opens, the first day, the last day, the day after — and the
  boundary *instant*: 23:59:59 vs 00:00:00, which is where time-zone defects live)
- **precision** (2 decimal places allowed → test 3)
- **pagination** (page 0, page 1, last page, last page + 1)

Every boundary you identify goes in the TCM's State & Boundary Analysis table. **That table is the
denominator for `boundary_coverage`** — which means an unidentified boundary does not merely go
untested, it silently inflates the coverage percentage. This is the single most common way a
specification-coverage number lies.

### 2.3 Decision Table
**Mandatory for:** any acceptance criterion combining **two or more conditions**.

1. List the conditions and their possible values.
2. Enumerate the full cartesian product of rules.
3. Mark rules that are **infeasible** (mutually exclusive in reality) and **record why** — an
   infeasible rule removed without a reason is indistinguishable from a rule someone found
   inconvenient.
4. Collapse rules that provably share an outcome *and* a code path. When in doubt, do not collapse.

The count of **feasible** rules is the denominator for `rule_coverage`.

```
Conditions          R1    R2    R3    R4
member?             Y     Y     N     N
cart >= 1000?       Y     N     Y     N
─────────────────────────────────────────
discount 20%        X
discount 10%              X
discount 5%                     X
discount 0%                           X
```

### 2.4 State Transition
**Mandatory for:** every entity with a status lifecycle.

Build the full N×N transition matrix from `test_basis.md`'s state model. Cover:
- every **valid** transition (0-switch coverage), and
- every **invalid** transition that a real actor could attempt.

Invalid transitions are where the defects are. "Cancel an already-shipped order", "pay an already-paid
invoice", "approve a withdrawn request" — these are rarely in the happy-path documentation and are
frequently unguarded in the code. The denominator for `transition_coverage` is
`valid + reachable-invalid` transitions, not just the valid ones.

### 2.5 Pairwise
**Mandatory for:** three or more independent multi-valued parameters where the full product exceeds
what the risk rating justifies.

Cover every **pair** of parameter values at least once. Record the generator or the reasoning — a
pairwise set nobody can reproduce is just an arbitrary subset. Pairwise is a reduction technique;
say what it reduced *from*, so a reviewer can judge the trade.

### 2.6 Error guessing / exception design
**Mandatory for:** every level, every story. Driven by `.claude/refs/exception-catalog.md`.

This is the technique most often skipped, and the one the human gates check hardest, because its
absence is invisible in a passing test run.

### 2.7 Use case / scenario
**Mandatory for:** every user journey (`level:ui` and end-to-end `level:api` flows).

Happy path, plus each **alternate** flow, plus each **exception** flow. A journey's exception flow
must be proven at the level the user actually observes it — a service-layer test proving the error
is raised does not prove the error reaches the screen.

### 2.8 CRUD × role matrix
**Mandatory for:** every entity under access control.

For each (operation, role) cell, one case for **allowed** and one for **denied**. The denied cases
matter more: an over-permissive endpoint is a security defect that no happy-path suite will find.
Include cross-tenant access explicitly — "user A reads user B's record" is a distinct case from
"anonymous user reads a record".

---

## 3. The Mandatory Counting Protocol

Non-negotiable. Run it **before** writing any case, and record it in `tcm.md`.

### Step 1 — count the surfaces

Count from `test_basis.md` (confirmed rows only) and `story_analysis.md`:

```
acceptance_criteria   = atomic AC in story_analysis.md
endpoints             = distinct endpoints this story touches
status_codes          = sum of documented status codes across those endpoints
                        (endpoint A has 3 + endpoint B has 4  =>  7, not 4)
request_fields        = sum of all request body/query/path fields across those endpoints
validation_rules      = total count of validation RULES, not fields
                        (a field with `required` + `maxLength` contributes 2)
error_codes           = distinct error codes the basis defines for this story
db_writes             = distinct write operations (INSERT/UPDATE/DELETE) the story performs
db_constraints        = DDL constraints those writes touch (UNIQUE, FK, NOT NULL, CHECK)
                        — count 0 for read-only stories: a SELECT triggers no DDL constraint
boundaries            = boundary values identified in the State & Boundary Analysis table
decision_rules        = feasible rules across all decision tables
transitions           = valid + reachable-invalid transitions across all state models
exceptions            = applicable rows from exception-catalog.md (after documented declines)
screens               = screens/components this story touches (UI only)
ui_states             = states summed across ALL screens
                        (Screen A has 4 + Screen B has 3 => 7 — sum, never max, never average)
ui_interactions       = distinct user actions (click, type, submit, navigate, upload…)
journeys              = distinct end-to-end user flows
journey_failures      = distinct user-observable failure outcomes per journey
```

### Step 2 — compute minimums

```
min_API   = status_codes + validation_rules + error_codes + boundaries + decision_rules
min_DB    = db_constraints + db_writes
min_UI    = ui_states + ui_interactions + journey_failures_visible_on_screen
min_E2E   = journeys + journey_failures
min_EXC   = exceptions
```

Every term is a **sum**. There is no multiplication anywhere. In particular: **never compute
`screens × states`** — `ui_states` is already summed across every screen. (The wrong formula
survives review distressingly often because on a two-screen story with four states each, `2 × 4`
and `4 + 4` both give 8. Check the terms, never the total.)

### Step 3 — write, then verify

After writing every case, count the actual IDs and compare:

```
IF actual < minimum for ANY category  → INCOMPLETE. Add cases. You may NOT proceed with a deficit.
IF actual >= minimum for ALL          → PASS. Record the Count Report in tcm.md.
IF actual > minimum                   → GOOD. Explain in one line what each extra covers.
```

Then compute the coverage ratios per `.claude/refs/coverage-model.md`. **Passing the count and
passing the ratios are two different checks** — the count proves you wrote enough cases, the ratios
prove they landed on the right things.

---

## 4. Choosing the level

A case belongs at the **lowest level that can actually prove it**. Pushing everything to UI is slow
and flaky; pushing everything to API misses what the user sees.

| The thing being proven | Level | Why not lower / higher |
|---|---|---|
| Field validation, format, range | `api` | The UI may also validate, but the API is the real boundary — a client can always bypass the form |
| Business rule / calculation | `api` | Deterministic, fast, no rendering |
| DDL constraint (UNIQUE, FK, NOT NULL, CHECK) | `api` + `db` | Only a real write proves the database enforces it |
| Persisted side effect | `db` | The API response often does not reveal what was written |
| Third-party failure handling | `integration` | Needs a stub that can return 500 / time out on demand — local only |
| Screen state, inline error, redirect, toast | `ui` | The only level where "the user can see it" is a real assertion |
| Complete user journey | `e2e` | Proves the parts connect, which no single-level test does |

**Rule of thumb:** if you find yourself writing more than two UI cases per acceptance criterion,
most of them belong at `api`. Justify each `ui` case in the TCM's Level Justification table, and
record every push-down in `## Spec non-compliance` — because pushing a case to a lower level is the
one move that reduces a minimum without reducing risk, and it must be visible rather than silent.

---

## 5. Anti-laziness rules

- **One case per validation RULE** — not "test the field".
- **One case per status code per endpoint** — not "test the endpoint".
- **One case per DDL constraint** the story's writes touch.
- **One case per boundary value** — the four values of a boundary are four cases, not one.
- **One case per feasible decision-table rule.**
- **One case per transition**, valid and invalid alike.
- **One case per UI state per screen** — not "test the screen".
- **One case per user-observable failure** at the level the user observes it.
- **Never merge two invalid classes into one case.**
- **Never write a case whose `Expected_Result` you cannot cite** to `test_basis.md` or an AC. If you
  cannot cite it, you do not know it — raise it as an open question instead of inventing it.
