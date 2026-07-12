#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
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
SOURCE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_strict_audio_artifact_review.py"
SOURCE_REQUEST_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_request.schema.json"
SOURCE_REPORT_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json"
SOURCE_REGISTRY = REPO_ROOT / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json"
SOURCE_ROW030_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"
SOURCE_WAVE30_HELPER = REPO_ROOT / "Plan/Instructions/QA/Scripts/test_wave30_audio_pipeline_strict.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_pcm_wav(path: Path, *, sample_rate: int = 16000, seconds: float = 0.3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frame = struct.pack("<h", 0)
        handle.writeframes(frame * frame_count)


def _binding(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _fixture_identity(
    *,
    proof_kind: str,
    producer_id: str,
    authority_id: str,
    model: str,
    model_sha256: str,
    synthetic_only: bool = True,
) -> dict[str, Any]:
    return {
        "proof_kind": proof_kind,
        "producer_id": producer_id,
        "engine": "fixture_engine",
        "model": model,
        "model_version": "1.0.0",
        "model_sha256": model_sha256,
        "authority_id": authority_id,
        "synthetic_only": synthetic_only,
    }


class Wave64StrictAudioArtifactReviewTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        (self.root / "Plan/07_IMPLEMENTATION/scripts").mkdir(parents=True, exist_ok=True)
        (self.root / "Plan/08_SCHEMAS").mkdir(parents=True, exist_ok=True)
        (self.root / "Plan/10_REGISTRIES").mkdir(parents=True, exist_ok=True)

        shutil.copy2(SOURCE_SCRIPT, self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_strict_audio_artifact_review.py")
        shutil.copy2(SOURCE_REQUEST_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_strict_audio_review_request.schema.json")
        shutil.copy2(SOURCE_REPORT_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json")
        shutil.copy2(SOURCE_REGISTRY, self.root / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json")
        shutil.copy2(SOURCE_ROW030_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json")
        self.registry_snapshot_sha = _sha256(self.root / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json")

        self._write_minimal_wave30_schemas()
        self._build_base_artifacts()
        self.script_path = self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_strict_audio_artifact_review.py"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_minimal_wave30_schemas(self) -> None:
        event_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": ["run_id", "is_synthetic"],
            "properties": {
                "run_id": {"type": "string"},
                "is_synthetic": {"type": "boolean"},
            },
        }
        mix_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": ["run_id", "is_synthetic", "event_manifest_bindings", "mixdown_artifact", "mix_technical"],
            "properties": {
                "run_id": {"type": "string"},
                "is_synthetic": {"type": "boolean"},
                "event_manifest_bindings": {"type": "array"},
                "mixdown_artifact": {"type": "object"},
                "mix_technical": {"type": "object"},
            },
        }
        qa_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": [
                "run_id",
                "is_synthetic",
                "event_manifest_binding",
                "mix_manifest_binding",
                "hard_gate_statuses",
                "proof_verification",
                "computed_flags",
                "promotion_decision",
            ],
            "properties": {
                "run_id": {"type": "string"},
                "is_synthetic": {"type": "boolean"},
                "event_manifest_binding": {"type": "object"},
                "mix_manifest_binding": {"type": "object"},
                "hard_gate_statuses": {"type": "object"},
                "proof_verification": {"type": "object"},
                "computed_flags": {"type": "object"},
                "promotion_decision": {"type": "string"},
            },
        }
        _write_json(self.root / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json", event_schema)
        _write_json(self.root / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json", mix_schema)
        _write_json(self.root / "Plan/08_SCHEMAS/wave30_audio_qa_report.schema.json", qa_schema)

    def _build_row030_report(self) -> dict[str, Any]:
        source_video = self.tmp_artifacts / "source_video.bin"
        final_mux = self.tmp_artifacts / "final_mux.bin"
        anchor_proof = self.tmp_artifacts / "anchor_measurement.json"
        gate_registry = self.tmp_artifacts / "wave64_gate_registry.json"
        runtime_proof = self.tmp_artifacts / "runtime_proof.json"
        playback_proof = self.tmp_artifacts / "row030_playback.json"
        for path, payload in (
            (source_video, b"video"),
            (final_mux, b"mux"),
            (anchor_proof, b"{}"),
            (gate_registry, b"{}"),
            (runtime_proof, b"{}"),
            (playback_proof, b"{}"),
        ):
            if isinstance(payload, bytes):
                path.write_bytes(payload)
            else:
                _write_json(path, payload)
        return {
            "schema_name": "wave64_av_sync_certification_report",
            "report_version": 1,
            "run_id": "run_wave64_audio",
            "scene_id": "scene_001",
            "shot_id": "shot_001",
            "take_id": "take_001",
            "is_synthetic": True,
            "evidence_origin": "technical_capture",
            "pyav_version": "13.1.0",
            "request_binding": {"path": str(self.request_path.resolve()), "sha256": _sha256(self.request_path)},
            "artifact_bindings": {
                "source_video_artifact": _binding(source_video),
                "source_audio_mix_artifact": _binding(self.wav_path),
                "final_mux_artifact": _binding(final_mux),
                "wave30_event_manifest": {
                    "path": str(self.event_manifest_path.resolve()),
                    "sha256": _sha256(self.event_manifest_path),
                },
                "wave30_mix_manifest": {
                    "path": str(self.mix_manifest_path.resolve()),
                    "sha256": _sha256(self.mix_manifest_path),
                },
                "observed_anchor_measurement_proof": {
                    "path": str(anchor_proof.resolve()),
                    "sha256": _sha256(anchor_proof),
                },
                "playback_proof": {"path": str(playback_proof.resolve()), "sha256": _sha256(playback_proof)},
                "runtime_proof": {"path": str(runtime_proof.resolve()), "sha256": _sha256(runtime_proof)},
                "production_certification_bundle": None,
                "wave64_gate_registry": {"path": str(gate_registry.resolve()), "sha256": _sha256(gate_registry)},
            },
            "metrics": {
                "source_video_decode": {
                    "container_format": "mp4",
                    "stream_count_video": 1,
                    "stream_count_audio": 1,
                    "codec": "h264",
                    "time_base": 0.001,
                    "frame_rate": 24.0,
                    "width": 1920,
                    "height": 1080,
                    "frame_count": 240,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 10.0,
                    "duration_seconds": 10.0,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_video_hash": "a" * 64,
                },
                "mux_video_decode": {
                    "container_format": "mp4",
                    "stream_count_video": 1,
                    "stream_count_audio": 1,
                    "codec": "h264",
                    "time_base": 0.001,
                    "frame_rate": 24.0,
                    "width": 1920,
                    "height": 1080,
                    "frame_count": 240,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 10.0,
                    "duration_seconds": 10.0,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_video_hash": "b" * 64,
                },
                "source_audio_decode": {
                    "stream_count_audio": 1,
                    "codec": "pcm_s16le",
                    "time_base": 0.0000625,
                    "sample_rate_hz": 16000,
                    "channels": 1,
                    "channel_layout": "mono",
                    "sample_count": 4800,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 0.3,
                    "duration_seconds": 0.3,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_audio_hash": "c" * 64,
                },
                "mux_audio_decode": {
                    "stream_count_audio": 1,
                    "codec": "aac",
                    "time_base": 0.0000625,
                    "sample_rate_hz": 16000,
                    "channels": 1,
                    "channel_layout": "mono",
                    "sample_count": 4800,
                    "first_pts_seconds": 0.0,
                    "last_pts_seconds": 0.3,
                    "duration_seconds": 0.3,
                    "packet_pts_monotonic": True,
                    "frame_pts_monotonic": True,
                    "missing_packet_pts_count": 0,
                    "missing_frame_pts_count": 0,
                    "decoded_audio_hash": "d" * 64,
                },
                "lineage": {
                    "video_hash_match": True,
                    "audio_hash_match": True,
                    "video_frame_count_match": True,
                    "audio_sample_count_match": True,
                    "stream_count_match": True,
                    "video_codec_match": True,
                    "audio_codec_match": True,
                },
                "sync": {
                    "audio_start_offset_seconds": 0.0,
                    "endpoint_delta_seconds": 0.0,
                    "cumulative_endpoint_drift_seconds": 0.0,
                },
                "anchors": {
                    "required_anchor_event_count": 0,
                    "observed_anchor_count": 0,
                    "missing_anchor_count": 0,
                    "extra_anchor_count": 0,
                    "duplicate_anchor_count": 0,
                    "measurement_producer": None,
                },
                "proofs": {
                    "playback_producer": None,
                    "runtime_producer": None,
                },
            },
            "gates": {
                "sync_offset_threshold": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "drift_check": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "mux_manifest": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "event_owner_alignment": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "av_review_record": {"status": "PASS", "blockers": [], "artifact_bindings": []},
                "production_runtime_proof": {"status": "BLOCKED", "blockers": ["not required"], "artifact_bindings": []},
                "production_av_sync_authority": {
                    "status": "BLOCKED",
                    "blockers": ["not required"],
                    "artifact_bindings": [],
                },
                "overall_pass": {"status": "BLOCKED", "blockers": ["prod gates blocked"], "artifact_bindings": []},
            },
            "blockers": [],
            "overall_pass": False,
        }

    def _build_base_artifacts(self) -> None:
        self.tmp_artifacts = self.root / "tmp_artifacts"
        self.tmp_artifacts.mkdir(parents=True, exist_ok=True)
        self.wav_path = self.tmp_artifacts / "mix.wav"
        _write_pcm_wav(self.wav_path)

        self.event_manifest_path = self.tmp_artifacts / "event_manifest.json"
        self.mix_manifest_path = self.tmp_artifacts / "mix_manifest.json"
        self.qa_report_path = self.tmp_artifacts / "qa_report.json"
        self.prompt_reference_path = self.tmp_artifacts / "prompt_reference.json"
        self.prompt_alignment_path = self.tmp_artifacts / "prompt_alignment.json"
        self.playback_path = self.tmp_artifacts / "playback.json"
        self.row030_path = self.tmp_artifacts / "row030.json"
        self.production_bundle_path = self.tmp_artifacts / "production_bundle.json"
        self.request_path = self.tmp_artifacts / "request.json"
        self.output_path = self.tmp_artifacts / "report.json"

        event_manifest = {
            "run_id": "run_wave64_audio",
            "is_synthetic": True,
            "audio_events": [],
        }
        _write_json(self.event_manifest_path, event_manifest)
        event_binding = _binding(self.event_manifest_path)

        mix_manifest = {
            "run_id": "run_wave64_audio",
            "is_synthetic": True,
            "event_manifest_bindings": [{"path": event_binding["path"], "sha256": event_binding["sha256"]}],
            "mixdown_artifact": {"path": str(self.wav_path.resolve()), "sha256": _sha256(self.wav_path)},
            "mix_technical": {
                "sample_rate_hz": 16000,
                "channels": 1,
                "sample_width_bytes": 2,
                "frame_count": int(16000 * 0.3),
                "duration_seconds": 0.3,
            },
        }
        _write_json(self.mix_manifest_path, mix_manifest)
        mix_binding = _binding(self.mix_manifest_path)

        hard_gates = {
            "decode": "pass",
            "duration": "pass",
            "loudness": "pass",
            "clipping": "pass",
            "sync": "pass",
            "voice_identity": "pass",
            "event_coverage": "pass",
            "mix_balance": "pass",
            "artifact_manifest": "pass",
            "runtime_proof": "pass",
            "audio_review": "pass",
        }
        qa_report = {
            "run_id": "run_wave64_audio",
            "is_synthetic": True,
            "event_manifest_binding": {"path": event_binding["path"], "sha256": event_binding["sha256"]},
            "mix_manifest_binding": {"path": mix_binding["path"], "sha256": mix_binding["sha256"]},
            "hard_gate_statuses": hard_gates,
            "proof_verification": {
                "runtime_proof_verified": True,
                "audio_review_verified": True,
                "artifact_bindings_verified": True,
            },
            "computed_flags": {"all_hard_gates_passed": True, "production_eligible": True},
            "promotion_decision": "promote",
        }
        _write_json(self.qa_report_path, qa_report)

        prompt_reference = {
            "schema_name": "wave64_prompt_reference",
            "prompt_kind": "speech",
            "expected_text": "hello there adventurer",
            "expected_attributes": [{"name": "tone", "value": "calm"}],
            "video_pairing_required": False,
        }
        _write_json(self.prompt_reference_path, prompt_reference)
        prompt_ref_binding = _binding(self.prompt_reference_path)

        prompt_alignment = {
            "schema_name": "wave64_prompt_alignment_proof",
            **_fixture_identity(
                proof_kind="prompt_alignment",
                producer_id="fixture_prompt_producer",
                authority_id="fixture_prompt_authority_v1",
                model="fixture_prompt_model",
                model_sha256="1111111111111111111111111111111111111111111111111111111111111111",
            ),
            "audio_sha256": _sha256(self.wav_path),
            "prompt_reference_sha256": prompt_ref_binding["sha256"],
            "observed_transcript": "hello there adventurer",
            "observed_attributes": {"tone": "calm"},
            "self_authorized": False,
            "is_synthetic": True,
            "production_evidence": False,
        }
        _write_json(self.prompt_alignment_path, prompt_alignment)

        playback = {
            "schema_name": "wave64_playback_review_proof",
            **_fixture_identity(
                proof_kind="playback_review",
                producer_id="fixture_playback_producer",
                authority_id="fixture_playback_authority_v1",
                model="fixture_playback_model",
                model_sha256="2222222222222222222222222222222222222222222222222222222222222222",
            ),
            "audio_sha256": _sha256(self.wav_path),
            "is_synthetic": True,
            "production_evidence": False,
            "self_authorized": False,
            "sections_reviewed": ["beginning", "middle", "end", "loud", "quiet", "transitions"],
            "category_scores": {
                "intelligibility": 5,
                "cleanliness": 5,
                "stylistic_fit": 5,
                "technical_consistency": 5,
                "content_correctness": 5,
            },
            "defects": [],
        }
        _write_json(self.playback_path, playback)

        _write_json(self.request_path, {"seed": "seed"})
        _write_json(self.row030_path, self._build_row030_report())

        bundle = {
            "schema_name": "wave64_production_review_bundle",
            **_fixture_identity(
                proof_kind="production_review",
                producer_id="fixture_production_producer",
                authority_id="fixture_production_authority_v1",
                model="fixture_production_model",
                model_sha256="3333333333333333333333333333333333333333333333333333333333333333",
                synthetic_only=False,
            ),
            "is_synthetic": False,
            "production_evidence": True,
            "bundle_sha256": "placeholder",
            "revoked": False,
        }
        _write_json(self.production_bundle_path, bundle)
        bundle["bundle_sha256"] = _sha256(self.production_bundle_path)
        _write_json(self.production_bundle_path, bundle)

        self.base_request = {
            "schema_name": "wave64_strict_audio_review_request",
            "request_version": 1,
            "run_id": "run_wave64_audio",
            "is_synthetic": True,
            "capture_mode": "technical_capture",
            "mix_wav_binding": _binding(self.wav_path),
            "wave30_event_manifest_binding": _binding(self.event_manifest_path),
            "wave30_mix_manifest_binding": _binding(self.mix_manifest_path),
            "wave30_qa_report_binding": _binding(self.qa_report_path),
            "prompt_reference_binding": _binding(self.prompt_reference_path),
            "prompt_alignment_proof_binding": _binding(self.prompt_alignment_path),
            "playback_proof_binding": _binding(self.playback_path),
            "row030_av_sync_report_binding": _binding(self.row030_path),
            "production_review_bundle_binding": _binding(self.production_bundle_path),
        }
        _write_json(self.request_path, self.base_request)

    def _run_eval(
        self,
        request_payload: dict[str, Any],
        *,
        output_path: Path | None = None,
        preserve_output: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        _write_json(self.request_path, request_payload)
        if output_path is None:
            output_path = self.output_path
        if output_path.exists() and not preserve_output:
            output_path.unlink()
        return subprocess.run(
            [sys.executable, str(self.script_path), "--input", str(self.request_path), "--output", str(output_path)],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _load_report(self) -> dict[str, Any]:
        return json.loads(self.output_path.read_text(encoding="utf-8"))

    def _set_non_synthetic_lineage(self, request: dict[str, Any]) -> None:
        request["is_synthetic"] = False
        event_manifest = json.loads(self.event_manifest_path.read_text(encoding="utf-8"))
        event_manifest["is_synthetic"] = False
        _write_json(self.event_manifest_path, event_manifest)
        request["wave30_event_manifest_binding"] = _binding(self.event_manifest_path)

        mix_manifest = json.loads(self.mix_manifest_path.read_text(encoding="utf-8"))
        mix_manifest["is_synthetic"] = False
        mix_manifest["event_manifest_bindings"][0]["sha256"] = request["wave30_event_manifest_binding"]["sha256"]
        _write_json(self.mix_manifest_path, mix_manifest)
        request["wave30_mix_manifest_binding"] = _binding(self.mix_manifest_path)

        qa_report = json.loads(self.qa_report_path.read_text(encoding="utf-8"))
        qa_report["is_synthetic"] = False
        qa_report["event_manifest_binding"]["sha256"] = request["wave30_event_manifest_binding"]["sha256"]
        qa_report["mix_manifest_binding"]["sha256"] = request["wave30_mix_manifest_binding"]["sha256"]
        qa_report["computed_flags"]["all_hard_gates_passed"] = True
        qa_report["computed_flags"]["production_eligible"] = True
        qa_report["promotion_decision"] = "promote"
        _write_json(self.qa_report_path, qa_report)
        request["wave30_qa_report_binding"] = _binding(self.qa_report_path)

        row030 = json.loads(self.row030_path.read_text(encoding="utf-8"))
        row030["is_synthetic"] = False
        row030["evidence_origin"] = request["capture_mode"]
        _write_json(self.row030_path, row030)
        request["row030_av_sync_report_binding"] = _binding(self.row030_path)

    def _require_video_pairing(self, request: dict[str, Any]) -> None:
        prompt_reference = json.loads(self.prompt_reference_path.read_text(encoding="utf-8"))
        prompt_reference["video_pairing_required"] = True
        _write_json(self.prompt_reference_path, prompt_reference)
        request["prompt_reference_binding"] = _binding(self.prompt_reference_path)

    def test_synthetic_contract_passes_technical_gates_but_blocks_production(self) -> None:
        result = self._run_eval(copy.deepcopy(self.base_request))
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = self._load_report()
        self.assertEqual(report["gates"]["audio_metadata_check"], "PASS")
        self.assertEqual(report["gates"]["prompt_alignment"], "PASS")
        self.assertEqual(report["gates"]["playback_review"], "PASS")
        self.assertEqual(report["gates"]["sync_evidence"], "PASS")
        self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")

    def test_relabel_mode_forces_promotion_block(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["capture_mode"] = "hand_authored_relabel"
        result = self._run_eval(request)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "synthetic-only prompt producer cannot be used for hand_authored_relabel capture mode",
            self._load_report()["blockers"],
        )

    def test_metadata_tamper_fails_audio_metadata_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        mix_manifest = json.loads(self.mix_manifest_path.read_text(encoding="utf-8"))
        mix_manifest["mix_technical"]["frame_count"] += 1
        _write_json(self.mix_manifest_path, mix_manifest)
        request["wave30_mix_manifest_binding"] = _binding(self.mix_manifest_path)
        qa_report = json.loads(self.qa_report_path.read_text(encoding="utf-8"))
        qa_report["mix_manifest_binding"]["sha256"] = request["wave30_mix_manifest_binding"]["sha256"]
        _write_json(self.qa_report_path, qa_report)
        request["wave30_qa_report_binding"] = _binding(self.qa_report_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["audio_metadata_check"], "FAIL")

    def test_hash_mismatch_is_invalid_input(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["mix_wav_binding"]["sha256"] = "0" * 64
        result = self._run_eval(request)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output_path.exists())

    def test_wav_tamper_fails_audio_metadata_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        self.wav_path.write_bytes(b"not-a-wav")
        request["mix_wav_binding"] = _binding(self.wav_path)
        mix_manifest = json.loads(self.mix_manifest_path.read_text(encoding="utf-8"))
        mix_manifest["mixdown_artifact"]["sha256"] = request["mix_wav_binding"]["sha256"]
        mix_manifest["mix_technical"]["frame_count"] = 1
        mix_manifest["mix_technical"]["duration_seconds"] = 0.0
        _write_json(self.mix_manifest_path, mix_manifest)
        request["wave30_mix_manifest_binding"] = _binding(self.mix_manifest_path)
        qa_report = json.loads(self.qa_report_path.read_text(encoding="utf-8"))
        qa_report["mix_manifest_binding"]["sha256"] = request["wave30_mix_manifest_binding"]["sha256"]
        _write_json(self.qa_report_path, qa_report)
        request["wave30_qa_report_binding"] = _binding(self.qa_report_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["audio_metadata_check"], "FAIL")

    def test_upstream_report_technical_gate_fail_closes_audio_metadata(self) -> None:
        request = copy.deepcopy(self.base_request)
        qa_report = json.loads(self.qa_report_path.read_text(encoding="utf-8"))
        qa_report["hard_gate_statuses"]["decode"] = "fail"
        _write_json(self.qa_report_path, qa_report)
        request["wave30_qa_report_binding"] = _binding(self.qa_report_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["audio_metadata_check"], "FAIL")

    def test_prompt_alignment_wer_failure_fails_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["observed_transcript"] = "completely unrelated words"
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "FAIL")

    def test_prompt_alignment_attribute_failure_fails_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["observed_attributes"] = {"tone": "angry"}
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "FAIL")

    def test_prompt_alignment_unapproved_producer_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["producer_id"] = "unknown_authority"
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_prompt_alignment_self_authorized_fails_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["self_authorized"] = True
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "FAIL")

    def test_playback_missing_proof_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        request.pop("playback_proof_binding")
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_missing_sections_fails_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["sections_reviewed"] = ["beginning", "middle", "end"]
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "FAIL")

    def test_playback_out_of_range_score_fails_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["category_scores"]["cleanliness"] = 6
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "FAIL")

    def test_playback_blocking_defect_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["defects"] = [{"code": "SEVERE_GLITCH", "severity": "high", "description": "blocking"}]
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_blocking_defect_lowercase_code_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["defects"] = [{"code": "major_clipping", "severity": "low", "description": "blocking"}]
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_blocking_defect_mixed_case_code_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["defects"] = [{"code": "SeVeRe_GlItCh", "severity": "low", "description": "blocking"}]
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_sync_pairing_required_without_row030_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._require_video_pairing(request)
        request.pop("row030_av_sync_report_binding")
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "BLOCKED")

    def test_supplied_row030_cannot_be_bypassed_by_prompt_reference(self) -> None:
        request = copy.deepcopy(self.base_request)
        row030 = json.loads(self.row030_path.read_text(encoding="utf-8"))
        row030["gates"]["av_review_record"]["status"] = "BLOCKED"
        _write_json(self.row030_path, row030)
        request["row030_av_sync_report_binding"] = _binding(self.row030_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "FAIL")

    def test_sync_schema_valid_row030_technical_pass(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._require_video_pairing(request)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "PASS")

    def test_sync_old_duck_typed_row030_fails_closed(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._require_video_pairing(request)
        row030 = {
            "source_audio_sha256": _sha256(self.wav_path),
            "gate_statuses": {
                "sync_offset_threshold": "PASS",
                "drift_check": "PASS",
                "mux_manifest": "PASS",
                "av_review_record": "PASS",
            },
        }
        _write_json(self.row030_path, row030)
        request["row030_av_sync_report_binding"] = _binding(self.row030_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "FAIL")

    def test_sync_source_audio_binding_mismatch_fails(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._require_video_pairing(request)
        row030 = json.loads(self.row030_path.read_text(encoding="utf-8"))
        row030["artifact_bindings"]["source_audio_mix_artifact"]["sha256"] = "0" * 64
        _write_json(self.row030_path, row030)
        request["row030_av_sync_report_binding"] = _binding(self.row030_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "FAIL")

    def _assert_sync_required_gate_non_pass_fails(self, gate_name: str, status: str) -> None:
        request = copy.deepcopy(self.base_request)
        self._require_video_pairing(request)
        row030 = json.loads(self.row030_path.read_text(encoding="utf-8"))
        row030["gates"][gate_name]["status"] = status
        _write_json(self.row030_path, row030)
        request["row030_av_sync_report_binding"] = _binding(self.row030_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "FAIL")

    def test_sync_gate_sync_offset_threshold_non_pass_fails(self) -> None:
        self._assert_sync_required_gate_non_pass_fails("sync_offset_threshold", "FAIL")

    def test_sync_gate_drift_check_non_pass_fails(self) -> None:
        self._assert_sync_required_gate_non_pass_fails("drift_check", "BLOCKED")

    def test_sync_gate_mux_manifest_non_pass_fails(self) -> None:
        self._assert_sync_required_gate_non_pass_fails("mux_manifest", "FAIL")

    def test_sync_gate_event_owner_alignment_non_pass_fails(self) -> None:
        self._assert_sync_required_gate_non_pass_fails("event_owner_alignment", "FAIL")

    def test_sync_gate_av_review_record_non_pass_fails(self) -> None:
        self._assert_sync_required_gate_non_pass_fails("av_review_record", "BLOCKED")

    def test_sync_production_only_blocked_states_do_not_poison_technical_sync(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._require_video_pairing(request)
        row030 = json.loads(self.row030_path.read_text(encoding="utf-8"))
        row030["gates"]["production_runtime_proof"]["status"] = "BLOCKED"
        row030["gates"]["production_av_sync_authority"]["status"] = "BLOCKED"
        row030["gates"]["overall_pass"]["status"] = "BLOCKED"
        _write_json(self.row030_path, row030)
        request["row030_av_sync_report_binding"] = _binding(self.row030_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["sync_evidence"], "PASS")

    def test_upstream_runtime_proof_fail_forged_production_flag_blocks_promotion(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._set_non_synthetic_lineage(request)
        qa_report = json.loads(self.qa_report_path.read_text(encoding="utf-8"))
        qa_report["hard_gate_statuses"]["runtime_proof"] = "fail"
        qa_report["computed_flags"]["production_eligible"] = True
        _write_json(self.qa_report_path, qa_report)
        request["wave30_qa_report_binding"] = _binding(self.qa_report_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        report = self._load_report()
        self.assertEqual(report["gates"]["audio_metadata_check"], "PASS")
        self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")

    def test_upstream_audio_review_block_forged_production_flag_blocks_promotion(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._set_non_synthetic_lineage(request)
        qa_report = json.loads(self.qa_report_path.read_text(encoding="utf-8"))
        qa_report["hard_gate_statuses"]["audio_review"] = "block"
        qa_report["computed_flags"]["production_eligible"] = True
        _write_json(self.qa_report_path, qa_report)
        request["wave30_qa_report_binding"] = _binding(self.qa_report_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        report = self._load_report()
        self.assertEqual(report["gates"]["audio_metadata_check"], "PASS")
        self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")

    def test_cross_role_prompt_playback_producers_block_promotion(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._set_non_synthetic_lineage(request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        playback["producer_id"] = prompt_alignment["producer_id"]
        playback["engine"] = prompt_alignment["engine"]
        playback["model"] = prompt_alignment["model"]
        playback["model_version"] = prompt_alignment["model_version"]
        playback["model_sha256"] = prompt_alignment["model_sha256"]
        playback["authority_id"] = prompt_alignment["authority_id"]
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_empty_allowlist_blocks_promotion_for_non_synthetic(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._set_non_synthetic_lineage(request)
        self.assertEqual(self._run_eval(request).returncode, 2)
        report = self._load_report()
        self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")
        self.assertIn("prompt alignment synthetic-only producer cannot be used on non-synthetic request", report["blockers"])

    def test_prompt_identity_engine_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["engine"] = "tampered_engine"
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_prompt_identity_model_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["model"] = "tampered_model"
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_prompt_identity_model_version_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["model_version"] = "9.9.9"
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_prompt_identity_model_sha256_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["model_sha256"] = "f" * 64
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_prompt_identity_authority_id_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["authority_id"] = "tampered_authority"
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_playback_identity_engine_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["engine"] = "tampered_engine"
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_identity_model_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["model"] = "tampered_model"
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_identity_model_version_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["model_version"] = "9.9.9"
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_identity_model_sha256_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["model_sha256"] = "f" * 64
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_identity_authority_id_tamper_blocks_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["authority_id"] = "tampered_authority"
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_playback_self_authorized_fails_gate(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["self_authorized"] = True
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "FAIL")

    def test_non_synthetic_request_with_synthetic_only_producers_blocks_prompt_and_playback(self) -> None:
        request = copy.deepcopy(self.base_request)
        self._set_non_synthetic_lineage(request)
        result = self._run_eval(request)
        self.assertEqual(result.returncode, 2)
        report = self._load_report()
        self.assertEqual(report["gates"]["prompt_alignment"], "BLOCKED")
        self.assertEqual(report["gates"]["playback_review"], "BLOCKED")

    def test_synthetic_only_prompt_with_production_evidence_true_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        prompt_alignment = json.loads(self.prompt_alignment_path.read_text(encoding="utf-8"))
        prompt_alignment["production_evidence"] = True
        _write_json(self.prompt_alignment_path, prompt_alignment)
        request["prompt_alignment_proof_binding"] = _binding(self.prompt_alignment_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["prompt_alignment"], "BLOCKED")

    def test_synthetic_only_playback_with_production_evidence_true_blocks(self) -> None:
        request = copy.deepcopy(self.base_request)
        playback = json.loads(self.playback_path.read_text(encoding="utf-8"))
        playback["production_evidence"] = True
        _write_json(self.playback_path, playback)
        request["playback_proof_binding"] = _binding(self.playback_path)
        self.assertEqual(self._run_eval(request).returncode, 2)
        self.assertEqual(self._load_report()["gates"]["playback_review"], "BLOCKED")

    def test_registry_cross_role_authority_collision_is_invalid_input(self) -> None:
        registry_path = self.root / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["playback_review_allowlist"][0]["authority_id"] = registry["prompt_alignment_allowlist"][0]["authority_id"]
        _write_json(registry_path, registry)
        result = self._run_eval(copy.deepcopy(self.base_request))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output_path.exists())

    def test_canonical_integration_wave30_helper_and_real_schemas(self) -> None:
        runtime_root = REPO_ROOT / "runtime_artifacts" / "tmp_wave64_strict_integration"
        if runtime_root.exists():
            shutil.rmtree(runtime_root)
        runtime_root.mkdir(parents=True, exist_ok=True)
        try:
            helper_spec = importlib.util.spec_from_file_location("wave30_helper_for_wave64", SOURCE_WAVE30_HELPER)
            assert helper_spec and helper_spec.loader
            helper_module = importlib.util.module_from_spec(helper_spec)
            helper_spec.loader.exec_module(helper_module)
            helper = helper_module.Wave30AudioPipelineStrictTests(methodName="runTest")
            packet_path, event_manifest_path = helper._base_event_packet(runtime_root)
            helper._compile(packet_path, event_manifest_path, expect_ok=True)
            mix_manifest_path, _, _ = helper._make_mix_manifest(runtime_root, event_manifest_path, synthetic=True)
            score_input_path = runtime_root / "score_input.json"
            qa_report_path = runtime_root / "qa_report.json"
            helper_module._write_json(score_input_path, helper._score_input(event_manifest_path, mix_manifest_path))
            helper._score(score_input_path, qa_report_path, expect_ok=True)

            mix_manifest = json.loads(mix_manifest_path.read_text(encoding="utf-8"))
            mix_wav_path = Path(mix_manifest["mixdown_artifact"]["path"])
            prompt_reference_path = runtime_root / "prompt_reference.json"
            prompt_alignment_path = runtime_root / "prompt_alignment.json"
            playback_path = runtime_root / "playback.json"
            request_path = runtime_root / "request.json"
            output_path = runtime_root / "report.json"

            prompt_reference = {
                "schema_name": "wave64_prompt_reference",
                "prompt_kind": "speech",
                "expected_text": "hello there adventurer",
                "expected_attributes": [{"name": "tone", "value": "calm"}],
                "video_pairing_required": False,
            }
            _write_json(prompt_reference_path, prompt_reference)
            prompt_ref_binding = _binding(prompt_reference_path)

            prompt_alignment = {
                "schema_name": "wave64_prompt_alignment_proof",
                **_fixture_identity(
                    proof_kind="prompt_alignment",
                    producer_id="fixture_prompt_producer",
                    authority_id="fixture_prompt_authority_v1",
                    model="fixture_prompt_model",
                    model_sha256="1111111111111111111111111111111111111111111111111111111111111111",
                ),
                "audio_sha256": _sha256(mix_wav_path),
                "prompt_reference_sha256": prompt_ref_binding["sha256"],
                "observed_transcript": "hello there adventurer",
                "observed_attributes": {"tone": "calm"},
                "self_authorized": False,
                "is_synthetic": True,
                "production_evidence": False,
            }
            _write_json(prompt_alignment_path, prompt_alignment)

            playback = {
                "schema_name": "wave64_playback_review_proof",
                **_fixture_identity(
                    proof_kind="playback_review",
                    producer_id="fixture_playback_producer",
                    authority_id="fixture_playback_authority_v1",
                    model="fixture_playback_model",
                    model_sha256="2222222222222222222222222222222222222222222222222222222222222222",
                ),
                "audio_sha256": _sha256(mix_wav_path),
                "is_synthetic": True,
                "production_evidence": False,
                "self_authorized": False,
                "sections_reviewed": ["beginning", "middle", "end", "loud", "quiet", "transitions"],
                "category_scores": {
                    "intelligibility": 5,
                    "cleanliness": 5,
                    "stylistic_fit": 5,
                    "technical_consistency": 5,
                    "content_correctness": 5,
                },
                "defects": [],
            }
            _write_json(playback_path, playback)

            request = {
                "schema_name": "wave64_strict_audio_review_request",
                "request_version": 1,
                "run_id": "run_wave30",
                "is_synthetic": True,
                "capture_mode": "technical_capture",
                "mix_wav_binding": _binding(mix_wav_path),
                "wave30_event_manifest_binding": _binding(event_manifest_path),
                "wave30_mix_manifest_binding": _binding(mix_manifest_path),
                "wave30_qa_report_binding": _binding(qa_report_path),
                "prompt_reference_binding": _binding(prompt_reference_path),
                "prompt_alignment_proof_binding": _binding(prompt_alignment_path),
                "playback_proof_binding": _binding(playback_path),
            }
            _write_json(request_path, request)

            result = subprocess.run(
                [sys.executable, str(SOURCE_SCRIPT), "--input", str(request_path), "--output", str(output_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["gates"]["audio_metadata_check"], "PASS")
            self.assertEqual(report["gates"]["prompt_alignment"], "PASS")
            self.assertEqual(report["gates"]["playback_review"], "PASS")
            self.assertEqual(report["gates"]["sync_evidence"], "PASS")
            self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")
        finally:
            shutil.rmtree(runtime_root, ignore_errors=True)

    def test_nonfinite_json_is_invalid_input(self) -> None:
        raw_request = (
            '{"schema_name":"wave64_strict_audio_review_request","request_version":1,"run_id":"x","is_synthetic":true,'
            '"capture_mode":"technical_capture","mix_wav_binding":{"path":"a","sha256":"%s","bytes":1},'
            '"wave30_event_manifest_binding":{"path":"a","sha256":"%s","bytes":1},'
            '"wave30_mix_manifest_binding":{"path":"a","sha256":"%s","bytes":1},'
            '"wave30_qa_report_binding":{"path":"a","sha256":"%s","bytes":1},'
            '"prompt_reference_binding":{"path":"a","sha256":"%s","bytes":1},'
            '"prompt_alignment_proof_binding":{"path":"a","sha256":"%s","bytes":1},"bad":NaN}'
        ) % ("0" * 64, "0" * 64, "0" * 64, "0" * 64, "0" * 64, "0" * 64)
        self.request_path.write_text(raw_request, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--input", str(self.request_path), "--output", str(self.output_path)],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output_path.exists())

    def test_unknown_request_key_is_invalid_input(self) -> None:
        request = copy.deepcopy(self.base_request)
        request["unknown_key"] = True
        self.assertEqual(self._run_eval(request).returncode, 1)

    def test_root_escape_is_invalid_input(self) -> None:
        outside = Path(tempfile.gettempdir()) / "outside_audio_file.bin"
        outside.write_bytes(b"outside")
        request = copy.deepcopy(self.base_request)
        request["mix_wav_binding"] = _binding(outside)
        self.assertEqual(self._run_eval(request).returncode, 1)

    def test_output_collision_is_invalid_and_preserves_existing_file(self) -> None:
        collision_path = self.output_path
        collision_path.write_text('{"existing":true}\n', encoding="utf-8")
        request = copy.deepcopy(self.base_request)
        result = self._run_eval(request, output_path=collision_path, preserve_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(collision_path.read_text(encoding="utf-8"), '{"existing":true}\n')

    def test_invalid_request_fails_without_writing_output(self) -> None:
        fresh_output = self.root / "tmp_artifacts/no_write_expected.json"
        bad_request = copy.deepcopy(self.base_request)
        bad_request["request_version"] = "bad"
        result = self._run_eval(bad_request, output_path=fresh_output)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(fresh_output.exists())

    def test_registry_unchanged_after_evaluation(self) -> None:
        result = self._run_eval(copy.deepcopy(self.base_request))
        self.assertEqual(result.returncode, 2)
        registry_path = self.root / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json"
        self.assertEqual(_sha256(registry_path), self.registry_snapshot_sha)


if __name__ == "__main__":
    unittest.main()
