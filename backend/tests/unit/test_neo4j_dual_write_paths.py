"""
Unit and integration tests for hardened dual-write paths and exact Decimal parity in Neo4j.
Verifies:
- add_income (balance paise and legacy twin exact, with ugly cents)
- add_or_update_goal (create and update, both target_amount and current_amount)
- add_loan (principal and outstanding)
- add_emi (amount)
- pay_emi (account balance paise and legacy twin exact after payment)
- update_transaction with category_name=None and with a category given (both return rows; rel updates only when given)
- Final sweep asserting Decimal(str(legacy)) == Decimal(paise) / Decimal(100) on all touched nodes
"""

from decimal import Decimal
import uuid
import pytest

from backend.app.database.neo4j_service import Neo4jService
from backend.app.core.money import to_paise
from backend.scripts.seed_db import seed_database


@pytest.fixture(scope="module", autouse=True)
def setup_seeded_database():
    """Ensure clean seeded database state before running suite."""
    seed_database()
    svc = Neo4jService()
    yield svc
    svc.close()


@pytest.fixture
def clean_user_context(setup_seeded_database):
    """Provide a fresh user and account for isolated dual-write testing, cleaned up after."""
    svc = setup_seeded_database
    u_suffix = uuid.uuid4().hex[:8].upper()
    user = svc.create_user(
        username=f"dw_user_{u_suffix.lower()}",
        password="SecretPassword123!",
        initial_balance=1000.00,
        bank_name="DualWrite Bank",
    )
    uid = user["user_id"]
    aid = user["account_id"]
    yield svc, uid, aid

    # Teardown: detach delete all test nodes for this user
    with svc.driver.session(database=svc.database) as session:
        session.run(
            """
            MATCH (u:User {id: $uid})
            OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)
            OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction)
            OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(i:Income)
            OPTIONAL MATCH (u)-[:HAS_LOAN]->(l:Loan)
            OPTIONAL MATCH (l)-[:HAS_EMI]->(e:EMI)
            OPTIONAL MATCH (u)-[:HAS_GOAL]->(g:Goal)
            DETACH DELETE u, a, t, i, l, e, g
            """,
            uid=uid,
        )


def test_add_income_dual_write_exact(clean_user_context):
    svc, uid, aid = clean_user_context
    # Starting balance: 1000.00 (100000 paise)
    # Add income with ugly cents: 1234.56 (123456 paise)
    inc = svc.add_income(user_id=uid, source="Consulting Bonus", amount=1234.56, account_id=aid)
    assert inc["amount"] == 1234.56

    with svc.driver.session(database=svc.database) as session:
        # Check Account
        a_row = session.run("MATCH (a:Account {id: $aid}) RETURN a.balance_paise AS bp, a.balance AS b", aid=aid).single()
        assert a_row["bp"] == 223456
        assert a_row["b"] == 2234.56
        assert Decimal(str(a_row["b"])) == Decimal(a_row["bp"]) / Decimal(100)

        # Check Income node
        i_row = session.run("MATCH (i:Income {id: $iid}) RETURN i.amount_paise AS ap, i.amount AS a", iid=inc["income_id"]).single()
        assert i_row["ap"] == 123456
        assert i_row["a"] == 1234.56
        assert Decimal(str(i_row["a"])) == Decimal(i_row["ap"]) / Decimal(100)


