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
EVIDENCE_ID = f"W70_LIPS_TOP_AUTHORITY_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "lips_top_failure_diagnostic": "W70_MF70_LIPS_TOP_GOLD_FAILURE_DIAGNOSTIC_*.json",
    "lapa_gold_benchmark_gate": "W70_FACIAL_LAPA_GOLD_BENCHMARK_GATE_*.json",
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


def diagnostic_best_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "best_radius_by_mean_iou": payload.get("best_radius_by_mean_iou"),
        "best_summary": payload.get("best_summary"),
        "finding": payload.get("finding"),
        "decision": payload.get("decision"),
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    diagnostic = sources["lips_top_failure_diagnostic"]
    lapa_gate = sources["lapa_gold_benchmark_gate"]
    lapa_lips_top = lapa_region_record(lapa_gate, "mf70_lips_top")
    if lapa_lips_top is None:
        raise RuntimeError("LaPa gate has no mf70_lips_top region record")

    lapa_pass = bool(lapa_lips_top.get("lapa_gold_benchmark_gate_pass"))
    best = diagnostic.get("best_summary", {})
    simple_expansion_pass = (
        float(best.get("mean_iou", 0.0)) >= 0.85
        and float(best.get("mean_false_positive_ratio_vs_gold", 1.0)) <= 0.15
        and float(best.get("mean_false_negative_ratio_vs_gold", 1.0)) <= 0.15
    )
    current_policy_pass = lapa_pass and simple_expansion_pass

    policy_options = [
        {
            "policy": "promote_current_lapa_lips_top_route",
            "decision": "rejected",
            "reason": "The current LaPa lips-top route fails the gold gate on mean IoU and false-positive ratio.",
        },
        {
            "policy": "promote_simple_expansion_repair",
            "decision": "rejected",
            "reason": "The best simple expansion radius improves recall but still fails mean IoU and false-positive gates.",
        },
        {
            "policy": "single_generated_portrait_visual_override",
            "decision": "rejected",
            "reason": "Generated target overlays are not pass authority for Wave70 gold-backed mask promotion.",
        },
        {
            "policy": "fail_closed_until_boundary_aware_lip_authority_or_explicit_row_policy",
            "decision": "selected",
            "reason": (
                "Current lips-top masks under/over-cover differently across gold samples, and simple expansion is exhausted. "
                "The row needs a boundary-aware lip authority, semantic parser/landmark route, or explicit row policy before target proof."
            ),
        },
    ]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_lips_top authority-policy decision from current LaPa gate and simple-expansion diagnostic evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_lips_top",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "primary_dataset_for_current_route": "LaPa",
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": [
            source_record(name, path, sources[name])
            for name, path in source_paths.items()
        ],
        "lapa_lips_top_gate_record": lapa_lips_top,
        "simple_expansion_diagnostic": diagnostic_best_summary(diagnostic),
        "lapa_lips_top_policy_pass": lapa_pass,
        "simple_expansion_policy_pass": simple_expansion_pass,
        "current_lips_top_policy_pass": current_policy_pass,
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_boundary_aware_lip_authority_or_explicit_row_policy",
        "result": "mf70_lips_top_authority_policy_fail_closed_no_promotion",
        "decision": (
            "Do not promote or target-proof mf70_lips_top from the current LaPa route or simple-expansion repair family. "
            "Resume this row only with a boundary-aware lip authority, stronger semantic parser/landmark route, or explicit row policy backed by gold evidence."
        ),
        "next_required_action": (
            "Switch to another local gold-backed blocked row, or introduce a boundary-aware lip authority / explicit row policy before any new lips-top proof."
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
                "lapa_lips_top_policy_pass": lapa_pass,
                "simple_expansion_policy_pass": simple_expansion_pass,
                "current_lips_top_policy_pass": current_policy_pass,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
