"""
Unit tests for Grounded Graph Retrieval and Multi-Entity Question Answering.

Demonstrates:
1. Multi-Entity Purchase Affordability (Account + Loan + EMI + Expense buffer).
2. Multi-Entity Debt & Obligation Analysis (Loan + EMI + Income).
3. Contextual Follow-Up with Strict Entity Isolation (Food -> Transport without data leakage).
4. Cross-User Data Isolation in Grounded Subgraph Retrieval.
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from backend.app.rag.graph_rag import GraphRAG
from backend.app.database.neo4j_service import Neo4jService


# =====================================================================
# Test 1: Multi-Entity Purchase Affordability
# =====================================================================
def test_grounded_retrieval_multi_entity_purchase_affordability():
    """
    Question: "Can I spend ₹15,000 on a phone?"
    Requires multi-entity graph retrieval:
      - Account (liquid balance)
      - Loan -> EMI (pending obligations)
      - Transaction -> Category (90-day expenses for 3-month emergency buffer)
    """
    mock_db = MagicMock(spec=Neo4jService)
    
    # Grounded subgraph retrieved specifically for PURCHASE_SAFETY
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "PURCHASE_SAFETY",
        "grounded_entities": {
            "accounts": [{"id": "A001", "bank": "HDFC", "balance": 70000.0}],
            "loans": [{"loan_id": "L001", "loan": "Personal Loan", "emi_id": "E001", "emi": 5000.0, "status": "PENDING"}],
            "transactions": [
                {"id": "T001", "amount": 10000.0, "type": "EXPENSE", "date": "2025-08-01", "category": "Food"},
                {"id": "T002", "amount": 5000.0, "type": "EXPENSE", "date": "2025-08-15", "category": "Utilities"},
            ],
            "incomes": [],
            "goals": [],
        },
        "source_identifiers": ["Account:A001", "EMI:E001", "Loan:L001", "Transaction:T001", "Transaction:T002"],
        "graph_paths": [
            "(User:U001)-[:HAS_ACCOUNT]->(Account:A001)",
            "(User:U001)-[:HAS_LOAN]->(Loan:L001)-[:HAS_EMI]->(EMI:E001)",
        ],
        "context": {
            "accounts": [{"id": "A001", "bank": "HDFC", "balance": 70000.0}],
            "loans": [{"loan_id": "L001", "loan": "Personal Loan", "emi_id": "E001", "emi": 5000.0, "status": "PENDING"}],
            "transactions": [
                {"id": "T001", "amount": 10000.0, "type": "EXPENSE", "date": "2025-08-01", "category": "Food"},
                {"id": "T002", "amount": 5000.0, "type": "EXPENSE", "date": "2025-08-15", "category": "Utilities"},
            ],
            "incomes": [],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {
            "content": "Purchase is safe. You have ₹70,000 in your HDFC account and after ₹5,000 EMI and ₹15,000 purchase, you maintain your emergency buffer.",
            "prompt_tokens": 150,
            "completion_tokens": 40,
            "tokens_used": 190,
        }

        result = rag.process_query("Can I spend ₹15,000 on a phone?", user_id="U001")

        # 1. Verify intent and entities identified
        assert result["intent"] == "PURCHASE_SAFETY"
        assert result["entities"]["amount"] == 15000.0

        # 2. Verify deterministic financial engine computation
        math = result["math_result"]
        assert math["decision"] == "SAFE"
        assert math["evidence"]["current_balance"] == 70000.0
        assert math["evidence"]["pending_emi"] == 5000.0
        assert math["evidence"]["purchase_amount"] == 15000.0
        assert math["evidence"]["balance_after_purchase"] == 50000.0

        # 3. Verify retrieved evidence and source identifiers
        assert "Account:A001" in result["source_identifiers"]
        assert "EMI:E001" in result["source_identifiers"]
        assert "Loan:L001" in result["source_identifiers"]
        assert len(result["evidence"]) >= 5

        # Check evidence facts have source_node_ids linked
        account_fact = next(f for f in result["evidence"] if f["label"] == "Current Account Balance")
        assert "Account:A001" in account_fact["source_node_ids"]

        emi_fact = next(f for f in result["evidence"] if f["label"] == "Pending EMI Obligations")
        assert "EMI:E001" in emi_fact["source_node_ids"]

        # 4. Verify call to LLM passed evidence containing grounded source metadata
        called_prompt = mock_ask_llm.call_args[0][0]
        assert "_source_identifiers" in called_prompt
        assert "Account:A001" in called_prompt


# =====================================================================
# Test 2: Multi-Entity Debt & Obligation Analysis
# =====================================================================
def test_grounded_retrieval_multi_entity_debt_and_dti():
    """
    Question: "What are my loan obligations and DTI ratio?"
    Requires multi-entity graph retrieval:
      - Loan (principal & outstanding)
      - EMI (monthly payment obligation)
      - Income (monthly inflow to compute debt-to-income percentage)
    """
    mock_db = MagicMock(spec=Neo4jService)
    today = date.today()
    curr_period_date = f"{today.year}-{today.month:02d}-05"
    curr_income_date = f"{today.year}-{today.month:02d}-01"

    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "DEBT_ANALYSIS",
        "grounded_entities": {
            "accounts": [],
            "loans": [
                {
                    "loan_id": "L_CAR_01",
                    "loan": "Car Loan",
                    "outstanding": 300000.0,
                    "emi_id": "E_CAR_01",
                    "emi": 12000.0,
                    "due_date": curr_period_date,
                    "status": "PENDING",
                }
            ],
            "incomes": [
                {"id": "I_SALARY_01", "source": "Tech Corp Salary", "amount": 60000.0, "date": curr_income_date}
            ],
            "transactions": [],
            "goals": [],
        },
        "source_identifiers": ["EMI:E_CAR_01", "Income:Tech Corp Salary", "Loan:L_CAR_01"],
        "graph_paths": [
            "(User:U001)-[:HAS_LOAN]->(Loan:L_CAR_01)-[:HAS_EMI]->(EMI:E_CAR_01)",
            "(User:U001)-[:RECEIVED_INCOME]->(Income:Tech Corp Salary)",
        ],
        "context": {
            "accounts": [],
            "loans": [
                {
                    "loan_id": "L_CAR_01",
                    "loan": "Car Loan",
                    "outstanding": 300000.0,
                    "emi_id": "E_CAR_01",
                    "emi": 12000.0,
                    "due_date": curr_period_date,
                    "status": "PENDING",
                }
            ],
            "incomes": [
                {"id": "I_SALARY_01", "source": "Tech Corp Salary", "amount": 60000.0, "date": curr_income_date}
            ],
            "transactions": [],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {
            "content": "Your total outstanding debt is ₹3,00,000 with a monthly EMI of ₹12,000. Your DTI ratio is 20.0%, which is Healthy.",
            "prompt_tokens": 140,
            "completion_tokens": 35,
            "tokens_used": 175,
        }

        result = rag.process_query("What are my loan obligations and DTI ratio?", user_id="U001")

        assert result["intent"] == "DEBT_ANALYSIS"
        math = result["math_result"]
        assert math["total_outstanding_debt"] == 300000.0
        assert math["monthly_emi"] == 12000.0
        assert math["dti_ratio"] == 20.0
        assert math["assessment"] == "Healthy debt level (under 20% of income)."

        # Verify source identifiers
        assert "Loan:L_CAR_01" in result["source_identifiers"]
        assert "EMI:E_CAR_01" in result["source_identifiers"]
        assert "Income:Tech Corp Salary" in result["source_identifiers"]

        # Check evidence node IDs
        loan_fact = next(f for f in result["evidence"] if f["label"] == "Total Outstanding Loan Principal")
        assert "Loan:L_CAR_01" in loan_fact["source_node_ids"]


# =====================================================================
# Test 3: Follow-Up Questions with Strict Entity & Context Isolation
# =====================================================================
def test_grounded_retrieval_followup_entity_isolation():
    """
    Turn 1: "How much did I spend on food in September 2025?"
    Turn 2: "What about transport?"

    Turn 2 must:
      - Inherit temporal scope (September 2025) and intent (CATEGORY_EXPENSE).
      - Retrieve ONLY Transport category and Transport transactions.
      - NOT retrieve Food transactions, Loans, EMIs, or other unrelated data.
    """
    mock_db = MagicMock(spec=Neo4jService)

    # In turn 2, retrieve_grounded_subgraph is called with category='Transport' and reporting_date=2025-09-01
    def mock_retrieve_grounded(user_id, intent, entities):
        cat = entities.get("category")
        rep_date = entities.get("reporting_date")
        assert intent == "CATEGORY_EXPENSE"
        assert cat == "Transport"
        assert rep_date == date(2025, 9, 1)

        return {
            "user_id": user_id,
            "intent": "CATEGORY_EXPENSE",
            "grounded_entities": {
                "accounts": [{"id": "A001", "bank": "HDFC", "balance": 45000.0}],
                "transactions": [
                    {"id": "T_TRANS_01", "amount": 2500.0, "type": "EXPENSE", "date": "2025-09-12", "category": "Transport"},
                    {"id": "T_TRANS_02", "amount": 1500.0, "type": "EXPENSE", "date": "2025-09-24", "category": "Transport"},
                ],
                "loans": [],
                "incomes": [],
                "goals": [],
            },
            "source_identifiers": ["Account:A001", "Category:Transport", "Transaction:T_TRANS_01", "Transaction:T_TRANS_02"],
            "graph_paths": [
                "(Account:A001)-[:MADE_TRANSACTION]->(Transaction:T_TRANS_01)-[:BELONGS_TO]->(Category:Transport)",
                "(Account:A001)-[:MADE_TRANSACTION]->(Transaction:T_TRANS_02)-[:BELONGS_TO]->(Category:Transport)",
            ],
            "context": {
                "accounts": [{"id": "A001", "bank": "HDFC", "balance": 45000.0}],
                "transactions": [
                    {"id": "T_TRANS_01", "amount": 2500.0, "type": "EXPENSE", "date": "2025-09-12", "category": "Transport"},
                    {"id": "T_TRANS_02", "amount": 1500.0, "type": "EXPENSE", "date": "2025-09-24", "category": "Transport"},
                ],
                "loans": [],
                "incomes": [],
                "goals": [],
            },
        }

    mock_db.retrieve_grounded_subgraph.side_effect = mock_retrieve_grounded

    rag = GraphRAG(db=mock_db)

    # Conversation history containing Turn 1
    history = [
        {"role": "user", "content": "How much did I spend on food in September 2025?"},
        {"role": "assistant", "content": "In September 2025, you spent ₹8,200 on Food."},
    ]

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {
            "content": "For Transport in September 2025, you spent a total of ₹4,000 across 2 transactions.",
            "prompt_tokens": 130,
            "completion_tokens": 30,
            "tokens_used": 160,
        }

        # Follow-up question
        result = rag.process_query("What about transport?", user_id="U001", conversation_history=history)

        # 1. Correct intent and inherited temporal reporting date
        assert result["intent"] == "CATEGORY_EXPENSE"
        assert result["entities"]["category"] == "Transport"
        assert result["entities"]["reporting_date"] == date(2025, 9, 1)

        # 2. Strict Entity Isolation: ONLY Transport transactions retrieved
        assert "Category:Transport" in result["source_identifiers"]
        assert "Transaction:T_TRANS_01" in result["source_identifiers"]
        assert "Transaction:T_TRANS_02" in result["source_identifiers"]
        # Must NOT contain Food or Loans
        assert "Category:Food" not in result["source_identifiers"]
        assert not any("Loan" in s for s in result["source_identifiers"])

        # 3. Deterministic calculation
        math = result["math_result"]
        assert math["requested_category"] == "Transport"
        assert math["category_spent"] == 4000.0


# =====================================================================
# Test 4: Real Neo4j Grounded Cypher Query Builder Isolation
# =====================================================================
def test_neo4j_service_retrieve_grounded_subgraph_user_isolation():
    """
    Verifies that Neo4jService.retrieve_grounded_subgraph enforces user_id
    filtering in Cypher parameters and raises ValueError on invalid/empty user_id.
    """
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver.session.return_value.__exit__.return_value = None

    service = Neo4jService(driver=mock_driver)

    # Empty user_id must be rejected
    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        service.retrieve_grounded_subgraph("", "PURCHASE_SAFETY")

    with pytest.raises(ValueError, match="user_id must be a non-empty string"):
        service.retrieve_grounded_subgraph(None, "PURCHASE_SAFETY")

    # Mock return record
    mock_rec = {
        "accounts": [{"id": "A001", "bank": "HDFC", "balance": 50000.0}],
        "loans": [],
        "transactions": [],
    }
    mock_session.run.return_value.single.return_value = mock_rec

    res = service.retrieve_grounded_subgraph("USER_ALICE", "PURCHASE_SAFETY")
    assert res["user_id"] == "USER_ALICE"
    
    # Check that session.run was called with user_id='USER_ALICE'
    assert mock_session.run.call_count >= 1
    call_kwargs = mock_session.run.call_args[1]
    assert call_kwargs["user_id"] == "USER_ALICE"
