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
EVIDENCE_ID = f"W70_TEETH_MOUTH_AUTHORITY_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "teeth_mouth_v2_combined_gold_eval": "W70_MF70_TEETH_MOUTH_AREA_V2_COMBINED_GOLD_EVAL_*.json",
    "teeth_mouth_anisotropic_route_search": "W70_MF70_TEETH_MOUTH_AREA_ANISOTROPIC_ROUTE_SEARCH_*.json",
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


def anisotropic_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "best_route": payload.get("best_route"),
        "best_pass_gate": payload.get("best_pass_gate"),
        "best_summary": payload.get("best_summary"),
        "best_failed_reasons": payload.get("best_failed_reasons", []),
        "route_count": payload.get("route_count"),
        "best_dataset_summaries": payload.get("best_dataset_summaries"),
    }


def v2_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "route": payload.get("route"),
        "combined_pass_gate": payload.get("combined_pass_gate"),
        "combined_summary": payload.get("combined_summary"),
        "combined_failed_reasons": payload.get("combined_failed_reasons", []),
        "dataset_summaries": payload.get("dataset_summaries"),
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    v2 = sources["teeth_mouth_v2_combined_gold_eval"]
    anisotropic = sources["teeth_mouth_anisotropic_route_search"]

    v2_pass = bool(v2.get("combined_pass_gate"))
    anisotropic_pass = bool(anisotropic.get("best_pass_gate"))
    morphology_policy_pass = v2_pass or anisotropic_pass

    dataset_summaries = v2.get("dataset_summaries", {})
    celeba_v2_pass = bool(dataset_summaries.get("CelebAMask-HQ", {}).get("pass_gate"))
    lapa_v2_pass = bool(dataset_summaries.get("LaPa", {}).get("pass_gate"))

    policy_options = [
        {
            "policy": "promote_v2_current_route",
            "decision": "rejected",
            "reason": "The v2 route fails the combined gold gate and cannot use target-specific proof as gold support.",
        },
        {
            "policy": "promote_best_anisotropic_morphology_route",
            "decision": "rejected",
            "reason": "The 6,471-route anisotropic morphology/shift search still fails the combined gold IoU/FN gates.",
        },
        {
            "policy": "dataset_split_use_celeba_v2_only",
            "decision": "rejected",
            "reason": "v2 passes CelebAMask-HQ but fails LaPa; no current evidence justifies excluding LaPa from this row.",
        },
        {
            "policy": "fail_closed_until_non_morphology_mouth_boundary_authority_or_explicit_row_policy",
            "decision": "selected",
            "reason": (
                "Both the existing v2 route and the broader morphology/shift family are exhausted under current gold evidence. "
                "The row needs a non-morphology mouth-interior boundary authority, or an explicit dataset/runtime policy before target proof."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_teeth_mouth_area authority-policy decision from current combined-gold route evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_teeth_mouth_area",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "primary_datasets": ["CelebAMask-HQ", "LaPa"],
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "v2_combined_gold_summary": v2_summary(v2),
        "anisotropic_route_summary": anisotropic_summary(anisotropic),
        "v2_combined_policy_pass": v2_pass,
        "anisotropic_morphology_policy_pass": anisotropic_pass,
        "morphology_family_policy_pass": morphology_policy_pass,
        "v2_celeba_pass": celeba_v2_pass,
        "v2_lapa_pass": lapa_v2_pass,
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_non_morphology_mouth_boundary_authority_or_explicit_row_policy",
        "result": "mf70_teeth_mouth_area_authority_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote or target-proof mf70_teeth_mouth_area from v2 or the current morphology/shift route family. "
            "Resume this row only with a non-morphology mouth-interior boundary authority, stronger semantic parser/landmark route, "
            "or an explicit dataset/runtime row policy backed by gold evidence."
        ),
        "next_required_action": (
            "Switch to another local gold-backed blocked row, or introduce a non-morphology mouth-interior boundary authority / explicit row policy before any new teeth-mouth proof."
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
                "v2_combined_policy_pass": v2_pass,
                "anisotropic_morphology_policy_pass": anisotropic_pass,
                "morphology_family_policy_pass": morphology_policy_pass,
                "v2_celeba_pass": celeba_v2_pass,
                "v2_lapa_pass": lapa_v2_pass,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
