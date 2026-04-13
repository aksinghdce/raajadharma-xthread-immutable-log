"""
app.py — FastAPI backend for the RaajaDharma student portal.

This server runs on raajadharma.org and exposes a REST API that allows
student groups (2–9 members per group) to record:
  - Archery practice sessions (score, distance, form notes)
  - Spoken Sanskrit recitations (duration, recitation hash, accuracy)

Every record is appended to the group's own fork of the immutable
raajadharma-xthread-immutable-log repository.  The append-only rule is
enforced by AppendOnlyYAML — no update or delete endpoints exist.

─── API endpoints ─────────────────────────────────────────────────────────
  POST   /groups                             Create a new student group
  GET    /groups                             List all groups
  GET    /groups/{group_id}                  Get group details
  DELETE /groups/{group_id}                  Remove a group (admin only)

  GET    /groups/{group_id}/log              List all log entries
  GET    /groups/{group_id}/log/latest       Get the latest log entry
  POST   /groups/{group_id}/log/archery      Record an archery practice
  POST   /groups/{group_id}/log/sanskrit     Record a Sanskrit recitation
  POST   /groups/{group_id}/log/custom       Append a custom entry
  GET    /groups/{group_id}/validate         Validate the group's log

  GET    /health                             Health check

─── Running ───────────────────────────────────────────────────────────────
  pip install -r requirements.txt
  uvicorn app:app --host 0.0.0.0 --port 8000 --reload

  # Point to a local directory for testing (skips git clone):
  RAAJADHARMA_GROUPS_ROOT=/tmp/test-groups uvicorn app:app --reload
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ── Make the shared scripts importable ────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from examples.integration.backend.group_manager import GroupManager  # noqa: E402

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RaajaDharma Student Portal API",
    description=(
        "Immutable practice-record ledger for archery and spoken Sanskrit student groups.\n\n"
        "Community thread: https://x.com/i/communities/1981771124343283876"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

_manager: "GroupManager | None" = None


def _get_manager() -> GroupManager:
    """Lazy singleton — created on first request; can be replaced in tests."""
    global _manager
    if _manager is None:
        _manager = GroupManager()
    return _manager


# ── Request / Response models ──────────────────────────────────────────────────

class MemberIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    wallet: str = Field("", description="Ethereum wallet address (optional)")


class CreateGroupRequest(BaseModel):
    group_id: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9\-]+$")
    group_name: str = Field(..., min_length=2, max_length=100)
    members: list[MemberIn] = Field(..., min_length=2, max_length=9)
    discipline: Literal["archery", "sanskrit", "both"] = "archery"

    @field_validator("members")
    @classmethod
    def check_member_count(cls, v: list) -> list:
        if not (2 <= len(v) <= 9):
            raise ValueError("Group must have between 2 and 9 members.")
        return v


class ArcheryPracticeRequest(BaseModel):
    actor_wallet: str = Field(..., description="Wallet address of the recording member")
    description: str = Field(..., min_length=5, description="Summary of the session")
    score: Optional[int] = Field(None, ge=0, le=300, description="Score out of 300")
    distance_m: Optional[int] = Field(None, ge=1, le=100, description="Target distance in metres")
    arrow_count: Optional[int] = Field(None, ge=1, description="Number of arrows shot")
    form_notes: Optional[str] = Field(None, description="Coach's form observation notes")
    media_hashes: list[str] = Field(default_factory=list)


class SanskritRecitationRequest(BaseModel):
    actor_wallet: str = Field(..., description="Wallet address of the recording member")
    description: str = Field(..., min_length=5, description="What was recited")
    text_reference: Optional[str] = Field(None, description="Name of the text / shloka reference")
    recitation_hash: Optional[str] = Field(
        None, description="SHA-256 of the audio recording file"
    )
    duration_seconds: Optional[int] = Field(None, ge=1)
    accuracy_pct: Optional[int] = Field(None, ge=0, le=100, description="Assessed accuracy %")
    media_hashes: list[str] = Field(default_factory=list)


class CustomEntryRequest(BaseModel):
    actor_wallet: str
    action_type: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=5)
    extra: dict[str, Any] = Field(default_factory=dict)
    media_hashes: list[str] = Field(default_factory=list)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "raajadharma-student-portal"}


# ── Group management ──────────────────────────────────────────────────────────

@app.post("/groups", status_code=status.HTTP_201_CREATED, tags=["groups"])
def create_group(req: CreateGroupRequest) -> dict:
    """
    Provision a new student group.  This clones the template repository into
    a dedicated working copy on the raajadharma.org backend server.
    """
    try:
        manifest = _get_manager().create_group(
            group_id=req.group_id,
            group_name=req.group_name,
            members=[m.model_dump() for m in req.members],
            discipline=req.discipline,
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return manifest


@app.get("/groups", tags=["groups"])
def list_groups() -> list[dict]:
    """List all provisioned student groups."""
    return _get_manager().list_groups()


@app.get("/groups/{group_id}", tags=["groups"])
def get_group(group_id: str) -> dict:
    """Get details for a specific group."""
    try:
        return _get_manager().get_group(group_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/groups/{group_id}", tags=["groups"])
def delete_group(group_id: str) -> dict:
    """Remove a group's working copy (admin / reset only)."""
    try:
        _get_manager().delete_group(group_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": group_id}


# ── Log read endpoints ────────────────────────────────────────────────────────

@app.get("/groups/{group_id}/log", tags=["log"])
def get_log(group_id: str) -> list[dict]:
    """Return all immutable log entries for a group."""
    try:
        return _get_manager().get_entries(group_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/groups/{group_id}/log/latest", tags=["log"])
def get_latest(group_id: str) -> dict:
    """Return the most recent log entry."""
    try:
        entry = _get_manager().get_latest_entry(group_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if entry is None:
        raise HTTPException(status_code=404, detail="No entries yet.")
    return entry


@app.get("/groups/{group_id}/validate", tags=["log"])
def validate_log(group_id: str) -> dict:
    """Validate the group's YAML log for immutability and structural errors."""
    try:
        ok = _get_manager().validate_group_log(group_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"valid": ok, "group_id": group_id}


# ── Log write endpoints ───────────────────────────────────────────────────────

@app.post("/groups/{group_id}/log/archery", status_code=status.HTTP_201_CREATED, tags=["log"])
def record_archery(group_id: str, req: ArcheryPracticeRequest) -> dict:
    """
    Record an archery practice session for a student group.

    This is an **immutable append** — the entry cannot be edited or deleted
    once written.  It is permanently committed to the group's git log.

    Example session data that gets recorded:
    ```json
    {
      "actor_wallet": "0xABC...",
      "description": "Monday warm-up — 30 arrows at 18m",
      "score": 252,
      "distance_m": 18,
      "arrow_count": 30,
      "form_notes": "Release tension improved; elbow flare persists"
    }
    ```
    """
    extra: dict[str, Any] = {}
    if req.score is not None:
        extra["score"] = req.score
    if req.distance_m is not None:
        extra["distance_m"] = req.distance_m
    if req.arrow_count is not None:
        extra["arrow_count"] = req.arrow_count
    if req.form_notes:
        extra["form_notes"] = req.form_notes

    return _append(group_id, req.actor_wallet, "archery_practice", req.description, req.media_hashes, extra)


@app.post("/groups/{group_id}/log/sanskrit", status_code=status.HTTP_201_CREATED, tags=["log"])
def record_sanskrit(group_id: str, req: SanskritRecitationRequest) -> dict:
    """
    Record a spoken Sanskrit recitation for a student group.

    The audio file should be hashed (sha256) on the client before submission;
    only the hash is stored in the public ledger for privacy.

    Example:
    ```json
    {
      "actor_wallet": "0xDEF...",
      "description": "Gayatri Mantra recitation — 3 rounds",
      "text_reference": "Rigveda 3.62.10",
      "recitation_hash": "sha256:abc123...",
      "duration_seconds": 87,
      "accuracy_pct": 92
    }
    ```
    """
    extra: dict[str, Any] = {}
    if req.text_reference:
        extra["text_reference"] = req.text_reference
    if req.recitation_hash:
        extra["recitation_hash"] = req.recitation_hash
    if req.duration_seconds is not None:
        extra["duration_seconds"] = req.duration_seconds
    if req.accuracy_pct is not None:
        extra["accuracy_pct"] = req.accuracy_pct

    return _append(group_id, req.actor_wallet, "sanskrit_recitation", req.description, req.media_hashes, extra)


@app.post("/groups/{group_id}/log/custom", status_code=status.HTTP_201_CREATED, tags=["log"])
def record_custom(group_id: str, req: CustomEntryRequest) -> dict:
    """Append a free-form custom entry (governance votes, milestones, etc.)."""
    return _append(group_id, req.actor_wallet, req.action_type, req.description, req.media_hashes, req.extra)


# ── Internal helper ────────────────────────────────────────────────────────────

def _append(
    group_id: str,
    actor_wallet: str,
    action_type: str,
    description: str,
    media_hashes: list[str],
    extra: dict,
) -> dict:
    try:
        return _get_manager().append_entry(
            group_id,
            {
                "action_type": action_type,
                "actor_wallet": actor_wallet,
                "description": description,
                "media_hashes": media_hashes,
                **extra,
            },
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
