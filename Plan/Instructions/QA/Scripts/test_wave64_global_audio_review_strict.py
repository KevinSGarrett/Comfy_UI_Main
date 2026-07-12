#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import math
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
SOURCE_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_global_audio_review.py"
SOURCE_REQUEST_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_request.schema.json"
SOURCE_REPORT_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json"
SOURCE_REGISTRY = REPO_ROOT / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"
SOURCE_ROW030_SCHEMA = REPO_ROOT / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _binding(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _write_wav(path: Path, channels: int, sample_rate: int, frames: list[tuple[float, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        packed = bytearray()
        for frame in frames:
            for value in frame:
                val = max(-1.0, min(1.0, value))
                packed.extend(struct.pack("<h", int(round(val * 32767.0))))
        handle.writeframes(bytes(packed))


class Wave64GlobalAudioReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        (self.root / "Plan/07_IMPLEMENTATION/scripts").mkdir(parents=True, exist_ok=True)
        (self.root / "Plan/08_SCHEMAS").mkdir(parents=True, exist_ok=True)
        (self.root / "Plan/10_REGISTRIES").mkdir(parents=True, exist_ok=True)
        (self.root / "runtime_artifacts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_SCRIPT, self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_global_audio_review.py")
        shutil.copy2(SOURCE_REQUEST_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_global_audio_review_request.schema.json")
        shutil.copy2(SOURCE_REPORT_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_global_audio_review_report.schema.json")
        shutil.copy2(SOURCE_REGISTRY, self.root / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json")
        shutil.copy2(SOURCE_ROW030_SCHEMA, self.root / "Plan/08_SCHEMAS/wave64_av_sync_certification_report.schema.json")
        self._write_supporting_schemas()
        self._build_base_fixtures()
        self.registry_snapshot_sha = _sha256(self.root / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_supporting_schemas(self) -> None:
        row031_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": ["run_id", "is_synthetic", "capture_mode", "artifact_bindings", "gates"],
        }
        event_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": ["run_id", "is_synthetic", "scene_id", "audio_events"],
        }
        mix_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": ["run_id", "is_synthetic", "scene_id", "event_manifest_bindings", "mixdown_artifact", "mix_event_metadata"],
        }
        qa_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": True,
            "required": ["run_id", "is_synthetic", "event_manifest_binding", "mix_manifest_binding", "hard_gate_statuses", "proof_verification", "computed_flags", "promotion_decision"],
        }
        _write_json(self.root / "Plan/08_SCHEMAS/wave64_strict_audio_review_report.schema.json", row031_schema)
        _write_json(self.root / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json", event_schema)
        _write_json(self.root / "Plan/08_SCHEMAS/wave30_audio_mix_manifest.schema.json", mix_schema)
        _write_json(self.root / "Plan/08_SCHEMAS/wave30_audio_qa_report.schema.json", qa_schema)

    def _build_frames(self, gain: float = 1.0) -> list[tuple[float, ...]]:
        sample_rate = 16000
        total = int(1.0 * sample_rate)
        frames: list[tuple[float, ...]] = []
        for i in range(total):
            t = i / sample_rate
            amp = 0.05
            if 0.20 <= t < 0.40:
                amp = 0.09
            elif 0.60 <= t < 0.80:
                amp = 0.07
            value = gain * amp * math.sin(2.0 * math.pi * 440.0 * t)
            frames.append((value,))
        return frames

    def _row031_report(self, run_id: str, mix_binding: dict[str, Any], evt_binding: dict[str, Any], mix_manifest_binding: dict[str, Any], qa_binding: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "is_synthetic": True,
            "capture_mode": "technical_capture",
            "artifact_bindings": {
                "mix_wav": mix_binding,
                "wave30_event_manifest": evt_binding,
                "wave30_mix_manifest": mix_manifest_binding,
                "wave30_qa_report": qa_binding,
            },
            "gates": {
                "audio_metadata_check": "PASS",
                "prompt_alignment": "PASS",
                "playback_review": "PASS",
                "sync_evidence": "PASS",
                "promotion_decision": "PASS",
                "overall_pass": "PASS",
            },
            "computed_metrics": {
                "upstream_production_eligible": False
            },
        }

    def _qa_report(self, run_id: str, is_synthetic: bool, evt_binding: dict[str, Any], mix_binding: dict[str, Any], production_eligible: bool = False) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "is_synthetic": is_synthetic,
            "event_manifest_binding": {"path": evt_binding["path"], "sha256": evt_binding["sha256"]},
            "mix_manifest_binding": {"path": mix_binding["path"], "sha256": mix_binding["sha256"]},
            "hard_gate_statuses": {
                "decode": "pass",
                "duration": "pass",
                "loudness": "pass",
                "clipping": "pass",
                "sync": "pass",
                "voice_identity": "pass",
                "event_coverage": "pass",
                "mix_balance": "pass",
                "artifact_manifest": "pass",
                "runtime_proof": "pass" if production_eligible else "fail",
                "audio_review": "pass" if production_eligible else "fail",
            },
            "proof_verification": {
                "runtime_proof_verified": production_eligible,
                "audio_review_verified": production_eligible,
                "artifact_bindings_verified": True,
            },
            "computed_flags": {"all_hard_gates_passed": production_eligible, "production_eligible": production_eligible},
            "promotion_decision": "promote" if production_eligible else "block",
        }

    def _build_base_fixtures(self) -> None:
        self.sample_rate = 16000
        self.baseline_wav = self.root / "runtime_artifacts/baseline.wav"
        self.candidate_wav = self.root / "runtime_artifacts/candidate.wav"
        baseline_frames = self._build_frames()
        candidate_frames = self._build_frames()
        for i in range(int(0.20 * self.sample_rate), int(0.40 * self.sample_rate)):
            candidate_frames[i] = (candidate_frames[i][0] * 1.1,)
        _write_wav(self.baseline_wav, 1, self.sample_rate, baseline_frames)
        _write_wav(self.candidate_wav, 1, self.sample_rate, candidate_frames)

        self.b_evt_path = self.root / "runtime_artifacts/b_event.json"
        self.c_evt_path = self.root / "runtime_artifacts/c_event.json"
        self.b_mix_manifest_path = self.root / "runtime_artifacts/b_mix_manifest.json"
        self.c_mix_manifest_path = self.root / "runtime_artifacts/c_mix_manifest.json"
        self.b_qa_path = self.root / "runtime_artifacts/b_qa.json"
        self.c_qa_path = self.root / "runtime_artifacts/c_qa.json"
        self.b_row031_path = self.root / "runtime_artifacts/b_row031.json"
        self.c_row031_path = self.root / "runtime_artifacts/c_row031.json"
        self.request_path = self.root / "runtime_artifacts/request.json"
        self.output_path = self.root / "runtime_artifacts/report.json"
        self.bundle_path = self.root / "runtime_artifacts/bundle.json"

        event_manifest = {
            "run_id": "run_base",
            "is_synthetic": True,
            "scene_id": "scene_a",
            "audio_events": [
                {"audio_event_id": "evt_target", "start_seconds": 0.20, "end_seconds": 0.40, "sync_class": "frame_exact", "layer": "fg"},
                {"audio_event_id": "evt_bg", "start_seconds": 0.60, "end_seconds": 0.80, "sync_class": "ambient_free", "layer": "bg"},
            ],
        }
        _write_json(self.b_evt_path, event_manifest)
        candidate_event_manifest = copy.deepcopy(event_manifest)
        candidate_event_manifest["run_id"] = "run_cand"
        _write_json(self.c_evt_path, candidate_event_manifest)

        b_evt_binding = _binding(self.b_evt_path)
        c_evt_binding = _binding(self.c_evt_path)

        b_mix_manifest = {
            "run_id": "run_base",
            "is_synthetic": True,
            "scene_id": "scene_a",
            "event_manifest_bindings": [{"path": b_evt_binding["path"], "sha256": b_evt_binding["sha256"]}],
            "mixdown_artifact": _binding(self.baseline_wav),
            "mix_technical": {
                "sample_rate_hz": self.sample_rate,
                "channels": 1,
                "sample_width_bytes": 2,
                "frame_count": len(baseline_frames),
            },
            "mix_event_metadata": [
                {"audio_event_id": "evt_target", "gain_db": -2.0, "pan": 0.0, "spatial_position": {"x": 0, "y": 0, "z": 0}, "distance_meters": 1.0},
                {"audio_event_id": "evt_bg", "gain_db": -6.0, "pan": 0.0, "spatial_position": {"x": 0, "y": 0, "z": 0}, "distance_meters": 2.0},
            ],
        }
        c_mix_manifest = copy.deepcopy(b_mix_manifest)
        c_mix_manifest["run_id"] = "run_cand"
        c_mix_manifest["event_manifest_bindings"] = [{"path": c_evt_binding["path"], "sha256": c_evt_binding["sha256"]}]
        c_mix_manifest["mixdown_artifact"] = _binding(self.candidate_wav)
        c_mix_manifest["mix_technical"]["frame_count"] = len(candidate_frames)
        _write_json(self.b_mix_manifest_path, b_mix_manifest)
        _write_json(self.c_mix_manifest_path, c_mix_manifest)
        b_mix_binding = _binding(self.b_mix_manifest_path)
        c_mix_binding = _binding(self.c_mix_manifest_path)

        _write_json(self.b_qa_path, self._qa_report("run_base", True, b_evt_binding, b_mix_binding))
        _write_json(self.c_qa_path, self._qa_report("run_cand", True, c_evt_binding, c_mix_binding))
        b_qa_binding = _binding(self.b_qa_path)
        c_qa_binding = _binding(self.c_qa_path)

        _write_json(self.b_row031_path, self._row031_report("run_base", _binding(self.baseline_wav), b_evt_binding, b_mix_binding, b_qa_binding))
        _write_json(self.c_row031_path, self._row031_report("run_cand", _binding(self.candidate_wav), c_evt_binding, c_mix_binding, c_qa_binding))

        self.request = {
            "schema_name": "wave64_global_audio_review_request",
            "request_version": 1,
            "review_run_id": "run_review",
            "baseline_run_id": "run_base",
            "candidate_run_id": "run_cand",
            "is_synthetic": True,
            "capture_mode": "technical_capture",
            "baseline_mix_wav_binding": _binding(self.baseline_wav),
            "candidate_mix_wav_binding": _binding(self.candidate_wav),
            "baseline_row031_strict_report_binding": _binding(self.b_row031_path),
            "candidate_row031_strict_report_binding": _binding(self.c_row031_path),
            "baseline_wave30_event_manifest_binding": _binding(self.b_evt_path),
            "candidate_wave30_event_manifest_binding": _binding(self.c_evt_path),
            "baseline_wave30_mix_manifest_binding": _binding(self.b_mix_manifest_path),
            "candidate_wave30_mix_manifest_binding": _binding(self.c_mix_manifest_path),
            "baseline_wave30_qa_report_binding": _binding(self.b_qa_path),
            "candidate_wave30_qa_report_binding": _binding(self.c_qa_path),
            "localized_change_declaration": {
                "change_kind": "audio_localized",
                "audio_change_expected": True,
                "target_audio_event_ids": ["evt_target"],
                "non_target_audio_event_ids": ["evt_bg"],
                "allowed_change_windows_seconds": [{"start_seconds": 0.15, "end_seconds": 0.45}],
            },
            "output_report_path": str(self.output_path.resolve()),
        }

    def _run(self, request: dict[str, Any], *, raw_json: str | None = None, preserve_output: bool = False) -> subprocess.CompletedProcess[str]:
        if self.output_path.exists() and not preserve_output:
            self.output_path.unlink()
        if raw_json is not None:
            self.request_path.write_text(raw_json, encoding="utf-8")
        else:
            _write_json(self.request_path, request)
        return subprocess.run(
            [sys.executable, str(self.root / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_global_audio_review.py"), "--input", str(self.request_path), "--output", str(self.output_path)],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def _report(self) -> dict[str, Any]:
        return json.loads(self.output_path.read_text(encoding="utf-8"))

    def _refresh_lineage(self, request: dict[str, Any]) -> None:
        for prefix, wav_path, event_path, mix_path, qa_path, row031_path in (
            ("baseline", self.baseline_wav, self.b_evt_path, self.b_mix_manifest_path, self.b_qa_path, self.b_row031_path),
            ("candidate", self.candidate_wav, self.c_evt_path, self.c_mix_manifest_path, self.c_qa_path, self.c_row031_path),
        ):
            event_binding = _binding(event_path)
            mix = json.loads(mix_path.read_text(encoding="utf-8"))
            mix["event_manifest_bindings"] = [event_binding]
            mix["mixdown_artifact"] = _binding(wav_path)
            _write_json(mix_path, mix)
            mix_binding = _binding(mix_path)

            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            qa["event_manifest_binding"] = event_binding
            qa["mix_manifest_binding"] = mix_binding
            _write_json(qa_path, qa)
            qa_binding = _binding(qa_path)

            row031 = json.loads(row031_path.read_text(encoding="utf-8"))
            row031["artifact_bindings"]["mix_wav"] = _binding(wav_path)
            row031["artifact_bindings"]["wave30_event_manifest"] = event_binding
            row031["artifact_bindings"]["wave30_mix_manifest"] = mix_binding
            row031["artifact_bindings"]["wave30_qa_report"] = qa_binding
            _write_json(row031_path, row031)

            request[f"{prefix}_mix_wav_binding"] = _binding(wav_path)
            request[f"{prefix}_wave30_event_manifest_binding"] = event_binding
            request[f"{prefix}_wave30_mix_manifest_binding"] = mix_binding
            request[f"{prefix}_wave30_qa_report_binding"] = qa_binding
            request[f"{prefix}_row031_strict_report_binding"] = _binding(row031_path)

    def _build_valid_candidate_row030(self) -> dict[str, Any]:
        from Plan.Instructions.QA.Scripts.test_wave64_strict_audio_artifact_review import (
            Wave64StrictAudioArtifactReviewTests,
        )

        if not self.request_path.exists():
            _write_json(self.request_path, self.request)
        builder = Wave64StrictAudioArtifactReviewTests(methodName="runTest")
        builder.tmp_artifacts = self.root / "runtime_artifacts/row030_fixture"
        builder.tmp_artifacts.mkdir(parents=True, exist_ok=True)
        builder.root = self.root
        builder.request_path = self.request_path
        builder.wav_path = self.candidate_wav
        builder.event_manifest_path = self.c_evt_path
        builder.mix_manifest_path = self.c_mix_manifest_path
        report = builder._build_row030_report()
        report["run_id"] = "run_cand"
        report["scene_id"] = "scene_a"
        report["is_synthetic"] = True
        report["evidence_origin"] = "synthetic_fixture"
        report["artifact_bindings"]["source_audio_mix_artifact"] = _binding(self.candidate_wav)
        return report

    def test_positive_synthetic_expected_audio_change_probe(self) -> None:
        result = self._run(copy.deepcopy(self.request))
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertEqual(report["gates"]["required_target_audio_check"], "PASS")
        self.assertEqual(report["gates"]["required_non_target_audio_scan"], "PASS")
        self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")
        self.assertEqual(report["final_decision"]["overall_status"], "BLOCKED")

    def test_visual_no_audio_change_probe(self) -> None:
        shutil.copy2(self.baseline_wav, self.candidate_wav)
        request = copy.deepcopy(self.request)
        request["candidate_mix_wav_binding"] = _binding(self.candidate_wav)
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["mix_wav"] = request["candidate_mix_wav_binding"]
        _write_json(self.c_row031_path, row031)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        request["localized_change_declaration"] = {
            "change_kind": "visual_localized",
            "audio_change_expected": False,
            "target_audio_event_ids": [],
            "non_target_audio_event_ids": ["evt_bg", "evt_target"],
            "allowed_change_windows_seconds": [],
        }
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["gates"]["required_target_audio_check"], "PASS")

    def test_visual_audio_change_requires_row030_binding(self) -> None:
        request = copy.deepcopy(self.request)
        request["localized_change_declaration"]["change_kind"] = "visual_localized"
        request["localized_change_declaration"]["audio_change_expected"] = True
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "visual_localized with audio_change_expected=true requires candidate row031 row030_av_sync_report binding",
            "\n".join(self._report()["review_lineage_blockers"]),
        )

    def test_visual_audio_change_with_row030_binding_allowed(self) -> None:
        row030_path = self.root / "runtime_artifacts/row030_sync.json"
        _write_json(row030_path, self._build_valid_candidate_row030())
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["row030_av_sync_report"] = _binding(row030_path)
        _write_json(self.c_row031_path, row031)
        request = copy.deepcopy(self.request)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        request["localized_change_declaration"]["change_kind"] = "visual_localized"
        request["localized_change_declaration"]["audio_change_expected"] = True
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["gates"]["required_target_audio_check"], "PASS")

    def test_visual_audio_change_rejects_failed_row030_gate(self) -> None:
        row030_path = self.root / "runtime_artifacts/row030_sync_failed.json"
        row030 = self._build_valid_candidate_row030()
        row030["gates"]["drift_check"]["status"] = "FAIL"
        _write_json(row030_path, row030)
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["row030_av_sync_report"] = _binding(row030_path)
        _write_json(self.c_row031_path, row031)
        request = copy.deepcopy(self.request)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        request["localized_change_declaration"]["change_kind"] = "visual_localized"
        request["localized_change_declaration"]["audio_change_expected"] = True
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("candidate row030 AV sync required gate not PASS: drift_check", "\n".join(self._report()["review_lineage_blockers"]))

    def test_no_overall_pass_when_blockers_exist(self) -> None:
        request = copy.deepcopy(self.request)
        request["localized_change_declaration"]["allowed_change_windows_seconds"] = [{"start_seconds": 0.10, "end_seconds": 0.50}]
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertNotEqual(report["final_decision"]["overall_status"], "PASS")
        self.assertTrue(report["blockers"])

    def test_lineage_run_id_mismatch_fails(self) -> None:
        bad_evt = json.loads(self.c_evt_path.read_text(encoding="utf-8"))
        bad_evt["run_id"] = "wrong_run"
        _write_json(self.c_evt_path, bad_evt)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_event_manifest_binding"] = _binding(self.c_evt_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("candidate wave30 run_id lineage mismatch", "\n".join(self._report()["blockers"]))

    def test_wave30_binding_mismatch_fails(self) -> None:
        bad_mix = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        bad_mix["event_manifest_bindings"] = [{"path": "x", "sha256": "0" * 64}]
        _write_json(self.c_mix_manifest_path, bad_mix)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_mix_manifest_binding"] = _binding(self.c_mix_manifest_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("candidate wave30 mix manifest missing event manifest binding", "\n".join(self._report()["blockers"]))

    def test_non_target_recompute_rejects_missing_extra(self) -> None:
        request = copy.deepcopy(self.request)
        request["localized_change_declaration"]["non_target_audio_event_ids"] = []
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("caller non_target_audio_event_ids mismatch against canonical recomputation", self._report()["blockers"])

    def test_non_target_event_and_mix_metadata_change_rejected(self) -> None:
        evt = json.loads(self.c_evt_path.read_text(encoding="utf-8"))
        evt["audio_events"][1]["layer"] = "changed_layer"
        _write_json(self.c_evt_path, evt)
        mix_manifest = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        mix_manifest["mix_event_metadata"][1]["gain_db"] = -1.0
        _write_json(self.c_mix_manifest_path, mix_manifest)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_event_manifest_binding"] = _binding(self.c_evt_path)
        request["candidate_wave30_mix_manifest_binding"] = _binding(self.c_mix_manifest_path)
        self.assertEqual(self._run(request).returncode, 2)
        blockers = "\n".join(self._report()["blockers"])
        self.assertIn("non-target event record changed: evt_bg", blockers)
        self.assertIn("non-target mix_event_metadata changed: evt_bg", blockers)

    def test_per_target_rms_delta_enforced(self) -> None:
        _write_wav(self.candidate_wav, 1, self.sample_rate, self._build_frames(gain=1.0001))
        request = copy.deepcopy(self.request)
        request["candidate_mix_wav_binding"] = _binding(self.candidate_wav)
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["mix_wav"] = request["candidate_mix_wav_binding"]
        _write_json(self.c_row031_path, row031)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertIn("target event RMS delta below threshold", "\n".join(self._report()["blockers"]))

    def test_same_layer_foreground_overlap_blocked(self) -> None:
        evt = json.loads(self.c_evt_path.read_text(encoding="utf-8"))
        evt["audio_events"].append(
            {"audio_event_id": "evt_fg_conflict", "start_seconds": 0.22, "end_seconds": 0.28, "sync_class": "frame_exact", "layer": "fg"}
        )
        _write_json(self.c_evt_path, evt)
        mix = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        mix["mix_event_metadata"].append({"audio_event_id": "evt_fg_conflict", "gain_db": -5.0, "pan": 0.0, "spatial_position": {"x": 0, "y": 0, "z": 0}, "distance_meters": 2.0})
        _write_json(self.c_mix_manifest_path, mix)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_event_manifest_binding"] = _binding(self.c_evt_path)
        request["candidate_wave30_mix_manifest_binding"] = _binding(self.c_mix_manifest_path)
        request["localized_change_declaration"]["non_target_audio_event_ids"] = ["evt_bg", "evt_fg_conflict"]
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("same-layer foreground non-target overlap with target-derived window", "\n".join(self._report()["blockers"]))

    def test_ambient_full_duration_nested_target_pass(self) -> None:
        b_evt = json.loads(self.b_evt_path.read_text(encoding="utf-8"))
        b_evt["audio_events"].append(
            {"audio_event_id": "evt_ambient_full", "start_seconds": 0.00, "end_seconds": 1.00, "sync_class": "ambient_free", "layer": "fg"}
        )
        _write_json(self.b_evt_path, b_evt)
        evt = json.loads(self.c_evt_path.read_text(encoding="utf-8"))
        evt["audio_events"].append(
            {"audio_event_id": "evt_ambient_full", "start_seconds": 0.00, "end_seconds": 1.00, "sync_class": "ambient_free", "layer": "fg"}
        )
        _write_json(self.c_evt_path, evt)
        b_mix = json.loads(self.b_mix_manifest_path.read_text(encoding="utf-8"))
        b_mix["mix_event_metadata"].append({"audio_event_id": "evt_ambient_full", "gain_db": -9.0, "pan": 0.0, "spatial_position": {"x": 0, "y": 0, "z": 0}, "distance_meters": 3.0})
        _write_json(self.b_mix_manifest_path, b_mix)
        mix = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        mix["mix_event_metadata"].append({"audio_event_id": "evt_ambient_full", "gain_db": -9.0, "pan": 0.0, "spatial_position": {"x": 0, "y": 0, "z": 0}, "distance_meters": 3.0})
        _write_json(self.c_mix_manifest_path, mix)
        request = copy.deepcopy(self.request)
        request["baseline_wave30_event_manifest_binding"] = _binding(self.b_evt_path)
        request["candidate_wave30_event_manifest_binding"] = _binding(self.c_evt_path)
        request["baseline_wave30_mix_manifest_binding"] = _binding(self.b_mix_manifest_path)
        request["candidate_wave30_mix_manifest_binding"] = _binding(self.c_mix_manifest_path)
        request["localized_change_declaration"]["non_target_audio_event_ids"] = ["evt_ambient_full", "evt_bg"]
        self._refresh_lineage(request)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertEqual(report["gates"]["required_non_target_audio_scan"], "PASS")

    def test_different_layer_foreground_overlap_allowed(self) -> None:
        for event_path in (self.b_evt_path, self.c_evt_path):
            event_manifest = json.loads(event_path.read_text(encoding="utf-8"))
            event_manifest["audio_events"].append(
                {"audio_event_id": "evt_other_layer", "start_seconds": 0.22, "end_seconds": 0.28, "sync_class": "frame_exact", "layer": "other"}
            )
            _write_json(event_path, event_manifest)
        for mix_path in (self.b_mix_manifest_path, self.c_mix_manifest_path):
            mix_manifest = json.loads(mix_path.read_text(encoding="utf-8"))
            mix_manifest["mix_event_metadata"].append(
                {"audio_event_id": "evt_other_layer", "gain_db": -5.0, "pan": 0.0, "spatial_position": {"x": 0, "y": 0, "z": 0}, "distance_meters": 2.0}
            )
            _write_json(mix_path, mix_manifest)
        request = copy.deepcopy(self.request)
        request["localized_change_declaration"]["non_target_audio_event_ids"] = ["evt_bg", "evt_other_layer"]
        self._refresh_lineage(request)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self._report()["gates"]["required_non_target_audio_scan"], "PASS")

    def test_single_channel_clipping_and_dropout_regressions(self) -> None:
        with wave.open(str(self.candidate_wav), "rb") as handle:
            channels = handle.getnchannels()
            sample_rate = handle.getframerate()
            samples = list(memoryview(handle.readframes(handle.getnframes())).cast("h"))
        for i in range(int(0.20 * sample_rate), int(0.30 * sample_rate)):
            samples[i * channels] = 32767
        for i in range(int(0.62 * sample_rate), int(0.74 * sample_rate)):
            samples[i * channels] = 0
        frames = [(samples[i] / 32768.0,) for i in range(0, len(samples), channels)]
        _write_wav(self.candidate_wav, 1, sample_rate, frames)
        request = copy.deepcopy(self.request)
        request["candidate_mix_wav_binding"] = _binding(self.candidate_wav)
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["mix_wav"] = request["candidate_mix_wav_binding"]
        _write_json(self.c_row031_path, row031)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        self.assertEqual(self._run(request).returncode, 2)
        blockers = "\n".join(self._report()["blockers"])
        self.assertIn("single-channel clipping regression detected", blockers)
        self.assertIn("single-channel dropout regression detected", blockers)

    def test_frame_count_mismatch_is_evaluated_not_invalid(self) -> None:
        short_frames = self._build_frames()[: int(0.95 * self.sample_rate)]
        _write_wav(self.candidate_wav, 1, self.sample_rate, short_frames)
        request = copy.deepcopy(self.request)
        request["candidate_mix_wav_binding"] = _binding(self.candidate_wav)
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["mix_wav"] = request["candidate_mix_wav_binding"]
        _write_json(self.c_row031_path, row031)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        self.assertIn("evaluated duration delta exceeds tolerance", "\n".join(self._report()["blockers"]))

    def test_wave30_hard_gate_regression_fails_lineage(self) -> None:
        qa = json.loads(self.c_qa_path.read_text(encoding="utf-8"))
        qa["hard_gate_statuses"]["decode"] = "fail"
        _write_json(self.c_qa_path, qa)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_qa_report_binding"] = _binding(self.c_qa_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("required technical hard gate not pass: decode", "\n".join(self._report()["review_lineage_blockers"]))

    def test_wave30_proof_flag_regression_fails_lineage(self) -> None:
        qa = json.loads(self.c_qa_path.read_text(encoding="utf-8"))
        qa["proof_verification"]["artifact_bindings_verified"] = False
        _write_json(self.c_qa_path, qa)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_qa_report_binding"] = _binding(self.c_qa_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("proof_verification.artifact_bindings_verified must be true", "\n".join(self._report()["review_lineage_blockers"]))

    def test_mixdown_binding_regression_fails_lineage(self) -> None:
        mix = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        mix["mixdown_artifact"]["sha256"] = "0" * 64
        _write_json(self.c_mix_manifest_path, mix)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_mix_manifest_binding"] = _binding(self.c_mix_manifest_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("mixdown_artifact binding mismatch", "\n".join(self._report()["review_lineage_blockers"]))

    def test_mix_technical_regression_fails_lineage(self) -> None:
        mix = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        mix["mix_technical"]["sample_rate_hz"] = 44100
        _write_json(self.c_mix_manifest_path, mix)
        request = copy.deepcopy(self.request)
        request["candidate_wave30_mix_manifest_binding"] = _binding(self.c_mix_manifest_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("mix_technical sample_rate_hz mismatch", "\n".join(self._report()["review_lineage_blockers"]))

    def test_row031_technical_gate_regression_fails_lineage(self) -> None:
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["gates"]["audio_metadata_check"] = "FAIL"
        _write_json(self.c_row031_path, row031)
        request = copy.deepcopy(self.request)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("required technical gates not PASS", "\n".join(self._report()["review_lineage_blockers"]))

    def test_request_const_version_enforced(self) -> None:
        request = copy.deepcopy(self.request)
        request["request_version"] = 2
        self.assertEqual(self._run(request).returncode, 1)

    def test_review_baseline_candidate_run_ids_must_be_distinct(self) -> None:
        request = copy.deepcopy(self.request)
        request["review_run_id"] = request["candidate_run_id"]
        self.assertEqual(self._run(request).returncode, 1)

    def test_row031_binding_bytes_mismatch_fails_lineage(self) -> None:
        row031 = json.loads(self.c_row031_path.read_text(encoding="utf-8"))
        row031["artifact_bindings"]["mix_wav"]["bytes"] += 1
        _write_json(self.c_row031_path, row031)
        request = copy.deepcopy(self.request)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("candidate_row031_report mix_wav binding mismatch", self._report()["review_lineage_blockers"])

    def test_production_authority_objects_required(self) -> None:
        baseline_mix_sha = self.request["baseline_mix_wav_binding"]["sha256"]
        bundle = {
            "schema_name": "wave64_global_audio_production_bundle",
            "schema_version": 1,
            "bundle_id": "bundle_a",
            "scene_id": "scene_a",
            "baseline_authority_id": "auth_base",
            "bundle_authority_id": "auth_bundle",
            "baseline_run_id": "run_base",
            "candidate_run_id": "run_cand",
            "review_run_id": "run_review",
            "synthetic_only": False,
            "baseline_mix_wav_sha256": baseline_mix_sha,
            "baseline_row031_sha256": self.request["baseline_row031_strict_report_binding"]["sha256"],
            "candidate_mix_wav_sha256": self.request["candidate_mix_wav_binding"]["sha256"],
            "candidate_row031_sha256": self.request["candidate_row031_strict_report_binding"]["sha256"],
            "candidate_wave30_qa_sha256": self.request["candidate_wave30_qa_report_binding"]["sha256"],
        }
        _write_json(self.bundle_path, bundle)
        request = copy.deepcopy(self.request)
        request["production_bundle_binding"] = _binding(self.bundle_path)
        self.assertEqual(self._run(request).returncode, 2)
        self.assertIn("baseline production authority is not approved", "\n".join(self._report()["blockers"]))
        self.assertEqual(baseline_mix_sha, bundle["baseline_mix_wav_sha256"])

    def test_fixture_only_authority_contract_can_reach_exit_zero(self) -> None:
        request = copy.deepcopy(self.request)
        request["is_synthetic"] = False

        for event_path in (self.b_evt_path, self.c_evt_path):
            event_manifest = json.loads(event_path.read_text(encoding="utf-8"))
            event_manifest["is_synthetic"] = False
            _write_json(event_path, event_manifest)
        b_evt_binding = _binding(self.b_evt_path)
        c_evt_binding = _binding(self.c_evt_path)

        for mix_path, event_binding in (
            (self.b_mix_manifest_path, b_evt_binding),
            (self.c_mix_manifest_path, c_evt_binding),
        ):
            mix_manifest = json.loads(mix_path.read_text(encoding="utf-8"))
            mix_manifest["is_synthetic"] = False
            mix_manifest["event_manifest_bindings"] = [event_binding]
            _write_json(mix_path, mix_manifest)
        b_mix_binding = _binding(self.b_mix_manifest_path)
        c_mix_binding = _binding(self.c_mix_manifest_path)

        _write_json(self.b_qa_path, self._qa_report("run_base", False, b_evt_binding, b_mix_binding, production_eligible=True))
        _write_json(self.c_qa_path, self._qa_report("run_cand", False, c_evt_binding, c_mix_binding, production_eligible=True))
        b_qa_binding = _binding(self.b_qa_path)
        c_qa_binding = _binding(self.c_qa_path)

        b_row031 = self._row031_report("run_base", _binding(self.baseline_wav), b_evt_binding, b_mix_binding, b_qa_binding)
        c_row031 = self._row031_report("run_cand", _binding(self.candidate_wav), c_evt_binding, c_mix_binding, c_qa_binding)
        for row031 in (b_row031, c_row031):
            row031["is_synthetic"] = False
            row031["computed_metrics"]["upstream_production_eligible"] = True
        _write_json(self.b_row031_path, b_row031)
        _write_json(self.c_row031_path, c_row031)

        request.update(
            {
                "baseline_wave30_event_manifest_binding": b_evt_binding,
                "candidate_wave30_event_manifest_binding": c_evt_binding,
                "baseline_wave30_mix_manifest_binding": b_mix_binding,
                "candidate_wave30_mix_manifest_binding": c_mix_binding,
                "baseline_wave30_qa_report_binding": b_qa_binding,
                "candidate_wave30_qa_report_binding": c_qa_binding,
                "baseline_row031_strict_report_binding": _binding(self.b_row031_path),
                "candidate_row031_strict_report_binding": _binding(self.c_row031_path),
            }
        )

        bundle = {
            "schema_name": "wave64_global_audio_production_bundle",
            "schema_version": 1,
            "bundle_id": "fixture_bundle_contract_only",
            "scene_id": "scene_a",
            "baseline_authority_id": "fixture_baseline_authority",
            "bundle_authority_id": "fixture_bundle_authority",
            "baseline_run_id": "run_base",
            "candidate_run_id": "run_cand",
            "review_run_id": "run_review",
            "synthetic_only": False,
            "baseline_mix_wav_sha256": request["baseline_mix_wav_binding"]["sha256"],
            "baseline_row031_sha256": request["baseline_row031_strict_report_binding"]["sha256"],
            "candidate_mix_wav_sha256": request["candidate_mix_wav_binding"]["sha256"],
            "candidate_row031_sha256": request["candidate_row031_strict_report_binding"]["sha256"],
            "candidate_wave30_qa_sha256": c_qa_binding["sha256"],
        }
        _write_json(self.bundle_path, bundle)
        request["production_bundle_binding"] = _binding(self.bundle_path)

        registry_path = self.root / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["production_rules"]["approved_production_baselines"] = [
            {
                "scene_id": "scene_a",
                "baseline_authority_id": "fixture_baseline_authority",
                "baseline_run_id": "run_base",
                "synthetic_only": False,
                "baseline_mix_wav_sha256": request["baseline_mix_wav_binding"]["sha256"],
                "baseline_row031_sha256": request["baseline_row031_strict_report_binding"]["sha256"],
            }
        ]
        registry["production_rules"]["approved_production_bundles"] = [
            {
                "scene_id": "scene_a",
                "baseline_authority_id": "fixture_baseline_authority",
                "bundle_authority_id": "fixture_bundle_authority",
                "bundle_id": "fixture_bundle_contract_only",
                "baseline_run_id": "run_base",
                "candidate_run_id": "run_cand",
                "review_run_id": "run_review",
                "synthetic_only": False,
                "bundle_sha256": request["production_bundle_binding"]["sha256"],
                "baseline_mix_wav_sha256": request["baseline_mix_wav_binding"]["sha256"],
                "baseline_row031_sha256": request["baseline_row031_strict_report_binding"]["sha256"],
                "candidate_mix_wav_sha256": request["candidate_mix_wav_binding"]["sha256"],
                "candidate_row031_sha256": request["candidate_row031_strict_report_binding"]["sha256"],
                "candidate_wave30_qa_sha256": c_qa_binding["sha256"],
            }
        ]
        _write_json(registry_path, registry)

        result = self._run(request)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = self._report()
        self.assertEqual(report["gates"]["promotion_decision"], "PASS")
        self.assertEqual(report["final_decision"]["overall_status"], "PASS")
        self.assertFalse(report["blockers"])

    def test_hand_authored_non_synthetic_relabel_cannot_promote(self) -> None:
        request = copy.deepcopy(self.request)
        request["is_synthetic"] = False
        request["capture_mode"] = "hand_authored_relabel"

        for event_path in (self.b_evt_path, self.c_evt_path):
            event_manifest = json.loads(event_path.read_text(encoding="utf-8"))
            event_manifest["is_synthetic"] = False
            _write_json(event_path, event_manifest)
        b_evt_binding = _binding(self.b_evt_path)
        c_evt_binding = _binding(self.c_evt_path)

        for mix_path, event_binding in (
            (self.b_mix_manifest_path, b_evt_binding),
            (self.c_mix_manifest_path, c_evt_binding),
        ):
            mix_manifest = json.loads(mix_path.read_text(encoding="utf-8"))
            mix_manifest["is_synthetic"] = False
            mix_manifest["event_manifest_bindings"] = [event_binding]
            _write_json(mix_path, mix_manifest)
        b_mix_binding = _binding(self.b_mix_manifest_path)
        c_mix_binding = _binding(self.c_mix_manifest_path)

        _write_json(self.b_qa_path, self._qa_report("run_base", False, b_evt_binding, b_mix_binding))
        _write_json(self.c_qa_path, self._qa_report("run_cand", False, c_evt_binding, c_mix_binding))
        b_qa_binding = _binding(self.b_qa_path)
        c_qa_binding = _binding(self.c_qa_path)

        b_row031 = self._row031_report("run_base", _binding(self.baseline_wav), b_evt_binding, b_mix_binding, b_qa_binding)
        c_row031 = self._row031_report("run_cand", _binding(self.candidate_wav), c_evt_binding, c_mix_binding, c_qa_binding)
        for row031 in (b_row031, c_row031):
            row031["is_synthetic"] = False
            row031["capture_mode"] = "hand_authored_relabel"
            row031["gates"]["promotion_decision"] = "BLOCKED"
            row031["gates"]["overall_pass"] = "BLOCKED"
        _write_json(self.b_row031_path, b_row031)
        _write_json(self.c_row031_path, c_row031)

        request.update(
            {
                "baseline_wave30_event_manifest_binding": b_evt_binding,
                "candidate_wave30_event_manifest_binding": c_evt_binding,
                "baseline_wave30_mix_manifest_binding": b_mix_binding,
                "candidate_wave30_mix_manifest_binding": c_mix_binding,
                "baseline_wave30_qa_report_binding": b_qa_binding,
                "candidate_wave30_qa_report_binding": c_qa_binding,
                "baseline_row031_strict_report_binding": _binding(self.b_row031_path),
                "candidate_row031_strict_report_binding": _binding(self.c_row031_path),
            }
        )

        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        report = self._report()
        self.assertEqual(report["gates"]["full_duration_playback_review"], "PASS")
        self.assertEqual(report["gates"]["required_target_audio_check"], "PASS")
        self.assertEqual(report["gates"]["required_non_target_audio_scan"], "PASS")
        self.assertEqual(report["gates"]["promotion_decision"], "BLOCKED")
        self.assertEqual(report["final_decision"]["overall_status"], "BLOCKED")
        self.assertIn("production decision requires technical_capture", report["blockers"])

    def test_registry_rejects_malformed_authority_records(self) -> None:
        registry_path = self.root / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["production_rules"]["approved_production_baselines"] = [
            {
                "scene_id": "scene_a",
                "baseline_authority_id": "auth_a",
                "baseline_mix_wav_sha256": self.request["baseline_mix_wav_binding"]["sha256"],
                "baseline_row031_sha256": self.request["baseline_row031_strict_report_binding"]["sha256"],
            }
        ]
        _write_json(registry_path, registry)
        self.assertEqual(self._run(copy.deepcopy(self.request)).returncode, 1)

    def test_registry_rejects_thresholds_above_safety_ceiling(self) -> None:
        registry_path = self.root / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["non_target_rules"]["max_outside_target_diff_rms"] = 1.0
        _write_json(registry_path, registry)
        self.assertEqual(self._run(copy.deepcopy(self.request)).returncode, 1)

    def test_no_permanent_production_disable_blocker(self) -> None:
        self.assertEqual(self._run(copy.deepcopy(self.request)).returncode, 2)
        self.assertNotIn("production promotion is intentionally disabled", "\n".join(self._report()["blockers"]))

    def test_multichannel_independent_metric_maxima(self) -> None:
        sample_rate = self.sample_rate
        frames: list[tuple[float, float]] = []
        for i in range(sample_rate):
            t = i / sample_rate
            left = 0.04 * math.sin(2.0 * math.pi * 440.0 * t)
            right = 0.04 * math.sin(2.0 * math.pi * 330.0 * t)
            if 0.20 <= t < 0.40:
                left *= 1.12
            if 0.24 <= t < 0.27:
                right = 1.0
            frames.append((left, right))
        _write_wav(self.baseline_wav, 2, sample_rate, [(x * 0.95, y * 0.95) for x, y in frames])
        _write_wav(self.candidate_wav, 2, sample_rate, frames)

        b_evt_binding = _binding(self.b_evt_path)
        c_evt_binding = _binding(self.c_evt_path)
        b_mix = json.loads(self.b_mix_manifest_path.read_text(encoding="utf-8"))
        c_mix = json.loads(self.c_mix_manifest_path.read_text(encoding="utf-8"))
        b_mix["mixdown_artifact"] = _binding(self.baseline_wav)
        c_mix["mixdown_artifact"] = _binding(self.candidate_wav)
        b_mix["mix_technical"].update({"sample_rate_hz": sample_rate, "channels": 2, "sample_width_bytes": 2, "frame_count": sample_rate})
        c_mix["mix_technical"].update({"sample_rate_hz": sample_rate, "channels": 2, "sample_width_bytes": 2, "frame_count": sample_rate})
        _write_json(self.b_mix_manifest_path, b_mix)
        _write_json(self.c_mix_manifest_path, c_mix)

        b_mix_binding = _binding(self.b_mix_manifest_path)
        c_mix_binding = _binding(self.c_mix_manifest_path)
        _write_json(self.b_qa_path, self._qa_report("run_base", True, b_evt_binding, b_mix_binding))
        _write_json(self.c_qa_path, self._qa_report("run_cand", True, c_evt_binding, c_mix_binding))
        b_qa_binding = _binding(self.b_qa_path)
        c_qa_binding = _binding(self.c_qa_path)

        _write_json(self.b_row031_path, self._row031_report("run_base", _binding(self.baseline_wav), b_evt_binding, b_mix_binding, b_qa_binding))
        _write_json(self.c_row031_path, self._row031_report("run_cand", _binding(self.candidate_wav), c_evt_binding, c_mix_binding, c_qa_binding))

        request = copy.deepcopy(self.request)
        request["baseline_mix_wav_binding"] = _binding(self.baseline_wav)
        request["candidate_mix_wav_binding"] = _binding(self.candidate_wav)
        request["baseline_wave30_mix_manifest_binding"] = b_mix_binding
        request["candidate_wave30_mix_manifest_binding"] = c_mix_binding
        request["baseline_wave30_qa_report_binding"] = b_qa_binding
        request["candidate_wave30_qa_report_binding"] = c_qa_binding
        request["baseline_row031_strict_report_binding"] = _binding(self.b_row031_path)
        request["candidate_row031_strict_report_binding"] = _binding(self.c_row031_path)
        result = self._run(request)
        self.assertEqual(result.returncode, 2)
        metrics = self._report()["computed_metrics"]
        self.assertGreater(metrics["candidate_clipping_ratio"], 0.0)
        self.assertGreater(metrics["outside_target_diff_rms"], 0.0)

    def test_unknown_nonfinite_hash_collision_and_registry_immutable(self) -> None:
        request = copy.deepcopy(self.request)
        request["unknown_key"] = True
        self.assertEqual(self._run(request).returncode, 1)

        raw = json.dumps(copy.deepcopy(self.request))[:-1] + ',"bad":NaN}'
        self.assertEqual(self._run(copy.deepcopy(self.request), raw_json=raw).returncode, 1)

        duplicate = json.dumps(copy.deepcopy(self.request))[:-1] + ',"review_run_id":"duplicate"}'
        self.assertEqual(self._run(copy.deepcopy(self.request), raw_json=duplicate).returncode, 1)

        request = copy.deepcopy(self.request)
        request["candidate_mix_wav_binding"]["sha256"] = "0" * 64
        self.assertEqual(self._run(request).returncode, 1)

        request = copy.deepcopy(self.request)
        request["candidate_mix_wav_binding"] = _binding(SOURCE_SCRIPT)
        self.assertEqual(self._run(request).returncode, 1)

        self.output_path.write_text('{"preexisting":true}\n', encoding="utf-8")
        self.assertEqual(self._run(copy.deepcopy(self.request), preserve_output=True).returncode, 1)
        self.assertEqual(self.output_path.read_text(encoding="utf-8"), '{"preexisting":true}\n')

        self.assertEqual(_sha256(self.root / "Plan/10_REGISTRIES/wave64_global_audio_review_gate_rules.json"), self.registry_snapshot_sha)


if __name__ == "__main__":
    unittest.main()
