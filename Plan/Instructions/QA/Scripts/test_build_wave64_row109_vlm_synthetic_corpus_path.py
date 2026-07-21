#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_row109_vlm_synthetic_corpus_path.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_wave64_row109_vlm_synthetic_corpus_path", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


class Row109VlmSyntheticPathTests(unittest.TestCase):
    def test_metadata_proxy_receipt_marks_vlm_synthetic(self) -> None:
        case = {
            "case_id": "cal_footstep_00",
            "partition": "calibration",
            "event_family": "footstep",
            "material": "hardwood",
            "footwear": "bare_foot",
            "truth_class": "reference_truth",
            "annotation": {
                "silent_event": False,
                "labels": {"event_family": "footstep"},
            },
        }
        receipt = MOD.metadata_proxy_receipt(case)
        self.assertEqual(receipt["annotator_role"], "vlm_synthetic")
        self.assertEqual(receipt["autonomous_authority"], "VLM_SYNTHETIC")
        self.assertFalse(receipt["human_gold"])
        self.assertFalse(receipt["rights_bound_for_production"])
        self.assertTrue(receipt["agreement_with_synthetic_fixture"])

    def test_build_packet_fail_closed_on_production(self) -> None:
        tmp_reviews = (
            ROOT
            / "runtime_artifacts"
            / "_pytest_row109_vlm_synthetic"
            / "reviews"
        )
        original = MOD.REVIEWS_DIR
        try:
            if tmp_reviews.exists():
                for path in tmp_reviews.rglob("*"):
                    if path.is_file():
                        path.unlink()
            MOD.REVIEWS_DIR = tmp_reviews.relative_to(ROOT)
            packet = MOD.build_packet(
                root=ROOT,
                base_url="http://127.0.0.1:9",
                model="qwen2.5:7b-instruct",
                allow_metadata_proxy=True,
                live_limit=0,
            )
        finally:
            MOD.REVIEWS_DIR = original
            if tmp_reviews.exists():
                for path in sorted(tmp_reviews.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        path.rmdir()
                parent = tmp_reviews.parent
                if parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
        self.assertEqual(packet["autonomous_authority"], "VLM_SYNTHETIC")
        self.assertFalse(packet["product_completion_claimed"])
        self.assertFalse(packet["production_benchmark_authority"])
        self.assertTrue(packet["row074_pcm_left_alone"])
        self.assertGreaterEqual(packet["counts"]["cases_annotated"], 30)
        self.assertIn("GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT", packet["blocker_codes_retained"])
        self.assertTrue(packet["policy_gates"]["rights_required_for_production_still"])
        self.assertTrue(packet["decision"]["step2_still_blocked"])


if __name__ == "__main__":
    unittest.main()
