#!/usr/bin/env python3
"""Offline reaffirmation validator for TRK-W64-023 Wan repair candidate (2026-07-20)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_WAN = (
    "wan2.2_ti2v_5B_fp16.safetensors",
    "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    "wan2.2_vae.safetensors",
)
CANDIDATE_REL = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "aws_gpu_workflow_smoke_20260715T115203-0500/images/"
    "12_w64_row023_wan22_rerun_seed2272301_00001_.mp4"
)
CANDIDATE_SHA = "29823555e23ac47d58fd83740952817c0b6ddf379523dc3b61f6e8088d34949a"
PROBE_REL = "runtime_artifacts/wave64_row023_local_reaffirm_20260720/offline_chroma_probe.json"
DELTA_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-023_WAN_REPAIR_CANDIDATE_REAFFIRM_CURRENT_DELTA_20260720.json"
)
LEDGER_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-019_023_CLASS_B_BLOCKER_LEDGER_20260720.json"
)
MIN_BLUE_DELTA = 5.0


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def validate(root: Path) -> dict[str, Any]:
    candidate = root / CANDIDATE_REL
    probe = root / PROBE_REL
    delta = root / DELTA_REL
    ledger = root / LEDGER_REL
    _require(candidate.is_file(), f"missing candidate: {candidate}")
    _require(_sha(candidate) == CANDIDATE_SHA, "candidate sha256 mismatch")
    _require(probe.is_file(), f"missing chroma probe: {probe}")
    _require(delta.is_file(), f"missing delta: {delta}")
    _require(ledger.is_file(), f"missing ledger: {ledger}")

    probe_data = _load(probe)
    delta_data = _load(delta)
    ledger_data = _load(ledger)

    _require(probe_data.get("decoded_frames") == 49, "decoded_frames must be 49")
    _require(probe_data.get("mp4_sha256") == CANDIDATE_SHA, "probe mp4 sha mismatch")
    blue_delta = float(probe_data.get("blue_excess_delta_end_minus_start") or 0.0)
    _require(blue_delta >= MIN_BLUE_DELTA, f"blue excess delta {blue_delta} below {MIN_BLUE_DELTA}")

    _require(delta_data.get("tracker_id") == "TRK-W64-023", "delta tracker mismatch")
    _require(delta_data.get("row_complete") is False, "row_complete must stay false")
    _require(delta_data.get("strict_qa", {}).get("visual_qa_pass_bounded") is False, "must not claim VISUAL_QA_PASS_BOUNDED")
    _require(
        "FRAME_REPAIR_VISUAL_ACCEPTANCE_FAILED" in delta_data.get("blocker_codes", []),
        "missing FRAME_REPAIR_VISUAL_ACCEPTANCE_FAILED",
    )
    _require(
        "LOCAL_WAN_MODEL_PAYLOAD_MISSING" in delta_data.get("blocker_codes", []),
        "missing LOCAL_WAN_MODEL_PAYLOAD_MISSING",
    )

    _require(ledger_data.get("classification") == "Class_B_Failed_runtime_visual_QA", "ledger class mismatch")
    _require(ledger_data.get("row_complete") is False, "ledger row_complete must be false")
    _require(ledger_data.get("csv_sync", "").startswith("deferred"), "csv must remain deferred")

    models_root = root / "models"
    present = []
    missing = []
    for name in REQUIRED_WAN:
        hits = list(models_root.rglob(name)) if models_root.is_dir() else []
        if hits:
            present.append(name)
        else:
            missing.append(name)
    _require(len(missing) == 3, f"expected all Wan payloads missing locally, found present={present}")

    return {
        "result": "pass_offline_reaffirm_hold",
        "candidate_sha256": CANDIDATE_SHA,
        "blue_excess_delta_end_minus_start": blue_delta,
        "missing_wan_assets": missing,
        "visual_qa_pass_bounded": False,
        "row_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[3]))
    args = parser.parse_args()
    report = validate(Path(args.project_root).resolve())
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
