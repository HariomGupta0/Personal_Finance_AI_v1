# Feature Ideation & Technical Specification
## Zero-Cold-Start Onboarding Wizard & Setu-Ready Bank Connect Hub

**Project:** Explainable Personal Finance AI Assistant  
**Date:** November 18, 2026  
**Status:** Approved for Implementation  
**Target Environment:** FastAPI (Backend) + Neo4j (Database) + React 18 / Vite (Frontend)

---

## 1. Executive Summary & Problem Statement

### 1.1 The "Cold-Start" Empty Screen Problem
When a first-time user registers in a personal finance application, their account balance is ₹0, transaction history is empty, and the financial graph has zero nodes. Consequently:
* Key Performance Indicator (KPI) cards show `NaN` or `0.0`.
* The emergency runway calculation cannot run.
* The conversational AI assistant answers: *"I have no financial records for you,"* resulting in immediate user disengagement.

### 1.2 The "Data Ingestion Friction" Dilemma
Manual entry of historical transactions is rejected by over 85% of real-world users. While traditional apps relied on dangerous credential screen-scraping (banned by RBI), modern Indian FinTech applications (CRED, Fold, Fi Money, Jupiter) use the **RBI Account Aggregator (AA)** framework to fetch verified statements in 10 seconds via phone number and OTP.

### 1.3 The Solution
We are building two complementary onboarding and ingestion features:
1. **The 60-Second Onboarding Wizard:** An immediate 3-question setup modal for new signups that sets up baseline income, liquid balance, and active debt in Neo4j, activating live calculations in under 1 second.
2. **The "Connect Bank" Modal (2 Tabs):**
   * **Tab 1 (Instant Connect):** Live Setu Account Aggregator integration with automatic local fallback resilience (Circuit Breaker).
   * **Tab 2 (Upload Statement):** Direct drag-and-drop CSV and encrypted PDF statement parser with password-unlock support.

---

## 2. Feature 1: The 60-Second Onboarding Wizard

### 2.1 User Experience Flow
```text
[ New User Sign Up ]
        │
        ▼
[ Auto-Detect: Transactions == 0 && OnboardingIncomplete ]
        │
        ▼
[ Onboarding Wizard Modal Opens ]
  ├── Slide 1: "What is your monthly net income?"
  │     └── [ ₹ 50,000 ] (Quick chips: ₹25k, ₹50k, ₹75k, ₹100k)
  │
  ├── Slide 2: "What is your current total liquid balance across banks?"
  │     └── [ ₹ 45,000 ] in [ HDFC Bank ▼ ]
  │
  ├── Slide 3: "Do you have any active loan EMIs?"
  │     └── Toggle: [ None ] or [ ₹ 8,500/month Car Loan ]
  │
  └── Live Preview: "Instant Estimate: ~2.1 Months Emergency Runway"
        │
        ▼
[ Click: "Generate My Financial Blueprint" ]
        │
        ▼
[ Backend bootstraps Neo4j -> Dashboard immediately lights up! ]
```

### 2.2 Backend API Specification: Bootstrap Endpoint
* **Route:** `POST /api/onboarding/bootstrap`
* **Authentication:** Mandatory HTTP-only session cookie (`user_id`).
* **Request Payload Schema:**
  ```json
  {
    "bank_name": "HDFC Bank",
    "liquid_balance_inr": 45000.0,
    "monthly_income_inr": 50000.0,
    "monthly_emi_inr": 8500.0,
    "loan_type": "PERSONAL"
  }
  ```
* **Response Payload Schema:**
  ```json
  {
    "status": "SUCCESS",
    "user_id": "U001",
    "onboarding_completed": true,
    "accounts_created": 1,
    "initial_metrics": {
      "liquid_balance_inr": 45000.0,
      "monthly_income_inr": 50000.0,
      "monthly_emi_inr": 8500.0,
      "dti_ratio_pct": 17.0,
      "estimated_runway_months": 2.14,
      "health_score": 68.5
    }
  }
  ```

### 2.3 Neo4j Database Mutation Cypher
```cypher
// 1. Update User Onboarding State
MATCH (u:User {id: $user_id})
SET u.onboarding_completed = true,
    u.updated_at = datetime()

// 2. Upsert Primary Liquid Account
MERGE (a:Account {id: $user_id + '_ACC_PRIMARY'})
ON CREATE SET 
    a.user_id = $user_id,
    a.bank_name = $bank_name,
    a.type = 'SAVINGS',
    a.balance_paise = $balance_paise,
    a.opened_date = date(),
    a.status = 'ACTIVE'
ON MATCH SET
    a.balance_paise = $balance_paise

MERGE (u)-[:HAS_ACCOUNT]->(a)

// 3. Upsert Monthly Income Node
MERGE (i:Income {id: $user_id + '_INC_PRIMARY'})
SET i.user_id = $user_id,
    i.amount_paise = $income_paise,
    i.source = 'Primary Income',
    i.frequency = 'MONTHLY',
    i.date = date()
MERGE (u)-[:RECEIVED_INCOME]->(i)

// 4. Optional Active Loan & EMI Node
FOREACH (_ IN CASE WHEN $emi_paise > 0 THEN [1] ELSE [] END |
    MERGE (l:Loan {id: $user_id + '_LOAN_PRIMARY'})
    SET l.user_id = $user_id,
        l.type = $loan_type,
        l.monthly_emi_paise = $emi_paise,
        l.status = 'ACTIVE'
    MERGE (u)-[:HAS_LOAN]->(l)
)
```

---

## 3. Feature 2: Connect Bank Modal (2-Tab Hub)