def test_add_or_update_goal_dual_write_exact(clean_user_context):
    svc, uid, aid = clean_user_context
    # 1. Create Goal
    g_create = svc.add_or_update_goal(
        user_id=uid,
        name="House Downpayment",
        target_amount=54321.09,
        current_amount=12345.67,
    )
    gid = g_create["id"]

    with svc.driver.session(database=svc.database) as session:
        row1 = session.run(
            "MATCH (g:Goal {id: $gid}) RETURN g.target_amount_paise AS tp, g.target_amount AS t, g.current_amount_paise AS cp, g.current_amount AS c",
            gid=gid,
        ).single()
        assert row1["tp"] == 5432109
        assert row1["t"] == 54321.09
        assert row1["cp"] == 1234567
        assert row1["c"] == 12345.67
        assert Decimal(str(row1["t"])) == Decimal(row1["tp"]) / Decimal(100)
        assert Decimal(str(row1["c"])) == Decimal(row1["cp"]) / Decimal(100)

    # 2. Update Goal
    g_up = svc.add_or_update_goal(
        user_id=uid,
        name="House Downpayment",
        target_amount=60000.50,
        current_amount=25000.25,
    )
    with svc.driver.session(database=svc.database) as session:
        row2 = session.run(
            "MATCH (g:Goal {id: $gid}) RETURN g.target_amount_paise AS tp, g.target_amount AS t, g.current_amount_paise AS cp, g.current_amount AS c",
            gid=gid,
        ).single()
        assert row2["tp"] == 6000050
        assert row2["t"] == 60000.50
        assert row2["cp"] == 2500025
        assert row2["c"] == 25000.25
        assert Decimal(str(row2["t"])) == Decimal(row2["tp"]) / Decimal(100)
        assert Decimal(str(row2["c"])) == Decimal(row2["cp"]) / Decimal(100)


def test_add_loan_and_emi_dual_write_exact(clean_user_context):
    svc, uid, aid = clean_user_context
    # Add Loan
    loan = svc.add_loan(user_id=uid, name="Car Loan", principal=98765.43, outstanding=87654.32)
    lid = loan["id"]

    with svc.driver.session(database=svc.database) as session:
        l_row = session.run(
            "MATCH (l:Loan {id: $lid}) RETURN l.principal_paise AS pp, l.principal AS p, l.outstanding_paise AS op, l.outstanding AS o",
            lid=lid,
        ).single()
        assert l_row["pp"] == 9876543
        assert l_row["p"] == 98765.43
        assert l_row["op"] == 8765432
        assert l_row["o"] == 87654.32
        assert Decimal(str(l_row["p"])) == Decimal(l_row["pp"]) / Decimal(100)
        assert Decimal(str(l_row["o"])) == Decimal(l_row["op"]) / Decimal(100)

    # Add EMI
    emi = svc.add_emi(loan_id=lid, amount=4321.09, user_id=uid)
    eid = emi["id"]

    with svc.driver.session(database=svc.database) as session:
        e_row = session.run(
            "MATCH (e:EMI {id: $eid}) RETURN e.amount_paise AS ep, e.amount AS e",
            eid=eid,
        ).single()
        assert e_row["ep"] == 432109
        assert e_row["e"] == 4321.09
        assert Decimal(str(e_row["e"])) == Decimal(e_row["ep"]) / Decimal(100)


def test_pay_emi_dual_write_exact(clean_user_context):
    svc, uid, aid = clean_user_context
    # Starting account balance: 1000.00 = 100000 paise
    loan = svc.add_loan(user_id=uid, name="Bike Loan", principal=50000.0, outstanding=50000.0)
    emi = svc.add_emi(loan_id=loan["id"], amount=450.25, user_id=uid)
    eid = emi["id"]

    # Execute update_emi_status (the EMI payment method)
    paid_res = svc.update_emi_status(emi_id=eid, status="PAID", account_id=aid, user_id=uid)
    assert paid_res["status"] == "PAID"

    # 100000 - 45025 = 54975 paise = 549.75 rupees
    with svc.driver.session(database=svc.database) as session:
        a_row = session.run(
            "MATCH (a:Account {id: $aid}) RETURN a.balance_paise AS bp, a.balance AS b",
            aid=aid,
        ).single()
        assert a_row["bp"] == 54975
        assert a_row["b"] == 549.75
        assert Decimal(str(a_row["b"])) == Decimal(a_row["bp"]) / Decimal(100)


