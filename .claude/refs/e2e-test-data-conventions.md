# Shared ref — E2E test-data YAML conventions

Authoritative shape for `test_data/e2e_baseline.yaml` — split out of
`.claude/refs/e2e-api-conventions.md` (which used to own this in its old §3) so that a shared
**core convention** can stay stable while each verification **surface** (API, UI, database, bucket)
grows its own section without turning that file's data-section into an ever-branchier mess. Same
status as its sibling: a shared reference doc, read directly by both **automation-engineer**
(authors and revises `test_data/e2e_baseline.yaml`) and **script-reviewer** (checks that YAML
against this shape firsthand, before G5), via `Read`, not a `.claude/skills/` entry.

Read `.claude/refs/e2e-api-conventions.md` alongside this file: §4 (keyword-per-endpoint pattern)
and §5 (the two generic assertion keywords) define how a keyword *consumes* the data this file
shapes; §8 (reading cascade) is unchanged.

## 1. Core convention (applies to every surface)

These rules hold regardless of whether a scenario is API-only, UI/Browser, or reaches into a
database or object-storage bucket.

- **Dict key = the exact test case name.** One top-level key per test case in
  `test_data/e2e_baseline.yaml`, matched by the `Prepare Test Data` keyword's `${${TEST_NAME}}`
  lookup (mechanism unchanged — still defined in `e2e-api-conventions.md` §3 /
  `docs/test_stack.md`'s `e2e_test_data_prep`). A missing key fails that test with a
  variable-not-found error, never a silent skip.
- **`input_data` only when there's something to feed in; `expected_data` only when there's
  something to verify.** `input_data` holds whatever a keyword needs to build its call — form
  fields, headers, request body. `expected_data` holds whatever must be asserted afterward — a
  static UI label, a response body, a database row, a bucket object. A test case that needs no
  caller-supplied input (e.g. a parameterless GET) simply omits `input_data`; one with nothing left
  to check beyond a keyword's own default behavior omits `expected_data`.
- **Always nest `{core_feature}.{sub_feature}` — no flat-shape exception.** Every `input_data` and
  every `expected_data` block nests two levels deep before any payload keys, even for a
  single-endpoint scenario with nothing else going on. This is a deliberate, uniform rule (not
  "nest only when chained/complex") so every keyword's data-access path has exactly the same shape,
  regardless of how simple or elaborate the scenario behind it is:
  - `core_feature` — the project's ratified feature name, identical to the `FEATURES.md` entry and
    the `feature:<name>` tag (e.g. `orders`).
  - `sub_feature` — the specific keyword/endpoint/interaction within that feature (e.g.
    `create_order`). Often, but not necessarily, the same name as the per-endpoint keyword.
- **`Verify Deep Response Matches Expected` (see `e2e-api-conventions.md` §5) is the default way to
  check a dict/multi-field value against static, locked-in-YAML values.** Use it whenever a
  surface's block holds more than a field or two of fixed, predictable data.
- **Sentinel vocabulary** — for fields that cannot be pinned to a static value:
  - `${NONE}` / `__ANY__` — "don't care about this value at all"; the field is skipped entirely.
  - `__Verify Not Empty__` — the field MUST be present and non-empty, but its exact value cannot be
    predicted (a generated UUID, a `created_at` timestamp) and there is genuinely no way to derive
    it. This is a **stricter** check than `__ANY__` — the key must exist and hold a non-empty
    value, not merely "any value or none."
  - **If a field's value CAN be derived** (a deterministic hash, a computed formula, a value known
    from a prior step) — do not reach for a sentinel. The specific keyword adds an explicit extra
    verification step beyond the generic deep-diff call, checking the derived value directly.

## 2. api_convention — API surface (RequestsLibrary), plus the open surface layer

Adds one more nesting level, but **only under `expected_data`**: `{core_feature}.{sub_feature}.
{surface}`. A single keyword call hitting one endpoint can produce side effects that must be
verified across more than one surface at once — the API response, a database row that call wrote,
an object it uploaded to a bucket — so `expected_data` needs a place for each. `input_data` never
gets a surface key: you only ever feed input into the one call being made, regardless of how many
surfaces its result touches.