### 3.1 Tab 1 — Live Setu Account Aggregator ("Instant Connect")

#### A. The Setu Sandbox Architecture
The application integrates with **Setu FIU** (`https://fiu-sandbox.setu.co`), implementing the standardized RBI consent protocol:
1. **Consent Request:** Backend initiates consent detailing required financial accounts and data range (90 days).
2. **User Consent:** Setu renders the consent agreement; user confirms via test OTP (`123456`).
3. **Data Session:** Setu contacts banks and aggregates transaction ledgers into encrypted JSON (`FI_DATA`).
4. **Data Delivery & Ingestion:** Backend fetches decrypted JSON, runs collision-resistant SHA-256 fingerprinting, categorizes transactions, and persists nodes to Neo4j.

#### B. The Circuit Breaker & Fallback Resilience
To ensure the application **never fails** during live evaluation or if the Setu sandbox experiences downtime:
* If Setu API calls return `HTTP 5xx`, timeout (>5s), or network disconnects:
  1. The backend automatically catches the error.
  2. Falls back seamlessly to our verified multi-month bank dataset (`demo_bank_statement_3_months.csv`).
  3. Returns standard success with fallback diagnostic telemetry:
     ```json
     {
       "status": "SUCCESS",
       "provider": "SANDBOX_SIMULATOR_FALLBACK",
       "synced_transactions": 42,
       "message": "Setu gateway offline; loaded verified sandbox statement."
     }
     ```
  4. The UI displays a subtle badge: `"Connected via Resilient Sandbox"`.

#### C. Backend API Specification (Account Aggregator)
* **Endpoint 1: Discover Accounts:** `POST /api/import/aa/discover`
  * Input: `{ "phone": "9876543210", "bank": "HDFC" }`
  * Output: Discovered accounts with masked numbers and account types.
* **Endpoint 2: Create Consent Session:** `POST /api/import/aa/consent`
  * Input: `{ "phone": "9876543210", "account_ids": ["ACC_HDFC_4102"] }`
  * Output: `{ "consent_id": "...", "consent_url": "..." }`
* **Endpoint 3: Verify OTP & Sync:** `POST /api/import/aa/sync`
  * Input: `{ "consent_id": "...", "otp": "123456" }`
  * Output: Ingestion summary with transaction count and balance updates.

---

### 3.2 Tab 2 — Smart Bank Statement Upload ("File Upload")

#### A. Capabilities
* Accepts **CSV** and **PDF** formats.
* Implements client-side and server-side magic byte validation (`%PDF-` and plain text CSV).
* **PDF Password Decryptor:** Includes a dedicated password input box.
  * If a bank PDF is password-protected, the backend uses `pypdf` in-memory:
    ```python
    reader = pypdf.PdfReader(stream)
    if reader.is_encrypted:
        if not password or not reader.decrypt(password):
            raise HTTPException(status_code=400, detail="Invalid statement password.")
    ```
* Parsed records are presented in the interactive `PreviewTable` allowing users to inspect categorized rows before final commitment.

---

## 4. UI/UX Design Specifications

### 4.1 Header Trigger
In the top navigation bar of `App.jsx`, add a styled primary action button:
```jsx
<button className="btn-primary" onClick={() => setConnectModalOpen(true)}>
  <Building2 size={16} /> Connect Bank Account
</button>
```

### 4.2 Modal Layout & Tab Navigation
* Clean glassmorphism dialog (`glass-card`) with dark navy styling.
* Header featuring RBI Security & 256-Bit Encryption reassurance badges.
* Two segmented tabs:
  1. `[⚡ Instant Connect (Account Aggregator)]`
  2. `[📄 Upload Bank Statement (PDF/CSV)]`

---

## 5. Implementation Roadmap & Technical Deliverables

| Deliverable | File Path | Scope |
| :--- | :--- | :--- |
| **Backend 1: PDF Support** | `requirements.txt` / `.venv` | Install `pypdf` |
| **Backend 2: Onboarding API** | `backend/app/api/onboarding.py` | Implement `POST /api/onboarding/bootstrap` |
| **Backend 3: Setu AA Client** | `backend/app/services/setu_client.py` | Implement Setu FIU API + Resilient fallback |
| **Backend 4: AA Endpoints** | `backend/app/api/import_api.py` | Add `/aa/discover`, `/aa/consent`, `/aa/sync` |
| **Frontend 1: Wizard Modal** | `frontend/src/components/OnboardingWizard.jsx` | 3-step rapid onboarding with live preview |
| **Frontend 2: Connect Modal** | `frontend/src/components/ConnectBankModal.jsx` | 2-tab modal (Setu flow + PDF/CSV drag-and-drop) |
| **Frontend 3: Integration** | `frontend/src/App.jsx` | Mount modals and wire auto-refresh handlers |

---

## 6. Verification & Quality Assurance Criteria

1. **Zero Cold-Start Verification:** Register a new user; confirm wizard pops up; submit income & balance; verify dashboard immediately renders non-zero runway and health score.
2. **Setu AA Flow Verification:** Connect via phone number and OTP `123456`; verify 42 transactions ingested into Neo4j; verify transaction table populates.
3. **Resilience & Fallback Verification:** Disconnect network or invalidate Setu API credentials; trigger sync; verify automatic fallback safely seeds data without UI crash.
4. **Encrypted PDF Verification:** Upload a password-protected PDF; enter password; verify in-memory decryption succeeds and rows are parsed.
5. **Deduplication Check:** Trigger sync twice; verify SHA-256 fingerprinting prevents duplicate transaction creation ($\Delta N = 0$).
