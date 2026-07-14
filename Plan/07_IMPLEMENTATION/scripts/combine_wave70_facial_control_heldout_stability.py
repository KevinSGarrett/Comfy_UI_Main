#!/usr/bin/env python3
"""Combine controlled and held-out facial class gates without promoting a route."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_path(project_root: Path, value: str) -> Path:
    candidate = Path(value.replace("\\", "/"))
    path = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError(f"source_path_outside_project:{value}") from exc
    return path


def records_by_class(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = gate.get("class_gate_records")
    if not isinstance(records, list) or not records:
        raise ValueError("class_gate_records_missing")
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        name = str(record.get("class_name", "")).strip()
        if not name or name in indexed:
            raise ValueError(f"invalid_or_duplicate_class:{name}")
        indexed[name] = record
    return indexed


def combine_class_records(
    control: dict[str, dict[str, Any]], heldout: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    if set(control) != set(heldout):
        missing_control = sorted(set(heldout) - set(control))
        missing_heldout = sorted(set(control) - set(heldout))
        raise ValueError(
            f"class_coverage_mismatch:missing_control={missing_control}:"
            f"missing_heldout={missing_heldout}"
        )
    decisions: list[dict[str, Any]] = []
    for class_name in sorted(control):
        control_record = control[class_name]
        heldout_record = heldout[class_name]
        control_pass = control_record.get("gate_pass") is True
        heldout_pass = heldout_record.get("gate_pass") is True
        control_empty = control_record.get("gold_empty_all_samples") is True
        heldout_empty = heldout_record.get("gold_empty_all_samples") is True
        if control_pass and heldout_pass:
            if control_empty != heldout_empty:
                classification = "split_presence_inconsistent_blocked"
            elif control_empty:
                classification = "cross_split_empty_only_specificity_evidence"
            else:
                classification = "cross_split_nonempty_candidate_evidence"
        elif control_pass != heldout_pass:
            classification = "split_inconsistent_blocked"
        else:
            classification = "failed_both_splits_blocked"
        decisions.append(
            {
                "class_name": class_name,
                "classification": classification,
                "control": {
                    "gate_pass": control_pass,
                    "aggregate_iou": control_record.get("aggregate_iou"),
                    "false_positive_ratio_vs_gold": control_record.get(
                        "false_positive_ratio_vs_gold"
                    ),
                    "false_negative_ratio_vs_gold": control_record.get(
                        "false_negative_ratio_vs_gold"
                    ),
                    "gold_empty_all_samples": control_empty,
                    "failed_reasons": control_record.get("failed_reasons", []),
                },
                "heldout": {
                    "gate_pass": heldout_pass,
                    "aggregate_iou": heldout_record.get("aggregate_iou"),
                    "false_positive_ratio_vs_gold": heldout_record.get(
                        "false_positive_ratio_vs_gold"
                    ),
                    "false_negative_ratio_vs_gold": heldout_record.get(
                        "false_negative_ratio_vs_gold"
                    ),
                    "gold_empty_all_samples": heldout_empty,
                    "failed_reasons": heldout_record.get("failed_reasons", []),
                },
                "promotion_authorized": False,
                "certification_authorized": False,
            }
        )
    return decisions


def benchmark_binding(
    project_root: Path, gate_path: Path, gate: dict[str, Any]
) -> tuple[Path, dict[str, Any], list[str]]:
    benchmark_path = project_path(project_root, str(gate.get("benchmark_evidence", "")))
    if not benchmark_path.is_file():
        raise ValueError(f"benchmark_missing:{benchmark_path}")
    observed = sha256(benchmark_path)
    if observed.lower() != str(gate.get("benchmark_sha256", "")).lower():
        raise ValueError(f"benchmark_hash_mismatch:{gate_path}")
    benchmark = load_json(benchmark_path)
    if benchmark.get("status") != "pass" or benchmark.get("fail_closed_events"):
        raise ValueError(f"benchmark_not_pass:{benchmark_path}")
    sample_ids = [str(sample.get("sample_id")) for sample in benchmark.get("sample_results", [])]
    if len(sample_ids) < 3 or len(sample_ids) != len(set(sample_ids)):
        raise ValueError(f"invalid_sample_ids:{benchmark_path}")
    return benchmark_path, benchmark, sample_ids


def build_evidence(args: argparse.Namespace) -> dict[str, Any]:
    project_root = args.project_root.resolve()
    control_gate_path = args.control_gate.resolve()
    heldout_gate_path = args.heldout_gate.resolve()
    control_gate = load_json(control_gate_path)
    heldout_gate = load_json(heldout_gate_path)
    for role, gate in (("control", control_gate), ("heldout", heldout_gate)):
        if gate.get("mask_promoted") is not False or gate.get("certification_authorized") is not False:
            raise ValueError(f"{role}_gate_claim_boundary_invalid")
    if control_gate.get("thresholds") != heldout_gate.get("thresholds"):
        raise ValueError("gate_threshold_mismatch")

    control_benchmark_path, _, control_ids = benchmark_binding(
        project_root, control_gate_path, control_gate
    )
    heldout_benchmark_path, _, heldout_ids = benchmark_binding(
        project_root, heldout_gate_path, heldout_gate
    )
    overlap = sorted(set(control_ids) & set(heldout_ids))
    if overlap:
        raise ValueError(f"control_heldout_sample_overlap:{overlap}")

    decisions = combine_class_records(
        records_by_class(control_gate), records_by_class(heldout_gate)
    )
    stable_nonempty = [
        item["class_name"]
        for item in decisions
        if item["classification"] == "cross_split_nonempty_candidate_evidence"
    ]
    stable_empty = [
        item["class_name"]
        for item in decisions
        if item["classification"] == "cross_split_empty_only_specificity_evidence"
    ]
    split_inconsistent = [
        item["class_name"]
        for item in decisions
        if item["classification"] == "split_inconsistent_blocked"
    ]
    split_presence_inconsistent = [
        item["class_name"]
        for item in decisions
        if item["classification"] == "split_presence_inconsistent_blocked"
    ]
    failed_both = [
        item["class_name"]
        for item in decisions
        if item["classification"] == "failed_both_splits_blocked"
    ]
    stamp = args.timestamp.replace("-", "").replace(":", "")
    return {
        "schema_version": "1.0",
        "evidence_id": f"FACIAL-CONTROL-HELDOUT-CLASS-STABILITY-{stamp}",
        "timestamp": args.timestamp,
        "result": "cross_split_candidate_classes_identified_full_route_blocked",
        "classification": "FACIAL_CLASS_STABILITY_EVIDENCE_ONLY_NO_PROMOTION",
        "source_gates": {
            "control": {
                "path": control_gate_path.relative_to(project_root).as_posix(),
                "sha256": sha256(control_gate_path),
                "benchmark_path": control_benchmark_path.relative_to(project_root).as_posix(),
                "benchmark_sha256": sha256(control_benchmark_path),
                "sample_ids": control_ids,
            },
            "heldout": {
                "path": heldout_gate_path.relative_to(project_root).as_posix(),
                "sha256": sha256(heldout_gate_path),
                "benchmark_path": heldout_benchmark_path.relative_to(project_root).as_posix(),
                "benchmark_sha256": sha256(heldout_benchmark_path),
                "sample_ids": heldout_ids,
            },
        },
        "thresholds": control_gate["thresholds"],
        "class_decisions": decisions,
        "cross_split_nonempty_candidate_classes": stable_nonempty,
        "cross_split_empty_only_specificity_classes": stable_empty,
        "split_inconsistent_blocked_classes": split_inconsistent,
        "split_presence_inconsistent_blocked_classes": split_presence_inconsistent,
        "failed_both_splits_blocked_classes": failed_both,
        "claim_boundary": {
            "production_route_promoted": False,
            "mask_promoted": False,
            "certification_authorized": False,
            "stable_class_deployment_authorized": False,
            "body_mask_dependency_cleared": False,
            "wave70_hard_gate_rerun": False,
            "wave71_activation_authorized": False,
        },
        "next_action": (
            "Use the cross-split decision as route-repair prioritization only. Preserve stable "
            "nonempty classes while repairing split-inconsistent and failed-both classes through "
            "a distinct originals-only implementation hypothesis."
        ),
        "process_exit_contract": {
            "0": "all classes pass both controlled and held-out gates and a separate promotion gate passes",
            "1": "source validation or combination failed",
            "2": "cross-split evidence is valid but the full route remains blocked",
            "current_exit_code": 2,
        },
        "boundaries": [
            "No model inference or prediction regeneration occurred.",
            "Gold annotations remained evaluator-side; this combiner reads only completed benchmark and gate evidence.",
            "No body mask, contact, Wave70 hard gate, Wave71+, Jira, AWS, or EC2 action occurred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--control-gate", required=True, type=Path)
    parser.add_argument("--heldout-gate", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--tracker-out", required=True, type=Path)
    parser.add_argument(
        "--timestamp", default=datetime.now().astimezone().isoformat(timespec="seconds")
    )
    args = parser.parse_args()
    evidence = build_evidence(args)
    payload = json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    for output in (args.out, args.tracker_out):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
