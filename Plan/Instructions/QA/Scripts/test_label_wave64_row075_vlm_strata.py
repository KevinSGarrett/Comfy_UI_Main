#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/label_wave64_row075_vlm_strata.py"


def _load():
    spec = importlib.util.spec_from_file_location("label_wave64_row075_vlm_strata", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


class Row075VlmStrataTests(unittest.TestCase):
    def test_metadata_proxy_labels_pending_and_blocked(self) -> None:
        pending = {
            "truth_label_status": "pending",
            "severe_defect_codes": ["dropouts", "clicks"],
        }
        blocked = {
            "truth_label_status": "blocked",
            "severe_defect_codes": [],
            "blocker_code": "DEFECT_EXTRACTION_FAILED",
        }
        p = MOD.metadata_proxy_label(pending)
        b = MOD.metadata_proxy_label(blocked)
        self.assertEqual(p["vlm_label_status"], "labeled")
        self.assertEqual(p["vlm_severe_defect_codes"], ["dropouts", "clicks"])
        self.assertEqual(b["vlm_label_status"], "blocked")
        self.assertEqual(b["source"], "metadata_proxy")

    def test_apply_labels_refuse_complete_and_unfreeze(self) -> None:
        strata_path = ROOT / MOD.STRATA_PACKET
        strata = json.loads(strata_path.read_text(encoding="utf-8"))
        packet = MOD.apply_labels(
            strata,
            base_url="http://127.0.0.1:9",
            model="qwen2.5:7b-instruct",
            allow_metadata_proxy=True,
        )
        self.assertFalse(packet["product_completion_claimed"])
        self.assertFalse(packet["threshold_authority_unfrozen"])
        self.assertFalse(packet["library_pcm_decode_invoked"])
        self.assertTrue(packet["row074_pcm_left_alone"])
        self.assertEqual(packet["autonomous_authority"], "VLM_METADATA")
        self.assertEqual(packet["counts"]["shortlist_unlabeled_input"], 8)
        self.assertEqual(len(packet["labels"]), 8)
        self.assertIn(
            "REGISTERED_THRESHOLD_AUTHORITY_FROZEN_SYNTHETIC_ONLY",
            packet["blocker_codes_retained"],
        )
        self.assertTrue(all(row.get("human_gold") is False for row in packet["labels"]))


if __name__ == "__main__":
    unittest.main()
