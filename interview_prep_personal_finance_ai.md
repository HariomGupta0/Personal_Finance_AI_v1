# 🎯 Interview Prep: Personal Finance AI Assistant
### Complete Cheat Sheet for Infosys Systems Engineer Interview

---

## 1. The 60-Second Elevator Pitch

> *"My final year project is a **Personal Finance AI Assistant**. The problem I solved is that AI chatbots hallucinate when doing financial math — they give wrong numbers, miss pending loan EMIs, and even convert ₹ to $.*
>
> *So I designed a **three-layer decoupled architecture**:*
> 1. *A **Neo4j graph database** stores all financial entities — Users, Accounts, Transactions, Loans, EMIs, Goals — as interconnected nodes.*
> 2. *A **deterministic Python engine** performs all calculations — savings rate, emergency runway, purchase risk, debt-to-income — so there's zero chance of wrong numbers.*
> 3. *The **LLM** (via Groq API) is only used for understanding intent and explaining results in natural language. It never touches the math.*
>
> *I also built CSV bank statement import, receipt image OCR extraction, user authentication, and a React dashboard — all connected through a FastAPI REST backend."*

---

## 2. Architecture Deep Dive (Know This Cold)

```
User Input (Text / Image / CSV)
         ↓
┌─────────────────────────────┐
│  NLU Layer (question_parser) │  ← Rule-based first, LLM fallback
│  Intent + Entity Extraction  │
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│  GraphRAG (graph_rag.py)     │  ← Targeted Cypher subgraph retrieval
│  retrieve_subgraph()         │     (NOT full database dump)
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│  Financial Engine (Python)   │  ← Single source of truth for ALL math
│  Deterministic calculations  │     savings, runway, purchase safety, DTI
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│  Evidence Card Builder       │  ← Node-level facts with source citations
│  construct_evidence_payload()│
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│  LLM Explanation Generator   │  ← Strict prompt: preserve ₹, no math
│  prompt_builder.py           │
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│  FastAPI REST API (Port 8000)│  ← 6 routers: finance, transactions,
│  React Dashboard (Port 3000)│     goals, assistant, auth, import
└─────────────────────────────┘
```

### The 5 Stages of a Query (Memorize This)

| Stage | Module | What Happens |
|:------|:-------|:-------------|
| **1. NLU** | `question_parser.py` | Classifies intent (PURCHASE_SAFETY, SAVINGS_ANALYSIS, etc.) and extracts amount/category using regex rules → LLM fallback |
| **2. Subgraph Retrieval** | `graph_rag.py` → `neo4j_service.py` | Runs intent-specific Cypher queries to fetch ONLY relevant nodes (e.g., for purchase safety: Account balance + Pending EMIs + Monthly expenses) |
| **3. Deterministic Math** | `financial_engine.py` | Computes exact results using Python formulas — NO LLM math |
| **4. Evidence Construction** | `graph_rag.py` | Builds verifiable evidence cards with ₹ values and node-level source citations |
| **5. LLM Explanation** | `prompt_builder.py` → `llm_service.py` | Strict prompt constrains LLM to ONLY narrate the pre-computed evidence |

---

## 3. Knowledge Graph Schema (Draw This If Asked)

```
(:User) ──HAS_ACCOUNT──→ (:Account) ──MADE_TRANSACTION──→ (:Transaction) ──BELONGS_TO──→ (:Category)
  │
  ├──RECEIVED_INCOME──→ (:Income)
  │
  ├──HAS_LOAN──→ (:Loan) ──HAS_EMI──→ (:EMI)
  │
  └──HAS_GOAL──→ (:Goal)
```

**Node Properties:**
- **User**: `{id, username, name, password_hash, salt}`
- **Account**: `{id, bank, account_type, balance}`
- **Transaction**: `{id, description, amount, type (EXPENSE/INCOME), date}`
- **Category**: `{id, name}` — Housing, Food, Transport, Utilities, Shopping, Healthcare, Entertainment, Education
- **Income**: `{id, source, amount, date}`
- **Loan**: `{id, name, principal, outstanding}`
- **EMI**: `{id, amount, due_date, status (PENDING/PAID)}`
- **Goal**: `{id, name, target_amount, current_amount, target_date}`

