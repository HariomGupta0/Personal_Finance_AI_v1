"""
Unit tests for Financial Assistant Evidence Presentation and Missing-Data Caveats.

Verifies:
1. Evidence Correctness:
   - Metric name and verified authoritative value.
   - Reporting period and data freshness calculation.
   - Supporting entity identifiers (Account, Loan, EMI, Goal, Transaction).
   - Mathematical formula and calculation methodology.
2. Missing-Data Caveats:
   - Zero recorded expenses caveat in purchase affordability and runway.
   - Zero income caveat in savings and critical debt situations.
   - Missing bank accounts caveat.
   - Missing emergency fund goal caveat.
   - Unknown intent fallback evidence metadata.
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from backend.app.rag.graph_rag import GraphRAG
from backend.app.database.neo4j_service import Neo4jService


# =====================================================================
# 1. Evidence Correctness & Metadata Tests
# =====================================================================

def test_evidence_presentation_purchase_safety():
    """
    Verifies that for purchase safety:
    - Authoritative metric names and values are exposed.
    - Reporting period and data freshness are present.
    - Supporting node IDs (Account, EMI, Transaction) are populated on items.
    - Methodology formula and calculation method are documented.
    """
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "PURCHASE_SAFETY",
        "grounded_entities": {
            "accounts": [{"id": "A_SBI_01", "bank": "SBI", "balance": 80000.0}],
            "loans": [{"loan_id": "L001", "loan": "Personal Loan", "emi_id": "E001", "emi": 6000.0, "status": "PENDING"}],
            "transactions": [
                {"id": "TX_01", "amount": 12000.0, "type": "EXPENSE", "date": "2026-09-15", "category": "Food"},
                {"id": "TX_02", "amount": 8000.0, "type": "EXPENSE", "date": "2026-09-20", "category": "Utilities"},
            ],
            "incomes": [],
            "goals": [],
        },
        "source_identifiers": ["Account:A_SBI_01", "EMI:E001", "Loan:L001", "Transaction:TX_01", "Transaction:TX_02"],
        "graph_paths": [],
        "context": {
            "accounts": [{"id": "A_SBI_01", "bank": "SBI", "balance": 80000.0}],
            "loans": [{"loan_id": "L001", "loan": "Personal Loan", "emi_id": "E001", "emi": 6000.0, "status": "PENDING"}],
            "transactions": [
                {"id": "TX_01", "amount": 12000.0, "type": "EXPENSE", "date": "2026-09-15", "category": "Food"},
                {"id": "TX_02", "amount": 8000.0, "type": "EXPENSE", "date": "2026-09-20", "category": "Utilities"},
            ],
            "incomes": [],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {
            "content": "Purchase of ₹20,000 is safe.",
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "tokens_used": 120,
        }

        result = rag.process_query("Can I spend ₹20,000 on a laptop?", user_id="U001")

        # 1. Structure separation: evidence exists independent of explanation
        assert "explanation" in result
        assert "evidence" in result
        assert "evidence_metadata" in result

        metadata = result["evidence_metadata"]
        assert metadata["reporting_period"] is not None
        assert "Verified through latest transaction (2026-09-20)" in metadata["data_freshness"]
        assert "Post-Purchase Balance = Current Balance - Pending EMIs - Purchase Cost" in metadata["methodology_formula"]
        assert metadata["is_sufficient_data"] is True
        assert len(metadata["caveats"]) == 0

        # 2. Metric names, verified values, formulas, and source node IDs
        balance_card = next(c for c in result["evidence"] if c["label"] == "Current Account Balance")
        assert balance_card["value"] == "₹80,000"
        assert balance_card["source"] == "Account.balance"
        assert balance_card["formula"] == "Sum of verified liquid account balances"
        assert "Account:A_SBI_01" in balance_card["source_node_ids"]

        emi_card = next(c for c in result["evidence"] if c["label"] == "Pending EMI Obligations")
        assert emi_card["value"] == "₹6,000"
        assert "EMI:E001" in emi_card["source_node_ids"]

        buffer_card = next(c for c in result["evidence"] if c["label"] == "Recommended 3-Month Emergency Buffer")
        assert buffer_card["value"] == "₹60,000"  # 3 * (12000 + 8000) = 60,000
        assert "Transaction:TX_01" in buffer_card["source_node_ids"]
        assert "Transaction:TX_02" in buffer_card["source_node_ids"]

        decision_card = next(c for c in result["evidence"] if c["label"] == "Decision & Safety Rating")
        assert "SAFE" in decision_card["value"]


def test_evidence_presentation_savings_analysis():
    """
    Verifies that for savings analysis:
    - Income, Expenses, Savings, and Savings Rate are exposed with formulas.
    - Supporting income and transaction node IDs are properly attached.
    """
    mock_db = MagicMock(spec=Neo4jService)
    today = date.today()
    curr_month = f"{today.year}-{today.month:02d}"

    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "SAVINGS_ANALYSIS",
        "grounded_entities": {
            "accounts": [],
            "loans": [],
            "transactions": [
                {"id": "T01", "amount": 20000.0, "type": "EXPENSE", "date": f"{curr_month}-10", "category": "Food"}
            ],
            "incomes": [
                {"id": "INC_01", "source": "Primary Salary", "amount": 80000.0, "date": f"{curr_month}-01"}
            ],
            "goals": [],
        },
        "source_identifiers": ["Income:Primary Salary", "Transaction:T01"],
        "graph_paths": [],
        "context": {
            "accounts": [],
            "loans": [],
            "transactions": [
                {"id": "T01", "amount": 20000.0, "type": "EXPENSE", "date": f"{curr_month}-10", "category": "Food"}
            ],
            "incomes": [
                {"id": "INC_01", "source": "Primary Salary", "amount": 80000.0, "date": f"{curr_month}-01"}
            ],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {"content": "Your savings rate is 75%.", "prompt_tokens": 100, "completion_tokens": 15, "tokens_used": 115}
        result = rag.process_query("What is my savings rate?", user_id="U001")

        savings_rate_card = next(c for c in result["evidence"] if c["label"] == "Savings Rate")
        assert savings_rate_card["value"] == "75.0%"
        assert savings_rate_card["formula"] == "(Net Savings / Total Income) × 100"
        assert "Income:Primary Salary" in savings_rate_card["source_node_ids"]
        assert "Transaction:T01" in savings_rate_card["source_node_ids"]

        meta = result["evidence_metadata"]
        assert meta["reporting_period"] == curr_month
        assert meta["is_sufficient_data"] is True


def test_evidence_presentation_emergency_fund():
    """
    Verifies that emergency fund analysis:
    - Shows monthly expenses, recommended fund, current fund, and shortfall.
    - Captures goal identifiers.
    """
    mock_db = MagicMock(spec=Neo4jService)
    today = date.today()
    curr_month = f"{today.year}-{today.month:02d}"

    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "EMERGENCY_FUND_ANALYSIS",
        "grounded_entities": {
            "accounts": [],
            "loans": [],
            "transactions": [
                {"id": "T01", "amount": 25000.0, "type": "EXPENSE", "date": f"{curr_month}-10", "category": "General"}
            ],
            "incomes": [],
            "goals": [
                {"id": "G001", "name": "Emergency Fund", "current_amount": 50000.0, "target_amount": 100000.0}
            ],
        },
        "source_identifiers": ["Goal:Emergency Fund", "Transaction:T01"],
        "graph_paths": [],
        "context": {
            "accounts": [],
            "loans": [],
            "transactions": [
                {"id": "T01", "amount": 25000.0, "type": "EXPENSE", "date": f"{curr_month}-10", "category": "General"}
            ],
            "incomes": [],
            "goals": [
                {"id": "G001", "name": "Emergency Fund", "current_amount": 50000.0, "target_amount": 100000.0}
            ],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {"content": "Your shortfall is ₹25,000.", "prompt_tokens": 100, "completion_tokens": 15, "tokens_used": 115}
        result = rag.process_query("How much emergency fund do I need?", user_id="U001")

        recommended_card = next(c for c in result["evidence"] if c["label"] == "Recommended 3-Month Fund")
        assert recommended_card["value"] == "₹75,000"  # 3 * 25,000

        current_card = next(c for c in result["evidence"] if c["label"] == "Current Fund Reserve")
        assert current_card["value"] == "₹50,000"
        assert "Goal:Emergency Fund" in current_card["source_node_ids"]

        shortfall_card = next(c for c in result["evidence"] if c["label"] == "Reserve Shortfall")
        assert shortfall_card["value"] == "₹25,000"


# =====================================================================
# 2. Missing-Data Caveat Tests
# =====================================================================

def test_missing_data_caveat_zero_expenses_in_purchase_safety():
    """
    When monthly expenses are 0, purchase affordability must explicitly flag
    that the 3-month baseline reserve requirement could not be verified from transactions.
    """
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "PURCHASE_SAFETY",
        "grounded_entities": {
            "accounts": [{"id": "A001", "balance": 50000.0}],
            "loans": [],
            "transactions": [],  # Zero recorded expenses
            "incomes": [],
            "goals": [],
        },
        "source_identifiers": ["Account:A001"],
        "graph_paths": [],
        "context": {
            "accounts": [{"id": "A001", "balance": 50000.0}],
            "loans": [],
            "transactions": [],
            "incomes": [],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {"content": "Purchase verified.", "prompt_tokens": 50, "completion_tokens": 10, "tokens_used": 60}
        result = rag.process_query("Can I spend ₹5000 on shoes?", user_id="U001")

        meta = result["evidence_metadata"]
        assert meta["is_sufficient_data"] is False
        assert any("Zero monthly expenses recorded" in c for c in meta["caveats"])


def test_missing_data_caveat_zero_income_with_active_debt():
    """
    When user has active EMI obligations but zero recorded income,
    debt analysis must generate a critical debt risk caveat.
    """
    mock_db = MagicMock(spec=Neo4jService)
    today = date.today()
    curr_month = f"{today.year}-{today.month:02d}"

    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "DEBT_ANALYSIS",
        "grounded_entities": {
            "accounts": [],
            "loans": [
                {"loan_id": "L01", "loan": "Personal Loan", "outstanding": 100000.0, "emi_id": "E01", "emi": 8000.0, "due_date": f"{curr_month}-05", "status": "PENDING"}
            ],
            "transactions": [],
            "incomes": [],  # Zero income recorded
            "goals": [],
        },
        "source_identifiers": ["EMI:E01", "Loan:L01"],
        "graph_paths": [],
        "context": {
            "accounts": [],
            "loans": [
                {"loan_id": "L01", "loan": "Personal Loan", "outstanding": 100000.0, "emi_id": "E01", "emi": 8000.0, "due_date": f"{curr_month}-05", "status": "PENDING"}
            ],
            "transactions": [],
            "incomes": [],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {"content": "Debt risk evaluated.", "prompt_tokens": 50, "completion_tokens": 10, "tokens_used": 60}
        result = rag.process_query("What is my debt burden and DTI?", user_id="U001")

        meta = result["evidence_metadata"]
        assert any("Active monthly EMI obligations with zero recorded income" in c for c in meta["caveats"])


def test_missing_data_caveat_no_accounts_linked():
    """
    When no bank accounts exist in the graph, purchase safety and runway must flag
    that no active accounts are linked.
    """
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "PURCHASE_SAFETY",
        "grounded_entities": {"accounts": [], "loans": [], "transactions": [], "incomes": [], "goals": []},
        "source_identifiers": [],
        "graph_paths": [],
        "context": {"accounts": [], "loans": [], "transactions": [], "incomes": [], "goals": []},
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {"content": "No accounts.", "prompt_tokens": 40, "completion_tokens": 10, "tokens_used": 50}
        result = rag.process_query("Can I spend ₹2000?", user_id="U001")

        meta = result["evidence_metadata"]
        assert any("No active bank accounts linked" in c for c in meta["caveats"])


def test_missing_data_caveat_missing_emergency_goal():
    """
    When no dedicated emergency fund goal exists, emergency fund analysis must flag
    the missing goal caveat and count current reserve as ₹0.
    """
    mock_db = MagicMock(spec=Neo4jService)
    today = date.today()
    curr_month = f"{today.year}-{today.month:02d}"

    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "EMERGENCY_FUND_ANALYSIS",
        "grounded_entities": {
            "accounts": [],
            "loans": [],
            "transactions": [{"id": "T01", "amount": 10000.0, "type": "EXPENSE", "date": f"{curr_month}-05"}],
            "incomes": [],
            "goals": [],  # No goals
        },
        "source_identifiers": ["Transaction:T01"],
        "graph_paths": [],
        "context": {
            "accounts": [],
            "loans": [],
            "transactions": [{"id": "T01", "amount": 10000.0, "type": "EXPENSE", "date": f"{curr_month}-05"}],
            "incomes": [],
            "goals": [],
        },
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_ask_llm:
        mock_ask_llm.return_value = {"content": "No emergency goal.", "prompt_tokens": 40, "completion_tokens": 10, "tokens_used": 50}
        result = rag.process_query("How much emergency fund do I need?", user_id="U001")

        meta = result["evidence_metadata"]
        assert any("No designated 'Emergency Fund' goal found" in c for c in meta["caveats"])

        current_card = next(c for c in result["evidence"] if c["label"] == "Current Fund Reserve")
        assert current_card["value"] == "₹0"


def test_missing_data_caveat_unknown_intent():
    """
    When user asks an unrecognizable query, returns unknown intent with safe
    empty evidence and explicit caveat.
    """
    rag = GraphRAG()
    result = rag.process_query("What is the meaning of life?", user_id="U001")

    assert result["intent"] == "UNKNOWN"
    assert result["evidence"] == []
    meta = result["evidence_metadata"]
    assert meta["is_sufficient_data"] is False
    assert any("Unrecognized intent" in c for c in meta["caveats"])
