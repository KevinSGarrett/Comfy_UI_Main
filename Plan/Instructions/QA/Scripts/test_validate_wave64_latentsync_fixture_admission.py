from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_latentsync_fixture_admission.py"
ADMISSION = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_fixture_admission.json"
SPEC = importlib.util.spec_from_file_location("validate_latentsync_fixture_admission", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def load_admission() -> dict:
    return json.loads(ADMISSION.read_text(encoding="utf-8"))


def test_real_fixture_admission_and_exact_local_files_are_valid() -> None:
    assert MODULE.validate(load_admission()) == []


def test_product_authority_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["authority"]["product_approval"] = True
    assert "fixture admission exceeds storage-only authority" in MODULE.validate(
        admission, verify_local_files=False
    )


def test_golden_identity_authority_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["video"]["visual_review"]["golden_identity_authority"] = True
    assert "fixture cannot grant golden identity authority" in MODULE.validate(
        admission, verify_local_files=False
    )


def test_rights_drift_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["audio"]["voice_rights"] = "unknown"
    assert "audio voice rights mismatch" in MODULE.validate(admission, verify_local_files=False)


def test_fixture_hash_drift_fails_closed() -> None:
    admission = copy.deepcopy(load_admission())
    admission["video"]["sha256"] = "0" * 64
    assert "video fixture sha256 mismatch" in MODULE.validate(admission)
