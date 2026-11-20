"""
Unit tests for multi-turn financial conversations, context preservation,
topic change isolation, missing information clarifications, and defense against
contradictory historical claims.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch

from backend.app.nlu.question_parser import (
    parse_question,
    parse_question_rules,
    check_date_ambiguity,
    extract_candidate_amounts,
)
from backend.app.rag.graph_rag import GraphRAG


# ─────────────────────────────────────────────────────────────────────────────
# 1. Multi-Turn Follow-Ups
# ─────────────────────────────────────────────────────────────────────────────
class TestMultiTurnFollowUps:
    def test_purchase_amount_followup(self):
        history = [
            {"role": "user", "content": "Can I buy a phone for ₹15,000?"},
            {"role": "assistant", "content": "🎯 The Quick Take: It is NOT SAFE to buy this phone."},
        ]
        res = parse_question_rules("What if it costs ₹10,000?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is True
        assert res["turn_type"] == "FOLLOW_UP"
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 10000.0
        assert res["category"] == "Shopping"
        assert res["needs_clarification"] is False

    def test_purchase_bare_amount_reply_after_missing_amount(self):
        history = [
            {"role": "user", "content": "Can I buy a laptop?"},
            {"role": "assistant", "content": "Please specify the purchase amount to check affordability."},
        ]
        res = parse_question_rules("₹45,000", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is True
        assert res["turn_type"] == "FOLLOW_UP"
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 45000.0
        assert res["category"] == "Shopping"

    def test_category_expense_followup(self):
        history = [
            {"role": "user", "content": "Where did I spend the most money?"},
            {"role": "assistant", "content": "Your largest spending category was Housing."},
        ]
        res = parse_question_rules("What about groceries?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is True
        assert res["turn_type"] == "FOLLOW_UP"
        assert res["intent"] == "CATEGORY_EXPENSE"
        assert res["category"] == "Food"

    def test_temporal_date_followup(self):
        history = [
            {"role": "user", "content": "What was my savings rate?"},
            {"role": "assistant", "content": "Your savings rate is 25%."},
        ]
        res = parse_question_rules("What about last month?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is True
        assert res["turn_type"] == "FOLLOW_UP"
        assert res["intent"] == "SAVINGS_ANALYSIS"
        assert res["reporting_date"] is not None

    def test_justification_followup(self):
        history = [
            {"role": "user", "content": "Can I spend ₹20,000 on a vacation?"},
            {"role": "assistant", "content": "It is NOT SAFE due to your upcoming EMIs."},
        ]
        res = parse_question_rules("Why is it not safe?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is True
        assert res["turn_type"] == "FOLLOW_UP"
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 20000.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Topic Changes & Context Reset
# ─────────────────────────────────────────────────────────────────────────────
class TestTopicChanges:
    def test_switch_from_purchase_to_savings(self):
        history = [
            {"role": "user", "content": "Can I buy a phone for ₹25,000?"},
            {"role": "assistant", "content": "Affordability check complete: SAFE."},
        ]
        res = parse_question_rules("What is my savings rate?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is False
        assert res["turn_type"] == "NEW_TOPIC"
        assert res["intent"] == "SAVINGS_ANALYSIS"
        # Must NOT carry over purchase amount or shopping category
        assert res["amount"] is None
        assert res["category"] is None

    def test_switch_from_temporal_category_to_runway(self):
        history = [
            {"role": "user", "content": "How much did I spend on food in September 2025?"},
            {"role": "assistant", "content": "You spent ₹12,000 on Food in September 2025."},
        ]
        res = parse_question_rules("What is my emergency runway?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is False
        assert res["turn_type"] == "NEW_TOPIC"
        assert res["intent"] == "EMERGENCY_RUNWAY_ANALYSIS"
        # Must NOT pin runway to September 2025
        assert res["reporting_date"] is None

    def test_switch_to_new_purchase_item(self):
        history = [
            {"role": "user", "content": "Can I buy a phone for ₹15,000?"},
            {"role": "assistant", "content": "Affordability: SAFE."},
        ]
        res = parse_question_rules("Can I afford to buy a car for 800000?", conversation_history=history)
        assert res is not None
        assert res["is_followup"] is False
        assert res["turn_type"] == "NEW_TOPIC"
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 800000.0
        assert res["category"] == "Transport"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Missing Information & Ambiguity Clarifications
# ─────────────────────────────────────────────────────────────────────────────
class TestMissingInformationAndAmbiguity:
    def test_purchase_missing_amount_triggers_clarification(self):
        res = parse_question_rules("Can I buy a phone?")
        assert res is not None
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] is None
        assert res["needs_clarification"] is True
        assert res["clarification_type"] == "MISSING_AMOUNT"
        assert "specify the purchase amount" in res["clarification_message"].lower()

    def test_purchase_ambiguous_multiple_amounts(self):
        res = parse_question_rules("Can I spend 15k or 25k on a laptop?")
        assert res is not None
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["needs_clarification"] is True
        assert res["clarification_type"] == "AMBIGUOUS_AMOUNT"
        assert "multiple amounts" in res["clarification_message"].lower()

    def test_ambiguous_date_slash_format(self):
        res = parse_question_rules("How much did I spend on 04/05/2025?")
        assert res is not None
        assert res["is_date_ambiguous"] is True
        assert res["needs_clarification"] is True
        assert res["clarification_type"] == "AMBIGUOUS_DATE"
        assert "ambiguous" in res["clarification_message"].lower()

    def test_unambiguous_date_iso_format(self):
        res = parse_question_rules("How much did I spend on food in 2025-08?")
        assert res is not None
        assert res["is_date_ambiguous"] is False
        assert res["needs_clarification"] is False
        assert res["reporting_date"] == date(2025, 8, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Contradictory Historical Context & Defense Against False Claims
# ─────────────────────────────────────────────────────────────────────────────
class TestContradictoryHistoryDefense:
    def test_parser_ignores_unverified_claims_in_user_prompt(self):
        # User claims an exorbitant savings rate in their question
        res = parse_question_rules(
            "Earlier you told me my savings rate was 90%, so can I spend ₹50,000 on a phone?"
        )
        assert res is not None
        assert res["intent"] == "PURCHASE_SAFETY"
        assert res["amount"] == 50000.0
        assert res["category"] == "Shopping"
        # The parser does NOT output savings_rate = 90
        assert "savings_rate" not in res

    def test_parser_never_extracts_facts_from_assistant_turns(self):
        # History contains hallucinated or hypothetical assistant response
        history = [
            {"role": "user", "content": "Can I buy a phone for ₹15,000?"},
            {
                "role": "assistant",
                "content": "You have ₹2,000,000 in your savings account and 18 months of runway.",
            },
        ]
        # Follow-up
        res = parse_question_rules("What if it costs ₹18,000?", conversation_history=history)
        assert res is not None
        # Does NOT adopt ₹2,000,000 as the amount; adopts ₹18,000 from current user turn
        assert res["amount"] == 18000.0

    @pytest.mark.anyio
    async def test_graph_rag_recalculates_on_current_authorized_data(self):
        """
        Verify that GraphRAG always uses fresh authorized database records
        and ignores contradictory assertions in history.
        """
        mock_db = MagicMock()
        mock_db.get_purchase_context.return_value = {
            "monthly_income": 30000.0,
            "monthly_expenses": 25000.0,
            "total_savings": 10000.0,
            "pending_emis": 2000.0,
            "accounts": [{"id": "ACC1", "balance": 10000.0}],
            "incomes": [{"id": "INC1", "amount": 30000.0}],
        }

        graph_rag = GraphRAG(db=mock_db)

        history = [
            {"role": "user", "content": "I have 50 lakhs in savings."},
            {"role": "assistant", "content": "You have plenty of funds."},
        ]

        with patch("backend.app.rag.graph_rag.ask_llm_async", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "content": "🎯 The Quick Take: It is NOT SAFE.",
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "tokens_used": 150,
            }

            result = await graph_rag.process_query_async(
                question="Can I spend ₹50,000 on a phone?",
                user_id="U001",
                conversation_history=history,
            )

            assert result["recalculated_fresh"] is True
            # Verified against DB data (income 30k, savings 10k), NOT 50 lakhs!
            assert result["math_result"]["decision"] == "NOT_SAFE"
            assert result["intent"] == "PURCHASE_SAFETY"
            mock_db.get_purchase_context.assert_called_once_with("U001")

    @pytest.mark.anyio
    async def test_graph_rag_intercepts_clarification_before_math(self):
        """
        Verify that GraphRAG returns a clarification response rather than
        silently evaluating math with amount = 0.0 when amount is missing.
        """
        mock_db = MagicMock()
        graph_rag = GraphRAG(db=mock_db)

        result = await graph_rag.process_query_async(
            question="Can I buy a phone?",
            user_id="U001",
        )

        assert result["decision"] == "NEEDS_CLARIFICATION"
        assert result["needs_clarification"] is True
        assert result["clarification_type"] == "MISSING_AMOUNT"
        assert "specify the purchase amount" in result["explanation"].lower()
        # Verify db was NOT called for zero-amount calculation
        mock_db.get_purchase_context.assert_not_called()
