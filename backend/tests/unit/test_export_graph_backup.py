"""
Unit tests for backend/scripts/export_graph_backup.py.
Verifies serializer logic and path rejection without needing a database connection.
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from backend.scripts.export_graph_backup import serialize_value, is_path_inside_repo


def test_serialize_primitive_values():
    assert serialize_value(100) == 100
    assert serialize_value(12.34) == 12.34
    assert serialize_value("hello world") == "hello world"
    assert serialize_value(True) is True
    assert serialize_value(False) is False
    assert serialize_value(None) is None


def test_serialize_dates_and_times():
    d = date(2026, 10, 31)
    res_d = serialize_value(d)
    assert res_d == {"$type": "date", "$value": "2026-10-31"}

    dt = datetime(2026, 10, 31, 14, 30, 45, tzinfo=timezone.utc)
    res_dt = serialize_value(dt)
    assert res_dt == {"$type": "datetime", "$value": "2026-10-31T14:30:45+00:00"}

    t = time(12, 0, 15)
    res_t = serialize_value(t)
    assert res_t == {"$type": "time", "$value": "12:00:15"}


def test_serialize_nested_collections():
    payload = {
        "user_id": "U123",
        "created_at": datetime(2026, 1, 1, 10, 0, 0),
        "scores": [1, 2, 3],
        "balance": Decimal("500.50"),
        "meta": {
            "date": date(2026, 1, 1),
            "tags": ["alpha", "beta"],
        },
    }
    serialized = serialize_value(payload)
    assert serialized["user_id"] == "U123"
    assert serialized["created_at"] == {"$type": "datetime", "$value": "2026-01-01T10:00:00"}
    assert serialized["scores"] == [1, 2, 3]
    assert serialized["balance"] == {"$type": "decimal", "$value": "500.50"}
    assert serialized["meta"]["date"] == {"$type": "date", "$value": "2026-01-01"}
    assert serialized["meta"]["tags"] == ["alpha", "beta"]


def test_is_path_inside_repo():
    repo_root = Path(__file__).resolve().parents[3]
    inside_path = repo_root / "backend" / "backup.json"
    assert is_path_inside_repo(inside_path) is True

    outside_path = repo_root.parent / "money_checks" / "backup.json"
    assert is_path_inside_repo(outside_path) is False