---

## 4. Key Financial Formulas (The Engine)

### Savings Rate
```
Total Expenses = Sum of all EXPENSE transactions in the month
Savings = Total Income − Total Expenses
Savings Rate = (Savings / Total Income) × 100
```

### Emergency Fund
```
Recommended Fund = Monthly Expenses × 3
Shortfall = max(0, Recommended − Current Emergency Goal Amount)
```

### Purchase Safety Check (Most Important — They WILL Ask)
```
Balance After Purchase = Current Balance − Pending EMIs − Purchase Amount

Decision: SAFE if Balance After Purchase ≥ Emergency Requirement (3× monthly expenses)

Risk Classification:
  LOW:       Balance After Purchase ≥ 3× monthly expenses
  MEDIUM:    Monthly expenses ≤ Balance After Purchase < 3× monthly expenses
  HIGH:      0 < Balance After Purchase < Monthly expenses
  VERY_HIGH: Balance After Purchase ≤ 0
```

### Debt-to-Income (DTI) Ratio
```
DTI = (Monthly EMI / Total Monthly Income) × 100

Risk: LOW (≤20%), MODERATE (≤35%), HIGH (≤50%), CRITICAL (>50%)
```

### Financial Health Score (0–100)
```
Savings Score     = min(35, (savings_rate / 20) × 35)      — max 35 pts
Emergency Score   = min(35, (runway_months / 3) × 35)      — max 35 pts
Debt Score        = 30 pts if DTI ≤ 20%, 0 pts if DTI ≥ 50% — max 30 pts

Grade: A (≥85), B (≥70), C (≥50), D (<50)
```

---

## 5. Complete Feature List (What Your Project Has)

| Feature | How It Works |
|:--------|:-------------|
| **Conversational Q&A** | User types natural language → NLU parses intent → GraphRAG → Engine → LLM explanation |
| **Natural Language Ingestion** | "I spent ₹5,000 on groceries" → `transaction_extractor.py` extracts amount, category, date → creates graph node → updates balance |
| **CSV Bank Statement Import** | Upload CSV → `csv_parser.py` auto-maps columns (supports Indian bank formats) → dedup pipeline → user confirms → persisted to Neo4j |
| **Receipt/Screenshot OCR** | Upload image → Groq Vision API extracts transaction → pytesseract OCR fallback → user reviews → confirm to save |
| **Purchase Safety Analysis** | Checks balance, pending EMIs, and 3-month emergency buffer before recommending |
| **Savings Rate Analysis** | Monthly income vs expenses with percentage |
| **Emergency Runway** | How many months your balance can cover expenses (STRONG/HEALTHY/INSUFFICIENT/CRITICAL) |
| **Expense Breakdown** | Category-wise spending with percentages and top category |
| **Debt Burden Analysis** | DTI ratio with risk classification |
| **Financial Health Score** | Composite 0–100 score combining savings, runway, and debt |
| **User Authentication** | Signup/Login with PBKDF2 password hashing, HMAC-signed session cookies |
| **React Dashboard** | Interactive UI with expense charts, evidence cards, goal tracking |
| **Evidence Cards** | Every answer comes with verifiable facts linked to specific graph nodes |

---

## 6. Technical Q&A (Top 15 Questions They'll Ask)

### Q1: "Why Neo4j instead of MySQL or MongoDB?"
> Financial data is inherently relational — a User has Accounts, Accounts have Transactions, Transactions belong to Categories, Users have Loans with EMIs. In a relational DB, answering "get all pending EMIs across all loans for this user" requires multiple JOINs. In Neo4j, it's a single graph traversal:
> ```cypher
> MATCH (u:User {id: $user_id})-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI {status: 'PENDING'})
> RETURN l.name, e.amount, e.due_date
> ```
> This is faster and more intuitive for multi-hop queries.

### Q2: "What is GraphRAG? How is it different from normal RAG?"
> **Normal RAG:** Convert documents to vector embeddings → user query gets embedded → cosine similarity finds similar text chunks → chunks are stuffed into LLM prompt. Problem: loses relational structure.
>
> **GraphRAG (what I built):** User query → NLU detects intent → runs a *targeted Cypher query* to fetch only the relevant connected nodes (not the entire database). For example, for "Can I buy a phone for ₹15,000?", I only fetch: Account balance + Pending EMIs + Monthly expense transactions + Emergency goal. This is precise, fast, and structured.

