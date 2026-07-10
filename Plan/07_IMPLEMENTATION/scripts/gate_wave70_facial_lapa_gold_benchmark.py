#!/usr/bin/env python3
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
EVIDENCE_ID = f"W70_FACIAL_LAPA_GOLD_BENCHMARK_GATE_{RUN_STAMP}"

MIN_MEAN_IOU = 0.85
MIN_SAMPLE_COUNT = 3
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15


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


def latest_lapa_benchmark() -> Path:
    matches = sorted(
        QA_DIR.glob("W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError("No W70_FACIAL_LAPA_GOLD_LABEL_BENCHMARK evidence found")
    return matches[0]


def evaluate_region(region: str, summary: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "region": region,
        "mask_type_id": region,
        "sample_count": sample_count,
        "mean_iou": mean_iou,
        "mean_dice": mean_dice,
        "mean_false_positive_ratio_vs_gold": fp,
        "mean_false_negative_ratio_vs_gold": fn,
        "lapa_gold_benchmark_gate_pass": not failed_reasons,
        "failed_reasons": failed_reasons,
        "gate_decision": (
            "lapa_gold_benchmark_supports_candidate_route_not_promotion"
            if not failed_reasons
            else "blocked_lapa_gold_benchmark_metric_threshold_not_met"
        ),
    }


def main() -> int:
    benchmark_path = latest_lapa_benchmark()
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    region_summary = benchmark.get("summary", {}).get("region_summary", {})
    records = [evaluate_region(region, region_summary[region]) for region in sorted(region_summary)]
    passed = [record for record in records if record["lapa_gold_benchmark_gate_pass"]]
    blocked = [record for record in records if not record["lapa_gold_benchmark_gate_pass"]]
    weakest_blocked = sorted(blocked, key=lambda record: record["mean_iou"])[:5]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "fail-closed Wave70 facial gold benchmark gate from MaskedWarehouse/LaPa original+semantic-label metrics",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "benchmark_evidence": rel(benchmark_path),
        "benchmark_sha256": sha256(benchmark_path),
        "dataset_used": "LaPa",
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
                "mean_iou": record["mean_iou"],
                "mean_dice": record["mean_dice"],
                "failed_reasons": record["failed_reasons"],
            }
            for record in weakest_blocked
        ],
        "result": (
            "blocked_wave70_facial_lapa_gold_benchmark_gate_regions_require_repair"
            if blocked
            else "pass_wave70_facial_lapa_gold_benchmark_gate_all_regions_metric_threshold_met"
        ),
        "promotion_decision": "no_mask_promotion_no_active_input_change_gate_only",
        "next_required_action": (
            "Treat generated-portrait facial mask QA as subordinate to gold dataset evidence. Combine CelebAMask-HQ and LaPa "
            "gate records before promoting or trusting any facial route; current LaPa failures identify eyes, mouth interior, hair, "
            "lips, eyebrows, and combined lips as requiring route repair or policy separation."
        ),
        "dataset_boundary": (
            "LaPa does not provide a neck label in the ingested 0-10 semantic map, so mf70_neck remains governed by CelebAMask-HQ "
            "or a separate body/neck gold source."
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
