# Agent Rules

- One task per run, on its own commit(s). Touch only files in the task's scope. Never edit existing test expectations, golden files, or fixtures.
- If the task conflicts with an existing test or is ambiguous, STOP and ask ONE question. Do not invent a design.
- Never retype or summarize outputs. Run scripts/verify_task.ps1 and report only its output file path and the last 30 lines of it.
- "Deviations: NONE" must be backed by git diff --stat showing only in-scope files. List every behavior change, even small.
- Before every commit run git status. Never commit personal or generated files (statements, images, reports, node_modules, .env).
- Anything touching Neo4j data: backup first, additive only (keep old properties), dry-run by default, idempotent, never delete.
- No live LLM calls in tests. Measurements that call the LLM must sleep between calls, record the model name the API returned, and count LLM errors separately from verification failures. Never claim a number you did not measure.
