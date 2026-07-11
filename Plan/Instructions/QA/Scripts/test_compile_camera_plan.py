#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = PROJECT_ROOT / "Plan" / "07_IMPLEMENTATION" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from compile_camera_plan import compile_plan, compile_prompt_profile  # noqa: E402
from score_framing_composition import score  # noqa: E402
from validate_camera_plan import validate_plan  # noqa: E402


def full_body_request() -> dict:
    return {
        "camera_plan_id": "cam_test_full_body",
        "scene_id": "scene_test",
        "shot_size": "full_body",
        "lens_profile": "classic_35mm",
        "camera_angle": "eye_level",
        "width": 768,
        "height": 1024,
        "aspect_ratio": "3:4",
        "must_not_crop": ["head", "hair", "hands", "feet"],
        "positive_prompt": "hyperrealistic photograph of exactly one fully clothed adult",
        "negative_prompt": "cartoon, illustration",
        "seed": 7152026101,
        "save_prefix": "camera_test_full_body",
        "reference_route": {"enabled": False},
        "control_plan": {"enabled": False},
    }


class CompileCameraPlanTests(unittest.TestCase):
    def test_compile_plan_backward_compatible_default_request(self) -> None:
        plan = compile_plan({})
        self.assertEqual(plan["shot_size"], "half_body")
        self.assertEqual(plan["resolution"], {"width": 1024, "height": 1280})
        self.assertIn("workflow_instructions", plan)

    def test_profile_is_deterministic(self) -> None:
        request = full_body_request()
        plan_a = compile_plan(copy.deepcopy(request))
        plan_b = compile_plan(copy.deepcopy(request))
        self.assertEqual(plan_a, plan_b)
        self.assertEqual(compile_prompt_profile(request, plan_a), compile_prompt_profile(request, plan_b))

    def test_unknown_taxonomies_fail_closed(self) -> None:
        for field, value in (
            ("shot_size", "mystery_shot"),
            ("lens_profile", "imaginary_42mm"),
            ("camera_angle", "inside_out"),
        ):
            request = full_body_request()
            request[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_plan(request)

    def test_invalid_dimensions_fail_closed(self) -> None:
        for field, value in (("width", 0), ("width", 513), ("height", 4096), ("height", "bad"), ("width", True)):
            request = full_body_request()
            request[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                compile_plan(request)

    def test_nonintegral_seed_steps_and_depth_order_fail_closed(self) -> None:
        seed_request = full_body_request()
        seed_request["seed"] = 1.5
        with self.assertRaisesRegex(ValueError, "seed_must_be_an_integer"):
            plan = compile_plan(seed_request)
            compile_prompt_profile(seed_request, plan)

        steps_request = full_body_request()
        steps_request["sampler_settings"] = {"steps": 12.5}
        with self.assertRaisesRegex(ValueError, "sampler_settings.steps_must_be_an_integer"):
            plan = compile_plan(steps_request)
            compile_prompt_profile(steps_request, plan)

        depth_request = full_body_request()
        depth_request["subjects"] = [{"depth_order": 1.5, "must_show": ["face", "hands", "feet"]}]
        with self.assertRaisesRegex(ValueError, "depth_order_must_be_an_integer"):
            compile_plan(depth_request)

    def test_nonfinite_float_fields_fail_closed(self) -> None:
        for field, value in (("background_blur_strength", float("nan")), ("background_blur_strength", float("inf"))):
            request = full_body_request()
            request[field] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                compile_plan(request)

        request = full_body_request()
        request["sampler_settings"] = {"cfg": float("nan")}
        with self.assertRaisesRegex(ValueError, "cfg_must_be_finite"):
            plan = compile_plan(request)
            compile_prompt_profile(request, plan)

    def test_full_body_crop_override_fails_closed(self) -> None:
        request = full_body_request()
        request["must_not_crop"] = ["head", "hands"]
        with self.assertRaisesRegex(ValueError, "full_body_must_not_crop_missing"):
            compile_plan(request)

    def test_full_body_intentional_crop_fails_closed(self) -> None:
        request = full_body_request()
        request["intentional_crop_allowed"] = True
        with self.assertRaisesRegex(ValueError, "full_body_intentional_crop"):
            compile_plan(request)

    def test_reference_and_control_are_disabled_by_default(self) -> None:
        request = full_body_request()
        request.pop("reference_route")
        request.pop("control_plan")
        instructions = compile_plan(request)["workflow_instructions"]
        self.assertFalse(instructions["reference_routing_plan"]["enabled"])
        self.assertFalse(instructions["control_plan"]["enabled"])

    def test_reference_claim_without_proof_fails(self) -> None:
        request = full_body_request()
        request["reference_route"] = {"enabled": True, "route_id": "ipadapter", "asset": "face.png"}
        with self.assertRaisesRegex(ValueError, "reference_route_requires_explicit_proven_status"):
            compile_plan(request)

    def test_control_claim_without_proof_fails(self) -> None:
        request = full_body_request()
        request["control_plan"] = {"enabled": True, "route_id": "canny"}
        with self.assertRaisesRegex(ValueError, "control_plan_requires_explicit_proven_status"):
            compile_plan(request)

    def test_profile_contains_run_package_patch_values(self) -> None:
        request = full_body_request()
        plan = compile_plan(request)
        profile = compile_prompt_profile(request, plan)
        patch = profile["request_patch_values"]
        self.assertEqual(profile["target_lane_id"], "sdxl_realvisxl_base_lane")
        self.assertEqual(patch["latent_resolution"], {"width": 768, "height": 1024, "batch_size": 1})
        self.assertIn("cropped feet", patch["negative_prompt"])
        self.assertIn("entire subject visible", patch["positive_prompt"])
        self.assertEqual(patch["save_prefix"], "camera_test_full_body")
        self.assertFalse(profile["runtime_boundaries"]["aws_contacted"])
        self.assertFalse(profile["runtime_boundaries"]["generation_executed"])

    def test_validator_passes_compiler_output(self) -> None:
        report = validate_plan(compile_plan(full_body_request()))
        self.assertEqual(report["validation"], "PASS")
        self.assertEqual(report["blocking_issues"], [])

    def test_validator_blocks_tampered_crop_and_latent(self) -> None:
        plan = compile_plan(full_body_request())
        plan["framing"]["must_not_crop"].remove("feet")
        plan["workflow_instructions"]["latent_resolution"]["width"] = 1024
        report = validate_plan(plan)
        self.assertEqual(report["validation"], "FAIL")
        self.assertTrue(any("must_not_crop missing" in issue for issue in report["blocking_issues"]))
        self.assertTrue(any("latent resolution" in issue for issue in report["blocking_issues"]))

    def test_scorer_detects_profile_resolution_mismatch(self) -> None:
        request = full_body_request()
        plan = compile_plan(request)
        profile = compile_prompt_profile(request, plan)
        profile["request_patch_values"]["latent_resolution"]["width"] = 1024
        result = score(plan, {"profile": profile})
        self.assertLess(result["metadata_score"], 100)
        self.assertTrue(any("does not match" in issue for issue in result["issues"]))

    def test_cli_writes_plan_and_profile(self) -> None:
        script = SCRIPT_DIR / "compile_camera_plan.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            request_path = temp / "request.json"
            plan_path = temp / "plan.json"
            profile_path = temp / "profile.json"
            request_path.write_text(json.dumps(full_body_request()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--request",
                    str(request_path),
                    "--out",
                    str(plan_path),
                    "--profile-out",
                    str(profile_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(plan_path.read_text(encoding="utf-8"))["shot_size"], "full_body")
            self.assertEqual(
                json.loads(profile_path.read_text(encoding="utf-8"))["profile_id"],
                "camera_test_full_body_profile",
            )


if __name__ == "__main__":
    unittest.main()
