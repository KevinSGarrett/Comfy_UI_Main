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
EVIDENCE_ID = f"W70_FACIAL_COMBINED_GOLD_GATE_DECISION_{RUN_STAMP}"


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


def latest(pattern: str) -> Path:
    matches = sorted(QA_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(pattern)
    return matches[0]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def gate_records_by_region(gate: dict[str, Any], pass_key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for record in gate.get("region_gate_records", []):
        region = str(record["region"])
        out[region] = {
            "region": region,
            "pass": bool(record.get(pass_key)),
            "sample_count": record.get("sample_count"),
            "mean_iou": record.get("mean_iou"),
            "mean_dice": record.get("mean_dice"),
            "false_positive_ratio_vs_gold": record.get("mean_false_positive_ratio_vs_gold"),
            "false_negative_ratio_vs_gold": record.get("mean_false_negative_ratio_vs_gold"),
            "failed_reasons": record.get("failed_reasons", []),
            "gate_decision": record.get("gate_decision"),
        }
    return out


def combined_decision(region: str, celeba: dict[str, Any] | None, lapa: dict[str, Any] | None) -> dict[str, Any]:
    dataset_records: dict[str, Any] = {}
    blocked_by: list[str] = []
    passed_by: list[str] = []
    missing_from: list[str] = []
    for dataset, record in (("CelebAMask-HQ", celeba), ("LaPa", lapa)):
        if record is None:
            missing_from.append(dataset)
            dataset_records[dataset] = {"covered": False}
            continue
        dataset_records[dataset] = {"covered": True, **record}
        if record["pass"]:
            passed_by.append(dataset)
        else:
            blocked_by.append(dataset)

    if blocked_by:
        route_decision = "blocked_combined_gold_gate_requires_repair_or_policy_split"
    elif missing_from:
        route_decision = "supported_by_available_gold_gates_but_missing_dataset_coverage"
    else:
        route_decision = "supported_by_all_current_gold_gates_candidate_only_not_promotion"

    return {
        "region": region,
        "dataset_records": dataset_records,
        "passed_by": passed_by,
        "blocked_by": blocked_by,
        "missing_from": missing_from,
        "combined_route_decision": route_decision,
        "promotion_decision": "no_promotion_combined_gate_only",
    }


def main() -> int:
    celeba_gate_path = latest("W70_FACIAL_GOLD_BENCHMARK_GATE_*.json")
    lapa_gate_path = latest("W70_FACIAL_LAPA_GOLD_BENCHMARK_GATE_*.json")
    celeba_gate = load(celeba_gate_path)
    lapa_gate = load(lapa_gate_path)
    celeba_records = gate_records_by_region(celeba_gate, "gold_benchmark_gate_pass")
    lapa_records = gate_records_by_region(lapa_gate, "lapa_gold_benchmark_gate_pass")
    regions = sorted(set(celeba_records) | set(lapa_records))
    decisions = [combined_decision(region, celeba_records.get(region), lapa_records.get(region)) for region in regions]
    fully_supported = [item for item in decisions if item["combined_route_decision"].startswith("supported_by_all")]
    missing_coverage = [item for item in decisions if "missing_dataset_coverage" in item["combined_route_decision"]]
    blocked = [item for item in decisions if item["combined_route_decision"].startswith("blocked_")]

    evidence = {
        "evidence_id": EVIDENCE_ID,
        "timestamp": RUN_STAMP,
        "scope": "combined fail-closed Wave70 facial route decision from current CelebAMask-HQ and LaPa gold gates",
        "local_only": True,
        "ec2_started": False,
        "generation_executed": False,
        "active_input_mask_overwritten": False,
        "mask_promoted": False,
        "source_gates": {
            "celeba_gate": rel(celeba_gate_path),
            "celeba_gate_sha256": sha256(celeba_gate_path),
            "lapa_gate": rel(lapa_gate_path),
            "lapa_gate_sha256": sha256(lapa_gate_path),
        },
        "region_decisions": decisions,
        "fully_supported_regions": [item["region"] for item in fully_supported],
        "missing_coverage_regions": [item["region"] for item in missing_coverage],
        "blocked_regions": [item["region"] for item in blocked],
        "result": (
            "blocked_combined_facial_gold_gate_routes_require_repair"
            if blocked
            else "pass_combined_facial_gold_gate_available_routes_candidate_only"
        ),
        "finding": (
            "Only facial routes supported by both available gold datasets should advance toward target-portrait proof. "
            "Rows blocked by either dataset require repair or a named policy split; rows missing a dataset label need a separate authority."
        ),
        "next_required_action": (
            "Do not return to single generated-portrait mask tuning. Select the next repair from blocked combined-gate rows, "
            "or create a separate policy/authority record for rows whose dataset definitions intentionally differ."
        ),
    }
    evidence_path = QA_DIR / f"{EVIDENCE_ID}.json"
    tracker_path = TRACKER_DIR / f"{EVIDENCE_ID}.json"
    write_json(evidence_path, evidence)
    write_json(tracker_path, evidence)
    print(
        json.dumps(
            {
                "evidence": str(evidence_path),
                "tracker": str(tracker_path),
                "result": evidence["result"],
                "fully_supported_regions": evidence["fully_supported_regions"],
                "blocked_regions": evidence["blocked_regions"],
                "missing_coverage_regions": evidence["missing_coverage_regions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
