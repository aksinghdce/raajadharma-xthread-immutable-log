"""
append_only_yaml.py — Core immutability engine for the RaajaDharma append-only YAML ledger.

Rules enforced:
  1. Past entries (by entry_number) are NEVER modified or deleted.
  2. Every new entry gets the next sequential entry_number.
  3. Blood-succession entries require: family_consent_video_hash, affidavit_hash,
     successor_wallet (all non-empty).
  4. All entries receive a UTC timestamp automatically if not supplied.

Usage (as a library):
    from scripts.append_only_yaml import AppendOnlyYAML
    log = AppendOnlyYAML("yaml/raajadharma-log.yaml")
    log.append(action_type="governance_vote", actor_wallet="0x...", description="...")
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


MASTER_YAML_DEFAULT = Path(__file__).parent.parent / "yaml" / "raajadharma-log.yaml"
COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"

REQUIRED_SUCCESSION_FIELDS = [
    "successor_wallet",
    "family_consent_video_hash",
    "affidavit_hash",
]


class ImmutabilityViolation(Exception):
    """Raised when a mutation of a past entry is detected."""


class ValidationError(Exception):
    """Raised when a new entry fails validation."""


class AppendOnlyYAML:
    """Load, validate, and append to the master YAML ledger."""

    def __init__(self, yaml_path: str | Path = MASTER_YAML_DEFAULT) -> None:
        self.yaml_path = Path(yaml_path)
        self._data: dict[str, Any] = {}
        self._original_entries_snapshot: list[dict] = []
        self._load()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"Master YAML not found: {self.yaml_path}")
        with self.yaml_path.open("r", encoding="utf-8") as fh:
            self._data = yaml.safe_load(fh) or {}
        if "updates" not in self._data:
            self._data["updates"] = []
        # Deep-copy existing entries for mutation checking
        self._original_entries_snapshot = copy.deepcopy(self._data["updates"])

    # ── Immutability checking ──────────────────────────────────────────────

    def _entry_fingerprint(self, entry: dict) -> str:
        """Stable SHA-256 fingerprint of an entry (excluding x_tweet_id which is filled later)."""
        mutable_allowed = {"x_tweet_id", "verified_by"}
        filtered = {k: v for k, v in entry.items() if k not in mutable_allowed}
        serialized = json.dumps(filtered, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def verify_no_mutations(self, current_entries: list[dict] | None = None) -> None:
        """
        Compare current on-disk entries against the snapshot taken at load time.
        Raises ImmutabilityViolation if any past entry was altered or removed.
        """
        if current_entries is None:
            # Re-read from disk
            with self.yaml_path.open("r", encoding="utf-8") as fh:
                on_disk = yaml.safe_load(fh) or {}
            current_entries = on_disk.get("updates", [])

        original_numbers = {e["entry_number"] for e in self._original_entries_snapshot}

        for orig in self._original_entries_snapshot:
            num = orig["entry_number"]
            # Find the matching entry in current_entries
            matches = [e for e in current_entries if e.get("entry_number") == num]
            if not matches:
                raise ImmutabilityViolation(
                    f"Entry #{num} was DELETED — immutability violation!"
                )
            current = matches[0]
            orig_fp = self._entry_fingerprint(orig)
            cur_fp = self._entry_fingerprint(current)
            if orig_fp != cur_fp:
                raise ImmutabilityViolation(
                    f"Entry #{num} was MODIFIED — immutability violation!\n"
                    f"  Original fingerprint : {orig_fp}\n"
                    f"  Current fingerprint  : {cur_fp}"
                )

    # ── Validation ─────────────────────────────────────────────────────────

    def _validate_new_entry(self, entry: dict) -> None:
        required = ["action_type", "actor_wallet", "description"]
        for field in required:
            if not entry.get(field):
                raise ValidationError(f"Missing required field: '{field}'")

        if entry.get("action_type") == "blood_succession":
            for field in REQUIRED_SUCCESSION_FIELDS:
                if not entry.get(field):
                    raise ValidationError(
                        f"Blood-succession entries require '{field}' (non-empty)."
                    )

    # ── Append ─────────────────────────────────────────────────────────────

    def append(
        self,
        action_type: str,
        actor_wallet: str,
        description: str,
        date: str | None = None,
        media_hashes: list[str] | None = None,
        ipfs_hashes: list[str] | None = None,
        x_tweet_id: str = "",
        **extra_fields: Any,
    ) -> dict:
        """
        Append a new immutable entry to the ledger and save it to disk.

        Returns the newly created entry dict.
        """
        # Verify existing entries have not been tampered with
        self.verify_no_mutations()

        new_entry: dict[str, Any] = {
            "entry_number": self._next_entry_number(),
            "date": date or datetime.now(timezone.utc).isoformat(),
            "actor_wallet": actor_wallet,
            "action_type": action_type,
            "description": description,
            "media_hashes": media_hashes or [],
            "ipfs_hashes": ipfs_hashes or [],
            "x_tweet_id": x_tweet_id,
            "community_url": COMMUNITY_URL,
            "verified_by": [],
        }
        new_entry.update(extra_fields)

        self._validate_new_entry(new_entry)

        self._data["updates"].append(new_entry)
        self._save()
        # Update snapshot so subsequent calls within the same session are consistent
        self._original_entries_snapshot = copy.deepcopy(self._data["updates"])
        return new_entry

    def update_tweet_id(self, entry_number: int, tweet_id: str) -> None:
        """
        Fill in the x_tweet_id for an existing entry after it has been posted.
        This is the ONLY allowed post-creation mutation (tweet IDs are unknown at
        append time).
        """
        for entry in self._data["updates"]:
            if entry["entry_number"] == entry_number:
                entry["x_tweet_id"] = tweet_id
                self._save()
                # Sync snapshot — tweet_id is excluded from fingerprinting
                self._original_entries_snapshot = copy.deepcopy(self._data["updates"])
                return
        raise KeyError(f"No entry with entry_number={entry_number}")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _next_entry_number(self) -> int:
        if not self._data["updates"]:
            return 1
        return max(e["entry_number"] for e in self._data["updates"]) + 1

    def latest_entry(self) -> dict | None:
        if not self._data["updates"]:
            return None
        return self._data["updates"][-1]

    def all_entries(self) -> list[dict]:
        return list(self._data["updates"])

    def _save(self) -> None:
        """Persist the current in-memory state back to disk (YAML)."""
        with self.yaml_path.open("w", encoding="utf-8") as fh:
            yaml.dump(
                self._data,
                fh,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    # ── Diff ───────────────────────────────────────────────────────────────

    def generate_diff_text(self, entry: dict) -> str:
        """Return a human-readable YAML snippet for a single entry (suitable for tweeting)."""
        return yaml.dump(
            {"update": entry},
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
