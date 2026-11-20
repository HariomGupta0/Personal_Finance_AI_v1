# Project Context: Personal Finance AI Assistant Using Dynamic Knowledge Graphs and LLM-Based GraphRAG

## 1. Executive Summary

This project is an explainable, research-grade, full-stack personal finance advisory system that combines:
1. **Dynamic Knowledge Graphs (Neo4j)** for structured, relational, and auditable financial fact representation.
2. **Deterministic Financial Reasoning (Python Engine)** as the single source of truth for all mathematical calculations (savings rate, emergency runway, purchase affordability, debt burden, comprehensive health scoring).
3. **Graph Retrieval-Augmented Generation (GraphRAG)** to selectively retrieve grounded subgraphs for user queries rather than naive full-database dumps.
4. **Strict Grounded LLM Explanations (Groq / Open Models)** that translate mathematical evidence into human-friendly explanations without hallucinating numbers or performing arithmetic.
5. **Multimodal Transaction Ingestion** via natural language statements, bank statement CSV imports with SHA-256 deduplication, and Groq Vision OCR for receipts and UPI screenshots.
6. **Full-Stack Interface (FastAPI + React Dashboard)** featuring real-time Neo4j health monitoring, interactive KPI cards, multi-turn AI advisory chat, and transaction management.
7. **Automated Evaluation Benchmark Suite** providing empirical testing across 6 research dimensions (numerical correctness, status consistency, hallucination rejection, missing data caveats, injection resistance, and graceful fallback).

---

## 2. Core Architectural Philosophy & Data Flow

```text
User Interaction (Text / CSV / Receipt Image)
                         ↓
  [Ingestion / NLU Layer]
  • Multimodal Groq Vision (qwen/qwen3.8-27b) for Receipts & Screenshots
  • CSV Statement Parser + Merchant Normalizer + SHA-256 Fingerprint Deduplication
  • NLU Question Parser & Intent Classifier (Rules + Date Ambiguity + Follow-Up Memory)
                         ↓
  [Dynamic Knowledge Graph (Neo4j: finance-ai-antigravity)]
  • Live mutations: accounts, transactions, loans, EMIs, incomes, goals
                         ↓
  [Targeted Subgraph Retrieval (GraphRAG)]
  • Intent-scoped Cypher traversal extracting authorized nodes & relationships
                         ↓
  [Deterministic Financial Engine (Python Source of Truth)]
  • Mathematical computation of Savings, Runway, Emergency Fund, DTI, Safety, Health
                         ↓
  [Structured Grounding & Verifiable Evidence Payload]
  • Facts, exact formulas, node IDs, reporting periods, and missing data caveats
                         ↓
  [LLM Response Generator (Groq Async Client - openai/gpt-oss-120b)]
  • Prompt Registry (v1.0 baseline vs v1.1 4-section executive cards)
  • XML delimiter isolation (<user_question>, <financial_evidence>) preventing prompt injection
  • Strict Indian Rupee (₹) symbol preservation and zero arithmetic hallucination
                         ↓
  [FastAPI REST API Layer] (Port 8000, Session-Based Cookie Auth & CSRF Protection)
                         ↓
  [React + Vite Frontend Dashboard] (Port 3000, Interactive Cards, Charts & AI Chat)
```

> **Core Axiom: The LLM is NEVER the source of truth for financial math.**
> - Neo4j stores immutable, verified financial facts.
> - Python computes exact financial formulas and decision boundaries deterministically.
> - Evidence is structured explicitly as verifiable data points with source node IDs.
> - The LLM explains only the evidence provided, adhering to strict formatting rules (e.g., preserving `₹` currency symbols and never modifying numeric values).

---

## 3. Knowledge Graph Schema

### Entity Nodes
- **`User`**: `{id: String, name: String}`
- **`Account`**: `{id: String, bank: String, account_type: String, balance: Float}`
- **`Transaction`**: `{id: String, description: String, amount: Float, type: String ('EXPENSE' | 'INCOME'), date: Date, category: String, fingerprint: String}`
- **`Category`**: `{id: String, name: String}`
- **`Income`**: `{id: String, source: String, amount: Float, date: Date, category: String}`
- **`Loan`**: `{id: String, name: String, principal: Float, outstanding: Float, emi: Float}`
- **`EMI`**: `{id: String, amount: Float, due_date: Date, status: String ('PENDING' | 'PAID')}`
- **`Goal`**: `{id: String, name: String, target_amount: Float, current_amount: Float, target_date: Date}`
- **`Budget`**: `{id: String, category: String, monthly_limit: Float, period: String}`

