# Personal Finance AI Assistant
### *Using Dynamic Knowledge Graphs, Deterministic Reasoning, and LLM-Based GraphRAG*

An explainable, research-grade, full-stack personal finance advisory system that combines **Neo4j Knowledge Graphs**, **Deterministic Mathematical Computation**, **GraphRAG Subgraph Traversal**, and **Grounded LLM Explanations**.

---

## 🌟 Key Architecture & Contributions

```text
User Question / Natural Language Ingestion
                   ↓
   Advanced NLU (Rules + LLM Fallback Entity Extractor)
                   ↓
   Dynamic Knowledge Graph (Neo4j - Isolated DB)
                   ↓
   Targeted Subgraph Retrieval (GraphRAG)
                   ↓
   Deterministic Financial Engine (Python Source of Truth)
                   ↓
   Structured Verifiable Evidence (Fact/Math/Source Tracking)
                   ↓
   Grounded LLM Response Engine (Strict ₹ Currency & Zero Math Hallucination)
                   ↓
   FastAPI REST API (Port 8000) ↔ React Frontend Dashboard (Port 3000)
```

1. **Zero Arithmetic Hallucination**: The LLM is never permitted to perform financial arithmetic or act as the source of truth. All calculations (savings rate, emergency runway, purchase safety, debt-to-income) are executed deterministically in Python.
2. **Dynamic Knowledge Graph**: Real-time transaction ingestion via natural language (e.g., *"I spent ₹5,000 on groceries today"*) automatically mutates graph nodes, updates account balances, and immediately recalculates all financial metrics.
3. **GraphRAG Subgraph Traversal**: Selectively extracts the exact subgraphs needed for a given intent rather than dumping flat text or full databases into prompt contexts.
4. **Transparent Evidence Cards**: Every answer is accompanied by verifiable, node-level evidence cards tracking facts, formulas, and sources.
5. **Strict Currency Integrity**: Enforces complete preservation of Indian Rupee (`₹`) denominations with zero currency drift.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Neo4j Desktop or Server (running locally on `neo4j://127.0.0.1:7687`)

### 2. Environment Configuration
The `.env` file at the root contains:
```env
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=finance-ai-antigravity
GROQ_API_KEY=your_groq_api_key
```

### 3. Reset / Seed Baseline Graph
```powershell
& ".\.venv\Scripts\python.exe" -m backend.scripts.seed_db
```

### 4. Run Interactive CLI Assistant
```powershell
& ".\.venv\Scripts\python.exe" run_cli.py
```

### 5. Start the FastAPI REST Backend
```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --port 8000
```
*API Documentation & Swagger UI:* [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 6. Start the React Frontend Dashboard
```powershell
cd frontend
npm run dev
```
*Frontend UI:* [http://localhost:3000](http://localhost:3000)

### 7. Run Full Automated Test Suite & Benchmark
```powershell
& ".\.venv\Scripts\python.exe" run_tests.py
& ".\.venv\Scripts\python.exe" backend/tests/test_evaluation_benchmark.py
```

---

## 📊 Documentation Index

- **[PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)**: Full project context, formulas, and schema mappings.
- **[DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md)**: Chronological phase-by-phase development and test logs.
- **[NEXT_STEPS.md](docs/NEXT_STEPS.md)**: Roadmap tracker and completed phase checklist.
- **[GRAPH_SCHEMA.md](docs/GRAPH_SCHEMA.md)**: Graph entities, properties, and relationship semantics.
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: In-depth system architecture and component designs.
- **[API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)**: Complete REST API specifications with payload examples.
- **[EVALUATION.md](docs/EVALUATION.md)**: Research benchmark comparing Conventional Vector RAG vs Proposed GraphRAG.
