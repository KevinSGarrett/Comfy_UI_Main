from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "07_IMPLEMENTATION/scripts/apply_wave64_kokoro_audition_tracking.py"
SPEC = importlib.util.spec_from_file_location("wave64_kokoro_tracking", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_append_unique_is_idempotent() -> None:
    first = MODULE.append_unique("a", "b", "; ")
    second = MODULE.append_unique(first, "b", "; ")
    assert first == "a; b"
    assert second == first


def test_stale_candidate_and_taxonomy_blockers_are_reconciled() -> None:
    blockers = [
        {"classification": "Blocked_Production_Eligible_Voice_Candidate_Missing"},
        {"classification": "Blocked_Voice_Emotion_Taxonomy_Authority_Missing"},
    ]
    updated = MODULE.blockers_for_row("027", blockers)
    classes = {row["classification"] for row in updated}
    assert "Blocked_Production_Eligible_Voice_Candidate_Missing" not in classes
    assert "Blocked_Voice_Emotion_Taxonomy_Authority_Missing" not in classes
    assert "Blocked_Human_Audio_Playback_Review_Missing" in classes
    assert "Blocked_Audio_Production_Review_Authority_Missing" in classes


def test_voice_profile_update_selects_synthetic_baseline_without_authority(tmp_path: Path) -> None:
    source = MODULE.ROOT / "Plan/10_REGISTRIES/wave30_voice_profile_registry.json"
    target = tmp_path / "registry.json"
    target.write_bytes(source.read_bytes())
    result = MODULE.update_voice_profile(target, True)
    payload = json.loads(target.read_text(encoding="utf-8"))
    profile = next(row for row in payload["character_profiles"] if row["character_id"] == "C01")
    assert result["identity_policy"] == "designed_synthetic_voice"
    assert profile["reference_ids"] == []
    assert profile["production_authorized"] is False
    assert profile["engine_configuration"]["voice_sha256"] == "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff"


def test_evidence_requires_human_review_to_remain_false() -> None:
    result = MODULE.verify_evidence()
    assert result["sha256"] == MODULE.EVIDENCE_SHA256
    assert result["status"] == "PASS_AUTOMATED_CANDIDATE_ELIGIBLE_HUMAN_PLAYBACK_REQUIRED"