### Relationships
- `(:User)-[:HAS_ACCOUNT]->(:Account)`
- `(:Account)-[:MADE_TRANSACTION]->(:Transaction)`
- `(:Transaction)-[:BELONGS_TO]->(:Category)`
- `(:User)-[:RECEIVED_INCOME]->(:Income)`
- `(:User)-[:HAS_LOAN]->(:Loan)`
- `(:Loan)-[:HAS_EMI]->(:EMI)`
- `(:User)-[:HAS_GOAL]->(:Goal)`
- `(:User)-[:HAS_BUDGET]->(:Budget)`

---

## 4. Deterministic Financial Reasoning Formulas

All calculations are executed in `backend/app/engine/financial_engine.py`:

### 1. Savings Rate & Net Savings
$$\text{Total Monthly Expenses} = \sum_{\text{type} = \text{'EXPENSE'}} \text{Transaction.amount}$$
$$\text{Net Savings} = \text{Total Income} - \text{Total Expenses}$$
$$\text{Savings Rate (\%)} = \left(\frac{\text{Net Savings}}{\text{Total Income}}\right) \times 100$$

### 2. Emergency Fund Requirement & Shortfall
$$\text{Recommended Emergency Reserve} = \text{Monthly Expenses} \times 3$$
$$\text{Emergency Shortfall} = \max(0, \text{Recommended Emergency Reserve} - \text{Current Emergency Goal Fund})$$

### 3. Emergency Runway (Months)
$$\text{Emergency Runway} = \frac{\text{Current Liquid Balance}}{\text{Monthly Expenses}}$$
- `CRITICAL`: Balance $< 0$ or Runway $< 1.0$ month
- `INSUFFICIENT`: $1.0 \le \text{Runway} < 3.0$ months
- `HEALTHY`: $3.0 \le \text{Runway} < 6.0$ months
- `STRONG`: $\text{Runway} \ge 6.0$ months

### 4. Debt Burden & Debt-to-Income (DTI)
$$\text{Monthly EMI} = \sum \text{Deduplicated Pending EMIs (Target Month)}$$
$$\text{DTI Ratio (\%)} = \left(\frac{\text{Monthly EMI}}{\text{Total Income}}\right) \times 100$$
- `LOW`: $\text{DTI} \le 20\%$ (Healthy debt level)
- `MODERATE`: $20\% < \text{DTI} \le 35\%$ (Manageable obligations)
- `HIGH`: $35\% < \text{DTI} \le 50\%$ (Elevated burden)
- `CRITICAL`: $\text{DTI} > 50\%$ or active EMI with zero income

### 5. Purchase Safety Decision & Risk Classification
$$\text{Balance After Purchase} = \text{Liquid Balance} - \text{Pending EMIs} - \text{Sanitized Purchase Amount}$$
- **Decision**: `SAFE` if $\text{Balance After Purchase} \ge \text{Recommended Emergency Reserve}$, else `NOT_SAFE`.
- **Risk Level**:
  - `LOW`: $\text{Balance After Purchase} \ge \text{Recommended Emergency Reserve}$
  - `MEDIUM`: $\text{Monthly Expenses} \le \text{Balance After Purchase} < \text{Recommended Emergency Reserve}$
  - `HIGH`: $0 < \text{Balance After Purchase} < \text{Monthly Expenses}$
  - `VERY_HIGH`: $\text{Balance After Purchase} \le 0$

### 6. Comprehensive Financial Health Score (0–100) & Grade
$$\text{Health Score} = (\text{Savings Component} \times 0.35) + (\text{Runway Component} \times 0.35) + (\text{Debt Component} \times 0.20) + (\text{Goal Component} \times 0.10)$$
- Clamped strictly between `0.0` and `100.0`.
- Letter grades: `A` ($\ge 85$), `B` ($\ge 70$), `C` ($\ge 50$), `D` ($< 50$).

---

## 5. Modular Project Directory Structure

