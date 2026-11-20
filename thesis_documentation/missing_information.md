# Audit of Project Evidence, Assumptions & Identified Information Gaps

## 1. Executive Status of Technical Evidence

In accordance with strict academic engineering standards, this document explicitly records the verified empirical evidence, distinguishes implemented features from proposed extensions, and catalogs areas where experimental data must be qualified or gathered.

---

## 2. Verified Implemented Features & Empirical Evidence

The following subsystems and capabilities were directly verified through repository inspection, source code execution, and test suites:

| Subsystem / Capability | Verification Method | Source File(s) / Evidence Artifact | Empirical Status |
| :--- | :--- | :--- | :--- |
| **Deterministic Financial Arithmetic** | Unit Tests (`test_financial_engine.py`, `test_historical_runway.py`) | `backend/app/engine/financial_engine.py`, `historical_runway.py` | **100% Verified** (84/84 unit tests passing, zero floating-point errors). |
| **Internal Transfer Disambiguation** | Live Neo4j Integration + Unit Tests | `backend/app/services/transfer_detector.py`, `test_internal_transfers.py` | **100% Verified** (16/16 unit tests passing; $\pm 2$ day window, 1-to-1 matching). |
| **Idempotent Ingestion & Deduplication** | Test suite + Neo4j Uniqueness Constraints | `backend/app/services/fingerprint.py`, `import_pipeline.py` | **100% Verified** (SHA-256 fingerprint on `Transaction.fingerprint`). |
| **Two-Tier Explanation Verifier** | Automated Benchmark Suite | `backend/app/services/verifier.py`, `evaluation_report.json` | **100% Verified** (24/24 benchmark tests passed across 6 dimensions). |
| **Multimodal Vision OCR** | Test Client + Groq Vision API | `backend/app/services/image_extractor.py`, `test_ocr_confirm_flow.py` | **100% Verified** (`qwen/qwen3.8-27b` zero-shot parsing with user review). |
| **Targeted Cypher GraphRAG** | Cypher Query Inspection + Benchmark | `backend/app/rag/graph_rag.py`, `benchmark_results.json` | **100% Verified** (Average graph retrieval latency: 11.8 ms). |
| **Session Authentication & Rate Limiting**| Auth Hardening Unit Tests | `backend/app/api/auth.py`, `test_auth_hardening.py` | **100% Verified** (Signed cookies, PBKDF2 salting, slowapi throttling). |
| **Live Database Connectivity** | Live Bolt Handshake | `neo4j://127.0.0.1:7687`, database `finance-ai-antigravity` | **100% Verified** (Health check: ONLINE, 30 seed nodes active). |

---

## 3. Partially Implemented vs. Proposed Future Features

To avoid academic misrepresentation, the thesis must maintain a rigorous distinction between fully implemented features, architectural stubs, and proposed future work:

### 3.1 Fully Implemented & Tested
1. Intent-scoped Knowledge Graph construction in Neo4j with 10 node labels and 9 relationship types.
2. Pure integer-paise financial engine calculating Savings Rate, Emergency Runway, DTI Ratio, Purchase Affordability, and Comprehensive Financial Health (0–100).
3. Rule-based NLU question parser with follow-up conversational context memory and date-ambiguity detection.
4. Groq Vision OCR for receipts and UPI payment confirmations.
5. Automated post-generation verifier with retry feedback and deterministic 4-section fallback.
6. Full-stack React + FastAPI application with live KPI updates, dark-mode dashboard, and chat interface.

### 3.2 Implemented in Schema / Stubs (Partially Integrated)
1. **`Budget` Node Entity:** The Neo4j graph schema defines `(:Budget {id, category, monthly_limit, period})` and the relationship `(:User)-[:HAS_BUDGET]->(:Budget)`. However, automated dynamic monthly budget breach notifications are currently presented via category expense proportions rather than an active notification daemon.
2. **LLM Question Parser Fallback:** `parse_question_llm` exists in `question_parser.py` as a secondary fallback when rule matching fails; in production benchmarks, rule-based parsing handles 100% of standard benchmark intents.

### 3.3 Proposed Future Scope (Unimplemented in Source Code)
1. **Live Open Banking / Account Aggregator (AA) Integration:** The application currently relies on file-based CSV bank statement imports and receipt image uploads. Real-time bank sync via India's Account Aggregator framework (e.g. Sahamati / Setu / Anumati APIs) is proposed future scope.
2. **Real-Time Investment Portfolio Valuation:** Stocks, mutual funds, and crypto portfolios are currently represented as static liquid/restricted balances; automated live price feed integration (e.g. NSE/BSE ticker feeds) is future work.
3. **Multilingual Speech & Natural Language:** The current system operates in English with Indian banking domain vernacular (UPI, NEFT, IMPS, FASTag, Lakh, Crore). Regional language support (Hindi, Tamil, Marathi, etc.) is proposed.
4. **Mobile Native Application:** The system provides a responsive React web dashboard; native Android/iOS packaging via React Native is a future milestone.

---

## 4. Identified Experimental Data Gaps & Academic Qualifications

1. **Human Subjective Usability Study (SUS Score):**
   - *Status:* Automated benchmarks across 24 quantitative test cases and 10 representative user queries have verified 100% mathematical and status accuracy. However, a formal human usability study (System Usability Scale across 30–50 human test participants) has not yet been conducted.
   - *Academic Recommendation:* In Chapter 7, document the 24 automated benchmark results thoroughly, and include a standardized 10-item System Usability Scale (SUS) questionnaire template as proposed methodology for future human evaluation.
2. **Longitudinal Real-World Ledger Tracking:**
   - *Status:* Testing was performed on comprehensive multi-month synthetic and seed datasets (e.g. user `Rahul` with 3–6 months of transactions, accounts, and loans). Multi-year longitudinal behavioral studies are beyond the academic time window.
   - *Academic Recommendation:* Explicitly describe the evaluation dataset as an expert-crafted representative benchmark covering balanced, affluent, overdraft, and zero-expense financial archetypes.

