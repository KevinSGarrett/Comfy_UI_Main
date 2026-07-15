from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/validate_wave64_row023_wan_rerun_readiness.py"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("row023_wan_readiness", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def write_png(path: Path, value: int, width: int = 2, height: int = 2) -> None:
    pixel = bytes((value, value, value))
    rows = b"".join(b"\x00" + pixel * width for _ in range(height))
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(rows))
    payload += chunk(b"IEND", b"")
    path.write_bytes(payload)


def profile(source: dict, prior: set[int] | None = None) -> dict:
    del prior
    return {
        "profile_id": "test-profile",
        "target_lane_id": MODULE.LANE_ID,
        "source_binding": {
            "project_path": source["source"]["path"],
            "staged_filename": MODULE.STAGED_FILENAME,
            "sha256": source["source"]["sha256"],
            "size_bytes": source["source"]["bytes"],
            "source_width": MODULE.SOURCE_WIDTH,
            "source_height": MODULE.SOURCE_HEIGHT,
            "selected_frame_index": source["selected_frame_index"],
        },
        "request_patch_values": {
            "positive_prompt": "exact face identity white collared blouse black studio background locked camera head-and-shoulders",
            "negative_prompt": "identity drift scene change background change terminal frame corruption",
            "seed": MODULE.SEED,
            "sampler_settings": {"steps": 20, "cfg": 5, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1},
            "video_latent": {"width": 480, "height": 640, "length": 49, "batch_size": 1},
            "source_image": MODULE.STAGED_FILENAME,
            "output_video": {"filename_prefix": MODULE.OUTPUT_PREFIX, "format": "mp4", "codec": "h264"},
        },
        "runtime_boundaries": {
            "local_readiness_only": True,
            "targeted_rerun_shot": True,
            "material_route_change_from_failed_animatediff": True,
            "authorized_generation_count": 1,
            "retry_allowed": False,
            "ec2_start_allowed": False,
            "generation_allowed": False,
            "gold_masks_consumed": False,
            "body_mask_or_geometry_authority_claimed": False,
            "mask_promotion_allowed": False,
            "content_based_suppression": False,
            "adult_or_nsfw_asset_visibility_restricted": False,
            "requires_direct_before_after_temporal_review_after_execution": True,
            "production_video_lane_certification_claimed": False,
            "wave71_activation_claimed": False,
            "jira_mutated": False,
        },
    }


