#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts"
TEMPLATE_DIR = REPO_ROOT / "Plan/07_IMPLEMENTATION/templates/powershell"
COMPILE_SCRIPT = SCRIPT_DIR / "compile_wave30_audio_event_manifest.py"
SCORE_SCRIPT = SCRIPT_DIR / "score_wave30_audio_qa.py"
VALIDATE_SCRIPT = SCRIPT_DIR / "run_wave30_local_validation.py"
WRAPPER_SCRIPT = TEMPLATE_DIR / "Run-Wave30-AudioGenerationValidation.ps1"

GATES = {
    "decode": "pass",
    "duration": "pass",
    "loudness": "pass",
    "clipping": "pass",
    "sync": "pass",
    "voice_identity": "pass",
    "event_coverage": "pass",
    "mix_balance": "pass",
    "artifact_manifest": "pass",
    "runtime_proof": "fail",
    "audio_review": "fail",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_pcm_wav(path: Path, *, sample_rate: int = 16000, seconds: float = 0.25) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        silence_frame = struct.pack("<h", 0)
        handle.writeframes(silence_frame * frame_count)
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
        "seconds": frame_count / float(sample_rate),
        "sample_rate_hz": sample_rate,
        "channels": 1,
        "sample_width_bytes": 2,
        "frame_count": frame_count,
    }


def _write_runtime_proof(
    path: Path,
    *,
    run_id: str,
    mix_id: str,
    event_manifest_sha256: str,
    mixdown_sha256: str,
    extra_fields: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema_name": "wave30_audio_runtime_proof",
        "proof_kind": "runtime",
        "verified": True,
        "run_id": run_id,
        "mix_id": mix_id,
        "event_manifest_sha256": event_manifest_sha256,
        "mixdown_sha256": mixdown_sha256,
        "generation_executed": True,
        "decode_passed": True,
        "duration_passed": True,
        "artifact_hash_passed": True,
        "av_sync_passed": True,
    }
    if extra_fields:
        payload.update(extra_fields)
    _write_json(path, payload)


def _write_audio_review_proof(
    path: Path,
    *,
    run_id: str,
    mix_id: str,
    event_manifest_sha256: str,
    mixdown_sha256: str,
    extra_fields: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema_name": "wave30_audio_review_proof",
        "proof_kind": "audio_review",
        "verified": True,
        "review_method": "audio_playback_review",
        "run_id": run_id,
        "mix_id": mix_id,
        "event_manifest_sha256": event_manifest_sha256,
        "mixdown_sha256": mixdown_sha256,
        "correct_speaker": True,
        "voice_profile_consistency": True,
        "speech_intelligibility": True,
        "foley_action_alignment": True,
        "ambience_dialogue_balance": True,
        "no_clipping": True,
        "mix_balance": True,
        "av_sync": True,
    }
    if extra_fields:
        payload.update(extra_fields)
    _write_json(path, payload)