```text
Personal_Finance_AI_FYP/
├── backend/
│   ├── main.py                        # FastAPI application entrypoint & middleware
│   ├── config.py                      # Centralized configuration & environment loader
│   ├── app/
│   │   ├── api/                       # REST API endpoint routers
│   │   │   ├── auth.py                # Cookie-based session authentication & CSRF
│   │   │   ├── assistant.py           # Multi-turn AI assistant query & memory endpoints
│   │   │   ├── finance.py             # Dashboard KPIs, health, runway & debt endpoints
│   │   │   ├── transactions.py        # Transaction CRUD & real-time graph mutation
│   │   │   ├── goals.py               # Financial goals tracking & updates
│   │   │   ├── import_api.py          # Multimodal vision OCR & CSV statement import
│   │   │   └── deps.py                # FastApi dependency injection (auth & GraphRAG)
│   │   ├── core/                      # Logging & core utilities
│   │   ├── database/
│   │   │   └── neo4j_service.py       # Neo4j driver, Cypher queries, graph mutations
│   │   ├── engine/
│   │   │   └── financial_engine.py    # Deterministic mathematical calculation engine
│   │   ├── nlu/
│   │   │   ├── question_parser.py     # Intent classification, date ambiguity, entity parsing
│   │   │   └── transaction_extractor.py # Rules + Groq Vision receipt image extractor
│   │   ├── rag/
│   │   │   └── graph_rag.py           # Targeted subgraph retrieval & async GraphRAG pipeline
│   │   ├── services/
│   │   │   ├── llm_service.py         # Async Groq client with exponential backoff & telemetry
│   │   │   ├── prompt_builder.py      # Versioned prompt registry (v1.0, v1.1) & injection defense
│   │   │   ├── response_generator.py  # Response orchestrator bridging engine and LLM
│   │   │   ├── ingestion_service.py   # Transaction ingestion & live graph balance updates
│   │   │   ├── csv_parser.py          # Bank statement CSV dialect & schema detection
│   │   │   ├── import_pipeline.py     # Batch statement processing with deduplication
│   │   │   ├── merchant_normalizer.py # Standardizes raw merchant strings to clean entities
│   │   │   ├── fingerprint.py         # SHA-256 deduplication hashing for transactions
│   │   │   └── financial_planner.py   # AI financial recommendations & scenario analysis
│   │   └── evaluation/
│   │       ├── dataset.py             # 24 research benchmark test cases across 6 dimensions
│   │       ├── evaluator.py           # Automated evaluation runner & scoring logic
│   │       └── runner.py              # CLI & programmatic benchmark execution
│   ├── cli/
│   │   └── assistant.py               # Interactive terminal-based financial assistant
│   ├── scripts/
│   │   ├── seed_db.py                 # Idempotent database seeder for demo user Rahul
│   │   └── run_evaluation.py          # CLI runner for automated 24-test evaluation suite
│   └── tests/                         # Comprehensive unit, integration, and security tests
├── frontend/                          # Production React 18 + Vite dashboard
│   ├── src/
│   │   ├── App.jsx                    # Root app layout, auth protection & view routing
│   │   ├── index.css                  # Modern dark-mode glassmorphic design system
│   │   ├── components/
│   │   │   ├── AssistantChat.jsx      # Multi-turn chat with 4-section executive cards
│   │   │   ├── Dashboard.jsx          # KPI cards, Recharts visualizations & health grade
│   │   │   ├── TransactionManager.jsx # Interactive transaction table with filtering & add/delete
│   │   │   ├── ImportManager.jsx      # CSV statement upload & Groq Vision receipt OCR
│   │   │   └── FinancialPlan.jsx      # Strategic financial advisory action plans
│   └── package.json
├── docs/                              # Architecture, schemas, deployment & API guides
├── .env                               # Active environment variables (gitignored)
├── requirements.txt                   # Backend Python dependencies
├── run_tests.py                       # Full test suite launcher
└── HOW_TO_RUN.md                      # Complete setup & developer instructions
```

---

## 6. Environment & Database Configuration

- **Workspace Path**: `c:\Users\gupta\Documents\HARIOM\Personal_Finance_AI_FYP`
- **Database Engine**: Neo4j Community/Enterprise (Bolt protocol on `neo4j://127.0.0.1:7687`)
- **Active Isolated Database**: `finance-ai-antigravity`
- **LLM Model**: `openai/gpt-oss-120b` (Groq API client)
- **Vision Model**: `qwen/qwen3.8-27b` (Groq Vision OCR for receipts/invoices)
- **Prompt Template Default**: `v1.1` (4-section executive cards)
- **Demo User Profile**: `Rahul` (`U001`) with password `demo1234`
- **Session Authentication**: Signed HTTP-only cookie with secret token and 8-hour TTL
- **Python Environment**: Python 3.13 (`.venv`)
