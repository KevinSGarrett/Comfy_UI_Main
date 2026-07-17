from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/bind_flux2_repair_packet_to_sdxl_inpaint.py"
WORKFLOW = ROOT / "Workflows/base_generation/sdxl_realvisxl_inpaint_detail_lane/workflow.api.json"
PATCH_POINTS = ROOT / "Workflows/base_generation/sdxl_realvisxl_inpaint_detail_lane/patch_points.json"
REQUIREMENTS = ROOT / "Workflows/base_generation/sdxl_realvisxl_inpaint_detail_lane/runtime_requirements.json"
PROFILE = ROOT / "Plan/10_REGISTRIES/flux2_seed7261704_structural_repair_profile.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Flux2RepairPacketSdxlBindingTests(unittest.TestCase):
    def make_packet(self, root: Path) -> Path:
        source = root / "source.png"
        mask = root / "mask.png"
        Image.new("RGB", (64, 80), (100, 110, 120)).save(source)
        operational_mask = Image.new("L", (64, 80), 0)
        for x in range(20, 40):
            for y in range(25, 55):
                operational_mask.putpixel((x, y), 255)
        operational_mask.save(mask)
        packet = {
            "classification": "LOCALIZED_ANATOMY_REPAIR_PACKET_READY_GENERATION_NOT_EXECUTED",
            "source": {"path": "source.png", "sha256": sha256_file(source), "width": 64, "height": 80},
            "prompt_request": {"seed": 7261704},
            "operational_mask": {
                "path": "mask.png",
                "sha256": sha256_file(mask),
                "classification": "non_gold_operational_repair_region",
                "consumed_as_evaluation_truth": False,
            },
            "runtime": {"generation_executed": False},
            "boundaries": {"production_promotion_allowed": False},
        }
        packet_path = root / "repair_packet.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        return packet_path

    def run_binder(self, root: Path, packet_path: Path) -> subprocess.CompletedProcess[str]:
        lane_dir = root / "lane"
        lane_dir.mkdir(exist_ok=True)
        shutil.copy2(WORKFLOW, lane_dir / "workflow.api.json")
        shutil.copy2(PATCH_POINTS, lane_dir / "patch_points.json")
        shutil.copy2(REQUIREMENTS, lane_dir / "runtime_requirements.json")
        shutil.copy2(PROFILE, lane_dir / "structural_profile.json")
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(root),
                "--repair-packet",
                packet_path.name,
                "--workflow",
                "lane/workflow.api.json",
                "--patch-points",
                "lane/patch_points.json",
                "--runtime-requirements",
                "lane/runtime_requirements.json",
                "--structural-profile",
                "lane/structural_profile.json",
                "--seed",
                "7261704",
                "--positive-prompt",
                "remove detached extra hand, reconstruct empty workbench",
                "--negative-prompt",
                "extra hand, duplicate limb, identity change",
                "--save-prefix",
                "flux2_seed7261704_sdxl_repair",
                "--output-dir",
                "binding",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_builds_static_binding_with_source_preserving_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            packet_path = self.make_packet(root)
            result = self.run_binder(root, packet_path)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            manifest = json.loads((root / "binding/binding_manifest.json").read_text(encoding="utf-8"))
            prompt = json.loads((root / "binding/prompt_request.json").read_text(encoding="utf-8"))
            self.assertTrue(all(manifest["topology_checks"].values()))
            self.assertEqual(manifest["prompt_request"]["patch_count"], 13)
            self.assertFalse(manifest["runtime"]["execution_allowed"])
            self.assertEqual(manifest["runtime"]["candidate_count_allowed"], 1)
            self.assertFalse(manifest["boundaries"]["cross_family_latent_transfer_allowed"])
            self.assertEqual(prompt["prompt"]["5"]["inputs"]["image"], "flux2_seed7261704_source.png")
            self.assertEqual(
                prompt["prompt"]["6"]["inputs"]["image"],
                "flux2_seed7261704_operational_repair_mask.png",
            )
            self.assertEqual(prompt["prompt"]["3"]["inputs"]["denoise"], 0.38)
            self.assertEqual(prompt["prompt"]["14"]["inputs"]["destination"], ["5", 0])
            self.assertTrue(
                manifest["input_provisioning"][1]["channel_verification"]
                ["grayscale_to_red_equivalent_after_rgb_conversion"]
            )
            self.assertFalse(manifest["lane"]["existing_body_hand_contact_authority_inherited"])
            self.assertEqual(
                manifest["structural_repair_profile"]["calibration_status"],
                "unproven_structural_removal_pilot",
            )

    def test_rejects_tampered_operational_mask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            packet_path = self.make_packet(root)
            (root / "mask.png").write_bytes(b"tampered")
            result = self.run_binder(root, packet_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("operational mask hash mismatch", result.stderr)

    def test_rejects_packet_that_allows_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            packet_path = self.make_packet(root)
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["boundaries"]["production_promotion_allowed"] = True
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            result = self.run_binder(root, packet_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("promotion boundary", result.stderr)


if __name__ == "__main__":
    unittest.main()
