import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "07_IMPLEMENTATION"
    / "scripts"
    / "route_video_engine_candidate.py"
)

spec = importlib.util.spec_from_file_location("route_video_engine_candidate", SCRIPT_PATH)
router = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(router)


def base_request():
    return {
        "output_type": "mp4",
        "width": 1280,
        "height": 720,
        "duration_seconds": 6.0,
        "fps": 24.0,
        "character_count": 1,
        "camera_movement": "low",
        "motion_complexity": "low",
        "reference_video_present": False,
        "keyframe_count": 0,
        "identity_lock_required": False,
        "contact_deformation_required": False,
        "audio_required": False,
        "prior_generation_failed": False,
        "frame_sequence_available": False,
        "isolated_frame_failure": False,
        "structured_linear_guidance": False,
        "execution_target": "local",
        "available_vram_gb": 16.0,
        "cost_tier": "medium",
        "requested_engine": None,
        "promotion_required": True,
    }


def unverified_engine(engine_id, engine_class):
    return {
        "id": engine_id,
        "class": engine_class,
        "best_for": [],
        "model_registry_link": {"verification_status": "unverified", "value": None},
        "object_info_evidence": {"verification_status": "unverified", "value": None},
        "runtime_proof": {"verification_status": "unverified", "value": None},
        "supported_outputs": {"verification_status": "unverified", "values": []},
        "supported_features": {"verification_status": "unverified", "values": []},
        "resource_limits": {
            "verification_status": "unverified",
            "max_width": None,
            "max_height": None,
            "max_duration_seconds": None,
            "max_fps": None,
            "min_vram_gb": None,
        },
        "execution_targets": {"verification_status": "unverified", "values": []},
        "cost_tiers": {"verification_status": "unverified", "values": []},
        "availability": {"verification_status": "unverified", "state": None},
        "promotion_proof": {"verification_status": "unverified", "items": []},
    }


def verified_engine(engine_id, engine_class, features):
    normalized_features = sorted(set(features)) if features else ["reference_video_input"]
    return {
        "id": engine_id,
        "class": engine_class,
        "best_for": [],
        "model_registry_link": {
            "verification_status": "verified",
            "value": "registry://model",
        },
        "object_info_evidence": {
            "verification_status": "verified",
            "value": "object_info://proof",
        },
        "runtime_proof": {
            "verification_status": "verified",
            "value": "runtime://proof",
        },
        "supported_outputs": {
            "verification_status": "verified",
            "values": ["mp4", "gif", "webm", "image_sequence"],
        },
        "supported_features": {
            "verification_status": "verified",
            "values": normalized_features,
        },
        "resource_limits": {
            "verification_status": "verified",
            "max_width": 1920,
            "max_height": 1080,
            "max_duration_seconds": 30.0,
            "max_fps": 30.0,
            "min_vram_gb": 8.0,
        },
        "execution_targets": {
            "verification_status": "verified",
            "values": ["local", "ec2"],
        },
        "cost_tiers": {
            "verification_status": "verified",
            "values": ["low", "medium", "high"],
        },
        "availability": {"verification_status": "verified", "state": "available"},
        "promotion_proof": {
            "verification_status": "verified",
            "items": ["qa_manifest_hash"],
        },
    }


def default_rules():
    return {
        "rules": [
            {
                "id": "isolated_frame_repair",
                "priority": 10,
                "route": "frame_repair_lane",
                "all": [{"field": "isolated_frame_failure", "op": "eq", "value": True}],
            },
            {
                "id": "failed_generation_with_frame_sequence",
                "priority": 20,
                "route": "animatediff_fallback",
                "all": [
                    {"field": "prior_generation_failed", "op": "eq", "value": True},
                    {"field": "frame_sequence_available", "op": "eq", "value": True},
                ],
            },
            {
                "id": "ltx_audio_preference",
                "priority": 30,
                "route": "ltxv",
                "all": [{"field": "audio_required", "op": "eq", "value": True}],
            },
            {
                "id": "reference_video_priority",
                "priority": 40,
                "route": "ltxv",
                "all": [{"field": "reference_video_present", "op": "eq", "value": True}],
            },
            {
                "id": "structured_linear_guidance",
                "priority": 50,
                "route": "hunyuan_video",
                "all": [{"field": "structured_linear_guidance", "op": "eq", "value": True}],
            },
            {
                "id": "keyframe_moderate_motion",
                "priority": 60,
                "route": "wan",
                "all": [
                    {"field": "keyframe_count", "op": "gte", "value": 1},
                    {"field": "motion_complexity", "op": "eq", "value": "moderate"},
                ],
            },
            {
                "id": "default_primary_candidate_wan",
                "priority": 70,
                "route": "wan",
                "all": [],
            },
        ]
    }


