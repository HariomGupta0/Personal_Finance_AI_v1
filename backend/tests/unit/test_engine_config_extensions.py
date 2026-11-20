"""
Unit tests for config-driven thresholds and financial engine extensions (T6).
Verifies:
1. Default EngineConfig matches production defaults identically.
2. Custom emergency reserve multiplier modifies emergency fund & purchase safety requirement.
3. Custom DTI bands adjust risk classification thresholds.
4. Custom runway bands adjust status thresholds.
5. Custom health score weights and grade cutoffs modify scoring and letter grades.
6. Optional trailing-N-month average expense basis in purchase safety (off by default).
7. Optional fixed obligations deduction in purchase safety (off by default).
"""

from datetime import date
import pytest

from backend.app.engine.engine_config import (
    DEFAULT_ENGINE_CONFIG,
    DTIBands,
    EngineConfig,
    GradeCutoffs,
    HealthScoreWeights,
    RunwayBands,
)
from backend.app.engine.financial_engine import (
    calculate_comprehensive_health,
    calculate_debt_burden,
    calculate_emergency_fund,
    calculate_emergency_runway,
    check_purchase_safety,
)


@pytest.fixture
def sample_context():
    return {
        "accounts": [{"id": "acc1", "balance": 150000.0, "balance_paise": 15000000}],
        "transactions": [
            {"id": "tx1", "type": "EXPENSE", "amount": 20000.0, "amount_paise": 2000000, "date": "2026-10-05"},
            {"id": "tx2", "type": "EXPENSE", "amount": 10000.0, "amount_paise": 1000000, "date": "2026-10-15"},
            # Previous month expenses for trailing average tests
            {"id": "tx3", "type": "EXPENSE", "amount": 60000.0, "amount_paise": 6000000, "date": "2026-09-10"},
            {"id": "tx4", "type": "EXPENSE", "amount": 90000.0, "amount_paise": 9000000, "date": "2026-08-10"},
        ],
        "incomes": [
            {"id": "inc1", "amount": 100000.0, "amount_paise": 10000000, "date": "2026-10-01"}
        ],
        "loans": [
            {"id": "l1", "name": "Auto Loan", "outstanding": 200000.0, "emi": 15000.0, "status": "PENDING", "due_date": "2026-10-20"}
        ],
        "goals": [
            {"name": "Emergency Fund", "current_amount": 50000.0}
        ],
    }


class TestEngineConfigDefaults:
    def test_default_config_values(self):
        cfg = DEFAULT_ENGINE_CONFIG
        assert cfg.emergency_reserve_multiplier == 3
        assert cfg.dti_bands.healthy_max == 20.0
        assert cfg.dti_bands.moderate_max == 35.0
        assert cfg.dti_bands.high_max == 50.0
        assert cfg.runway_bands.critical_max == 1.0
        assert cfg.runway_bands.insufficient_max == 3.0
        assert cfg.runway_bands.healthy_max == 6.0
        assert cfg.runway_bands.target_months == 3.0
        assert cfg.health_weights.savings_max_score == 35.0
        assert cfg.health_weights.savings_target_rate == 20.0
        assert cfg.health_weights.runway_max_score == 35.0
        assert cfg.health_weights.runway_target_months == 3.0
        assert cfg.health_weights.debt_max_score == 30.0
        assert cfg.health_weights.debt_min_dti == 20.0
        assert cfg.health_weights.debt_max_dti == 50.0
        assert cfg.grade_cutoffs.grade_a_min == 85.0
        assert cfg.grade_cutoffs.grade_b_min == 70.0
        assert cfg.grade_cutoffs.grade_c_min == 50.0
        assert cfg.trailing_n_months is None
        assert cfg.fixed_obligations_default == 0.0

    def test_frozen_dataclass_immutability(self):
        cfg = DEFAULT_ENGINE_CONFIG
        with pytest.raises(Exception):
            cfg.emergency_reserve_multiplier = 6  # type: ignore


class TestCustomEmergencyReserveMultiplier:
    def test_emergency_fund_with_custom_multiplier(self, sample_context):
        # October expenses = 30,000
        # Default 3x = 90,000
        default_res = calculate_emergency_fund(sample_context, reporting_date="2026-10-15")
        assert default_res["recommended_fund"] == 90000.0
        assert default_res["shortfall"] == 40000.0  # 90000 - 50000

        # Custom 6x = 180,000
        custom_cfg = EngineConfig(emergency_reserve_multiplier=6)
        custom_res = calculate_emergency_fund(sample_context, reporting_date="2026-10-15", config=custom_cfg)
        assert custom_res["recommended_fund"] == 180000.0
        assert custom_res["shortfall"] == 130000.0  # 180000 - 50000


