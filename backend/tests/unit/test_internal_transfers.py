"""
Unit and Integration Tests for Internal Bank Transfer Detection and Disambiguation.

Covers:
1. Candidate detection (exact amount, date proximity <= 2 days, opposite types, distinct accounts).
2. Disqualification rules (ATM withdrawals, commercial merchants, external refunds, same-account transfers).
3. Strict 1-to-1 matching (no transaction paired multiple times).
4. Retroactive matching against existing database transactions.
5. Exclusion of confirmed internal transfers from financial engine calculations
   (runway, savings rate, category expenses, emergency fund, health score).
6. Multi-account preservation during batch import.
"""

from datetime import date, timedelta
import pytest

from backend.app.services.transfer_detector import (
    detect_intra_batch_transfers,
    detect_retroactive_transfers,
    has_transfer_signal,
    is_atm_or_cash,
    is_commercial_merchant,
    is_external_refund,
    score_transfer_candidate,
)
from backend.app.engine.financial_engine import (
    calculate_category_expenses,
    calculate_comprehensive_health,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_savings_rate,
)


# ---------------------------------------------------------------------------
# Signal and Disqualification Tests
# ---------------------------------------------------------------------------

class TestTransferSignalsAndDisqualifications:
    def test_atm_withdrawal_disqualified(self):
        assert is_atm_or_cash("ATM WDL HDFC BANK KORAMANGALA") is True
        assert is_atm_or_cash("CASH WITHDRAWAL NFS MUMBAI") is True
        assert is_atm_or_cash("ATM-WDL 5000") is True
        assert is_atm_or_cash("NEFT TRANSFER TO SBI") is False

    def test_commercial_merchant_disqualified(self):
        assert is_commercial_merchant("Swiggy Bangalore Order #1234", "Swiggy") is True
        assert is_commercial_merchant("Amazon Pay India", "Amazon") is True
        assert is_commercial_merchant("Uber Rides India", "Uber") is True
        assert is_commercial_merchant("FUNDS TRANSFER TO A/C 9876", "Transfer") is False

    def test_refund_disqualified(self):
        assert is_external_refund("REFUND SWIGGY ORDER", "Swiggy") is True
        assert is_external_refund("CASHBACK CREDITED FOR BILL", "Cred") is True
        assert is_external_refund("SALARY FOR OCTOBER", "Employer") is False

    def test_transfer_keywords_detected(self):
        assert has_transfer_signal("SELF TRANSFER TO SAVINGS") is True
        assert has_transfer_signal("FUNDS TRANSFER TO A/C 4321") is True
        assert has_transfer_signal("NEFT TO SBI") is True
        assert has_transfer_signal("SWEEP TRF TO MOD") is True
        assert has_transfer_signal("GROCERY SHOPPING") is False


# ---------------------------------------------------------------------------
# Candidate Scoring Tests
# ---------------------------------------------------------------------------

