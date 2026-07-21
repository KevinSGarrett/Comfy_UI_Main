from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / (
    "Plan/07_IMPLEMENTATION/scripts/validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
)
OVERSTATED = ROOT / (
    "Plan/Instructions/QA/Evidence/Wave64/"
    "TRK-W64-019_023_RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_PROOF_20260721T004726-0500.json"
)

spec = importlib.util.spec_from_file_location(
    "validate_wave64_wan_ti2v_class_e_runtime_proof_claim", MODULE_PATH
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class WanTi2vClassEClaimPolicyTest(unittest.TestCase):
    def test_overstated_proof_landed_packet_fails_closed(self) -> None:
        packet = module.load_json(OVERSTATED)
        result = module.evaluate_claim(packet)
        self.assertFalse(result["policy_pass"])
        self.assertIn("class_e_proof_min_bytes", result["failed_checks"])
        self.assertIn("visual_review_performed_for_proof_success", result["failed_checks"])

    def test_tiny_black_ish_bytes_fail_absolute_floor(self) -> None:
        packet = {
            "claim_tier": "smoke_emission",
            "status": "Blocked_Runtime_Smoke_Emitted",
            "row_complete": False,
            "production_completion_allowed": False,
            "production_video_complete_claimed": False,
            "row074_touched": False,
            "ec2_touched": False,
            "generation": {"artifact": {"bytes": 1200}},
        }
        result = module.evaluate_claim(packet)
        self.assertFalse(result["policy_pass"])
        self.assertIn("artifact_above_absolute_min_bytes", result["failed_checks"])

    def test_honest_smoke_claim_passes(self) -> None:
        packet = {
            "claim_tier": "smoke_emission",
            "status": "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Runtime_Smoke_Emitted",
            "verdict": "WAN_TI2V_BOUNDED_RUNTIME_SMOKE_EMISSION_ON_RUNPOD",
            "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_RUNTIME_SMOKE_EMISSION",
            "row_complete": False,
            "production_completion_allowed": False,
            "production_video_complete_claimed": False,
            "row074_touched": False,
            "ec2_touched": False,
            "vlm_review": {"performed": False, "reason": "smoke_not_product_visual_pass"},
            "generation": {"artifact": {"bytes": 94378}},
        }
        result = module.evaluate_claim(packet)
        self.assertTrue(result["policy_pass"], result["failed_checks"])

    def test_class_e_proof_requires_bytes_and_visual_pass(self) -> None:
        packet = {
            "claim_tier": "class_e_runtime_proof",
            "status": "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_E_Runtime_Proof_Landed",
            "verdict": "WAN_TI2V_BOUNDED_RUNTIME_GENERATION_PROOF_ON_RUNPOD",
            "row_complete": False,
            "production_completion_allowed": False,
            "production_video_complete_claimed": False,
            "row074_touched": False,
            "ec2_touched": False,
            "vlm_review": {"performed": True, "pass": True},
            "generation": {"artifact": {"bytes": 400_000}},
        }
        result = module.evaluate_claim(packet)
        self.assertTrue(result["policy_pass"], result["failed_checks"])

    def test_honest_fail_reject_below_bytes_floor_passes(self) -> None:
        packet = {
            "claim_tier": "class_e_attempt_fail",
            "status": (
                "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
                "Class_E_Proof_Attempt_FAIL_Bytes_Gate"
            ),
            "verdict": "WAN_TI2V_BOUNDED_CLASS_E_PROOF_ATTEMPT_FAIL_REJECT",
            "proof_tier": "RUNPOD_WAN_TI2V_BOUNDED_CLASS_E_PROOF_ATTEMPT_FAIL",
            "row_complete": False,
            "production_completion_allowed": False,
            "production_video_complete_claimed": False,
            "row074_touched": False,
            "ec2_touched": False,
            "vlm_review": {"performed": True, "pass": True},
            "generation": {"artifact": {"bytes": 194351}},
        }
        result = module.evaluate_claim(packet)
        self.assertTrue(result["policy_pass"], result["failed_checks"])
        self.assertTrue(result["uses_fail_language"])


if __name__ == "__main__":
    unittest.main()
