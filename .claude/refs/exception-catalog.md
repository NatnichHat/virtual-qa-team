# Shared ref — exception catalog

The mandatory checklist of failure modes. Every story answers **every applicable row**: covered, or
declined with a recorded reason (see `coverage-model.md` §5). Silence is not a decline.

Exception coverage is the dimension most often quietly skipped, because its absence is invisible in a
green test run — a suite with no exception cases passes just as convincingly as one with fifty.
That is exactly why it gets a checklist rather than a judgement call.

The applicable rows for a story form the denominator for `exception_coverage`.

---

## A. Input exceptions
Applicable whenever the story accepts input. Test at `api` level — the UI may also validate, but a
client can always bypass a form.

| # | Scenario | Applicable when | Typical expectation |
|---|---|---|---|
| A1 | `null` / field absent | field is optional-looking but required | 400 + field-level error |
| A2 | empty string `""` | any string field | 400, distinct from `null` — many handlers treat them differently |
| A3 | whitespace only `"   "` | any string field | 400 — trimming is a decision the basis must state |
| A4 | over max length | any bounded string | 400; also test max exactly (BVA) |
| A5 | wrong type (`"abc"` for a number, array for object) | any typed field | 400, not 500 |
| A6 | wrong format (malformed email / date / UUID) | any formatted field | 400 with the specific error code |
| A7 | number out of range (negative, zero, huge) | any numeric field | 400; pairs with BVA |
| A8 | precision overflow (3 decimals where 2 allowed) | money, measurements | 400 or documented rounding — never silent truncation |
| A9 | unicode, emoji, RTL, combining marks | any user-facing text | stored and returned intact |
| A10 | **Thai text specifics** — stacked vowels/tone marks, no word boundaries | any Thai-facing text field | length counted correctly, no mojibake, sort/search behave |
| A11 | injection payloads (`' OR 1=1`, `<script>`, `${jndi:}`, `../`) | any field reaching a query, template, or path | rejected or safely escaped; never executed |
| A12 | leading zeros, `+`/`-` prefixes, thousands separators | numeric-as-string fields | documented handling |
| A13 | oversized payload (huge array, large body) | list/upload endpoints | 413 or documented limit, not a hang |
| A14 | duplicate keys / conflicting fields in one request | structured payloads | documented precedence, not undefined behaviour |

## B. Authentication & authorisation
Applicable to every protected endpoint and screen. The denial cases matter more than the permit
cases — an over-permissive endpoint is a security defect no happy-path suite will ever find.

| # | Scenario | Typical expectation |
|---|---|---|
| B1 | no token / no session | 401 |
| B2 | expired token | 401, distinct from B1 |
| B3 | malformed or wrong-signature token | 401 — never 500 |
| B4 | valid token, insufficient role | 403, distinct from 401 |
| B5 | **cross-tenant / cross-user access** — user A requests user B's resource | 403 or 404 per the basis; never the other user's data |
| B6 | token valid for a different audience/scope | 401 or 403 per the basis |
| B7 | session expiry mid-journey (UI) | redirect to login, no partial write, no silent data loss |

## C. State exceptions
Applicable to any entity with a lifecycle. This is where undocumented, unguarded behaviour lives.

| # | Scenario | Typical expectation |
|---|---|---|
| C1 | operate on a deleted / cancelled entity | 404 or 409 per the basis |
| C2 | duplicate submit (same request twice) | idempotent, or 409 — never two records |
| C3 | invalid state transition (cancel a shipped order) | 409 with a specific code |
| C4 | concurrent update (two writers, same record) | last-write-wins, optimistic lock, or 409 — the basis must say which |
| C5 | out-of-order operations (confirm before create) | 409 / 404 |
| C6 | operation on an entity owned by someone else | see B5 |
| C7 | replay of a stale request (old version/etag) | 409 or 412 |

## D. Dependency exceptions
Applicable when the story calls a third party or another service. **Requires WireMock — local only**
(see `docs/env_matrix.md`). These cases carry `env:local` in `Env_Scope`.

| # | Scenario | Typical expectation |
|---|---|---|
| D1 | dependency returns 500 | SUT returns its own documented error, not a leaked upstream body |
| D2 | dependency times out | documented timeout behaviour, bounded wait — not a hang |
| D3 | dependency returns malformed / unexpected payload | handled, not a 500 |
| D4 | dependency returns 4xx (rejected, not found) | mapped to a documented SUT error |
| D5 | dependency slow but successful (within timeout) | request succeeds; no premature failure |
| D6 | dependency unavailable (connection refused) | documented behaviour; retry/circuit policy if the basis states one |
| D7 | partial failure — one of several calls fails | documented rollback or compensation; no half-written state |

## E. Data & constraint exceptions
Applicable when the story **writes**. Provable only at `api` + `db` level — never through the UI.

| # | Scenario | Typical expectation |
|---|---|---|
| E1 | UNIQUE violation (duplicate key) | 409 with a specific code, not 500 |
| E2 | FOREIGN KEY violation (reference does not exist) | 400/404 per the basis |
| E3 | NOT NULL violation via a path that skips app validation | 400; and the fact it is reachable is itself a finding |
| E4 | CHECK constraint violation | 400 with the field named |
| E5 | referenced row deleted between read and write | 409 or documented behaviour |
| E6 | cascade behaviour on delete (RESTRICT / CASCADE) | matches the basis; verified in the database, not inferred from the response |

## F. Business exceptions
Applicable per the story's domain. `test-basis-analyst` and `story-analyst` name these — they are
the rows this catalog cannot enumerate generically.

| # | Scenario (examples — replace with the story's real ones) | Typical expectation |
|---|---|---|
| F1 | limit / quota exceeded | documented error code |
| F2 | insufficient balance / stock | documented error code |
| F3 | outside a permitted window (business hours, promotion period) | documented error code |
| F4 | entity in a blocked/suspended condition | documented error code |

## G. UI-observable exceptions
Applicable to `level:ui` stories. Lower levels prove the error is *raised*; only this level proves
the user can *see* it.

| # | Scenario | Typical expectation |
|---|---|---|
| G1 | server returns 4xx during a journey | user-visible message, form state preserved, no data loss |
| G2 | server returns 5xx during a journey | user-visible message; no blank screen, no silent swallow |
| G3 | slow response | loading state visible; controls disabled against double-submit |
| G4 | empty result set | empty state, not a broken layout or a spinner forever |
| G5 | validation error | inline, next to the field, in the user's language |
| G6 | double-click submit | one request, or one record — pairs with C2 |
| G7 | navigate away mid-operation | documented behaviour; no orphaned record |

---

## Recording decisions

In `tcm.md`:

```markdown
## Exception coverage

| # | Scenario | Applicable | Covered by | Declined — reason |
|---|---|---|---|---|
| A1 | null / absent | yes | TC-REQ001-US001-021 | |
| A10 | Thai stacked vowels | yes | TC-REQ001-US001-034 | |
| D1 | dependency 500 | yes | TC-REQ001-US001-047 (env:local) | |
| D7 | partial failure | no | — | story calls exactly one dependency — `test_basis.md#integrations` |
| E1 | UNIQUE violation | yes | | **deferred** → docs/test_debt.md #4 (counts against coverage) |
```

**Declined** leaves the denominator — the scenario genuinely cannot occur.
**Deferred** stays in the denominator and lowers the score, requires a reviewer's approval, and gets
a row in `docs/test_debt.md`. Keeping those two distinct is what stops "not applicable" from becoming
the universal solvent for inconvenient coverage.
