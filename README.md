# Personal Finance AI Assistant
### *Using Dynamic Knowledge Graphs, Deterministic Reasoning, and LLM-Based GraphRAG*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph%20Database-008CC1.svg)](https://neo4j.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF.svg)](https://vitejs.dev/)
[![Account Aggregator](https://img.shields.io/badge/RBI%20AA-Setu%20v2%20OAuth2.0-10B981.svg)](https://setu.co/)

An explainable, research-grade, full-stack personal finance advisory platform. It integrates the **RBI Account Aggregator framework (via Setu)**, **in-memory encrypted bank statement PDF parsing**, **Neo4j Property Graphs**, **Deterministic Financial Arithmetic (Paise Precision)**, and **GraphRAG Subgraph Traversal** with grounded LLM reasoning.

---

## 🌟 Key Architecture & Capabilities

```text
               ┌────────────────────────────────────────────────────────┐
               │              MULTI-CHANNEL DATA INGESTION              │
               │                                                        │
               │  1. Live Account Aggregator (Setu v2 OAuth 2.0)        │
               │  2. Password-Protected PDF Statements (In-Memory AES)   │
               │  3. CSV / TSV Bank Statement Uploads                   │
               │  4. Receipt & UPI Screenshots (Multimodal Groq Vision) │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │          INGESTION & CLEANING PIPELINE                 │
               │                                                        │
               │  • Merchant Normalizer (cleans UPI/POS/NEFT noise)     │
               │  • 4-Tier Categorizer (Rules + Known Brands + Keywords)│
               │  • Internal Transfer Detector (prevents double-counting)│
               │  • SHA-256 Fingerprint Deduplication                   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │             NEO4J PROPERTY KNOWLEDGE GRAPH             │
               │  (:User)-[:HAS_ACCOUNT]->(:Account)-[:MADE_TXN]->      │
               │  (:Transaction)-[:IN_CATEGORY]->(:Category)            │
               └───────────────┬────────────────────────┬───────────────┘
                               │                        │
                               ▼                        ▼
               ┌────────────────────────┐      ┌────────────────────────┐
               │ DETERMINISTIC ENGINE   │      │ GRAPHRAG RETRIEVAL     │
               │ (Paise-Precision Math) │      │ • Subgraph Traversal   │
               │ • 50/30/20 Budgeting   │      │ • Evidence Card Builder│
               │ • Emergency Runway     │      │ • XML Injection Guard  │
               │ • Debt Snowball/Avlnch │      │ • Grounded LLM Response│
               │ • Health Score (0-100) │      │   (Strict ₹ Currency)  │
               └───────────────┬────────┘      └────────┬───────────────┘
                               │                        │
                               └───────────┬────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │          FASTAPI BACKEND ↔ REACT 18 VITE UI           │
               │  • Real-time Financial Dashboard & KPI Metrics         │
               │  • Instant Bank Connect & Statement Upload Modal       │
               │  • Interactive AI Financial Twin Drawer                │
               │  • 5 Lifestyle Demo Profiles (Rahul, Priya, Arjun,...) │
               └────────────────────────────────────────────────────────┘
```

1. **Zero Arithmetic Hallucination**: The LLM is strictly prohibited from performing financial calculations. All math (50/30/20 budget allocations, runway, debt payoff schedules, and financial health scores) is executed deterministically in Python using integer paise arithmetic.
2. **Dual-Path Bank Ingestion**:
   - **Automated**: Real-time consent-driven bank sync via Setu Account Aggregator (OAuth 2.0 with RS256 token caching and ReBIT-compliant v2 consent routing).
   - **Manual Fallback**: Drag-and-drop Indian bank e-statement PDF parser supporting in-memory AES decryption (PAN / DOB passwords) and multi-line wrapped UPI extraction.
3. **Intelligent Narration Cleaning & Transfer Detection**:
   - `merchant_normalizer.py`: Strips banking routing noise (`UPI/DR/603207903267/SWIGGY/okhdfcbank/Order` $\rightarrow$ `Swiggy`).
   - `transfer_detector.py`: Detects intra-batch and retroactive self-transfers (e.g. Bank $\rightarrow$ Broker or Account A $\rightarrow$ B) so they are **not double-counted as expenses**.
4. **Targeted GraphRAG Subgraph Traversal**: Selectively extracts the exact subgraphs needed for a specific intent rather than dumping flat text or monolithic tables into LLM contexts.
5. **Defense-in-Depth & Strict Currency Integrity**: XML boundary isolation prevents prompt injection; all amounts strictly enforce Indian Rupee (`₹`) denomination.

---

## 📂 Project Structure

```text
Personal_Finance_AI_FYP/
├── backend/
│   ├── app/
│   │   ├── api/                      # REST Endpoints
│   │   │   ├── assistant.py          # AI Financial Twin & GraphRAG Chat
│   │   │   ├── auth.py               # Session Cookie Authentication & Onboarding
│   │   │   ├── finance.py            # Financial KPIs, 50/30/20, Health Score
│   │   │   ├── import_api.py         # CSV, PDF, OCR & Setu AA Ingestion
│   │   │   └── transactions.py       # Transaction CRUD & Ledger Operations
│   │   ├── core/                     # Foundational Core Modules
│   │   │   ├── config.py             # App Configuration & Environment Settings
│   │   │   └── money.py              # Integer Paise Arithmetic (Normalize & Convert)
│   │   ├── database/                 # Graph Storage Layer
│   │   │   └── neo4j_service.py      # Neo4j Driver, Cypher Queries, CRUD & Indexes
│   │   ├── engine/                   # Deterministic Computational Engine
│   │   │   ├── financial_engine.py   # Savings rate, DTI, Runway, Health Score
│   │   │   ├── plan_generator.py     # 50/30/20 Plan & Optimization Recommendations
│   │   │   └── purchase_evaluator.py # Purchase safety evaluator & risk scoring
│   │   ├── nlu/                      # Natural Language Understanding
│   │   │   ├── question_parser.py    # Intent Classifier & Entity/Date Extraction
│   │   │   └── transaction_extractor.py # Narration Heuristics & RegEx
│   │   ├── rag/                      # Graph Retrieval-Augmented Generation
│   │   │   ├── graph_rag.py          # Subgraph Traversal & Context Construction
│   │   │   └── prompt_registry.py    # Versioned System Prompts & XML Tags
│   │   └── services/                 # Business & Integration Services
│   │       ├── csv_parser.py         # Robust CSV / TSV Bank Statement Parser
│   │       ├── fingerprint.py        # Deterministic SHA-256 Deduplication
│   │       ├── image_extractor.py    # Groq Vision Multimodal Receipt OCR
│   │       ├── import_pipeline.py    # Validation, Normalization & Dedup Engine
│   │       ├── llm_service.py        # Async LLM Interface with Circuit Breaker
│   │       ├── merchant_normalizer.py# UPI/POS Channel Detector & 4-Tier Categorizer
│   │       ├── pdf_parser.py         # In-Memory PDF Decryption & Multi-Line Extractor
│   │       ├── setu_client.py        # Setu Account Aggregator v2 OAuth 2.0 Client
│   │       └── transfer_detector.py  # Intra-batch & Retroactive Transfer Detection
│   ├── scripts/
│   │   ├── generate_demo_statements.py # Generator for 20 Indian Statement PDFs/CSVs
│   │   └── seed_db.py                # Graph Baseline Seeder (User Rahul)
│   ├── tests/                        # Comprehensive Test Suites
│   │   ├── test_evaluation_benchmark.py # 24-Scenario Research Evaluation
│   │   └── unit/
│   │       └── test_setu_and_onboarding.py # Setu OAuth & Onboarding Unit Tests
│   └── main.py                       # FastAPI Application Entrypoint
├── demo_statements/                  # Demo Datasets for Presentation & Viva
│   ├── pdfs/                         # 10 Indian Bank Statement PDFs (5 Open, 5 Encrypted)
│   │   ├── 1_rahul_sharma_hdfc_3_months.pdf (HDFC - Open)
│   │   ├── 1_rahul_sharma_hdfc_password_protected.pdf (Password: RAHUL1234S)
│   │   ├── 2_priya_nair_icici_3_months.pdf (ICICI - Open)
│   │   ├── 2_priya_nair_icici_password_protected.pdf (Password: PRIYA1234N)
│   │   ├── 3_arjun_mehta_state_3_months.pdf (SBI - Open)
│   │   ├── 3_arjun_mehta_state_password_protected.pdf (Password: ARJUN1234M)
│   │   ├── 4_sunita_devi_axis_3_months.pdf (Axis - Open)
│   │   ├── 4_sunita_devi_axis_password_protected.pdf (Password: SUNIT1234D)
│   │   ├── 5_ramesh_iyer_state_3_months.pdf (SBI - Open)
│   │   └── 5_ramesh_iyer_state_password_protected.pdf (Password: RAMES1234I)
│   ├── csvs/                         # 10 Matching CSV Datasets (90-Day & 60-Day)
│   └── README_DEMO_DATASETS.md       # Profile & Password Cheatsheet
├── docs/                             # In-Depth Documentation
│   ├── API_DOCUMENTATION.md          # REST API Specification
│   ├── ARCHITECTURE.md               # Deep Architectural Design
│   ├── GRAPH_SCHEMA.md               # Neo4j Graph Data Model & Cypher Schema
│   ├── HOW_IT_WORKS.md               # End-to-End Functional Walkthrough
│   └── PROJECT_CONTEXT.md            # Comprehensive Project Reference & Formats
├── frontend/                         # Modern React 18 + Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── AssistantChat.jsx     # Conversational Financial Advisor Drawer
│   │   │   ├── ConnectBankModal.jsx  # Dual-Tab Modal (Setu AA & PDF Upload)
│   │   │   ├── ExpenseAnalytics.jsx  # Categorical Spends & 50/30/20 Charts
│   │   │   ├── FinancialPlan.jsx     # Collapsible Budget & Optimization Plan
│   │   │   ├── GoalManager.jsx       # Emergency Fund & Savings Target Tracker
│   │   │   ├── ImportManager.jsx     # Data Ingestion & OCR Editing Workbench
│   │   │   ├── KPICards.jsx          # Top Metrics (Net Savings, Runway, DTI)
│   │   │   ├── LoginScreen.jsx       # User Authentication Screen
│   │   │   ├── OnboardingWizardModal.jsx # Multi-Step New User Setup Flow
│   │   │   └── TransactionManager.jsx# Real-time Filterable Transaction Ledger
│   │   ├── App.jsx                   # Master Application State & View Routing
│   │   └── index.css                 # Dark Fintech Theme & Modern UI System
│   ├── package.json                  # Frontend Dependencies
│   └── vite.config.js                # Vite Build & Proxy Configuration
├── HOW_TO_RUN.md                     # Step-by-Step Manual Execution & Viva Guide
└── requirements.txt                  # Python Backend Dependencies
```

---

## 🚀 Quickstart & How to Run

For complete instructions, refer to **[`HOW_TO_RUN.md`](HOW_TO_RUN.md)**.

### 1. Prerequisites
* Python 3.10+ in `.venv`
* Node.js 18+ and npm
* Neo4j Database running locally on `neo4j://127.0.0.1:7687`

### 2. Reset / Seed Baseline Graph
```powershell
& ".\.venv\Scripts\python.exe" -m backend.scripts.seed_db
```

### 3. Launch Backend & Frontend

#### Terminal 1 — FastAPI Backend (Port 8000):
```powershell
$env:PYTHONPATH=".;.venv\Lib\site-packages"
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
* Interactive Swagger Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Terminal 2 — React Frontend (Port 3000):
```powershell
cd frontend
npm run dev
```
* Dashboard URL: [http://localhost:3000](http://localhost:3000)
* Default Credentials: User: `Rahul` | Password: `demo1234`

---

## 👥 Demo Profiles & Statement Datasets

We bundle **10 Indian bank statements and 10 CSVs** representing **5 distinct lifestyle personas** to prove the system handles diverse real-world use cases:

| # | Profile Name | Bank | Lifestyle / Persona | PDF Password (PAN) | 90D Txns | Sample PDF File |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- |
| **1** | **Rahul Sharma** | HDFC Bank | Tech Lead (₹95k salary, Zerodha SIP, Rent, Swiggy) | `RAHUL1234S` | 85 | `1_rahul_sharma_hdfc_password_protected.pdf` |
| **2** | **Priya Nair** | ICICI Bank | Homemaker (Family budget, BigBasket, School fees) | `PRIYA1234N` | 85 | `2_priya_nair_icici_password_protected.pdf` |
| **3** | **Arjun Mehta** | SBI | Student / Intern (₹18k stipend, micro UPI, Canteen) | `ARJUN1234M` | 79 | `3_arjun_mehta_state_password_protected.pdf` |
| **4** | **Sunita Devi** | Axis Bank | Freelancer (Irregular income, fabric vendors, Canva) | `SUNIT1234D` | 88 | `4_sunita_devi_axis_password_protected.pdf` |
| **5** | **Ramesh Iyer** | SBI | Pensioner (Central Pension, Apollo Pharmacy, TNEB) | `RAMES1234I` | 82 | `5_ramesh_iyer_state_password_protected.pdf` |

*All files reside in [`demo_statements/`](demo_statements/). Unencrypted versions are also provided for instant 1-click loading without typing a password.*

---

## 🧪 Testing & Research Evaluation

```powershell
# Run Unit Tests (Setu AA, Onboarding, PDF Decryption)
& ".\.venv\Scripts\python.exe" -m pytest backend/tests/unit/test_setu_and_onboarding.py

# Run Full 24-Scenario Research Evaluation Benchmark
& ".\.venv\Scripts\python.exe" backend/tests/test_evaluation_benchmark.py
```

---

## 📚 Documentation Index

* **[HOW_TO_RUN.md](HOW_TO_RUN.md)**: Complete manual startup guide, Setu AA testing, and viva defense notes.
* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: In-depth system architecture, security boundary, and data pipeline designs.
* **[docs/GRAPH_SCHEMA.md](docs/GRAPH_SCHEMA.md)**: Neo4j schema, relationship semantics, and Cypher query templates.
* **[docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)**: Full REST API specification with request/response schemas.
* **[demo_statements/README_DEMO_DATASETS.md](demo_statements/README_DEMO_DATASETS.md)**: Reference sheet for all demo datasets and passwords.
