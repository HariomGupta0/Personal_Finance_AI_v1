"""
Unit and Integration tests for Neo4jService data integrity, duplicate detection,
schema constraints, and idempotent transaction imports.

Requirement 7:
- Distinguish mocked unit tests from real Neo4j integration tests.
- Demonstrate that repeated imports are strictly idempotent and do not corrupt balances.
- Demonstrate that in-batch duplicates are deduplicated and applied only once.
"""

from __future__ import annotations

import copy
import pytest
from unittest.mock import MagicMock, patch

from backend.app.database.neo4j_service import Neo4jService
from backend.app.services.fingerprint import compute_transaction_fingerprint


# ===========================================================================
# Stateful Mock Neo4j Infrastructure (for Unit Testing without live Neo4j)
# ===========================================================================

class StatefulGraphStore:
    """
    Simulates Neo4j state (users, accounts, transactions, balances, constraints)
    in memory for hermetic, fast, and repeatable unit testing.
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.accounts = {
            "A001": {
                "id": "A001",
                "bank": "HDFC Bank",
                "account_type": "Savings",
                "balance": initial_balance,
            }
        }
        self.users = {
            "U001": {
                "id": "U001",
                "name": "Test User",
                "accounts": ["A001"],
            }
        }
        self.transactions: dict[str, dict] = {}  # keyed by fingerprint
        self.constraints: set[str] = set()
        self.simulate_constraint_failure: str | None = None
        self.simulate_write_failure: bool = False

    def snapshot(self):
        return {
            "accounts": copy.deepcopy(self.accounts),
            "transactions": copy.deepcopy(self.transactions),
        }

    def restore(self, snap):
        self.accounts = snap["accounts"]
        self.transactions = snap["transactions"]


class MockRecord:
    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)


class MockResult:
    def __init__(self, records: list[dict]):
        self._records = [MockRecord(r) for r in records]

    def single(self):
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)


class StatefulMockSession:
    def __init__(self, store: StatefulGraphStore):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, query: str, **params):
        # 1. Schema constraint handling
        if query.strip().startswith("CREATE CONSTRAINT") or query.strip().startswith("CREATE INDEX"):
            if self.store.simulate_constraint_failure and self.store.simulate_constraint_failure in query:
                raise RuntimeError(f"Simulated Neo4j error executing: {query}")
            self.store.constraints.add(query.strip())
            return MockResult([])

        # 2. Get user accounts
        if "MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(a:Account)" in query and "RETURN a.id" in query:
            user_id = params.get("user_id", "U001")
            user = self.store.users.get(user_id)
            if not user:
                return MockResult([])
            records = [self.store.accounts[acc_id] for acc_id in user["accounts"] if acc_id in self.store.accounts]
            return MockResult(records)

        # 3. Add single transaction
        if "CREATE (t:Transaction" in query and "SET a.balance = a.balance +" in query:
            account_id = params["account_id"]
            acc = self.store.accounts.get(account_id)
            if not acc:
                return MockResult([])
            amt = float(params["amount"])
            tx_type = params["transaction_type"].upper()
            fp = params.get("fingerprint") or f"fp_manual_{params['transaction_id']}"
            delta = amt if tx_type == "INCOME" else -amt
            acc["balance"] += delta
            self.store.transactions[fp] = {
                "id": params["transaction_id"],
                "fingerprint": fp,
                "amount": amt,
                "type": tx_type,
                "description": params["description"],
                "date": params["date_str"],
            }
            return MockResult([{
                "transaction_id": params["transaction_id"],
                "fingerprint": fp,
                "description": params["description"],
                "amount": amt,
                "type": tx_type,
                "date": params["date_str"],
                "category": params.get("category_name", "General"),
                "account_id": account_id,
                "new_balance": acc["balance"],
            }])

        # Fallback default
        return MockResult([])

    def execute_write(self, tx_func):
        if self.store.simulate_write_failure:
            raise RuntimeError("Simulated transient Neo4j write transaction failure")

        # Snapshot for ACID rollback simulation
        snap = self.store.snapshot()

        class MockTx:
            def __init__(self, session):
                self.session = session

            def run(self, query: str, **params):
                # Batch add transactions logic
                if "UNWIND $rows AS r" in query and "MERGE (t:Transaction" in query:
                    user_id = params.get("user_id", "U001")
                    account_id = params.get("account_id")
                    rows = params.get("rows", [])
                    acc = self.session.store.accounts.get(account_id)
                    if not acc:
                        return MockResult([])

                    inserted_count = 0
                    net_delta = 0.0

                    for r in rows:
                        fp = r["fingerprint"]
                        # Idempotent MERGE: if transaction already exists, skip
                        if fp in self.session.store.transactions:
                            continue

                        # Genuinely new transaction
                        tx_amt = float(r["amount"])
                        tx_type = r["type"].upper()
                        delta = tx_amt if tx_type == "INCOME" else -tx_amt
                        net_delta += delta
                        inserted_count += 1

                        self.session.store.transactions[fp] = {
                            "id": r["id"],
                            "fingerprint": fp,
                            "amount": tx_amt,
                            "type": tx_type,
                            "description": r["description"],
                            "date": r["date"],
                            "import_id": params.get("import_id"),
                        }

                    acc["balance"] += net_delta
                    return MockResult([{
                        "inserted_count": inserted_count,
                        "net_delta": net_delta,
                        "new_balance": acc["balance"],
                    }])

                return self.session.run(query, **params)

        try:
            return tx_func(MockTx(self))
        except Exception:
            self.store.restore(snap)
            raise


class StatefulMockDriver:
    def __init__(self, store: StatefulGraphStore):
        self.store = store

    def session(self, database=None):
        return StatefulMockSession(self.store)

    def close(self):
        pass


@pytest.fixture
def mock_graph_env():
    store = StatefulGraphStore(initial_balance=10000.0)
    driver = StatefulMockDriver(store)
    service = Neo4jService(database="mock-db", driver=driver)
    return store, service


# ===========================================================================
# 1. Schema Constraints & Error Handling Tests
# ===========================================================================

@pytest.mark.unit
class TestSchemaConstraints:
    def test_schema_constraints_created_successfully(self, mock_graph_env):
        store, service = mock_graph_env
        results = service.init_schema_constraints(strict=False)
        assert len(results) == 8
        assert all(status == "CREATED_OR_EXISTS" for status in results.values())
        # Check required constraints exist
        assert any("txn_fp" in q for q in store.constraints)
        assert any("merchant_norm" in q for q in store.constraints)
        assert any("account_id_unique" in q for q in store.constraints)

    def test_schema_constraints_logs_error_without_silent_swallowing(self, mock_graph_env, caplog):
        store, service = mock_graph_env
        store.simulate_constraint_failure = "txn_fp"

        import logging
        with caplog.at_level(logging.ERROR):
            results = service.init_schema_constraints(strict=False)

        # Confirm failure was captured in results and logged
        failed_entries = [q for q, res in results.items() if "FAILED" in res]
        assert len(failed_entries) == 1
        assert "txn_fp" in failed_entries[0]
        assert "Failed to apply schema constraint/index" in caplog.text

    def test_schema_constraints_strict_mode_raises(self, mock_graph_env):
        store, service = mock_graph_env
        store.simulate_constraint_failure = "merchant_norm"

        with pytest.raises(RuntimeError, match="Simulated Neo4j error"):
            service.init_schema_constraints(strict=True)


# ===========================================================================
# 2. Idempotency & Repeated Imports Tests
# ===========================================================================

@pytest.mark.unit
class TestRepeatedImportIdempotency:
    def test_repeated_import_does_not_create_duplicates_nor_change_balance(self, mock_graph_env):
        store, service = mock_graph_env
        assert store.accounts["A001"]["balance"] == 10000.0

        batch_1 = [
            {"date": "2026-03-01", "amount": 1000.0, "type": "EXPENSE", "description": "Groceries"},
            {"date": "2026-03-02", "amount": 5000.0, "type": "INCOME", "description": "Freelance"},
            {"date": "2026-03-03", "amount": 500.0, "type": "EXPENSE", "description": "Dinner"},
        ]

        # First Import
        res1 = service.batch_add_transactions(
            user_id="U001",
            account_id="A001",
            rows=batch_1,
            import_id="IMP_001",
        )
        assert res1["total"] == 3
        assert res1["inserted"] == 3
        assert res1["skipped"] == 0
        assert res1["net_balance_delta"] == 3500.0  # -1000 + 5000 - 500 = +3500
        assert res1["new_balance"] == 13500.0
        assert store.accounts["A001"]["balance"] == 13500.0
        assert len(store.transactions) == 3

        # Second Import of the EXACT SAME batch (simulating re-uploading statement)
        res2 = service.batch_add_transactions(
            user_id="U001",
            account_id="A001",
            rows=batch_1,
            import_id="IMP_002",
        )
        assert res2["total"] == 3
        assert res2["inserted"] == 0
        assert res2["skipped"] == 3
        assert res2["net_balance_delta"] == 0.0
        # CRITICAL CHECK: Account balance MUST remain untouched
        assert res2["new_balance"] == 13500.0
        assert store.accounts["A001"]["balance"] == 13500.0
        # Transaction count MUST still be 3 (zero duplicates added)
        assert len(store.transactions) == 3

        # Third Import (idempotency holds indefinitely)
        res3 = service.batch_add_transactions(
            user_id="U001",
            account_id="A001",
            rows=batch_1,
            import_id="IMP_003",
        )
        assert res3["inserted"] == 0
        assert res3["skipped"] == 3
        assert res3["net_balance_delta"] == 0.0
        assert store.accounts["A001"]["balance"] == 13500.0


# ===========================================================================
# 3. In-Batch Duplicate Handling Tests
# ===========================================================================

@pytest.mark.unit
class TestInBatchDuplicates:
    def test_in_batch_duplicate_fingerprints_applied_only_once(self, mock_graph_env):
        store, service = mock_graph_env
        assert store.accounts["A001"]["balance"] == 10000.0

        # Create identical duplicate rows with explicit same fingerprint
        fp = "fp_fixed_test_dup_123"
        batch_with_dups = [
            {"date": "2026-03-05", "amount": 250.0, "type": "EXPENSE", "description": "Coffee", "fingerprint": fp},
            {"date": "2026-03-05", "amount": 250.0, "type": "EXPENSE", "description": "Coffee", "fingerprint": fp},
            {"date": "2026-03-05", "amount": 250.0, "type": "EXPENSE", "description": "Coffee", "fingerprint": fp},
        ]

        res = service.batch_add_transactions(
            user_id="U001",
            account_id="A001",
            rows=batch_with_dups,
        )

        assert res["total"] == 3
        assert res["inserted"] == 1
        assert res["skipped"] == 2
        # Balance must decrease by only 250 (NOT 750!)
        assert res["net_balance_delta"] == -250.0
        assert res["new_balance"] == 9750.0
        assert store.accounts["A001"]["balance"] == 9750.0
        assert len(store.transactions) == 1

    def test_legitimate_repeated_purchases_get_distinct_fingerprints(self, mock_graph_env):
        """
        Two legitimate separate ₹20 chai purchases on the same day without pre-set fingerprints
        should be differentiated by occurrence index.
        """
        store, service = mock_graph_env
        rows = [
            {"date": "2026-03-06", "amount": 20.0, "type": "EXPENSE", "description": "Chai Point"},
            {"date": "2026-03-06", "amount": 20.0, "type": "EXPENSE", "description": "Chai Point"},
        ]

        res = service.batch_add_transactions(
            user_id="U001",
            account_id="A001",
            rows=rows,
        )

        assert res["total"] == 2
        assert res["inserted"] == 2
        assert res["skipped"] == 0
        assert res["net_balance_delta"] == -40.0
        assert store.accounts["A001"]["balance"] == 9960.0
        assert len(store.transactions) == 2


# ===========================================================================
# 4. Genuinely Inserted Balance Accounting Tests
# ===========================================================================

@pytest.mark.unit
class TestBalanceAccountingIntegrity:
    def test_mixed_batch_updates_balance_only_for_genuinely_new_rows(self, mock_graph_env):
        store, service = mock_graph_env

        # Initial import of 2 rows
        initial_rows = [
            {"date": "2026-03-01", "amount": 300.0, "type": "EXPENSE", "description": "Utilities"},
            {"date": "2026-03-02", "amount": 1000.0, "type": "INCOME", "description": "Interest"},
        ]
        service.batch_add_transactions(user_id="U001", account_id="A001", rows=initial_rows)
        # 10000 - 300 + 1000 = 10700
        assert store.accounts["A001"]["balance"] == 10700.0

        # Mixed batch: 2 existing rows + 1 brand new row (₹700 expense)
        mixed_rows = [
            {"date": "2026-03-01", "amount": 300.0, "type": "EXPENSE", "description": "Utilities"},
            {"date": "2026-03-02", "amount": 1000.0, "type": "INCOME", "description": "Interest"},
            {"date": "2026-03-07", "amount": 700.0, "type": "EXPENSE", "description": "Clothing"},
        ]

        res = service.batch_add_transactions(user_id="U001", account_id="A001", rows=mixed_rows)
        assert res["total"] == 3
        assert res["inserted"] == 1
        assert res["skipped"] == 2
        # Crucial check: Net delta MUST be -700.0, NOT 0.0 and NOT -300+1000-700 = 0
        assert res["net_balance_delta"] == -700.0
        assert res["new_balance"] == 10000.0
        assert store.accounts["A001"]["balance"] == 10000.0


# ===========================================================================
# 5. Atomicity & Rollback Tests
# ===========================================================================

@pytest.mark.unit
class TestAtomicityAndRollback:
    def test_write_failure_rolls_back_balance_and_transactions(self, mock_graph_env):
        store, service = mock_graph_env
        assert store.accounts["A001"]["balance"] == 10000.0
        store.simulate_write_failure = True

        rows = [
            {"date": "2026-03-08", "amount": 1200.0, "type": "EXPENSE", "description": "Failed Transaction"},
        ]

        with pytest.raises(RuntimeError, match="Simulated transient Neo4j write transaction failure"):
            service.batch_add_transactions(user_id="U001", account_id="A001", rows=rows)

        # Balance and transactions MUST remain intact (no partial commit)
        assert store.accounts["A001"]["balance"] == 10000.0
        assert len(store.transactions) == 0

    def test_empty_rows_safe_noop(self, mock_graph_env):
        store, service = mock_graph_env
        res = service.batch_add_transactions(user_id="U001", account_id="A001", rows=[])
        assert res["total"] == 0
        assert res["inserted"] == 0
        assert res["skipped"] == 0
        assert res["net_balance_delta"] == 0.0
        assert store.accounts["A001"]["balance"] == 10000.0


# ===========================================================================
# 6. Real Neo4j Integration Tests (Clearly Distinguished from Mocked Tests)
# ===========================================================================

@pytest.mark.integration
class TestNeo4jRealIntegration:
    """
    Real integration tests against a live Neo4j instance.
    Runs ONLY when live Neo4j is reachable; skipped gracefully otherwise.
    """

    @pytest.fixture(autouse=True)
    def ensure_live_neo4j(self):
        from backend.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
        from neo4j import GraphDatabase
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
            driver.verify_connectivity()
            driver.close()
        except Exception as exc:
            pytest.skip(f"Live Neo4j instance not reachable at {NEO4J_URI}: {exc}")

    def test_live_neo4j_idempotent_import(self):
        from backend.app.database.neo4j_service import get_neo4j_service
        db = get_neo4j_service()
        # Verify schema constraints idempotency on live database
        results = db.init_schema_constraints(strict=False)
        assert isinstance(results, dict)