def test_update_transaction_category_variations(clean_user_context):
    svc, uid, aid = clean_user_context
    # Starting balance: 1000.00 = 100000 paise
    # 1. Add transaction: 50.00 (5000 paise) -> new balance 950.00 (95000 paise)
    t = svc.add_transaction(user_id=uid, account_id=aid, amount=50.00, description="Dinner", category_name="Food")
    tid = t["transaction_id"]
    assert t["new_balance"] == 950.00
    assert t["category"] == "Food"

    # 2. Update transaction with category_name=None (amount changes to 80.12 = 8012 paise)
    # Delta: +3012 paise expense -> new balance 919.88 (91988 paise)
    t_up1 = svc.update_transaction(user_id=uid, transaction_id=tid, amount=80.12, category_name=None)
    assert t_up1 is not None
    assert t_up1["transaction_id"] == tid
    assert t_up1["amount"] == 80.12
    assert t_up1["new_balance"] == 919.88
    # Category relation remains "Food"
    assert t_up1["category"] == "Food"

    with svc.driver.session(database=svc.database) as session:
        row1 = session.run(
            "MATCH (t:Transaction {id: $tid})-[:BELONGS_TO]->(c:Category) RETURN c.name AS cat, t.amount_paise AS tp, t.amount AS t",
            tid=tid,
        ).single()
        assert row1["cat"] == "Food"
        assert row1["tp"] == 8012
        assert row1["t"] == 80.12
        assert Decimal(str(row1["t"])) == Decimal(row1["tp"]) / Decimal(100)

    # 3. Update transaction with category given ("Transport", amount changes to 100.00 = 10000 paise)
    # Delta: +1988 paise expense -> new balance 900.00 (90000 paise)
    t_up2 = svc.update_transaction(user_id=uid, transaction_id=tid, amount=100.00, category_name="Transport")
    assert t_up2 is not None
    assert t_up2["amount"] == 100.00
    assert t_up2["new_balance"] == 900.00
    assert t_up2["category"] == "Transport"

    with svc.driver.session(database=svc.database) as session:
        row2 = session.run(
            "MATCH (t:Transaction {id: $tid})-[:BELONGS_TO]->(c:Category) RETURN c.name AS cat, t.amount_paise AS tp, t.amount AS t",
            tid=tid,
        ).single()
        assert row2["cat"] == "Transport"
        assert row2["tp"] == 10000
        assert row2["t"] == 100.00
        assert Decimal(str(row2["t"])) == Decimal(row2["tp"]) / Decimal(100)


def test_final_decimal_sweep_on_all_touched_nodes(clean_user_context):
    """Assert for every migrated label/property pair on all user nodes, Decimal(str(legacy)) == Decimal(paise)/100."""
    svc, uid, aid = clean_user_context

    # Create one of each entity type
    inc = svc.add_income(user_id=uid, source="Bonus", amount=333.33, account_id=aid)
    tx = svc.add_transaction(user_id=uid, account_id=aid, amount=111.11, description="Sweep Test")
    goal = svc.add_or_update_goal(user_id=uid, name="Sweep Goal", target_amount=777.77, current_amount=222.22)
    loan = svc.add_loan(user_id=uid, name="Sweep Loan", principal=5555.55, outstanding=4444.44)
    emi = svc.add_emi(loan_id=loan["id"], amount=99.99, user_id=uid)

    specs = [
        ("Account", "balance", "balance_paise"),
        ("Transaction", "amount", "amount_paise"),
        ("Income", "amount", "amount_paise"),
        ("Loan", "principal", "principal_paise"),
        ("Loan", "outstanding", "outstanding_paise"),
        ("EMI", "amount", "amount_paise"),
        ("Goal", "target_amount", "target_amount_paise"),
        ("Goal", "current_amount", "current_amount_paise"),
    ]

    with svc.driver.session(database=svc.database) as session:
        for label, leg_prop, paise_prop in specs:
            q = f"""
            MATCH (n:{label})
            WHERE n.{paise_prop} IS NOT NULL
            RETURN n.id AS nid, n.{leg_prop} AS leg, n.{paise_prop} AS paise
            """
            records = session.run(q).data()
            assert len(records) > 0, f"Expected records for {label}"
            for r in records:
                leg_val = r["leg"]
                paise_val = r["paise"]
                assert leg_val is not None, f"Node {label} (id={r['nid']}) missing legacy prop {leg_prop}"
                expected_dec = Decimal(paise_val) / Decimal(100)
                actual_dec = Decimal(str(leg_val))
                assert actual_dec == expected_dec, (
                    f"Decimal mismatch on {label} (id={r['nid']}): legacy {actual_dec} != {expected_dec}"
                )
