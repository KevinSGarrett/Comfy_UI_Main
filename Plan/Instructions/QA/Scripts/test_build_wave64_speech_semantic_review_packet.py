from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "build_wave64_speech_semantic_review_packet.py"
SPEC = importlib.util.spec_from_file_location("semantic_packet", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SemanticReviewPacketTests(unittest.TestCase):
    def test_packet_writer_has_no_physical_newlines_and_round_trips_content(self) -> None:
        value = {"artifact_type": "test", "files": [{"path": "a.py", "content": "one\ntwo\r\n"}]}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "packet.json"
            MODULE.write_packet(output, value)
            payload = output.read_bytes()
            self.assertNotIn(b"\n", payload)
            self.assertNotIn(b"\r", payload)
            self.assertEqual(value, json.loads(payload))

    def test_default_scope_is_bounded(self) -> None:
        self.assertEqual(12, len(MODULE.DEFAULT_PATHS))
        self.assertEqual(12, len(set(MODULE.DEFAULT_PATHS)))


if __name__ == "__main__":
    unittest.main()