class TestCustomDTIBands:
    def test_dti_bands_classification(self, sample_context):
        # Income = 100,000, EMI = 15,000 -> DTI = 15%
        # Default: <= 20% is LOW
        res_default = calculate_debt_burden(sample_context, reporting_date="2026-10-15")
        assert res_default["dti_ratio"] == 15.0
        assert res_default["risk_level"] == "LOW"

        # Tighter custom bands: healthy <= 10%, moderate <= 25%
        custom_cfg = EngineConfig(dti_bands=DTIBands(healthy_max=10.0, moderate_max=25.0, high_max=40.0))
        res_custom = calculate_debt_burden(sample_context, reporting_date="2026-10-15", config=custom_cfg)
        assert res_custom["risk_level"] == "MODERATE"


class TestCustomRunwayBands:
    def test_runway_bands_classification(self, sample_context):
        # Balance = 150,000, Expenses = 30,000 -> Runway = 5.0 months
        # Default: >= 6.0 STRONG, >= 3.0 HEALTHY -> HEALTHY
        res_default = calculate_emergency_runway(sample_context, reporting_date="2026-10-15")
        assert res_default["runway_months"] == 5.0
        assert res_default["status"] == "HEALTHY"

        # Custom bands where >= 4.0 is STRONG
        custom_cfg = EngineConfig(runway_bands=RunwayBands(critical_max=1.0, insufficient_max=2.0, healthy_max=4.0))
        res_custom = calculate_emergency_runway(sample_context, reporting_date="2026-10-15", config=custom_cfg)
        assert res_custom["status"] == "STRONG"


class TestCustomHealthWeightsAndGradeCutoffs:
    def test_health_weights_and_grade_cutoffs(self, sample_context):
        # Default evaluation
        res_default = calculate_comprehensive_health(sample_context, reporting_date="2026-10-15")
        assert isinstance(res_default["health_score"], float)

        # Heavily penalize debt by shifting weights to debt (Debt max 70 pts)
        custom_weights = HealthScoreWeights(
            savings_max_score=15.0,
            runway_max_score=15.0,
            debt_max_score=70.0,
            debt_min_dti=5.0,  # 15% DTI is well above 5% min
            debt_max_dti=25.0,
        )
        custom_cutoffs = GradeCutoffs(grade_a_min=95.0, grade_b_min=80.0, grade_c_min=60.0)
        custom_cfg = EngineConfig(health_weights=custom_weights, grade_cutoffs=custom_cutoffs)

        res_custom = calculate_comprehensive_health(sample_context, reporting_date="2026-10-15", config=custom_cfg)
        assert res_custom["health_score"] != res_default["health_score"]


class TestPurchaseSafetyExtensions:
    def test_defaults_maintain_exact_behavior(self, sample_context):
        # Balance = 150,000, EMI = 15,000, Purchase = 10,000
        # Oct expenses = 30,000, 3x reserve = 90,000
        # Balance after = 150,000 - 15,000 - 10,000 = 125,000 >= 90,000 -> SAFE
        res = check_purchase_safety(sample_context, purchase_amount=10000.0, reporting_date="2026-10-15")
        assert res["decision"] == "SAFE"
        assert res["risk_level"] == "LOW"
        assert "fixed_obligations" not in res["evidence"]
        assert "trailing_n_months" not in res["evidence"]
        assert "After the pending EMI and purchase," in res["reason"]

    def test_fixed_obligations_deduction(self, sample_context):
        # Balance = 150,000, EMI = 15,000, Purchase = 10,000
        # Reserve requirement = 90,000
        # With fixed_obligations = 40,000:
        # Balance after = 150,000 - 15,000 - 40,000 - 10,000 = 85,000 < 90,000 -> NOT_SAFE!
        res = check_purchase_safety(
            sample_context,
            purchase_amount=10000.0,
            reporting_date="2026-10-15",
            fixed_obligations=40000.0,
        )
        assert res["decision"] == "NOT_SAFE"
        assert res["evidence"]["fixed_obligations"] == 40000.0
        assert res["evidence"]["balance_after_purchase"] == 85000.0
        assert "pending EMI, fixed obligations, and purchase" in res["reason"]

    def test_trailing_n_month_average_expense_basis(self, sample_context):
        # Oct expenses = 30,000
        # Sep expenses = 60,000
        # Aug expenses = 90,000
        # 3-month total = 180,000 -> 3-month average = 60,000 / month
        # 3x emergency reserve based on trailing-3 average = 180,000
        # Balance = 150,000, EMI = 15,000, Purchase = 10,000
        # Balance after = 125,000 < 180,000 -> NOT_SAFE!
        res = check_purchase_safety(
            sample_context,
            purchase_amount=10000.0,
            reporting_date="2026-10-15",
            trailing_n_months=3,
        )
        assert res["decision"] == "NOT_SAFE"
        assert res["evidence"]["monthly_expenses"] == 60000.0
        assert res["evidence"]["emergency_requirement"] == 180000.0
        assert res["evidence"]["trailing_n_months"] == 3
