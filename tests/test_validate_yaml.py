"""
tests/test_validate_yaml.py — Unit tests for the validate_yaml script.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validate_yaml import (
    entry_fingerprint,
    load_yaml,
    validate_no_regressions,
    validate_structure,
    main as validate_main,
)

COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"


def _write_yaml(path: Path, data: dict) -> None:
    with path.open("w") as fh:
        yaml.dump(data, fh, default_flow_style=False)


def _minimal_valid_entry(n: int = 1) -> dict:
    return {
        "entry_number": n,
        "date": "2024-01-01T00:00:00Z",
        "actor_wallet": "0x1",
        "action_type": "governance_vote",
        "description": f"Entry {n}",
        "media_hashes": [],
        "ipfs_hashes": [],
        "x_tweet_id": "",
        "community_url": COMMUNITY_URL,
        "verified_by": [],
    }


def _minimal_valid_data(entries: list[dict] | None = None) -> dict:
    return {
        "metadata": {"dao_name": "Test"},
        "members": [],
        "updates": entries or [],
    }


# ── validate_structure ────────────────────────────────────────────────────────

class TestValidateStructure:
    def test_valid_empty_updates(self) -> None:
        errors = validate_structure(_minimal_valid_data())
        assert errors == []

    def test_valid_one_entry(self) -> None:
        errors = validate_structure(_minimal_valid_data([_minimal_valid_entry()]))
        assert errors == []

    def test_missing_metadata(self) -> None:
        data = _minimal_valid_data()
        del data["metadata"]
        errors = validate_structure(data)
        assert any("metadata" in e for e in errors)

    def test_missing_updates(self) -> None:
        data = _minimal_valid_data()
        del data["updates"]
        errors = validate_structure(data)
        assert any("updates" in e for e in errors)

    def test_duplicate_entry_numbers(self) -> None:
        data = _minimal_valid_data([_minimal_valid_entry(1), _minimal_valid_entry(1)])
        errors = validate_structure(data)
        assert any("duplicate" in e.lower() for e in errors)

    def test_missing_required_field(self) -> None:
        entry = _minimal_valid_entry()
        del entry["actor_wallet"]
        errors = validate_structure(_minimal_valid_data([entry]))
        assert any("actor_wallet" in e for e in errors)

    def test_blood_succession_missing_video_hash(self) -> None:
        entry = _minimal_valid_entry()
        entry["action_type"] = "blood_succession"
        entry["successor_wallet"] = "0x2"
        entry["affidavit_hash"] = "sha256:abc"
        # Missing family_consent_video_hash
        errors = validate_structure(_minimal_valid_data([entry]))
        assert any("family_consent_video_hash" in e for e in errors)

    def test_valid_blood_succession(self) -> None:
        entry = _minimal_valid_entry()
        entry["action_type"] = "blood_succession"
        entry["successor_wallet"] = "0x2"
        entry["affidavit_hash"] = "sha256:abc"
        entry["family_consent_video_hash"] = "sha256:def"
        errors = validate_structure(_minimal_valid_data([entry]))
        assert errors == []

    def test_community_url_mismatch_flagged(self) -> None:
        entry = _minimal_valid_entry()
        entry["community_url"] = "https://x.com/i/communities/WRONG"
        errors = validate_structure(_minimal_valid_data([entry]))
        assert any("mismatch" in e.lower() for e in errors)

    def test_entry_number_gap_flagged(self) -> None:
        e1 = _minimal_valid_entry(1)
        e3 = _minimal_valid_entry(3)  # gap: 2 is missing
        errors = validate_structure(_minimal_valid_data([e1, e3]))
        assert any("gap" in e.lower() for e in errors)


# ── validate_no_regressions ───────────────────────────────────────────────────

class TestValidateNoRegressions:
    def test_no_changes_ok(self) -> None:
        e = _minimal_valid_entry()
        errors = validate_no_regressions([e], [e])
        assert errors == []

    def test_deletion_detected(self) -> None:
        e = _minimal_valid_entry(1)
        errors = validate_no_regressions([e], [])
        assert any("DELETED" in err for err in errors)

    def test_mutation_detected(self) -> None:
        orig = _minimal_valid_entry(1)
        mutated = dict(orig)
        mutated["description"] = "TAMPERED"
        errors = validate_no_regressions([orig], [mutated])
        assert any("MODIFIED" in err for err in errors)

    def test_tweet_id_change_not_flagged(self) -> None:
        orig = _minimal_valid_entry(1)
        updated = dict(orig)
        updated["x_tweet_id"] = "9999999"
        errors = validate_no_regressions([orig], [updated])
        assert errors == []


# ── entry_fingerprint ─────────────────────────────────────────────────────────

class TestEntryFingerprint:
    def test_same_entry_same_fingerprint(self) -> None:
        e = _minimal_valid_entry()
        assert entry_fingerprint(e) == entry_fingerprint(e)

    def test_different_description_different_fingerprint(self) -> None:
        e1 = _minimal_valid_entry()
        e2 = dict(e1)
        e2["description"] = "different"
        assert entry_fingerprint(e1) != entry_fingerprint(e2)

    def test_tweet_id_excluded_from_fingerprint(self) -> None:
        e1 = _minimal_valid_entry()
        e2 = dict(e1)
        e2["x_tweet_id"] = "new_tweet"
        assert entry_fingerprint(e1) == entry_fingerprint(e2)


# ── main / CLI ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_valid_file_returns_0(self, tmp_path: Path) -> None:
        p = tmp_path / "log.yaml"
        data = _minimal_valid_data([_minimal_valid_entry()])
        _write_yaml(p, data)
        assert validate_main(p) == 0

    def test_missing_file_returns_1(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.yaml"
        assert validate_main(p) == 1

    def test_invalid_file_returns_1(self, tmp_path: Path) -> None:
        p = tmp_path / "log.yaml"
        data = _minimal_valid_data()
        del data["metadata"]
        _write_yaml(p, data)
        assert validate_main(p) == 1
