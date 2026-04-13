"""
group_manager.py — Per-student-group repository clone manager.

Each student group (2–9 members) gets its own working copy of the
raajadharma-xthread-immutable-log repo, stored on the raajadharma.org
backend server under:

    /var/raajadharma/groups/<group_id>/raajadharma-xthread-immutable-log/

The manager handles:
  - Provisioning a fresh clone for a new group
  - Pulling the latest state before each read/write
  - Delegating all immutability-enforced writes to AppendOnlyYAML
  - Enforcing group-size constraints (2 ≤ members ≤ 9)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# ── Absolute path configuration ───────────────────────────────────────────────

# Root directory where all group working copies live on the server
GROUPS_ROOT = Path(os.getenv("RAAJADHARMA_GROUPS_ROOT", "/var/raajadharma/groups"))

# The canonical upstream template repository
TEMPLATE_REPO_URL = os.getenv(
    "RAAJADHARMA_TEMPLATE_REPO",
    "https://github.com/aksinghdce/raajadharma-xthread-immutable-log.git",
)

# Absolute path to the *installed* scripts package (same server, shipped as part
# of the raajadharma-xthread-immutable-log deployment)
SCRIPTS_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT.parent))  # make `scripts` importable

from scripts.append_only_yaml import AppendOnlyYAML  # noqa: E402
from scripts.validate_yaml import main as run_validate  # noqa: E402

MIN_GROUP_SIZE = 2
MAX_GROUP_SIZE = 9

# ── Group manifest ─────────────────────────────────────────────────────────────

MANIFEST_FILENAME = "group_manifest.json"


def _manifest_path(group_dir: Path) -> Path:
    return group_dir / MANIFEST_FILENAME


def _load_manifest(group_dir: Path) -> dict:
    p = _manifest_path(group_dir)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_manifest(group_dir: Path, manifest: dict) -> None:
    _manifest_path(group_dir).write_text(json.dumps(manifest, indent=2))


# ── Public API ─────────────────────────────────────────────────────────────────

class GroupManager:
    """Manages per-group repository clones for the raajadharma.org student portal."""

    def __init__(self, groups_root: Path = GROUPS_ROOT) -> None:
        self.groups_root = groups_root
        self.groups_root.mkdir(parents=True, exist_ok=True)

    # ── Group lifecycle ────────────────────────────────────────────────────

    def create_group(
        self,
        group_id: str,
        group_name: str,
        members: list[dict],
        discipline: str = "archery",
    ) -> dict:
        """
        Provision a new group working copy.

        Parameters
        ----------
        group_id    : Unique identifier (e.g. "group-2024-01").
        group_name  : Human-readable name.
        members     : List of member dicts (each must have 'name' and 'wallet').
                      Length must be between MIN_GROUP_SIZE and MAX_GROUP_SIZE.
        discipline  : 'archery' | 'sanskrit' | 'both'

        Returns
        -------
        The group manifest dict.
        """
        if not (MIN_GROUP_SIZE <= len(members) <= MAX_GROUP_SIZE):
            raise ValueError(
                f"Group must have between {MIN_GROUP_SIZE} and {MAX_GROUP_SIZE} members "
                f"(got {len(members)})."
            )

        group_dir = self._group_dir(group_id)
        if group_dir.exists():
            raise FileExistsError(f"Group '{group_id}' already exists.")

        group_dir.mkdir(parents=True)
        repo_dir = self._repo_dir(group_id)

        # Clone the template repo into the group's directory
        self._git(["clone", TEMPLATE_REPO_URL, str(repo_dir)])

        # Build a group-specific YAML with just these members
        self._initialize_group_yaml(repo_dir, group_id, group_name, members, discipline)

        manifest = {
            "group_id": group_id,
            "group_name": group_name,
            "discipline": discipline,
            "members": members,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "repo_dir": str(repo_dir),
        }
        _save_manifest(group_dir, manifest)
        return manifest

    def delete_group(self, group_id: str) -> None:
        """Remove a group's working copy (for cleanup/reset only)."""
        group_dir = self._group_dir(group_id)
        if not group_dir.exists():
            raise KeyError(f"Group '{group_id}' not found.")
        shutil.rmtree(group_dir)

    def get_group(self, group_id: str) -> dict:
        """Return the manifest for an existing group."""
        group_dir = self._group_dir(group_id)
        if not group_dir.exists():
            raise KeyError(f"Group '{group_id}' not found.")
        return _load_manifest(group_dir)

    def list_groups(self) -> list[dict]:
        """Return manifests for all provisioned groups."""
        result = []
        for p in sorted(self.groups_root.iterdir()):
            mp = _manifest_path(p)
            if mp.exists():
                result.append(json.loads(mp.read_text()))
        return result

    # ── Log operations ─────────────────────────────────────────────────────

    def append_entry(self, group_id: str, entry: dict) -> dict:
        """
        Append an entry to the group's immutable log.

        Parameters
        ----------
        group_id : The group identifier.
        entry    : Dict with at minimum: action_type, actor_wallet, description.
                   For 'archery_practice'  entries: optionally include score, distance_m.
                   For 'sanskrit_recitation' entries: optionally include recitation_hash,
                   duration_seconds.

        Returns
        -------
        The newly created entry dict.
        """
        self._pull(group_id)
        log = AppendOnlyYAML(self._yaml_path(group_id))
        created = log.append(**entry)
        self._commit_and_push(group_id, f"Entry #{created['entry_number']}: {entry['action_type']}")
        return created

    def get_entries(self, group_id: str) -> list[dict]:
        """Return all log entries for a group."""
        self._pull(group_id)
        log = AppendOnlyYAML(self._yaml_path(group_id))
        return log.all_entries()

    def get_latest_entry(self, group_id: str) -> dict | None:
        """Return the most recent log entry for a group."""
        self._pull(group_id)
        log = AppendOnlyYAML(self._yaml_path(group_id))
        return log.latest_entry()

    def validate_group_log(self, group_id: str) -> bool:
        """Validate the group's YAML for structural and immutability errors. Returns True if OK."""
        self._pull(group_id)
        return run_validate(self._yaml_path(group_id)) == 0

    # ── Internal helpers ───────────────────────────────────────────────────

    def _group_dir(self, group_id: str) -> Path:
        return self.groups_root / group_id

    def _repo_dir(self, group_id: str) -> Path:
        return self._group_dir(group_id) / "raajadharma-xthread-immutable-log"

    def _yaml_path(self, group_id: str) -> Path:
        return self._repo_dir(group_id) / "yaml" / "raajadharma-log.yaml"

    def _git(self, args: list[str], cwd: Path | None = None) -> str:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr}")
        return result.stdout.strip()

    def _pull(self, group_id: str) -> None:
        """Pull latest changes to keep the working copy up-to-date."""
        repo_dir = self._repo_dir(group_id)
        if not repo_dir.exists():
            raise KeyError(f"Group '{group_id}' repo not found.")
        try:
            self._git(["pull", "--ff-only"], cwd=repo_dir)
        except RuntimeError:
            pass  # Offline / no remote — continue with local copy

    def _commit_and_push(self, group_id: str, message: str) -> None:
        """Stage, commit, and push the updated YAML."""
        repo_dir = self._repo_dir(group_id)
        self._git(["add", "yaml/raajadharma-log.yaml"], cwd=repo_dir)
        self._git(
            ["commit", "--allow-empty", "-m", message],
            cwd=repo_dir,
        )
        try:
            self._git(["push"], cwd=repo_dir)
        except RuntimeError:
            pass  # Push is best-effort; local commit is always created

    def _initialize_group_yaml(
        self,
        repo_dir: Path,
        group_id: str,
        group_name: str,
        members: list[dict],
        discipline: str,
    ) -> None:
        """
        Overwrite the template YAML with a group-specific header and member list.
        """
        yaml_path = repo_dir / "yaml" / "raajadharma-log.yaml"
        group_members = []
        roles = ["Leader", "Co-Leader"] + ["Member"] * MAX_GROUP_SIZE
        for i, m in enumerate(members):
            group_members.append(
                {
                    "id": f"M{i + 1:03d}",
                    "name": m["name"],
                    "role": roles[i],
                    "wallet": m.get("wallet", f"0x{'0' * 39}{i + 1:x}"),
                    "discipline": discipline,
                    "joined_at": datetime.now(timezone.utc).isoformat(),
                    "active": True,
                }
            )

        data: dict[str, Any] = {
            "metadata": {
                "dao_name": group_name,
                "group_id": group_id,
                "discipline": discipline,
                "community_url": "https://x.com/i/communities/1981771124343283876",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0",
                "description": (
                    f"Append-only practice record ledger for {group_name}. "
                    f"Discipline: {discipline}."
                ),
            },
            "members": group_members,
            "updates": [],
        }

        with yaml_path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)