### Q3: "How does the NLU/Intent Classification work?"
> Two-layer approach:
> 1. **Rule-based parser first** (`parse_question_rules`) — Uses regex patterns and keyword matching to classify into 10 intents (PURCHASE_SAFETY, SAVINGS_ANALYSIS, etc.) and extract amounts/categories. This is fast and deterministic.
> 2. **LLM fallback** (`parse_question_llm`) — If rules don't match, sends the question to Groq LLM with a structured JSON schema prompt. The LLM returns intent + entities as JSON.
>
> I always try rules first because they're faster, free, and predictable.

### Q4: "Why not let the LLM do the financial calculations?"
> Three critical reasons:
> 1. **LLMs hallucinate arithmetic** — ask GPT "45000 - 10000 - 15000" and it sometimes says 25000 or 30000.
> 2. **LLMs can't maintain state** — they don't know the user's current balance, pending EMIs, or monthly spending pattern unless we explicitly provide it.
> 3. **Auditability** — in finance, every number must be traceable. My Python engine produces a deterministic result that I can unit-test. LLM outputs are non-deterministic.

### Q5: "How does the image/OCR extraction work?"
> Three-tier approach:
> 1. **Primary:** Send the image as base64 to Groq's Vision API (tries multiple vision models as fallback).
> 2. **Fallback:** If Vision API fails, use pytesseract (local OCR) to extract text from the image, then send the text to a regular Groq text model for structured extraction.
> 3. **Output:** Returns a JSON with date, amount, merchant, direction (expense/income/refund), status, confidence level, and warnings.
> 4. **Safety:** Nothing is saved to the database until the user explicitly reviews and confirms the extracted data.

### Q6: "How does CSV parsing work?"
> The `csv_parser.py` supports multiple Indian and international bank CSV formats. It auto-maps columns using alias dictionaries — for example, it recognizes "Narration", "Particulars", and "Remarks" all as the description column. It handles separate Debit/Credit columns, combined Amount columns, and various date formats. If the mapping is ambiguous, it returns candidates for the user to choose rather than guessing.

### Q7: "How did you handle authentication?"
> - **Password hashing:** PBKDF2 with SHA-256, 100,000 iterations, random 16-byte salt per user
> - **Sessions:** HMAC-signed session tokens stored in HttpOnly cookies with configurable TTL
> - **Verification:** `hmac.compare_digest()` for timing-attack-resistant comparison
> - User data is stored in Neo4j itself as User nodes

### Q8: "What is your tech stack?"
> | Layer | Technology |
> |:------|:-----------|
> | Backend | Python 3.13, FastAPI, Uvicorn |
> | Database | Neo4j (Cypher query language) |
> | LLM | Groq API (open-source models) |
> | OCR | Groq Vision API + Pytesseract fallback |
> | Frontend | React (Vite), vanilla CSS |
> | Auth | PBKDF2 + HMAC session cookies |
> | Testing | Pytest, automated benchmark suite |

### Q9: "What is Cypher? Can you write a query?"
> Cypher is Neo4j's query language for graph databases (like SQL is for relational databases).
> ```cypher
> // Get all expense transactions for a user with their categories
> MATCH (u:User {id: "U001"})-[:HAS_ACCOUNT]->(a:Account)
>       -[:MADE_TRANSACTION]->(t:Transaction)-[:BELONGS_TO]->(c:Category)
> WHERE t.type = "EXPENSE"
> RETURN t.description, t.amount, c.name, t.date
> ORDER BY t.date DESC
> ```

### Q10: "How does the prompt builder prevent LLM hallucination?"
> The prompt has strict constraints:
> 1. **Never convert ₹ to $ or any other currency**
> 2. **Never modify numeric values** — preserve every number exactly as computed
> 3. **Never perform arithmetic** — only explain the pre-computed results
> 4. **Structured output format** — forced into 4 sections: Quick Take, The Numbers, Smart Insights, What To Do Next
> 5. The financial result dict is passed as "Verified Financial Analysis" — the LLM treats it as ground truth

