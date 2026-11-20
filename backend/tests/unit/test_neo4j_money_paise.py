"""
Integration and invariant tests for Neo4j integer paise money storage.

Tests cover:
- Exact paise balance accounting for ugly cents and repeat transactions
- Add, update, delete round-trip balance restoration
- Bulk import of 100 ugly-cent rows and re-import idempotency
- Dual-write legacy vs paise consistency across all seeded graph entities
- Negative account balance update support
- Fail-fast assert_money_migrated() validation on unmigrated legacy nodes
- Source scan ensuring float literal reduce accumulators are eliminated
"""

from decimal import Decimal
from pathlib import Path
import uuid
import pytest

from backend.app.core.money import to_paise
from backend.app.database.neo4j_service import Neo4jService
from backend.scripts.seed_db import seed_database


@pytest.fixture(scope="module", autouse=True)
def setup_seeded_database():
    """Ensure clean seeded database state before running suite."""
    seed_database()
    svc = Neo4jService()
    yield svc
    svc.close()


def test_no_float_reduce_in_neo4j_service_source():
    """Assert via source code scan that float reduce accumulator 'reduce(s = 0.0' is gone."""
    source_path = Path(__file__).resolve().parents[2] / "app" / "database" / "neo4j_service.py"
    content = source_path.read_text(encoding="utf-8")
    assert "reduce(s = 0.0" not in content, "Found forbidden float reduce accumulator 'reduce(s = 0.0' in neo4j_service.py"
    assert "reduce(s = 0," in content, "Expected integer reduce accumulator 'reduce(s = 0,' in neo4j_service.py"


def test_three_transactions_and_ugly_cents_balance_exact(setup_seeded_database):
    """
    Add three transactions of 33.33 and one of 0.10 and 0.20:
    balance_paise equals the exact expected integer, legacy balance equals balance_paise / 100.0,
    and returned new_balance matches expected rupee value.
    """
    svc = setup_seeded_database
    u_suffix = uuid.uuid4().hex[:6].lower()
    user = svc.create_user(username=f"user_{u_suffix}", password="SecretPassword123!", initial_balance=1000.00)
    uid = user["user_id"]
    aid = user["account_id"]

    try:
        # Add 3 transactions of 33.33 (3 * 3333 = 9999 paise)
        t1 = svc.add_transaction(user_id=uid, account_id=aid, amount=33.33, description="Tx 1")
        assert t1["new_balance"] == 966.67
        t2 = svc.add_transaction(user_id=uid, account_id=aid, amount=33.33, description="Tx 2")
        assert t2["new_balance"] == 933.34
        t3 = svc.add_transaction(user_id=uid, account_id=aid, amount=33.33, description="Tx 3")
        assert t3["new_balance"] == 900.01

        # Add 0.10 (10 paise) and 0.20 (20 paise)
        t4 = svc.add_transaction(user_id=uid, account_id=aid, amount=0.10, description="Ugly Cent 1")
        assert t4["new_balance"] == 899.91
        t5 = svc.add_transaction(user_id=uid, account_id=aid, amount=0.20, description="Ugly Cent 2")
        assert t5["new_balance"] == 899.71

        # Total spend: 9999 + 10 + 20 = 10029 paise. Initial: 100000 paise. Expected: 89971 paise.
        with svc.driver.session(database=svc.database) as session:
            rec = session.run("MATCH (a:Account {id: $aid}) RETURN a.balance_paise AS bp, a.balance AS b", aid=aid).single()
            assert rec["bp"] == 89971
            assert rec["b"] == 899.71
    finally:
        with svc.driver.session(database=svc.database) as session:
            session.run("MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account) OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction) DETACH DELETE u, a, t", uid=uid)


def test_add_update_delete_round_trip_exact_paise(setup_seeded_database):
    """Verify add, update (change amount), delete round trip returns balance to exact starting paise."""
    svc = setup_seeded_database
    u_suffix = uuid.uuid4().hex[:6].lower()
    user = svc.create_user(username=f"user_{u_suffix}", password="SecretPassword123!", initial_balance=500.00)
    uid = user["user_id"]
    aid = user["account_id"]

    try:
        # Starting: 50000 paise
        t = svc.add_transaction(user_id=uid, account_id=aid, amount=45.67, description="Initial")
        tid = t["transaction_id"]
        # 50000 - 4567 = 45433 paise = 454.33
        assert t["new_balance"] == 454.33

        # Update to 80.12 (8012 paise)
        t_up = svc.update_transaction(user_id=uid, transaction_id=tid, amount=80.12)
        # 50000 - 8012 = 41988 paise = 419.88
        assert t_up["new_balance"] == 419.88

        # Delete transaction
        res_del = svc.delete_transaction(user_id=uid, transaction_id=tid)
        assert res_del["restored_balance"] == 500.00

        with svc.driver.session(database=svc.database) as session:
            rec = session.run("MATCH (a:Account {id: $aid}) RETURN a.balance_paise AS bp, a.balance AS b", aid=aid).single()
            assert rec["bp"] == 50000
            assert rec["b"] == 500.00
    finally:
        with svc.driver.session(database=svc.database) as session:
            session.run("MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account) OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction) DETACH DELETE u, a, t", uid=uid)


