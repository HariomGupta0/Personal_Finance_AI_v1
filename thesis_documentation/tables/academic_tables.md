# Academic Tables Reference: Personal Finance AI Assistant

This document contains the consolidated, academically formatted tables required for the B.Tech thesis, derived directly from the verified codebase, database schema, and empirical evaluation reports.

---

## Table 1.1: Comparative Analysis of Personal Finance Advisory Approaches

| Feature / Dimension | Traditional Mobile Banking Apps (e.g. Mint, YNAB) | Conventional Vector RAG (LLM + Vector DB) | Proposed Decoupled GraphRAG System (Ours) |
| :--- | :--- | :--- | :--- |
| **User Interaction** | Static forms, hardcoded charts | Conversational natural language | Conversational natural language + Dynamic cards |
| **Mathematical Accuracy** | Deterministic (100%) | Stochastic / Hallucinatory (40–60%) | **Deterministic Python Engine (100%)** |
| **Data Representation** | Relational SQL / NoSQL tables | Flat unstructured text chunks | **Multi-relational Knowledge Graph (Neo4j)** |
| **Currency Handling** | Fixed app locale | Frequent USD ($) hallucination | **Strict INR (₹) Symbol Preservation** |
| **Multi-Hop Relational Retrieval**| Rigid pre-joined queries | Fails semantic cosine similarity | **Targeted Cypher Subgraph Traversal** |
| **Hallucination Mitigation** | N/A (No generative text) | None or post-hoc LLM evaluation | **Two-Tier Deterministic Verifier + Fallback** |
| **Explainability (XAI)** | Static dashboards | Black-box generated prose | **Traceable 4-Section Cards with Node IDs** |
| **Transaction Ingestion** | Manual or Open Banking APIs | Manual copy-paste | **CSV Dialect Dedup + Groq Vision OCR** |

---

## Table 2.1: Verified System Technology Stack Specification

| Subsystem | Technology Component | Version | Academic / Engineering Purpose | Source File Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend Framework** | React.js | 18.3.1 | Component-driven UI rendering and state | `frontend/package.json` |
| **Frontend Build Tool** | Vite | 5.4.2 | Ultra-fast HMR and production bundling | `frontend/vite.config.js` |
| **Charting Library** | Recharts | 2.13.0 | Declarative SVG financial visualization | `frontend/src/components/Dashboard.jsx` |
| **Iconography** | Lucide React | 1.16.0 | Modern interface visual cues | `frontend/src/components/KPICards.jsx` |
| **Backend Framework** | FastAPI | 0.115.0+ | Asynchronous RESTful API Gateway | `backend/main.py` |
| **ASGI Web Server** | Uvicorn | 0.32.0+ | High-throughput asynchronous event loop | `backend/main.py` |
| **Graph Database** | Neo4j Community / Server | 5.25.0+ | Native graph storage and Cypher traversal| `backend/app/database/neo4j_service.py` |
| **Graph Protocol** | Neo4j Bolt Driver | 5.25.0+ | Binary socket multiplexing (Port 7687) | `backend/app/database/neo4j_service.py` |
| **Conversational LLM** | `openai/gpt-oss-120b` | Groq Cloud | Low-latency natural language explanation | `backend/config.py`, `llm_service.py` |
| **Multimodal Vision OCR**| `qwen/qwen3.8-27b` | Groq Vision | Zero-shot receipt and invoice OCR | `backend/config.py`, `image_extractor.py`|
| **Data Validation** | Pydantic v2 | 2.9.0+ | Strict schema validation and typing | `backend/app/api/auth.py` |
| **Deduplication Hashing**| Python `hashlib` SHA-256 | Native | Idempotent transaction fingerprinting | `backend/app/services/fingerprint.py` |
| **Monetary Arithmetic**| Custom Integer Paise Engine| Native | Absolute prevention of IEEE 754 floats | `backend/app/core/money.py` |
| **Rate Limiting** | SlowAPI | 0.1.9+ | Brute-force and DoS defense on auth routes| `backend/app/core/limiter.py` |

