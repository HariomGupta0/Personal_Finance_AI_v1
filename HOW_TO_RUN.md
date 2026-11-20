# 🚀 Quickstart & Complete Execution Guide

This document contains step-by-step instructions to set up, seed, run, and evaluate the **Personal Finance AI Assistant** (GraphRAG + Neo4j + FastAPI + React + Setu Account Aggregator).

---

## 📋 Prerequisites & Initial Setup

### 1. Requirements
* **Neo4j Database**: Desktop or Server running locally on `neo4j://127.0.0.1:7687` (Database name: `finance-ai-antigravity`).
* **Python**: 3.10+ with virtual environment (`.venv`).
* **Node.js**: v18+ for the React frontend.
* **Environment Variables (`.env`)**:
  * `GROQ_API_KEY`: For NLU, Vision, and LLM reasoning.
  * `SETU_CLIENT_ID`, `SETU_CLIENT_SECRET`, `SETU_PRODUCT_INSTANCE_ID`: For Live Sandbox Account Aggregator.

---

### 2. Installation (First Time Setup)

#### Step A: Backend Setup
Open Terminal / PowerShell in project root:
```powershell
# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install -r requirements.txt
```
*(Direct one-liner without activating):*
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

#### Step B: Frontend Setup
```powershell
cd frontend
npm install
cd ..
```

---

## ⚡ Step-by-Step Execution Guide (Manual Startup)

### STEP 1: Ensure Neo4j is Running
Open **Neo4j Desktop** or start your Neo4j service.
Verify it is active on `neo4j://127.0.0.1:7687` with credentials matching your `.env`.

---

