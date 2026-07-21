#!/usr/bin/env python3
"""Offline unit tests for wave64_climb_strict_visual_gate presets / fail-closed."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "Plan" / "07_IMPLEMENTATION" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from wave64_climb_strict_visual_gate import (  # noqa: E402
    CLIMB_PRESETS,
    ClimbStrictVisualGateError,
    require_strict_pod_llm_pass,
    resolve_climb_preset,
)


class ClimbStrictVisualGateTests(unittest.TestCase):
    def test_presets_cover_producer_paths(self) -> None:
        self.assertIn("row010_pulid_identity", CLIMB_PRESETS)
        self.assertIn("wan_ti2v_class_e", CLIMB_PRESETS)
        self.assertIn("wan_ti2v_class_a", CLIMB_PRESETS)
        self.assertIn("global_review_product", CLIMB_PRESETS)
        self.assertIn("smoke", CLIMB_PRESETS)
        self.assertEqual(
            resolve_climb_preset("row010_pulid_identity")["lane"], "IDENTITY_GATE"
        )
        self.assertEqual(resolve_climb_preset("wan_ti2v_class_e")["lane"], "PROOF_LANDED")
        self.assertEqual(resolve_climb_preset("wan_ti2v_class_a")["lane"], "CLASS_A")
        self.assertEqual(resolve_climb_preset("global_review_product")["lane"], "PRODUCT")
        self.assertEqual(resolve_climb_preset("smoke")["lane"], "SMOKE")

    def test_require_pass_rejects_smoke_and_reject(self) -> None:
        with self.assertRaises(ClimbStrictVisualGateError):
            require_strict_pod_llm_pass(
                {"strict_pod_llm_review": "PASS", "lane": "SMOKE"},
                climb_kind="smoke",
            )
        with self.assertRaises(ClimbStrictVisualGateError):
            require_strict_pod_llm_pass(
                {"strict_pod_llm_review": "REJECT", "lane": "PRODUCT"},
                climb_kind="global_review_product",
            )

    def test_require_pass_accepts_product_pass(self) -> None:
        payload = {"strict_pod_llm_review": "PASS", "lane": "IDENTITY_GATE"}
        out = require_strict_pod_llm_pass(payload, climb_kind="row010_pulid_identity")
        self.assertEqual(out["strict_pod_llm_review"], "PASS")

    def test_require_pass_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            path.write_text(
                json.dumps(
                    {
                        "strict_pod_llm_review": "PASS",
                        "lane": "PROOF_LANDED",
                    }
                ),
                encoding="utf-8",
            )
            out = require_strict_pod_llm_pass(path, climb_kind="wan_ti2v_class_e")
            self.assertEqual(out["lane"], "PROOF_LANDED")


if __name__ == "__main__":
    raise SystemExit(unittest.main(verbosity=2))
