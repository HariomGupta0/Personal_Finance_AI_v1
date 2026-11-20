# Chapter 1 — Project Understanding & Comprehensive Overview

## 1.1 Project Title and Academic Context
* **Thesis Title:** EXPLAINABLE PERSONAL FINANCE AI ASSISTANT USING DYNAMIC KNOWLEDGE GRAPH AND LARGE LANGUAGE MODEL
* **Degree:** Bachelor of Technology (B.Tech) in Computer Science and Engineering (Artificial Intelligence)
* **Domain:** Financial Technology (FinTech), Explainable Artificial Intelligence (XAI), Graph Retrieval-Augmented Generation (GraphRAG), Knowledge Graphs, and Natural Language Processing (NLP).

---

## 1.2 Problem Statement & Research Motivation

### 1.2.1 The Core Dilemma in Financial AI
Personal finance management is inherently quantitative, relational, and high-stakes. While conversational Artificial Intelligence—specifically Large Language Models (LLMs)—has demonstrated remarkable fluency in natural language comprehension, deploying generic LLMs or conventional Vector Retrieval-Augmented Generation (Vector RAG) for personal financial advice introduces three catastrophic vulnerabilities:

1. **Arithmetic Hallucination and Stochastic Inconsistency:**
   LLMs generate text probabilistically based on next-token distribution rather than executing algebraic reasoning. In financial domains requiring exact accounting (such as debt-to-income ratios, emergency runway buffers, or post-purchase solvency), LLMs regularly invent numbers, round inconsistently, or fail basic multi-hop arithmetic (e.g. subtracting loan EMIs from liquid balances while factoring in a 3-month expense reserve).
2. **Loss of Relational and Temporal Context in Vector Embeddings:**
   Standard Vector RAG flattens financial ledgers into unstructured text chunks, computing cosine similarity over dense embeddings. This approach destroys the strict multi-entity relational topologies fundamental to financial health—specifically, how a `User` owns multiple `Accounts`, how an `Account` incurs `Transactions` grouped under `Categories`, and how recurring `Loans` obligate specific contractual `EMIs`. In vector search, semantic similarity often retrieves unrelated transactions while missing critical pending liabilities.
3. **Black-Box Opacity and Lack of Auditability:**
   Conventional financial chatbots output advice without traceable provenance. When a user asks *"Can I afford a ₹15,000 smartphone?"*, a generic model provides an ungrounded binary judgment without demonstrating the mathematical steps or proving which specific bank balances and loan obligations were factored into the decision.

### 1.2.2 Proposed Solution: Decoupled Explainable Architecture
This project resolves these fundamental challenges by proposing and implementing a **decoupled, hybrid neuro-symbolic architecture**:
- **Symbolic Layer (Neo4j Dynamic Knowledge Graph + Deterministic Python Financial Engine):** Serves as the immutable single source of truth. All financial entities, relational edges, and transactions are stored as graph nodes. All mathematical aggregations, ratios, health scores, and solvency boundaries are computed deterministically using integer-paise precision in Python.
- **Neural Layer (Groq-hosted Open LLM + Multimodal Vision OCR):** Serves purely as a natural language interface. The LLM translates verified mathematical evidence cards into empathetic, transparent 4-section executive explanations, while a post-generation Deterministic Verifier actively intercepts any contradictory or ungrounded assertions before they reach the user.

---

## 1.3 Core Architectural Axioms

The implementation of this system is governed by five non-negotiable architectural axioms:

| Axiom | Principle | Implementation Enforcement |
| :--- | :--- | :--- |
| **Axiom 1** | **The LLM is NEVER the source of financial truth.** | Financial arithmetic is strictly forbidden in LLM prompts. All figures are computed by `backend/app/engine/financial_engine.py` and provided as structured evidence. |
| **Axiom 2** | **Integer-Paise Precision Throughout.** | To eliminate IEEE 754 floating-point rounding errors (e.g., $0.1 + 0.2 \neq 0.3$), all monetary amounts are normalized, stored, and calculated in integer paise ($1\text{ Rupee} = 100\text{ Paise}$) via `backend/app/core/money.py`. |
| **Axiom 3** | **Relational Grounding via Intent-Scoped GraphRAG.** | Rather than passing monolithic database dumps or flat vector chunks, `backend/app/rag/graph_rag.py` executes targeted Cypher graph traversals to extract only the authorized subgraph relevant to the user's specific financial intent. |
| **Axiom 4** | **Two-Tier Post-Generation Verification.** | Every generated LLM response is parsed by `backend/app/services/verifier.py`. Any contradiction in status (e.g. Engine: `NOT_SAFE` vs LLM: `SAFE`) or hallucinated numerical token immediately triggers automated retry or deterministic fallback. |
| **Axiom 5** | **Zero-Trust Input & Sovereign Deduplication.** | Financial inputs (CSV statements, receipt images) undergo SHA-256 fingerprint deduplication with occurrence tracking, canonical merchant normalization, and user isolation in Neo4j. |

