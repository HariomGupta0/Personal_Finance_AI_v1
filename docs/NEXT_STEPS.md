# Next Steps & Roadmap Tracker

| Phase | Description | Priority | Status | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Project Audit & Baseline Setup | P0 | **COMPLETED** | Isolated `.venv`, `finance-ai-antigravity` DB, baseline tests pass, context docs created. |
| **Phase 1** | Dynamic Knowledge Graph Updates | P1 | **COMPLETED** | Parameterized CRUD for transactions/incomes/goals/loans, balance auto-update, NL extractor, 100% tests pass. |
| **Reorg** | Clean Modular Project Structure | - | **COMPLETED** | Modular `backend/app/`, `frontend/`, `docs/`, root entrypoints `run_cli.py` & `run_tests.py`. |
| **Phase 2** | Expanded Financial Reasoning | P2 | **NEXT UP** | Category-wise spending, trends, months of coverage, debt-to-income, obligation schedule. |
| **Phase 3** | Advanced Question Understanding | P3 | PENDING | Multi-entity extraction (amount, category, period, operation) with hybrid regex + LLM parsing. |
| **Phase 4** | Graph Data Model Improvement | P4 | PENDING | Extended schema (`Budget`, `Merchant`, `FinancialPeriod`), documented `GRAPH_SCHEMA.md`. |
| **Phase 5** | GraphRAG Engine | P5 | PENDING | Targeted subgraph extraction based on intent and entities without full DB retrieval. |
| **Phase 6** | Vector / Hybrid Semantic Retrieval | P6 | PENDING | Hybrid GraphRAG combining semantic vector embeddings with Cypher graph traversal. |
| **Phase 7** | Structured Evidence & Grounding | P7 | PENDING | Verifiable evidence payload linking facts, formulas, and recommendations for every query. |
| **Phase 8** | LLM Response & Explanation System | P8 | PENDING | Multi-tier response generator (Fact vs Calculation vs Recommendation) with strict currency rules. |
| **Phase 9** | FastAPI REST Backend | P9 | PENDING | Modular API endpoints for auth, transactions, finances, goals, and assistant queries. |
| **Phase 10** | React Frontend Dashboard | P10 | PENDING | Modern responsive UI with Recharts analytics, transaction management, and AI chat assistant. |
| **Phase 11** | Comprehensive Testing Suite | P11 | PENDING | Unit, integration, and end-to-end tests for all calculations, graph operations, and APIs. |
| **Phase 12** | Edge Case Resilience | P12 | PENDING | Zero balance, negative values, missing data, LLM outage fallbacks, invalid inputs handling. |
| **Phase 13** | Security & Data Isolation | P13 | PENDING | User data isolation, query parameterization, JWT auth, environment protection. |
| **Phase 14** | Production Logging & Monitoring | P14 | PENDING | Structured logging, sanitization of credentials/keys, audit trails. |
| **Phase 15** | Research & Evaluation Benchmark | P15 | PENDING | Academic benchmark comparing Conventional Vector RAG vs Proposed Dynamic GraphRAG. |
| **Phase 16** | Comprehensive Documentation | P16 | PENDING | Full documentation (`README.md`, `ARCHITECTURE.md`, `API_DOCUMENTATION.md`, `EVALUATION.md`). |
