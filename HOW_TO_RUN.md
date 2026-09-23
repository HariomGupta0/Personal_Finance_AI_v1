# 🚀 Quickstart & Execution Guide

This document contains all execution commands, project architecture summary, and viva defense notes for the **Personal Finance AI Assistant**.

---

## 📋 Prerequisites
1. **Neo4j Database**:
   - Must be running on `neo4j://127.0.0.1:7687` (Database: `finance-ai-antigravity`).
   - Start it from **Neo4j Desktop** before running backend or benchmarks.
2. **Python Virtual Environment**:
   - Uses `.venv` in the project root containing all dependencies (`groq`, `neo4j`, `fastapi`, `uvicorn`, etc.).
3. **Node.js**:
   - Required for the React frontend (`frontend/`).

---

## ⚡ Execution Commands

### 1. Reset / Seed Baseline Graph Database
Populate Neo4j with clean demo financial data (accounts, loans, EMIs, expenses, emergency goals):
```powershell
.venv\Scripts\Activate.ps1
python -m backend.scripts.seed_db
```
*(Alternative one-line command without activation:)*
```powershell
& ".\.venv\Scripts\python.exe" -m backend.scripts.seed_db
```

---

### 2. Run Full-Stack Web Application (Recommended for Demo)

#### Terminal 1 — Start FastAPI REST Backend (Port 8000):
```powershell
.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```
- **Backend API & Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Terminal 2 — Start React Frontend Dashboard (Port 3000):
```powershell
cd frontend
npm run dev
```
- **Interactive UI Dashboard:** [http://localhost:3000](http://localhost:3000)

---

### 3. Run Interactive Terminal CLI Assistant
To test natural language advisory directly in your console:
```powershell
.venv\Scripts\Activate.ps1
python run_cli.py
```
**Example Prompts to Try:**
- `Can I spend ₹15,000 on a phone?` (Evaluates affordability against EMI and 3-month emergency fund)
- `What is my savings rate?` (Calculates deterministic savings percentage)
- `I spent ₹3,000 on groceries today` (Dynamically mutates graph and recalculates balances)
- `How many months can I survive on my runway?` (Calculates liquid runway)
- `How much debt do I have?` (Evaluates loans and DTI ratio)

---

### 4. Run Automated Evaluation & Test Suite

#### Run the 10-Scenario Research Benchmark:
```powershell
.venv\Scripts\Activate.ps1
python backend/tests/test_evaluation_benchmark.py
```

#### Run All 4 Test Suites (Environment + Neo4j CRUD + API Endpoints + Benchmark):
```powershell
.venv\Scripts\Activate.ps1
python run_tests.py
```

---

## 🎓 Viva Cheat Sheet: Key Questions & Answers

### Q1: "On what model did you train your chatbot?"
> **Answer:**
> *"We did **not train or fine-tune** the foundation LLM. In personal finance, LLMs hallucinate arithmetic and cannot maintain real-time dynamic balances.
> Instead, we used a **Decoupled GraphRAG Architecture**:
> 1. **Neo4j Knowledge Graph** holds verified relational facts (Accounts, EMIs, Expenses).
> 2. A **Deterministic Python Engine** acts as the single source of truth for all mathematical calculations (100% precision).
> 3. An open-weights LLM (served via **Groq**) is used strictly for **intent recognition and natural language explanation**, grounded entirely in verified evidence cards with strict ₹ currency preservation."*

---

### Q2: "What is your GraphRAG structure?"
> **Answer:**
> *"Our GraphRAG pipeline operates in 5 deterministic stages:
> 1. **NLU & Intent Extraction:** Classifies intent (`PURCHASE_SAFETY`, `SAVINGS_ANALYSIS`, etc.) and extracts entities/amounts.
> 2. **Targeted Subgraph Retrieval:** Runs targeted Cypher queries in Neo4j to retrieve only the relevant interconnected nodes (e.g. Account balance + Pending EMIs + 3-month expense history).
> 3. **Deterministic Math Reasoning:** Computes runway, risk level, or safe-to-spend balance in Python.
> 4. **Verifiable Evidence Construction:** Tags every number with its source database node (e.g. `Account.balance`, `EMI.amount`).
> 5. **Grounded LLM Generation:** Prompt constraints enforce 0 arithmetic by the LLM, strict preservation of `₹`, and structured 4-part explanations."*

---

### Q3: "Why GraphRAG instead of standard Vector RAG?"
> **Answer:**
> *"Conventional Vector RAG stores flat text chunks and fails on multi-hop relational dependencies (e.g. connecting liquid balance to upcoming loan EMIs and emergency buffers). GraphRAG natively traverses these multi-hop relationships in Neo4j and updates instantly when new transactions occur without needing vector re-indexing."*

---

### Q4: "Where are the evaluation results?"
> - Test script: `backend/tests/test_evaluation_benchmark.py`
> - Research report: `docs/EVALUATION.md`
> - Benchmarked on 10 diverse queries: **+55% improvement in math accuracy**, **100% currency preservation**, and **zero arithmetic hallucinations**.