### STEP 2: Seed / Reset Database to a Clean Slate
Whenever you want to reset the database to a fresh, clean demo state:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.scripts.seed_db
```
*(Direct one-liner:)*
```powershell
& ".\.venv\Scripts\python.exe" -m backend.scripts.seed_db
```
*Creates user `Rahul` with baseline accounts, salary, rent, loans, and categories ready for presentation.*

---

### STEP 3: Launch Full-Stack Application

Open two separate PowerShell terminal windows:

#### Terminal 1 — Start FastAPI Backend (Port 8000):
```powershell
$env:PYTHONPATH=".;.venv\Lib\site-packages"
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
* 🟢 **Backend Health Endpoint:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* 📚 **Interactive Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Terminal 2 — Start React Frontend (Port 3000):
```powershell
cd frontend
npm run dev
```
* 🖥️ **Interactive UI Dashboard:** [http://localhost:3000](http://localhost:3000)

---

## 🔑 Login Credentials

* **URL:** [http://localhost:3000](http://localhost:3000)
* **Default Demo User:** `Rahul`
* **Default Password:** `demo1234`

---

## 🏦 Bank Connection & Statement Upload Demonstration

### Method 1: Instant Connect via Setu Account Aggregator (Live Sandbox)
1. In the top navigation or banner, click **Connect Bank**.
2. Stay on the **Instant Connect (Setu AA)** tab.
3. Select your bank (e.g. **HDFC Bank** or **State Bank of India**).
4. Enter any 10-digit mobile number (e.g., `9876543210`).
5. Click **Verify & Request Consent** — the app fetches a live OAuth 2.0 token from Setu and initializes consent with Setu Sandbox.
6. Enter Sandbox Test OTP: **`123456`**.
7. Click **Authorize & Sync Data** — transactions are decrypted, normalized, deduplicated via SHA-256, and linked into the Neo4j Knowledge Graph.

---

### Method 2: Smart Statement Upload (PDF with Password Decryption)
1. Click **Connect Bank** and switch to the **Statement Upload (PDF / CSV)** tab.
2. Drag and drop any statement from the [`demo_statements/pdfs/`](demo_statements/pdfs/) folder.
3. If using an encrypted statement, enter the corresponding PAN password from the table below:

#### Demo Statement Profiles & Passwords Reference:
All generated files are stored in [`demo_statements/`](demo_statements/):

| Profile Name | Bank & Theme | Lifestyle Persona | PDF Password (PAN) | Sample Statement File |
| :--- | :--- | :--- | :---: | :--- |
| **Rahul Sharma** | **HDFC Bank** (Navy) | Tech Lead: ₹95k salary, Zerodha SIP, Rent, Swiggy, Uber | `RAHUL1234S` | `1_rahul_sharma_hdfc_password_protected.pdf` |
| **Priya Nair** | **ICICI Bank** (Maroon) | Homemaker: Family budget, BigBasket, DMart, School fees | `PRIYA1234N` | `2_priya_nair_icici_password_protected.pdf` |
| **Arjun Mehta** | **SBI** (Blue/Green) | Student / Intern: ₹18k stipend, micro UPI spends, Canteen | `ARJUN1234M` | `3_arjun_mehta_state_password_protected.pdf` |
| **Sunita Devi** | **Axis Bank** (Burgundy)| Freelancer: Irregular cashflow, fabric vendors, BlueDart | `SUNIT1234D` | `4_sunita_devi_axis_password_protected.pdf` |
| **Ramesh Iyer** | **SBI** (Classic Blue) | Pensioner: ₹38k pension, Apollo Pharmacy, PathLabs, TNEB | `RAMES1234I` | `5_ramesh_iyer_state_password_protected.pdf` |

*(Unencrypted versions for all profiles are also available in `demo_statements/pdfs/` for instant 1-click loading without a password).*

4. Click **Parse Statement** — view the live table preview with Date, Clean Payee, Category badge, and ₹ Amount.
5. Click **Confirm & Save to Graph** — transactions immediately update all dashboard charts and AI insights.

---

### Method 3: Receipt / Screenshot Image OCR Extraction
1. Navigate to **Import Transactions** in the navigation bar.
2. Select **Receipt / Screenshot**.
3. Upload any receipt or UPI screenshot image (JPEG, PNG).
4. Groq Vision (`qwen/qwen3.8-27b`) extracts date, merchant, ₹ amount, and category.
5. Review in the side-by-side editing workbench and click **Confirm Import**.

---

## 🛠️ Utility Scripts

### Regenerate All 20 Demo Statements (PDFs + CSVs):
```powershell
& ".\.venv\Scripts\python.exe" backend/scripts/generate_demo_statements.py
```

### Run Automated Unit Tests:
```powershell
& ".\.venv\Scripts\python.exe" -m pytest backend/tests/unit/test_setu_and_onboarding.py
```

### Run 10-Scenario Research Evaluation Benchmark:
```powershell
& ".\.venv\Scripts\python.exe" backend/tests/test_evaluation_benchmark.py
```

---

## 🎓 Viva Defense: Key Architecture & Questions

### Q1: "How does bank statement parsing and categorization work?"
> *"We use a **hybrid deterministic-first architecture**:
> 1. **In-Memory Decryption:** Password-protected PDFs are decrypted in an in-memory byte stream via `pypdf` without saving unprotected files to disk.
> 2. **Merchant Normalization:** We strip payment routing noise (e.g. `UPI/DR/123/SWIGGY/okhdfc`) into clean canonical payees (`Swiggy`).
> 3. **4-Tier Categorization:** Evaluates direction, high-confidence known merchant dictionaries, and keyword rules with deterministic confidence scoring.
> 4. **Transfer Detection:** Intra-batch and retroactive algorithms identify self-transfers to prevent double-counting expenses before writing to Neo4j."*

### Q2: "Why GraphRAG (Neo4j) instead of standard Vector RAG or SQL?"
> *"Financial health is fundamentally multi-hop and relational. Vector RAG stores unstructured text chunks and hallucinates math. Relational SQL struggles with dynamic multi-hop queries across accounts, loans, and categories.
> Neo4j models transactions as an interconnected knowledge graph:
> `(User)-[:HAS_ACCOUNT]->(Account)-[:MADE_TRANSACTION]->(Transaction)-[:IN_CATEGORY]->(Category)`.
> Our deterministic Python engine computes 100% accurate financial metrics, while the LLM acts purely as an explainer grounded in verified graph evidence cards."*

### Q3: "How is Account Aggregator (AA) integrated?"
> *"We implement the RBI Account Aggregator protocol via Setu's v2 REST APIs using OAuth 2.0 Bearer authentication. When a user authorizes consent via OTP, encrypted financial data is retrieved from Financial Information Providers (FIPs) and ingested directly into the user's graph twin."*