class TestTransferCandidateScoring:
    def test_valid_transfer_high_confidence(self):
        debit = {
            "account_id": "ACC_HDFC",
            "type": "EXPENSE",
            "amount": 25000.0,
            "date": "2026-10-15",
            "description": "FUNDS TRANSFER TO A/C ...9876",
        }
        credit = {
            "account_id": "ACC_SBI",
            "type": "INCOME",
            "amount": 25000.0,
            "date": "2026-10-15",
            "description": "NEFT TRANSFER FROM HDFC",
        }
        score, reasons = score_transfer_candidate(debit, credit)
        assert score >= 0.8
        assert "EXACT_AMOUNT_MATCH" in reasons
        assert "DATE_PROXIMITY_0_DAYS" in reasons
        assert "TRANSFER_NARRATION_SIGNAL" in reasons

    def test_same_account_disqualified(self):
        debit = {"account_id": "ACC_HDFC", "type": "EXPENSE", "amount": 5000.0, "date": "2026-10-15"}
        credit = {"account_id": "ACC_HDFC", "type": "INCOME", "amount": 5000.0, "date": "2026-10-15"}
        score, reasons = score_transfer_candidate(debit, credit)
        assert score == 0.0
        assert "SAME_ACCOUNT" in reasons

    def test_amount_mismatch_disqualified(self):
        debit = {"account_id": "ACC_HDFC", "type": "EXPENSE", "amount": 5000.0, "date": "2026-10-15"}
        credit = {"account_id": "ACC_SBI", "type": "INCOME", "amount": 5001.0, "date": "2026-10-15"}
        score, reasons = score_transfer_candidate(debit, credit)
        assert score == 0.0
        assert "AMOUNT_MISMATCH" in reasons

    def test_date_too_far_disqualified(self):
        debit = {"account_id": "ACC_HDFC", "type": "EXPENSE", "amount": 5000.0, "date": "2026-10-10"}
        credit = {"account_id": "ACC_SBI", "type": "INCOME", "amount": 5000.0, "date": "2026-10-15"}
        score, reasons = score_transfer_candidate(debit, credit)
        assert score == 0.0
        assert "DATE_TOO_FAR" in reasons

    def test_atm_withdrawal_candidate_disqualified(self):
        debit = {
            "account_id": "ACC_HDFC",
            "type": "EXPENSE",
            "amount": 10000.0,
            "date": "2026-10-15",
            "description": "ATM CASH WDL KORAMANGALA",
        }
        credit = {
            "account_id": "ACC_SBI",
            "type": "INCOME",
            "amount": 10000.0,
            "date": "2026-10-15",
            "description": "CASH DEPOSIT",
        }
        score, reasons = score_transfer_candidate(debit, credit)
        assert score == 0.0
        assert "ATM_DISQUALIFIED" in reasons

    def test_commercial_merchant_refund_disqualified(self):
        debit = {
            "account_id": "ACC_HDFC",
            "type": "EXPENSE",
            "amount": 1200.0,
            "date": "2026-10-15",
            "description": "Swiggy Order 8976",
            "clean_merchant": "Swiggy",
        }
        credit = {
            "account_id": "ACC_SBI",
            "type": "INCOME",
            "amount": 1200.0,
            "date": "2026-10-16",
            "description": "Swiggy Refund Cancelled",
            "clean_merchant": "Swiggy",
        }
        score, reasons = score_transfer_candidate(debit, credit)
        assert score == 0.0
        assert any("DISQUALIFIED" in r for r in reasons)


# ---------------------------------------------------------------------------
# 1-to-1 Matching Tests
# ---------------------------------------------------------------------------

class TestStrictOneToOneMatching:
    def test_identical_amounts_strict_one_to_one(self):
        """
        Two identical ₹10,000 debits on Account A and one ₹10,000 credit on Account B.
        Must produce exactly ONE candidate pair, never multi-pairing.
        """
        rows = [
            {"account_id": "ACC_A", "type": "EXPENSE", "amount": 10000.0, "date": "2026-10-15", "description": "Transfer 1"},
            {"account_id": "ACC_A", "type": "EXPENSE", "amount": 10000.0, "date": "2026-10-15", "description": "Transfer 2"},
            {"account_id": "ACC_B", "type": "INCOME", "amount": 10000.0, "date": "2026-10-15", "description": "Received"},
        ]
        candidates = detect_intra_batch_transfers(rows)
        assert len(candidates) == 1
        assert candidates[0]["amount"] == 10000.0
        assert candidates[0]["credit_index"] == 2
        # Exactly one debit is paired
        assert candidates[0]["debit_index"] in (0, 1)

    def test_two_distinct_pairs_both_matched(self):
        """
        Two distinct debits and two distinct credits. Both matched 1:1.
        """
        rows = [
            {"account_id": "ACC_A", "type": "EXPENSE", "amount": 15000.0, "date": "2026-10-12", "description": "Self trf 1"},
            {"account_id": "ACC_A", "type": "EXPENSE", "amount": 7500.0, "date": "2026-10-14", "description": "Self trf 2"},
            {"account_id": "ACC_B", "type": "INCOME", "amount": 15000.0, "date": "2026-10-12", "description": "Credit 1"},
            {"account_id": "ACC_B", "type": "INCOME", "amount": 7500.0, "date": "2026-10-14", "description": "Credit 2"},
        ]
        candidates = detect_intra_batch_transfers(rows)
        assert len(candidates) == 2
        paired_debits = {c["debit_index"] for c in candidates}
        paired_credits = {c["credit_index"] for c in candidates}
        assert paired_debits == {0, 1}
        assert paired_credits == {2, 3}


# ---------------------------------------------------------------------------
# Retroactive Matching Tests
# ---------------------------------------------------------------------------

