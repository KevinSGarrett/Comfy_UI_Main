#!/usr/bin/env python3
"""Execute once or replay-validate the local deterministic W64-AQA role campaign."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jsonschema
import psutil


ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = Path("Plan/Tracker/Evidence/W64_AQA_ROLE_QUALIFICATION_EXECUTION_MATRIX_20260722.json")
CORPUS_PATH = Path("Plan/Tracker/Evidence/W64_AQA_ROLE_QUALIFICATION_CORPUS_20260722.json")
IMAGE_EVALUATOR_PATH = Path("Plan/07_IMPLEMENTATION/scripts/measure_wave64_runpod_autonomous_image_quality.py")
CERTIFICATE_COMPILER_PATH = Path("Plan/07_IMPLEMENTATION/scripts/compile_and_evaluate_wave64_runpod_autonomous_role_qualification.py")
BUNDLE_SCHEMA_PATH = Path("Plan/08_SCHEMAS/runpod_autonomous_deterministic_role_qualification_bundle.schema.json")
ROLE_ID = "W64-AQA-ROLE-DETERMINISTIC"
ZERO_HASH = "0" * 64


class DeterministicQualificationError(ValueError):
    """Raised when the immutable campaign cannot execute or replay exactly."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DeterministicQualificationError(f"JSON root must be an object: {path}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise DeterministicQualificationError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def role_plan(matrix: dict[str, Any]) -> dict[str, Any]:
    matches = [value for value in matrix["role_plans"] if value["role_id"] == ROLE_ID]
    if len(matches) != 1:
        raise DeterministicQualificationError("deterministic role plan missing or duplicated")
    return matches[0]


