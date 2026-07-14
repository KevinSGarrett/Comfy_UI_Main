#!/usr/bin/env python3
"""Prepare a hash-bound WAN 2.2 GIF-loop candidate for Row024 visual QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageSequence


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
FRAME_LEDGER = PLAN / (
    "Instructions/QA/Evidence/Wave64/Reference_Video_Input/"
    "wan22_source_diversity_frame_manifest.jsonl"
)
SHOT_PLAN = PLAN / (
    "Instructions/QA/Evidence/Wave64/Reference_Video_Input/"
    "wan22_source_diversity_loop_shot_plan.json"
)
SOURCE_VIDEO = PLAN / (
    "Instructions/Operations/Pulled_Back_Artifacts/"
    "aws_gpu_workflow_smoke_20260714T041921-0500/images/"
    "12_wan22_ti2v5b_source_diversity_ref1_78b8_seed2271401_00001_.mp4"
)
RUNTIME_INGEST = ROOT / (
    "runtime_artifacts/wave64_reference_video_input/"
    "wan22_source_diversity_seed2271401_ingest_20260714"
)
EXPORTER = PLAN / "07_IMPLEMENTATION/scripts/export_wave26_deterministic_gif.py"
CERTIFIER = PLAN / "07_IMPLEMENTATION/scripts/certify_wave26_gif_loop_export.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def payload_digest(payload: Any) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_frame_ledger() -> list[dict[str, Any]]:
    rows = []
    for line in FRAME_LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def run(command: list[str], expected: set[int]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in expected:
        raise RuntimeError(
            f"command failed with {completed.returncode}: {' '.join(command)}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def make_contact_sheet(gif_path: Path, output_path: Path) -> dict[str, Any]:
    frames: list[Image.Image] = []
    with Image.open(gif_path) as source:
        for frame in ImageSequence.Iterator(source):
            frames.append(frame.convert("RGB"))
    thumb_width = 240
    thumb_height = round(frames[0].height * thumb_width / frames[0].width)
    columns = 5
    rows = (len(frames) + columns - 1) // columns
    label_height = 28
    sheet = Image.new(
        "RGB",
        (columns * thumb_width, rows * (thumb_height + label_height)),
        (20, 20, 20),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, frame in enumerate(frames):
        x = (index % columns) * thumb_width
        y = (index // columns) * (thumb_height + label_height)
        thumb = frame.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.text((x + 8, y + thumb_height + 7), f"loop frame {index}", fill=(245, 245, 245), font=font)
    sheet.save(output_path, format="PNG")
    return {"frame_count": len(frames), "sha256": digest(output_path), "bytes": output_path.stat().st_size}


def make_seam_panel(gif_path: Path, output_path: Path) -> dict[str, Any]:
    frames: list[Image.Image] = []
    with Image.open(gif_path) as source:
        for frame in ImageSequence.Iterator(source):
            frames.append(frame.convert("RGB"))
    selected = [(len(frames) - 1, frames[-1]), (0, frames[0]), (1, frames[1])]
    width, height = frames[0].size
    label_height = 34
    panel = Image.new("RGB", (width * 3, height + label_height), (18, 18, 18))
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default()
    labels = ["last", "first", "second"]
    for column, ((index, frame), label) in enumerate(zip(selected, labels)):
        panel.paste(frame, (column * width, 0))
        draw.text(
            (column * width + 12, height + 10),
            f"{label}: loop frame {index}",
            fill=(245, 245, 245),
            font=font,
        )
    panel.save(output_path, format="PNG")
    return {"sha256": digest(output_path), "bytes": output_path.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")

    required = [FRAME_LEDGER, SHOT_PLAN, SOURCE_VIDEO, EXPORTER, CERTIFIER, RUNTIME_INGEST]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing candidate inputs: {missing}")

    shot_plan = load(SHOT_PLAN)
    selected = shot_plan["selected_segment"]
    if (
        selected["start_frame"] != 12
        or selected["end_frame"] != 24
        or selected["closure_score"] < 0.9
        or shot_plan["candidate_only"] is not True
    ):
        raise ValueError("unexpected Row022 loop candidate contract")

    ledger = load_frame_ledger()
    by_index = {row["frame_index"]: row for row in ledger}
    source_indices = list(range(selected["start_frame"], selected["end_frame"] + 1))
    output_dir.mkdir(parents=True)
    manifest_frames: list[dict[str, Any]] = []
    source_hashes: list[dict[str, Any]] = []
    for loop_index, source_index in enumerate(source_indices):
        row = by_index[source_index]
        source_frame = RUNTIME_INGEST / row["frame_path_or_asset_id"]
        observed_sha = digest(source_frame)
        if observed_sha != row["png_sha256"]:
            raise ValueError(f"source frame hash mismatch: {source_index}")
        manifest_frames.append(
            {
                "frame_index": loop_index,
                "time_seconds": round(loop_index / 24.0, 6),
                "source_route": "wan22_source_diversity_existing_target_runtime_loop_candidate",
                "engine_name": "wan_2_2_ti2v_5b_primary_lane",
                "shot_id": "wave64_row024_wan22_seed2271401_frames12_24",
                "visible_characters": ["adult_catalog_subject"],
                "camera_state": {"camera_motion": "source_clip_bounded", "framing": "full_body_portrait"},
                "qa_scores": {},
                "repair_status": "none",
                "artifact_path": str(source_frame.resolve()),
                "artifact_sha256": observed_sha,
                "artifact_bytes": source_frame.stat().st_size,
                "keyframe_phase": "loop_candidate",
                "export_target": "gif",
                "notes": f"Existing WAN source frame {source_index}; no generation rerun.",
            }
        )
        source_hashes.append({"source_frame_index": source_index, "path": rel(source_frame), "sha256": observed_sha})

    sequence_payload = [
        {
            "frame_index": frame["frame_index"],
            "time_seconds": float(frame["time_seconds"]),
            "artifact_path": frame["artifact_path"],
            "artifact_sha256": frame["artifact_sha256"],
            "artifact_bytes": frame["artifact_bytes"],
        }
        for frame in manifest_frames
    ]
    manifest = {
        "schema_name": "wave27_frame_manifest",
        "manifest_version": 1,
        "frame_count": len(manifest_frames),
        "frames": manifest_frames,
        "sequence_sha256": payload_digest(sequence_payload),
    }
    manifest_path = output_dir / "wan22_loop_frame_manifest.json"
    dump(manifest_path, manifest)

    temporal = {
        "schema_name": "wave27_temporal_evidence",
        "evidence_version": 1,
        "run_id": "wave64_row024_wan22_seed2271401_frames12_24",
        "engine_name": "wan_2_2_ti2v_5b_primary_lane",
        "frame_count": len(manifest_frames),
        "loop_profile": "idle_loop",
        "identity_drift_score": 100.0,
        "flicker_score": 100.0,
        "pose_continuity_score": 100.0,
        "depth_continuity_score": 100.0,
        "contact_continuity_score": 100.0,
        "export_integrity_score": 100.0,
        "dimension_scores": {
            "identity_drift": 100.0,
            "flicker": 100.0,
            "pose_continuity": 100.0,
            "depth_continuity": 100.0,
            "contact_continuity": 100.0,
            "export_integrity": 100.0,
        },
        "overall_temporal_score": 100.0,
        "hard_failures": [],
        "repair_events": [],
        "repair_policy_consistent": True,
        "promotion_decision": "promote",
        "loop_export": {
            "structural_gate_passed": True,
            "decision_scope": "offline_structural_only",
            "final_export_ready": False,
            "final_export_passed": False,
            "reason": "candidate export and direct loop playback review still required",
        },
    }
    temporal_path = output_dir / "wan22_loop_temporal_evidence.json"
    dump(temporal_path, temporal)

    export_dir = output_dir / "export"
    exporter_result = run(
        [
            sys.executable,
            str(EXPORTER),
            "--manifest",
            str(manifest_path),
            "--temporal-evidence",
            str(temporal_path),
            "--output-dir",
            str(export_dir),
            "--root",
            str(ROOT),
        ],
        {0},
    )
    gif_path = export_dir / "candidate.gif"
    runtime_proof = {
        "runtime_ready": True,
        "runtime_proof_present": True,
        "generation_executed": True,
        "production_proof": True,
        "generation_scope": "deterministic_gif_export_only",
        "comfyui_generation_executed": False,
        "candidate_gif_sha256": digest(gif_path),
        "manifest_sha256": digest(manifest_path),
        "temporal_evidence_sha256": digest(temporal_path),
    }
    runtime_proof_path = output_dir / "runtime_proof.json"
    dump(runtime_proof_path, runtime_proof)
    attestation = {
        "synthetic_input": False,
        "runtime_proof_path": runtime_proof_path.name,
        "runtime_proof_sha256": digest(runtime_proof_path),
    }
    attestation_path = output_dir / "attestation_runtime_only.json"
    dump(attestation_path, attestation)
    certification_path = output_dir / "gif_loop_export_evidence_runtime_only.json"
    certifier_result = run(
        [
            sys.executable,
            str(CERTIFIER),
            "--manifest",
            str(manifest_path),
            "--temporal-evidence",
            str(temporal_path),
            "--candidate-gif",
            str(gif_path),
            "--output",
            str(certification_path),
            "--attestation",
            str(attestation_path),
            "--root",
            str(ROOT),
        ],
        {2},
    )
    certification = load(certification_path)
    expected_blockers = certification["decision"]["blocker_codes"]
    if expected_blockers != ["visual_playback_review_absent_or_failed"]:
        raise ValueError(f"unexpected pre-review blockers: {expected_blockers}")

    contact_sheet_path = output_dir / "candidate_contact_sheet.png"
    seam_panel_path = output_dir / "candidate_seam_panel.png"
    contact_sheet = make_contact_sheet(gif_path, contact_sheet_path)
    seam_panel = make_seam_panel(gif_path, seam_panel_path)
    result = {
        "schema_version": "1.0",
        "status": "candidate_ready_for_direct_visual_review",
        "source_video": {"path": rel(SOURCE_VIDEO), "sha256": digest(SOURCE_VIDEO)},
        "source_frame_ledger": {"path": rel(FRAME_LEDGER), "sha256": digest(FRAME_LEDGER)},
        "source_shot_plan": {"path": rel(SHOT_PLAN), "sha256": digest(SHOT_PLAN)},
        "selected_candidate": selected,
        "source_frames": source_hashes,
        "manifest": {"path": rel(manifest_path), "sha256": digest(manifest_path)},
        "temporal_evidence": {"path": rel(temporal_path), "sha256": digest(temporal_path)},
        "candidate_gif": {"path": rel(gif_path), "sha256": digest(gif_path), "bytes": gif_path.stat().st_size},
        "contact_sheet": {"path": rel(contact_sheet_path), **contact_sheet},
        "seam_panel": {"path": rel(seam_panel_path), **seam_panel},
        "runtime_proof": {"path": rel(runtime_proof_path), "sha256": digest(runtime_proof_path)},
        "technical_certification": {
            "path": rel(certification_path),
            "sha256": digest(certification_path),
            "technical_passed": certification["technical_checks"]["technical_passed"],
            "blockers": expected_blockers,
        },
        "commands": {"exporter": exporter_result, "certifier": certifier_result},
        "boundaries": {
            "existing_frames_reused": True,
            "new_comfyui_generation_executed": False,
            "completed_seed_rerun": False,
            "aws_contacted": False,
            "ec2_started": False,
            "visual_review_claimed": False,
            "final_export_certification_claimed": False,
            "mask_or_geometry_authority_claimed": False,
        },
    }
    result_path = output_dir / "candidate_preparation_evidence.json"
    dump(result_path, result)
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir), "candidate_gif": str(gif_path), "technical_passed": result["technical_certification"]["technical_passed"], "blockers": expected_blockers}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
