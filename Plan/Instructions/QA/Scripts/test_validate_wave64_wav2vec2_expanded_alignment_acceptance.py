from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_wav2vec2_expanded_alignment_acceptance.py"
EVIDENCE = ROOT / "Plan/Tracker/Evidence/W64_AQA_WAV2VEC2_EXPANDED_ALIGNMENT_20260722T202608Z"
SPEC = importlib.util.spec_from_file_location("wav2vec2_acceptance", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_canonical_packet_passes() -> None:
    MODULE.validate(EVIDENCE, EVIDENCE / "integration_acceptance.json")


def test_secret_lease_token_is_rejected() -> None:
    with pytest.raises(MODULE.AcceptanceError, match="lease token"):
        MODULE.reject_secret_keys({"nested": {"lease_token": "forbidden"}})


def test_failed_case_is_rejected() -> None:
    receipt = json.loads((EVIDENCE / "held_out_receipt.json").read_text(encoding="utf-8"))
    receipt = copy.deepcopy(receipt)
    receipt["results"][0]["passed"] = False
    with pytest.raises(MODULE.AcceptanceError, match="contains a failed case"):
        MODULE.validate_partition(receipt, "held_out", receipt["lease"]["lease_id"], 1024)


def test_cleanup_escape_is_rejected() -> None:
    receipt = json.loads((EVIDENCE / "calibration_receipt.json").read_text(encoding="utf-8"))
    receipt = copy.deepcopy(receipt)
    receipt["runtime"]["process_exit_cleanup_delta_mib"] = 1025
    with pytest.raises(MODULE.AcceptanceError, match="process-exit cleanup failed"):
        MODULE.validate_partition(receipt, "calibration", receipt["lease"]["lease_id"], 1024)
