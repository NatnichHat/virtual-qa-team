---
description: "Initialise docs/test_stack.md, docs/env_matrix.md, and docs/test_strategy.md — the three files every agent reads. Run this before /phase1 on any new project."
argument-hint: "[--refresh]"
---

# /init — stack initialisation

You are the orchestrator.

## Steps

1. **Check for `docs/test_stack.md`.** If it exists and `$ARGUMENTS` is not `--refresh`, say so and
   stop. If `--refresh`, proceed in refresh mode.
2. **Spawn `test-stack-init`** (`subagent_type: "test-stack-init"`) with the repo root and the mode.
   It will interrogate the human directly — it has `AskUserQuestion`.
3. **Verify** all three files were written and check for remaining `<TBD>` markers in the fields that
   block Phase 1: `start_local_cmd`, the environment base URLs, `defect_tracker`, and the coverage
   thresholds.
4. **Report:** the three paths, a one-line summary per section, every remaining `<TBD>` with what it
   blocks, and the next command — `/phase1 <REQ_ID>`.
