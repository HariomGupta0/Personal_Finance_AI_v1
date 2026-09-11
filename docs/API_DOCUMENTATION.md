# REST API Documentation: Personal Finance AI

Base URL: `http://127.0.0.1:8000`

---

## 1. System Endpoints

### `GET /`
Health check and API metadata.
- **Response `200 OK`**:
```json
{
  "status": "ONLINE",
  "service": "Personal Finance AI Assistant API",
  "database": "Neo4j (finance-ai-antigravity)",
  "docs_url": "/docs"
}
```

---

## 2. Financial Analytics Endpoints

### `GET /api/finance/summary`
Returns comprehensive financial snapshot.
- **Query Params**: `user_id` (default: `"U001"`)
- **Response `200 OK`**:
```json
{
  "income": 60000.0,
  "expenses": 21000.0,
  "savings": 39000.0,
  "savings_rate": 65.0,
  "monthly_expenses": 21000.0,
  "current_emergency_fund": 30000.0,
  "recommended_emergency_fund": 63000.0,
  "emergency_fund_shortfall": 33000.0,
  "health_score": 90.0,
  "health_grade": "A",
  "top_expense_category": "Housing",
  "dti_ratio": 16.67
}
```

### `GET /api/finance/expenses`
Returns category-wise expense distribution.
- **Response `200 OK`**:
```json
{
  "total_expenses": 21000.0,
  "top_category": "Housing",
  "top_amount": 12000.0,
  "categories": [
    {"category": "Housing", "amount": 12000.0, "percentage": 57.14},
    {"category": "Food", "amount": 4000.0, "percentage": 19.05},
    {"category": "Utilities", "amount": 3000.0, "percentage": 14.29},
    {"category": "Transport", "amount": 2000.0, "percentage": 9.52}
  ]
}
```

### `GET /api/finance/emergency-fund`
Returns emergency reserve buffer, shortfall, and months of runway.
- **Response `200 OK`**:
```json
{
  "monthly_expenses": 21000.0,
  "recommended_fund": 63000.0,
  "current_fund": 30000.0,
  "shortfall": 33000.0,
  "current_balance": 45000.0,
  "runway_months": 2.14,
  "status": "INSUFFICIENT",
  "target_runway_months": 3.0
}
```

### `GET /api/finance/debt`
Returns loans, pending EMIs, and Debt-to-Income (DTI) ratio.
- **Response `200 OK`**:
```json
{
  "total_outstanding_debt": 150000.0,
  "monthly_emi": 10000.0,
  "dti_ratio": 16.67,
  "risk_level": "LOW",
  "assessment": "Healthy debt level (under 20% of income)."
}
```

---

## 3. Transaction Management Endpoints

### `GET /api/transactions`
Returns all transaction ledger entries, categories, and accounts.

### `POST /api/transactions`
Adds a transaction via structured data or natural language.
- **Natural Language Payload**:
```json
{
  "user_id": "U001",
  "natural_language_input": "I spent ₹5000 on food today"
}
```
- **Response `200 OK`**:
```json
{
  "status": "SUCCESS",
  "transaction": {
    "transaction_id": "T_A1B2C3D4",
    "amount": 5000.0,
    "category": "Food",
    "new_balance": 40000.0
  },
  "impact_summary": "Successfully recorded EXPENSE of ₹5,000.00 (Food). Updated Balance: ₹40,000.00."
}
```

### `DELETE /api/transactions/{id}`
Deletes a transaction and automatically restores the account balance.

---

## 4. AI Assistant Endpoints

### `POST /api/assistant/query`
GraphRAG powered question answering.
- **Request**:
```json
{
  "user_id": "U001",
  "question": "Can I spend ₹15000 on a phone?"
}
```
- **Response `200 OK`**:
```json
{
  "query": "Can I spend ₹15000 on a phone?",
  "intent": "PURCHASE_SAFETY",
  "math_result": {
    "decision": "NOT_SAFE",
    "risk_level": "HIGH"
  },
  "evidence": [
    {"label": "Current Account Balance", "value": "₹45,000", "source": "Account.balance"},
    {"label": "Pending EMI Obligations", "value": "₹10,000", "source": "EMI.amount"},
    {"label": "Purchase Cost", "value": "₹15,000", "source": "User Query"},
    {"label": "Post-Purchase Remaining Balance", "value": "₹20,000", "source": "Deterministic Math"},
    {"label": "Recommended 3-Month Emergency Buffer", "value": "₹63,000", "source": "Emergency Fund Formula"}
  ],
  "explanation": "The purchase is not financially safe..."
}
```
