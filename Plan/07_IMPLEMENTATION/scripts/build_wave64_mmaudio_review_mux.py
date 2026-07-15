#!/usr/bin/env python3
"""Build a hash-bound review mux from completed video and MMAudio artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> str:
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise ValueError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")
    return actual


def duration_delta_allowed(frame_rate: float, floor_seconds: float = 0.002) -> float:
    if frame_rate <= 0:
        raise ValueError("frame rate must be positive")
    return max(floor_seconds, 1.0 / frame_rate)


def resolved_video_duration(stream_duration: float, decoded_frames: int, frame_rate: float) -> float:
    if stream_duration > 0:
        return stream_duration
    if decoded_frames <= 0 or frame_rate <= 0:
        raise ValueError("video duration cannot be resolved from stream metadata or decoded frames")
    return decoded_frames / frame_rate


def _load_av():
    try:
        import av
    except ImportError as exc:
        raise RuntimeError("PyAV is required to build the review mux") from exc
    return av


def _stream_duration(stream) -> float:
    if stream.duration is None or stream.time_base is None:
        return 0.0
    return float(stream.duration * stream.time_base)


def inspect_media(path: Path) -> dict:
    av = _load_av()
    with av.open(str(path)) as container:
        video_streams = list(container.streams.video)
        audio_streams = list(container.streams.audio)
        result = {
            "path": str(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "video_stream_count": len(video_streams),
            "audio_stream_count": len(audio_streams),
        }
        if video_streams:
            stream = video_streams[0]
            decoded_frames = sum(1 for _ in container.decode(stream))
            frame_rate = float(stream.average_rate or 0)
            duration_seconds = resolved_video_duration(
                _stream_duration(stream), decoded_frames, frame_rate
            )
            result["video"] = {
                "codec": stream.codec_context.name,
                "width": stream.codec_context.width,
                "height": stream.codec_context.height,
                "frame_rate": frame_rate,
                "decoded_frames": decoded_frames,
                "duration_seconds": duration_seconds,
            }

    if result["audio_stream_count"]:
        with av.open(str(path)) as container:
            stream = container.streams.audio[0]
            decoded_samples = sum(frame.samples for frame in container.decode(stream))
            result["audio"] = {
                "codec": stream.codec_context.name,
                "sample_rate_hz": stream.codec_context.sample_rate,
                "channels": stream.codec_context.channels,
                "decoded_samples": decoded_samples,
                "duration_seconds": decoded_samples / stream.codec_context.sample_rate,
            }
    return result


def remux(video_path: Path, audio_path: Path, output_path: Path) -> None:
    av = _load_av()
    with av.open(str(video_path)) as video_input, av.open(str(audio_path)) as audio_input:
        if len(video_input.streams.video) != 1:
            raise ValueError("source video must contain exactly one video stream")
        if len(audio_input.streams.audio) != 1:
            raise ValueError("source audio must contain exactly one audio stream")

        video_input_stream = video_input.streams.video[0]
        audio_input_stream = audio_input.streams.audio[0]
        with av.open(str(output_path), mode="w", format="matroska") as output:
            video_output_stream = output.add_stream_from_template(video_input_stream)
            audio_output_stream = output.add_stream_from_template(audio_input_stream)
            packets = []
            for packet in video_input.demux(video_input_stream):
                if packet.dts is not None and packet.size:
                    packets.append((Fraction(packet.dts) * packet.time_base, 0, packet, video_output_stream))
            for packet in audio_input.demux(audio_input_stream):
                if packet.dts is not None and packet.size:
                    packets.append((Fraction(packet.dts) * packet.time_base, 1, packet, audio_output_stream))
            if not packets:
                raise ValueError("no media packets were available for muxing")
            for _, _, packet, output_stream in sorted(packets, key=lambda item: (item[0], item[1])):
                packet.stream = output_stream
                output.mux(packet)


def build(args: argparse.Namespace) -> dict:
    video = Path(args.source_video).resolve()
    audio = Path(args.source_audio).resolve()
    output_dir = Path(args.output_dir).resolve()
    for path, label in ((video, "source video"), (audio, "source audio")):
        if not path.is_file():
            raise ValueError(f"{label} is not a file: {path}")
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")

    video_hash = require_hash(video, args.expected_video_sha256, "source video")
    audio_hash = require_hash(audio, args.expected_audio_sha256, "source audio")
    video_input = inspect_media(video)
    audio_input = inspect_media(audio)
    if video_input["video_stream_count"] != 1 or video_input["audio_stream_count"] != 0:
        raise ValueError("source video must have exactly one video stream and no audio stream")
    if audio_input["audio_stream_count"] != 1 or audio_input["video_stream_count"] != 0:
        raise ValueError("source audio must have exactly one audio stream and no video stream")
    if video_input["video"]["decoded_frames"] != args.expected_video_frames:
        raise ValueError(
            f"source video frame mismatch: expected {args.expected_video_frames}, "
            f"got {video_input['video']['decoded_frames']}"
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = output_dir.with_name(f".{output_dir.name}.tmp")
    if temporary_dir.exists():
        shutil.rmtree(temporary_dir)
    temporary_dir.mkdir()
    try:
        mux_path = temporary_dir / "mmaudio_review_mux_video_copy_pcm48_mono.mkv"
        remux(video, audio, mux_path)
        mux = inspect_media(mux_path)
        if mux["video_stream_count"] != 1 or mux["audio_stream_count"] != 1:
            raise ValueError("review mux must contain exactly one video and one audio stream")
        if mux["video"]["decoded_frames"] != args.expected_video_frames:
            raise ValueError("review mux did not preserve the expected decoded video frame count")
        if mux["audio"]["sample_rate_hz"] != audio_input["audio"]["sample_rate_hz"]:
            raise ValueError("review mux did not preserve the source audio sample rate")
        if mux["audio"]["decoded_samples"] != audio_input["audio"]["decoded_samples"]:
            raise ValueError("review mux did not preserve the source decoded audio sample count")

        frame_rate = mux["video"]["frame_rate"]
        duration_delta = abs(mux["video"]["duration_seconds"] - mux["audio"]["duration_seconds"])
        allowed_delta = duration_delta_allowed(frame_rate)
        if duration_delta > allowed_delta:
            raise ValueError(
                f"review mux duration delta {duration_delta:.6f}s exceeds {allowed_delta:.6f}s"
            )

        manifest = {
            "schema_version": "1.0",
            "artifact_type": "wave64_mmaudio_hash_bound_review_mux",
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PASS_TECHNICAL_MUX_PLAYBACK_REVIEW_BLOCKED",
            "classification": "GENUINE_MMAUDIO_REVIEW_MUX_TECHNICAL_PASS",
            "direct_qa_state": "PASS_TECHNICAL_REVIEW",
            "direct_qa_passed": True,
            "source_bindings": {
                "video": {**video_input, "sha256": video_hash, "regenerated": False},
                "audio": {**audio_input, "sha256": audio_hash, "regenerated": False},
            },
            "output": mux,
            "acceptance": {
                "video_hash_verified": True,
                "audio_hash_verified": True,
                "video_frame_count_preserved": True,
                "audio_sample_count_preserved": True,
                "audio_sample_rate_preserved": True,
                "one_video_one_audio_stream": True,
                "duration_delta_seconds": duration_delta,
                "duration_delta_allowed_seconds": allowed_delta,
                "duration_alignment_pass": True,
                "independent_perceptual_playback_review_present": False,
                "contact_owner_alignment_present": False,
                "production_audio_certification_allowed": False,
            },
            "runtime_boundary": {
                "source_video_regenerated": False,
                "source_audio_regenerated": False,
                "model_execution_performed": False,
                "ec2_started": False,
                "s3_mutated": False,
                "mask_truth_consumed": False,
                "wave71_activated": False,
                "jira_mutated": False,
                "promotion_claimed": False,
            },
            "remaining_blockers": [
                "independent perceptual playback review is not present",
                "trusted contact-owner and Wave22 force alignment authority is not present",
                "production audio certification authority is not present",
            ],
            "row_complete": False,
        }
        manifest_path = temporary_dir / "review_mux_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary_dir.rename(output_dir)
        manifest["output"]["path"] = str(output_dir / mux_path.name)
        manifest_path = output_dir / manifest_path.name
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-video", required=True)
    parser.add_argument("--source-audio", required=True)
    parser.add_argument("--expected-video-sha256", required=True)
    parser.add_argument("--expected-audio-sha256", required=True)
    parser.add_argument("--expected-video-frames", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), indent=2))