def test_batch_import_ugly_cents_and_idempotency(setup_seeded_database):
    """Batch import of 100 ugly-cent rows: net_balance_delta exact in paise; re-import is pure zero-delta noop."""
    svc = setup_seeded_database
    u_suffix = uuid.uuid4().hex[:6].lower()
    user = svc.create_user(username=f"user_{u_suffix}", password="SecretPassword123!", initial_balance=2000.00)
    uid = user["user_id"]
    aid = user["account_id"]

    try:
        # Generate 100 rows with ugly-cent amounts: 0.07, 0.17, 0.27 ...
        rows = []
        expected_total_paise = 0
        for i in range(100):
            amt = round(0.07 + (i * 0.13), 2)
            expected_total_paise += to_paise(amt)
            rows.append({
                "date": f"2026-10-{(i % 28) + 1:02d}",
                "amount": amt,
                "type": "EXPENSE",
                "description": f"Ugly cent expense {i}",
                "clean_merchant": f"Merchant_{i % 10}",
                "category": "Shopping",
                "source_ref": f"REF_UGLY_{i}",
            })

        expected_delta_rupees = round(float(expected_total_paise) / 100.0, 2)
        expected_new_balance = round(2000.00 - expected_delta_rupees, 2)

        # 1. First import:
        res1 = svc.batch_add_transactions(user_id=uid, account_id=aid, rows=rows)
        assert res1["inserted"] == 100
        assert res1["skipped"] == 0
        assert res1["net_balance_delta"] == -expected_delta_rupees
        assert res1["new_balance"] == expected_new_balance

        # 2. Second repeat import with same rows:
        res2 = svc.batch_add_transactions(user_id=uid, account_id=aid, rows=rows)
        assert res2["inserted"] == 0
        assert res2["skipped"] == 100
        assert res2["net_balance_delta"] == 0.0
        assert res2["new_balance"] == expected_new_balance

        # Verify DB directly
        with svc.driver.session(database=svc.database) as session:
            rec = session.run("MATCH (a:Account {id: $aid}) RETURN a.balance_paise AS bp, a.balance AS b", aid=aid).single()
            assert rec["bp"] == (200000 - expected_total_paise)
            assert rec["b"] == expected_new_balance
    finally:
        with svc.driver.session(database=svc.database) as session:
            session.run("MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account) OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction) DETACH DELETE u, a, t", uid=uid)


def test_dual_write_consistency_seeded_nodes(setup_seeded_database):
    """For every migrated label/property pair, legacy == paise / 100.0 for all seeded nodes."""
    svc = setup_seeded_database
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
        for label, legacy_prop, paise_prop in specs:
            query = f"""
            MATCH (n:{label})
            WHERE n.{legacy_prop} IS NOT NULL
            RETURN id(n) AS nid, n.{legacy_prop} AS leg, n.{paise_prop} AS p
            """
            rows = list(session.run(query))
            assert len(rows) > 0, f"Expected seeded nodes for {label}"
            for r in rows:
                nid = r["nid"]
                leg = r["leg"]
                p = r["p"]
                assert p is not None, f"Node {label} (id={nid}) missing {paise_prop}"
                computed_from_p = round(float(p) / 100.0, 2)
                assert abs(float(leg) - computed_from_p) < 1e-4, f"Mismatch on {label} id {nid}: {leg} != {computed_from_p}"


def test_update_account_balance_accepts_negative(setup_seeded_database):
    """update_account_balance accepts a negative balance and stores it exactly in paise and legacy float."""
    svc = setup_seeded_database
    u_suffix = uuid.uuid4().hex[:6].lower()
    user = svc.create_user(username=f"user_{u_suffix}", password="SecretPassword123!", initial_balance=100.00)
    uid = user["user_id"]
    aid = user["account_id"]

    try:
        updated = svc.update_account_balance(account_id=aid, new_balance=-1500.50, user_id=uid)
        assert updated["balance"] == -1500.50

        with svc.driver.session(database=svc.database) as session:
            rec = session.run("MATCH (a:Account {id: $aid}) RETURN a.balance_paise AS bp, a.balance AS b", aid=aid).single()
            assert rec["bp"] == -150050
            assert rec["b"] == -1500.50
    finally:
        with svc.driver.session(database=svc.database) as session:
            session.run("MATCH (u:User {id: $uid})-[:HAS_ACCOUNT]->(a:Account) DETACH DELETE u, a", uid=uid)


def test_assert_money_migrated_fail_fast(setup_seeded_database):
    """assert_money_migrated() passes on seeded DB; fails (RuntimeError) when a node lacks *_paise."""
    svc = setup_seeded_database
    # Passes initially on clean DB
    svc.assert_money_migrated()

    throwaway_id = f"ACC_UNMIGRATED_{uuid.uuid4().hex[:8].upper()}"
    try:
        with svc.driver.session(database=svc.database) as session:
            session.run("CREATE (a:Account {id: $aid, balance: 250.00})", aid=throwaway_id)

        # Now must fail fast
        with pytest.raises(RuntimeError) as exc_info:
            svc.assert_money_migrated()
        assert "unmigrated money properties found in database" in str(exc_info.value)
        assert "Account.balance -> balance_paise" in str(exc_info.value)
    finally:
        with svc.driver.session(database=svc.database) as session:
            session.run("MATCH (a:Account {id: $aid}) DETACH DELETE a", aid=throwaway_id)

    # After cleanup, passes again
    svc.assert_money_migrated()
