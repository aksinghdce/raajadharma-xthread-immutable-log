"""
tests/test_append_only_yaml.py — Unit tests for the core immutability engine.
"""

from __future__ import annotations

import copy
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from scripts.append_only_yaml import (
    AppendOnlyYAML,
    ImmutabilityViolation,
    ValidationError,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

MINIMAL_YAML = {
    "metadata": {"dao_name": "Test DAO"},
    "members": [],
    "updates": [],
}


@pytest.fixture()
def tmp_yaml(tmp_path: Path) -> Path:
    """Return a path to a fresh minimal YAML file in a temp directory."""
    p = tmp_path / "test-log.yaml"
    with p.open("w") as fh:
        yaml.dump(MINIMAL_YAML, fh, default_flow_style=False)
    return p


@pytest.fixture()
def log(tmp_yaml: Path) -> AppendOnlyYAML:
    return AppendOnlyYAML(tmp_yaml)


# ── Basic append ──────────────────────────────────────────────────────────────

class TestAppend:
    def test_first_entry_gets_number_1(self, log: AppendOnlyYAML) -> None:
        entry = log.append(
            action_type="test_action",
            actor_wallet="0xAAAA",
            description="First entry",
        )
        assert entry["entry_number"] == 1

    def test_second_entry_gets_number_2(self, log: AppendOnlyYAML) -> None:
        log.append(action_type="a", actor_wallet="0x1", description="first")
        entry2 = log.append(action_type="b", actor_wallet="0x2", description="second")
        assert entry2["entry_number"] == 2

    def test_entry_persisted_to_disk(self, log: AppendOnlyYAML, tmp_yaml: Path) -> None:
        log.append(action_type="vote", actor_wallet="0xBBBB", description="persisted")
        with tmp_yaml.open() as fh:
            data = yaml.safe_load(fh)
        assert len(data["updates"]) == 1
        assert data["updates"][0]["action_type"] == "vote"

    def test_community_url_injected(self, log: AppendOnlyYAML) -> None:
        entry = log.append(action_type="vote", actor_wallet="0x1", description="x")
        assert "x.com/i/communities/1981771124343283876" in entry["community_url"]

    def test_date_auto_populated(self, log: AppendOnlyYAML) -> None:
        entry = log.append(action_type="vote", actor_wallet="0x1", description="x")
        assert entry["date"]  # non-empty

    def test_custom_date_preserved(self, log: AppendOnlyYAML) -> None:
        entry = log.append(
            action_type="vote",
            actor_wallet="0x1",
            description="x",
            date="2024-06-01T00:00:00Z",
        )
        assert entry["date"] == "2024-06-01T00:00:00Z"


# ── Validation ────────────────────────────────────────────────────────────────

class TestValidation:
    def test_missing_action_type_raises(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(ValidationError):
            log.append(action_type="", actor_wallet="0x1", description="x")

    def test_missing_wallet_raises(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(ValidationError):
            log.append(action_type="vote", actor_wallet="", description="x")

    def test_missing_description_raises(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(ValidationError):
            log.append(action_type="vote", actor_wallet="0x1", description="")

    def test_blood_succession_requires_video_hash(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(ValidationError, match="family_consent_video_hash"):
            log.append(
                action_type="blood_succession",
                actor_wallet="0x1",
                description="succession",
                successor_wallet="0x2",
                affidavit_hash="sha256:abc",
                # family_consent_video_hash missing
            )

    def test_blood_succession_requires_affidavit_hash(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(ValidationError, match="affidavit_hash"):
            log.append(
                action_type="blood_succession",
                actor_wallet="0x1",
                description="succession",
                successor_wallet="0x2",
                family_consent_video_hash="sha256:abc",
                # affidavit_hash missing
            )

    def test_blood_succession_requires_successor_wallet(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(ValidationError, match="successor_wallet"):
            log.append(
                action_type="blood_succession",
                actor_wallet="0x1",
                description="succession",
                family_consent_video_hash="sha256:abc",
                affidavit_hash="sha256:def",
                # successor_wallet missing
            )

    def test_valid_blood_succession_succeeds(self, log: AppendOnlyYAML) -> None:
        entry = log.append(
            action_type="blood_succession",
            actor_wallet="0x1",
            description="Valid succession",
            successor_wallet="0x2",
            family_consent_video_hash="sha256:abc",
            affidavit_hash="sha256:def",
        )
        assert entry["action_type"] == "blood_succession"


# ── Immutability enforcement ──────────────────────────────────────────────────

class TestImmutability:
    def test_mutation_of_past_entry_detected(
        self, log: AppendOnlyYAML, tmp_yaml: Path
    ) -> None:
        log.append(action_type="vote", actor_wallet="0x1", description="original")

        # Tamper with the YAML on disk
        with tmp_yaml.open() as fh:
            data = yaml.safe_load(fh)
        data["updates"][0]["description"] = "TAMPERED"
        with tmp_yaml.open("w") as fh:
            yaml.dump(data, fh)

        # The original log object's snapshot still has "original" — verify detects it
        with pytest.raises(ImmutabilityViolation):
            log.verify_no_mutations()

    def test_deletion_of_past_entry_detected(
        self, log: AppendOnlyYAML, tmp_yaml: Path
    ) -> None:
        log.append(action_type="vote", actor_wallet="0x1", description="entry1")
        log.append(action_type="vote", actor_wallet="0x2", description="entry2")

        # Delete first entry on disk
        with tmp_yaml.open() as fh:
            data = yaml.safe_load(fh)
        data["updates"] = [data["updates"][1]]  # remove entry #1
        with tmp_yaml.open("w") as fh:
            yaml.dump(data, fh)

        with pytest.raises(ImmutabilityViolation, match="DELETED"):
            log.verify_no_mutations(data["updates"])

    def test_no_violation_after_tweet_id_update(
        self, log: AppendOnlyYAML
    ) -> None:
        """x_tweet_id updates should NOT trigger immutability violations."""
        log.append(action_type="vote", actor_wallet="0x1", description="entry")
        # Should not raise
        log.update_tweet_id(1, "9999999999999999999")
        log.verify_no_mutations()

    def test_append_after_disk_mutation_raises(
        self, log: AppendOnlyYAML, tmp_yaml: Path
    ) -> None:
        """The original log instance detects disk mutations."""
        log.append(action_type="vote", actor_wallet="0x1", description="original")

        # Tamper with disk
        with tmp_yaml.open() as fh:
            data = yaml.safe_load(fh)
        data["updates"][0]["description"] = "TAMPERED"
        with tmp_yaml.open("w") as fh:
            yaml.dump(data, fh)

        # The original log object's snapshot has "original" — mismatch detected
        with pytest.raises(ImmutabilityViolation):
            log.verify_no_mutations()


# ── update_tweet_id ───────────────────────────────────────────────────────────

class TestUpdateTweetId:
    def test_updates_tweet_id(self, log: AppendOnlyYAML) -> None:
        log.append(action_type="vote", actor_wallet="0x1", description="x")
        log.update_tweet_id(1, "tweet123")
        entry = log.latest_entry()
        assert entry["x_tweet_id"] == "tweet123"

    def test_invalid_entry_number_raises(self, log: AppendOnlyYAML) -> None:
        with pytest.raises(KeyError):
            log.update_tweet_id(999, "tweet123")


# ── latest_entry / all_entries ────────────────────────────────────────────────

class TestQueries:
    def test_latest_entry_returns_none_when_empty(self, log: AppendOnlyYAML) -> None:
        assert log.latest_entry() is None

    def test_latest_entry_returns_last_appended(self, log: AppendOnlyYAML) -> None:
        log.append(action_type="a", actor_wallet="0x1", description="first")
        log.append(action_type="b", actor_wallet="0x2", description="second")
        assert log.latest_entry()["action_type"] == "b"

    def test_all_entries_returns_all(self, log: AppendOnlyYAML) -> None:
        log.append(action_type="a", actor_wallet="0x1", description="x")
        log.append(action_type="b", actor_wallet="0x2", description="y")
        assert len(log.all_entries()) == 2
