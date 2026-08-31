# Feature catalog

Automation is organised **by feature/capability**, never by the story or requirement that introduced
it — but the *shape* of that organisation differs by artifact:

- **`keyword/<feature>/` and `page/<feature>/`** are physically per feature, exactly **one level deep**.
- **`test_suites/e2e_baseline.robot` and `test_data/e2e_baseline.yaml`** are **single project-wide
  files**. There, feature identity is a `feature:<name>` **tag**, not a folder.

This catalog is the single list of valid feature names, used both ways.

## Rules

- **One level deep**, so `config/import.resource`'s relative `Resource` lines stay simple.
- **`common` is reserved and never listed here** — cross-cutting keywords (shared assertions,
  `Prepare Test Data`, `Prepare Session API`) live in `keyword/common/` and `page/common/`.
- **The two shared files are edited surgically.** Every story writes into the same
  `test_suites/e2e_baseline.robot` and `test_data/e2e_baseline.yaml` — always re-read immediately
  before editing, never regenerate or wholesale-overwrite.
- **Traceability lives in tags, not paths.** Every case carries its `E2E-*` ID, `US[ID]`,
  `feature:<name>`, `level:<level>`, and `env:<env>` tags. The runner is path-agnostic: point it at
  `tests/e2e/` and select with `--include`.
- **Keep it coarse — roughly 6 to 10 features.** A catalog with thirty entries is a folder structure
  pretending to be a taxonomy. `impact-analyst` maps each REQ onto this list and may *propose*
  additions; **adding a feature is a deliberate, human-ratified edit to this file.** Nobody invents
  ad-hoc folders or tag values.

## Features

_(None yet — fresh skeleton. Add a row per feature as coverage grows.)_

| Feature | Scope (what capability it covers) |
|---|---|
| _e.g._ `auth` | _login, logout, session expiry, unauthorized access_ |
| _(add real rows here)_ | |
