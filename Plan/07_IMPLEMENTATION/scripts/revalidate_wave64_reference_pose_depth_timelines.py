#!/usr/bin/env python3
"""Revalidate immutable Row022 runtime outputs under the exact coordinate contract."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_reference_pose_depth_timelines.py"
SPEC = importlib.util.spec_from_file_location("row022_pose_depth_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUNNER)


def verify_prior_outputs(runtime_dir: Path, prior: dict[str, Any]) -> tuple[list[Path], list[Path]]:
    if prior.get("prompt_id") is None or not (runtime_dir / "history.json").is_file():
        raise ValueError("Prior runtime prompt/history proof is missing")
    pose_paths = sorted((runtime_dir / "pose").glob("frame_*.png"))
    depth_paths = sorted((runtime_dir / "depth").glob("frame_*.png"))
    pose_records = RUNNER.read_jsonl(runtime_dir / "pose_timeline.jsonl")
    depth_records = RUNNER.read_jsonl(runtime_dir / "depth_timeline.jsonl")
    if len(pose_paths) != len(pose_records) or len(depth_paths) != len(depth_records):
        raise ValueError("Prior timeline/output counts do not match")
    for path, record in zip(pose_paths, pose_records):
        if RUNNER.sha256(path) != record.get("pose_render_sha256"):
            raise ValueError(f"Prior pose output hash mismatch: {path}")
    for path, record in zip(depth_paths, depth_records):
        if RUNNER.sha256(path) != record.get("depth_render_sha256"):
            raise ValueError(f"Prior depth output hash mismatch: {path}")
    return pose_paths, depth_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timestamp")
    args = parser.parse_args()

    runtime_dir = args.runtime_dir.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Correction output must be empty or absent: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    prior_path = runtime_dir / "runtime_technical_evidence.json"
    prior = RUNNER.read_json(prior_path)
    pose_paths, depth_paths = verify_prior_outputs(runtime_dir, prior)
    source_records = RUNNER.read_jsonl(args.source_manifest)
    requirements = RUNNER.read_json(args.requirements)
    pose_frames = json.loads((runtime_dir / "pose_keypoints.json").read_text(encoding="utf-8"))
    technical = RUNNER.evaluate_timelines(
        source_records, pose_paths, depth_paths, pose_frames, requirements, output_dir
    )
    evidence = {
        "schema_name": "wave64_reference_pose_depth_timeline_coordinate_revalidation",
        "schema_version": "1.0",
        "timestamp": args.timestamp or datetime.now().astimezone().isoformat(timespec="seconds"),
        "tracker_id": RUNNER.TRACKER_ID,
        "item_id": RUNNER.ITEM_ID,
        "result": (
            "pass_pose_and_relative_depth_timelines_target_mask_contact_authority_blocked"
            if technical["technical_pass"]
            else "blocked_pose_or_relative_depth_technical_validation_failed"
        ),
        "prior_runtime_evidence": {
            "path": RUNNER.rel(prior_path),
            "sha256": RUNNER.sha256(prior_path),
            "prompt_id": prior["prompt_id"],
            "result": prior["result"],
            "failed_checks": prior["technical_evaluation"]["failed_checks"],
        },
        "correction": {
            "classification": "PREPROCESSOR_COORDINATE_CONTRACT_CORRECTED_NO_RUNTIME_RERUN",
            "reason": "The initial evaluator incorrectly required source dimensions for deterministic short-edge-scaled render layers. DWPose keypoints already use source coordinates; pose/depth renders use an exact recorded inverse transform.",
            "runtime_rerun": False,
            "source_or_output_bytes_changed": False,
        },
        "source_manifest": {
            "path": RUNNER.rel(args.source_manifest),
            "sha256": RUNNER.sha256(args.source_manifest),
        },
        "runtime_requirements": {
            "path": RUNNER.rel(args.requirements),
            "sha256": RUNNER.sha256(args.requirements),
        },
        "technical_evaluation": technical,
        "authority_boundaries": requirements["authority_boundaries"],
    }
    evidence_path = output_dir / "coordinate_revalidation_evidence.json"
    RUNNER.write_json(evidence_path, evidence)
    print(
        json.dumps(
            {
                "result": evidence["result"],
                "technical_pass": technical["technical_pass"],
                "failed_checks": technical["failed_checks"],
                "evidence": str(evidence_path),
            },
            indent=2,
        )
    )
    return 0 if technical["technical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
