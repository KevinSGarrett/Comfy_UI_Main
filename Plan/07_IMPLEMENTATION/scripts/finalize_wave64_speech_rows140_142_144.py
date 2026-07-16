#!/usr/bin/env python3
"""Package Wave64 overlap/adversarial/promotion controls and reconcile Rows140/142/144."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_CLASSIFICATION = "W64_ROWS140_142_144_CONTROLS_EXECUTED_PRODUCTION_BLOCKED"
ROW_STATUS = {
    "140": "Blocked_Independent_Diarization_Intelligibility_And_Playback_Authority_Pending_Overlap_Diagnostic_Pass",
    "142": "Blocked_Full_Adversarial_Corpus_Coverage_Pending_Immutable_Defect_Matrix_Pass",
    "144": "Blocked_Complete_Authority_And_Production_Review_Pending_Atomic_Promotion_Control_Pass",
}
ROW_BLOCKERS = {
    "140": [
        "independent overlap diarization and intelligibility evidence is missing",
        "human full-play review and production authority are missing",
    ],
    "142": [
        "hallucination, repetition, truncation-defect, difficult-text, identity-drift, noise, reverb, and multilingual fixtures are not yet covered",
    ],
    "144": [
        "every current speech candidate lacks complete playback and final-production authority",
        "no current candidate satisfies all promotion hard gates",
    ],
}


class FinalizationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise FinalizationError(f"required file is missing: {path}")
    return {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise FinalizationError(f"JSON root must be an object: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def require_bound_file(record: dict[str, Any], label: str) -> Path:
    path = Path(str(record.get("path", ""))).resolve()
    observed = binding(path)
    if observed["sha256"] != record.get("sha256") or observed["bytes"] != record.get("bytes"):
        raise FinalizationError(f"{label} binding mismatch")
    return path


def copy_exact(source: Path, destination: Path) -> dict[str, Any]:
    source_binding = binding(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(destination) != source_binding["sha256"]:
            raise FinalizationError(f"durable artifact hash conflict: {destination}")
    else:
        shutil.copy2(source, destination)
    durable = binding(destination)
    if durable["sha256"] != source_binding["sha256"]:
        raise FinalizationError(f"durable artifact copy mismatch: {destination}")
    return durable


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Path]:
    if manifest.get("classification") != EXPECTED_CLASSIFICATION:
        raise FinalizationError("runtime classification is invalid")
    if manifest.get("source_hashes_unchanged") is not True or manifest.get("row_complete") is not False:
        raise FinalizationError("source immutability or row boundary is invalid")
    overlap = manifest.get("overlap", {})
    gates = overlap.get("gates", {})
    required_true = (
        "source_ownership_from_isolated_stems_pass",
        "overlap_interval_present_pass",
        "priority_duck_pass",
        "spatial_separation_pass",
        "sample_sum_integrity_pass",
        "technical_clipping_pass",
    )
    if any(gates.get(name) is not True for name in required_true):
        raise FinalizationError("overlap technical gate is not passing")
    required_false = (
        "independent_diarization_pass",
        "independent_overlap_intelligibility_pass",
        "human_playback_review_pass",
        "production_authority_pass",
    )
    if any(gates.get(name) is not False for name in required_false):
        raise FinalizationError("overlap authority gate does not fail closed")
    matrix = manifest.get("adversarial_matrix", {})
    if matrix.get("known_fixture_detection_pass") is not True or matrix.get("known_fixture_detection_rate") != 1.0:
        raise FinalizationError("known immutable defect detection is incomplete")
    if matrix.get("full_required_category_coverage_pass") is not False or matrix.get("candidate_media_mutated") is not False:
        raise FinalizationError("adversarial coverage or media boundary is invalid")
    promotion = manifest.get("promotion_control", {})
    probe = promotion.get("synthetic_non_media_control_probe", {})
    if promotion.get("all_current_candidates_refused_pass") is not True or promotion.get("production_promotion_performed") is not False:
        raise FinalizationError("current candidate promotion boundary is invalid")
    for field in ("atomic_write_pass", "idempotent_replay_pass", "revocation_invalidation_pass", "rollback_pass"):
        if probe.get(field) is not True:
            raise FinalizationError(f"promotion control probe failed: {field}")
    if probe.get("production_candidate") is not False or probe.get("media_promotion_performed") is not False:
        raise FinalizationError("synthetic control probe was represented as production media")
    boundaries = manifest.get("boundaries", {})
    for field in (
        "candidate_regenerated", "candidate_media_mutated", "human_review_fabricated",
        "production_promotion_performed", "ec2_started", "s3_mutated", "mask_or_wave71_touched",
        "jira_mutated", "content_based_suppression",
    ):
        if boundaries.get(field) is not False:
            raise FinalizationError(f"runtime boundary is invalid: {field}")
    paths: dict[str, Path] = {}
    for name, record in manifest.get("overlap_artifacts", {}).items():
        paths[name] = require_bound_file(record, f"overlap artifact {name}")
    paths["immutable_adversarial_defect_matrix"] = require_bound_file(matrix.get("binding", {}), "adversarial matrix")
    paths["promotion_gate_decisions"] = require_bound_file(promotion.get("binding", {}), "promotion decisions")
    paths["promotion_control_probe"] = require_bound_file(probe.get("probe_artifact", {}), "promotion control probe")
    paths["promotion_control_probe_ledger"] = require_bound_file(probe.get("ledger", {}), "promotion control probe ledger")
    return paths


def update_rows(path: Path, id_column: str, prefix: str, evidence_root: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if not fieldnames or id_column not in fieldnames:
        raise FinalizationError(f"CSV schema mismatch: {path}")
    found: set[str] = set()
    for row in rows:
        for number, status in ROW_STATUS.items():
            if row[id_column] != f"{prefix}-W64-{number}":
                continue
            found.add(number)
            evidence = f"{evidence_root}/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
            row["Status"] = status
            row["Coverage_Audit_Status"] = "bounded_runtime_control_recorded_exact_remaining_authority_or_corpus_blockers_preserved"
            if "Evidence_Path" in row:
                row["Evidence_Path"] = evidence
            if "Status_Decision" in row:
                row["Status_Decision"] = status.lower()
            row["Notes"] = (
                f"Hash-bound runtime/control evidence is recorded in {evidence}. Existing immutable candidates were reused without regeneration. "
                "Overlap stem ownership, technical mix, known-defect detection, atomic write, idempotent replay, revocation, rollback, and current-candidate refusal gates pass. "
                "Independent overlap listening/diarization, full adversarial corpus coverage, and complete playback/final-production authority remain blocked. "
                "No candidate was promoted. content_based_suppression=false."
            )
    if found != set(ROW_STATUS):
        raise FinalizationError(f"missing expected rows in {path}: {sorted(set(ROW_STATUS) - found)}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def build(root: Path, manifest_path: Path, durable_dir_name: str) -> dict[str, Any]:
    manifest = load_object(manifest_path)
    runtime_paths = validate_manifest(manifest)
    runtime_paths["wave64_rows140_142_144_runtime_manifest"] = manifest_path.resolve()
    durable_dir = root / "Plan/Instructions/Operations/Pulled_Back_Artifacts" / durable_dir_name
    durable = {name: copy_exact(source, durable_dir / source.name) for name, source in runtime_paths.items()}
    runtime = {name: binding(path) for name, path in runtime_paths.items()}
    implementation_paths = {
        "overlap_adversarial_runner": "Plan/07_IMPLEMENTATION/scripts/run_wave64_overlap_adversarial_promotion_control.py",
        "promotion_control": "Plan/07_IMPLEMENTATION/scripts/manage_wave64_speech_promotion.py",
        "finalizer": "Plan/07_IMPLEMENTATION/scripts/finalize_wave64_speech_rows140_142_144.py",
        "runner_tests": "Plan/Instructions/QA/Scripts/test_run_wave64_overlap_adversarial_promotion_control.py",
        "promotion_tests": "Plan/Instructions/QA/Scripts/test_manage_wave64_speech_promotion.py",
        "finalizer_tests": "Plan/Instructions/QA/Scripts/test_finalize_wave64_speech_rows140_142_144.py",
    }
    implementation = {name: binding(root / relative) for name, relative in implementation_paths.items()}
    common = {
        "schema_version": "1.0",
        "runtime_classification": manifest["classification"],
        "runtime_manifest": manifest,
        "runtime_artifacts": runtime,
        "durable_artifacts": durable,
        "implementation": implementation,
        "boundaries": {
            **manifest["boundaries"],
            "row_complete_claimed": False,
            "pass_like_claimed": False,
        },
    }
    capabilities = {
        "140": "deterministic two-source overlap diagnostic with isolated ownership stems, explicit interruption priority ducking, stereo separation, and sample-sum proof",
        "142": "immutable accepted/rejected speech fixture matrix with exact documented defect detection and category-level coverage accounting",
        "144": "atomic promotion ledger with idempotent replay, hash-conflict rejection, reference/model revocation invalidation, rollback, and fail-closed current-candidate refusal",
    }
    gates = {
        "140": manifest["overlap"]["gates"],
        "142": {
            "known_fixture_detection_pass": True,
            "immutable_candidate_hashes_pass": True,
            "full_required_category_coverage_pass": False,
        },
        "144": {
            "atomic_write_control_pass": True,
            "idempotent_replay_control_pass": True,
            "revocation_invalidation_control_pass": True,
            "rollback_control_pass": True,
            "all_current_candidates_refused_pass": True,
            "production_candidate_promotion_pass": False,
            "production_authority_pass": False,
        },
    }
    qa_root = root / "Plan/Instructions/QA/Evidence/Audio_Asset_Intake"
    tracker_root = root / "Plan/Tracker/Evidence/Audio_Asset_Intake"
    for number in ROW_STATUS:
        record = {
            **common,
            "artifact_type": f"wave64_autonomous_hyperreal_speech_row{number}_evidence",
            "row": {
                "item_id": f"ITEM-W64-{number}",
                "tracker_id": f"TRK-W64-{number}",
                "implemented_capability": capabilities[number],
                "status": ROW_STATUS[number],
                "automated_gates": gates[number],
                "blockers": ROW_BLOCKERS[number],
                "pass_like": False,
            },
            "row_complete": False,
        }
        name = f"WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{number}.json"
        write_json_atomic(qa_root / name, record)
        write_json_atomic(tracker_root / name, record)
    update_rows(
        root / "Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv",
        "Item_ID", "ITEM", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake",
    )
    update_rows(
        root / "Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv",
        "Tracker_ID", "TRK", "Plan/Instructions/QA/Evidence/Audio_Asset_Intake",
    )
    return {
        "classification": "W64_ROWS140_142_144_CONTROLS_RECONCILED_PRODUCTION_BLOCKED",
        "durable_artifacts": durable,
        "row_status": ROW_STATUS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--durable-dir-name", required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    manifest_path = args.runtime_manifest.resolve() if args.runtime_manifest.is_absolute() else (root / args.runtime_manifest).resolve()
    try:
        result = build(root, manifest_path, args.durable_dir_name)
    except Exception as exc:
        print(json.dumps({"classification": "W64_ROWS140_142_144_FINALIZATION_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
