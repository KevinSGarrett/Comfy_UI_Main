#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sample_ids(gate: dict[str, Any]) -> list[str]:
    benchmark_path = Path(str(gate["benchmark_evidence"]))
    benchmark = read_json(benchmark_path)
    return [str(sample["sample_id"]) for sample in benchmark.get("sample_results", [])]


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_ids = sample_ids(baseline)
    candidate_ids = sample_ids(candidate)
    if baseline_ids != candidate_ids:
        raise ValueError(f"controlled_sample_ids_mismatch:{baseline_ids}!={candidate_ids}")
    baseline_records = {record["class_name"]: record for record in baseline["class_gate_records"]}
    candidate_records = {record["class_name"]: record for record in candidate["class_gate_records"]}
    if set(baseline_records) != set(candidate_records):
        raise ValueError("class_set_mismatch")
    baseline_passed = set(baseline.get("passed_classes", []))
    candidate_passed = set(candidate.get("passed_classes", []))
    baseline_record_passed = {name for name, record in baseline_records.items() if bool(record["gate_pass"])}
    candidate_record_passed = {name for name, record in candidate_records.items() if bool(record["gate_pass"])}
    if baseline_passed != baseline_record_passed:
        raise ValueError("baseline_passed_classes_inconsistent_with_records")
    if candidate_passed != candidate_record_passed:
        raise ValueError("candidate_passed_classes_inconsistent_with_records")

    class_deltas: list[dict[str, Any]] = []
    comparable_deltas: list[float] = []
    for class_name in sorted(baseline_records):
        old = baseline_records[class_name]
        new = candidate_records[class_name]
        old_iou = old.get("aggregate_iou")
        new_iou = new.get("aggregate_iou")
        delta = None if old_iou is None or new_iou is None else float(new_iou) - float(old_iou)
        if delta is not None:
            comparable_deltas.append(delta)
        class_deltas.append(
            {
                "class_name": class_name,
                "baseline_iou": old_iou,
                "candidate_iou": new_iou,
                "iou_delta": delta,
                "baseline_gate_pass": bool(old["gate_pass"]),
                "candidate_gate_pass": bool(new["gate_pass"]),
                "newly_passed": not bool(old["gate_pass"]) and bool(new["gate_pass"]),
                "regressed_from_pass": bool(old["gate_pass"]) and not bool(new["gate_pass"]),
            }
        )

    newly_passed = [record["class_name"] for record in class_deltas if record["newly_passed"]]
    pass_regressions = [record["class_name"] for record in class_deltas if record["regressed_from_pass"]]
    improved = len(candidate_passed) > len(baseline_passed) and not pass_regressions
    candidate_fully_passed = not candidate.get("blocked_classes")
    if improved and candidate_fully_passed:
        classification = "FACIAL_NATIVE_SCALE_ROUTE_IMPROVED_FULL_GATE_PASS"
    elif improved:
        classification = "FACIAL_NATIVE_SCALE_ROUTE_IMPROVED_REMAINS_BLOCKED"
    else:
        classification = "FACIAL_ROUTE_COMPARISON_NO_ACCEPTABLE_IMPROVEMENT"
    return {
        "controlled_sample_ids": baseline_ids,
        "baseline_pass_count": len(baseline_passed),
        "candidate_pass_count": len(candidate_passed),
        "pass_count_delta": len(candidate_passed) - len(baseline_passed),
        "newly_passed_classes": newly_passed,
        "previously_passing_classes_regressed": pass_regressions,
        "mean_comparable_iou_delta": (
            sum(comparable_deltas) / len(comparable_deltas) if comparable_deltas else None
        ),
        "comparable_iou_class_count": len(comparable_deltas),
        "class_deltas": class_deltas,
        "candidate_route_improved": improved,
        "candidate_route_fully_passed": candidate_fully_passed,
        "classification": classification,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two controlled facial gold gate results.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tracker-out", required=True)
    args = parser.parse_args()
    baseline_path = Path(args.baseline).resolve()
    candidate_path = Path(args.candidate).resolve()
    baseline = read_json(baseline_path)
    candidate = read_json(candidate_path)
    evidence = compare(baseline, candidate)
    evidence.update(
        {
            "baseline_gate": str(baseline_path),
            "baseline_gate_sha256": sha256_file(baseline_path),
            "candidate_gate": str(candidate_path),
            "candidate_gate_sha256": sha256_file(candidate_path),
            "candidate_blocked_classes": candidate.get("blocked_classes", []),
            "promotion_authorized": False,
            "certification_authorized": False,
        }
    )
    write_json(Path(args.out).resolve(), evidence)
    write_json(Path(args.tracker_out).resolve(), evidence)
    print(json.dumps({key: evidence[key] for key in (
        "classification", "pass_count_delta", "newly_passed_classes", "candidate_blocked_classes"
    )}, indent=2))
    return 0 if evidence["candidate_route_improved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
