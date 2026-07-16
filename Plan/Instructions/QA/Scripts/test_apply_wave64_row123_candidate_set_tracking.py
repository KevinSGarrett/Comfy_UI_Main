from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[3] / "07_IMPLEMENTATION" / "scripts" / "apply_wave64_row123_candidate_set_tracking.py"
SPEC = importlib.util.spec_from_file_location("row123_tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def candidate(engine: str) -> dict:
    return {
        "engine_family": engine,
        "immutable": True,
        "hash_bound": True,
        "retry_authorized": False,
    }


class Row123CandidateSetTests(unittest.TestCase):
    def test_candidate_set_requires_exact_four_engine_outcomes(self) -> None:
        values = [candidate(name) for name in ("parler_tts", "cosyvoice2", "chatterbox", "qwen3_tts")]
        MODULE.validate_candidate_set(values)
        with self.assertRaisesRegex(MODULE.TrackingError, "four engine"):
            MODULE.validate_candidate_set(values[:-1])

    def test_candidate_set_rejects_retry_authorization(self) -> None:
        values = [candidate(name) for name in ("parler_tts", "cosyvoice2", "chatterbox", "qwen3_tts")]
        values[-1]["retry_authorized"] = True
        with self.assertRaisesRegex(MODULE.TrackingError, "retry"):
            MODULE.validate_candidate_set(values)

    def test_note_update_is_idempotent(self) -> None:
        once = MODULE.append_note("existing")
        self.assertEqual(once, MODULE.append_note(once))


if __name__ == "__main__":
    unittest.main()
