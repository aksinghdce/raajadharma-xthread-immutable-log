"""
examples/example_usage.py — Working examples showing all major CLI features.

Run this file to see a complete demo of the append-only log in action:
    python examples/example_usage.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts.append_only_yaml import AppendOnlyYAML  # noqa: E402
from scripts.validate_yaml import main as validate_main  # noqa: E402

COMMUNITY_URL = "https://x.com/i/communities/1981771124343283876"

SAMPLE_YAML = {
    "metadata": {
        "dao_name": "RaajaDharma Archery Club DAO (Demo)",
        "community_url": COMMUNITY_URL,
    },
    "members": [
        {"id": "M001", "name": "Alice", "role": "Governor", "wallet": "0xAAAA", "blood_relation": "Head of Family"},
        {"id": "M002", "name": "Bob",   "role": "Coach",     "wallet": "0xBBBB", "blood_relation": "Eldest Child"},
    ],
    "updates": [],
}


def run_demo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "demo-log.yaml"
        with yaml_path.open("w") as fh:
            yaml.dump(SAMPLE_YAML, fh, default_flow_style=False)

        print("=" * 60)
        print("RaajaDharma Immutable Log — DEMO")
        print(f"Community: {COMMUNITY_URL}")
        print("=" * 60)

        log = AppendOnlyYAML(yaml_path)

        # Example 1: Append a governance vote
        print("\n📝 Example 1: Governance Vote")
        e1 = log.append(
            action_type="governance_vote",
            actor_wallet="0xAAAA",
            description="Approved new archery practice schedule: every Saturday 9am–12pm.",
            date="2024-03-01T10:00:00Z",
        )
        print(f"   Entry #{e1['entry_number']} appended ✅")

        # Example 2: Append a training milestone
        print("\n🏆 Example 2: Archery Milestone")
        e2 = log.append(
            action_type="archery_milestone",
            actor_wallet="0xBBBB",
            description="M002 (Bob) achieved regional Level 2 certification on 2024-03-15.",
            date="2024-03-15T14:00:00Z",
        )
        print(f"   Entry #{e2['entry_number']} appended ✅")

        # Example 3: Blood succession
        print("\n🔑 Example 3: Blood Succession Transfer")
        e3 = log.append(
            action_type="blood_succession",
            actor_wallet="0xAAAA",
            description="Governor role transferred from Alice (M001) to Bob (M002, Eldest Child).",
            date="2024-06-01T00:00:00Z",
            successor_wallet="0xBBBB",
            successor_member_id="M002",
            family_consent_video_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            affidavit_hash="sha256:abc123def456abc123def456abc123def456abc123def456abc123def456abc123",
            witnesses=[
                {"member_id": "M003", "wallet": "0xCCCC"},
                {"member_id": "M004", "wallet": "0xDDDD"},
            ],
        )
        print(f"   Entry #{e3['entry_number']} appended ✅")

        # Example 4: Link a tweet ID (after manual posting)
        print("\n🐦 Example 4: Link Tweet ID")
        log.update_tweet_id(1, "1234567890123456789")
        print("   Tweet ID linked to Entry #1 ✅")

        # Example 5: Validate
        print("\n🔍 Example 5: Validate Log")
        result = validate_main(yaml_path)
        print(f"   Validation result: {'PASSED ✅' if result == 0 else 'FAILED ❌'}")

        # Show the full log
        print("\n📋 Full Log:")
        print("-" * 60)
        for entry in log.all_entries():
            print(f"  #{entry['entry_number']} — {entry['action_type']} — {entry['date']}")
            print(f"        {entry['description'][:80].strip()}...")
            if entry.get("x_tweet_id"):
                print(f"        🐦 Tweet: {entry['x_tweet_id']}")
        print("-" * 60)

        # Generate diff text for one entry
        print("\n📄 YAML Diff for Entry #3 (Blood Succession):")
        diff = log.generate_diff_text(e3)
        print(diff)

        print(f"\n✅  Demo complete. Community thread: {COMMUNITY_URL}")


if __name__ == "__main__":
    run_demo()
