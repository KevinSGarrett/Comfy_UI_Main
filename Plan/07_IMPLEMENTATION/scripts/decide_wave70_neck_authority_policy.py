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
EVIDENCE_ID = f"W70_NECK_AUTHORITY_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "neck_boundary_route_search": "W70_MF70_NECK_BOUNDARY_ROUTE_SEARCH_*.json",
    "neck_body_source_authority_audit": "W70_MF70_NECK_BODY_SOURCE_AUTHORITY_AUDIT_*.json",
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

    boundary = sources["neck_boundary_route_search"]
    authority = sources["neck_body_source_authority_audit"]

    boundary_pass = bool(boundary.get("best_pass_gate"))
    direct_neck_authority_available = bool(authority.get("direct_neck_authority_available"))
    policy_pass = boundary_pass and direct_neck_authority_available

    policy_options = [
        {
            "policy": "promote_current_boundary_route",
            "decision": "rejected",
            "reason": "The best current neck boundary route fails the gold gate on mean IoU and false-positive ratio.",
        },
        {
            "policy": "promote_body_source_neck_label",
            "decision": "rejected",
            "reason": "The audited body-source datasets do not expose a direct explicit neck label.",
        },
        {
            "policy": "target_portrait_visual_override",
            "decision": "rejected",
            "reason": "Target-portrait overlays are not pass authority for Wave70 gold-backed mask promotion.",
        },
        {
            "policy": "fail_closed_until_explicit_neck_authority_or_gold_reviewed_policy",
            "decision": "selected",
            "reason": (
                "Current boundary geometry overfills lower-neck/torso area and no body parser with an explicit neck label "
                "is registered. Neck needs a new authority, or a separately justified face/torso-to-neck policy with gold review."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_neck authority-policy decision from current gold-backed boundary and body-source evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_neck",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "boundary_route_summary": metric_summary(boundary),
        "boundary_policy_pass": boundary_pass,
        "direct_neck_authority_available": direct_neck_authority_available,
        "direct_neck_authority_sources": authority.get("direct_neck_authority_sources", []),
        "body_root": authority.get("body_root"),
        "dataset_audits": authority.get("dataset_audits", []),
        "current_neck_authority_policy_pass": policy_pass,
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_explicit_neck_authority_or_gold_reviewed_policy",
        "result": "mf70_neck_authority_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote or target-proof mf70_neck from the current boundary route family or current body-source audit. "
            "Resume neck only after registering a parser/dataset with an explicit neck label, or after defining a separately "
            "gold-reviewed face/torso-to-neck policy that is not derived from target-portrait visual preference."
        ),
        "next_required_action": (
            "Switch to another local gold-backed blocked row, or register an explicit neck-label authority / gold-reviewed neck policy before any new neck proof."
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
                "boundary_policy_pass": boundary_pass,
                "direct_neck_authority_available": direct_neck_authority_available,
                "current_neck_authority_policy_pass": policy_pass,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
