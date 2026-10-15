"""
Unit tests for backend/app/nlu/question_parser.py

Tests rule-based intent parsing, entity extraction (amounts, categories),
and fallback behavior without live LLM calls.
"""
import pytest
from backend.app.nlu.question_parser import parse_question, parse_question_rules


class TestPurchaseSafetyIntent:
    def test_purchase_with_rupee_symbol(self):
        res = parse_question_rules("Can I spend ₹15,000 on a phone?")
        assert res is not None
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 15000.0

    def test_purchase_with_plain_number(self):
        res = parse_question_rules("Can I buy a laptop for 50000?")
        assert res is not None
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 50000.0

    def test_purchase_afford_keyword(self):
        res = parse_question_rules("Can I afford to buy a car for 800000?")
        assert res is not None
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 800000.0


class TestSavingsAnalysisIntent:
    def test_savings_rate(self):
        res = parse_question_rules("What is my savings rate?")
        assert res is not None
        assert res["intent"] == "SAVINGS_ANALYSIS"

    def test_how_much_am_i_saving(self):
        res = parse_question_rules("How much am I saving?")
        assert res is not None
        assert res["intent"] == "SAVINGS_ANALYSIS"


class TestEmergencyFundIntent:
    def test_emergency_fund_query(self):
        res = parse_question_rules("How much emergency fund do I need?")
        assert res is not None
        assert res["intent"] == "EMERGENCY_FUND_ANALYSIS"

    def test_emergency_reserve_query(self):
        res = parse_question_rules("What should my emergency reserve target be?")
        assert res is not None
        assert res["intent"] == "EMERGENCY_FUND_ANALYSIS"


class TestEmergencyRunwayIntent:
    def test_emergency_runway_query(self):
        res = parse_question_rules("What is my emergency runway?")
        assert res is not None
        assert res["intent"] == "EMERGENCY_RUNWAY_ANALYSIS"

    def test_survival_query(self):
        res = parse_question_rules("How many months can I survive if I lose my job?")
        assert res is not None
        assert res["intent"] == "EMERGENCY_RUNWAY_ANALYSIS"


class TestDebtAnalysisIntent:
    def test_debt_query(self):
        res = parse_question_rules("How much debt do I have?")
        assert res is not None
        assert res["intent"] == "DEBT_ANALYSIS"

    def test_emi_query(self):
        res = parse_question_rules("What are my pending EMIs?")
        assert res is not None
        assert res["intent"] == "DEBT_ANALYSIS"

    def test_dti_ratio_query(self):
        res = parse_question_rules("What is my DTI ratio?")
        assert res is not None
        assert res["intent"] == "DEBT_ANALYSIS"


class TestFinancialHealthAndSummary:
    def test_financial_health_query(self):
        res = parse_question_rules("How is my financial health?")
        assert res is not None
        assert res["intent"] == "FINANCIAL_HEALTH"

    def test_health_score_query(self):
        res = parse_question_rules("What is my financial health score?")
        assert res is not None
        assert res["intent"] == "FINANCIAL_HEALTH"

    def test_financial_summary_query(self):
        res = parse_question_rules("Give me a financial summary")
        assert res is not None
        assert res["intent"] == "FINANCIAL_SUMMARY"

    def test_financial_situation_query(self):
        res = parse_question_rules("What is my financial situation?")
        assert res is not None
        assert res["intent"] == "FINANCIAL_SUMMARY"


class TestExpenseBreakdownAndCategories:
    def test_expense_breakdown_query(self):
        res = parse_question_rules("Where did I spend the most money?")
        assert res is not None
        assert res["intent"] == "EXPENSE_BREAKDOWN"

    def test_category_expense_query(self):
        res = parse_question_rules("How much did I spend on food?")
        assert res is not None
        assert res["intent"] == "CATEGORY_EXPENSE"
        assert res["category"] == "Food"


class TestTransactionIngestionIntent:
    def test_spent_transaction(self):
        res = parse_question_rules("I spent ₹500 on food today")
        assert res is not None
        assert res["intent"] == "TRANSACTION_INGESTION"
        assert res["amount"] == 500.0


class TestUnknownFallback:
    def test_unmatched_rules_without_llm(self):
        res = parse_question("Random irrelevant gibberish xyz abc", use_llm_fallback=False)
        assert res["intent"] == "UNKNOWN"
        assert res["amount"] is None