---

## Table 2.2: Hardware and Software Environment Requirements

| Category | Specification Requirement | Minimum Development Baseline | Production Deployment Recommendation |
| :--- | :--- | :--- | :--- |
| **Host Processor (CPU)** | x86_64 / ARM64 Multi-core | Quad-Core Intel Core i5 / AMD Ryzen 5 | Octa-Core Intel Xeon / AMD EPYC |
| **System Memory (RAM)** | DDR4 / DDR5 | 8 GB RAM (Neo4j JVM heap: 2 GB) | 16 GB RAM (Neo4j JVM heap: 8 GB) |
| **Secondary Storage** | Solid State Drive (NVMe/SSD) | 20 GB free disk space | 100 GB NVMe SSD with automated backups |
| **Operating System** | POSIX / Windows | Windows 11 / Ubuntu 22.04 LTS | Ubuntu Server 24.04 LTS (Dockerized) |
| **Python Runtime** | Python Virtual Environment | Python 3.10.x – 3.13.x | Python 3.11/3.12 LTS Docker Base |
| **Node.js Runtime** | Node Engine | Node.js v18.18+ / v20.x LTS | Node.js v20 LTS Alpine Image |
| **Database Server** | Local / Cloud Neo4j Instance | Neo4j Desktop 5.x on `127.0.0.1:7687` | Neo4j AuraDB Enterprise or Docker Cluster |
| **Network & Outbound** | HTTPS / TLS 1.3 | Broadband (Groq Cloud API access) | Dedicated low-latency VPC peering |

---

## Table 3.1: Neo4j Knowledge Graph Entity Schema (Node Labels & Properties)

| Node Label | Key Properties (Datatypes) | Description & Domain Significance | Uniqueness Constraint |
| :--- | :--- | :--- | :--- |
| **`:User`** | `id` (String), `username` (String), `name` (String), `password_hash` (String), `salt` (String) | Represents the authenticated account holder; acts as the root boundary for all graph isolations. | `u.id UNIQUE`, `u.username UNIQUE` |
| **`:Account`** | `id` (String), `bank` (String), `account_type` (String), `balance` (Float), `balance_paise` (Integer), `opened_date` (Date), `status` (String) | Financial repository (Savings, Checking, Credit Card). Stores balance in both rupee float and integer paise. | `a.id UNIQUE` |
| **`:Transaction`**| `id` (String), `description` (String), `amount` (Float), `amount_paise` (Integer), `type` (String: `EXPENSE`/`INCOME`), `date` (Date), `category` (String), `fingerprint` (String), `is_transfer` (Boolean) | Individual debit or credit record. Fingerprint ensures idempotent ingestion. Confirmed internal transfers are flagged. | `t.id UNIQUE`, `t.fingerprint UNIQUE` |
| **`:Category`** | `id` (String), `name` (String: `Rent`, `Food`, `Utilities`, etc.) | Taxonomy classification for expenses and income streams. | `c.id UNIQUE` |
| **`:Income`** | `id` (String), `source` (String), `amount` (Float), `amount_paise` (Integer), `date` (Date), `category` (String) | Verified monthly recurring salary, dividends, or freelance earnings. | `i.id UNIQUE` |
| **`:Loan`** | `id` (String), `name` (String), `principal` (Float), `outstanding` (Float), `emi` (Float), `emi_paise` (Integer) | Contractual debt liability (e.g. Home Loan, Car Loan, Personal Loan). | `l.id UNIQUE` |
| **`:EMI`** | `id` (String), `amount` (Float), `amount_paise` (Integer), `due_date` (Date), `status` (String: `PENDING`/`PAID`) | Monthly scheduled loan repayment tranche used for DTI and runway calculations. | `e.id UNIQUE` |
| **`:Goal`** | `id` (String), `name` (String), `target_amount` (Float), `current_amount` (Float), `target_date` (Date) | Savings objective (e.g. Emergency Fund, Vacation, Retirement). | `g.id UNIQUE` |
| **`:Merchant`** | `name` (String), `normalized` (String), `channel` (String), `default_category` (String) | Normalized payee entity (e.g. Swiggy, Uber, Amazon) extracted from noisy narrations. | `m.normalized UNIQUE` |
| **`:ImportBatch`**| `id` (String), `filename` (String), `timestamp` (DateTime), `total_records` (Integer), `imported_count` (Integer), `duplicate_count` (Integer) | Auditable batch provenance for CSV statement and receipt uploads. | `b.id UNIQUE` |

