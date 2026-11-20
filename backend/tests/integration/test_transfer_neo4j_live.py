"""
Live Neo4j Integration Tests for Internal Bank Transfer Linking.

Target: Real Neo4j instance at 127.0.0.1:7687
Isolated Test Users:
- TEST_USER_XFER_LIVE
- TEST_USER_XFER_LIVE_2

Guarantees Verified:
1. Atomic multi-account ingestion and transfer linking.
2. Database-level strict 1-to-1 matching constraint.
3. Cross-user transfer linking rejection (strict user isolation).
4. Idempotent repeated linking (no duplicate relationships).
5. GraphRAG query exclusion of confirmed transfers.
6. Clean teardown leaving zero test artifacts in Neo4j.
"""

import pytest
from datetime import date
from backend.app.database.neo4j_service import Neo4jService
from backend.app.core.money import to_paise


USER_1 = "TEST_USER_XFER_LIVE"
USER_2 = "TEST_USER_XFER_LIVE_2"
ACC_HDFC = "ACC_LIVE_HDFC"
ACC_SBI = "ACC_LIVE_SBI"
ACC_ICICI = "ACC_LIVE_ICICI"


def _cleanup(db: Neo4jService):
    with db.driver.session(database=db.database) as session:
        session.run(
            """
            MATCH (u:User)
            WHERE u.id IN [$u1, $u2]
            OPTIONAL MATCH (u)-[:HAS_ACCOUNT]->(a:Account)
            OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction)
            OPTIONAL MATCH (imp:ImportBatch) WHERE imp.id STARTS WITH 'IMP_LIVE_'
            DETACH DELETE u, a, t, imp
            """,
            u1=USER_1,
            u2=USER_2,
        )


@pytest.fixture(scope="module")
def live_db():
    try:
        db = Neo4jService()
        db.driver.verify_connectivity()
    except Exception as e:
        pytest.skip(f"Live Neo4j instance not reachable at 127.0.0.1:7687: {e}")
    
    # Teardown before tests
    _cleanup(db)
    
    # Setup test users and accounts
    with db.driver.session(database=db.database) as session:
        session.run(
            """
            MERGE (u1:User {id: $u1, name: 'Live Test User 1'})
            MERGE (a1:Account {id: $acc1, bank: 'HDFC', balance_paise: 10000000, balance: 100000.0})
            MERGE (a2:Account {id: $acc2, bank: 'SBI', balance_paise: 5000000, balance: 50000.0})
            MERGE (u1)-[:HAS_ACCOUNT]->(a1)
            MERGE (u1)-[:HAS_ACCOUNT]->(a2)

            MERGE (u2:User {id: $u2, name: 'Live Test User 2'})
            MERGE (a3:Account {id: $acc3, bank: 'ICICI', balance_paise: 20000000, balance: 200000.0})
            MERGE (u2)-[:HAS_ACCOUNT]->(a3)
            """,
            u1=USER_1,
            u2=USER_2,
            acc1=ACC_HDFC,
            acc2=ACC_SBI,
            acc3=ACC_ICICI,
        )

    yield db

    # Teardown after tests
    _cleanup(db)


