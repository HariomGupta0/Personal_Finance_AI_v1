# 🚀 Quickstart & Complete Execution Guide

This document contains step-by-step instructions to set up, seed, run, and evaluate the **Personal Finance AI Assistant** (GraphRAG + Neo4j + FastAPI + React).

---

## 📋 Prerequisites & Initial Setup

### 1. Requirements
* **Neo4j Database**: Desktop or Server running locally on `neo4j://127.0.0.1:7687` (Database name: `finance-ai-antigravity`).
* **Python**: 3.10+ with virtual environment (`.venv`).
* **Node.js**: v18+ for the React frontend.
* **Groq API Key**: Provided in `.env` (`GROQ_API_KEY`) for NLU & Vision processing.

---

### 2. Installation (First Time Setup)

#### Step A: Install Backend Dependencies
Open Terminal / PowerShell in project root:
```powershell
# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install required Python packages
python -m pip install -r requirements.txt
```

*(Alternative single-line command without activation)*:
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

#### Step B: Install Frontend Dependencies
```powershell
cd frontend
npm install
cd ..
```

---

## ⚡ Step-by-Step Execution Guide

### STEP 1: Ensure Neo4j is Running
Open **Neo4j Desktop** or start your Neo4j service, ensuring it is listening at `neo4j://127.0.0.1:7687`.

---

### STEP 2: Seed / Reset Baseline Financial Database
Populate Neo4j with clean demo financial data (accounts, income, loans, EMIs, expenses, emergency goals):

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.scripts.seed_db
```
*(One-liner:)*
```powershell
& ".\.venv\Scripts\python.exe" -m backend.scripts.seed_db
```

---

### STEP 3: Launch the Full-Stack Web Application

#### Terminal 1 — Start FastAPI REST Backend (Port 8000):
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```
* 🟢 **Backend Health Endpoint:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* 📚 **Interactive Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Terminal 2 — Start React Frontend Dashboard (Port 3000):
```powershell
cd frontend
npm run dev
```
* 🖥️ **Interactive UI Dashboard:** [http://localhost:3000](http://localhost:3000)

---

## 🔑 Application Credentials & Access

* **URL:** [http://localhost:3000](http://localhost:3000)
* **Demo User:** `Rahul`
* **Demo Password:** `demo1234`

---

## 📷 How to Use Receipt / Screenshot Image Extraction

1. Open the UI Dashboard at [http://localhost:3000](http://localhost:3000) and log in.
2. Navigate to **Import Transactions** in the sidebar.
3. Switch tab from **CSV Bank Statement** to **Receipt / Screenshot**.
4. Drag & drop or upload any transaction image (JPEG, PNG, WebP) such as a UPI receipt or invoice.
5. The backend uses Groq Vision (`qwen/qwen3.8-27b`) to parse the date, merchant, amount (in ₹), payment status, and category.
6. Review the extracted fields in the interactive form and click **Confirm Import** to update your financial graph in real time.

---

## 🧪 Running Automated Tests & Evaluation Benchmarks

#### Run Full Test Suite (4 Suites: Environment + Graph CRUD + API + Research Benchmark):
```powershell
.\.venv\Scripts\Activate.ps1
python run_tests.py
```

#### Run 10-Scenario Research Evaluation Benchmark Only:
```powershell
.\.venv\Scripts\Activate.ps1
python backend/tests/test_evaluation_benchmark.py
```

#### Run Interactive Console CLI Assistant:
```powershell
.\.venv\Scripts\Activate.ps1
python run_cli.py
```

---

## 🎓 Viva Defense Notes: Architecture & Key Questions

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

### Q4: "How does receipt image extraction work?"
> **Answer:**
> *"Image upload POST requests to `/api/import/image` encode raw image bytes into base64 and pass them to Groq's multimodal vision model (`qwen/qwen3.8-27b`). Structured JSON extraction parses merchant, date, amount, direction, and status. It is then validated by Python heuristics, deduplicated against Neo4j, and presented to the user for review before graph mutation."*