### Q11: "Walk me through the purchase safety flow end-to-end"
> User asks: *"Can I spend ₹15,000 on a phone?"*
> 1. **NLU** → Detects intent: `PURCHASE_SAFETY`, extracts amount: `15000`
> 2. **Subgraph Retrieval** → Runs `get_purchase_context()` Cypher query → fetches Account(balance=₹45,000), Pending EMI(₹10,000), Monthly Transactions
> 3. **Financial Engine** → `check_purchase_safety(context, 15000)`:
>    - Balance after = 45000 − 10000 − 15000 = ₹20,000
>    - Emergency requirement = monthly_expenses × 3
>    - If ₹20,000 < emergency requirement → Decision: NOT_SAFE, Risk: HIGH
> 4. **Evidence Card** → Labels each value with its source node (Account.balance, EMI.amount, etc.)
> 5. **LLM Explanation** → Narrates the result naturally while preserving all ₹ values

### Q12: "What is the difference between GraphRAG subgraph retrieval methods?"
> Each intent fetches different nodes to minimize data:
> | Intent | What's Fetched |
> |:-------|:---------------|
> | PURCHASE_SAFETY | Accounts + Loans/EMIs + Transactions + Goals |
> | SAVINGS_ANALYSIS | Incomes + Transactions (no loans needed) |
> | EMERGENCY_FUND | Transactions + Goals (no income needed) |
> | DEBT_ANALYSIS | Loans/EMIs + Incomes (for DTI ratio) |
> | FINANCIAL_SUMMARY | Everything (comprehensive) |

### Q13: "How do you add a transaction via natural language?"
> User types: *"I spent ₹5,000 on groceries today"*
> 1. `transaction_extractor.py` → regex extracts amount (5000), infers category ("Food" from keyword "groceries"), parses date ("today")
> 2. `ingestion_service.py` → calls `neo4j_service.add_transaction()`
> 3. Neo4j Cypher → Creates Transaction node, links it to Account and Category, **atomically updates account balance** (`SET a.balance = a.balance - 5000`)
> 4. All financial metrics are instantly recalculated on next query

### Q14: "How does the balance stay consistent?"
> Balance updates are **atomic within the Cypher query itself**:
> ```cypher
> SET a.balance = a.balance + (CASE WHEN $type = 'INCOME' THEN $amount ELSE -$amount END)
> ```
> This runs in the same transaction as the node creation — no race conditions, no separate update step.

### Q15: "What would you improve if you had more time?"
> 1. **Multi-currency support** — currently only supports ₹ (INR)
> 2. **Bank API integration** — direct bank statement fetch via account aggregator APIs instead of manual CSV upload
> 3. **Budget planning module** — set monthly category budgets and get alerts when approaching limits
> 4. **Recurring transaction detection** — automatically identify monthly subscriptions and rent from transaction patterns

---

## 7. Walkthrough Example (Use If They Say "Show Me How It Works")

**Scenario:** User asks *"What is my savings rate?"*

```
INPUT:  "What is my savings rate?"

STEP 1 — NLU (question_parser.py):
  → Keyword "savings rate" matched
  → Intent: SAVINGS_ANALYSIS

STEP 2 — Subgraph Retrieval (graph_rag.py):
  → Calls db.get_savings_context("U001")
  → Cypher fetches: Incomes [₹60,000 salary] + Transactions [₹21,000 total expenses]

STEP 3 — Financial Engine:
  → total_income = ₹60,000
  → total_expenses = ₹21,000
  → savings = 60,000 − 21,000 = ₹39,000
  → savings_rate = (39,000 / 60,000) × 100 = 65%

STEP 4 — Evidence Card:
  [
    {"label": "Total Monthly Income",   "value": "₹60,000", "source": "Income.amount"},
    {"label": "Total Monthly Expenses", "value": "₹21,000", "source": "Transaction.amount"},
    {"label": "Net Monthly Savings",    "value": "₹39,000", "source": "Deterministic Math"},
    {"label": "Savings Rate",           "value": "65%",      "source": "Savings Formula"}
  ]

STEP 5 — LLM Explanation:
  "🎯 Great news! You're saving 65% of your income — ₹39,000 out of ₹60,000.
   That's well above the recommended 20% benchmark..."
```

