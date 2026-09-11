# Project Context: Personal Finance AI Assistant Using Dynamic Knowledge Graphs and LLM-Based GraphRAG

## 1. Executive Summary

This project is a research-oriented, explainable personal finance assistant that combines:
1. **Dynamic Knowledge Graphs (Neo4j)** for structured, relational, and auditable financial fact representation.
2. **Deterministic Financial Reasoning (Python Engine)** as the single source of truth for all mathematical calculations (savings rate, emergency fund adequacy, purchase affordability, debt burden).
3. **Graph Retrieval-Augmented Generation (GraphRAG)** to selectively retrieve grounded subgraphs for given queries and user contexts.
4. **Strict Grounded LLM Explanations (Groq / Open Models)** that translate mathematical evidence into natural language without hallucinating numbers or performing arithmetic.
5. **Full-Stack Interface (FastAPI + React Dashboard)** for real-time visualization, graph interaction, and conversational advisory.

---

## 2. Core Architectural Philosophy

```
User Financial Input / Question
              ↓
  Natural Language Understanding (Parser / Extractor)
              ↓
  Dynamic Knowledge Graph (Neo4j - Isolated Database)
              ↓
  Relevant Subgraph Retrieval (GraphRAG + Semantic Search)
              ↓
  Deterministic Financial Engine (Python Source of Truth)
              ↓
  Structured Grounding & Verifiable Evidence
              ↓
  LLM Explanation Generator (Strict Prompt Constraints)
              ↓
  API Layer (FastAPI) → UI (React Dashboard & Assistant)
```

> **The LLM is NEVER the source of truth for financial math.**
> - Neo4j stores verified facts.
> - Python computes exact financial formulas and decision boundaries.
> - Evidence is structured explicitly as verifiable data points.
> - The LLM explains only the evidence provided, adhering to strict formatting rules (e.g., preserving `₹` currency symbols and never modifying numeric values).

---

## 3. Knowledge Graph Schema

### Entity Nodes
- **`User`**: `{id: String, name: String}`
- **`Account`**: `{id: String, bank: String, account_type: String, balance: Float}`
- **`Transaction`**: `{id: String, description: String, amount: Float, type: String ('EXPENSE' | 'INCOME'), date: Date}`
- **`Category`**: `{id: String, name: String}`
- **`Income`**: `{id: String, source: String, amount: Float, date: Date}`
- **`Loan`**: `{id: String, name: String, principal: Float, outstanding: Float}`
- **`EMI`**: `{id: String, amount: Float, due_date: Date, status: String ('PENDING' | 'PAID')}`
- **`Goal`**: `{id: String, name: String, target_amount: Float, current_amount: Float, target_date: Date}`

### Relationships
- `(:User)-[:HAS_ACCOUNT]->(:Account)`
- `(:Account)-[:MADE_TRANSACTION]->(:Transaction)`
- `(:Transaction)-[:BELONGS_TO]->(:Category)`
- `(:User)-[:RECEIVED_INCOME]->(:Income)`
- `(:User)-[:HAS_LOAN]->(:Loan)`
- `(:Loan)-[:HAS_EMI]->(:EMI)`
- `(:User)-[:HAS_GOAL]->(:Goal)`

---

## 4. Deterministic Financial Reasoning Formulas

1. **Savings Rate**:
   $$\text{Total Expenses} = \sum_{\text{type} = \text{'EXPENSE'}} \text{Transaction.amount}$$
   $$\text{Savings} = \text{Total Income} - \text{Total Expenses}$$
   $$\text{Savings Rate} = \left(\frac{\text{Savings}}{\text{Total Income}}\right) \times 100$$

2. **Emergency Fund Requirement**:
   $$\text{Recommended Emergency Reserve} = \text{Monthly Expenses} \times 3$$
   $$\text{Emergency Shortfall} = \max(0, \text{Recommended Emergency Reserve} - \text{Current Goal Amount})$$

3. **Purchase Safety Decision & Risk Classification**:
   $$\text{Balance After Purchase} = \text{Current Account Balance} - \sum \text{Pending EMIs} - \text{Purchase Amount}$$
   - **Decision**: `SAFE` if $\text{Balance After Purchase} \ge \text{Recommended Emergency Reserve}$, else `NOT_SAFE`.
   - **Risk Classification**:
     - `LOW`: $\text{Balance After Purchase} \ge \text{Recommended Emergency Reserve}$
     - `MEDIUM`: $\text{Monthly Expenses} \le \text{Balance After Purchase} < \text{Recommended Emergency Reserve}$
     - `HIGH`: $0 < \text{Balance After Purchase} < \text{Monthly Expenses}$
     - `VERY_HIGH`: $\text{Balance After Purchase} \le 0$

---

## 5. Clean Modular Directory Structure

```text
Personal_Finance_AI_Antigravity/
├── backend/
│   ├── config.py                      # Centralized environment & settings management
│   ├── app/
│   │   ├── database/neo4j_service.py  # Neo4j driver & parameterized graph operations
│   │   ├── engine/financial_engine.py # Deterministic financial calculation engine
│   │   ├── nlu/
│   │   │   ├── question_parser.py     # Intent & entity extraction
│   │   │   └── transaction_extractor.py # NL transaction extraction (rules + LLM)
│   │   ├── services/
│   │   │   ├── ingestion_service.py   # Transaction ingestion & instant recalculation
│   │   │   ├── llm_service.py         # Groq LLM API client
│   │   │   ├── prompt_builder.py      # Strict prompt constructor
│   │   │   └── response_generator.py  # Response orchestrator
│   │   └── rag/
│   │       └── graph_rag.py           # Subgraph retrieval & hybrid GraphRAG (Phase 5/6)
│   ├── cli/assistant.py               # Interactive CLI financial assistant
│   ├── scripts/seed_db.py             # Idempotent database seeder
│   └── tests/                         # Complete automated test suite
├── frontend/                          # Prepared directory for React dashboard (Phase 10)
├── docs/                              # Project documentation
├── .env                               # Isolated environment config
├── requirements.txt                   # Dependency list
├── run_cli.py                         # Root launcher for CLI assistant
└── run_tests.py                       # Root launcher for all test suites
```

---

## 6. Environment & Database Configuration

- **Database**: Neo4j Community/Enterprise (Bolt protocol on `neo4j://127.0.0.1:7687`)
- **Active Isolated Database**: `finance-ai-antigravity`
- **Configuration**: [.env](file:///c:/Users/gupta/Documents/HARIOM/Personal_Finance_AI_Antigravity/.env)
- **Runtime Environment**: Python 3.13 (`.venv`) with packages `neo4j`, `python-dotenv`, `groq`
