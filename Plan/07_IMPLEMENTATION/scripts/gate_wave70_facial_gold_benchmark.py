#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
BENCHMARK_EVIDENCE = PROJECT_ROOT / (
    "Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/"
    "W70_FACIAL_GOLD_STANDARD_BENCHMARK_20260710T012300-0500.json"
)
TRACKER_CSV = PROJECT_ROOT / "Plan/Tracker/wave70_ultimate_mask_factory_tracker.csv"
ITEM_CSV = PROJECT_ROOT / "Plan/Items/wave70_ultimate_mask_factory_itemized_list.csv"
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"

RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_FACIAL_GOLD_BENCHMARK_GATE_{RUN_STAMP}"

# A row is not allowed to use the parser benchmark as promotion-supporting
# evidence unless the mean score clears this minimum on real gold originals.
MIN_MEAN_IOU = 0.85
MIN_SAMPLE_COUNT = 3
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15

REGION_TO_MASK_TYPE = {
    "mf70_face_skin": "mf70_face_skin",
    "mf70_hair": "mf70_hair",
    "mf70_nose": "mf70_nose",
    "mf70_eyes_full": "mf70_eyes_full",
    "mf70_eyebrows": "mf70_eyebrows",
    "mf70_lips_top": "mf70_lips_top",
    "mf70_lips_bottom": "mf70_lips_bottom",
    "mf70_lips_combined": "mf70_lips_combined",
    "mf70_teeth_mouth_area": "mf70_teeth_mouth_area",
    "mf70_neck": "mf70_neck",
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_rows(path: Path, id_field: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        mask_type = row.get("Source_Key", "").split(":")[-1] or row.get("Task_Name", "")
        if mask_type:
            out[mask_type] = {
                "id": row.get(id_field, ""),
                "status": row.get("Status", ""),
                "status_decision": row.get("Status_Decision", ""),
                "evidence_path": row.get("Evidence_Path", ""),
                "task_name": row.get("Task_Name", ""),
                "source_key": row.get("Source_Key", ""),
            }
    return out


def evaluate_region(region: str, summary: dict[str, Any], tracker_rows: dict[str, dict[str, str]], item_rows: dict[str, dict[str, str]]) -> dict[str, Any]:
    mask_type = REGION_TO_MASK_TYPE[region]
    sample_count = int(summary.get("sample_count", 0))
    mean_iou = float(summary.get("mean_iou", 0.0))
    mean_dice = float(summary.get("mean_dice", 0.0))
    fp = summary.get("mean_false_positive_ratio_vs_gold")
    fn = summary.get("mean_false_negative_ratio_vs_gold")
    fp_value = float(fp or 0.0)
    fn_value = float(fn or 0.0)

    failed_reasons: list[str] = []
    if sample_count < MIN_SAMPLE_COUNT:
        failed_reasons.append(f"sample_count_below_{MIN_SAMPLE_COUNT}")
    if mean_iou < MIN_MEAN_IOU:
        failed_reasons.append(f"mean_iou_below_{MIN_MEAN_IOU}")
    if fp is None or fp_value > MAX_FALSE_POSITIVE_RATIO_VS_GOLD:
        failed_reasons.append(f"false_positive_ratio_above_{MAX_FALSE_POSITIVE_RATIO_VS_GOLD}")
    if fn is None or fn_value > MAX_FALSE_NEGATIVE_RATIO_VS_GOLD:
        failed_reasons.append(f"false_negative_ratio_above_{MAX_FALSE_NEGATIVE_RATIO_VS_GOLD}")

    pass_gate = not failed_reasons
    return {
        "region": region,
        "mask_type_id": mask_type,
        "tracker_row": tracker_rows.get(mask_type, {}),
        "item_row": item_rows.get(mask_type, {}),
        "sample_count": sample_count,
        "mean_iou": mean_iou,
        "mean_dice": mean_dice,
        "mean_false_positive_ratio_vs_gold": fp,
        "mean_false_negative_ratio_vs_gold": fn,
        "gold_benchmark_gate_pass": pass_gate,
        "failed_reasons": failed_reasons,
        "gate_decision": (
            "parser_route_gold_benchmark_supports_candidate_evidence_not_promotion"
            if pass_gate
            else "blocked_gold_benchmark_metric_threshold_not_met"
        ),
    }


def main() -> int:
    if not BENCHMARK_EVIDENCE.exists():
        raise FileNotFoundError(BENCHMARK_EVIDENCE)
    benchmark = json.loads(BENCHMARK_EVIDENCE.read_text(encoding="utf-8"))
    region_summary = benchmark.get("summary", {}).get("region_summary", {})
    tracker_rows = load_rows(TRACKER_CSV, "Tracker_ID")
    item_rows = load_rows(ITEM_CSV, "Item_ID")

    records = [
        evaluate_region(region, region_summary[region], tracker_rows, item_rows)
        for region in sorted(region_summary)
        if region in REGION_TO_MASK_TYPE
    ]
    passed = [record for record in records if record["gold_benchmark_gate_pass"]]
    blocked = [record for record in records if not record["gold_benchmark_gate_pass"]]
    weakest_blocked = sorted(blocked, key=lambda record: record["mean_iou"])[:5]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "fail-closed Wave70 facial gold benchmark gate from MaskedWarehouse/CelebAMask original+gold-mask metrics",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "benchmark_evidence": rel(BENCHMARK_EVIDENCE),
        "benchmark_sha256": sha256(BENCHMARK_EVIDENCE),
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "min_sample_count": MIN_SAMPLE_COUNT,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "region_gate_records": records,
        "pass_region_count": len(passed),
        "blocked_region_count": len(blocked),
        "passed_regions": [record["region"] for record in passed],
        "blocked_regions": [record["region"] for record in blocked],
        "weakest_blocked_regions": [
            {
                "region": record["region"],
                "mask_type_id": record["mask_type_id"],
                "mean_iou": record["mean_iou"],
                "mean_dice": record["mean_dice"],
                "failed_reasons": record["failed_reasons"],
            }
            for record in weakest_blocked
        ],
        "result": (
            "blocked_wave70_facial_gold_benchmark_gate_regions_require_repair"
            if blocked
            else "pass_wave70_facial_gold_benchmark_gate_all_regions_metric_threshold_met"
        ),
        "promotion_decision": "no_mask_promotion_no_active_input_change_gate_only",
        "next_required_action": (
            "Repair or replace the lowest-IoU blocked facial parser/mask route before using target-portrait output as row evidence. "
            "Current priority starts with mf70_neck, then mf70_lips_top, mf70_face_skin, mf70_teeth_mouth_area, and mf70_lips_combined."
        ),
    }

    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": str(evidence_path), "tracker": str(tracker_path), "result": evidence["result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
