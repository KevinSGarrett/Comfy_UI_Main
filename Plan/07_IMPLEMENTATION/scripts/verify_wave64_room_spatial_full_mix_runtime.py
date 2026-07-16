#!/usr/bin/env python3
"""Verify the existing genuine Wave64 stereo room mix and review mux."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import wave
from array import array
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any


CLASSIFICATION = "W64_ROWS029_030_056_FULL_MIX_TECHNICAL_RUNTIME_PASS_AUTHORITY_BLOCKED"
EXPECTED_MANIFEST_SHA256 = "9eb91fb2c84105b470a27c939babd9ca8537045f3818f01f3187779e354c0a07"
EXPECTED_VIDEO_SHA256 = "5006e96e211538f3d2bb6795e93014d6642946583cc31aa635e171e13e1c80bf"
EXPECTED_MIX_SHA256 = "5a07f0a654499266509453421c3efdc1b2e4ce83b8706e0138ebc4b1d3ad924a"
EXPECTED_MUX_SHA256 = "03b5b55f871d7460c37e97bacd53968d183b0e1adc3022fb2daffc5e056a9b7d"
EXPECTED_FRAMES = 49
EXPECTED_RATE = 48_000
EXPECTED_AUDIO_FRAMES = 97_920
CORRECTED_AUDIO_FRAMES = 97_968
MIX_WEIGHTS = {"voice_stem": 1.0, "foley_stem": 0.16, "ambience_stem": 0.45}


class RuntimeVerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise RuntimeVerificationError(f"required file is missing: {path}")
    actual = sha256_file(path)
    if expected_sha256 and actual != expected_sha256:
        raise RuntimeVerificationError(f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeVerificationError(f"JSON root must be an object: {path}")
    return value


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RuntimeVerificationError(f"immutable output already exists: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=True, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_pcm16_stereo(path: Path) -> tuple[array, dict[str, Any]]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            compression = handle.getcomptype()
            payload = handle.readframes(frame_count)
    except wave.Error as exc:
        raise RuntimeVerificationError(f"invalid PCM WAV: {path}") from exc
    if (channels, sample_width, sample_rate, compression) != (2, 2, EXPECTED_RATE, "NONE"):
        raise RuntimeVerificationError(
            f"unexpected PCM profile for {path}: channels={channels}, width={sample_width}, "
            f"rate={sample_rate}, compression={compression}"
        )
    if frame_count != EXPECTED_AUDIO_FRAMES or len(payload) != frame_count * channels * sample_width:
        raise RuntimeVerificationError(f"unexpected PCM frame or payload count for {path}")
    samples = array("h")
    samples.frombytes(payload)
    if os.sys.byteorder != "little":
        samples.byteswap()
    left_sum = right_sum = 0.0
    peak = 0
    clips = 0
    for index in range(0, len(samples), 2):
        left, right = int(samples[index]), int(samples[index + 1])
        left_sum += left * left
        right_sum += right * right
        peak = max(peak, abs(left), abs(right))
        clips += int(abs(left) >= 32767) + int(abs(right) >= 32767)
    left_rms = math.sqrt(left_sum / frame_count) / 32768.0
    right_rms = math.sqrt(right_sum / frame_count) / 32768.0
    return samples, {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": frame_count / sample_rate,
        "peak_absolute": peak / 32768.0,
        "clipping_ratio": clips / len(samples),
        "left_rms": left_rms,
        "right_rms": right_rms,
        "stereo_balance_delta": abs(left_rms - right_rms) / max(left_rms + right_rms, 1e-12),
    }


def fitted_linear_mix_metrics(
    voice: array, foley: array, ambience: array, final_mix: array
) -> dict[str, float]:
    if not (len(voice) == len(foley) == len(ambience) == len(final_mix)) or not voice:
        raise RuntimeVerificationError("mix reconstruction arrays must be non-empty and equal length")
    dot_xy = dot_xx = 0.0
    for v, f, a, observed in zip(voice, foley, ambience, final_mix, strict=True):
        expected = float(v) + MIX_WEIGHTS["foley_stem"] * float(f) + MIX_WEIGHTS["ambience_stem"] * float(a)
        dot_xy += expected * float(observed)
        dot_xx += expected * expected
    if dot_xx <= 0.0:
        raise RuntimeVerificationError("pre-loudness mix has no measurable energy")
    gain = dot_xy / dot_xx
    residual_sum = observed_sum = max_residual = 0.0
    for v, f, a, observed in zip(voice, foley, ambience, final_mix, strict=True):
        expected = gain * (
            float(v) + MIX_WEIGHTS["foley_stem"] * float(f) + MIX_WEIGHTS["ambience_stem"] * float(a)
        )
        residual = float(observed) - expected
        residual_sum += residual * residual
        observed_sum += float(observed) * float(observed)
        max_residual = max(max_residual, abs(residual) / 32768.0)
    normalized_rmse = math.sqrt(residual_sum / len(final_mix)) / max(
        math.sqrt(observed_sum / len(final_mix)), 1e-12
    )
    return {
        "fitted_linear_loudness_gain": gain,
        "normalized_reconstruction_rmse": normalized_rmse,
        "max_absolute_reconstruction_residual": max_residual,
    }


def inspect_mux(path: Path, authoritative_frame_rate: float = 24.0) -> dict[str, Any]:
    try:
        import av
    except ImportError as exc:
        raise RuntimeVerificationError("PyAV is required for full-mix runtime verification") from exc
    with av.open(str(path)) as container:
        if len(container.streams.video) != 1 or len(container.streams.audio) != 1:
            raise RuntimeVerificationError("review mux must contain exactly one video and one audio stream")
        video_stream = container.streams.video[0]
        video_frames = sum(1 for _ in container.decode(video_stream))
        reported_frame_rate = float(video_stream.average_rate or 0)
    with av.open(str(path)) as container:
        audio_stream = container.streams.audio[0]
        audio_frames = list(container.decode(audio_stream))
        audio_samples = sum(frame.samples for frame in audio_frames)
        channels = audio_stream.codec_context.channels
        sample_rate = audio_stream.codec_context.sample_rate
    return {
        "video_stream_count": 1,
        "audio_stream_count": 1,
        "decoded_video_frames": video_frames,
        "container_reported_average_frame_rate": reported_frame_rate,
        "authoritative_source_frame_rate": authoritative_frame_rate,
        "decoded_audio_frames": audio_samples,
        "audio_sample_rate_hz": sample_rate,
        "audio_channels": channels,
        "video_duration_seconds": video_frames / authoritative_frame_rate if authoritative_frame_rate else 0.0,
        "audio_duration_seconds": audio_samples / sample_rate if sample_rate else 0.0,
    }


def resolve_manifest_output(root: Path, manifest: dict[str, Any], name: str) -> Path:
    record = manifest.get("outputs", {}).get(name)
    if not isinstance(record, dict):
        raise RuntimeVerificationError(f"delivery manifest output is missing: {name}")
    path = Path(str(record.get("path", ""))).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeVerificationError(f"delivery manifest output escapes project root: {name}") from exc
    actual = binding(path, str(record.get("sha256", "")))
    if actual["bytes"] != record.get("bytes"):
        raise RuntimeVerificationError(f"delivery manifest byte count mismatch: {name}")
    return path


def verify(args: argparse.Namespace) -> dict[str, Any]:
    root = args.project_root.resolve()
    manifest_path = args.delivery_manifest.resolve()
    binding(manifest_path, EXPECTED_MANIFEST_SHA256)
    manifest = load_object(manifest_path)
    if manifest.get("artifact_type") != "wave64_genuine_audio_delivery_chain":
        raise RuntimeVerificationError("unexpected delivery manifest artifact type")
    if manifest.get("evidence_origin") != "local_production_execution" or manifest.get("is_synthetic") is not False:
        raise RuntimeVerificationError("delivery manifest is not the expected genuine local execution")
    if manifest.get("promotion_claimed") is not False:
        raise RuntimeVerificationError("delivery manifest improperly claims promotion")

    paths = {
        name: resolve_manifest_output(root, manifest, name)
        for name in ("voice_stem", "foley_stem", "ambience_stem", "final_mix", "review_mux")
    }
    source_video_record = manifest.get("source_bindings", {}).get("source_video", {})
    source_video = Path(str(source_video_record.get("path", ""))).resolve()
    binding(source_video, EXPECTED_VIDEO_SHA256)
    if paths["final_mix"] != Path(manifest["outputs"]["final_mix"]["path"]).resolve():
        raise RuntimeVerificationError("final mix path normalization changed")
    binding(paths["final_mix"], EXPECTED_MIX_SHA256)
    binding(paths["review_mux"], EXPECTED_MUX_SHA256)

    correction_manifest_path = args.correction_manifest.resolve()
    correction_manifest_binding = binding(correction_manifest_path)
    correction = load_object(correction_manifest_path)
    if correction.get("classification") != "W64_GENUINE_AUDIO_REVIEW_MUX_49_FRAME_TECHNICAL_PASS":
        raise RuntimeVerificationError("mux correction manifest classification is invalid")
    if correction.get("source_bindings", {}).get("original_defective_mux", {}).get("sha256") != EXPECTED_MUX_SHA256:
        raise RuntimeVerificationError("mux correction does not bind the original defective mux")
    corrected_mux_record = correction.get("correction", {}).get("corrected_mux", {})
    corrected_mux_path = Path(str(corrected_mux_record.get("path", ""))).resolve()
    try:
        corrected_mux_path.relative_to(root)
    except ValueError as exc:
        raise RuntimeVerificationError("corrected mux escapes project root") from exc
    corrected_mux_binding = binding(corrected_mux_path, str(corrected_mux_record.get("sha256", "")))

    decoded = {}
    pcm_metrics = {}
    for name in ("voice_stem", "foley_stem", "ambience_stem", "final_mix"):
        decoded[name], pcm_metrics[name] = read_pcm16_stereo(paths[name])
    reconstruction = fitted_linear_mix_metrics(
        decoded["voice_stem"], decoded["foley_stem"], decoded["ambience_stem"], decoded["final_mix"]
    )
    original_mux = inspect_mux(paths["review_mux"])
    if original_mux["decoded_video_frames"] != 48:
        raise RuntimeVerificationError("original review mux no longer reproduces the 48-frame defect")
    mux = inspect_mux(corrected_mux_path)
    duration_delta = abs(mux["video_duration_seconds"] - mux["audio_duration_seconds"])
    allowed_delta = 1.0 / mux["authoritative_source_frame_rate"] if mux["authoritative_source_frame_rate"] else 0.0

    contact_sheet = args.contact_sheet.resolve()
    contact_sheet_binding = binding(contact_sheet, args.expected_contact_sheet_sha256)
    visual_evidence = args.visual_evidence.resolve()
    visual_evidence_binding = binding(visual_evidence)
    visual = load_object(visual_evidence)
    if visual.get("source_bindings", {}).get("video", {}).get("sha256") != EXPECTED_VIDEO_SHA256:
        raise RuntimeVerificationError("visual evidence is not bound to the same source video")
    if visual.get("outputs", {}).get("contact_sheet", {}).get("sha256") != contact_sheet_binding["sha256"]:
        raise RuntimeVerificationError("visual evidence does not bind the exact contact sheet")

    technical_gates = {
        "delivery_manifest_hash_pass": True,
        "source_video_hash_pass": True,
        "all_delivery_output_hashes_pass": True,
        "stems_and_mix_pcm48_stereo_pass": True,
        "stem_frame_counts_match_pass": True,
        "linear_loudness_mix_reconstruction_pass": reconstruction["normalized_reconstruction_rmse"] <= 0.001,
        "final_mix_clipping_pass": pcm_metrics["final_mix"]["clipping_ratio"] == 0.0,
        "final_mix_stereo_balance_pass": pcm_metrics["final_mix"]["stereo_balance_delta"] <= 0.01,
        "review_mux_one_video_one_audio_pass": True,
        "original_review_mux_48_frame_defect_reproduced": True,
        "review_mux_video_frame_count_pass": mux["decoded_video_frames"] == EXPECTED_FRAMES,
        "review_mux_audio_profile_pass": (
            mux["decoded_audio_frames"] == CORRECTED_AUDIO_FRAMES
            and mux["audio_sample_rate_hz"] == EXPECTED_RATE
            and mux["audio_channels"] == 2
        ),
        "review_mux_duration_alignment_pass": duration_delta <= allowed_delta,
        "same_source_visual_decode_evidence_pass": True,
    }
    if not all(technical_gates.values()):
        failed = [name for name, passed in technical_gates.items() if not passed]
        raise RuntimeVerificationError("technical runtime gates failed: " + ", ".join(failed))

    authority_gates = {
        "camera_pan_ground_truth_pass": False,
        "source_listener_geometry_authority_pass": False,
        "room_rt60_measurement_authority_pass": False,
        "environment_reverb_match_authority_pass": False,
        "contact_owner_alignment_pass": False,
        "independent_perceptual_playback_review_pass": False,
        "production_spatial_room_authority_pass": False,
    }
    result = {
        "schema_version": "1.0",
        "artifact_type": "wave64_room_spatial_full_mix_runtime_verification",
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "classification": CLASSIFICATION,
        "source_identity": {
            "run_id": manifest["run_id"],
            "scene_id": manifest["scene_id"],
            "shot_id": manifest["shot_id"],
            "take_id": manifest["take_id"],
            "is_synthetic": False,
            "evidence_origin": manifest["evidence_origin"],
        },
        "source_bindings": {
            "delivery_manifest": binding(manifest_path, EXPECTED_MANIFEST_SHA256),
            "source_video": binding(source_video, EXPECTED_VIDEO_SHA256),
            **{name: binding(path) for name, path in paths.items()},
            "mux_correction_manifest": correction_manifest_binding,
            "corrected_review_mux": corrected_mux_binding,
            "visual_evidence": visual_evidence_binding,
            "contact_sheet": contact_sheet_binding,
        },
        "mix_contract": {
            "pre_loudness_weights": MIX_WEIGHTS,
            "loudness_stage": "ffmpeg_loudnorm_linear_fit_verified",
            "spatial_profile_claim": "centered_stereo_full_mix_technical_only",
            "visual_scene_observation": "centered full-body subject on a neutral seamless studio background",
            "geometry_or_material_inference_used_as_authority": False,
        },
        "metrics": {
            "pcm": pcm_metrics,
            "mix_reconstruction": reconstruction,
            "original_review_mux": original_mux,
            "corrected_review_mux": {**mux, "duration_delta_seconds": duration_delta, "allowed_delta_seconds": allowed_delta},
        },
        "technical_gates": technical_gates,
        "authority_gates": authority_gates,
        "row_results": {
            "029": {"technical_full_mix_runtime_pass": True, "row_complete": False, "pass_like": False},
            "030": {"stereo_review_mux_runtime_pass": True, "row_complete": False, "pass_like": False},
            "056": {"room_spatial_system_technical_runtime_partial": True, "row_complete": False, "pass_like": False},
        },
        "remaining_blockers": {
            "029": ["camera/source geometry, RT60/room measurement, perceptual playback, and production authority are absent"],
            "030": ["independent full-duration AV playback and production mux authority are absent"],
            "056": ["camera pan, source-listener geometry, environment reverb, distance cues, and perceptual review remain unauthoritative"],
        },
        "boundaries": {
            "source_media_regenerated": False,
            "source_media_mutated": False,
            "new_media_created": False,
            "model_execution_performed": False,
            "subjective_audio_review_fabricated": False,
            "geometry_or_room_truth_fabricated": False,
            "production_promotion_claimed": False,
            "content_based_suppression": False,
            "aws_or_ec2_used": False,
            "mask_or_wave71_touched": False,
            "jira_mutated": False,
        },
        "row_complete": False,
    }
    write_json_new(args.output.resolve(), result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--delivery-manifest", type=Path, required=True)
    parser.add_argument("--visual-evidence", type=Path, required=True)
    parser.add_argument("--correction-manifest", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    parser.add_argument("--expected-contact-sheet-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "classification": result["classification"], "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