---

## 8. API Endpoints (If They Ask About REST APIs)

| Method | Endpoint | Purpose |
|:-------|:---------|:--------|
| `POST` | `/api/auth/signup` | Create new user with PBKDF2 hashed password |
| `POST` | `/api/auth/login` | Authenticate and set session cookie |
| `POST` | `/api/auth/logout` | Clear session |
| `GET`  | `/api/auth/session` | Check current auth status |
| `POST` | `/api/finance/ask` | Main GraphRAG Q&A endpoint |
| `GET`  | `/api/finance/summary` | Full financial summary |
| `GET`  | `/api/transactions` | List transactions (paginated) |
| `POST` | `/api/transactions` | Add transaction |
| `PUT`  | `/api/transactions/{id}` | Update transaction |
| `DELETE` | `/api/transactions/{id}` | Delete transaction (restores balance) |
| `POST` | `/api/import/csv` | Upload bank statement CSV |
| `POST` | `/api/import/image` | Upload receipt image for OCR |
| `POST` | `/api/import/confirm` | Confirm and persist imported rows |

---

## 9. File Map (Know Where Everything Lives)

```
Personal_Finance_AI_FYP/
├── backend/
│   ├── main.py                          ← FastAPI app entry point (6 routers)
│   ├── config.py                        ← Environment variables loader
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py                  ← Signup/Login/Logout/Session
│   │   │   ├── finance.py               ← /ask (GraphRAG) + /summary
│   │   │   ├── transactions.py          ← CRUD for transactions
│   │   │   ├── goals.py                 ← Goal management
│   │   │   ├── assistant.py             ← Chat endpoint
│   │   │   └── import_api.py            ← CSV + Image upload + Confirm
│   │   ├── database/
│   │   │   └── neo4j_service.py         ← All Cypher queries + CRUD + Auth
│   │   ├── engine/
│   │   │   └── financial_engine.py      ← ALL financial formulas (373 lines)
│   │   ├── nlu/
│   │   │   ├── question_parser.py       ← Intent classification (rules + LLM)
│   │   │   └── transaction_extractor.py ← NL transaction parsing
│   │   ├── rag/
│   │   │   └── graph_rag.py             ← GraphRAG pipeline orchestrator
│   │   └── services/
│   │       ├── llm_service.py           ← Groq API wrapper
│   │       ├── prompt_builder.py        ← Strict LLM prompt template
│   │       ├── response_generator.py    ← Bridges prompt + LLM
│   │       ├── csv_parser.py            ← Bank statement CSV parser
│   │       ├── image_extractor.py       ← OCR + Vision extraction
│   │       ├── import_pipeline.py       ← Normalize + validate + dedup
│   │       └── ingestion_service.py     ← Transaction/Income ingestion
│   └── tests/                           ← Pytest test suite
├── frontend/
│   └── src/
│       ├── App.jsx                      ← Main React app
│       ├── components/                  ← Dashboard components
│       └── index.css                    ← Styling
└── README.md
```

---

## 10. Quick Confidence Boosters

### "What makes this project different from a typical chatbot?"
> *"Most chatbots dump everything into the LLM and hope for the best. Mine uses a 3-layer architecture where the database stores facts, Python computes math, and the LLM only explains. Every answer is traceable to specific graph nodes."*

### "What was the hardest bug you fixed?"
> *"Getting the account balance to stay consistent when transactions are added, updated, or deleted. I solved it by making balance updates atomic within the same Cypher query — the balance adjustment happens in the same database transaction as the node creation, so there's no window for inconsistency."*

### "Did you work alone or in a team?"
> *"I designed the architecture, wrote the backend (FastAPI, Neo4j Cypher queries, financial engine, NLU pipeline), and built the React frontend. I also wrote the automated test suite and benchmark evaluation."*

---

> [!TIP]
> **Practice the elevator pitch 3 times out loud before sleeping tonight. Say it standing up, looking at a mirror or webcam. Confidence comes from repetition.**

> [!IMPORTANT]
> **If you don't know an answer, say:** *"I haven't implemented that specific feature yet, but here's how I would approach it..."* — this shows problem-solving ability, which Infosys values more than memorized answers.
