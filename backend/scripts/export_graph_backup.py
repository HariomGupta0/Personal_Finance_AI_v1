"""
Graph export backup script for Neo4j.

Restore Notes:
The supported restore path is neo4j-admin database restore or programmatic
re-import from this JSON export.
WARNING: This file contains personal financial data. Handle and store securely.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
import logging
from pathlib import Path
import sys
from typing import Any

from neo4j import GraphDatabase
try:
    from neo4j.time import Date as Neo4jDate, DateTime as Neo4jDateTime, Time as Neo4jTime
except ImportError:
    Neo4jDate = type("Neo4jDate", (), {})
    Neo4jDateTime = type("Neo4jDateTime", (), {})
    Neo4jTime = type("Neo4jTime", (), {})

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

logger = logging.getLogger("export_graph_backup")


def serialize_value(val: Any) -> Any:
    """
    Serialize Neo4j property values into JSON-compatible objects with type markers
    for date, datetime, and time objects.
    """
    if val is None or isinstance(val, (int, float, str, bool)):
        return val

    if isinstance(val, (datetime, Neo4jDateTime)):
        iso_val = val.iso_format() if hasattr(val, "iso_format") else val.isoformat()
        return {"$type": "datetime", "$value": iso_val}

    if isinstance(val, (date, Neo4jDate)):
        iso_val = val.iso_format() if hasattr(val, "iso_format") else val.isoformat()
        return {"$type": "date", "$value": iso_val}

    if isinstance(val, (time, Neo4jTime)):
        iso_val = val.iso_format() if hasattr(val, "iso_format") else val.isoformat()
        return {"$type": "time", "$value": iso_val}

    if isinstance(val, Decimal):
        return {"$type": "decimal", "$value": str(val)}

    if isinstance(val, list):
        return [serialize_value(item) for item in val]

    if isinstance(val, dict):
        return {str(k): serialize_value(v) for k, v in val.items()}

    return str(val)


def is_path_inside_repo(path: Path) -> bool:
    """Check if the given path is located inside the repository directory."""
    repo_root = Path(__file__).resolve().parents[2]
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
        return True
    except ValueError:
        return False


def export_graph_backup(database: str, out_path: Path, batch_size: int = 1000) -> dict:
    """
    Read-only streaming export of all nodes and relationships to a JSON file.
    Refuses to write inside the repository directory.
    """
    if is_path_inside_repo(out_path):
        raise ValueError(f"Refusing to write backup inside repository: {out_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    node_counts: Counter[str] = Counter()
    rel_counts: Counter[str] = Counter()
    nodes_list: list[dict] = []
    rels_list: list[dict] = []

    try:
        with driver.session(database=database) as session:
            # 1. Stream Nodes
            skip = 0
            while True:
                result = session.run(
                    """
                    MATCH (n)
                    RETURN id(n) AS internal_id, elementId(n) AS element_id,
                           labels(n) AS labels, properties(n) AS props
                    ORDER BY id(n)
                    SKIP $skip LIMIT $limit
                    """,
                    skip=skip,
                    limit=batch_size,
                )
                batch = list(result)
                if not batch:
                    break

                for record in batch:
                    lbls = list(record["labels"])
                    for lbl in lbls:
                        node_counts[lbl] += 1
                    props = serialize_value(dict(record["props"]))
                    nodes_list.append({
                        "id": record["internal_id"],
                        "element_id": record["element_id"],
                        "labels": lbls,
                        "properties": props,
                    })

                skip += len(batch)
                if len(batch) < batch_size:
                    break

            # 2. Stream Relationships
            skip = 0
            while True:
                result = session.run(
                    """
                    MATCH ()-[r]->()
                    RETURN id(r) AS internal_id, elementId(r) AS element_id,
                           type(r) AS type,
                           id(startNode(r)) AS start_id, elementId(startNode(r)) AS start_element_id,
                           id(endNode(r)) AS end_id, elementId(endNode(r)) AS end_element_id,
                           properties(r) AS props
                    ORDER BY id(r)
                    SKIP $skip LIMIT $limit
                    """,
                    skip=skip,
                    limit=batch_size,
                )
                batch = list(result)
                if not batch:
                    break

                for record in batch:
                    r_type = record["type"]
                    rel_counts[r_type] += 1
                    props = serialize_value(dict(record["props"]))
                    rels_list.append({
                        "id": record["internal_id"],
                        "element_id": record["element_id"],
                        "type": r_type,
                        "start_node_id": record["start_id"],
                        "start_element_id": record["start_element_id"],
                        "end_node_id": record["end_id"],
                        "end_element_id": record["end_element_id"],
                        "properties": props,
                    })

                skip += len(batch)
                if len(batch) < batch_size:
                    break
    finally:
        driver.close()

    backup_payload = {
        "_restore_notes": (
            "The supported restore path is neo4j-admin database restore or re-import "
            "from this JSON file. Note: This file contains personal financial data; handle securely."
        ),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "database": database,
        "total_nodes": len(nodes_list),
        "total_relationships": len(rels_list),
        "node_counts": dict(node_counts),
        "relationship_counts": dict(rel_counts),
        "nodes": nodes_list,
        "relationships": rels_list,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(backup_payload, f, indent=2, ensure_ascii=False)

    return backup_payload


def main():
    parser = argparse.ArgumentParser(description="Export Neo4j graph backup to JSON")
    parser.add_argument(
        "--database",
        default=NEO4J_DATABASE,
        help=f"Neo4j database name (default: {NEO4J_DATABASE})",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Path to output JSON file (must be outside the repository)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for streaming nodes and relationships",
    )
    args = parser.parse_args()

    try:
        payload = export_graph_backup(args.database, args.out, batch_size=args.batch_size)
    except Exception as exc:
        print(f"Error during graph backup: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully exported {payload['total_nodes']} nodes and {payload['total_relationships']} relationships to {args.out}")
    print("Node counts per label:")
    for lbl, cnt in sorted(payload["node_counts"].items()):
        print(f"  {lbl}: {cnt}")
    print("Relationship counts per type:")
    for r_type, cnt in sorted(payload["relationship_counts"].items()):
        print(f"  {r_type}: {cnt}")


if __name__ == "__main__":
    main()
