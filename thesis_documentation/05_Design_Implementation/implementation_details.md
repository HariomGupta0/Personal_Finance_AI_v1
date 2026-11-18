# Chapter 5 — System Design & Implementation Details

## 5.1 Architectural Tier Implementation

The system is organized into decoupled layers, ensuring strict separation of concerns, testability, and deterministic auditability.

```
+-----------------------------------------------------------------------------------+
|                        FASTAPI APPLICATION ENTRYPOINT (main.py)                   |
|   Routers: /api/auth, /api/finance, /api/transactions, /api/assistant, /api/import|
+-----------------------------------------+-----------------------------------------+
                                          |
        +---------------------------------+---------------------------------+
        |                                                                   |
        v                                                                   v
+-----------------------------------+             +---------------------------------+
|   INGESTION & STATEMENT ROUTER    |             |   CONVERSATIONAL ASSISTANT ROUTER|
|   (import_api.py)                 |             |   (assistant.py)                |
+-----------------+-----------------+             +----------------+----------------+
                  |                                                |
                  v                                                v
+-----------------------------------+             +---------------------------------+
|   MULTIMODAL INGESTION PIPELINE   |             |   NLU QUESTION PARSER           |
|   • csv_parser.py                 |             |   • question_parser.py          |
|   • image_extractor.py            |             |   • query_plan.py               |
|   • merchant_normalizer.py        |             +----------------+----------------+
|   • fingerprint.py                |                              |
|   • transfer_detector.py          |                              v
+-----------------+-----------------+             +---------------------------------+
                  |                               |   TARGETED GRAPHRAG RETRIEVAL   |
                  |                               |   (backend/app/rag/graph_rag.py)|
                  |                               +----------------+----------------+
                  |                                                |
                  +-----------------------+------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        NEO4J SERVICE (neo4j_service.py)                           |
|   Bolt Driver | Database: finance-ai-antigravity | Cypher Mutations & Queries     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               DETERMINISTIC FINANCIAL REASONING ENGINE                            |
|   • financial_engine.py: Savings, Runway, DTI, Purchase Safety, Health Score      |
|   • historical_runway.py: 4-State Lifecycle, MTD Interval Anchoring, Gating       |
|   • money.py: Integer-paise single source of truth                                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               LLM ORCHESTRATION & HALLUCINATION VERIFIER                          |
|   • prompt_builder.py: Versioned Prompt Registry (v1.1 Executive Cards)           |
|   • llm_service.py: Async Groq Client (openai/gpt-oss-120b)                      |
|   • verifier.py: Two-Tier Factual & Metric Auditor                                |
|   • response_generator.py: Deterministic Fallback Synthesis                       |
+-----------------------------------------------------------------------------------+
```

---

## 5.2 Detailed Module Engineering & Source Code Analysis

