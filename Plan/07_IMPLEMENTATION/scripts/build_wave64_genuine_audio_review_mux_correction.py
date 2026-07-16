#!/usr/bin/env python3
"""Correct the genuine-audio review mux without changing source media."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import wave
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any


SOURCE_VIDEO_SHA256 = "5006e96e211538f3d2bb6795e93014d6642946583cc31aa635e171e13e1c80bf"
SOURCE_MIX_SHA256 = "5a07f0a654499266509453421c3efdc1b2e4ce83b8706e0138ebc4b1d3ad924a"
ORIGINAL_MUX_SHA256 = "03b5b55f871d7460c37e97bacd53968d183b0e1adc3022fb2daffc5e056a9b7d"
EXPECTED_VIDEO_FRAMES = 49
EXPECTED_RATE = 48_000
SOURCE_AUDIO_FRAMES = 97_920
TARGET_AUDIO_FRAMES = 97_968


class MuxCorrectionError(RuntimeError):
    pass


def authoritative_video_duration(frame_count: int, frame_rate: float) -> float:
    if frame_count <= 0 or frame_rate <= 0:
        raise MuxCorrectionError("authoritative video duration inputs must be positive")
    return frame_count / frame_rate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise MuxCorrectionError(f"required file is missing: {path}")
    actual = sha256_file(path)
    if expected_sha256 and actual != expected_sha256:
        raise MuxCorrectionError(f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def write_json_lf(path: Path, value: dict[str, Any]) -> None:
    content = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    payload = path.read_bytes()
    if b"\r" in payload or not payload.endswith(b"\n"):
        raise MuxCorrectionError(f"JSON output is not canonical LF UTF-8: {path}")


def write_padded_pcm16_stereo(source: Path, destination: Path) -> dict[str, Any]:
    with wave.open(str(source), "rb") as handle:
        profile = (handle.getnchannels(), handle.getsampwidth(), handle.getframerate(), handle.getcomptype())
        frames = handle.getnframes()
        payload = handle.readframes(frames)
    if profile != (2, 2, EXPECTED_RATE, "NONE") or frames != SOURCE_AUDIO_FRAMES:
        raise MuxCorrectionError(f"source mix profile is invalid: profile={profile}, frames={frames}")
    pad_frames = TARGET_AUDIO_FRAMES - frames
    if pad_frames <= 0:
        raise MuxCorrectionError("target audio frame count must exceed source frame count")
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(EXPECTED_RATE)
        handle.writeframes(payload)
        handle.writeframes(b"\x00" * pad_frames * 2 * 2)
    with wave.open(str(destination), "rb") as handle:
        if handle.getnframes() != TARGET_AUDIO_FRAMES or handle.getnchannels() != 2 or handle.getframerate() != EXPECTED_RATE:
            raise MuxCorrectionError("padded stereo output did not decode to the target profile")
    return {
        **binding(destination),
        "sample_rate_hz": EXPECTED_RATE,
        "channels": 2,
        "source_frames": frames,
        "padding_frames": pad_frames,
        "target_frames": TARGET_AUDIO_FRAMES,
        "padding_seconds": pad_frames / EXPECTED_RATE,
    }


def inspect_mux(path: Path, authoritative_frame_rate: float = 24.0) -> dict[str, Any]:
    try:
        import av
    except ImportError as exc:
        raise MuxCorrectionError("PyAV is required for mux correction") from exc
    with av.open(str(path)) as container:
        if len(container.streams.video) != 1 or len(container.streams.audio) != 1:
            raise MuxCorrectionError("mux must contain exactly one video and one audio stream")
        video_stream = container.streams.video[0]
        video_frames = sum(1 for _ in container.decode(video_stream))
        reported_frame_rate = float(video_stream.average_rate or 0)
    with av.open(str(path)) as container:
        audio_stream = container.streams.audio[0]
        audio_frames = sum(frame.samples for frame in container.decode(audio_stream))
        sample_rate = audio_stream.codec_context.sample_rate
        channels = audio_stream.codec_context.channels
    return {
        **binding(path),
        "decoded_video_frames": video_frames,
        "container_reported_average_frame_rate": reported_frame_rate,
        "authoritative_source_frame_rate": authoritative_frame_rate,
        "decoded_audio_frames": audio_frames,
        "audio_sample_rate_hz": sample_rate,
        "audio_channels": channels,
        "video_duration_seconds": authoritative_video_duration(video_frames, authoritative_frame_rate),
        "audio_duration_seconds": audio_frames / sample_rate if sample_rate else 0.0,
    }


def remux(video_path: Path, audio_path: Path, output_path: Path) -> None:
    try:
        import av
    except ImportError as exc:
        raise MuxCorrectionError("PyAV is required for mux correction") from exc
    with av.open(str(video_path)) as video_input, av.open(str(audio_path)) as audio_input:
        if len(video_input.streams.video) != 1 or len(video_input.streams.audio) != 0:
            raise MuxCorrectionError("source video must contain exactly one video stream and no audio")
        if len(audio_input.streams.audio) != 1 or len(audio_input.streams.video) != 0:
            raise MuxCorrectionError("source audio must contain exactly one audio stream and no video")
        video_stream = video_input.streams.video[0]
        audio_stream = audio_input.streams.audio[0]
        with av.open(str(output_path), mode="w", format="matroska") as output:
            video_out = output.add_stream_from_template(video_stream)
            audio_out = output.add_stream_from_template(audio_stream)
            packets = []
            for packet in video_input.demux(video_stream):
                if packet.dts is not None and packet.size:
                    packets.append((Fraction(packet.dts) * packet.time_base, 0, packet, video_out))
            for packet in audio_input.demux(audio_stream):
                if packet.dts is not None and packet.size:
                    packets.append((Fraction(packet.dts) * packet.time_base, 1, packet, audio_out))
            for _, _, packet, target in sorted(packets, key=lambda item: (item[0], item[1])):
                packet.stream = target
                output.mux(packet)


def make_contact_sheet(mux_path: Path, output_path: Path, frame_indices: tuple[int, ...] = (0, 9, 19, 29, 39, 48)) -> dict[str, Any]:
    try:
        import av
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise MuxCorrectionError("PyAV and Pillow are required for corrected-mux visual review") from exc
    selected = {}
    with av.open(str(mux_path)) as container:
        stream = container.streams.video[0]
        for index, frame in enumerate(container.decode(stream)):
            if index in frame_indices:
                selected[index] = frame.to_image().convert("RGB")
    if tuple(sorted(selected)) != frame_indices:
        raise MuxCorrectionError(f"corrected mux contact sheet is missing frames: {sorted(set(frame_indices) - set(selected))}")
    tile_width = 240
    first = selected[frame_indices[0]]
    tile_height = round(first.height * tile_width / first.width)
    sheet = Image.new("RGB", (tile_width * 3, (tile_height + 24) * 2), "white")
    draw = ImageDraw.Draw(sheet)
    for position, index in enumerate(frame_indices):
        image = selected[index].resize((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = (position % 3) * tile_width
        y = (position // 3) * (tile_height + 24)
        sheet.paste(image, (x, y))
        draw.text((x + 6, y + tile_height + 4), f"frame {index}", fill="black")
    sheet.save(output_path, format="PNG")
    return {**binding(output_path), "reviewed_frame_indices": list(frame_indices)}


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_video = args.source_video.resolve()
    source_mix = args.source_mix.resolve()
    original_mux = args.original_mux.resolve()
    output_dir = args.output_dir.resolve()
    source_bindings = {
        "video": binding(source_video, SOURCE_VIDEO_SHA256),
        "mix": binding(source_mix, SOURCE_MIX_SHA256),
        "original_defective_mux": binding(original_mux, ORIGINAL_MUX_SHA256),
    }
    original_metrics = inspect_mux(original_mux)
    if original_metrics["decoded_video_frames"] != 48:
        raise MuxCorrectionError("original mux no longer reproduces the exact 48-frame defect")
    if output_dir.exists():
        raise MuxCorrectionError(f"immutable output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        padded_audio = temporary / "final_mix_stereo_48k_pad48.wav"
        corrected_mux = temporary / "review_mux_video_copy_pcm48_stereo_49f.mkv"
        contact_sheet = temporary / "corrected_mux_contact_sheet.png"
        padded = write_padded_pcm16_stereo(source_mix, padded_audio)
        remux(source_video, padded_audio, corrected_mux)
        corrected = inspect_mux(corrected_mux)
        if corrected["decoded_video_frames"] != EXPECTED_VIDEO_FRAMES:
            raise MuxCorrectionError("corrected mux did not preserve all 49 video frames")
        if (
            corrected["decoded_audio_frames"] != TARGET_AUDIO_FRAMES
            or corrected["audio_sample_rate_hz"] != EXPECTED_RATE
            or corrected["audio_channels"] != 2
        ):
            raise MuxCorrectionError("corrected mux did not preserve the padded 48 kHz stereo profile")
        duration_delta = abs(corrected["video_duration_seconds"] - corrected["audio_duration_seconds"])
        allowed = 1.0 / corrected["authoritative_source_frame_rate"]
        if duration_delta > allowed:
            raise MuxCorrectionError("corrected mux duration delta exceeds one video frame")
        contact_sheet_binding = make_contact_sheet(corrected_mux, contact_sheet)
        manifest = {
            "schema_version": "1.0",
            "artifact_type": "wave64_genuine_audio_review_mux_frame_preservation_correction",
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "classification": "W64_GENUINE_AUDIO_REVIEW_MUX_49_FRAME_TECHNICAL_PASS",
            "source_bindings": source_bindings,
            "original_defect": {
                "decoded_video_frames": original_metrics["decoded_video_frames"],
                "expected_video_frames": EXPECTED_VIDEO_FRAMES,
                "decoded_audio_frames": original_metrics["decoded_audio_frames"],
                "cause": "shortest_mux_terminated_at_2.040_second_audio_before_49th_video_frame",
            },
            "correction": {
                "method": "append_48_zero_pcm_frames_then_packet_remux_video_without_regeneration",
                "padded_audio": padded,
                "corrected_mux": corrected,
                "contact_sheet": contact_sheet_binding,
                "duration_delta_seconds": duration_delta,
                "allowed_delta_seconds": allowed,
            },
            "gates": {
                "source_hashes_pass": True,
                "original_48_frame_defect_reproduced": True,
                "padding_exactly_48_stereo_frames_pass": padded["padding_frames"] == 48,
                "corrected_video_49_frames_pass": True,
                "corrected_audio_97968_frames_pass": True,
                "corrected_audio_48k_stereo_pass": True,
                "duration_alignment_pass": True,
                "source_video_regenerated": False,
                "source_mix_mutated": False,
            },
            "boundaries": {
                "independent_perceptual_playback_review_present": False,
                "contact_owner_alignment_present": False,
                "room_geometry_authority_present": False,
                "production_audio_certification_allowed": False,
                "promotion_claimed": False,
                "aws_or_ec2_used": False,
                "mask_or_wave71_touched": False,
                "jira_mutated": False,
            },
            "row_complete": False,
        }
        manifest_path = temporary / "mux_correction_manifest.json"
        write_json_lf(manifest_path, manifest)
        os.replace(temporary, output_dir)
        manifest["correction"]["padded_audio"]["path"] = str(output_dir / padded_audio.name)
        manifest["correction"]["corrected_mux"]["path"] = str(output_dir / corrected_mux.name)
        manifest["correction"]["contact_sheet"]["path"] = str(output_dir / contact_sheet.name)
        write_json_lf(output_dir / manifest_path.name, manifest)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-video", type=Path, required=True)
    parser.add_argument("--source-mix", type=Path, required=True)
    parser.add_argument("--original-mux", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "classification": result["classification"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
