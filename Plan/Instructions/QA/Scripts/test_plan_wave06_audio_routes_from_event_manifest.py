#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/plan_wave06_audio_routes_from_event_manifest.py"
PLAN_SCHEMA = ROOT / "Plan/08_SCHEMAS/wave06_audio_event_route_plan.schema.json"
sys.path.insert(0, str(ROOT / "Plan/07_IMPLEMENTATION/scripts"))
import plan_wave06_audio_routes_from_event_manifest as bridge  # noqa: E402


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


class AudioRouteBridgeTests(unittest.TestCase):
    def manifest(self, base: Path, *, channels: int = 1, synchronized: bool = False) -> Path:
        base.mkdir(parents=True, exist_ok=True); wav_path = base / "source.wav"
        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(channels); wav.setsampwidth(2); wav.setframerate(16000); wav.writeframes(b"\0\0" * channels * 4000)
        types = ["dialogue", "breath", "body_foley", "ambience", "music", "impact"]
        events = []
        for index, event_type in enumerate(types):
            binding = {"binding_type": "character", "character_id": "c"} if event_type in {"dialogue", "breath", "body_foley"} else ({"binding_type": "object", "object_id": "o"} if event_type == "impact" else {"binding_type": "environment"})
            events.append({
                "audio_event_id": f"event_{index}", "scene_id": "scene", "shot_id": "shot", "event_type": event_type,
                "sync_class": "frame_exact", "purpose": "test", "source_event_id": f"source_{index}",
                "start_seconds": 0.0, "end_seconds": 0.25,
                "expected_video_frame_range": {"start_frame": 0, "end_frame": 6, "frame_rate": 24.0},
                "qa_rules": ["decode"], "layer": event_type,
                "routing": {"bus": "main", "synchronized_av_required": synchronized and event_type == "impact"},
                "subject_binding": binding,
                "artifact": {"path": str(wav_path), "sha256": sha(wav_path), "bytes": wav_path.stat().st_size,
                             "duration_seconds": 0.25, "sample_rate_hz": 16000, "channels": channels,
                             "sample_width_bytes": 2, "frame_count": 4000},
                "synthetic_state": {"synthetic_origin": "test", "production_proof_claimed": False},
            })
        payload = {"$schema": "https://json-schema.org/draft/2020-12/schema", "schema_name": "wave30_audio_event_manifest",
                   "event_manifest_version": 1, "run_id": "run", "scene_id": "scene", "shot_id": "shot", "is_synthetic": True,
                   "production_proof": {"runtime_proof_present": False, "audio_review_present": False, "certified_for_release": False},
                   "taxonomy_registry_path": "registry", "taxonomy_registry_sha256": "0" * 64,
                   "audio_event_count": len(events), "required_lanes": [], "audio_events": events,
                   "artifact_manifest": {"source_input_path": "input", "source_input_sha256": "1" * 64},
                   "av_sync_binding": {"frame_rate": 24.0, "sync_scope": "event_level"}}
        path = base / "manifest.json"; path.write_text(json.dumps(payload), encoding="utf-8"); return path

    def run_bridge(self, manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(ROOT), "--event-manifest", str(manifest), "--output-dir", str(output)], cwd=ROOT, text=True, capture_output=True)

    def test_maps_all_event_types_and_fails_closed_on_missing_proofs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as tmp:
            base = Path(tmp); out = base / "out"; result = self.run_bridge(self.manifest(base), out)
            self.assertEqual(result.returncode, 2, result.stderr)
            plan = json.loads((out / "route_plan.json").read_text())
            Draft202012Validator(json.loads(PLAN_SCHEMA.read_text())).validate(plan)
            self.assertEqual(plan["event_count"], 6); self.assertEqual(plan["request_count"], 6)
            self.assertEqual(plan["selected_count"], 0); self.assertTrue(plan["block_final_av_promotion"])
            mapped = {item["event_type"]: item["route_type"] for item in plan["events"]}
            self.assertEqual(mapped["body_foley"], "foley_contact_fabric")
            self.assertEqual(mapped["breath"], "breath_body_effort")
            self.assertTrue(all("missing_capability_proof" in item["blockers"] for item in plan["events"]))

    def test_synchronized_av_override_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as tmp:
            base = Path(tmp); out = base / "out"; self.run_bridge(self.manifest(base, synchronized=True), out)
            plan = json.loads((out / "route_plan.json").read_text())
            impact = next(item for item in plan["events"] if item["event_type"] == "impact")
            request = json.loads(Path(impact["request"]["path"]).read_text())
            self.assertEqual(impact["route_type"], "synchronized_av"); self.assertEqual(request["output_type"], "av")

    def test_unsupported_channel_count_blocks_only_derivation(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as tmp:
            base = Path(tmp); out = base / "out"; self.run_bridge(self.manifest(base, channels=3), out)
            plan = json.loads((out / "route_plan.json").read_text())
            self.assertEqual(plan["request_count"], 0); self.assertEqual(plan["blocked_count"], 6)
            self.assertTrue(all(item["blockers"] == ["bridge_derivation_failed:unsupported_channel_layout_derivation"] for item in plan["events"]))

    def test_request_and_decision_hash_bindings_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as tmp:
            base = Path(tmp); out = base / "out"; self.run_bridge(self.manifest(base), out)
            plan = json.loads((out / "route_plan.json").read_text())
            for item in plan["events"]:
                self.assertEqual(sha(Path(item["request"]["path"])), item["request"]["sha256"])
                self.assertEqual(sha(Path(item["decision"]["path"])), item["decision"]["sha256"])

    def test_existing_output_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as tmp:
            base = Path(tmp); out = base / "out"; out.mkdir(); marker = out / "keep"; marker.write_text("yes")
            result = self.run_bridge(self.manifest(base), out); self.assertEqual(result.returncode, 2); self.assertEqual(marker.read_text(), "yes")

    def test_successful_aggregate_respects_production_usage_scope(self) -> None:
        def selected(_root: Path, request: dict[str, object]) -> tuple[int, dict[str, object]]:
            return 0, {
                "$schema": "https://json-schema.org/draft/2020-12/schema", "decision_version": 1,
                "output_type": request["output_type"], "route_type": request["route_type"],
                "request_constraints_hash": "0" * 64, "selected_engine_id": "approved_audio_test_engine",
                "route_mode": "audio_engine_selected", "block_final_av_promotion": False,
                "is_synthetic": False, "blockers": [], "required_next_proofs": [],
                "evaluated_candidates": ["approved_audio_test_engine"],
                "authority_bindings": {"registry_sha256": "0" * 64, "matrix_sha256": "0" * 64,
                                       "rules_sha256": "0" * 64, "notes_sha256": "0" * 64},
                "proof_evaluation": {kind: "pass" for kind in ("capability", "license", "asset", "runtime", "qa")},
            }

        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as tmp:
            base = Path(tmp); manifest = self.manifest(base); payload = json.loads(manifest.read_text())
            payload["is_synthetic"] = False; manifest.write_text(json.dumps(payload))
            with mock.patch.object(bridge, "route_request", side_effect=selected):
                production = bridge.build_plan(ROOT, manifest, base / "production", base / "proofs", "production")
                evaluation = bridge.build_plan(ROOT, manifest, base / "evaluation", base / "proofs", "internal_eval")
            self.assertEqual(production["selected_count"], production["event_count"])
            self.assertTrue(production["all_events_routed"]); self.assertTrue(production["production_selection_claimed"])
            self.assertFalse(production["block_final_av_promotion"])
            self.assertTrue(evaluation["all_events_routed"]); self.assertFalse(evaluation["production_selection_claimed"])
            self.assertTrue(evaluation["block_final_av_promotion"])


if __name__ == "__main__": unittest.main()
