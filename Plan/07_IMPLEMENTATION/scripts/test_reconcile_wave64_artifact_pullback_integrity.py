from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reconcile_wave64_artifact_pullback_integrity import (
    ITEM_CSVS,
    TRACKER_CSVS,
    upsert_leading_section,
)


class ArtifactPullbackLedgerRegressionTests(unittest.TestCase):
    def test_both_tracker_ledgers_are_authoritative_outputs(self) -> None:
        relative = {path.as_posix().split("/Plan/", 1)[-1] for path in TRACKER_CSVS}
        self.assertEqual(
            relative,
            {
                "Tracker/wave64_end_to_end_strict_ai_tracker.csv",
                "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv",
            },
        )

    def test_both_item_ledgers_are_authoritative_outputs(self) -> None:
        relative = {path.as_posix().split("/Plan/", 1)[-1] for path in ITEM_CSVS}
        self.assertEqual(
            relative,
            {
                "Items/wave64_end_to_end_strict_ai_itemized_list.csv",
                "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv",
            },
        )

    def test_hydration_section_is_replaced_instead_of_stacked(self) -> None:
        heading = "Wave64 Row043 Artifact Pullback Reconciliation - "
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "NEXT_ACTION.md"
            path.write_text(
                "## Wave64 Row043 Artifact Pullback Reconciliation - old\n\nOld body.\n\n"
                "## Other Section\n\nKeep me.\n",
                encoding="utf-8",
            )
            replacement = "## Wave64 Row043 Artifact Pullback Reconciliation - new\n\nNew body."
            upsert_leading_section(path, heading, replacement)
            rendered = path.read_text(encoding="utf-8")
            self.assertEqual(rendered.count("## Wave64 Row043 Artifact Pullback Reconciliation - "), 1)
            self.assertIn("New body.", rendered)
            self.assertNotIn("Old body.", rendered)
            self.assertIn("## Other Section", rendered)


if __name__ == "__main__":
    unittest.main()
