# Chapter 5 (Supplement) — Neo4j Knowledge Graph Modeling & DDL Specifications

## 1. Graph Data Model Overview

The financial knowledge base is implemented as a **Labeled Property Graph (LPG)** in Neo4j, accessible via the Bolt binary protocol (`neo4j://127.0.0.1:7687`) within database `finance-ai-antigravity`. 

The graph topology explicitly captures the multi-relational ownership and causality of personal finances:
- A `:User` owns one or more transactional `:Account` entities.
- An `:Account` executes `:Transaction` nodes categorized under `:Category` nodes.
- A `:User` receives `:Income` streams, services `:Loan` debts structured into periodic `:EMI` payments, and funds long-term capital `:Goal` nodes.
- Upload batches are tracked as `:ImportBatch` nodes to provide full transactional provenance.

---

## 2. Neo4j Cypher DDL Constraints & Index Specifications

The following uniqueness constraints and indexes are established during system initialization ([`init_schema_constraints`](file:///c:/Users/gupta/Documents/HARIOM\Personal_Finance_AI_FYP\backend\app\database\neo4j_service.py#L905)) to guarantee data integrity and sub-millisecond query traversal:

```cypher
// 1. User Entity Uniqueness Constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT user_username_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.username IS UNIQUE;

// 2. Account Entity Uniqueness Constraint
CREATE CONSTRAINT account_id_unique IF NOT EXISTS
FOR (a:Account) REQUIRE a.id IS UNIQUE;

// 3. Transaction Entity Uniqueness & Collision Constraints
CREATE CONSTRAINT txn_id_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT txn_fp IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.fingerprint IS UNIQUE;

// 4. Merchant Canonical Uniqueness Constraint
CREATE CONSTRAINT merchant_norm IF NOT EXISTS
FOR (m:Merchant) REQUIRE m.normalized IS UNIQUE;

// 5. Category Entity Uniqueness Constraint
CREATE CONSTRAINT category_id_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.id IS UNIQUE;

// 6. Import Batch Provenance Constraint
CREATE CONSTRAINT import_batch_id_unique IF NOT EXISTS
FOR (b:ImportBatch) REQUIRE b.id IS UNIQUE;

// 7. Performance Indexes on Temporal and Categorical Properties
CREATE INDEX txn_date_idx IF NOT EXISTS
FOR (t:Transaction) ON (t.date);

CREATE INDEX txn_type_idx IF NOT EXISTS
FOR (t:Transaction) ON (t.type);

CREATE INDEX emi_due_date_idx IF NOT EXISTS
FOR (e:EMI) ON (e.due_date, e.status);
```

---

## 3. Node Label Specifications

### 3.1 `:User`
* **Description:** Represents the registered account holder and serves as the authorization boundary.
* **Properties:**
  - `id` (String, e.g. `"U001"`): Unique system user identifier.
  - `username` (String, e.g. `"Rahul"`): Unique login identifier.
  - `name` (String, e.g. `"Rahul Sharma"`): User's legal name.
  - `password_hash` (String): Hexadecimal PBKDF2 hash.
  - `salt` (String): 16-byte random salt.
  - `created_at` (DateTime): Account registration timestamp.

### 3.2 `:Account`
* **Description:** Represents a bank account, credit card, or liquid cash reserve.
* **Properties:**
  - `id` (String, e.g. `"ACC_HDFC"`): Unique account identifier.
  - `bank` (String, e.g. `"HDFC Bank"`): Name of the financial institution.
  - `account_type` (String, e.g. `"SAVINGS"`, `"CHECKING"`, `"CREDIT_CARD"`): Account classification.
  - `balance` (Float, e.g. `45000.0`): Rupee balance representation.
  - `balance_paise` (Integer, e.g. `4500000`): Integer paise balance representation.
  - `opened_date` (Date, e.g. `2025-01-01`): Certified bank account opening date.
  - `status` (String, e.g. `"ACTIVE"`, `"DORMANT"`, `"CLOSED"`): Operational lifecycle state.

### 3.3 `:Transaction`
* **Description:** Individual debit or credit entry recorded in an account statement.
* **Properties:**
  - `id` (String, e.g. `"TXN_10928"`): System transaction identifier.
  - `description` (String, e.g. `"Swiggy Bangalore"`): Raw bank narration.
  - `amount` (Float, e.g. `450.0`): Rupee amount.
  - `amount_paise` (Integer, e.g. `45000`): Integer paise amount.
  - `type` (String, e.g. `"EXPENSE"`, `"INCOME"`): Transaction direction.
  - `date` (Date, e.g. `2026-10-15`): Transaction execution date.
  - `category` (String, e.g. `"Food"`): Classified spending category.
  - `fingerprint` (String, e.g. `"a3b9f1092e48..."`): 24-char SHA-256 deduplication hash.
  - `is_transfer` (Boolean, e.g. `false`): Flag excluding confirmed internal transfers from expenses.
  - `essential_subtype` (String, e.g. `"COMMUTE"`, optional): Explicit evidence marker.

### 3.4 `:Income`
* **Description:** Verified recurring or ad-hoc incoming earnings.
* **Properties:**
  - `id` (String, e.g. `"INC_01"`): Unique income entry ID.
  - `source` (String, e.g. `"TechCorp India"`): Employer or revenue source.
  - `amount` (Float, e.g. `50000.0`): Rupee amount.
  - `amount_paise` (Integer, e.g. `5000000`): Integer paise amount.
  - `date` (Date, e.g. `2026-10-01`): Credited date.
  - `category` (String, e.g. `"Salary"`): Income classification.

### 3.5 `:Loan` and `:EMI`
* **Description:** Contractual liabilities and scheduled periodic debt servicing obligations.
* **Properties (`:Loan`):**
  - `id` (String), `name` (String: `"Auto Loan"`), `principal` (Float), `outstanding` (Float), `emi` (Float), `emi_paise` (Integer).
* **Properties (`:EMI`):**
  - `id` (String), `amount` (Float: `10000.0`), `amount_paise` (Integer: `1000000`), `due_date` (Date: `2026-10-10`), `status` (String: `"PENDING"` | `"PAID"`).

### 3.6 `:Goal`
* **Description:** Capital accumulation target established by the user.
* **Properties:**
  - `id` (String), `name` (String: `"Emergency Fund"`), `target_amount` (Float: `63000.0`), `current_amount` (Float: `45000.0`), `target_date` (Date).

---

## 4. Representative Cypher Traversal Queries

### 4.1 Purchase Affordability Subgraph Retrieval
```cypher
MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)
OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)-[:HAS_EMI]->(e:EMI {status: 'PENDING'})
WHERE e.due_date >= $start_of_month AND e.due_date <= $end_of_month
OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal {name: 'Emergency Fund'})
RETURN 
    collect(DISTINCT a) as accounts,
    collect(DISTINCT e) as pending_emis,
    g as emergency_goal;
```

### 4.2 Monthly Savings Analysis with Internal Transfer Exclusion
```cypher
MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
WHERE t.date >= $month_start AND t.date <= $month_end AND t.is_transfer = false
OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
WHERE i.date >= $month_start AND i.date <= $month_end AND i.is_transfer = false
RETURN 
    collect(DISTINCT t) as expense_txs,
    collect(DISTINCT i) as income_records;
```

### 4.3 Atomic Internal Transfer Linking
```cypher
MATCH (t1:Transaction {id: $t1_id}), (t2:Transaction {id: $t2_id})
WHERE NOT (t1)-[:INTER_ACCOUNT_TRANSFER]-(t2)
SET t1.is_transfer = true, t2.is_transfer = true
MERGE (t1)-[:INTER_ACCOUNT_TRANSFER]->(t2);
```

