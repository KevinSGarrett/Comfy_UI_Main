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
EVIDENCE_ID = f"W70_HAIR_PROMPT_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "hair_foreground_ownership_route_search": "W70_MF70_HAIR_FOREGROUND_OWNERSHIP_ROUTE_SEARCH_*.json",
    "hair_person_segmentation_authority_audit": "W70_HAIR_PERSON_SEGMENTATION_AUTHORITY_AUDIT_*.json",
    "sam2_hair_promptability_probe": "W70_SAM2_HAIR_PROMPTABILITY_PROBE_*.json",
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


def metric_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "best_route": payload.get("best_route"),
        "best_pass_gate": payload.get("best_pass_gate"),
        "best_summary": payload.get("best_summary"),
        "best_failed_reasons": payload.get("best_failed_reasons", []),
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    ownership = sources["hair_foreground_ownership_route_search"]
    authority = sources["hair_person_segmentation_authority_audit"]
    sam2 = sources["sam2_hair_promptability_probe"]

    sam2_route_count = len(sam2.get("route_records", []))
    sam2_best_is_oracle = bool(sam2.get("best_is_diagnostic_oracle"))
    sam2_prompt_policy_pass = bool(sam2.get("best_pass_gate")) and not sam2_best_is_oracle
    ownership_pass = bool(ownership.get("best_pass_gate"))
    current_hair_routes_pass = sam2_prompt_policy_pass or ownership_pass

    policy_options = [
        {
            "policy": "promote_current_foreground_ownership_route",
            "decision": "rejected",
            "reason": "The best foreground ownership route still fails the gold IoU gate.",
        },
        {
            "policy": "promote_current_sam2_bbox_point_prompt_policy",
            "decision": "rejected",
            "reason": "The bounded SAM2 promptability probe found no non-oracle promotable candidate and the best route remains the parser baseline.",
        },
        {
            "policy": "dataset_runtime_split_for_hair_edge_cases",
            "decision": "rejected",
            "reason": (
                "No evidence currently justifies excluding LaPa owner/tiny-hair edge cases from the Wave70 hair row; "
                "the row remains governed by gold-backed masks."
            ),
        },
        {
            "policy": "fail_closed_until_stronger_person_instance_or_owner_prompt_authority",
            "decision": "selected",
            "reason": (
                "SAM2 is available locally, but the current automatic bbox/point prompt policy is not a valid hair authority. "
                "Hair needs a stronger non-oracle owner/person prompt route, person-instance segmentation, or another registered authority."
            ),
        },
    ]

    findings = authority.get("findings", {})
    sam2_available_local = bool(findings.get("sam2_importable")) and bool(findings.get("sam2_checkpoint_exists"))

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_hair prompt-policy decision from current gold-backed ownership and SAM2 evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_hair",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "sam2_available_local": sam2_available_local,
        "sam2_authority_findings": {
            "sam2_importable": findings.get("sam2_importable"),
            "sam2_checkpoint_exists": findings.get("sam2_checkpoint_exists"),
            "rembg_available": findings.get("rembg_available"),
            "segment_anything_available": findings.get("segment_anything_available"),
            "background_removal_nonempty_model_count": findings.get("background_removal_nonempty_model_count"),
        },
        "sam2_checkpoint": sam2.get("sam2_checkpoint"),
        "foreground_ownership_summary": metric_summary(ownership),
        "sam2_promptability_summary": metric_summary(sam2),
        "sam2_route_count": sam2_route_count,
        "sam2_best_is_diagnostic_oracle": sam2_best_is_oracle,
        "sam2_prompt_policy_pass": sam2_prompt_policy_pass,
        "ownership_policy_pass": ownership_pass,
        "current_hair_routes_pass": current_hair_routes_pass,
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_stronger_person_instance_or_owner_prompt_authority",
        "result": "mf70_hair_prompt_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote or target-proof mf70_hair from the current foreground-ownership route or current SAM2 bbox/point prompt policy. "
            "The current SAM2 prompt policy is exhausted for promotion purposes; resume hair only with a stronger non-oracle owner/person prompt "
            "authority, person-instance segmentation, or another registered hair segmentation authority."
        ),
        "next_required_action": (
            "Switch to another local gold-backed blocked row, or introduce a stronger hair owner/person-instance prompt authority before any new hair proof."
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
                "sam2_available_local": sam2_available_local,
                "sam2_prompt_policy_pass": sam2_prompt_policy_pass,
                "ownership_policy_pass": ownership_pass,
                "current_hair_routes_pass": current_hair_routes_pass,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
