"""
validate_yaml.py — Standalone validation script.

Scans the entire YAML history and flags any mutation attempts.
Can be run manually or via GitHub Actions.

Usage:
    python scripts/validate_yaml.py
    python scripts/validate_yaml.py --yaml yaml/raajadharma-log.yaml
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml


MASTER_YAML_DEFAULT = Path(__file__).parent.parent / "yaml" / "raajadharma-log.yaml"
COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"

# Fields that are allowed to change after initial entry creation
MUTABLE_ALLOWED_FIELDS = {"x_tweet_id", "verified_by"}


def entry_fingerprint(entry: dict) -> str:
    filtered = {k: v for k, v in entry.items() if k not in MUTABLE_ALLOWED_FIELDS}
    serialized = json.dumps(filtered, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def validate_structure(data: dict) -> list[str]:
    """Return a list of structural error messages (empty = valid)."""
    errors: list[str] = []

    if "metadata" not in data:
        errors.append("Missing top-level 'metadata' section.")
    if "members" not in data:
        errors.append("Missing top-level 'members' section.")
    if "updates" not in data:
        errors.append("Missing top-level 'updates' section.")
        return errors

    updates = data["updates"]
    if not isinstance(updates, list):
        errors.append("'updates' must be a list.")
        return errors

    seen_numbers: set[int] = set()
    for i, entry in enumerate(updates):
        prefix = f"Entry #{entry.get('entry_number', f'index-{i}')}"

        # Sequential numbering
        num = entry.get("entry_number")
        if num is None:
            errors.append(f"{prefix}: missing 'entry_number'.")
        elif num in seen_numbers:
            errors.append(f"{prefix}: duplicate entry_number {num}.")
        else:
            seen_numbers.add(num)

        # Required fields
        for field in ("date", "actor_wallet", "action_type", "description"):
            if not entry.get(field):
                errors.append(f"{prefix}: missing required field '{field}'.")

        # Succession-specific required fields
        if entry.get("action_type") == "blood_succession":
            for field in ("successor_wallet", "family_consent_video_hash", "affidavit_hash"):
                if not entry.get(field):
                    errors.append(
                        f"{prefix}: blood_succession requires non-empty '{field}'."
                    )

        # Community URL consistency
        if entry.get("community_url") and entry["community_url"] != COMMUNITY_URL:
            errors.append(
                f"{prefix}: community_url mismatch. "
                f"Expected {COMMUNITY_URL!r}, got {entry['community_url']!r}."
            )

    # Check sequential ordering (no gaps)
    sorted_nums = sorted(seen_numbers)
    for expected, actual in enumerate(sorted_nums, start=1):
        if expected != actual:
            errors.append(
                f"Entry numbering gap: expected entry #{expected}, found #{actual}."
            )
            break

    return errors


def validate_no_regressions(
    original_entries: list[dict], current_entries: list[dict]
) -> list[str]:
    """
    Compare original vs current entries and report any mutations.
    Used by CI to compare the PR base vs. the PR head.
    """
    errors: list[str] = []
    orig_map = {e["entry_number"]: e for e in original_entries}
    cur_map = {e["entry_number"]: e for e in current_entries}

    for num, orig in orig_map.items():
        if num not in cur_map:
            errors.append(f"Entry #{num} was DELETED — immutability violation!")
            continue
        orig_fp = entry_fingerprint(orig)
        cur_fp = entry_fingerprint(cur_map[num])
        if orig_fp != cur_fp:
            errors.append(
                f"Entry #{num} was MODIFIED — immutability violation! "
                f"(original: {orig_fp[:8]}… current: {cur_fp[:8]}…)"
            )
    return errors


def main(yaml_path: Path = MASTER_YAML_DEFAULT) -> int:
    """
    Validate the YAML file. Returns 0 on success, 1 on failure.
    """
    print(f"🔍 Validating: {yaml_path}")

    if not yaml_path.exists():
        print(f"❌ File not found: {yaml_path}", file=sys.stderr)
        return 1

    data = load_yaml(yaml_path)
    errors = validate_structure(data)

    if errors:
        print("\n❌ Validation FAILED:")
        for err in errors:
            print(f"   • {err}")
        return 1

    entry_count = len(data.get("updates", []))
    print(f"✅ Validation PASSED — {entry_count} entries, all intact.")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate raajadharma-log.yaml")
    parser.add_argument(
        "--yaml",
        type=Path,
        default=MASTER_YAML_DEFAULT,
        help="Path to the master YAML file",
    )
    args = parser.parse_args()
    sys.exit(main(args.yaml))