---

## Table 3.2: Neo4j Knowledge Graph Relationships

| Relationship Type | Source Node | Target Node | Cardinality | Semantic Meaning in Graph |
| :--- | :--- | :--- | :---: | :--- |
| **`HAS_ACCOUNT`** | `:User` | `:Account` | $1 : N$ | User legally owns and operates the transactional account. |
| **`MADE_TRANSACTION`** | `:Account` | `:Transaction` | $1 : N$ | Financial transaction originated from or credited to the account. |
| **`BELONGS_TO`** | `:Transaction` | `:Category` | $N : 1$ | Categorical classification of transaction for budget tracking. |
| **`RECEIVED_INCOME`** | `:User` | `:Income` | $1 : N$ | Verified incoming earnings credited to the user's portfolio. |
| **`HAS_LOAN`** | `:User` | `:Loan` | $1 : N$ | Debt facility legally held by the user. |
| **`HAS_EMI`** | `:Loan` | `:EMI` | $1 : N$ | Scheduled periodic repayment obligation belonging to a loan. |
| **`HAS_GOAL`** | `:User` | `:Goal` | $1 : N$ | Capital allocation target set by the user. |
| **`PART_OF_BATCH`** | `:Transaction` | `:ImportBatch` | $N : 1$ | Traceable lineage linking transaction to its source upload file. |
| **`INTER_ACCOUNT_TRANSFER`**| `:Transaction` | `:Transaction` | $1 : 1$ | Symmetrical pair linking debit on Account A with credit on Account B. |

---

## Table 4.1: Deterministic Financial Engine Mathematical Formulations

| Metric Name | Mathematical Formulation | Variable Definitions | Decision Thresholds / Diagnostic Bands |
| :--- | :--- | :--- | :--- |
| **Net Savings** | $\text{NetSavings} = \sum \text{Income} - \sum \text{Expenses}$ | All confirmed non-transfer income and expenses in reporting month. | $\text{NetSavings} > 0$: Positive Cash Flow; $\le 0$: Deficit. |
| **Savings Rate** | $\text{SR} = \left(\frac{\text{NetSavings}}{\sum \text{Income}}\right) \times 100$ | Expressed as percentage of total monthly income. | $\ge 20\%$: Healthy baseline; $< 0\%$: Critical dissaving. |
| **Emergency Target** | $\text{Target} = (K \times \text{MonthlyBurn}) + \text{Obligations}$ | $K = 3$ (default reserve multiplier); $\text{Obligations}$ = annual irregulars. | Standard 3-month survival baseline. |
| **Emergency Runway** | $R = \frac{\text{LiquidCashAssets}}{\text{MonthlyLivingBurn}}$ | $\text{LiquidCashAssets} = \sum \max(0, \text{Balance})$; exclusions apply. | $R < 1.0$: `CRITICAL`; $1.0 \le R < 3.0$: `INSUFFICIENT`; $3.0 \le R < 6.0$: `HEALTHY`; $R \ge 6.0$: `STRONG`. |
| **Debt-to-Income (DTI)**| $\text{DTI} = \left(\frac{\sum \text{PendingEMIs}}{\sum \text{Income}}\right) \times 100$ | Deduplicated EMIs due in target reporting calendar month. | $\le 20\%$: `LOW`; $20–35\%$: `MODERATE`; $35–50\%$: `HIGH`; $> 50\%$: `CRITICAL`. |
| **Post-Purchase Solvency**| $\text{Bal}_{\text{post}} = \text{LiquidBalance} - \text{EMIs} - \text{Purchase}$ | Immediate cash remaining after servicing pending debts and proposed purchase. | $\text{Bal}_{\text{post}} \ge \text{Target} \implies \mathbf{SAFE}$; otherwise $\mathbf{NOT\_SAFE}$. |
| **Purchase Risk Tier**| Evaluated on $\text{Bal}_{\text{post}}$ vs Living Expenses | Compares post-purchase liquidity against monthly survival burn. | $\ge \text{Target}$: `LOW`; $\ge \text{Expenses}$: `MEDIUM`; $> 0$: `HIGH`; $\le 0$: `VERY_HIGH`. |
| **Comprehensive Health**| $\text{HealthScore} = \sum_{i=1}^4 w_i \cdot S_i$ | Weights: Savings 35%, Runway 35%, Debt 20%, Goals 10%. | Grade `A` ($\ge 85$), `B` ($70–84$), `C` ($50–69$), `D` ($< 50$). |

