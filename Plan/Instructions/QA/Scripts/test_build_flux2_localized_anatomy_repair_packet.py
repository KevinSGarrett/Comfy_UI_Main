from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_flux2_localized_anatomy_repair_packet.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LocalizedAnatomyRepairPacketTests(unittest.TestCase):
    def make_fixture(self, root: Path, result: str = "fail_whole_image_anatomy") -> tuple[Path, Path]:
        source = root / "source.png"
        Image.new("RGB", (100, 120), (90, 100, 110)).save(source)
        evidence = root / "evidence.json"
        evidence.write_text(
            json.dumps(
                {
                    "visual_qa": {
                        "samples": [
                            {
                                "run_id": "adult_woman_portrait_seed7261704",
                                "seed": 7261704,
                                "artifact": "source.png",
                                "sha256": sha256_file(source),
                                "result": result,
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        prompt = root / "prompt.json"
        prompt.write_text(
            json.dumps(
                {
                    "client_id": "fixture",
                    "prompt": {"8": {"class_type": "RandomNoise", "inputs": {"noise_seed": 7261704}}},
                }
            ),
            encoding="utf-8",
        )
        return evidence, prompt

    def run_builder(self, root: Path, evidence: Path, prompt: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--project-root",
                str(root),
                "--qualification-evidence",
                evidence.name,
                "--prompt-request",
                prompt.name,
                "--seed",
                "7261704",
                "--defect-region-id",
                "extraneous_left_workbench_hand_forearm",
                "--defect-description",
                "detached extra hand and forearm",
                "--bbox",
                "20",
                "30",
                "40",
                "50",
                "--polygon",
                "22,32",
                "58,32",
                "58,78",
                "22,78",
                "--context-margin",
                "12",
                "--output-dir",
                "packet",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_builds_hash_bound_fail_closed_packet_and_operational_mask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            evidence, prompt = self.make_fixture(root)
            result = self.run_builder(root, evidence, prompt)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            packet = json.loads((root / "packet/repair_packet.json").read_text(encoding="utf-8"))
            contract = json.loads(
                (root / "packet/hard_anatomy_repair_contract.json").read_text(encoding="utf-8")
            )
            mask_path = root / packet["operational_mask"]["path"]
            with Image.open(mask_path) as mask:
                self.assertIsNotNone(mask.getbbox())
                self.assertEqual(mask.getpixel((10, 10)), 0)
                self.assertEqual(mask.getpixel((30, 40)), 255)

            self.assertEqual(packet["hard_anatomy_contract"]["canonical_validator_result"], "PASS")
            self.assertFalse(packet["runtime"]["generation_executed"])
            self.assertFalse(packet["runtime"]["runtime_execution_allowed"])
            self.assertFalse(packet["operational_mask"]["consumed_as_evaluation_truth"])
            self.assertFalse(packet["boundaries"]["production_promotion_allowed"])
            self.assertTrue(contract["hard_reject_on_deformation"]["triggered"])
            self.assertFalse(contract["hard_reject_on_deformation"]["promotion_allowed"])

    def test_rejects_tampered_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            evidence, prompt = self.make_fixture(root)
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["visual_qa"]["samples"][0]["sha256"] = "0" * 64
            evidence.write_text(json.dumps(payload), encoding="utf-8")
            result = self.run_builder(root, evidence, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source image hash mismatch", result.stderr)

    def test_rejects_nonfailed_visual_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            evidence, prompt = self.make_fixture(root, result="pass_with_notes")
            result = self.run_builder(root, evidence, prompt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("require a failed visual-QA sample", result.stderr)


if __name__ == "__main__":
    unittest.main()