def _run(args: list[str], *, expect_ok: bool, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if expect_ok and result.returncode != 0:
        raise AssertionError(
            "command failed unexpectedly\n"
            f"cmd={' '.join(args)}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    if (not expect_ok) and result.returncode == 0:
        raise AssertionError(
            "command succeeded unexpectedly\n"
            f"cmd={' '.join(args)}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


class Wave30AudioPipelineStrictTests(unittest.TestCase):
    def _compile(self, packet_path: Path, output_path: Path, expect_ok: bool) -> subprocess.CompletedProcess[str]:
        return _run(
            [
                sys.executable,
                str(COMPILE_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--input",
                str(packet_path),
                "--output",
                str(output_path),
            ],
            expect_ok=expect_ok,
        )

    def _score(self, score_input: Path, output_path: Path, expect_ok: bool) -> subprocess.CompletedProcess[str]:
        return _run(
            [
                sys.executable,
                str(SCORE_SCRIPT),
                "--root",
                str(REPO_ROOT),
                "--input",
                str(score_input),
                "--output",
                str(output_path),
            ],
            expect_ok=expect_ok,
        )

    def _base_event_packet(self, tmpdir: Path) -> tuple[Path, Path]:
        wav_dialogue = _write_pcm_wav(tmpdir / "dialogue.wav", seconds=0.25)
        wav_ambience = _write_pcm_wav(tmpdir / "ambience.wav", seconds=0.5)
        packet = {
            "run_id": "run_wave30",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "is_synthetic": True,
            "required_lanes": ["dialogue", "ambience"],
            "av_frame_rate": 24.0,
            "audio_events": [
                {
                    "audio_event_id": "event_dialogue_001",
                    "scene_id": "scene_001",
                    "shot_id": "shot_001",
                    "event_type": "dialogue",
                    "sync_class": "frame_exact",
                    "source_event_id": "src_dialogue_001",
                    "purpose": "spoken line",
                    "start_seconds": 0.0,
                    "end_seconds": wav_dialogue["seconds"],
                    "expected_video_frame_range": {
                        "start_frame": 0,
                        "end_frame": int(round(wav_dialogue["seconds"] * 24.0)),
                        "frame_rate": 24.0,
                    },
                    "qa_rules": ["speaker_match", "sync_exact"],
                    "layer": "dialogue",
                    "routing": {"bus": "dialogue_main"},
                    "subject_binding": {
                        "binding_type": "character",
                        "character_id": "char_main",
                    },
                    "artifact": {
                        "path": wav_dialogue["path"],
                        "sha256": wav_dialogue["sha256"],
                        "bytes": wav_dialogue["bytes"],
                    },
                },
                {
                    "audio_event_id": "event_ambience_001",
                    "scene_id": "scene_001",
                    "shot_id": "shot_001",
                    "event_type": "ambience",
                    "sync_class": "ambient_free",
                    "source_event_id": "src_ambience_001",
                    "purpose": "environment bed",
                    "start_seconds": 0.0,
                    "end_seconds": wav_ambience["seconds"],
                    "expected_video_frame_range": {
                        "start_frame": 0,
                        "end_frame": int(round(wav_ambience["seconds"] * 24.0)),
                        "frame_rate": 24.0,
                    },
                    "qa_rules": ["dialogue_not_masked"],
                    "layer": "ambience",
                    "routing": {"bus": "ambience_bed"},
                    "subject_binding": {
                        "binding_type": "environment"
                    },
                    "artifact": {
                        "path": wav_ambience["path"],
                        "sha256": wav_ambience["sha256"],
                        "bytes": wav_ambience["bytes"],
                    },
                },
            ],
        }
        packet_path = tmpdir / "event_packet.json"
        event_manifest = tmpdir / "event_manifest.json"
        _write_json(packet_path, packet)
        return packet_path, event_manifest

    def _make_mix_manifest(self, tmpdir: Path, event_manifest_path: Path, synthetic: bool = True) -> tuple[Path, Path, Path]:
        event_manifest = json.loads(event_manifest_path.read_text(encoding="utf-8"))
        mix_wav = _write_pcm_wav(tmpdir / "mixdown.wav", seconds=0.5)
        runtime_proof = tmpdir / "runtime_proof.json"
        review_proof = tmpdir / "audio_review.json"
        event_sha = _sha256(event_manifest_path)
        _write_runtime_proof(
            runtime_proof,
            run_id="run_wave30",
            mix_id="mix_001",
            event_manifest_sha256=event_sha,
            mixdown_sha256=mix_wav["sha256"],
        )
        _write_audio_review_proof(
            review_proof,
            run_id="run_wave30",
            mix_id="mix_001",
            event_manifest_sha256=event_sha,
            mixdown_sha256=mix_wav["sha256"],
        )
        mix_manifest = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_name": "wave30_audio_mix_manifest",
            "mix_manifest_version": 1,
            "run_id": "run_wave30",
            "mix_id": "mix_001",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "is_synthetic": synthetic,
            "event_manifest_bindings": [
                {
                    "path": str(event_manifest_path.resolve()),
                    "sha256": event_sha,
                }
            ],
            "mixdown_artifact": {
                "path": mix_wav["path"],
                "sha256": mix_wav["sha256"],
                "bytes": mix_wav["bytes"],
            },
            "mix_technical": {
                "duration_seconds": mix_wav["seconds"],
                "sample_rate_hz": mix_wav["sample_rate_hz"],
                "channels": mix_wav["channels"],
                "channel_layout": "mono",
                "sample_width_bytes": mix_wav["sample_width_bytes"],
                "frame_count": mix_wav["frame_count"],
            },
            "mix_event_metadata": [
                {
                    "audio_event_id": event["audio_event_id"],
                    "gain_db": -3.0,
                    "pan": 0.0,
                    "spatial_position": {"x": 0.0, "y": 0.0, "z": 1.0},
                    "distance_meters": 1.0,
                }
                for event in event_manifest["audio_events"]
            ],
            "mix_loudness": {
                "integrated_lufs": -16.0,
                "true_peak_dbtp": -1.0,
                "clipping_detected": False,
            },
            "dialogue_ducking": {
                "enabled": True,
                "duck_db": -8.0,
                "recovery_ms": 150,
            },
            "av_sync_evidence": {
                "frame_rate": 24.0,
                "start_frame": 0,
                "end_frame": 12,
                "frame_offset": 0,
            },
            "runtime_proof": {
                "proof_kind": "runtime",
                "path": str(runtime_proof),
                "sha256": _sha256(runtime_proof),
            },
            "audio_review": {
                "proof_kind": "audio_review",
                "path": str(review_proof),
                "sha256": _sha256(review_proof),
            },
            "production_state": {
                "runtime_proof_present": False,
                "audio_review_present": False,
                "certified_for_release": False,
            },
            "promotion_decision": "block",
        }
        mix_manifest_path = tmpdir / "mix_manifest.json"
        _write_json(mix_manifest_path, mix_manifest)
        return mix_manifest_path, runtime_proof, review_proof

    def _score_input(
        self,
        event_manifest_path: Path,
        mix_manifest_path: Path,
        *,
        is_synthetic: bool = True,
        gates: dict[str, str] | None = None,
        required_lanes: list[str] | None = None,
    ) -> dict[str, Any]:
        if gates is None:
            gates = dict(GATES)
        if required_lanes is None:
            required_lanes = ["dialogue", "ambience"]
        return {
            "run_id": "run_wave30",
            "is_synthetic": is_synthetic,
            "required_lanes": required_lanes,
            "event_manifest_bindings": [
                {
                    "path": str(event_manifest_path.resolve()),
                    "sha256": _sha256(event_manifest_path),
                }
            ],
            "mix_manifest_binding": {
                "path": str(mix_manifest_path.resolve()),
                "sha256": _sha256(mix_manifest_path),
            },
            "qa_scores": {
                "decode": 100.0,
                "duration": 100.0,
                "loudness": 95.0,
                "clipping": 100.0,
                "sync": 96.0,
                "voice_identity": 97.0,
                "event_coverage": 98.0,
                "mix_balance": 94.0,
            },
            "gate_statuses": gates,
        }

    def _production_gate_statuses(self) -> dict[str, str]:
        gates = dict(GATES)
        gates["runtime_proof"] = "pass"
        gates["audio_review"] = "pass"
        return gates

    def test_valid_synthetic_multi_lane_packet_remains_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=True)
            report = json.loads(qa_report.read_text(encoding="utf-8"))
            self.assertEqual(report["promotion_decision"], "block")
            self.assertTrue(report["is_synthetic"])

    def test_compiler_rejects_unknown_taxonomy_and_missing_subject_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["audio_events"][0]["event_type"] = "unknown_taxonomy"
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["audio_events"][0]["event_type"] = "dialogue"
            payload["audio_events"][0]["subject_binding"] = {"binding_type": "none"}
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)

    def test_compiler_rejects_wav_decode_hash_bytes_timing_and_av_frame_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            payload = json.loads(packet_path.read_text(encoding="utf-8"))

            payload["audio_events"][0]["artifact"]["bytes"] += 1
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["audio_events"][0]["artifact"]["bytes"] -= 1
            payload["audio_events"][0]["artifact"]["sha256"] = "0" * 64
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["audio_events"][0]["artifact"]["sha256"] = _sha256(Path(payload["audio_events"][0]["artifact"]["path"]))
            payload["audio_events"][0]["end_seconds"] = 5.0
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["audio_events"][0]["end_seconds"] = payload["audio_events"][0]["start_seconds"] + 0.25
            payload["audio_events"][0]["expected_video_frame_range"]["end_frame"] = 99
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)

    def test_compiler_transactional_output_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            original_payload = {"existing": True}
            _write_json(event_manifest_path, original_payload)
            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["audio_events"][0]["artifact"]["sha256"] = "f" * 64
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=False)
            observed = json.loads(event_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(observed, original_payload)

    def test_compiler_rejects_non_boolean_is_synthetic_and_invalid_frame_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            for bad_value in ["true", "false", 1, 0, None, [], {}]:
                payload["is_synthetic"] = bad_value
                _write_json(packet_path, payload)
                self._compile(packet_path, event_manifest_path, expect_ok=False)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["is_synthetic"] = True
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            manifest = json.loads(event_manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["is_synthetic"])

            payload["is_synthetic"] = False
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            manifest = json.loads(event_manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["is_synthetic"])

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload.pop("is_synthetic", None)
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            manifest = json.loads(event_manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["is_synthetic"])

            for bad_frame_rate in [0.0, -1.0, float("inf"), float("-inf"), float("nan")]:
                payload = json.loads(packet_path.read_text(encoding="utf-8"))
                payload["av_frame_rate"] = bad_frame_rate
                _write_json(packet_path, payload)
                self._compile(packet_path, event_manifest_path, expect_ok=False)

            payload = json.loads(packet_path.read_text(encoding="utf-8"))
            payload["av_frame_rate"] = 60.0
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            manifest = json.loads(event_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["av_sync_binding"]["frame_rate"], 60.0)

            payload.pop("av_frame_rate", None)
            _write_json(packet_path, payload)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            manifest = json.loads(event_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["av_sync_binding"]["frame_rate"], 24.0)

    def test_scorer_rejects_event_mix_hash_mismatch_and_missing_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"

            bad_input = self._score_input(event_manifest_path, mix_manifest_path)
            bad_input["mix_manifest_binding"]["sha256"] = "0" * 64
            _write_json(score_input, bad_input)
            self._score(score_input, qa_report, expect_ok=False)

            missing_lane_input = self._score_input(
                event_manifest_path,
                mix_manifest_path,
                required_lanes=["dialogue", "music"],
            )
            _write_json(score_input, missing_lane_input)
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_missing_failed_gate_and_non_finite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"

            gates = dict(GATES)
            gates.pop("audio_review")
            _write_json(
                score_input,
                self._score_input(event_manifest_path, mix_manifest_path, gates=gates),
            )
            self._score(score_input, qa_report, expect_ok=False)

            score_input.write_text(
                '{"run_id":"run_wave30","is_synthetic":true,"required_lanes":["dialogue"],'
                '"event_manifest_bindings":[],"mix_manifest_binding":{},"qa_scores":{"decode":NaN},'
                '"gate_statuses":{"decode":"pass"}}',
                encoding="utf-8",
            )
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_inline_spoof_and_meaningless_json_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, runtime_proof, review_proof = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=False)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"
            gates = self._production_gate_statuses()

            # Inline self-assertions in mix manifest must be rejected by schema/validator.
            mix_payload["runtime_proof"]["verified"] = True
            mix_payload["runtime_proof"]["binding"] = {
                "run_id": "run_wave30",
                "mix_id": "mix_001",
                "event_manifest_sha256": _sha256(event_manifest_path),
            }
            mix_payload["audio_review"]["verified"] = True
            mix_payload["audio_review"]["binding"] = {
                "run_id": "run_wave30",
                "mix_id": "mix_001",
                "event_manifest_sha256": _sha256(event_manifest_path),
            }
            _write_json(mix_manifest_path, mix_payload)
            _write_json(
                score_input,
                self._score_input(
                    event_manifest_path,
                    mix_manifest_path,
                    is_synthetic=False,
                    gates=gates,
                ),
            )
            self._score(score_input, qa_report, expect_ok=False)

            # Meaningless but hash-consistent JSON proofs must still fail strict proof parsing.
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["runtime_proof"] = {
                "proof_kind": "runtime",
                "path": str(runtime_proof),
                "sha256": _sha256(runtime_proof),
            }
            mix_payload["audio_review"] = {
                "proof_kind": "audio_review",
                "path": str(review_proof),
                "sha256": _sha256(review_proof),
            }
            _write_json(runtime_proof, {"proof": "runtime", "ok": True})
            _write_json(review_proof, {"proof": "review", "ok": True})
            mix_payload["runtime_proof"]["sha256"] = _sha256(runtime_proof)
            mix_payload["audio_review"]["sha256"] = _sha256(review_proof)
            _write_json(mix_manifest_path, mix_payload)
            _write_json(
                score_input,
                self._score_input(
                    event_manifest_path,
                    mix_manifest_path,
                    is_synthetic=False,
                    gates=gates,
                ),
            )
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_proof_schema_unknown_keys_and_stale_mixdown_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, runtime_proof, review_proof = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=False)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"
            gates = self._production_gate_statuses()

            _write_runtime_proof(
                runtime_proof,
                run_id="run_wave30",
                mix_id="mix_001",
                event_manifest_sha256=_sha256(event_manifest_path),
                mixdown_sha256=mix_payload["mixdown_artifact"]["sha256"],
                extra_fields={"schema_name": "wrong_schema"},
            )
            mix_payload["runtime_proof"]["sha256"] = _sha256(runtime_proof)
            _write_json(mix_manifest_path, mix_payload)
            _write_json(
                score_input,
                self._score_input(
                    event_manifest_path,
                    mix_manifest_path,
                    is_synthetic=False,
                    gates=gates,
                ),
            )
            self._score(score_input, qa_report, expect_ok=False)

            _write_runtime_proof(
                runtime_proof,
                run_id="run_wave30",
                mix_id="mix_001",
                event_manifest_sha256=_sha256(event_manifest_path),
                mixdown_sha256=mix_payload["mixdown_artifact"]["sha256"],
            )
            _write_audio_review_proof(
                review_proof,
                run_id="run_wave30",
                mix_id="mix_001",
                event_manifest_sha256=_sha256(event_manifest_path),
                mixdown_sha256=mix_payload["mixdown_artifact"]["sha256"],
                extra_fields={"unexpected_field": True},
            )
            mix_payload["runtime_proof"]["sha256"] = _sha256(runtime_proof)
            mix_payload["audio_review"]["sha256"] = _sha256(review_proof)
            _write_json(mix_manifest_path, mix_payload)
            _write_json(
                score_input,
                self._score_input(
                    event_manifest_path,
                    mix_manifest_path,
                    is_synthetic=False,
                    gates=gates,
                ),
            )
            self._score(score_input, qa_report, expect_ok=False)

            _write_audio_review_proof(
                review_proof,
                run_id="run_wave30",
                mix_id="mix_001",
                event_manifest_sha256=_sha256(event_manifest_path),
                mixdown_sha256=mix_payload["mixdown_artifact"]["sha256"],
            )
            _write_runtime_proof(
                runtime_proof,
                run_id="run_wave30",
                mix_id="mix_001",
                event_manifest_sha256=_sha256(event_manifest_path),
                mixdown_sha256="0" * 64,
            )
            mix_payload["runtime_proof"]["sha256"] = _sha256(runtime_proof)
            mix_payload["audio_review"]["sha256"] = _sha256(review_proof)
            _write_json(mix_manifest_path, mix_payload)
            _write_json(
                score_input,
                self._score_input(
                    event_manifest_path,
                    mix_manifest_path,
                    is_synthetic=False,
                    gates=gates,
                ),
            )
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_attested_loudness_and_clipping_contradictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))

            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["mix_loudness"]["clipping_detected"] = True
            _write_json(mix_manifest_path, mix_payload)
            score_payload = json.loads(score_input.read_text(encoding="utf-8"))
            score_payload["mix_manifest_binding"]["sha256"] = _sha256(mix_manifest_path)
            _write_json(score_input, score_payload)
            self._score(score_input, qa_report, expect_ok=False)

            mix_payload["mix_loudness"]["clipping_detected"] = False
            mix_payload["mix_loudness"]["integrated_lufs"] = -30.0
            _write_json(mix_manifest_path, mix_payload)
            score_payload["mix_manifest_binding"]["sha256"] = _sha256(mix_manifest_path)
            _write_json(score_input, score_payload)
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_invalid_or_tampered_mixdown_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"

            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_path = Path(mix_payload["mixdown_artifact"]["path"])
            mix_path.write_bytes(b"this-is-not-a-wav")
            mix_payload["mixdown_artifact"]["bytes"] = mix_path.stat().st_size
            mix_payload["mixdown_artifact"]["sha256"] = _sha256(mix_path)
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["mix_technical"]["frame_count"] += 5
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_required_event_omission_duplicate_and_extra_event_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"

            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["mix_event_metadata"] = mix_payload["mix_event_metadata"][1:]
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            duplicate = dict(mix_payload["mix_event_metadata"][0])
            mix_payload["mix_event_metadata"].append(duplicate)
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["mix_event_metadata"][0]["audio_event_id"] = "event_extra_999"
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

    def test_scorer_rejects_run_id_and_av_sync_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path, event_manifest_path = self._base_event_packet(tmpdir)
            self._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            score_input = tmpdir / "score_input.json"
            qa_report = tmpdir / "qa_report.json"

            bad_run = self._score_input(event_manifest_path, mix_manifest_path)
            bad_run["run_id"] = "run_mismatch"
            _write_json(score_input, bad_run)
            self._score(score_input, qa_report, expect_ok=False)

            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["av_sync_evidence"]["frame_rate"] = 30.0
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["av_sync_evidence"]["frame_offset"] = 1
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["av_sync_evidence"]["end_frame"] = 4
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

            mix_manifest_path, _, _ = self._make_mix_manifest(tmpdir, event_manifest_path, synthetic=True)
            mix_payload = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_payload["av_sync_evidence"]["end_frame"] = 40
            _write_json(mix_manifest_path, mix_payload)
            _write_json(score_input, self._score_input(event_manifest_path, mix_manifest_path))
            self._score(score_input, qa_report, expect_ok=False)

    def test_local_validator_passes(self) -> None:
        result = _run(
            [
                sys.executable,
                str(VALIDATE_SCRIPT),
                "--root",
                str(REPO_ROOT),
            ],
            expect_ok=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "pass")

    def test_wrapper_reports_missing_validator_cleanly(self) -> None:
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if pwsh is None:
            self.skipTest("PowerShell is unavailable in this environment")
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            result = subprocess.run(
                [
                    pwsh,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(WRAPPER_SCRIPT),
                    "-Root",
                    str(tmpdir),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            combined = f"{result.stdout}\n{result.stderr}"
            self.assertIn("Missing validator script", combined)


if __name__ == "__main__":
    unittest.main()
