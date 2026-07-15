from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "apply_wave64_rows118_122_tracking.py"
SPEC = importlib.util.spec_from_file_location("speech_tracking_118_122", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class Rows118122TrackingTests(unittest.TestCase):
    def test_decision_map_requires_exact_rows(self) -> None:
        with self.assertRaisesRegex(MODULE.TrackingError, "exactly Rows118-122"):
            MODULE.decision_map({"decisions": {"TRK-W64-118": {"status": "blocked"}}})

    def test_append_note_is_idempotent(self) -> None:
        first = MODULE.append_note("existing", "evidence.json")
        self.assertEqual(first, MODULE.append_note(first, "evidence.json"))

    def test_mirror_evidence_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / MODULE.EVIDENCE
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps({"classification": "test"}) + "\n", encoding="utf-8")
            left, right = MODULE.mirror_evidence(root)
            self.assertEqual((root / left).read_bytes(), (root / right).read_bytes())


if __name__ == "__main__":
    unittest.main()
