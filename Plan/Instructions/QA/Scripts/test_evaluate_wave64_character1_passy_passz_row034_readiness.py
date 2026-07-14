#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_character1_passy_passz_row034_readiness.py"
SPEC = importlib.util.spec_from_file_location("row034_readiness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sha256(path: Path) -> str:
    return MODULE.bind_file(path, path.parent)["sha256"]


class Row034Character1ReadinessTests(unittest.TestCase):
    def build(self, root: Path) -> dict[str, Path]:
        ztest = root / "ztest"
        paths = {
            "pass_y": ztest / MODULE.PASS_Y,
            "pass_z": ztest / MODULE.PASS_Z,
            "pass_z_source": ztest / MODULE.PASS_Z_SOURCE,
            "pass_y_workflow": ztest / MODULE.PASS_Y_WORKFLOW,
            "pass_z_workflow": ztest / MODULE.PASS_Z_WORKFLOW,
        }
        for key in ("pass_y", "pass_z", "pass_z_source"):
            paths[key].parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (4, 3), (10, 20, 30)).save(paths["pass_y"])
        paths["pass_z_source"].write_bytes(paths["pass_y"].read_bytes())
        candidate = Image.new("RGB", (4, 3), (10, 20, 30))
        candidate.putpixel((1, 1), (50, 60, 70))
        candidate.save(paths["pass_z"])
        write_json(paths["pass_y_workflow"], {"workflow": "y"})
        write_json(paths["pass_z_workflow"], {"workflow": "z"})

        records = []
        for key, path in paths.items():
            records.append(
                {
                    "relative_path": str(path.relative_to(ztest)).replace("/", "\\"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path).upper(),
                }
            )
        for manifest, selected in (
            (ztest / MODULE.FILE_MANIFEST, records),
            (ztest / MODULE.IMAGE_INVENTORY, [records[0], records[1]]),
        ):
            manifest.parent.mkdir(parents=True, exist_ok=True)
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["relative_path", "bytes", "sha256"])
                writer.writeheader()
                writer.writerows(selected)

        integration = root / MODULE.INTEGRATION_EVIDENCE
        write_json(
            integration,
            {
                "retained_images": {
                    "pass_y": {"path": MODULE.PASS_Y.as_posix(), "sha256": sha256(paths["pass_y"]), "bytes": paths["pass_y"].stat().st_size},
                    "pass_z": {"path": MODULE.PASS_Z.as_posix(), "sha256": sha256(paths["pass_z"]), "bytes": paths["pass_z"].stat().st_size},
                    "pass_z_source": {"path": MODULE.PASS_Z_SOURCE.as_posix(), "sha256": sha256(paths["pass_z_source"]), "matches_pass_y_exactly": True},
                },
                "calibration_acceptance": {"target_met": False, "mask_promotion_allowed": False},
            },
        )
        rules = root / MODULE.RULES_PATH
        write_json(
            rules,
            {"authority_rules": {"production_authority_exact_objects": [], "fixture_authority_exact_objects": []}},
        )
        return {**paths, "root": root, "ztest": ztest, "integration": integration, "rules": rules}

    def evidence(self, paths: dict[str, Path]) -> dict[str, object]:
        return MODULE.build_evidence(
            paths["root"], paths["ztest"], paths["integration"], paths["rules"], "2026-07-14T12:00:00-05:00"
        )

    def test_verifies_primary_media_and_keeps_row034_blocked(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            evidence = self.evidence(self.build(Path(temporary)))
        self.assertEqual(evidence["result"], "blocked_passy_passz_primary_media_verified_row034_request_not_formable")
        self.assertTrue(evidence["verification"]["pass_z_source_matches_pass_y_bytes"])
        self.assertTrue(evidence["verification"]["pass_y_pass_z_delta"]["material_change_observed"])
        self.assertEqual(len(evidence["row034_contract_gap"]["missing_non_primary_bindings"]), 12)
        self.assertFalse(evidence["claim_boundary"]["target_region_correctness_proven"])

    def test_image_delta_reports_exact_changed_fraction_and_mae(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            delta = MODULE.image_delta(paths["pass_y"], paths["pass_z"])
        self.assertEqual(delta["changed_pixel_count"], 1)
        self.assertAlmostEqual(delta["changed_pixel_fraction"], 1 / 12)
        self.assertAlmostEqual(delta["rgb_mean_absolute_error_0_255"], 120 / 36)

    def test_rejects_manifest_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            manifest = paths["ztest"] / MODULE.FILE_MANIFEST
            text = manifest.read_text(encoding="utf-8").replace(sha256(paths["pass_y"]).upper(), "0" * 64, 1)
            manifest.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.evidence(paths)

    def test_rejects_nonidentical_pass_z_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            paths["pass_z_source"].write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "byte mismatch|does not exactly equal"):
                self.evidence(paths)

    def test_rejects_promotable_integration_claim(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            integration = json.loads(paths["integration"].read_text())
            integration["calibration_acceptance"]["mask_promotion_allowed"] = True
            write_json(paths["integration"], integration)
            with self.assertRaisesRegex(ValueError, "mask_promotion_allowed=false"):
                self.evidence(paths)

    def test_cli_writes_byte_identical_primary_and_tracker_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary))
            output = paths["root"] / "primary.json"
            tracker = paths["root"] / "tracker.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project-root", str(paths["root"]),
                    "--ztest-root", str(paths["ztest"]),
                    "--integration-evidence", str(paths["integration"]),
                    "--rules", str(paths["rules"]),
                    "--timestamp", "2026-07-14T12:00:00-05:00",
                    "--output", str(output),
                    "--tracker-output", str(tracker),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(output.read_bytes(), tracker.read_bytes())


if __name__ == "__main__":
    unittest.main()
