"""
Differential comparison test for financial planner budget limit rounding:
Pre-migration (float, ec6e2b9) vs Post-migration (integer paise, c8af934).
"""

from decimal import Decimal
import pytest

from backend.app.services.financial_planner import _calculate_budget_limits


def old_budget_limit_calc(current_spent: float, disc_cut_factor: float, is_disc: bool = True) -> tuple[float, float]:
    """
    Reference implementation copied verbatim from pre-migration commit ec6e2b9
    (backend/app/services/financial_planner.py, lines 145-154):

        if is_disc and current_spent > 0:
            reduction = round(current_spent * disc_cut_factor, 2)
            # Round limit to nearest 50 for clean human budgeting
            rec_limit = max(0.0, round((current_spent - reduction) / 50) * 50)
            potential = round(current_spent - rec_limit, 2)
        else:
            # Essential categories are preserved
            rec_limit = current_spent
            potential = 0.0
    """
    if is_disc and current_spent > 0:
        reduction = round(current_spent * disc_cut_factor, 2)
        rec_limit = max(0.0, round((current_spent - reduction) / 50) * 50)
        potential = round(current_spent - rec_limit, 2)
    else:
        rec_limit = current_spent
        potential = 0.0
    return rec_limit, potential


def new_budget_limit_calc(current_spent: float, disc_cut_factor: float) -> tuple[float, float]:
    """
    Calls the real planner code path (_calculate_budget_limits) on the current branch.
    Maps cut factor to savings_rate:
      - 0.25 -> savings_rate < 0 (e.g. -5.0)
      - 0.20 -> 0 <= savings_rate < 20 (e.g. 10.0)
      - 0.10 -> savings_rate >= 20 (e.g. 25.0)
    """
    sr_map = {0.25: -5.0, 0.20: 10.0, 0.10: 25.0}
    if disc_cut_factor not in sr_map:
        raise ValueError(f"Cut factor {disc_cut_factor} does not exist in planner's savings rate thresholds.")
    sr = sr_map[disc_cut_factor]
    res = _calculate_budget_limits(
        total_income=100000.0,
        total_expenses=current_spent,
        category_breakdown=[{"category": "Dining", "amount": current_spent, "percentage": 100.0}],
        savings_rate=sr,
    )
    cat = res["categories"][0]
    return cat["recommended_limit"], cat["potential_savings"]


def test_essential_category_zero_cut():
    """For essential categories (effective cut factor 0.0), old and new agree exactly."""
    res = _calculate_budget_limits(
        total_income=100000.0,
        total_expenses=1234.56,
        category_breakdown=[{"category": "Rent", "amount": 1234.56, "percentage": 100.0}],
        savings_rate=10.0,
    )
    cat = res["categories"][0]
    assert cat["recommended_limit"] == 1234.56
    assert cat["potential_savings"] == 0.0


@pytest.mark.parametrize("factor", [0.10, 0.20, 0.25])
def test_differential_sweep_categories(factor: float):
    """
    Differential analysis across current spend from 0.00 to 2000.00:
    - (a) old == new: majority of points
    - (b) tie-breaking differences: odd multiples of 0.5 where Python half-to-even rounds down to even,
          while Decimal ROUND_HALF_UP rounds up to odd.
    - (c) clamp to 5000 paise: count is 0 (the clamp was not implemented in code).
    - (d) negative potential in old code: old produced negative savings (current_spent < rec_limit),
          while new has max(0, current_spent_paise - rec_limit_paise).
    """
    for i in range(0, 200001, 100):  # Sampled fast sweep in test suite
        spend = round(i * 0.01, 2)
        old_lim, old_pot = old_budget_limit_calc(spend, factor)
        new_lim, new_pot = new_budget_limit_calc(spend, factor)

        if (old_lim, old_pot) == (new_lim, new_pot):
            continue

        reduction = round(spend * factor, 2)
        target = spend - reduction
        quot = target / 50.0
        is_tie_break = abs(abs(quot - round(quot)) - 0.5) < 1e-4

        if is_tie_break and old_lim != new_lim:
            # Category (b): intentional behavior change to ROUND_HALF_UP
            continue
        elif old_lim == new_lim and old_pot < 0 and new_pot == 0.0:
            # Category (d): intentional behavior change in new code: potential savings floored at 0
            continue
        else:
            pytest.fail(f"Unexpected difference at spend={spend}, factor={factor}: old=({old_lim}, {old_pot}), new=({new_lim}, {new_pot})")

