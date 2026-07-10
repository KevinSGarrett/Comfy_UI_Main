from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_LIPS_BOTTOM_AUTHORITY_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "lapa_gold_benchmark_gate": "W70_FACIAL_LAPA_GOLD_BENCHMARK_GATE_*.json",
    "combined_gold_postprocess_route_eval": "W70_COMBINED_GOLD_POSTPROCESS_ROUTE_EVAL_*.json",
    "mediapipe_landmark_route_eval": "W70_MEDIAPIPE_LANDMARK_ROUTE_EVAL_*.json",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest(pattern: str) -> Path:
    matches = sorted(QA_DIR.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No evidence found for {pattern}")
    return matches[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_record(name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "path": rel(path),
        "sha256": sha256(path),
        "result": payload.get("result"),
    }


def lapa_region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("region_gate_records", []):
        if record.get("region") == region or record.get("mask_type_id") == region:
            return record
    return None


def postprocess_region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("region_route_records", []):
        if record.get("region") == region:
            return record
    return None


def mediapipe_region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("route_records", []):
        if record.get("region") == region:
            return record
    return None


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    lapa_gate = sources["lapa_gold_benchmark_gate"]
    postprocess = sources["combined_gold_postprocess_route_eval"]
    mediapipe = sources["mediapipe_landmark_route_eval"]

    lapa_record = lapa_region_record(lapa_gate, "mf70_lips_bottom")
    postprocess_record = postprocess_region_record(postprocess, "mf70_lips_bottom")
    mediapipe_record = mediapipe_region_record(mediapipe, "mf70_lips_bottom")
    if lapa_record is None:
        raise RuntimeError("LaPa gate has no mf70_lips_bottom record")
    if postprocess_record is None:
        raise RuntimeError("Postprocess eval has no mf70_lips_bottom record")
    if mediapipe_record is None:
        raise RuntimeError("MediaPipe eval has no mf70_lips_bottom record")

    lapa_pass = bool(lapa_record.get("lapa_gold_benchmark_gate_pass"))
    postprocess_pass = bool(postprocess_record.get("best_pass_gate"))
    mediapipe_pass = bool(mediapipe_record.get("passes_current_gold_gate"))
    current_policy_pass = lapa_pass or postprocess_pass or mediapipe_pass

    policy_options = [
        {
            "policy": "promote_current_lapa_lips_bottom_route",
            "decision": "rejected",
            "reason": "The current LaPa lips-bottom route fails mean IoU and false-positive gates.",
        },
        {
            "policy": "promote_best_combined_gold_postprocess_route",
            "decision": "rejected",
            "reason": "The best combined-gold postprocess route still fails mean IoU and false-positive gates.",
        },
        {
            "policy": "promote_mediapipe_lip_landmark_route",
            "decision": "rejected",
            "reason": "The MediaPipe landmark route still fails mean IoU and false-negative gates.",
        },
        {
            "policy": "fail_closed_until_boundary_aware_bottom_lip_authority_or_explicit_row_policy",
            "decision": "selected",
            "reason": (
                "Current parser, postprocess, and MediaPipe landmark routes all fail gold-backed lips-bottom gates. "
                "The row needs a boundary-aware bottom-lip authority, stronger semantic parser/landmark route, or explicit row policy."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_lips_bottom authority-policy decision from current LaPa, postprocess, and MediaPipe evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_lips_bottom",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "primary_datasets": ["CelebAMask-HQ", "LaPa"],
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "lapa_lips_bottom_gate_record": lapa_record,
        "combined_gold_postprocess_record": postprocess_record,
        "mediapipe_lips_bottom_record": mediapipe_record,
        "lapa_lips_bottom_policy_pass": lapa_pass,
        "combined_gold_postprocess_policy_pass": postprocess_pass,
        "mediapipe_lips_bottom_policy_pass": mediapipe_pass,
        "current_lips_bottom_policy_pass": current_policy_pass,
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_boundary_aware_bottom_lip_authority_or_explicit_row_policy",
        "result": "mf70_lips_bottom_authority_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote or target-proof mf70_lips_bottom from the current LaPa route, combined-gold postprocess route, "
            "or MediaPipe landmark route. Resume this row only with a boundary-aware bottom-lip authority, stronger semantic parser/landmark route, "
            "or explicit row policy backed by gold evidence."
        ),
        "next_required_action": (
            "Switch to another local gold-backed blocked row, or introduce a boundary-aware bottom-lip authority / explicit row policy before any new lips-bottom proof."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": rel(evidence_path),
                "tracker": rel(tracker_path),
                "result": evidence["result"],
                "selected_policy": evidence["selected_policy"],
                "lapa_lips_bottom_policy_pass": lapa_pass,
                "combined_gold_postprocess_policy_pass": postprocess_pass,
                "mediapipe_lips_bottom_policy_pass": mediapipe_pass,
                "current_lips_bottom_policy_pass": current_policy_pass,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
