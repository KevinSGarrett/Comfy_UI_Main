from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
QA_DIR = PROJECT_ROOT / "Plan" / "Instructions" / "QA" / "Evidence" / "Mask_Factory" / "Wave70"
TRACKER_DIR = PROJECT_ROOT / "Plan" / "Tracker" / "Evidence"
RUN_STAMP = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y%m%dT%H%M%S-0500")
EVIDENCE_ID = f"W70_EYE_BROW_ROUTE_DATASET_FAILURE_DIAGNOSTIC_{RUN_STAMP}"

MIN_MEAN_IOU = 0.85
MAX_FALSE_POSITIVE_RATIO_VS_GOLD = 0.15
MAX_FALSE_NEGATIVE_RATIO_VS_GOLD = 0.15


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def latest(pattern: str) -> Path:
    matches = sorted(QA_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [sample["metrics"] for sample in samples]
    summary = {
        "sample_count": len(samples),
        "mean_iou": mean([float(item["iou"]) for item in metrics]),
        "mean_dice": mean([float(item["dice"]) for item in metrics]),
        "mean_false_positive_ratio_vs_gold": mean([float(item["false_positive_ratio_vs_gold"] or 0.0) for item in metrics]),
        "mean_false_negative_ratio_vs_gold": mean([float(item["false_negative_ratio_vs_gold"] or 0.0) for item in metrics]),
    }
    failed = []
    if summary["mean_iou"] < MIN_MEAN_IOU:
        failed.append("mean_iou_below_gate")
    if summary["mean_false_positive_ratio_vs_gold"] > MAX_FALSE_POSITIVE_RATIO_VS_GOLD:
        failed.append("false_positive_ratio_above_gate")
    if summary["mean_false_negative_ratio_vs_gold"] > MAX_FALSE_NEGATIVE_RATIO_VS_GOLD:
        failed.append("false_negative_ratio_above_gate")
    summary["pass_gate"] = not failed
    summary["failed_reasons"] = failed
    return summary


def sample_sort_key(sample: dict[str, Any]) -> tuple[float, float, float]:
    metrics = sample["metrics"]
    return (
        float(metrics["iou"]),
        -float(metrics["false_positive_ratio_vs_gold"] or 0.0),
        -float(metrics["false_negative_ratio_vs_gold"] or 0.0),
    )


def diagnose_evidence(path: Path) -> dict[str, Any]:
    evidence = load_json(path)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for sample in evidence.get("best_sample_metrics", []):
        grouped[(sample["region"], sample["dataset"])].append(sample)

    dataset_results = []
    for (region, dataset), samples in sorted(grouped.items()):
        summary = summarize(samples)
        worst = sorted(samples, key=sample_sort_key)[:3]
        dataset_results.append(
            {
                "region": region,
                "dataset": dataset,
                "best_route": samples[0].get("best_route"),
                "summary": summary,
                "worst_samples": [
                    {
                        "sample_key": sample["sample_key"],
                        "iou": sample["metrics"]["iou"],
                        "false_positive_ratio_vs_gold": sample["metrics"]["false_positive_ratio_vs_gold"],
                        "false_negative_ratio_vs_gold": sample["metrics"]["false_negative_ratio_vs_gold"],
                    }
                    for sample in worst
                ],
            }
        )

    blocking_patterns = []
    for region in sorted({item["region"] for item in dataset_results}):
        rows = [item for item in dataset_results if item["region"] == region]
        passing = [item["dataset"] for item in rows if item["summary"]["pass_gate"]]
        blocking = [item["dataset"] for item in rows if not item["summary"]["pass_gate"]]
        blocking_patterns.append(
            {
                "region": region,
                "passing_datasets": passing,
                "blocking_datasets": blocking,
                "requires_policy_or_stronger_route": bool(blocking),
            }
        )

    return {
        "source_evidence": rel(path),
        "source_result": evidence.get("result"),
        "source_route_family": evidence.get("route_family"),
        "dataset_results": dataset_results,
        "blocking_patterns": blocking_patterns,
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    source_paths = [
        latest("W70_MEDIAPIPE_EYE_BROW_COMBINED_ROUTE_EVAL_*.json"),
        latest("W70_EYE_BROW_HYBRID_ROUTE_EVAL_*.json"),
    ]
    diagnostics = [diagnose_evidence(path) for path in source_paths]
    any_pass_by_dataset = any(
        item["summary"]["pass_gate"]
        for diagnostic in diagnostics
        for item in diagnostic["dataset_results"]
    )
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "dataset-level failure diagnostic for MediaPipe and hybrid eye/brow route evidence",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "thresholds": {
            "min_mean_iou": MIN_MEAN_IOU,
            "max_false_positive_ratio_vs_gold": MAX_FALSE_POSITIVE_RATIO_VS_GOLD,
            "max_false_negative_ratio_vs_gold": MAX_FALSE_NEGATIVE_RATIO_VS_GOLD,
        },
        "diagnostics": diagnostics,
        "any_dataset_level_pass": any_pass_by_dataset,
        "result": "eye_brow_dataset_failure_diagnostic_completed_no_promotion",
        "next_required_action": (
            "Use the dataset-level blocking patterns to decide whether eyes/brows need a stronger segmentation route "
            "or an explicit dataset-policy split before target-portrait proof."
        ),
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / evidence_path.name
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(json.dumps({"evidence": rel(evidence_path), "tracker": rel(tracker_path), "result": evidence["result"], "any_dataset_level_pass": any_pass_by_dataset}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
