from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
NODE = ROOT / "Plan/07_IMPLEMENTATION/comfyui_custom_nodes/wave64_speech_bridge/__init__.py"
MANAGER = ROOT / "Plan/07_IMPLEMENTATION/scripts/manage_wave64_speech_runtime_cache_cost.py"
SMOKE = ROOT / "Plan/07_IMPLEMENTATION/scripts/install_and_smoke_wave64_speech_bridge.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE = load(NODE, "wave64_speech_bridge_tests")
MANAGE = load(MANAGER, "wave64_speech_cache_manager_tests")
SMOKER = load(SMOKE, "wave64_speech_bridge_smoke_tests")


def request() -> dict:
    value = SMOKER.sample_request()
    value["request_id"] = "test_request_001"
    return value


class Wave64SpeechBridgeTests(unittest.TestCase):
    def test_request_matches_schema_and_manual_validator(self) -> None:
        schema = json.loads((ROOT / "Plan/08_SCHEMAS/wave64_speech_bridge_request.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(request())
        self.assertEqual("test_request_001", BRIDGE.validate_request(request())["request_id"])

    def test_cache_key_is_order_stable_and_authority_independent(self) -> None:
        first = request()
        first["engine"]["model_asset_sha256"].append("0" * 64)
        first["preprocessing_transform_ids"].append("trim_none")
        second = json.loads(json.dumps(first))
        second["engine"]["model_asset_sha256"].reverse()
        second["preprocessing_transform_ids"].reverse()
        second["authority"]["voice_authority_valid"] = True
        self.assertEqual(BRIDGE.compute_cache_key(first), BRIDGE.compute_cache_key(second))

    def test_invalid_hash_fails_closed(self) -> None:
        value = request()
        value["line_contract_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "expected_lowercase_sha256"):
            BRIDGE.validate_request(value)

    def test_manual_validator_matches_schema_length_limits(self) -> None:
        value = request()
        value["engine"]["family"] = "x" * 129
        with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "engine.family"):
            BRIDGE.validate_request(value)
        value = request()
        value["preprocessing_transform_ids"] = ["x" * 257]
        with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "preprocessing_transform_ids"):
            BRIDGE.validate_request(value)

    def test_nonfinite_sampling_parameter_is_rejected(self) -> None:
        value = request()
        value["sampling_params"]["temperature"] = math.nan
        with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "nonfinite_number"):
            BRIDGE.validate_request(value)

    def test_dry_run_writes_control_evidence_without_media_or_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Plan").mkdir()
            (root / "runtime_artifacts").mkdir()
            result = BRIDGE.execute_request(request(), dry_run=True, root=root)
            self.assertEqual("BLOCKED", result["status"])
            self.assertIn("BLOCKED_VOICE_AUTHORITY_MISSING", result["blockers"])
            self.assertFalse(result["boundaries"]["media_generated"])
            self.assertFalse((root / "runtime_artifacts/audio_speech_candidates").exists())
            self.assertFalse((root / "runtime_artifacts/audio_speech_promoted").exists())
            self.assertTrue(Path(result["result_binding"]["path"]).is_file())
            self.assertTrue(Path(result["telemetry_binding"]["path"]).is_file())

    def test_cache_lock_rejects_contention_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            key = "a" * 64
            with BRIDGE.cache_lock(root, key):
                with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "CACHE_KEY_LOCKED"):
                    with BRIDGE.cache_lock(root, key):
                        pass
            self.assertFalse((root / "locks" / f"{key}.lock").exists())

    def test_all_authority_blocker_branches(self) -> None:
        cases = {
            "reference": "BLOCKED_REFERENCE_RIGHTS_OR_PROVENANCE",
            "engine": "BLOCKED_ENGINE_MODEL_OR_RUNTIME_MISSING",
            "license": "BLOCKED_ASSET_LICENSE_OR_GATED_ACCESS",
            "assets": "BLOCKED_ASSET_EXACT_SOURCE_OR_HASH_UNRESOLVED",
        }
        for case, expected in cases.items():
            with self.subTest(case=case):
                value = request()
                value["authority"]["voice_authority_valid"] = True
                value["authority"]["production_authorized"] = True
                if case == "reference":
                    value["reference_bindings"][0]["rights_valid"] = False
                elif case == "engine":
                    value["authority"]["engine_runtime_valid"] = False
                elif case == "license":
                    value["authority"]["asset_license_valid"] = False
                else:
                    value["authority"]["exact_assets_resolved"] = False
                self.assertIn(expected, BRIDGE.authority_blockers(value))

    def test_immutable_result_conflict_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            BRIDGE.write_json_atomic(path, {"value": 1}, immutable=True)
            with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "IMMUTABLE_BRIDGE_RESULT_CONFLICT"):
                BRIDGE.write_json_atomic(path, {"value": 2}, immutable=True)

    def test_non_dry_run_dispatch_is_not_implemented_or_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = request()
            value["dry_run"] = False
            with self.assertRaisesRegex(BRIDGE.SpeechBridgeError, "REQUIRES_DRY_RUN"):
                BRIDGE.execute_request(value, dry_run=False, root=Path(temporary))

    def test_cache_report_aggregates_real_local_telemetry_without_dollar_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            telemetry = cache / "telemetry"
            telemetry.mkdir()
            (telemetry / "one.json").write_text(json.dumps({
                "schema_version": "1.0", "cache_hit": False, "wall_clock_seconds": 0.25,
            }), encoding="utf-8")
            report = MANAGE.report(cache)
            self.assertEqual(1, report["telemetry_record_count"])
            self.assertEqual(0.25, report["total_wall_clock_seconds"])
            self.assertIsNone(report["estimated_cost_usd"])

    def test_history_parser_rejects_media_and_accepts_text_result(self) -> None:
        result = {"classification": "W64_SPEECH_BRIDGE_DRY_RUN_VALIDATED_AUTHORITY_BLOCKED"}
        history = {"p1": {
            "status": {"status_str": "success", "completed": True},
            "outputs": {"1": {"text": [json.dumps(result)]}},
        }}
        self.assertEqual(result, SMOKER.extract_result(history, "p1"))
        history["p1"]["outputs"]["1"]["audio"] = [{"filename": "bad.wav"}]
        with self.assertRaisesRegex(SMOKER.SmokeError, "emitted media"):
            SMOKER.extract_result(history, "p1")

    def test_tracked_workflow_is_one_bridge_node_with_no_media_output(self) -> None:
        lane = ROOT / "Workflows/audio_generation/wave64_speech_bridge_dry_run"
        workflow = json.loads((lane / "workflow.api.json").read_text(encoding="utf-8"))
        requirements = json.loads((lane / "runtime_requirements.json").read_text(encoding="utf-8"))
        self.assertEqual(["1"], list(workflow))
        self.assertEqual("Wave64SpeechBridge", workflow["1"]["class_type"])
        embedded = json.loads(workflow["1"]["inputs"]["request_json"])
        BRIDGE.validate_request(embedded)
        self.assertTrue(embedded["dry_run"])
        self.assertFalse(requirements["execution_contract"]["media_output_allowed"])
        self.assertFalse(requirements["execution_contract"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