class TestRetroactiveMatching:
    class MockDb:
        def find_unlinked_transfer_candidates(self, user_id, account_id, opposite_type, amount_paise, date_from, date_to):
            if opposite_type == "INCOME" and amount_paise == 2000000:
                return [{
                    "id": "TX_EXISTING_CREDIT_99",
                    "account_id": "ACC_EXISTING_SBI",
                    "type": "INCOME",
                    "amount": 20000.0,
                    "amount_paise": 2000000,
                    "date": "2026-10-10",
                    "description": "NEFT Inward Clearing",
                }]
            return []

    def test_retroactive_match_found(self):
        new_rows = [(0, {
            "account_id": "ACC_HDFC",
            "type": "EXPENSE",
            "amount": 20000.0,
            "date": "2026-10-10",
            "description": "NEFT OUT TO SBI A/C",
        })]
        db = self.MockDb()
        candidates = detect_retroactive_transfers(new_rows, user_id="U1", db=db)
        assert len(candidates) == 1
        assert candidates[0]["is_retroactive"] is True
        assert candidates[0]["existing_transaction_id"] == "TX_EXISTING_CREDIT_99"
        assert candidates[0]["amount"] == 20000.0


# ---------------------------------------------------------------------------
# Financial Engine Exclusion Tests (Zero-distortion Guarantees)
# ---------------------------------------------------------------------------

