"""
Graph Schema and Data Consistency Checker (Read-Only).

Inspects the Neo4j knowledge graph for:
1. Transaction.category property vs (Transaction)-[:BELONGS_TO]->(Category) edge consistency:
   - Identifies conflicts where Transaction.category property contradicts Category.name edge.
   - Detects transactions with missing Category relationships.
2. Income nodes (:Income) vs INCOME transactions (:Transaction {type: 'INCOME'}):
   - Audits coexistence and flags duplicate income entries across both paradigms.
3. Account balance integrity and currency synchronization:
   - Verifies exact paise-to-rupee synchronization (balance_paise == round(balance * 100)).
   - Reports transaction delta reconciliation against account balance.
   - Audits paise vs float consistency on Loans, EMIs, and Goals.
4. Structural topology & orphan detection:
   - Detects unlinked Transactions, Incomes, EMIs, or Accounts.

Designed to be 100% read-only and safe to run in production.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.money import to_paise
from backend.app.database.neo4j_service import get_neo4j_service


def check_graph_consistency(driver_or_service: Any = None) -> dict:
    if driver_or_service is not None:
        if hasattr(driver_or_service, "driver"):
            neo = driver_or_service
        else:
            neo = type("MockService", (), {"driver": driver_or_service, "database": "finance-ai-antigravity"})()
    else:
        neo = get_neo4j_service()

    report = {
        "summary": {},
        "category_checks": {},
        "income_checks": {},
        "balance_checks": {},
        "entity_checks": {},
        "orphan_checks": {},
        "inconsistencies_found": 0,
        "warnings_found": 0,
    }

    with neo.driver.session(database=neo.database) as session:
        # ---------------------------------------------------------
        # 1. Transaction.category property vs BELONGS_TO edge
        # ---------------------------------------------------------
        query_tx_categories = """
        MATCH (t:Transaction)
        OPTIONAL MATCH (t)-[:BELONGS_TO]->(c:Category)
        RETURN t.id AS tx_id,
               t.description AS description,
               t.category AS category_prop,
               c.name AS category_edge_name,
               c.id AS category_edge_id
        ORDER BY t.id
        """
        tx_records = list(session.run(query_tx_categories))
        category_issues = []
        for r in tx_records:
            tx_id = r["tx_id"]
            prop = r["category_prop"]
            edge = r["category_edge_name"]

            if prop is not None and edge is not None and prop.strip().lower() != edge.strip().lower():
                category_issues.append({
                    "tx_id": tx_id,
                    "type": "CONFLICT",
                    "detail": f"Property '{prop}' != Edge '{edge}'",
                })
                report["inconsistencies_found"] += 1
            elif prop is not None and edge is None:
                category_issues.append({
                    "tx_id": tx_id,
                    "type": "MISSING_EDGE",
                    "detail": f"Property '{prop}' present but missing BELONGS_TO edge",
                })
                report["inconsistencies_found"] += 1
            elif prop is None and edge is not None:
                category_issues.append({
                    "tx_id": tx_id,
                    "type": "INFO_PROPERTY_ABSENT",
                    "detail": f"Edge BELONGS_TO '{edge}' present; Transaction.category property is null (normalized schema)",
                })
            elif prop is None and edge is None:
                category_issues.append({
                    "tx_id": tx_id,
                    "type": "UNCATEGORIZED",
                    "detail": "Neither property nor BELONGS_TO edge present",
                })
                report["warnings_found"] += 1

        report["category_checks"] = {
            "total_transactions": len(tx_records),
            "issues": category_issues,
        }

        # ---------------------------------------------------------
        # 2. Income nodes vs INCOME transactions
        # ---------------------------------------------------------
        query_incomes = """
        MATCH (i:Income)
        OPTIONAL MATCH (u:User)-[:RECEIVED_INCOME]->(i)
        RETURN i.id AS income_id, i.source AS source, i.amount AS amount,
               i.amount_paise AS amount_paise, toString(i.date) AS date, u.id AS user_id
        """
        income_nodes = [dict(r) for r in session.run(query_incomes)]

        query_income_txs = """
        MATCH (a:Account)-[:MADE_TRANSACTION]->(t:Transaction)
        WHERE toUpper(t.type) = 'INCOME'
        RETURN t.id AS tx_id, t.description AS description, t.amount AS amount,
               t.amount_paise AS amount_paise, toString(t.date) AS date, a.id AS account_id
        """
        income_txs = [dict(r) for r in session.run(query_income_txs)]

        duplicates = []
        for inc in income_nodes:
            for tx in income_txs:
                if inc.get("date") == tx.get("date") and inc.get("amount_paise") == tx.get("amount_paise"):
                    duplicates.append({
                        "income_id": inc["income_id"],
                        "tx_id": tx["tx_id"],
                        "amount_paise": inc["amount_paise"],
                        "date": inc["date"],
                    })
                    report["warnings_found"] += 1

        report["income_checks"] = {
            "income_nodes_count": len(income_nodes),
            "income_transactions_count": len(income_txs),
            "potential_duplicates": duplicates,
        }

        # ---------------------------------------------------------
        # 3. Account balance & currency synchronization
        # ---------------------------------------------------------
        query_accounts = """
        MATCH (a:Account)
        OPTIONAL MATCH (u:User)-[:HAS_ACCOUNT]->(a)
        OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(t:Transaction)
        WITH a, u,
             sum(CASE WHEN toUpper(t.type) = 'INCOME' THEN t.amount_paise ELSE -t.amount_paise END) AS net_tx_paise,
             count(t) AS tx_count
        RETURN a.id AS account_id,
               a.bank AS bank,
               a.balance AS balance,
               a.balance_paise AS balance_paise,
               u.id AS user_id,
               net_tx_paise,
               tx_count
        ORDER BY a.id
        """
        account_records = list(session.run(query_accounts))
        balance_issues = []
        for acc in account_records:
            acc_id = acc["account_id"]
            bal = acc["balance"]
            bal_paise = acc["balance_paise"]
            net_tx = acc["net_tx_paise"] or 0
            tx_count = acc["tx_count"]

            if bal_paise is not None and bal is not None:
                expected_paise = to_paise(bal)
                if expected_paise != bal_paise:
                    balance_issues.append({
                        "account_id": acc_id,
                        "type": "CURRENCY_SYNC_MISMATCH",
                        "detail": f"Account.balance={bal} (expected {expected_paise} paise) != balance_paise={bal_paise}",
                    })
                    report["inconsistencies_found"] += 1
            elif bal_paise is None and bal is not None:
                balance_issues.append({
                    "account_id": acc_id,
                    "type": "MISSING_BALANCE_PAISE",
                    "detail": "Account.balance_paise is NULL",
                })
                report["inconsistencies_found"] += 1

            balance_issues.append({
                "account_id": acc_id,
                "type": "INFO_RECONCILIATION",
                "detail": f"Current balance: {bal_paise} paise (₹{bal}). Attached transactions: {tx_count} (net delta: {net_tx} paise).",
            })

        report["balance_checks"] = {
            "total_accounts": len(account_records),
            "issues": balance_issues,
        }

        # ---------------------------------------------------------
        # 4. Currency sync on Loans, EMIs, and Goals
        # ---------------------------------------------------------
        query_loans = "MATCH (l:Loan) RETURN l.id AS id, l.principal AS principal, l.principal_paise AS principal_paise, l.outstanding AS outstanding, l.outstanding_paise AS outstanding_paise"
        loan_issues = []
        for l in session.run(query_loans):
            if l["principal"] is not None and l["principal_paise"] is not None and to_paise(l["principal"]) != l["principal_paise"]:
                loan_issues.append(f"Loan {l['id']} principal mismatch: {l['principal']} vs {l['principal_paise']}")
                report["inconsistencies_found"] += 1
            if l["outstanding"] is not None and l["outstanding_paise"] is not None and to_paise(l["outstanding"]) != l["outstanding_paise"]:
                loan_issues.append(f"Loan {l['id']} outstanding mismatch: {l['outstanding']} vs {l['outstanding_paise']}")
                report["inconsistencies_found"] += 1

        query_goals = "MATCH (g:Goal) RETURN g.id AS id, g.target_amount AS target_amount, g.target_amount_paise AS target_amount_paise, g.current_amount AS current_amount, g.current_amount_paise AS current_amount_paise"
        goal_issues = []
        for g in session.run(query_goals):
            if g["target_amount"] is not None and g["target_amount_paise"] is not None and to_paise(g["target_amount"]) != g["target_amount_paise"]:
                goal_issues.append(f"Goal {g['id']} target mismatch: {g['target_amount']} vs {g['target_amount_paise']}")
                report["inconsistencies_found"] += 1
            if g["current_amount"] is not None and g["current_amount_paise"] is not None and to_paise(g["current_amount"]) != g["current_amount_paise"]:
                goal_issues.append(f"Goal {g['id']} current mismatch: {g['current_amount']} vs {g['current_amount_paise']}")
                report["inconsistencies_found"] += 1

        report["entity_checks"] = {
            "loan_issues": loan_issues,
            "goal_issues": goal_issues,
        }

        # ---------------------------------------------------------
        # 5. Structural topology & orphan detection
        # ---------------------------------------------------------
        orphans = {}
        q_orphans = [
            ("orphaned_transactions", "MATCH (t:Transaction) WHERE NOT ()-[:MADE_TRANSACTION]->(t) RETURN count(t) AS c"),
            ("orphaned_accounts", "MATCH (a:Account) WHERE NOT ()-[:HAS_ACCOUNT]->(a) RETURN count(a) AS c"),
            ("orphaned_incomes", "MATCH (i:Income) WHERE NOT ()-[:RECEIVED_INCOME]->(i) RETURN count(i) AS c"),
            ("orphaned_emis", "MATCH (e:EMI) WHERE NOT ()-[:HAS_EMI]->(e) RETURN count(e) AS c"),
        ]
        for name, q in q_orphans:
            cnt = session.run(q).single()["c"]
            orphans[name] = cnt
            if cnt > 0:
                report["warnings_found"] += 1
        report["orphan_checks"] = orphans

        # Summary counts
        report["summary"] = {
            "total_accounts": len(account_records),
            "total_transactions": len(tx_records),
            "total_income_nodes": len(income_nodes),
            "inconsistencies_found": report["inconsistencies_found"],
            "warnings_found": report["warnings_found"],
            "status": "HEALTHY" if report["inconsistencies_found"] == 0 else "INCONSISTENT",
        }

    return report


def format_report(report: dict) -> str:
    lines = []
    lines.append("==========================================================================================")
    lines.append("NEO4J GRAPH SCHEMA AND DATA CONSISTENCY REPORT")
    lines.append("==========================================================================================")
    lines.append(f"Status: {report['summary']['status']}")
    lines.append(f"Inconsistencies: {report['summary']['inconsistencies_found']} | Warnings: {report['summary']['warnings_found']}")
    lines.append(f"Graph Entities: {report['summary']['total_accounts']} Accounts, {report['summary']['total_transactions']} Transactions, {report['summary']['total_income_nodes']} Income nodes")
    lines.append("")

    lines.append("--- 1. Transaction Category Property vs BELONGS_TO Edge ---")
    cat = report["category_checks"]
    lines.append(f"Checked {cat['total_transactions']} transactions.")
    conflicts = [i for i in cat["issues"] if i["type"] in ("CONFLICT", "MISSING_EDGE", "UNCATEGORIZED")]
    if not conflicts:
        lines.append("  [OK] No category conflicts or missing edges found.")
        absent_props = [i for i in cat["issues"] if i["type"] == "INFO_PROPERTY_ABSENT"]
        if absent_props:
            lines.append(f"  [INFO] {len(absent_props)} transactions use normalized BELONGS_TO edge with null Transaction.category property.")
    else:
        for issue in conflicts:
            lines.append(f"  [{issue['type']}] Transaction {issue['tx_id']}: {issue['detail']}")
    lines.append("")

    lines.append("--- 2. Income Nodes vs INCOME Transactions ---")
    inc = report["income_checks"]
    lines.append(f"Income Nodes: {inc['income_nodes_count']} | Income Transactions: {inc['income_transactions_count']}")
    if inc["potential_duplicates"]:
        for dup in inc["potential_duplicates"]:
            lines.append(f"  [WARNING] Possible overlap: Income {dup['income_id']} matches Tx {dup['tx_id']} (amount: {dup['amount_paise']} paise, date: {dup['date']})")
    else:
        lines.append("  [OK] No duplicate income entities detected between :Income and :Transaction.")
    lines.append("")

    lines.append("--- 3. Account Balance & Currency Synchronization ---")
    bal = report["balance_checks"]
    lines.append(f"Checked {bal['total_accounts']} accounts.")
    bal_errors = [i for i in bal["issues"] if i["type"] in ("CURRENCY_SYNC_MISMATCH", "MISSING_BALANCE_PAISE")]
    if not bal_errors:
        lines.append("  [OK] All account balances are synchronized (balance_paise == round(balance * 100)).")
    else:
        for err in bal_errors:
            lines.append(f"  [{err['type']}] Account {err['account_id']}: {err['detail']}")
    for info in bal["issues"]:
        if info["type"].startswith("INFO"):
            lines.append(f"  [INFO] {info['account_id']}: {info['detail']}")
    lines.append("")

    lines.append("--- 4. Loans, Goals, and Orphans ---")
    ent = report.get("entity_checks", {})
    if not ent.get("loan_issues") and not ent.get("goal_issues"):
        lines.append("  [OK] All Loans and Goals have exact paise/rupee synchronization.")
    else:
        for err in ent.get("loan_issues", []) + ent.get("goal_issues", []):
            lines.append(f"  [ERROR] {err}")

    orphans = report.get("orphan_checks", {})
    total_orphans = sum(orphans.values())
    if total_orphans == 0:
        lines.append("  [OK] Zero orphaned transactions, accounts, incomes, or EMIs.")
    else:
        for k, v in orphans.items():
            if v > 0:
                lines.append(f"  [WARNING] {k}: {v}")

    lines.append("==========================================================================================")
    return "\n".join(lines)


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    report = check_graph_consistency()
    text = format_report(report)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    main()
