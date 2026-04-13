"""
tests/integration/test_backend_api.py — Integration tests for the FastAPI backend.

Uses FastAPI's TestClient + a patched GroupManager so no real git clone or
filesystem I/O is required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Make scripts and examples importable
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_mock_manager(groups: list[dict] | None = None, entries: list[dict] | None = None):
    """Return a MagicMock GroupManager pre-configured with canned data."""
    m = MagicMock()
    _groups = list(groups or [])
    _entries = list(entries or [])

    m.list_groups.return_value = _groups
    m.create_group.side_effect = lambda **kw: {**kw, "created_at": "2024-01-01T00:00:00Z"}
    m.get_group.side_effect = lambda gid: next(
        (g for g in _groups if g["group_id"] == gid),
        (_ for _ in ()).throw(KeyError(gid)),
    )
    m.delete_group.side_effect = lambda gid: None
    m.get_entries.return_value = _entries
    m.get_latest_entry.return_value = _entries[-1] if _entries else None
    m.validate_group_log.return_value = True
    m.append_entry.side_effect = lambda gid, entry: {
        "entry_number": len(_entries) + 1,
        "date": "2024-06-01T00:00:00Z",
        "actor_wallet": entry.get("actor_wallet", ""),
        "action_type": entry.get("action_type", ""),
        "description": entry.get("description", ""),
        "community_url": "https://x.com/i/communities/1981771124343283876",
        "x_tweet_id": "",
        "verified_by": [],
        **{k: v for k, v in entry.items() if k not in ("actor_wallet", "action_type", "description")},
    }
    return m


SAMPLE_GROUP = {
    "group_id":   "test-group",
    "group_name": "Test Archery Batch",
    "discipline": "archery",
    "members": [
        {"name": "Alice", "wallet": "0xAAA"},
        {"name": "Bob",   "wallet": "0xBBB"},
    ],
    "created_at": "2024-01-01T00:00:00Z",
}

SAMPLE_ENTRY = {
    "entry_number": 1,
    "date": "2024-06-01T00:00:00Z",
    "actor_wallet": "0xAAA",
    "action_type": "archery_practice",
    "description": "Test session",
    "score": 250,
    "distance_m": 18,
    "community_url": "https://x.com/i/communities/1981771124343283876",
    "x_tweet_id": "",
    "verified_by": [],
}


@pytest.fixture()
def client_empty():
    """TestClient with no groups provisioned."""
    mock_mgr = _make_mock_manager()
    with patch("examples.integration.backend.app._get_manager", return_value=mock_mgr):
        from examples.integration.backend.app import app
        with TestClient(app) as c:
            yield c, mock_mgr


@pytest.fixture()
def client_with_group():
    """TestClient with one group and one log entry."""
    mock_mgr = _make_mock_manager(groups=[SAMPLE_GROUP], entries=[SAMPLE_ENTRY])
    with patch("examples.integration.backend.app._get_manager", return_value=mock_mgr):
        from examples.integration.backend.app import app
        with TestClient(app) as c:
            yield c, mock_mgr


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client_empty):
        client, _ = client_empty
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Groups CRUD ───────────────────────────────────────────────────────────────

class TestGroupsCRUD:
    def test_list_groups_empty(self, client_empty):
        client, _ = client_empty
        resp = client.get("/groups")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_groups_with_data(self, client_with_group):
        client, _ = client_with_group
        resp = client.get("/groups")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_group_success(self, client_empty):
        client, mock_mgr = client_empty
        payload = {
            "group_id":   "new-group",
            "group_name": "New Group",
            "discipline": "archery",
            "members": [
                {"name": "Alice", "wallet": "0xAAA"},
                {"name": "Bob",   "wallet": "0xBBB"},
            ],
        }
        resp = client.post("/groups", json=payload)
        assert resp.status_code == 201
        mock_mgr.create_group.assert_called_once()

    def test_create_group_too_few_members(self, client_empty):
        client, _ = client_empty
        payload = {
            "group_id":   "one-member",
            "group_name": "Solo",
            "discipline": "archery",
            "members": [{"name": "Alice", "wallet": "0xAAA"}],
        }
        resp = client.post("/groups", json=payload)
        assert resp.status_code == 422

    def test_create_group_too_many_members(self, client_empty):
        client, _ = client_empty
        payload = {
            "group_id":   "big-group",
            "group_name": "Big Group",
            "discipline": "archery",
            "members": [{"name": f"M{i}", "wallet": ""} for i in range(10)],
        }
        resp = client.post("/groups", json=payload)
        assert resp.status_code == 422

    def test_create_group_invalid_id(self, client_empty):
        client, _ = client_empty
        payload = {
            "group_id":   "INVALID ID!",
            "group_name": "Bad ID Group",
            "discipline": "archery",
            "members": [
                {"name": "A", "wallet": ""},
                {"name": "B", "wallet": ""},
            ],
        }
        resp = client.post("/groups", json=payload)
        assert resp.status_code == 422

    def test_create_group_duplicate(self, client_empty):
        client, mock_mgr = client_empty
        mock_mgr.create_group.side_effect = FileExistsError("already exists")
        payload = {
            "group_id":   "dup",
            "group_name": "Dup",
            "discipline": "archery",
            "members": [
                {"name": "A", "wallet": ""},
                {"name": "B", "wallet": ""},
            ],
        }
        resp = client.post("/groups", json=payload)
        assert resp.status_code == 409

    def test_get_group_not_found(self, client_empty):
        client, mock_mgr = client_empty
        mock_mgr.get_group.side_effect = KeyError("nope")
        resp = client.get("/groups/nope")
        assert resp.status_code == 404

    def test_delete_group(self, client_with_group):
        client, mock_mgr = client_with_group
        resp = client.delete("/groups/test-group")
        assert resp.status_code == 200
        mock_mgr.delete_group.assert_called_once_with("test-group")


# ── Log read ──────────────────────────────────────────────────────────────────

class TestLogRead:
    def test_get_log(self, client_with_group):
        client, _ = client_with_group
        resp = client.get("/groups/test-group/log")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["entry_number"] == 1

    def test_get_latest(self, client_with_group):
        client, _ = client_with_group
        resp = client.get("/groups/test-group/log/latest")
        assert resp.status_code == 200
        assert resp.json()["entry_number"] == 1

    def test_get_latest_empty(self, client_empty):
        client, mock_mgr = client_empty
        mock_mgr.get_latest_entry.return_value = None
        mock_mgr.get_group.return_value = SAMPLE_GROUP  # group exists
        resp = client.get("/groups/test-group/log/latest")
        assert resp.status_code == 404

    def test_validate_ok(self, client_with_group):
        client, _ = client_with_group
        resp = client.get("/groups/test-group/validate")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True


# ── Log write — Archery ───────────────────────────────────────────────────────

class TestArcheryRecord:
    def test_record_archery_minimal(self, client_with_group):
        client, mock_mgr = client_with_group
        payload = {
            "actor_wallet": "0xAAA",
            "description":  "Monday 30 arrows",
        }
        resp = client.post("/groups/test-group/log/archery", json=payload)
        assert resp.status_code == 201
        mock_mgr.append_entry.assert_called_once()
        entry = resp.json()
        assert entry["action_type"] == "archery_practice"

    def test_record_archery_full(self, client_with_group):
        client, mock_mgr = client_with_group
        payload = {
            "actor_wallet": "0xAAA",
            "description":  "Full session",
            "score":        275,
            "distance_m":   18,
            "arrow_count":  36,
            "form_notes":   "Great follow-through",
        }
        resp = client.post("/groups/test-group/log/archery", json=payload)
        assert resp.status_code == 201
        called_entry = mock_mgr.append_entry.call_args[0][1]
        assert called_entry["score"] == 275
        assert called_entry["form_notes"] == "Great follow-through"

    def test_record_archery_invalid_score(self, client_with_group):
        client, _ = client_with_group
        payload = {
            "actor_wallet": "0xAAA",
            "description":  "Bad score",
            "score":        999,   # > 300
        }
        resp = client.post("/groups/test-group/log/archery", json=payload)
        assert resp.status_code == 422

    def test_record_archery_missing_description(self, client_with_group):
        client, _ = client_with_group
        payload = {"actor_wallet": "0xAAA"}
        resp = client.post("/groups/test-group/log/archery", json=payload)
        assert resp.status_code == 422


# ── Log write — Sanskrit ──────────────────────────────────────────────────────

class TestSanskritRecord:
    def test_record_sanskrit_minimal(self, client_with_group):
        client, mock_mgr = client_with_group
        payload = {
            "actor_wallet": "0xBBB",
            "description":  "Gayatri Mantra",
        }
        resp = client.post("/groups/test-group/log/sanskrit", json=payload)
        assert resp.status_code == 201
        entry = resp.json()
        assert entry["action_type"] == "sanskrit_recitation"

    def test_record_sanskrit_full(self, client_with_group):
        client, mock_mgr = client_with_group
        payload = {
            "actor_wallet":    "0xBBB",
            "description":     "Rigveda 3.62.10 — 3 rounds",
            "text_reference":  "Rigveda 3.62.10",
            "recitation_hash": "sha256:abc123",
            "duration_seconds": 87,
            "accuracy_pct":     92,
        }
        resp = client.post("/groups/test-group/log/sanskrit", json=payload)
        assert resp.status_code == 201
        called_entry = mock_mgr.append_entry.call_args[0][1]
        assert called_entry["recitation_hash"] == "sha256:abc123"
        assert called_entry["accuracy_pct"] == 92

    def test_record_sanskrit_invalid_accuracy(self, client_with_group):
        client, _ = client_with_group
        payload = {
            "actor_wallet":  "0xBBB",
            "description":   "Test",
            "accuracy_pct":  150,  # > 100
        }
        resp = client.post("/groups/test-group/log/sanskrit", json=payload)
        assert resp.status_code == 422


# ── Custom entry ──────────────────────────────────────────────────────────────

class TestCustomEntry:
    def test_record_custom(self, client_with_group):
        client, mock_mgr = client_with_group
        payload = {
            "actor_wallet": "0xAAA",
            "action_type":  "group_milestone",
            "description":  "Completed 100 practice sessions",
            "extra":        {"total_sessions": 100},
        }
        resp = client.post("/groups/test-group/log/custom", json=payload)
        assert resp.status_code == 201
        entry = resp.json()
        assert entry["action_type"] == "group_milestone"