class TestNeo4jTransferLive:
    def test_atomic_multi_account_batch_and_link(self, live_db: Neo4jService):
        """Verify atomic insertion across 2 accounts and internal transfer linking."""
        tx1_fp = "FP_LIVE_DEBIT_001"
        tx2_fp = "FP_LIVE_CREDIT_001"

        rows_by_acc = {
            ACC_HDFC: [
                {
                    "id": "TX_LIVE_DEBIT_1",
                    "fingerprint": tx1_fp,
                    "date": "2026-10-20",
                    "amount": 25000.0,
                    "type": "EXPENSE",
                    "description": "Transfer to SBI A/c 5678",
                    "category": "Transfer",
                    "is_transfer": True,
                }
            ],
            ACC_SBI: [
                {
                    "id": "TX_LIVE_CREDIT_1",
                    "fingerprint": tx2_fp,
                    "date": "2026-10-20",
                    "amount": 25000.0,
                    "type": "INCOME",
                    "description": "NEFT from HDFC A/c 1234",
                    "category": "Transfer",
                    "is_transfer": True,
                }
            ],
        }

        transfer_pairs = [
            {
                "tx1_id": "TX_LIVE_DEBIT_1",
                "tx1_fp": tx1_fp,
                "tx2_id": "TX_LIVE_CREDIT_1",
                "tx2_fp": tx2_fp,
                "confidence": "HIGH",
            }
        ]

        result = live_db.batch_add_multi_account_transactions(
            user_id=USER_1,
            rows_by_acc=rows_by_acc,
            import_id="IMP_LIVE_001",
            transfer_pairs=transfer_pairs,
        )

        assert result["inserted"] == 2
        assert result["transfers_linked"] == 1

        # Verify edge in Neo4j
        with live_db.driver.session(database=live_db.database) as session:
            rec = session.run(
                """
                MATCH (t1:Transaction {id: 'TX_LIVE_DEBIT_1'})-[r:INTERNAL_TRANSFER]->(t2:Transaction {id: 'TX_LIVE_CREDIT_1'})
                RETURN count(r) AS edge_count, t1.is_transfer AS t1_xfer, t2.is_transfer AS t2_xfer
                """
            ).single()
            assert rec["edge_count"] == 1
            assert rec["t1_xfer"] is True
            assert rec["t2_xfer"] is True

    def test_strict_one_to_one_enforcement(self, live_db: Neo4jService):
        """Verify that an already-linked transaction CANNOT be linked to a third transaction."""
        # Insert a third transaction T3 on ACC_SBI
        tx3_fp = "FP_LIVE_CREDIT_002"
        rows_by_acc = {
            ACC_SBI: [
                {
                    "id": "TX_LIVE_CREDIT_2",
                    "fingerprint": tx3_fp,
                    "date": "2026-10-20",
                    "amount": 25000.0,
                    "type": "INCOME",
                    "description": "Attempted second pair",
                    "category": "Transfer",
                    "is_transfer": False,
                }
            ]
        }
        live_db.batch_add_multi_account_transactions(
            user_id=USER_1,
            rows_by_acc=rows_by_acc,
            import_id="IMP_LIVE_002",
        )

        # Attempt to link TX_LIVE_DEBIT_1 (already paired) with TX_LIVE_CREDIT_2
        invalid_pair = [
            {
                "tx1_id": "TX_LIVE_DEBIT_1",
                "tx1_fp": "FP_LIVE_DEBIT_001",
                "tx2_id": "TX_LIVE_CREDIT_2",
                "tx2_fp": tx3_fp,
                "confidence": "HIGH",
            }
        ]

        linked = live_db.link_internal_transfers(user_id=USER_1, pairs=invalid_pair)
        # Must be rejected because TX_LIVE_DEBIT_1 is already linked
        assert linked == 0

        # Verify no relationship exists between T1 and T3
        with live_db.driver.session(database=live_db.database) as session:
            count = session.run(
                """
                MATCH (t1:Transaction {id: 'TX_LIVE_DEBIT_1'})-[r:INTERNAL_TRANSFER]-(t3:Transaction {id: 'TX_LIVE_CREDIT_2'})
                RETURN count(r) AS c
                """
            ).single()["c"]
            assert count == 0

    def test_cross_user_pairing_rejected(self, live_db: Neo4jService):
        """Verify transactions from another user's account cannot be paired."""
        # Insert a transaction on USER_2's account
        live_db.batch_add_multi_account_transactions(
            user_id=USER_2,
            rows_by_acc={
                ACC_ICICI: [
                    {
                        "id": "TX_LIVE_USER2_CREDIT",
                        "fingerprint": "FP_USER2_001",
                        "date": "2026-10-20",
                        "amount": 25000.0,
                        "type": "INCOME",
                        "description": "Incoming transfer",
                        "category": "General",
                        "is_transfer": False,
                    }
                ]
            },
            import_id="IMP_LIVE_003",
        )

        # Attempt to pair USER_1's debit with USER_2's credit under USER_1's context
        cross_pair = [
            {
                "tx1_id": "TX_LIVE_DEBIT_1",
                "tx1_fp": "FP_LIVE_DEBIT_001",
                "tx2_id": "TX_LIVE_USER2_CREDIT",
                "tx2_fp": "FP_USER2_001",
                "confidence": "HIGH",
            }
        ]

        linked = live_db.link_internal_transfers(user_id=USER_1, pairs=cross_pair)
        assert linked == 0

    def test_idempotent_linking(self, live_db: Neo4jService):
        """Re-linking the exact same pair should succeed idempotently without duplicating edges."""
        valid_pair = [
            {
                "tx1_id": "TX_LIVE_DEBIT_1",
                "tx1_fp": "FP_LIVE_DEBIT_001",
                "tx2_id": "TX_LIVE_CREDIT_1",
                "tx2_fp": "FP_LIVE_CREDIT_001",
                "confidence": "HIGH",
            }
        ]

        # Re-run linking
        linked = live_db.link_internal_transfers(user_id=USER_1, pairs=valid_pair)
        assert linked == 1

        # Check total relationship count is still exactly 1
        with live_db.driver.session(database=live_db.database) as session:
            count = session.run(
                """
                MATCH (t1:Transaction {id: 'TX_LIVE_DEBIT_1'})-[r:INTERNAL_TRANSFER]-(t2:Transaction {id: 'TX_LIVE_CREDIT_1'})
                RETURN count(r) AS c
                """
            ).single()["c"]
            assert count == 1

    def test_graphrag_transfer_exclusion_live(self, live_db: Neo4jService):
        """Verify GraphRAG top transactions and merchant queries exclude the confirmed transfer."""
        # Insert a normal non-transfer expense
        live_db.batch_add_multi_account_transactions(
            user_id=USER_1,
            rows_by_acc={
                ACC_HDFC: [
                    {
                        "id": "TX_LIVE_EXP_NORMAL",
                        "fingerprint": "FP_LIVE_NORMAL_EXP",
                        "date": "2026-10-21",
                        "amount": 3500.0,
                        "type": "EXPENSE",
                        "description": "Starbucks Coffee",
                        "clean_merchant": "Starbucks",
                        "category": "Dining",
                        "is_transfer": False,
                    }
                ]
            },
            import_id="IMP_LIVE_004",
        )

        subgraph = live_db.retrieve_grounded_subgraph(
            user_id=USER_1,
            intent="TOP_TRANSACTIONS",
            entities={"reporting_date": "2026-10-21"},
        )

        txns = subgraph.get("context", {}).get("transactions", [])
        tx_ids = [t["id"] for t in txns]

        # Normal expense must be present
        assert "TX_LIVE_EXP_NORMAL" in tx_ids
        # Confirmed transfer debit must NOT be present
        assert "TX_LIVE_DEBIT_1" not in tx_ids

    def test_atomic_rollback_on_failure(self, live_db: Neo4jService):
        """Verify that batch insertion rolls back if any account is invalid."""
        invalid_rows_by_acc = {
            ACC_HDFC: [
                {
                    "id": "TX_LIVE_ROLLBACK_1",
                    "fingerprint": "FP_LIVE_RB_1",
                    "date": "2026-10-22",
                    "amount": 1000.0,
                    "type": "EXPENSE",
                    "description": "Should rollback",
                    "category": "General",
                }
            ],
            "NON_EXISTENT_ACCOUNT_ID": [
                {
                    "id": "TX_LIVE_ROLLBACK_2",
                    "fingerprint": "FP_LIVE_RB_2",
                    "date": "2026-10-22",
                    "amount": 1000.0,
                    "type": "EXPENSE",
                    "description": "Should trigger error",
                    "category": "General",
                }
            ],
        }

        with pytest.raises(ValueError, match="not found"):
            live_db.batch_add_multi_account_transactions(
                user_id=USER_1,
                rows_by_acc=invalid_rows_by_acc,
                import_id="IMP_LIVE_RB",
            )

        # Verify TX_LIVE_ROLLBACK_1 was NOT committed
        with live_db.driver.session(database=live_db.database) as session:
            count = session.run(
                "MATCH (t:Transaction {id: 'TX_LIVE_ROLLBACK_1'}) RETURN count(t) AS c"
            ).single()["c"]
            assert count == 0
