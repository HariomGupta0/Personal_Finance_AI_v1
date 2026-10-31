"""
Unit tests for API request models amount normalization.
Verifies that SignupRequest, GoalSchema, TransactionCreateSchema,
TransactionUpdateSchema, and ConfirmRow normalize amounts via money.normalize_rupees.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from backend.app.api.auth import SignupRequest
from backend.app.api.goals import GoalSchema
from backend.app.api.transactions import TransactionCreateSchema, TransactionUpdateSchema
from backend.app.api.import_api import ConfirmRow


def test_signup_request_amount_normalization():
    # Valid normalizations
    req1 = SignupRequest(username="testuser", password="password123", initial_balance=1234.565)
    assert req1.initial_balance == 1234.57

    req2 = SignupRequest(username="testuser", password="password123", initial_balance=0.1 + 0.2)
    assert req2.initial_balance == 0.30

    req3 = SignupRequest(username="testuser", password="password123", initial_balance="1,234.50")
    assert req3.initial_balance == 1234.50

    req4 = SignupRequest(username="testuser", password="password123", initial_balance=19999.99)
    assert req4.initial_balance == 19999.99

    req5 = SignupRequest(username="testuser", password="password123", initial_balance=33.335)
    assert req5.initial_balance == 33.34

    req6 = SignupRequest(username="testuser", password="password123", initial_balance=-0.0)
    assert req6.initial_balance == 0.0

    # Invalid / out-of-bounds inputs raise ValidationError as before
    with pytest.raises(ValidationError):
        SignupRequest(username="testuser", password="password123", initial_balance=-10.0)

    with pytest.raises(ValidationError):
        SignupRequest(username="testuser", password="password123", initial_balance="invalid_str")


def test_goal_schema_amount_normalization():
    goal1 = GoalSchema(name="Car", target_amount=1234.565, current_amount=33.335)
    assert goal1.target_amount == 1234.57
    assert goal1.current_amount == 33.34

    goal2 = GoalSchema(name="Emergency", target_amount="1,00,000.50", current_amount="25,000.25")
    assert goal2.target_amount == 100000.50
    assert goal2.current_amount == 25000.25

    goal3 = GoalSchema(name="House", target_amount=0.1 + 0.2)
    assert goal3.target_amount == 0.30
    assert goal3.current_amount is None

    # Invalid string raises ValidationError
    with pytest.raises(ValidationError):
        GoalSchema(name="Car", target_amount="abc")


def test_transaction_schemas_amount_normalization():
    # TransactionCreateSchema
    t1 = TransactionCreateSchema(amount=1234.565)
    assert t1.amount == 1234.57

    t2 = TransactionCreateSchema(amount="1,234.50")
    assert t2.amount == 1234.50

    t3 = TransactionCreateSchema(amount=0.1 + 0.2)
    assert t3.amount == 0.30

    t4 = TransactionCreateSchema(amount=33.335)
    assert t4.amount == 33.34

    # Amount > 0 constraint maintained
    with pytest.raises(ValidationError):
        TransactionCreateSchema(amount=0)

    with pytest.raises(ValidationError):
        TransactionCreateSchema(amount=-50.0)

    with pytest.raises(ValidationError):
        TransactionCreateSchema(amount="invalid")

    # TransactionUpdateSchema
    u1 = TransactionUpdateSchema(amount=19999.99)
    assert u1.amount == 19999.99

    u2 = TransactionUpdateSchema(amount="500.555")
    assert u2.amount == 500.56

    u3 = TransactionUpdateSchema(amount=None)
    assert u3.amount is None


def test_confirm_row_amount_normalization():
    r1 = ConfirmRow(
        date="2026-10-01",
        description="Grocery Store",
        amount=1234.565,
        type="EXPENSE",
    )
    assert r1.amount == 1234.57

    r2 = ConfirmRow(
        date="2026-10-01",
        description="Salary",
        amount="1,00,000.50",
        type="INCOME",
    )
    assert r2.amount == 100000.50

    r3 = ConfirmRow(
        date="2026-10-01",
        description="Coffee",
        amount=33.335,
        type="EXPENSE",
    )
    assert r3.amount == 33.34

    # Rejection of zero and negative values
    with pytest.raises(ValidationError):
        ConfirmRow(date="2026-10-01", description="Zero", amount=0, type="EXPENSE")

    with pytest.raises(ValidationError):
        ConfirmRow(date="2026-10-01", description="Neg", amount=-10.0, type="EXPENSE")

    with pytest.raises(ValidationError):
        ConfirmRow(date="2026-10-01", description="Bad", amount="not_a_number", type="EXPENSE")