class Row023WanReadinessTests(unittest.TestCase):
    def test_png_decoder_and_medoid_select_frame_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = [0, 10, 20, 30, 100]
            frames = []
            for index, value in enumerate(values):
                path = root / f"frame_{index}.png"
                write_png(path, value)
                frames.append((index, path))
            selected, scores = MODULE.select_medoid(frames)
            self.assertEqual(selected, 2)
            self.assertLess(scores[2], scores[1])
            self.assertLess(scores[2], scores[3])

    def test_png_crc_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.png"
            write_png(path, 20)
            data = bytearray(path.read_bytes())
            data[-5] ^= 1
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "CRC mismatch"):
                MODULE.decode_png_rgb(path)

    def test_profile_accepts_exact_one_candidate_contract(self):
        source = {"selected_frame_index": 2, "source": {"path": MODULE.SOURCE_REL, "sha256": MODULE.SOURCE_SHA256, "bytes": MODULE.SOURCE_BYTES}}
        result = MODULE.validate_profile(profile(source), source, {2271301, 2271302, 2271303, 2271401})
        self.assertEqual(result["seed"], MODULE.SEED)
        self.assertEqual(result["completed_seed_count"], 4)

    def test_profile_rejects_completed_seed(self):
        source = {"selected_frame_index": 2, "source": {"path": MODULE.SOURCE_REL, "sha256": MODULE.SOURCE_SHA256, "bytes": MODULE.SOURCE_BYTES}}
        with self.assertRaisesRegex(ValueError, "already completed"):
            MODULE.validate_profile(profile(source), source, {MODULE.SEED})

    def test_profile_rejects_retry_permission(self):
        source = {"selected_frame_index": 2, "source": {"path": MODULE.SOURCE_REL, "sha256": MODULE.SOURCE_SHA256, "bytes": MODULE.SOURCE_BYTES}}
        candidate = profile(source)
        candidate["runtime_boundaries"]["retry_allowed"] = True
        with self.assertRaisesRegex(ValueError, "fail-closed boundary"):
            MODULE.validate_profile(candidate, source, {2271301})

    def test_profile_rejects_content_suppression(self):
        source = {"selected_frame_index": 2, "source": {"path": MODULE.SOURCE_REL, "sha256": MODULE.SOURCE_SHA256, "bytes": MODULE.SOURCE_BYTES}}
        candidate = profile(source)
        candidate["runtime_boundaries"]["content_based_suppression"] = True
        with self.assertRaisesRegex(ValueError, "fail-closed boundary"):
            MODULE.validate_profile(candidate, source, {2271301})

    def test_profile_rejects_source_hash_drift(self):
        source = {"selected_frame_index": 2, "source": {"path": MODULE.SOURCE_REL, "sha256": MODULE.SOURCE_SHA256, "bytes": MODULE.SOURCE_BYTES}}
        candidate = profile(source)
        candidate["source_binding"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source hash"):
            MODULE.validate_profile(candidate, source, {2271301})

    def test_atomic_writer_produces_identical_mirrors(self):
        with tempfile.TemporaryDirectory() as temporary:
            left = Path(temporary) / "left.json"
            right = Path(temporary) / "right.json"
            payload = {"status": "ready", "retry_allowed": False}
            MODULE.write_atomic(left, payload)
            MODULE.write_atomic(right, payload)
            self.assertEqual(left.read_bytes(), right.read_bytes())
            self.assertEqual(json.loads(left.read_text()), payload)

    def test_main_validates_hash_bound_run_package_end_to_end(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packet_source = PROJECT_ROOT / Path(MODULE.MANIFEST_REL).parent
            packet_target = root / Path(MODULE.MANIFEST_REL).parent
            shutil.copytree(packet_source, packet_target)
            for relative in (
                MODULE.VISUAL_REL,
                MODULE.ROUTING_REL,
                MODULE.ROBUSTNESS_REL,
                MODULE.DIVERSITY_REL,
                MODULE.WORKFLOW_REL,
                MODULE.PROFILE_REL,
            ):
                source = PROJECT_ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

            package_dir = root / "runtime_artifacts/run_packages/test-row023"
            packaged_source = package_dir / "inputs" / MODULE.STAGED_FILENAME
            packaged_source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / MODULE.SOURCE_REL, packaged_source)
            profile_payload = json.loads((root / MODULE.PROFILE_REL).read_text(encoding="utf-8"))
            patches = profile_payload["request_patch_values"]
            prompt_request = {
                "prompt": {
                    "4": {"inputs": {"text": patches["positive_prompt"]}},
                    "5": {"inputs": {"text": patches["negative_prompt"]}},
                    "7": {"inputs": {"image": MODULE.STAGED_FILENAME}},
                    "9": {"inputs": {"seed": MODULE.SEED}},
                    "12": {"inputs": {"filename_prefix": MODULE.OUTPUT_PREFIX}},
                }
            }
            request_path = package_dir / "prompt_request.json"
            request_path.parent.mkdir(parents=True, exist_ok=True)
            request_path.write_text(json.dumps(prompt_request), encoding="utf-8", newline="\n")
            request_hash = MODULE.sha256_file(request_path)
            manifest_path = package_dir / "RUN_PACKAGE_MANIFEST.json"
            manifest_payload = {
                "run_id": "test-row023",
                "lane_id": MODULE.LANE_ID,
                "result": "pass_local_only",
                "local_only": True,
                "aws_contacted": False,
                "comfyui_contacted": False,
                "ec2_started": False,
                "generation_executed": False,
                "prompt_profile": {
                    "supplied": True,
                    "applied": True,
                    "profile_id": profile_payload["profile_id"],
                    "source_binding": {
                        "valid": True,
                        "staged_filename": MODULE.STAGED_FILENAME,
                        "sha256": MODULE.SOURCE_SHA256,
                        "size_bytes": MODULE.SOURCE_BYTES,
                        "packaged": packaged_source.relative_to(root).as_posix(),
                    },
                },
                "prompt_request": {"sha256": request_hash},
                "generated_files": [
                    {
                        "purpose": "Patched ComfyUI /prompt request body for later runtime execution.",
                        "path": request_path.relative_to(root).as_posix(),
                        "sha256": request_hash,
                    }
                ],
                "runtime_boundaries": {
                    "ec2_start_allowed_by_package": False,
                    "generation_allowed_by_package": False,
                },
            }
            manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8", newline="\n")
            qa_path = root / "qa.json"
            tracker_path = root / "tracker.json"
            arguments = [
                str(SCRIPT),
                "--project-root",
                str(root),
                "--profile",
                MODULE.PROFILE_REL,
                "--run-package-manifest",
                manifest_path.relative_to(root).as_posix(),
                "--timestamp",
                "20260715T000000-0500",
                "--output",
                str(qa_path),
                "--tracker-output",
                str(tracker_path),
            ]
            with mock.patch.object(sys, "argv", arguments):
                self.assertEqual(MODULE.main(), 0)
            self.assertEqual(qa_path.read_bytes(), tracker_path.read_bytes())
            evidence = json.loads(qa_path.read_text(encoding="utf-8"))
            self.assertEqual(evidence["classification"], "ROW023_WAN_RERUN_RUN_PACKAGE_LOCAL_READINESS_PASS")
            self.assertFalse(evidence["runtime_gate"]["generation_authorized_by_this_evidence"])
            self.assertFalse(evidence["runtime_gate"]["retry_allowed"])


if __name__ == "__main__":
    unittest.main()