---

## 1.4 Verified Technology Stack Specification

The implementation of the system was thoroughly inspected across all configuration files, dependency manifests, and source modules:

### 1. Backend Architecture
* **Framework:** FastAPI (`v0.115.0+`) running ASGI server Uvicorn on Python 3.13 (`.venv`).
* **Database Driver:** `neo4j` Python driver (`v5.25.0+`) communicating via Bolt protocol on port `7687` to an isolated database (`finance-ai-antigravity`).
* **LLM Engine:** Groq Cloud API executing `openai/gpt-oss-120b` (low-latency inference, ~1,800 ms total pipeline turn).
* **Vision OCR Engine:** Groq Cloud Vision API executing `qwen/qwen3.8-27b` (fallback: `meta-llama/llama-4-scout-17b-16e-instruct`) for receipts and UPI screenshot parsing.
* **Security & Session:** Signed HTTP-only session cookies with PBKDF2 HMAC-SHA256 password salting, CSRF mitigation, and `slowapi` rate limiting.
* **Data Processing & Utilities:** Python `decimal.Decimal`, `pydantic v2`, `hashlib` SHA-256, `re` regex engine.

### 2. Frontend Architecture
* **Framework:** React 18 (`v18.3.1`) scaffolded with Vite (`v5.4.2`).
* **State & Networking:** Client-side React hooks (`useState`, `useEffect`) communicating with backend `/api` via Vite reverse proxy on port `3000`.
* **Visualizations & UI:** Recharts (`v2.13.0`), Lucide React (`v1.16.0`), custom dark-mode glassmorphic CSS design system.
* **Formatting:** Markdown rendering with `react-markdown` (`v10.1.0`) supporting structured 4-section executive cards.

---

## 1.5 System Functional Scope & Implemented Capabilities

The application provides a comprehensive suite of verified financial capabilities:

1. **Deterministic Solvency & Affordability Analysis (`PURCHASE_SAFETY`):**
   Evaluates proposed discretionary purchases against liquid checking/savings reserves, short-term debt servicing obligations (pending EMIs), and mandatory emergency reserve buffers ($3 \times \text{Monthly Expenses}$).
2. **Emergency Runway & Burn-Rate Diagnostics (`EMERGENCY_RUNWAY_ANALYSIS`):**
   Calculates available survival runway in months ($R = \frac{\text{Liquid Balance}}{\text{Monthly Burn}}$), categorizing financial resilience into `CRITICAL`, `INSUFFICIENT`, `HEALTHY`, and `STRONG`. Includes Task 2 Historical Runway improvements with 4-state account lifecycle and MTD interval continuity.
3. **Debt-to-Income (DTI) & Liability Servicing (`DEBT_ANALYSIS`):**
   Deduplicates pending loan EMIs across target reporting months, computing DTI ratios with tiered risk bands (`LOW` $\le 20\%$, `MODERATE` $\le 35\%$, `HIGH` $\le 50\%$, `CRITICAL` $> 50\%$).
4. **Comprehensive Financial Health Scoring (`FINANCIAL_HEALTH`):**
   Calculates an authoritative 0–100 financial health index across 4 weighted pillars: Savings Rate (35%), Runway Duration (35%), Debt Burden (20%), and Emergency Goal Funding (10%), assigning academic letter grades (A, B, C, D).
5. **Multimodal Ingestion & Statement Normalization:**
   Supports bank statement CSV uploads across varied bank dialects with SHA-256 fingerprint deduplication, UPI/POS/IMPS narration normalization, internal transfer disambiguation, and Groq Vision receipt image extraction.
6. **Conversational AI Financial Advisor with Grounded Evidence Cards:**
   Multi-turn conversational assistant with conversational memory, date-ambiguity resolution, XML delimiter prompt isolation, and structured 4-section executive responses (*The Quick Take, The Numbers, Smart Insights, What You Should Do Next*).

