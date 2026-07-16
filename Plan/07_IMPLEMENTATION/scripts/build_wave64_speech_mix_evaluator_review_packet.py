#!/usr/bin/env python3
"""Build the bounded Wave64 Rows139, 141, and 143 speech review packet."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any


SOURCE_SHA256 = "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815"
SPATIAL_SHA256 = "a85e855969e49c59007fd9c77d33dd76cb269096ec11d2ff1ae56d3a5c959555"
TRANSCRIPT = "We hold the frame steady and move on the beat."
TARGET_RATE = 16000
RUN_ID = "w64_rows139_141_143_l01_mix_001"
SCENE_ID = "scene_l01_diagnostic"
SHOT_ID = "shot_l01_spatial"
TAKE_ID = "take_seed12401_mix001"


class PacketError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bind(path: Path, expected_sha256: str | None = None, label: str = "artifact") -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise PacketError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if expected_sha256 and observed != expected_sha256.lower():
        raise PacketError(f"{label} SHA-256 mismatch: {observed}")
    return {"path": str(path), "sha256": observed, "bytes": path.stat().st_size}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise PacketError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json_new(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        raise PacketError(f"immutable output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, ensure_ascii=True, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)
    return bind(path)


def resample_channels(audio, source_rate: int, target_rate: int = TARGET_RATE):
    import numpy as np
    from scipy.signal import resample_poly

    if audio.ndim != 2 or audio.size == 0 or not np.isfinite(audio).all():
        raise PacketError("audio must be finite and two-dimensional")
    if source_rate <= 0 or target_rate <= 0:
        raise PacketError("sample rates must be positive")
    if source_rate == target_rate:
        return audio.astype(np.float32, copy=True)
    divisor = math.gcd(int(source_rate), int(target_rate))
    channels = [
        resample_poly(audio[:, index], target_rate // divisor, source_rate // divisor).astype(np.float32)
        for index in range(audio.shape[1])
    ]
    length = min(channel.size for channel in channels)
    return np.column_stack([channel[:length] for channel in channels]).astype(np.float32)


def build_stems(dry_source: Path, spatial_source: Path, output_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    import numpy as np
    import soundfile as sf
    from scipy.signal import butter, sosfilt

    output_dir.mkdir(parents=True, exist_ok=True)
    dry_raw, dry_rate = sf.read(str(dry_source), dtype="float32", always_2d=True)
    spatial_raw, spatial_rate = sf.read(str(spatial_source), dtype="float32", always_2d=True)
    dry_mono = dry_raw.mean(axis=1, keepdims=True)
    dry_stereo = resample_channels(np.repeat(dry_mono, 2, axis=1), int(dry_rate))
    spatial_stereo = resample_channels(spatial_raw, int(spatial_rate))
    count = min(dry_stereo.shape[0], spatial_stereo.shape[0])
    dry_stereo = dry_stereo[:count]
    spatial_stereo = spatial_stereo[:count]
    if count < TARGET_RATE:
        raise PacketError("source speech is unexpectedly short")

    generator = np.random.default_rng(139141143)
    noise = generator.standard_normal((count, 2)).astype(np.float64)
    shaped = sosfilt(butter(3, 950.0, btype="lowpass", fs=TARGET_RATE, output="sos"), noise, axis=0)
    shaped_rms = float(np.sqrt(np.mean(np.square(shaped))))
    if shaped_rms <= 0.0:
        raise PacketError("room-tone generator produced zero energy")
    ambience = (shaped * (0.0022 / shaped_rms)).astype(np.float32)
    previous = (ambience * 0.995).astype(np.float32)
    current = (ambience * 1.005).astype(np.float32)
    final_mix = (spatial_stereo + ambience).astype(np.float32)
    if float(np.max(np.abs(final_mix))) >= 0.98:
        raise PacketError("sample-sum final mix would clip")

    values = {
        "dry_dialogue": dry_stereo,
        "spatial_dialogue": spatial_stereo,
        "ambience_bed": ambience,
        "final_mix": final_mix,
        "previous_ambience": previous,
        "current_ambience": current,
    }
    bindings: dict[str, dict[str, Any]] = {}
    for name, audio in values.items():
        path = output_dir / f"{name}_pcm24_stereo_16k.wav"
        if path.exists():
            raise PacketError(f"immutable stem already exists: {path}")
        sf.write(str(path), audio, TARGET_RATE, subtype="PCM_24")
        decoded, observed_rate = sf.read(str(path), dtype="float32", always_2d=True)
        if observed_rate != TARGET_RATE or decoded.shape != audio.shape or not np.isfinite(decoded).all():
            raise PacketError(f"stem decode verification failed: {name}")
        bindings[name] = {**bind(path), "sample_rate_hz": TARGET_RATE, "channels": 2, "samples_per_channel": count, "subtype": "PCM_24"}
    metadata = {
        "sample_rate_hz": TARGET_RATE,
        "channels": 2,
        "samples_per_channel": count,
        "duration_seconds": round(count / TARGET_RATE, 9),
        "ambience_method": "deterministic_seeded_lowpass_room_tone_v1",
        "ambience_seed": 139141143,
        "mix_method": "sample_sum_spatial_dialogue_plus_ambience_v1",
        "gain_or_normalization_applied_to_final_mix": False,
    }
    return bindings, metadata


def make_wave31_manifests(output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    spatial = {
        "mix_id": "mix_l01_001",
        "scene_id": SCENE_ID,
        "shot_id": SHOT_ID,
        "audio_events": ["dialogue_l01", "quiet_room_tone"],
        "room_profile": "small_soft_room",
        "camera_listener_state": {"camera": "present", "listener": "present"},
        "spatial_layers": [{
            "source_id": "qwen_l01_dialogue",
            "pan": -0.108616,
            "gain": 0.5,
            "distance": 1.0,
            "reverb_profile": "short_warm_room",
            "occlusion_profile": "lowpass_4200hz",
            "sync_time": 0.0,
        }],
        "qa_scores": {"spatial_automated": 1.0, "human_playback": None},
        "promotion_decision": "hold",
        "run_id": RUN_ID,
        "take_id": TAKE_ID,
        "is_synthetic": True,
    }
    room = {
        "room_profile_id": "small_soft_room",
        "environment_type": "interior",
        "room_size": "small",
        "surface_materials": ["fabric", "carpet", "soft_furniture"],
        "furniture_density": "medium",
        "reverb_profile": "short_warm_room",
        "ambience_profile": "deterministic_quiet_room_tone_diagnostic",
        "run_id": RUN_ID,
        "scene_id": SCENE_ID,
        "shot_id": SHOT_ID,
        "take_id": TAKE_ID,
        "is_synthetic": True,
    }
    spatial_binding = write_json_new(output_dir / "wave31_spatial_audio_mix_manifest.json", spatial)
    room_binding = write_json_new(output_dir / "wave31_room_acoustics_manifest.json", room)
    return spatial_binding, room_binding


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.project_root.resolve()
    if root != Path("C:/Comfy_UI_Main").resolve():
        raise PacketError("project root must be C:/Comfy_UI_Main")
    dry_source = args.dry_source.resolve()
    spatial_source = args.spatial_source.resolve()
    source_before = bind(dry_source, SOURCE_SHA256, "immutable L01 dry source")
    spatial_before = bind(spatial_source, SPATIAL_SHA256, "immutable Row138 spatial source")
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise PacketError(f"immutable output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    optional_dir = output_dir / "optional_authority_inputs"
    optional_dir.mkdir()

    stems, stem_metadata = build_stems(dry_source, spatial_source, output_dir)
    spatial_manifest, room_manifest = make_wave31_manifests(output_dir)
    producer_path = root / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_spatial_room_evidence_bundle.py"
    evaluator_path = root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_spatial_room_evidence.py"
    review_path = root / "Plan/07_IMPLEMENTATION/scripts/prepare_wave64_human_audio_review.py"
    producer = load_module(producer_path, "wave64_spatial_room_bundle_for_speech")
    evaluator = load_module(evaluator_path, "wave64_spatial_room_evaluator_for_speech")
    review = load_module(review_path, "wave64_human_review_for_speech")

    request_path = output_dir / "row139_spatial_room_evidence_bundle.json"
    producer_args = SimpleNamespace(
        root=str(root), spatial_mix=spatial_manifest["path"], room_acoustics=room_manifest["path"],
        dry_dialogue=stems["dry_dialogue"]["path"], spatial_dialogue=stems["spatial_dialogue"]["path"],
        ambience_bed=stems["ambience_bed"]["path"], final_mix=stems["final_mix"]["path"],
        previous_ambience=stems["previous_ambience"]["path"], current_ambience=stems["current_ambience"]["path"],
        optional_dir=str(optional_dir), output=str(request_path), run_id=RUN_ID, scene_id=SCENE_ID,
        shot_id=SHOT_ID, take_id=TAKE_ID, listener_position="0,0,0", camera_position="0.2,0,0",
        camera_right="1,0,0", camera_forward="0,1,0", source_position="-0.109,0.994,0",
        production_input=False,
    )
    producer.produce(producer_args)
    request_binding = bind(request_path)

    evaluator_output = output_dir / "row141_spatial_room_evaluator_report.json"
    evaluator_code = evaluator.evaluate(root, request_path, evaluator_output)
    if evaluator_code not in (0, 2) or not evaluator_output.is_file():
        raise PacketError("strict spatial-room evaluator did not emit a report")
    evaluator_binding = bind(evaluator_output)
    evaluator_report = json.loads(evaluator_output.read_text(encoding="utf-8"))
    expected_automated_pass = all(
        evaluator_report["gates"][name]["status"] == "PASS"
        for name in ("ambience_continuity", "mix_balance_review")
    )
    if not expected_automated_pass:
        raise PacketError("Row139 ambience or mix automated gate did not pass")
    if evaluator_report.get("overall_pass") is not False:
        raise PacketError("synthetic packet improperly passed the global spatial-room authority gate")

    review_request_path = output_dir / "row143_human_playback_review_request.json"
    review_args = SimpleNamespace(
        artifact=stems["final_mix"]["path"], media_type="audio",
        review_id="W64-SPEECH-L01-SPATIAL-MIX-HUMAN-REVIEW-001", expected_transcript=TRANSCRIPT,
        character_id="UNASSIGNED_REFERENCE_POOL", voice_profile_id="W64_QWEN3_BASE_ICL_DIAGNOSTIC",
        emotion_class=None, delivery_style="controlled", intensity="moderate",
        pace_wpm=187.5, duration_target_seconds=stem_metadata["duration_seconds"], sync_required=False,
        engine_identity_hidden_initial_pass=True,
        automated_evidence=[
            str(args.row138_evaluation.resolve()), str(args.row135_alignment.resolve()), str(evaluator_output),
        ],
    )
    review_payload = review.build_request(review_args)
    review_binding = write_json_new(review_request_path, review_payload)

    source_after = bind(dry_source, SOURCE_SHA256, "immutable L01 dry source after packet")
    spatial_after = bind(spatial_source, SPATIAL_SHA256, "immutable Row138 spatial source after packet")
    if source_after != source_before or spatial_after != spatial_before:
        raise PacketError("source media changed during packet construction")
    manifest = {
        "schema_version": "1.0",
        "artifact_type": "wave64_speech_mix_evaluator_review_packet_manifest",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "classification": "W64_ROWS139_141_143_PACKET_PREPARED_PRODUCTION_AUTHORITY_BLOCKED",
        "source_bindings": {"dry_l01": source_before, "row138_spatial": spatial_before},
        "source_media_unchanged": True,
        "stems": stems,
        "stem_metadata": stem_metadata,
        "wave31_manifests": {"spatial_mix": spatial_manifest, "room_acoustics": room_manifest},
        "row139": {
            "status": "Blocked_Independent_Full_Duration_Playback_And_Production_Mix_Authority_Pending",
            "spatial_room_request": request_binding,
            "ambience_continuity_gate_pass": True,
            "mix_balance_gate_pass": True,
            "row_complete": False,
        },
        "row141": {
            "status": "Blocked_Mandatory_Ensemble_Assets_And_Production_Authority_Pending",
            "strict_evaluator_report": evaluator_binding,
            "spatial_room_evaluator_executed": True,
            "mandatory_ensemble_complete": False,
            "row_complete": False,
        },
        "row143": {
            "status": "Blocked_Real_Human_Playback_Record_Pending_Request_Packet_Pass",
            "human_review_request": review_binding,
            "request_schema_valid": True,
            "human_review_record_present": False,
            "human_playback_proof_present": False,
            "row_complete": False,
        },
        "implementation": {
            "packet_builder": bind(Path(__file__).resolve()),
            "spatial_room_producer": bind(producer_path),
            "spatial_room_evaluator": bind(evaluator_path),
            "human_review_request_producer": bind(review_path),
        },
        "boundaries": {
            "is_synthetic": True,
            "automated_metrics_are_human_review": False,
            "human_review_fabricated": False,
            "production_runtime_proof_present": False,
            "production_authority_present": False,
            "production_ready": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
        },
    }
    manifest_binding = write_json_new(output_dir / "wave64_speech_mix_evaluator_review_packet_manifest.json", manifest)
    return {
        "classification": manifest["classification"],
        "manifest": manifest_binding,
        "final_mix": stems["final_mix"],
        "strict_evaluator": evaluator_binding,
        "human_review_request": review_binding,
        "strict_evaluator_overall_pass": evaluator_report["overall_pass"],
        "strict_evaluator_blockers": evaluator_report["blockers"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--dry-source", type=Path, required=True)
    parser.add_argument("--spatial-source", type=Path, required=True)
    parser.add_argument("--row138-evaluation", type=Path, required=True)
    parser.add_argument("--row135-alignment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(json.dumps({"classification": "W64_ROWS139_141_143_PACKET_FAILED", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