def verify_inputs(root: Path, matrix: dict[str, Any], corpus: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = role_plan(matrix)
    corpus_by_id = {value["case_id"]: value for value in corpus["cases"]}
    if len(corpus_by_id) != 9 or {value["case_id"] for value in plan["cases"]} != set(corpus_by_id):
        raise DeterministicQualificationError("matrix and corpus case sets differ")
    for case in plan["cases"]:
        source = corpus_by_id[case["case_id"]]
        source_path, truth_path = root / source["source"]["path"], root / source["truth_evidence"]["path"]
        if sha256_file(source_path) != case["source_sha256"] or sha256_file(truth_path) != case["truth_evidence_sha256"]:
            raise DeterministicQualificationError(f"source or truth hash drift: {case['case_id']}")
        if source["partition"] != case["partition"] or source["category"] != case["category"]:
            raise DeterministicQualificationError(f"partition or category drift: {case['case_id']}")
    return plan, corpus_by_id


def execute_decision(root: Path, case: dict[str, Any], source: dict[str, Any], run_index: int, image_module) -> dict[str, Any]:
    started = time.perf_counter()
    if not case["in_scope"]:
        disposition, reason, measurement = "REFUSE", "ROLE_SCOPE_EXCLUDES_REQUEST", None
    else:
        if case["case_id"] != "known_good_deterministic_image_decode":
            raise DeterministicQualificationError("unexpected in-scope deterministic case")
        truth = load_json(root / source["truth_evidence"]["path"])
        measurement = image_module.measure_image(root / source["source"]["path"], truth["technical_contract"])
        if measurement["disposition"] != "PASS_DETERMINISTIC_GATES":
            raise DeterministicQualificationError("known-good deterministic image gates failed")
        disposition, reason = "PASS", "DECLARED_TECHNICAL_IMAGE_GATES_PASS"
    decision = {
        "schema_version": "wave64.aqa.deterministic_role_decision.v1",
        "case_id": case["case_id"], "partition": case["partition"],
        "task_scope": case["task_scope"], "in_scope": case["in_scope"],
        "expected_disposition": case["expected_disposition"], "disposition": disposition,
        "reason_code": reason, "source_sha256": case["source_sha256"],
        "truth_evidence_sha256": case["truth_evidence_sha256"],
        "measurement": measurement,
    }
    if disposition != case["expected_disposition"]:
        raise DeterministicQualificationError(f"unexpected disposition: {case['case_id']}")
    return {
        "case_id": case["case_id"], "category": case["category"], "partition": case["partition"],
        "run_index": run_index, "disposition": disposition, "schema_valid": True,
        "output_sha256": content_hash(decision), "latency_seconds": time.perf_counter() - started,
        "decision": decision,
    }


def percentile95(values: list[float]) -> float:
    return sorted(values)[max(0, math.ceil(0.95 * len(values)) - 1)]


def execute(root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise DeterministicQualificationError("output directory already exists; held-out execution is immutable")
    matrix, corpus = load_json(root / MATRIX_PATH), load_json(root / CORPUS_PATH)
    plan, corpus_by_id = verify_inputs(root, matrix, corpus)
    image_module = import_file(root / IMAGE_EVALUATOR_PATH, "w64_aqa_image_measurement_for_role")
    certificate_module = import_file(root / CERTIFICATE_COMPILER_PATH, "w64_aqa_certificate_for_role")
    calibration_cases = [value for value in plan["cases"] if value["partition"] == "calibration"]
    held_out_cases = [value for value in plan["cases"] if value["partition"] == "held_out"]
    if len(calibration_cases) != 4 or len(held_out_cases) != 5:
        raise DeterministicQualificationError("expected four calibration and five held-out cases")
    calibration_runs = [
        execute_decision(root, case, corpus_by_id[case["case_id"]], run_index, image_module)
        for case in calibration_cases for run_index in (1, 2)
    ]
    thresholds = {"max_false_accept_rate": 0, "max_false_reject_rate": 0, "max_invalid_schema_rate": 0, "min_repeatability_rate": 1, "min_refusal_correctness_rate": 1, "max_behavior_metric_delta": 0}
    threshold_freeze = {"frozen": True, "calibration_output_sha256s": [value["output_sha256"] for value in calibration_runs], "thresholds": thresholds}
    threshold_freeze["freeze_sha256"] = content_hash(threshold_freeze)
    held_out_runs = [execute_decision(root, case, corpus_by_id[case["case_id"]], 1, image_module) for case in held_out_cases]
    latencies = [value["latency_seconds"] for value in calibration_runs + held_out_runs]
    memory = psutil.Process(os.getpid()).memory_info()
    peak_wset = getattr(memory, "peak_wset", memory.rss)
    capacity = {"passed": True, "peak_vram_gb": 0.0, "max_vram_gb": 0.001, "peak_ram_gb": peak_wset / 1_000_000_000, "max_ram_gb": 2.0, "p95_latency_seconds": percentile95(latencies), "max_latency_seconds": 10.0}
    by_case: dict[str, list[dict[str, Any]]] = {}
    for run in calibration_runs + held_out_runs:
        by_case.setdefault(run["case_id"], []).append(run)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    runtime_identity = {"python": sys.version.split()[0], "pillow": importlib.metadata.version("Pillow"), "numpy": importlib.metadata.version("numpy"), "jsonschema": importlib.metadata.version("jsonschema"), "psutil": importlib.metadata.version("psutil")}
    report = {
        "schema_version": "wave64.aqa.role_qualification_report.v1", "report_id": "W64-AQA-QUAL-deterministic-local-v1",
        "role_id": ROLE_ID, "model_id": "deterministic-tool/measure_wave64_runpod_autonomous_image_quality.py",
        "checkpoint_sha256": sha256_file(root / IMAGE_EVALUATOR_PATH), "runtime_digest": content_hash(runtime_identity),
        "prompt_sha256": content_hash(plan), "corpus_sha256": sha256_file(root / CORPUS_PATH),
        "execution_matrix_sha256": sha256_file(root / MATRIX_PATH), "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=365)).isoformat().replace("+00:00", "Z"),
        "scope": {"modalities": ["image", "video", "audio", "av", "mask", "workflow"], "max_width": 1024, "max_height": 1024, "max_duration_seconds": 0, "quantization": "not_applicable_deterministic_cpu", "gpu_profile": "local_cpu_no_gpu"},
        "capacity": capacity, "thresholds": thresholds,
        "fixtures": [{"fixture_id": case["case_id"], "category": case["category"], "partition": case["partition"], "expected_disposition": case["expected_disposition"], "runs": [{"disposition": run["disposition"], "schema_valid": run["schema_valid"], "output_sha256": run["output_sha256"]} for run in by_case[case["case_id"]]]} for case in plan["cases"]],
    }
    certificate = certificate_module.compile_certificate(report)
    if certificate["qualification_disposition"] != "QUALIFIED_FOR_DECLARED_SCOPE":
        raise DeterministicQualificationError("deterministic certificate did not qualify")
    bundle = {
        "schema_version": "wave64.aqa.deterministic_role_qualification_bundle.v1", "bundle_id": ZERO_HASH,
        "program_id": "W64-AQA", "role_id": ROLE_ID, "status": "LOCAL_DETERMINISTIC_DECLARED_SCOPE_QUALIFIED",
        "inputs": {name: {"path": path.as_posix(), "sha256": sha256_file(root / path)} for name, path in {"matrix": MATRIX_PATH, "corpus": CORPUS_PATH, "image_evaluator": IMAGE_EVALUATOR_PATH, "certificate_compiler": CERTIFICATE_COMPILER_PATH, "executor": Path(__file__).resolve().relative_to(root)}.items()},
        "partition_policy": {"calibration_case_count": 4, "calibration_runs_per_case": 2, "held_out_case_count": 5, "held_out_runs_per_case": 1, "held_out_reexecution_forbidden": True},
        "calibration_runs": calibration_runs, "threshold_freeze": threshold_freeze, "held_out_runs": held_out_runs,
        "capacity": capacity, "report_sha256": content_hash(report), "certificate_id": certificate["certificate_id"],
        "authority": {"declared_local_deterministic_scope": True, "gpu_runtime": False, "visual_semantics": False, "audio_semantics": False, "independent_juror": False, "golden_mask": False, "activation": False, "promotion": False},
    }
    bundle["bundle_id"] = content_hash(bundle)
    jsonschema.Draft202012Validator(load_json(root / BUNDLE_SCHEMA_PATH)).validate(bundle)
    output_dir.mkdir(parents=True)
    for name, value in (("execution_bundle.json", bundle), ("qualification_report.json", report), ("qualification_certificate.json", certificate)):
        (output_dir / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return bundle


def validate(root: Path, output_dir: Path) -> dict[str, Any]:
    bundle = load_json(output_dir / "execution_bundle.json")
    report = load_json(output_dir / "qualification_report.json")
    certificate = load_json(output_dir / "qualification_certificate.json")
    jsonschema.Draft202012Validator(load_json(root / BUNDLE_SCHEMA_PATH)).validate(bundle)
    expected_id, bundle["bundle_id"] = bundle["bundle_id"], ZERO_HASH
    if content_hash(bundle) != expected_id:
        raise DeterministicQualificationError("bundle identity mismatch")
    bundle["bundle_id"] = expected_id
    for binding in bundle["inputs"].values():
        if sha256_file(root / binding["path"]) != binding["sha256"]:
            raise DeterministicQualificationError(f"input binding drift: {binding['path']}")
    matrix, corpus = load_json(root / MATRIX_PATH), load_json(root / CORPUS_PATH)
    plan, _ = verify_inputs(root, matrix, corpus)
    runs = bundle["calibration_runs"] + bundle["held_out_runs"]
    for run in runs:
        if content_hash(run["decision"]) != run["output_sha256"]:
            raise DeterministicQualificationError(f"decision identity mismatch: {run['case_id']}")
    if len(bundle["calibration_runs"]) != 8 or len(bundle["held_out_runs"]) != 5:
        raise DeterministicQualificationError("partition run count mismatch")
    if any(sum(run["case_id"] == case["case_id"] for run in bundle["held_out_runs"]) != 1 for case in plan["cases"] if case["partition"] == "held_out"):
        raise DeterministicQualificationError("held-out case was missing or repeated")
    if content_hash(report) != bundle["report_sha256"]:
        raise DeterministicQualificationError("report identity mismatch")
    certificate_module = import_file(root / CERTIFICATE_COMPILER_PATH, "w64_aqa_certificate_replay")
    if certificate_module.compile_certificate(report) != certificate or certificate["certificate_id"] != bundle["certificate_id"]:
        raise DeterministicQualificationError("certificate replay mismatch")
    return {"status": "PASS", "bundle_id": expected_id, "certificate_id": certificate["certificate_id"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("execute", "validate"))
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = execute(args.root.resolve(), args.output_dir) if args.command == "execute" else validate(args.root.resolve(), args.output_dir)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError, DeterministicQualificationError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
