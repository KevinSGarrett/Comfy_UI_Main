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
EVIDENCE_ID = f"W70_EYEBROW_DATASET_RUNTIME_POLICY_DECISION_{RUN_STAMP}"

SOURCES = {
    "combined_gold_gate": "W70_FACIAL_COMBINED_GOLD_GATE_DECISION_*.json",
    "dataset_failure_diagnostic": "W70_EYE_BROW_ROUTE_DATASET_FAILURE_DIAGNOSTIC_*.json",
    "supplied_landmark_eye_brow": "W70_LAPA_SUPPLIED_LANDMARK_EYE_BROW_ROUTE_EVAL_*.json",
    "parser_landmark_brow": "W70_LAPA_PARSER_LANDMARK_BROW_ROUTE_EVAL_*.json",
    "parser_options_audit": "W70_EYEBROW_SEMANTIC_PARSER_OPTIONS_AUDIT_*.json",
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


def region_record(payload: dict[str, Any], region: str) -> dict[str, Any] | None:
    for record in payload.get("region_decisions", []):
        if record.get("region") == region:
            return record
    return None


def diagnostic_region_records(payload: dict[str, Any], region: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for diagnostic in payload.get("diagnostics", []):
        for item in diagnostic.get("dataset_results", []):
            if item.get("region") == region:
                records.append(
                    {
                        "source_route_family": diagnostic.get("source_route_family"),
                        "source_evidence": diagnostic.get("source_evidence"),
                        "dataset": item.get("dataset"),
                        "best_route": item.get("best_route"),
                        "summary": item.get("summary"),
                    }
                )
    return records


def lapa_supplied_brow_record(payload: dict[str, Any]) -> dict[str, Any] | None:
    for record in payload.get("region_results", []):
        if record.get("region") == "mf70_eyebrows":
            return {
                "best_route": record.get("best_route"),
                "best_pass_gate": record.get("best_pass_gate"),
                "best_summary": record.get("best_summary"),
            }
    return None


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)

    source_paths = {name: latest(pattern) for name, pattern in SOURCES.items()}
    sources = {name: load_json(path) for name, path in source_paths.items()}

    combined_brow = region_record(sources["combined_gold_gate"], "mf70_eyebrows")
    if combined_brow is None:
        raise RuntimeError("Combined gold gate has no mf70_eyebrows record")

    combined_dataset_records = combined_brow.get("dataset_records", {})
    dataset_passes = {
        name: bool(record.get("pass"))
        for name, record in combined_dataset_records.items()
        if isinstance(record, dict) and record.get("covered", True)
    }
    any_combined_dataset_pass = any(dataset_passes.values())
    all_current_gold_datasets_block = all(not passed for passed in dataset_passes.values())
    parser_options = sources["parser_options_audit"]

    policy_options = [
        {
            "policy": "promote_runtime_brow_from_current_route",
            "decision": "rejected",
            "reason": "No current eyebrow route passes the combined gold gate or dataset-level route diagnostics.",
        },
        {
            "policy": "dataset_split_use_celeba_or_lapa_current_route",
            "decision": "rejected",
            "reason": "The current combined gate blocks mf70_eyebrows in both CelebAMask-HQ and LaPa, so a dataset split would not be evidence-backed.",
        },
        {
            "policy": "single_generated_portrait_visual_override",
            "decision": "rejected",
            "reason": "MaskedWarehouse gold originals and masks are the authority; generated portrait overlays are downstream sanity checks only.",
        },
        {
            "policy": "fail_closed_until_stronger_parser_or_new_row",
            "decision": "selected",
            "reason": "Both gold datasets block current eyebrow routes and no stronger local automatic eyebrow parser is registered.",
        },
    ]

    source_evidence = []
    for name, path in source_paths.items():
        source_evidence.append(
            {
                "name": name,
                "path": rel(path),
                "sha256": sha256(path),
                "result": sources[name].get("result"),
            }
        )

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "Wave70 mf70_eyebrows dataset-vs-runtime policy decision from current gold-backed evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "region": "mf70_eyebrows",
        "gold_mask_authority": {
            "masked_warehouse": str(PROJECT_ROOT / "MaskedWarehouse"),
            "primary_datasets": ["CelebAMask-HQ", "LaPa"],
            "single_generated_portrait_is_pass_authority": False,
        },
        "source_evidence": source_evidence,
        "combined_gold_brow_record": combined_brow,
        "dataset_passes": dataset_passes,
        "all_current_gold_datasets_block": all_current_gold_datasets_block,
        "any_combined_dataset_pass": any_combined_dataset_pass,
        "dataset_failure_records": diagnostic_region_records(sources["dataset_failure_diagnostic"], "mf70_eyebrows"),
        "lapa_supplied_landmark_brow_record": lapa_supplied_brow_record(sources["supplied_landmark_eye_brow"]),
        "parser_landmark_brow_record": sources["parser_landmark_brow"].get("region_result"),
        "stronger_local_eyebrow_semantic_parser_registered_now": parser_options.get(
            "stronger_local_eyebrow_semantic_parser_registered_now"
        ),
        "policy_options": policy_options,
        "selected_policy": "fail_closed_until_stronger_parser_or_new_row",
        "result": "mf70_eyebrows_policy_fail_closed_no_dataset_split_promotion",
        "decision": (
            "Do not promote or target-proof mf70_eyebrows from current routes. A dataset-vs-runtime split is not justified "
            "because current evidence blocks eyebrows on both CelebAMask-HQ and LaPa, and no stronger local automatic eyebrow parser is registered."
        ),
        "next_required_action": (
            "Register/validate a stronger eyebrow semantic parser, or switch to another blocked facial/body row with a genuinely new gold-backed route."
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
                "all_current_gold_datasets_block": all_current_gold_datasets_block,
                "stronger_local_eyebrow_semantic_parser_registered_now": evidence[
                    "stronger_local_eyebrow_semantic_parser_registered_now"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
