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
EVIDENCE_ID = f"W70_INSIGHTFACE_EYE_ROUTE_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "latest_insightface_106_eye_route_eval": "W70_INSIGHTFACE_106_EYE_ROUTE_EVAL_*.json",
    "runtime_106_landmark_source_audit": "W70_RUNTIME_106_LANDMARK_SOURCE_AUDIT_*.json",
    "lapa_supplied_landmark_eye_brow_eval": "W70_LAPA_SUPPLIED_LANDMARK_EYE_BROW_ROUTE_EVAL_*.json",
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


def lapa_eyes_record(payload: dict[str, Any]) -> dict[str, Any] | None:
    for record in payload.get("region_results", []):
        if record.get("region") == "mf70_eyes_full":
            return {
                "best_route": record.get("best_route"),
                "best_pass_gate": record.get("best_pass_gate"),
                "best_summary": record.get("best_summary"),
                "decision": record.get("decision"),
            }
    return None


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    eye_eval = sources["latest_insightface_106_eye_route_eval"]
    runtime_audit = sources["runtime_106_landmark_source_audit"]
    supplied_landmark = sources["lapa_supplied_landmark_eye_brow_eval"]

    best_pass_gate = bool(eye_eval.get("best_pass_gate"))
    failed_reasons = list(eye_eval.get("best_failed_reasons", []))
    best_summary = eye_eval.get("best_summary", {})
    thresholds = eye_eval.get("thresholds", {})
    route_count = int(eye_eval.get("route_count", 0))
    best_route = str(eye_eval.get("best_route", ""))
    shifted_family_tested = route_count >= 4861
    shifted_family_improved_best = "shifted" in best_route

    policy_options = [
        {
            "policy": "promote_current_insightface_106_eye_route",
            "decision": "rejected",
            "reason": "The latest InsightFace 106 route evaluation fails the gold gate and must not be promoted.",
        },
        {
            "policy": "continue_retuning_current_106_index_shift_window_family",
            "decision": "rejected",
            "reason": (
                "The bounded shifted union expansion has already been tested and did not improve the best route; "
                "more tuning of the same family is now a loop, not progress."
            ),
        },
        {
            "policy": "use_lapa_supplied_landmarks_as_runtime_authority",
            "decision": "rejected",
            "reason": (
                "LaPa supplied landmarks remain diagnostic only because target/runtime portraits do not supply those labels."
            ),
        },
        {
            "policy": "fail_closed_until_new_eye_authority_or_switch_row",
            "decision": "selected",
            "reason": (
                "A model-backed runtime 106-point source exists, but the current automatic InsightFace eye route family "
                "does not pass gold-backed IoU, false-positive, or false-negative gates."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_eyes_full InsightFace 106 route policy decision from current gold-backed evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_eyes_full",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "primary_dataset_for_current_route": "LaPa",
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "runtime_106_authority_available": (
            "insightface" in runtime_audit.get("runtime_106_candidate_modules", [])
            or eye_eval.get("landmark_source", "").startswith("insightface")
        ),
        "runtime_106_authority": eye_eval.get("landmark_source"),
        "latest_eye_eval_result": eye_eval.get("result"),
        "route_count": route_count,
        "best_route": best_route,
        "best_summary": best_summary,
        "thresholds": thresholds,
        "best_pass_gate": best_pass_gate,
        "best_failed_reasons": failed_reasons,
        "shifted_family_tested": shifted_family_tested,
        "shifted_family_improved_best": shifted_family_improved_best,
        "lapa_supplied_landmark_eye_record": lapa_eyes_record(supplied_landmark),
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_new_eye_authority_or_switch_row",
        "result": "mf70_eyes_full_insightface_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote, target-proof, or keep retuning mf70_eyes_full from the current InsightFace 106 route family. "
            "The route remains below the gold gate after the bounded shifted-family pass. Resume this row only after "
            "introducing a genuinely new eye authority, corrected 106-point index map, or explicit non-runtime diagnostic policy."
        ),
        "next_required_action": (
            "Switch to another local gold-backed blocked row or introduce a genuinely new eye segmentation/landmark authority; "
            "do not run another same-family InsightFace 106 retuning pass."
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
                "best_pass_gate": best_pass_gate,
                "best_failed_reasons": failed_reasons,
                "route_count": route_count,
                "shifted_family_improved_best": shifted_family_improved_best,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