### 5.2.1 NLU Question Parsing (`backend/app/nlu/question_parser.py`)
* **Role:** Transforms arbitrary user queries into structured semantic query plans.
* **Architecture:** Hybrid rule-based AST parser with secondary LLM fallback:
  - **Deterministic Fast Path ([`parse_question_rules`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\nlu\question_parser.py#L561)):** Employs regular expression syntax trees to detect intents (`PURCHASE_SAFETY`, `SAVINGS_ANALYSIS`, `EMERGENCY_RUNWAY_ANALYSIS`, `DEBT_ANALYSIS`, `EXPENSE_BREAKDOWN`, `FINANCIAL_HEALTH`, `FINANCIAL_SUMMARY`).
  - **Conversational Memory:** Preserves multi-turn state (`prev_intent`, `prev_amount`, `prev_category`). When a user asks *"Can I buy a phone?"* followed by *"What about for ₹20,000?"*, the parser resolves the follow-up without losing the purchase intent.
  - **Date Ambiguity Resolution:** Checks whether a date reference (e.g. *"in October"*) is unambiguous or requires user clarification.
  - **Secondary LLM Fallback ([`parse_question_llm`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\nlu\question_parser.py#L1075)):** Invoked only when rule matching fails; generates strict JSON conforming to the intent schema.

### 5.2.2 Targeted GraphRAG Pipeline (`backend/app/rag/graph_rag.py`)
* **Role:** Eliminates monolithic database token dumps by executing intent-scoped Cypher queries.
* **Mechanism:**
  - For `PURCHASE_SAFETY`: Retrieves only active liquid accounts, pending loan EMIs, and emergency reserve goal targets.
  - For `SAVINGS_ANALYSIS`: Retrieves verified income nodes and non-transfer expense transaction nodes for the target month.
  - For `DEBT_ANALYSIS`: Retrieves contractual loans and deduplicates pending EMIs.
* **Execution Flow:** The retrieved subgraph is passed directly into the deterministic financial engine to calculate verified metrics before any prompt generation occurs.

### 5.2.3 Deterministic Financial Engine (`backend/app/engine/financial_engine.py`)
* **Role:** Single mathematical authority of the system.
* **Guarantees:**
  - Strict integer-paise representation via `to_paise()`, `div_paise()`, `mul_paise()`.
  - Exclusion of confirmed internal transfers (`not tx.get("is_transfer", False)`).
  - Multi-account EMI deduplication preventing Cartesian join inflation.
  - Affordability calculation enforcing the 3-month survival buffer before classifying a purchase as `SAFE`.
  - 4-pillar financial health scoring clamped strictly between 0.0 and 100.0 with letter grades A through D.

### 5.2.4 Historical Runway Engine (`backend/app/engine/historical_runway.py`)
* **Role:** Advanced historical runway diagnostics resolving single-month myopia and partial-month distortions.
* **Implemented Components:**
  - **4-State Account Lifecycle:** `ACTIVE_FULL_MONTH`, `PARTIAL_LIFECYCLE`, `NOT_ACTIVE`, `UNKNOWN_LIFECYCLE`. Accounts opened or closed mid-month automatically disqualify that calendar month from the baseline burn.
  - **Continuous MTD Interval Anchoring:** Requires unbroken statement coverage starting on Day 1 through `reporting_date`. Detects internal coverage gaps (e.g. Nov 1–2 and Nov 4–5 yields `PARTIAL_MTD_COVERAGE` with effective through date Nov 2).
  - **Renormalized Confidence Scoring:** Binary eligibility gating for 100% account coverage, combined with renormalized weights ($0.50 \cdot S_{\text{months}} + 0.30 \cdot S_{\text{consistency}} + 0.20 \cdot S_{\text{volume}}$).
  - **Exhaustive 3-Gate Hierarchy:** Deterministically assigns `INSUFFICIENT_DATA`, `LOW`, `MEDIUM`, or `HIGH` confidence tiers.

### 5.2.5 Post-Generation Factual Verifier (`backend/app/services/verifier.py`)
* **Role:** Intercepts LLM hallucinations and contradictory claims.
* **Two-Tier Enforcement Policy:**
  - **Tier 1 (Blocking):** Decision labels (`SAFE` vs `NOT_SAFE`, `HEALTHY` vs `CRITICAL`) and numerical metrics cited in *The Quick Take*, *The Numbers*, or *Smart Insights*. Any deviation from the evidence card triggers a retry loop.
  - **Tier 2 (Advisory):** Numerical recommendations in *What You Should Do Next* (heuristic advice) are audited and flagged as advisory without crashing the user's turn.
  - **Automated Fallback:** If the LLM repeatedly fails verification or encounters an API timeout, [`build_deterministic_fallback()`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\services\response_generator.py#L20) generates an authoritative 4-section report directly from the engine metrics.

### 5.2.6 Multimodal Receipt & Ingestion Hub (`backend/app/services/image_extractor.py`, `import_pipeline.py`)
* **Role:** Ingests unstructured financial documents (CSV files and receipt images).
* **Vision Pipeline:**
  - Validates image MIME magic bytes (JPEG, PNG, WebP).
  - Passes base64 image data to Groq's `qwen/qwen3.8-27b` vision model with explicit system constraints preventing imaginary amounts.
  - Returns structured JSON to the frontend for interactive user review and confirmation before committing transactions to Neo4j.
* **Internal Transfer Disambiguation:** Pairs opposite-polarity transactions across accounts occurring within $\pm 2$ calendar days, excluding commercial merchants and ATM cash withdrawals.

---

## 5.3 Frontend Component Architecture & User Experience

The React 18 frontend is engineered for transparent, accessible financial decision-making:
1. **Dynamic Dashboard ([`Dashboard.jsx`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\frontend\src\components\Dashboard.jsx)):** Displays high-level financial health cards (Liquid Balance, Monthly Living Burn, Savings Rate, Emergency Runway) with real-time health grade pill (A/B/C/D) and Recharts SVG category distribution pie charts.
2. **Conversational Advisory Chat ([`AssistantChat.jsx`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\frontend\src\components\AssistantChat.jsx)):** Renders multi-turn AI responses in structured 4-section executive format (*The Quick Take, The Numbers, Smart Insights, What You Should Do Next*) with expandable evidence cards showing source node IDs.
3. **Import Manager ([`ImportManager.jsx`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\frontend\src\components\ImportManager.jsx)):** Features dual tabs for CSV Statement Ingestion (with preview, duplicate detection badges, and transfer confirmation toggles) and Receipt OCR Image Upload (with interactive form review).

