# Environment Matrix

> Which environment can do what. `test-stack-init` drafts it at `/init`; a human owns it.
> **The G6 gate reads this file.** A test case whose `Env_Scope` includes an environment that
> cannot support its capability is a finding, caught before anything runs.

## The single mechanism that makes one script run everywhere

No keyword, page object, or test case file ever changes between environments. Three things do the work:

1. `tests/e2e/config/environment.yaml` — non-secret config per environment (tracked in git)
2. `tests/e2e/config/auth/.env.<env>` — secrets per environment (**gitignored**)
3. `${ENV}` — one Robot variable, default `local`, selected with `make e2e-run ENV=sit`

Every request goes through a **session alias** (`POST On Session  <alias>  ...`) created once by
`Prepare Session API`, which loops `${Environment}[${ENV}][api_config]`. The alias resolves to a
different URL per environment; the keyword never sees a URL. **A raw URL anywhere in a keyword is a
gate failure** — it is the one thing that would break portability.

## Capability matrix

| Capability | local | sit | uat | Notes |
|---|---|---|---|---|
| SUT reachable | <TBD> | <TBD> | <TBD> | we do not own the SUT — see "How local works" below |
| Bring stack up / tear down | <TBD> | **no** | **no** | sit/uat are persistently deployed by someone else's CD |
| WireMock (third-party stubs) | yes | **no** | **no** | container exists only locally; sit/uat call the real third party |
| Direct DB access (verification) | <TBD> | <TBD> | <TBD> | needed by `level:db` cases |
| Seed / cleanup data | yes | <TBD> | <TBD> | via `make e2e-seed ENV=<env>` |
| Destructive test cases | <TBD> | **no** | **no** | `destructive`-tagged cases are blocked on shared envs |
| Full regression run | yes | <TBD> | smoke only | uat is usually a smoke target, not a full-suite target |

Fill every `<TBD>` before the first `/phase5`. A `<TBD>` here means the G6 gate cannot decide
whether a run is safe.

## How "local" works when we do not own the SUT

This is the decision `/init` must force, because the skeleton this project descends from assumed the
pipeline owned and composed the system under test. Pick one and record it:

- **(a) Point at a shared dev deployment.** `local` is just another remote target with a different
  URL. Then `start_local_cmd` is `none`, WireMock is unavailable everywhere, and `destructive` cases
  have nowhere safe to run — say so explicitly.
- **(b) The SUT team gives us a compose file.** `local` genuinely stands the stack up, WireMock works,
  destructive cases are safe. Record the exact command in `test_stack.md` → `start_local_cmd`.
- **(c) Hybrid.** Some services local, some remote. Then the `api_config` alias list differs per
  environment — document which alias points where.

## Per-environment detail

### local
- **Base URLs:** <TBD>
- **Credentials:** `tests/e2e/config/auth/.env.local`
- **Data policy:** free to create/mutate/delete
- **Third parties:** WireMock stubs under `tests/e2e/config/wiremock/mappings/`

### sit
- **Base URLs:** <TBD>
- **Credentials:** `tests/e2e/config/auth/.env.sit`
- **Data policy:** <TBD — may we write? who else uses it? cleanup obligation?>
- **Third parties:** real. Assertions target only the SUT's own response/DB state, never a mock's
  request log — which is why the same script works here unmodified.
- **Cleanup:** `make e2e-seed-down ENV=sit` after a manual session. There is no stack to tear down.

### uat
- **Base URLs:** <TBD>
- **Credentials:** `tests/e2e/config/auth/.env.uat`
- **Data policy:** <TBD — usually read-mostly; treat as production-adjacent>
- **Third parties:** real, and possibly billable/rate-limited — note any test that would cost money
- **Cleanup:** `make e2e-seed-down ENV=uat`

## Secrets

`tests/e2e/config/auth/.env.<env>` is gitignored. Commit `tests/e2e/config/auth/.env.example` with
every key present and every value blank, so a new machine knows what to fill in. A credential
inlined in `environment.yaml` is a gate failure, caught at script review (G5).