---

## Table 5.1: Multi-Dimensional Benchmark Evaluation Results (24 Research Scenarios)

| Evaluation Dimension | Total Test Cases | Passed Cases | Failed Cases | Empirical Accuracy (%) | Primary Research Objective Verified |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Numerical Correctness** | 5 | 5 | 0 | **100.0%** | Mathematical accuracy of solvency, DTI, and emergency buffers without floating-point error. |
| **2. Status Consistency** | 4 | 4 | 0 | **100.0%** | Strict alignment between engine decision and LLM textual verdict (rejection of contradictory claims). |
| **3. Unsupported Claims** | 4 | 4 | 0 | **100.0%** | Verification layer interception of phantom monetary figures and hallucinated ungrounded metrics. |
| **4. Reporting Periods & Data Gaps**| 4 | 4 | 0 | **100.0%** | Explicit qualification of incomplete months and zero-expense periods; prevents false 100% savings rate. |
| **5. Prompt Injection Defense** | 4 | 4 | 0 | **100.0%** | Robustness against adversarial system prompt overrides via XML delimiter boundary isolation. |
| **6. Safe Fallback Handling** | 3 | 3 | 0 | **100.0%** | Guaranteed delivery of authoritative 4-section reports during simulated LLM provider timeouts/outages. |
| **OVERALL COMPOSITE** | **24** | **24** | **0** | **100.0%** | **Empirical validation of decoupled neuro-symbolic financial advisory architecture.** |

---

## Table 5.2: End-to-End Latency Breakdown Across Pipeline Stages

| Pipeline Stage | Module Executing | Execution Nature | Empirical Latency (ms) | Percentage of Total Turn |
| :--- | :--- | :--- | :---: | :---: |
| **Stage 1: NLU & Question Parsing** | `backend/app/nlu/question_parser.py` | Regex / Rule-based AST | **0.1 ms** | $< 0.01\%$ |
| **Stage 2: Graph Subgraph Retrieval**| `backend/app/rag/graph_rag.py` | Indexed Cypher Socket | **11.8 ms** | $0.65\%$ |
| **Stage 3: Deterministic Financial Engine**| `backend/app/engine/financial_engine.py`| Pure Python Integer Math | **0.1 ms** | $< 0.01\%$ |
| **Stage 4: Evidence Assembly & Formatting**| `backend/app/services/prompt_builder.py`| String Template Synthesis | **0.1 ms** | $< 0.01\%$ |
| **Stage 5: LLM Inference & Generation** | Groq Cloud (`openai/gpt-oss-120b`) | Neural Autoregressive | **1,790.3 ms** | $99.33\%$ |
| **Stage 6: Factual Verification Audit** | `backend/app/services/verifier.py` | Regex Metric Auditor | **0.2 ms** | $0.01\%$ |
| **TOTAL END-TO-END TURN** | Full Stack Pipeline | Synchronous Request Turn | **~1,802.6 ms** | **100.0%** |

