BATCH A - low risk, run T1 to T5 in one go, commit each, no stops
T1 Env and docs: confirm the vision model ID in image_extractor.py exists by calling the Groq models list endpoint (print result); fix PROJECT_CONTEXT.md to match the code (models, grades A-D, no voice module); add .env.example, a pinned docker-compose.yml for Neo4j, and README run steps; make tests that need backend/tests/test-data skip when it is missing.
T2 Intent routing bug: "How long can I survive on my savings?" must route to EMERGENCY_RUNWAY_ANALYSIS, not SAVINGS_ANALYSIS. Add tests for 6 phrasings of each intent so nothing else regresses.
T3 OCR confirm-before-write: image/receipt extraction must only return a preview; nothing is written to Neo4j until the confirm endpoint is called with user-approved values. Add a sanity flag when extracted amount, date or merchant is missing or the amount looks implausible. Tests with a mocked extractor.
T4 Auth hardening: password hashing check, login rate limiting, demo password only when a DEV flag is set, secrets only from env. Tests.
T5 Redaction before external API calls: mask account IDs, UPI IDs and card-like numbers in anything sent to the LLM or vision API; unit tests.

BATCH B - touches formulas or the database: STOP after each task and wait for "next"
T6 Formulas (config-driven): move thresholds (3x reserve, DTI bands, health weights and grade cutoffs) to engine_config with defaults EQUAL to current behavior so golden tests stay green. Add an optional trailing-N-month average expense basis and an optional fixed-obligations input to purchase safety, both off by default. Fix any evidence text that claims an average when the engine uses one month. Add a sensitivity script for the health score weights.
T7 Schema consistency: write scripts/check_graph_consistency.py (read-only) reporting duplicated or conflicting data (Transaction.category property vs BELONGS_TO edge, Income nodes vs INCOME transactions, balance_paise vs sum of transactions). Fix only real inconsistencies found, additively. Tests.
T8 Graph enrichment: additive migration (backup, dry-run default) adding Merchant nodes (Transaction-[:AT]->Merchant using the existing normalizer), EMI-[:PAID_BY]->Transaction where a matching debit exists, and MonthlySnapshot nodes. New intent SPENDING_CHANGE_EXPLANATION: multi-hop query category -> merchant -> transactions across two months, a deterministic engine function ranking top contributors, evidence payload, verifier support. Tests and golden fixtures for it.
T9 Baseline comparison: add retrieval_mode (llm_only, full_graph_dump, targeted_graphrag) and a script that runs the existing 150-case benchmark with --limit and --sleep, resumable, reporting per mode: numeric correctness against engine ground truth, unsupported-number rate from the verifier (no LLM judge), tokens, latency, LLM_ERROR count, N. Run with a small limit first.

BATCH C - cleanup
T10 CI: pytest markers separating DB tests from unit tests, a GitHub Actions workflow running the unit tests, pinned requirements.
T11 Final README: architecture, how to run, results section containing only numbers produced by scripts in this repo, known limitations.
