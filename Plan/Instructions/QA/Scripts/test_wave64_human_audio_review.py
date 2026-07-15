import argparse
import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
import wave
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


PREPARE = _load("prepare_human_audio_review", ROOT / "Plan/07_IMPLEMENTATION/scripts/prepare_wave64_human_audio_review.py")
VALIDATE = _load("validate_human_audio_review", ROOT / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_human_audio_review.py")
STRICT = _load("strict_audio_review", ROOT / "Plan/07_IMPLEMENTATION/scripts/evaluate_wave64_strict_audio_artifact_review.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(struct.pack("<h", 0) * 16000)


class Wave64HumanAudioReviewTests(unittest.TestCase):
    def _case(self, base: Path):
        artifact = base / "candidate.wav"
        evidence = base / "automated.json"
        request_path = base / "request.json"
        record_path = base / "record.json"
        _write_wav(artifact)
        evidence.write_text('{"status":"PASS"}\n', encoding="utf-8")
        args = argparse.Namespace(
            artifact=str(artifact),
            media_type="audio",
            review_id="review_001",
            expected_transcript="Hold the line and wait for my signal.",
            character_id="C01",
            voice_profile_id="voice_C01_pending_authority",
            emotion_class=None,
            delivery_style="focused",
            intensity="controlled",
            pace_wpm=150.0,
            duration_target_seconds=3.0,
            sync_required=False,
            automated_evidence=[str(evidence)],
        )
        request = PREPARE.build_request(args)
        request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        sections = []
        for name in request["required_sections"]:
            not_applicable = name in {"loud", "quiet", "transitions"}
            sections.append({
                "name": name,
                "status": "not_applicable" if not_applicable else "reviewed",
                "not_applicable_reason": "short clip has no distinct passage" if not_applicable else None,
            })
        categories = []
        for name in request["required_categories"]:
            not_applicable = name in {"mix_balance", "av_sync"}
            categories.append({
                "name": name,
                "status": "not_applicable" if not_applicable else "scored",
                "score": None if not_applicable else 4.5,
                "not_applicable_reason": "single dry audio clip" if not_applicable else None,
                "notes": "fixture review",
            })
        record = {
            "schema_name": "wave64_human_audio_review_record",
            "record_version": 1,
            "review_id": request["review_id"],
            "request_sha256": _sha256(request_path),
            "authority_type": "human",
            "reviewer_identity": {
                "reviewer_id": "project_owner_audio_reviewer_v1",
                "authority_id": "wave64_project_owner_playback_authority_v1",
                "role": "playback_reviewer",
            },
            "independence_attestation": {"not_generator": True, "no_conflict": True, "reviewed_exact_hash": True},
            "playback_conditions": {
                "device_class": "headphones",
                "environment": "quiet room",
                "full_playback_count": 2,
                "reasonable_listening_level": True,
            },
            "section_results": sections,
            "category_results": categories,
            "observed_transcript": request["expected"]["transcript"],
            "defects": [],
            "decision": "PASS",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return artifact, request_path, record_path

    def test_valid_human_review_emits_strict_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact, request_path, record_path = self._case(Path(temporary))
            proof = VALIDATE.validate_review(request_path, record_path)
            self.assertEqual(proof["authority_type"], "human")
            self.assertEqual(proof["audio_sha256"], _sha256(artifact))
            blockers = []
            registry = json.loads((ROOT / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json").read_text(encoding="utf-8"))
            status, identity, blocking = STRICT._evaluate_human_playback_review(
                proof,
                registry,
                mix_wav_sha256=_sha256(artifact),
                request_is_synthetic=False,
                blockers=blockers,
            )
            self.assertEqual(status, "PASS")
            self.assertEqual(identity["reviewer_id"], "project_owner_audio_reviewer_v1")
            self.assertFalse(blocking)
            self.assertEqual(blockers, [])

    def test_low_score_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, request_path, record_path = self._case(Path(temporary))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["category_results"][0]["score"] = 3.5
            record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PASS decision conflicts"):
                VALIDATE.validate_review(request_path, record_path)

    def test_artifact_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact, request_path, record_path = self._case(Path(temporary))
            artifact.write_bytes(artifact.read_bytes() + b"tamper")
            with self.assertRaisesRegex(ValueError, "byte mismatch"):
                VALIDATE.validate_review(request_path, record_path)

    def test_request_producer_can_honestly_disable_engine_blinding(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            artifact = base / "kokoro_candidate.wav"
            evidence = base / "kokoro_evaluation.json"
            _write_wav(artifact)
            evidence.write_text('{"status":"PASS"}\n', encoding="utf-8")
            args = argparse.Namespace(
                artifact=str(artifact),
                media_type="audio",
                review_id="review_unblinded",
                expected_transcript="Hold the line.",
                character_id="C01",
                voice_profile_id="voice_C01_pending_authority",
                emotion_class=None,
                delivery_style="focused",
                intensity="controlled",
                pace_wpm=150.0,
                duration_target_seconds=3.0,
                sync_required=False,
                automated_evidence=[str(evidence)],
                engine_identity_hidden_initial_pass=False,
            )
            request = PREPARE.build_request(args)
            self.assertFalse(request["blinding"]["engine_identity_hidden_initial_pass"])

    def test_distinct_human_final_authority_bundle_is_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            bundle_path = base / "production_bundle.json"
            bundle = {
                "schema_name": "wave64_human_production_review_bundle",
                "bundle_version": 1,
                "proof_kind": "production_review",
                "authority_type": "human",
                "reviewer_id": "final_reviewer_v1",
                "authority_id": "final_authority_v1",
                "role": "final_production_authority",
                "is_synthetic": False,
                "production_evidence": True,
                "artifact_sha256": "a" * 64,
                "prompt_alignment_proof_sha256": "b" * 64,
                "playback_proof_sha256": "c" * 64,
                "independence_attestation": {
                    "not_generator": True,
                    "not_prompt_alignment_authority": True,
                    "not_playback_reviewer": True,
                    "no_conflict": True,
                    "reviewed_exact_hashes": True,
                },
                "decision": "PASS",
                "revoked": False,
            }
            bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            bundle_sha = _sha256(bundle_path)
            registry = json.loads((ROOT / "Plan/10_REGISTRIES/wave64_strict_audio_review_authority_registry.json").read_text(encoding="utf-8"))
            registry["human_production_review_authorities"] = [
                {"reviewer_id": "final_reviewer_v1", "authority_id": "final_authority_v1", "role": "final_production_authority"}
            ]
            registry["production_review_bundle_allowlist"] = [bundle_sha]
            blockers = []
            status, identity = STRICT._evaluate_promotion(
                request_payload={
                    "is_synthetic": False,
                    "capture_mode": "technical_capture",
                    "mix_wav_binding": {"sha256": "a" * 64},
                    "prompt_alignment_proof_binding": {"sha256": "b" * 64},
                    "playback_proof_binding": {"sha256": "c" * 64},
                },
                upstream_production_eligible=True,
                gate_states={
                    "audio_metadata_check": "PASS",
                    "prompt_alignment": "PASS",
                    "playback_review": "PASS",
                    "sync_evidence": "PASS",
                },
                prompt_producer={"authority_id": "prompt_authority", "producer_id": "p", "engine": "e", "model": "m", "model_version": "1", "model_sha256": "d" * 64},
                playback_producer={"authority_type": "human", "reviewer_id": "playback", "authority_id": "playback_authority", "role": "playback_reviewer"},
                production_bundle_binding={"path": str(bundle_path), "sha256": bundle_sha, "bytes": bundle_path.stat().st_size},
                registry=registry,
                blockers=blockers,
            )
            self.assertEqual(status, "PASS")
            self.assertEqual(identity["authority_id"], "final_authority_v1")
            self.assertEqual(blockers, [])


if __name__ == "__main__":
    unittest.main()
