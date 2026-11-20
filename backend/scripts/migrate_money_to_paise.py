"""
Database migration script: migrate money properties to integer paise.

Properties migrated:
- Account.balance -> balance_paise
- Transaction.amount -> amount_paise
- Income.amount -> amount_paise
- Loan.principal -> principal_paise
- Loan.outstanding -> outstanding_paise
- EMI.amount -> amount_paise
- Goal.target_amount -> target_amount_paise
- Goal.current_amount -> current_amount_paise

Contract:
- Pure integer paise arithmetic in Python via Decimal and ROUND_HALF_UP (to_paise).
- Never compute paise in Cypher.
- Never delete or overwrite legacy rupee properties.
- Fail fast and abort on >2-decimal values unless --allow-rounding is passed.
- Idempotent: detects drift and never overwrites conflicting *_paise values.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any, Sequence
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from neo4j import GraphDatabase

from backend.app.core.money import to_paise
from backend.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

logger = logging.getLogger("migrate_money_to_paise")

PROPERTIES_TO_MIGRATE: list[tuple[str, str, str]] = [
    ("Account", "balance", "balance_paise"),
    ("Transaction", "amount", "amount_paise"),
    ("Income", "amount", "amount_paise"),
    ("Loan", "principal", "principal_paise"),
    ("Loan", "outstanding", "outstanding_paise"),
    ("EMI", "amount", "amount_paise"),
    ("Goal", "target_amount", "target_amount_paise"),
    ("Goal", "current_amount", "current_amount_paise"),
]


@dataclass
class NodeMoneyRecord:
    node_id: int
    element_id: str
    legacy_val: Any
    existing_paise: int | None = None


@dataclass
class CensusResult:
    label: str
    property_name: str
    target_property: str
    total_nodes: int = 0
    null_count: int = 0
    int_count: int = 0
    float_count: int = 0
    other_type_count: int = 0
    min_val: float | None = None
    max_val: float | None = None
    over_two_decimals_count: int = 0
    over_two_decimals_samples: list[tuple[int, Any]] = field(default_factory=list)
    already_migrated_count: int = 0
    would_migrate_count: int = 0
    mismatch_drift_count: int = 0
    mismatch_samples: list[tuple[int, Any, int, int]] = field(default_factory=list)  # (id, legacy, existing_paise, computed_paise)


@dataclass
class VerificationResult:
    label: str
    property_name: str
    target_property: str
    legacy_count: int
    paise_count: int
    count_matches: bool
    legacy_sum_paise: int
    paise_sum: int
    sum_matches: bool


def has_more_than_two_decimals(val: Any) -> bool:
    """Check if a numeric value has more than 2 decimal places using Decimal."""
    if val is None or isinstance(val, bool):
        return False
    try:
        d = Decimal(str(val))
    except Exception:
        return False
    # Normalize to strip insignificant trailing zeros from strings if any,
    # but preserve canonical decimal places
    t = d.as_tuple()
    # In Decimal, exponent < -2 means fractional places beyond hundredths
    return t.exponent < -2


def analyze_records(
    label: str,
    legacy_prop: str,
    target_prop: str,
    records: Sequence[NodeMoneyRecord],
) -> tuple[CensusResult, list[tuple[int, int]]]:
    """
    Perform census on records and prepare batch migration list [(node_id, computed_paise)].
    Returns (census_result, items_to_write).
    """
    census = CensusResult(label=label, property_name=legacy_prop, target_property=target_prop)
    census.total_nodes = len(records)
    items_to_write: list[tuple[int, int]] = []

    numeric_vals: list[float] = []

    for rec in records:
        v = rec.legacy_val
        if v is None:
            census.null_count += 1
            continue

        if isinstance(v, bool):
            census.other_type_count += 1
            continue
        elif isinstance(v, int):
            census.int_count += 1
            numeric_vals.append(float(v))
        elif isinstance(v, float):
            census.float_count += 1
            numeric_vals.append(v)
        else:
            try:
                numeric_vals.append(float(v))
                census.other_type_count += 1
            except (ValueError, TypeError):
                census.other_type_count += 1
                continue

        # Decimal precision census
        if has_more_than_two_decimals(v):
            census.over_two_decimals_count += 1
            if len(census.over_two_decimals_samples) < 10:
                census.over_two_decimals_samples.append((rec.node_id, v))

        # Compute paise in Python
        computed_paise = to_paise(v)

        if rec.existing_paise is not None:
            if rec.existing_paise == computed_paise:
                census.already_migrated_count += 1
            else:
                census.mismatch_drift_count += 1
                if len(census.mismatch_samples) < 10:
                    census.mismatch_samples.append(
                        (rec.node_id, v, rec.existing_paise, computed_paise)
                    )
        else:
            census.would_migrate_count += 1
            items_to_write.append((rec.node_id, computed_paise))

    if numeric_vals:
        census.min_val = min(numeric_vals)
        census.max_val = max(numeric_vals)

    return census, items_to_write


def fetch_money_records(session, label: str, legacy_prop: str, target_prop: str) -> list[NodeMoneyRecord]:
    """Fetch all nodes for a label with their legacy and target money properties."""
    query = f"""
    MATCH (n:{label})
    RETURN id(n) AS node_id, elementId(n) AS element_id,
           n.{legacy_prop} AS legacy_val,
           n.{target_prop} AS existing_paise
    ORDER BY id(n)
    """
    records: list[NodeMoneyRecord] = []
    for row in session.run(query):
        records.append(
            NodeMoneyRecord(
                node_id=row["node_id"],
                element_id=row["element_id"],
                legacy_val=row["legacy_val"],
                existing_paise=row["existing_paise"],
            )
        )
    return records


def write_paise_batch(session, label: str, target_prop: str, batch: list[tuple[int, int]]) -> None:
    """Write integer paise values using UNWIND and integer parameters."""
    query = f"""
    UNWIND $batch AS item
    MATCH (n:{label})
    WHERE id(n) = item.id
    SET n.{target_prop} = item.paise
    """
    session.run(query, batch=[{"id": nid, "paise": p} for nid, p in batch])


def verify_property_migration(session, label: str, legacy_prop: str, target_prop: str) -> VerificationResult:
    """Verify post-migration consistency between legacy and paise properties."""
    query = f"""
    MATCH (n:{label})
    WHERE n.{legacy_prop} IS NOT NULL
    RETURN id(n) AS node_id, n.{legacy_prop} AS legacy_val, n.{target_prop} AS paise_val
    """
    legacy_count = 0
    paise_count = 0
    legacy_sum_paise = 0
    paise_sum = 0

    for row in session.run(query):
        legacy_count += 1
        legacy_v = row["legacy_val"]
        paise_v = row["paise_val"]

        if paise_v is not None:
            paise_count += 1
            paise_sum += int(paise_v)

        if legacy_v is not None and not isinstance(legacy_v, bool):
            legacy_sum_paise += to_paise(legacy_v)

    return VerificationResult(
        label=label,
        property_name=legacy_prop,
        target_property=target_prop,
        legacy_count=legacy_count,
        paise_count=paise_count,
        count_matches=(legacy_count == paise_count),
        legacy_sum_paise=legacy_sum_paise,
        paise_sum=paise_sum,
        sum_matches=(legacy_sum_paise == paise_sum),
    )


def check_account_drift(session) -> list[dict[str, Any]]:
    """
    Informational check: for each Account, report stored balance_paise vs
    (sum of INCOME minus sum of EXPENSE transaction paise).
    """
    query = """
    MATCH (a:Account)
    OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(tx_exp:Transaction)
    WHERE tx_exp.type = 'EXPENSE' OR tx_exp.type IS NULL
    WITH a, coalesce(sum(tx_exp.amount_paise), 0) AS total_expense_paise
    OPTIONAL MATCH (a)-[:MADE_TRANSACTION]->(tx_inc:Transaction)
    WHERE tx_inc.type = 'INCOME'
    WITH a, total_expense_paise, coalesce(sum(tx_inc.amount_paise), 0) AS total_tx_income_paise
    OPTIONAL MATCH (u:User)-[:HAS_ACCOUNT]->(a)
    OPTIONAL MATCH (u)-[:RECEIVED_INCOME]->(inc:Income)
    WITH a, total_expense_paise, total_tx_income_paise, coalesce(sum(inc.amount_paise), 0) AS user_income_paise
    RETURN a.id AS account_id, a.bank AS bank, a.balance AS legacy_balance,
           a.balance_paise AS balance_paise,
           total_expense_paise, total_tx_income_paise, user_income_paise
    ORDER BY a.id
    """
    results: list[dict[str, Any]] = []
    for row in session.run(query):
        stored_paise = row["balance_paise"]
        total_income_paise = int(row["total_tx_income_paise"]) + int(row["user_income_paise"])
        total_expense_paise = int(row["total_expense_paise"])
        net_calculated_paise = total_income_paise - total_expense_paise
        drift_paise = (stored_paise - net_calculated_paise) if stored_paise is not None else None

        results.append({
            "account_id": row["account_id"],
            "bank": row["bank"],
            "legacy_balance": row["legacy_balance"],
            "balance_paise": stored_paise,
            "total_income_paise": total_income_paise,
            "total_expense_paise": total_expense_paise,
            "net_calculated_paise": net_calculated_paise,
            "drift_paise": drift_paise,
        })
    return results


def run_migration(
    database: str = NEO4J_DATABASE,
    dry_run: bool = True,
    allow_rounding: bool = False,
    batch_size: int = 1000,
) -> bool:
    """
    Execute migration census, safety checks, batch execution, and verification.
    Returns True if migration succeeded with 0 mismatches/errors, False otherwise.
    """
    mode_str = "DRY-RUN (no changes will be written)" if dry_run else "REAL APPLY (writing to database)"
    print(f"\n=======================================================")
    print(f"Starting Money-to-Paise Migration: {mode_str}")
    print(f"Database: {database} | Allow Rounding: {allow_rounding}")
    print(f"=======================================================\n")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    has_errors = False

    all_censuses: list[CensusResult] = []
    all_pending_batches: list[tuple[str, str, list[tuple[int, int]]]] = []

    try:
        with driver.session(database=database) as session:
            # Step 1: Census and Planning across all properties
            total_over_two_decimals = 0
            total_mismatches = 0

            for label, legacy_prop, target_prop in PROPERTIES_TO_MIGRATE:
                records = fetch_money_records(session, label, legacy_prop, target_prop)
                census, items_to_write = analyze_records(label, legacy_prop, target_prop, records)
                all_censuses.append(census)
                all_pending_batches.append((label, target_prop, items_to_write))

                total_over_two_decimals += census.over_two_decimals_count
                total_mismatches += census.mismatch_drift_count

            # Print Census Table
            print("CENSUS SUMMARY:")
            header = f"{'Label.Property':<30} | {'Total':<6} | {'Null':<5} | {'Int':<5} | {'Float':<5} | {'>2 Dec':<6} | {'Min':<10} | {'Max':<10} | {'Already':<7} | {'Pending':<7} | {'Drift':<5}"
            print("-" * len(header))
            print(header)
            print("-" * len(header))
            for c in all_censuses:
                prop_str = f"{c.label}.{c.property_name}"
                min_s = f"{c.min_val:.2f}" if c.min_val is not None else "-"
                max_s = f"{c.max_val:.2f}" if c.max_val is not None else "-"
                print(
                    f"{prop_str:<30} | {c.total_nodes:<6} | {c.null_count:<5} | {c.int_count:<5} | "
                    f"{c.float_count:<5} | {c.over_two_decimals_count:<6} | {min_s:<10} | {max_s:<10} | "
                    f"{c.already_migrated_count:<7} | {c.would_migrate_count:<7} | {c.mismatch_drift_count:<5}"
                )
            print("-" * len(header) + "\n")

            # Check >2 decimal places abort condition
            if total_over_two_decimals > 0:
                if not allow_rounding:
                    print(f"ABORT: Found {total_over_two_decimals} values with >2 decimal places and --allow-rounding was NOT specified.")
                    print("Samples with >2 decimal places:")
                    for c in all_censuses:
                        for nid, val in c.over_two_decimals_samples:
                            print(f"  {c.label}.{c.property_name} on node id {nid}: {val}")
                    return False
                else:
                    print(f"NOTICE: --allow-rounding active. Found {total_over_two_decimals} values with >2 decimals; rounding with ROUND_HALF_UP:")
                    for c in all_censuses:
                        for nid, val in c.over_two_decimals_samples:
                            rounded_paise = to_paise(val)
                            print(f"  {c.label}.{c.property_name} node {nid}: {val} -> {rounded_paise} paise")

            # Check existing drift/mismatch abort condition
            if total_mismatches > 0:
                print(f"ERROR: Found {total_mismatches} nodes where existing *_paise DIFFERS from legacy value.")
                print("Refusing to overwrite conflicting paise values. Mismatch samples:")
                for c in all_censuses:
                    for nid, leg_val, existing_p, comp_p in c.mismatch_samples:
                        print(f"  {c.label} node {nid}: legacy={leg_val}, existing_paise={existing_p}, computed={comp_p}")
                has_errors = True
                return False

            # Step 2: Apply writes if not dry-run
            if dry_run:
                print("Dry-run complete. No database writes were performed. Use --apply to execute migration.")
                return True

            print("Applying migration batches to database...")
            for label, target_prop, items in all_pending_batches:
                if not items:
                    continue
                print(f"  Writing {len(items)} nodes for {label}.{target_prop} in batches of {batch_size}...")
                for i in range(0, len(items), batch_size):
                    batch_chunk = items[i : i + batch_size]
                    write_paise_batch(session, label, target_prop, batch_chunk)

            # Step 3: Verification
            print("\nVERIFYING MIGRATION INTEGRITY:")
            v_header = f"{'Label.Property':<32} | {'Legacy Cnt':<10} | {'Paise Cnt':<10} | {'Count Match':<11} | {'Legacy Sum (P)':<15} | {'Paise Sum':<15} | {'Sum Match':<9}"
            print("-" * len(v_header))
            print(v_header)
            print("-" * len(v_header))

            for label, legacy_prop, target_prop in PROPERTIES_TO_MIGRATE:
                vres = verify_property_migration(session, label, legacy_prop, target_prop)
                c_match_str = "YES" if vres.count_matches else "FAIL"
                s_match_str = "YES" if vres.sum_matches else "FAIL"
                prop_str = f"{label}.{legacy_prop} -> {target_prop}"
                print(
                    f"{prop_str:<32} | {vres.legacy_count:<10} | {vres.paise_count:<10} | {c_match_str:<11} | "
                    f"{vres.legacy_sum_paise:<15} | {vres.paise_sum:<15} | {s_match_str:<9}"
                )
                if not vres.count_matches or not vres.sum_matches:
                    has_errors = True

            print("-" * len(v_header) + "\n")

            # Step 4: Informational Account Balance Drift Check
            print("INFORMATIONAL: Account Balance Drift Audit (stored vs net transaction/income):")
            acc_drifts = check_account_drift(session)
            for acc in acc_drifts:
                print(
                    f"  Account [{acc['account_id']}] ({acc['bank']}): "
                    f"Stored Paise = {acc['balance_paise']} | "
                    f"Income Paise = {acc['total_income_paise']} | "
                    f"Expense Paise = {acc['total_expense_paise']} | "
                    f"Net Calc Paise = {acc['net_calculated_paise']} | "
                    f"Drift = {acc['drift_paise']}"
                )

    finally:
        driver.close()

    if has_errors:
        print("\nMIGRATION COMPLETED WITH ERRORS OR VERIFICATION FAILURES.")
        return False

    print("\nMIGRATION COMPLETED SUCCESSFULLY WITH EXACT INTEGER PARITY.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate Neo4j money properties to integer paise")
    parser.add_argument(
        "--database",
        default=NEO4J_DATABASE,
        help=f"Neo4j database name (default: {NEO4J_DATABASE})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes to the database (default is dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry run without modifying database (default)",
    )
    parser.add_argument(
        "--allow-rounding",
        action="store_true",
        default=False,
        help="Allow rounding of values with >2 decimal places using ROUND_HALF_UP",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for writing updates (default: 1000)",
    )
    args = parser.parse_args()

    # Determine execution mode: --apply overrides default dry-run
    dry_run = not args.apply

    success = run_migration(
        database=args.database,
        dry_run=dry_run,
        allow_rounding=args.allow_rounding,
        batch_size=args.batch_size,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