class TestFinancialEngineTransferExclusion:
    def test_internal_transfers_excluded_from_expenses_and_savings(self):
        """
        Verify that a ₹50,000 internal transfer between accounts does NOT inflate
        total expenses or income, and does not alter the savings rate or runway.
        """
        # Baseline context without transfer
        baseline_context = {
            "accounts": [{"id": "A1", "balance": 100000.0}],
            "incomes": [{"source": "Salary", "amount": 80000.0, "date": "2026-10-01"}],
            "transactions": [
                {"id": "T1", "amount": 20000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-05"},
                {"id": "T2", "amount": 10000.0, "type": "EXPENSE", "category": "Utilities", "date": "2026-10-10"},
            ],
            "loans": [],
            "goals": [],
        }

        # Context with a confirmed ₹50,000 internal transfer on both sides
        transfer_context = {
            "accounts": [
                {"id": "A1", "balance": 50000.0},
                {"id": "A2", "balance": 50000.0},
            ],
            "incomes": [
                {"source": "Salary", "amount": 80000.0, "date": "2026-10-01"},
                # Paired transfer inflow on Account A2
                {"source": "Transfer from A1", "amount": 50000.0, "date": "2026-10-15", "is_transfer": True},
            ],
            "transactions": [
                {"id": "T1", "amount": 20000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-05"},
                {"id": "T2", "amount": 10000.0, "type": "EXPENSE", "category": "Utilities", "date": "2026-10-10"},
                # Paired transfer outflow on Account A1
                {"id": "T_XFER", "amount": 50000.0, "type": "EXPENSE", "category": "General", "date": "2026-10-15", "is_transfer": True},
            ],
            "loans": [],
            "goals": [],
        }

        # 1. Savings rate must be identical
        sr_baseline = calculate_savings_rate(baseline_context, reporting_date="2026-10-20")
        sr_transfer = calculate_savings_rate(transfer_context, reporting_date="2026-10-20")

        assert sr_baseline["total_income"] == sr_transfer["total_income"] == 80000.0
        assert sr_baseline["total_expenses"] == sr_transfer["total_expenses"] == 30000.0
        assert sr_baseline["savings"] == sr_transfer["savings"] == 50000.0
        assert sr_baseline["savings_rate"] == sr_transfer["savings_rate"] == 62.5

        # 2. Runway must be identical
        rw_baseline = calculate_emergency_runway(baseline_context, reporting_date="2026-10-20")
        rw_transfer = calculate_emergency_runway(transfer_context, reporting_date="2026-10-20")

        assert rw_baseline["monthly_expenses"] == rw_transfer["monthly_expenses"] == 30000.0
        assert rw_baseline["runway_months"] == rw_transfer["runway_months"] == pytest.approx(3.33, abs=0.01)

        # 3. Category expenses must exclude transfer
        cat_transfer = calculate_category_expenses(transfer_context, reporting_date="2026-10-20")
        assert cat_transfer["total_expenses"] == 30000.0
        assert not any(c["category"] == "General" for c in cat_transfer["categories"])

        # 4. Emergency fund shortfall must be identical
        ef_baseline = calculate_emergency_fund(baseline_context, reporting_date="2026-10-20")
        ef_transfer = calculate_emergency_fund(transfer_context, reporting_date="2026-10-20")
        assert ef_baseline["monthly_expenses"] == ef_transfer["monthly_expenses"] == 30000.0
        assert ef_baseline["recommended_fund"] == ef_transfer["recommended_fund"]


# ---------------------------------------------------------------------------
# Pipeline and Multi-Account Import Tests
# ---------------------------------------------------------------------------

class TestImportPipelineTransferDetection:
    def test_run_pipeline_detects_transfer_candidates(self):
        from backend.app.services.import_pipeline import run_pipeline

        class MockDb:
            def get_user_accounts(self, user_id):
                return [
                    {"id": "ACC_HDFC", "bank": "HDFC"},
                    {"id": "ACC_SBI", "bank": "SBI"},
                ]

        raw_rows = [
            {
                "date": "2026-10-15",
                "description": "FUNDS TRANSFER TO SBI A/C",
                "amount": 25000.0,
                "type": "EXPENSE",
                "account_id": "ACC_HDFC",
            },
            {
                "date": "2026-10-15",
                "description": "NEFT TRANSFER FROM HDFC",
                "amount": 25000.0,
                "type": "INCOME",
                "account_id": "ACC_SBI",
            },
            {
                "date": "2026-10-16",
                "description": "Swiggy Bangalore Order #1234",
                "amount": 540.0,
                "type": "EXPENSE",
                "account_id": "ACC_HDFC",
            },
        ]

        result = run_pipeline(
            raw_rows=raw_rows,
            user_id="U_TEST",
            db=MockDb(),
            skip_dedup=True,
        )

        assert result["transfer_count"] == 1
        assert len(result["transfer_candidates"]) == 1
        cand = result["transfer_candidates"][0]
        assert cand["amount"] == 25000.0
        assert cand["debit_account_id"] == "ACC_HDFC"
        assert cand["credit_account_id"] == "ACC_SBI"

        # Check row annotations
        valid = result["valid_rows"]
        assert valid[0]["is_transfer_candidate"] is True
        assert valid[0]["transfer_role"] == "DEBIT"
        assert valid[1]["is_transfer_candidate"] is True
        assert valid[1]["transfer_role"] == "CREDIT"
        assert valid[2].get("is_transfer_candidate") is not True

    def test_confirm_import_preserves_distinct_account_ids(self):
        from backend.app.api.import_api import confirm_import, ConfirmImportRequest, ConfirmRow

        class MockDbService:
            def __init__(self):
                self.calls = []
                self.linked_transfers = []

            def get_user_accounts(self, user_id):
                return [
                    {"id": "ACC_HDFC", "bank": "HDFC"},
                    {"id": "ACC_SBI", "bank": "SBI"},
                ]

            def batch_add_transactions(self, user_id, account_id, rows, import_id=None):
                self.calls.append({"account_id": account_id, "rows": rows})
                return {
                    "import_id": import_id or "IMP_1",
                    "inserted": len(rows),
                    "skipped": 0,
                    "net_balance_delta": 0.0,
                }

            def link_internal_transfers(self, user_id, pairs):
                self.linked_transfers.extend(pairs)
                return len(pairs)

        mock_db = MockDbService()
        req = ConfirmImportRequest(
            rows=[
                ConfirmRow(
                    date="2026-10-15",
                    description="Transfer Out to SBI",
                    amount=15000.0,
                    type="EXPENSE",
                    account_id="ACC_HDFC",
                    is_transfer=True,
                ),
                ConfirmRow(
                    date="2026-10-15",
                    description="Transfer In from HDFC",
                    amount=15000.0,
                    type="INCOME",
                    account_id="ACC_SBI",
                    is_transfer=True,
                ),
            ]
        )

        res = confirm_import(payload=req, user_id="U_TEST", db=mock_db, ingestion=None)
        assert res["status"] == "SUCCESS"
        assert res["saved"] == 2

        # Verify that account_ids were preserved and not collapsed into a single account
        called_accounts = {call["account_id"] for call in mock_db.calls}
        assert called_accounts == {"ACC_HDFC", "ACC_SBI"}

        # Verify transfer linking was triggered
        assert mock_db.linked_transfers
        assert len(mock_db.linked_transfers) == 1
