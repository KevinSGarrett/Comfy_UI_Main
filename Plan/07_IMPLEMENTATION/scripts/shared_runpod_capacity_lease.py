#!/usr/bin/env python3
"""Validate the process-local shared RunPod lease before a GPU action."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

COORDINATOR = Path.home() / ".codex/shared_runpod_coordinator/coordinator_v2.py"


class SharedRunPodLeaseError(RuntimeError):
    """Raised when the cross-project capacity lease is absent or invalid."""


def validate_shared_runpod_lease(
    *, expected_profile: str | None = None
) -> dict[str, Any]:
    lease_id = os.environ.get("SHARED_RUNPOD_LEASE_ID", "").strip()
    token = os.environ.get("SHARED_RUNPOD_LEASE_TOKEN", "").strip()
    profile = os.environ.get("SHARED_RUNPOD_LEASE_PROFILE", "").strip()
    if not lease_id or not token or not profile:
        raise SharedRunPodLeaseError(
            "GPU action requires SHARED_RUNPOD_LEASE_ID, "
            "SHARED_RUNPOD_LEASE_TOKEN, and SHARED_RUNPOD_LEASE_PROFILE"
        )
    if expected_profile and profile != expected_profile:
        raise SharedRunPodLeaseError(
            f"lease profile mismatch: expected {expected_profile}, observed {profile}"
        )
    if not COORDINATOR.is_file():
        raise SharedRunPodLeaseError(f"shared coordinator is absent: {COORDINATOR}")
    completed = subprocess.run(
        [
            sys.executable,
            str(COORDINATOR),
            "validate",
            "--lease-id",
            lease_id,
            "--project",
            "comfyui_main",
            "--profile",
            profile,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "SHARED_RUNPOD_LEASE_TOKEN": token},
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:500]
        raise SharedRunPodLeaseError(f"shared RunPod lease validation failed: {detail}")
    try:
        receipt = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SharedRunPodLeaseError("coordinator returned invalid JSON") from exc
    if receipt.get("valid") is not True:
        raise SharedRunPodLeaseError("coordinator did not validate the lease")
    return {
        "lease_id": receipt["lease_id"],
        "project": receipt["project"],
        "profile": receipt["profile"],
        "lease_mode": receipt["lease_mode"],
        "reserved_peak_gb": receipt["reserved_peak_gb"],
        "expires_at": receipt["expires_at"],
        "token_retained": False,
    }
