#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_autonomous_hyperreal_speech_control_package.py"
SPEC = importlib.util.spec_from_file_location("speech_package", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SpeechControlPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        MODULE.main(ROOT)

    def test_exact_collision_free_row_range(self) -> None:
        with (ROOT / MODULE.TRACKER).open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["Tracker_ID"] for row in rows], [f"TRK-W64-{n:03d}" for n in range(113, 149)])
        self.assertEqual(len({row["Tracker_ID"] for row in rows}), 36)
        with (ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            canonical_ids = {row["Tracker_ID"] for row in csv.DictReader(handle)}
        self.assertFalse(canonical_ids.intersection(row["Tracker_ID"] for row in rows))

    def test_item_tracker_parity_and_canonical_headers(self) -> None:
        with (ROOT / MODULE.ITEMS).open("r", encoding="utf-8-sig", newline="") as handle:
            item_reader = csv.DictReader(handle); items = list(item_reader); item_fields = item_reader.fieldnames
        with (ROOT / MODULE.TRACKER).open("r", encoding="utf-8-sig", newline="") as handle:
            tracker_reader = csv.DictReader(handle); trackers = list(tracker_reader); tracker_fields = tracker_reader.fieldnames
        self.assertEqual(item_fields, MODULE.read_header(ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"))
        self.assertEqual(tracker_fields, MODULE.read_header(ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"))
        self.assertEqual([row["Item_ID"] for row in items], [row["Source_Item_ID"] for row in trackers])
        self.assertTrue(all(row["Status"] == MODULE.STATUS for row in items + trackers))

    def test_requirements_and_mirror_are_exact(self) -> None:
        source = (ROOT / MODULE.REQ).read_bytes(); mirror = (ROOT / MODULE.REQ_MIRROR).read_bytes()
        self.assertEqual(source, mirror)
        payload = json.loads(source)
        self.assertEqual(payload["row_range"], {"first": 113, "last": 148, "count": 36})
        self.assertFalse(payload["content_based_suppression"])
        self.assertEqual(len(payload["requirements"]), 36)
        row117 = next(row for row in payload["requirements"] if row["tracker_id"] == "TRK-W64-117")
        self.assertEqual(row117["asset_catalog"], MODULE.ASSET_CATALOG.as_posix())
        self.assertGreaterEqual(len(row117["required_asset_ids"]), 44)

    def test_schemas_are_draft_2020_and_meta_valid(self) -> None:
        try:
            import jsonschema
        except ImportError:
            jsonschema = None
        self.assertEqual(len(MODULE.SCHEMAS), 6)
        for name in MODULE.SCHEMAS:
            schema = json.loads((ROOT / "Plan/08_SCHEMAS" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            if jsonschema:
                jsonschema.Draft202012Validator.check_schema(schema)

    def test_registry_preserves_truth_and_visibility_boundaries(self) -> None:
        registry = json.loads((ROOT / MODULE.REGISTRY).read_text(encoding="utf-8"))
        self.assertEqual(len(registry["work_packages"]), 36)
        self.assertFalse(registry["boundaries"]["content_based_suppression"])
        self.assertFalse(registry["boundaries"]["planning_is_runtime"])
        self.assertFalse(registry["boundaries"]["download_is_ready"])
        self.assertFalse(registry["boundaries"]["human_review_may_be_fabricated"])
        self.assertEqual(registry["provider_resolved_asset_catalog"], MODULE.ASSET_CATALOG.as_posix())
        self.assertGreaterEqual(registry["provider_catalog_summary"]["official_asset_groups"], 31)
        self.assertGreaterEqual(registry["provider_catalog_summary"]["civitai_integration_candidates"], 13)

    def test_evidence_mirror_and_no_runtime_claim(self) -> None:
        source = (ROOT / MODULE.EVIDENCE).read_bytes(); mirror = (ROOT / MODULE.EVIDENCE_MIRROR).read_bytes()
        self.assertEqual(source, mirror)
        evidence = json.loads(source)
        self.assertEqual(evidence["result"], "pass_additive_planning_and_execution_control_package_only")
        self.assertFalse(evidence["boundaries"]["runtime_implementation_complete"])
        self.assertFalse(evidence["boundaries"]["generation_executed"])


if __name__ == "__main__":
    unittest.main()