**`surface` is an open name, not a fixed enum.** `api` is the one surface with a defined, reusable
mechanism (below — it always goes through the two `e2e_assertion_helper` keywords). Beyond that,
`automation-engineer` names whatever surface a scenario actually needs — `database`, `bucket`, or
anything else — and designs the verification for it itself (see "Database/bucket — examples, not a
contract," below). The only thing this convention fixes is *where in the YAML* that verification's
data lives, never *how* it's checked.

```yaml
E2E-REQ012-US045-001 Create Order Happy Path:
  input_data:
    orders:                       # core_feature
      create_order:               # sub_feature
        body:
          customer_id: CUST-1
          items:
            - sku: SKU-1
              qty: 2
  expected_data:
    orders:
      create_order:
        api:                      # surface: the endpoint's own response
          http_status: 201
          response:
            id: __Verify Not Empty__
            customerId: CUST-1
            items:
              - sku: SKU-1
                qty: 2
            status: created
        database:                 # surface: a row this same call wrote
          orders_db:
            orders:
              table: public.orders
              value:
                customer_id: CUST-1
                status: created
                created_at: __Verify Not Empty__
```

### Seed vs. verify — these are not the same thing

Seed-script-loaded data (per `e2e-api-conventions.md` §6) is a **prerequisite** — it is loaded
before the suite runs and is never itself an assertion target. The `database`/`bucket` blocks in
this section exist for the **opposite**
case: a step in the test case's own flow — the keyword call under test — writes, updates, or
deletes a database row or a bucket object, and *that resulting state change* is a first-class thing
the test must verify, exactly as it verifies an API response. A scenario whose action has such a
side effect but carries no matching `database`/`bucket` block is an **incomplete spec**, not an
optional extra — the same way a scenario that never checks the response body would be.

### Database/bucket — examples, not a contract

The two blocks below show what a `database` and a `bucket` surface *might* look like for a
scenario that needs one. They are **illustrations of the nesting pattern, not a fixed schema** —
automation-engineer is free to add, drop, or rename fields to fit what a given scenario actually
needs to pin down, as long as the block still sits at `expected_data.{core_feature}.{sub_feature}.{surface}`.

```yaml
database:                         # one possible shape — adapt freely
  <db_name>:
    <table_logical_name>:
      table: <fully-qualified table name, e.g. public.orders>
      value:
        <column>: <expected value, or __Verify Not Empty__ for non-deterministic columns>

bucket:                           # another possible shape — adapt freely
  <target_source_name>:
    target_source: <target_source_name>
    similarity_threshold: 90      # e.g. a value a bespoke comparison check reads, not a diffable field
```

**No fixed keyword exists for `database`/`bucket`/any other non-`api` surface, and none should be
invented preemptively.** `automation-engineer` designs and writes whatever verification the
scenario's action actually needs, inside the per-endpoint keyword (or a small helper it calls),
the same way it would design any other piece of test logic: a plain structural check reuses
`Verify Deep Response Matches Expected` (`e2e-api-conventions.md` §5) directly, exactly like the
`api` surface does; something that isn't a plain field-equality check (e.g. a similarity-threshold
comparison, a time-window check) is bespoke logic it writes for that keyword — it is not forced
through the generic deep-diff keyword just because a structural check happens to be the default
for `api`. Either way, verification stays entirely inside the keyword; a test case never queries
a DB or bucket directly.

### Deferral note — connection wiring is a separate task, writing the check is not

What's out of scope, and deliberately deferred, is the underlying **connection**: which Robot DB
library, which connection-string convention, which object-storage client, and how each gets wired
into `start-local`/`compose.yml`. This mirrors the exact precedent already set for WireMock
(`e2e-api-conventions.md` §7 / `test_stack.md`'s `e2e_external_mock`): "no compose stack exists yet
for this — this section documents the convention for whenever it does." Neither database nor bucket
access is wired into this project's stack today (`docs/test_stack.md` has no object-storage field
at all, and the DB connection details live in `environment.yaml`'s `database` block, still TBD per
`docs/env_matrix.md`). If a scenario needs a surface whose connection genuinely isn't wired yet,
`automation-engineer` reports that as a blocker rather than inventing credentials or containers —
but this is narrowly about the *connection*, never an excuse to skip *designing* the verification
logic itself, which is ordinary scenario-specific work it always does.

## 3. ui_convention — Browser surface (STUB)

No UI/Browser-surfaced story exists in this project yet, even though `Browser` library and
`page/<feature>/` folders are already wired per `docs/test_stack.md`. `ui` is the anticipated name
for that surface (e.g. static label text, an element's visible state, verified via
`page/<feature>/` keywords) under `expected_data.{core_feature}.{sub_feature}.ui` — but same as
`database`/`bucket` in §2, it's just a name automation-engineer would pick, not a reserved slot
with a fixed shape. The full shape is deliberately **not** designed yet, to avoid speculative design for a track
this project doesn't have; fill this section in when the first UI-surfaced REQ actually lands.