class RouteVideoEngineCandidateTests(unittest.TestCase):
    def canonical_registry(self):
        return {
            "engines": [
                unverified_engine("ltxv", "video_model"),
                unverified_engine("wan", "video_model"),
                unverified_engine("hunyuan_video", "video_model"),
                unverified_engine("animatediff_fallback", "fallback"),
                unverified_engine("frame_repair_lane", "repair"),
            ]
        }

    def registry_with_overrides(self, overrides):
        registry = self.canonical_registry()
        by_id = {engine["id"]: engine for engine in registry["engines"]}
        for key, value in overrides.items():
            by_id[key] = value
        return {"engines": [by_id["ltxv"], by_id["wan"], by_id["hunyuan_video"], by_id["animatediff_fallback"], by_id["frame_repair_lane"]]}

    def test_canonical_fail_closed_behavior(self):
        request = base_request()
        decision = router.decide_route(request, self.canonical_registry(), default_rules())
        self.assertIsNone(decision["selected_engine"])
        self.assertEqual(decision["result"], "blocked")
        self.assertFalse(decision["runtime_ready"])
        self.assertFalse(decision["final_promotion_ready"])
        self.assertEqual(decision["decision_scope"], "offline_routing_only")
        self.assertEqual(decision["candidate_order"], ["wan"])
        self.assertEqual(decision["matched_rule_ids"], ["default_primary_candidate_wan"])

    def test_rule_families_prioritize_expected_candidate(self):
        registry = self.canonical_registry()
        cases = [
            ("isolated_frame_failure", {"isolated_frame_failure": True}, "frame_repair_lane"),
            (
                "failed_generation_with_frame_sequence",
                {"prior_generation_failed": True, "frame_sequence_available": True},
                "animatediff_fallback",
            ),
            ("audio_required", {"audio_required": True}, "ltxv"),
            ("reference_video_present", {"reference_video_present": True}, "ltxv"),
            ("structured_linear_guidance", {"structured_linear_guidance": True}, "hunyuan_video"),
            (
                "keyframe_moderate_motion",
                {"keyframe_count": 2, "motion_complexity": "moderate"},
                "wan",
            ),
        ]
        for _, patch, expected in cases:
            request = base_request()
            request.update(patch)
            decision = router.decide_route(request, registry, default_rules())
            self.assertEqual(decision["candidate_order"][0], expected)

    def test_requested_engine_handling(self):
        request = base_request()
        request["requested_engine"] = "unknown_engine"
        decision = router.decide_route(request, self.canonical_registry(), default_rules())
        self.assertIsNone(decision["selected_engine"])
        self.assertIn("candidate_not_registered:unknown_engine", decision["blocked_reasons"])

    def test_requested_engine_success_with_verified_fixture(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["promotion_required"] = False
        registry = self.registry_with_overrides({"wan": verified_engine("wan", "video_model", [])})
        decision = router.decide_route(request, registry, default_rules())
        self.assertEqual(decision["selected_engine"], "wan")
        self.assertEqual(decision["result"], "compatible")
        self.assertTrue(decision["runtime_ready"])
        self.assertFalse(decision["final_promotion_ready"])
        self.assertEqual(decision["matched_rule_ids"], ["requested_engine_override"])

    def test_resource_and_cost_blocks(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["promotion_required"] = False
        engine = verified_engine("wan", "video_model", [])
        engine["resource_limits"]["max_width"] = 640
        engine["resource_limits"]["max_height"] = 360
        engine["resource_limits"]["max_duration_seconds"] = 2.0
        engine["resource_limits"]["max_fps"] = 12.0
        engine["resource_limits"]["min_vram_gb"] = 20.0
        engine["cost_tiers"]["values"] = ["low"]
        registry = self.registry_with_overrides({"wan": engine})
        decision = router.decide_route(request, registry, default_rules())
        self.assertIsNone(decision["selected_engine"])
        self.assertIn("wan:resource_limits:insufficient_or_unverified", decision["blocked_reasons"])
        self.assertIn("wan:cost_tiers:unsupported_or_unverified", decision["blocked_reasons"])

    def test_required_feature_blocks(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["identity_lock_required"] = True
        request["promotion_required"] = False
        registry = self.registry_with_overrides({"wan": verified_engine("wan", "video_model", [])})
        decision = router.decide_route(request, registry, default_rules())
        self.assertIsNone(decision["selected_engine"])
        self.assertIn("wan:supported_features:missing_or_unverified", decision["blocked_reasons"])

    def test_missing_model_object_runtime_proof_blocks(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["promotion_required"] = False
        engine = verified_engine("wan", "video_model", [])
        engine["model_registry_link"]["verification_status"] = "unverified"
        engine["object_info_evidence"]["verification_status"] = "unverified"
        engine["runtime_proof"]["verification_status"] = "unverified"
        engine["model_registry_link"]["value"] = None
        engine["object_info_evidence"]["value"] = None
        engine["runtime_proof"]["value"] = None
        decision = router.decide_route(
            request,
            self.registry_with_overrides({"wan": engine}),
            default_rules(),
        )
        self.assertIsNone(decision["selected_engine"])
        self.assertIn("wan:model_registry_link:unverified", decision["blocked_reasons"])
        self.assertIn("wan:object_info_evidence:unverified", decision["blocked_reasons"])
        self.assertIn("wan:runtime_proof:unverified", decision["blocked_reasons"])

    def test_bool_as_int_rejected_in_request(self):
        request = base_request()
        request["width"] = True
        with self.assertRaises(ValueError):
            router.decide_route(request, self.canonical_registry(), default_rules())

    def test_bool_as_int_rejected_in_rules(self):
        request = base_request()
        rules = default_rules()
        rules["rules"][0]["priority"] = True
        with self.assertRaises(ValueError):
            router.decide_route(request, self.canonical_registry(), rules)

    def test_malformed_verified_limits_fail_closed(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["promotion_required"] = False
        engine = verified_engine("wan", "video_model", [])
        engine["resource_limits"]["max_width"] = True
        with self.assertRaises(ValueError):
            router.decide_route(
                request,
                self.registry_with_overrides({"wan": engine}),
                default_rules(),
            )

    def test_unverified_scalar_evidence_must_be_null(self):
        engine = unverified_engine("wan", "video_model")
        engine["object_info_evidence"]["value"] = "hidden://unverified"
        with self.assertRaises(ValueError):
            router.decide_route(
                base_request(),
                self.registry_with_overrides({"wan": engine}),
                default_rules(),
            )

    def test_duplicate_engine_id_rejected(self):
        registry = {"engines": [unverified_engine("wan", "video_model"), unverified_engine("wan", "fallback")]}
        with self.assertRaises(ValueError):
            router.decide_route(base_request(), registry, default_rules())

    def test_duplicate_rule_id_rejected(self):
        rules = default_rules()
        rules["rules"][1]["id"] = rules["rules"][0]["id"]
        with self.assertRaises(ValueError):
            router.decide_route(base_request(), self.canonical_registry(), rules)

    def test_candidate_dedup_preserves_priority_order(self):
        request = base_request()
        request["audio_required"] = True
        request["reference_video_present"] = True
        decision = router.decide_route(request, self.canonical_registry(), default_rules())
        self.assertEqual(decision["candidate_order"], ["ltxv", "wan"])
        self.assertEqual(
            decision["matched_rule_ids"],
            ["ltx_audio_preference", "reference_video_priority", "default_primary_candidate_wan"],
        )

    def test_repair_and_fallback_override_precedence(self):
        request = base_request()
        request["isolated_frame_failure"] = True
        request["prior_generation_failed"] = True
        request["frame_sequence_available"] = True
        request["audio_required"] = True
        request["reference_video_present"] = True
        decision = router.decide_route(request, self.canonical_registry(), default_rules())
        self.assertEqual(decision["candidate_order"][0], "frame_repair_lane")
        self.assertEqual(decision["candidate_order"][1], "animatediff_fallback")
        self.assertIn("isolated_frame_repair", decision["matched_rule_ids"])
        self.assertIn("failed_generation_with_frame_sequence", decision["matched_rule_ids"])

    def test_default_wan_trace_and_hashes(self):
        decision = router.decide_route(base_request(), self.canonical_registry(), default_rules())
        self.assertEqual(decision["candidate_order"], ["wan"])
        self.assertEqual(decision["matched_rule_ids"], ["default_primary_candidate_wan"])
        self.assertEqual(decision["result"], "blocked")
        self.assertEqual(decision["request_sha256"], router.canonical_json_sha256(base_request()))
        self.assertEqual(
            decision["registry_sha256"],
            router.canonical_json_sha256(self.canonical_registry()),
        )
        self.assertEqual(
            decision["rules_sha256"],
            router.canonical_json_sha256(default_rules()),
        )

    def test_malformed_unknown_field_rejected(self):
        request = base_request()
        request["unknown_field"] = True
        with self.assertRaises(ValueError):
            router.decide_route(request, self.canonical_registry(), default_rules())

    def test_non_finite_json_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            request_path.write_text(
                '{"output_type":"mp4","width":1280,"height":720,'
                '"duration_seconds":NaN,"fps":24,"character_count":1,'
                '"camera_movement":"moderate","motion_complexity":"moderate",'
                '"reference_video_present":false,"keyframe_count":0,'
                '"identity_lock_required":false,"contact_deformation_required":false,'
                '"audio_required":false,"prior_generation_failed":false,'
                '"frame_sequence_available":false,"isolated_frame_failure":false,'
                '"structured_linear_guidance":false,"execution_target":"local",'
                '"available_vram_gb":16,"cost_tier":"medium","requested_engine":null,'
                '"promotion_required":true}',
                encoding="ascii",
            )
            with self.assertRaises(ValueError):
                router.load_json(request_path)

    def test_deterministic_output(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["promotion_required"] = False
        registry = self.registry_with_overrides({"wan": verified_engine("wan", "video_model", [])})
        first = router.decide_route(request, registry, default_rules())
        second = router.decide_route(request, registry, default_rules())
        self.assertEqual(first, second)

    def test_final_promotion_claim_never_true(self):
        request = base_request()
        request["requested_engine"] = "wan"
        request["promotion_required"] = False
        registry = self.registry_with_overrides({"wan": verified_engine("wan", "video_model", [])})
        decision = router.decide_route(request, registry, default_rules())
        self.assertIn("final_promotion_ready", decision)
        self.assertFalse(decision["final_promotion_ready"])

    def test_cli_failure_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "bad_request.json"
            request_path.write_text('{"width": true}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--request", str(request_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.strip(), "")
            payload = json.loads(proc.stderr)
            self.assertEqual(payload["result"], "blocked")
            self.assertFalse(payload["final_promotion_ready"])
            self.assertIsNone(payload["selected_engine"])
            decision_schema = json.loads(
                (Path(__file__).resolve().parents[3] / "08_SCHEMAS" / "video_engine_route_decision.schema.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(set(payload), set(decision_schema["required"]))
            self.assertIsNone(payload["request_sha256"])
            self.assertIsNone(payload["registry_sha256"])
            self.assertIsNone(payload["rules_sha256"])

    def test_cli_output_writes_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            output_path = Path(temp_dir) / "nested" / "decision.json"
            request_path.write_text(json.dumps(base_request()), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--request",
                    str(request_path),
                    "--registry",
                    str(Path(__file__).resolve().parents[3] / "10_REGISTRIES" / "wave27_video_engine_registry.json"),
                    "--rules",
                    str(Path(__file__).resolve().parents[3] / "10_REGISTRIES" / "wave27_video_route_selection_rules.json"),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.strip(), "")
            self.assertTrue(output_path.exists())

    def test_cli_unwritable_output_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_path = Path(temp_dir) / "request.json"
            request_path.write_text(json.dumps(base_request()), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--request",
                    str(request_path),
                    "--registry",
                    str(Path(__file__).resolve().parents[3] / "10_REGISTRIES" / "wave27_video_engine_registry.json"),
                    "--rules",
                    str(Path(__file__).resolve().parents[3] / "10_REGISTRIES" / "wave27_video_route_selection_rules.json"),
                    "--output",
                    str(Path(temp_dir)),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.strip(), "")
            payload = json.loads(proc.stderr)
            self.assertEqual(payload["result"], "blocked")
            self.assertFalse(payload["final_promotion_ready"])


if __name__ == "__main__":
    unittest.main()
