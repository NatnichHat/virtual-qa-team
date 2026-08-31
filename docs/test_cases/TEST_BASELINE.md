# Test Baseline — project-wide test inventory

> **1 project = 1 baseline.** The complete, standalone spec for every test case in the system across
> **all levels** (api / ui / db / integration) — not a summary, not an index. `automation-engineer`
> reads this as its main source; a human reviewer reads it side by side with the actual `.robot` file.
>
> This file exists so that "what tests do we have?" has exactly one answer. Without it, the answer
> lives scattered across per-story spec files and nobody can see regression impact at a glance.

## State — two-stage per action, pending then confirmed

| Action | Pending (set by `qa-analyst` when it merges the case) | Confirmed (set by `script-reviewer` on approval) |
|---|---|---|
| NEW | `planned` | `active` |
| MODIFY | `modify_pending_REQ[N]` | `modified_by_REQ[N]` |
| REMOVE | `remove_pending_REQ[N]` | `removed_by_REQ[N]` |

1. **`qa-analyst`** sets the *pending* state right after writing `design_notes.md`, before automation
   starts. For MODIFY it edits the existing entry's block **in place** to the new correct behaviour;
   for REMOVE it leaves the content as-is (historical record) and changes only the State.
2. **`script-reviewer`** flips pending → confirmed, and only after verifying the implementation
   actually matches: a REMOVE case confirmed *absent* from the suite, a NEW/MODIFY case confirmed
   present and matching. **Nothing else may flip a State.**
3. `make baseline-check` is a **read-only drift guard**. It re-checks that confirmed entries still
   match the suite and flags pending entries that have lingered. It never flips a State and never
   rewrites the authored prose.

**Append-only** means an entry is never physically deleted — a `removed_by_REQ[N]` entry stays
forever as a tombstone. It does **not** mean an entry's content is frozen: a MODIFY overwrites its
own Preconditions/Steps/Expected/Cleanup, because the whole point is that the behaviour changed.

## Approval

> **Round-level** human sign-off — not to be confused with the per-entry `State` field, which tracks
> each individual test case's own lifecycle. Only `/phase3`, `/approve-test-case`, `/phase4`, and
> `/approve-script` ever write these fields.

**Round:** —
**Round started:** —
**REQ in this round:** —
**Test case Approval:** —
**Test case Approved-by:** —
**Test case Approved-at:** —
**Script Approval:** —
**Script Approved-by:** —
**Script Approved-at:** —

`Test case Approval`: `—` (no round yet) | `pending_approval` | `approved` | `Canceled`
`Script Approval`: `—` (this round's `/phase4` hasn't run) | `pending_approval` | `approved`

## Summary index

| Feature | Test ID | Level | Scenario | US | Tags | State | Spec ref |
|---|---|---|---|---|---|---|---|
| _(none yet — fresh skeleton)_ | | | | | | | |

## Full detail

_(One block per automated test case, grouped under a `## <feature>` heading. Format is a 1:1 clone
of the scenario in `design_notes.md`, plus exactly two fields the baseline adds: `Spec ref` and
`State`. Same field names, same order — so a human who approved the design sees identical content
here. Example shape, delete once real entries exist:)_

```markdown
## orders

### E2E-REQ001-US001-001 — Create order happy path

| Spec ref | `docs/test_cases/REQ001_order_mgmt/US001/design_notes.md#E2E-REQ001-US001-001` |
| State | planned |

- **Level:** api
- **Target feature:** orders
- **Tags:** US001, smoke, feature:orders, level:api, env:local, env:sit, env:uat
- **Basis ref:** `test_basis.md#post-v1-orders`
- **Preconditions:** customer CUST-001 seeded by `make e2e-seed`; auth token available
- **Request:** `POST /v1/orders` body `{customerId, items}` per basis
- **Expected:** status 201, body matches `{id, customerId, items, status:"created"}` per basis;
  row exists in `orders` with `status='created'`
- **Cleanup:** `DELETE /v1/orders/{id}`
```

## Approval log

_(`/phase3` and `/approve-test-case` append `### Test case Revision N`; `/phase4` and
`/approve-script` append `### Script Revision N`. Each `N` counts up across the whole log per track,
never reset per round.)_
