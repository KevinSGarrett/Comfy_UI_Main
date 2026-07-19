#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_visual_material_recognition.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/visual_material_recognition_manifest.schema.json"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _evidence(kind: str, supports_class: str, digest_char: str) -> dict:
    return {
        "kind": kind,
        "source_id": f"{kind}_fixture",
        "observation_sha256": digest_char * 64,
        "supports_class": supports_class,
    }


def _texture(*, quality: float = 0.88) -> dict:
    return {
        "feature_digest_sha256": "1" * 64,
        "resolution_px": [256, 256],
        "crop_authority": "owner_region_mask_fixture",
        "quality_score": quality,
    }


def _decision(
    *,
    decision_id: str,
    frame_index: int,
    pts: int,
    region_id: str,
    region_kind: str = "surface",
    observed_class: str | None = "hardwood",
    broader_class: str | None = "hard_floor",
    decision_state: str = "observed_class",
    confidence: float = 0.92,
    ambiguity: str = "none",
    abstention_reason: str | None = None,
    supports_class: str = "hardwood",
    contact_context: dict | None = None,
    disagreement: bool = False,
    second_class: str | None = None,
) -> dict:
    if disagreement:
        evidence = [
            _evidence("material_classifier", supports_class, "a"),
            _evidence("texture_evidence", second_class or "carpet", "b"),
            _evidence("scene_registry", supports_class, "c"),
        ]
        fusion = {
            "independent_source_count": 3,
            "agreeing_source_count": 2,
            "disagreement": True,
            "fusion_rule": "require_independent_agreement_or_broaden_or_abstain",
        }
    else:
        evidence = [
            _evidence("material_classifier", supports_class, "a"),
            _evidence("texture_evidence", supports_class, "b"),
            _evidence("scene_registry", supports_class, "c"),
        ]
        fusion = {
            "independent_source_count": 3,
            "agreeing_source_count": 3,
            "disagreement": False,
            "fusion_rule": "require_independent_agreement_or_broaden_or_abstain",
        }
    return {
        "decision_id": decision_id,
        "frame_index": frame_index,
        "pts": pts,
        "owner_id": "character_1",
        "track_id": "track_actor_1",
        "region_id": region_id,
        "region_kind": region_kind,
        "observed_class": observed_class,
        "broader_class": broader_class,
        "decision_state": decision_state,
        "confidence": confidence,
        "ambiguity": ambiguity,
        "abstention_reason": abstention_reason,
        "evidence_sources": evidence,
        "texture_evidence": _texture(),
        "contact_context": contact_context,
        "fusion": fusion,
    }


def _base_packet() -> dict:
    return {
        "schema_version": "1.0.0",
        "manifest_id": "row089_visual_material_recognition_manifest",
        "revision": "r001",
        "run_id": "run_089",
        "scene_id": "scene_089",
        "shot_id": "shot_089",
        "take_id": "take_089",
        "is_synthetic": True,
        "video_sha256": "a" * 64,
        "timeline_binding": {
            "timeline_id": "timeline_row084_fixture",
            "timeline_sha256": "b" * 64,
            "frame_count": 48,
            "frame_rate": 24.0,
            "frame_time_origin_seconds": 0.0,
        },
        "scene_registry_binding": {
            "scene_registry_id": "scene_registry_fixture",
            "scene_registry_sha256": "c" * 64,
            "frame_span_id": "span_0_47",
            "entity_region_count": 3,
        },
        "classifier_stack": {
            "classifier_id": "fixture_material_classifier",
            "weights_sha256": "d" * 64,
            "preprocessing_sha256": "e" * 64,
            "class_map_sha256": "f" * 64,
            "revision": "fixture_v1",
        },
        "dependency_authority": {
            "row085_complete": False,
            "row088_complete": False,
        },
        "runtime_authority": {
            "material_benchmark_pass": False,
            "runtime_receipt_present": False,
            "combined_frame_contact_audio_review_present": False,
        },
        "material_decisions": [
            _decision(
                decision_id="dec_hardwood_floor",
                frame_index=0,
                pts=0,
                region_id="region_floor",
                observed_class="hardwood",
                broader_class="hard_floor",
                supports_class="hardwood",
            ),
            _decision(
                decision_id="dec_fabric_sleeve",
                frame_index=1,
                pts=1,
                region_id="region_sleeve",
                region_kind="clothing_region",
                observed_class="fabric",
                broader_class="textile",
                supports_class="fabric",
            ),
            _decision(
                decision_id="dec_ambiguous_surface",
                frame_index=2,
                pts=2,
                region_id="region_unknown",
                observed_class=None,
                broader_class=None,
                decision_state="abstain",
                confidence=0.0,
                ambiguity="high",
                abstention_reason="independent_evidence_disagreement",
                supports_class="hardwood",
                disagreement=True,
            ),
        ],
        "thresholds": {
            "min_class_confidence": 0.7,
            "min_agreeing_independent_sources": 2,
            "max_abstention_ratio": 0.75,
            "min_texture_quality": 0.5,
        },
        "provenance": {"fixture": "row089_unit"},
    }


class Row089VisualMaterialRecognitionCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))

    def _run_compile(self, packet: dict, *, expect_ok: bool) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            packet_path = tmpdir / "material_packet.json"
            output_path = tmpdir / "visual_material_recognition_manifest.json"
            _write_json(packet_path, packet)
            result = subprocess.run(
                [sys.executable, str(COMPILER), "--input", str(packet_path), "--output", str(output_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if expect_ok and result.returncode != 0:
                self.fail(f"compiler failed unexpectedly\nstdout={result.stdout}\nstderr={result.stderr}")
            if (not expect_ok) and result.returncode == 0:
                self.fail(f"compiler succeeded unexpectedly\nstdout={result.stdout}\nstderr={result.stderr}")
            if expect_ok:
                compiled = json.loads(output_path.read_text(encoding="utf-8"))
                errors = sorted(error.message for error in self.validator.iter_errors(compiled))
                self.assertEqual(errors, [])
                return result, compiled
            return result, None

    def test_compiles_hold_manifest_with_fusion_and_abstention(self) -> None:
        _, compiled = self._run_compile(_base_packet(), expect_ok=True)
        assert compiled is not None
        self.assertFalse(compiled["row_complete"])
        self.assertFalse(compiled["production_completion_allowed"])
        self.assertEqual(compiled["authority_ceiling"], "candidate")
        self.assertFalse(compiled["dependency_authority"]["dependency_ready"])
        self.assertFalse(compiled["runtime_authority"]["runtime_ready"])
        self.assertFalse(compiled["authority_summary"]["material_certification_allowed"])
        self.assertIn("dependency_row085_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("dependency_row088_incomplete", compiled["authority_summary"]["hold_reasons"])
        self.assertIn("material_benchmark_absent", compiled["authority_summary"]["hold_reasons"])
        self.assertEqual(compiled["metrics"]["decision_count"], 3)
        self.assertEqual(compiled["metrics"]["observed_class_count"], 2)
        self.assertEqual(compiled["metrics"]["abstention_count"], 1)
        self.assertEqual(compiled["metrics"]["disagreement_count"], 1)
        self.assertEqual(len(compiled["manifest_sha256"]), 64)
        self.assertIn("hardwood", compiled["taxonomy"]["required_material_classes"])
        self.assertEqual(compiled["taxonomy"]["governed_aliases"]["wood_floor"], "hardwood")

    def test_accepts_governed_alias_wood_floor(self) -> None:
        packet = _base_packet()
        packet["material_decisions"][0]["observed_class"] = "wood_floor"
        packet["material_decisions"][0]["evidence_sources"][0]["supports_class"] = "wood_floor"
        packet["material_decisions"][0]["evidence_sources"][1]["supports_class"] = "wood_floor"
        packet["material_decisions"][0]["evidence_sources"][2]["supports_class"] = "wood_floor"
        _, compiled = self._run_compile(packet, expect_ok=True)
        assert compiled is not None
        self.assertEqual(compiled["material_decisions"][0]["observed_class"], "hardwood")

    def test_rejects_ungoverned_alias(self) -> None:
        packet = _base_packet()
        packet["material_decisions"][0]["observed_class"] = "wood"
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("governed alias", result.stderr + result.stdout)

    def test_rejects_observed_class_with_disagreement(self) -> None:
        packet = _base_packet()
        packet["material_decisions"][0] = _decision(
            decision_id="dec_bad",
            frame_index=0,
            pts=0,
            region_id="region_floor",
            disagreement=True,
        )
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("blocked when evidence sources disagree", result.stderr + result.stdout)

    def test_rejects_abstain_with_nonzero_confidence(self) -> None:
        packet = _base_packet()
        packet["material_decisions"][2]["confidence"] = 0.3
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("abstain decision_state requires confidence=0", result.stderr + result.stdout)

    def test_rejects_contact_observed_without_trusted_ownership(self) -> None:
        packet = _base_packet()
        packet["material_decisions"][1] = _decision(
            decision_id="dec_contact",
            frame_index=1,
            pts=1,
            region_id="region_contact",
            region_kind="contact_region",
            observed_class="skin",
            broader_class="organic_surface",
            supports_class="skin",
            contact_context={
                "contact_id": "contact_1",
                "source_owner_id": "character_1",
                "target_owner_id": "prop_table",
                "ownership_state": "candidate",
            },
        )
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("trusted contact ownership_state", result.stderr + result.stdout)

    def test_rejects_low_confidence_observed_class(self) -> None:
        packet = _base_packet()
        packet["material_decisions"][0]["confidence"] = 0.4
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("confidence below thresholds.min_class_confidence", result.stderr + result.stdout)

    def test_rejects_single_independent_source_threshold(self) -> None:
        packet = _base_packet()
        packet["thresholds"]["min_agreeing_independent_sources"] = 1
        result, _ = self._run_compile(packet, expect_ok=False)
        self.assertIn("min_agreeing_independent_sources must be >= 2", result.stderr + result.stdout)

    def test_schema_requires_material_contracts_and_forbids_open_properties(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema.get("additionalProperties", True))
        required = set(schema["required"])
        self.assertIn("scene_registry_binding", required)
        self.assertIn("classifier_stack", required)
        self.assertIn("taxonomy", required)
        self.assertIn("material_decisions", required)
        self.assertIn("row_complete", required)


if __name__ == "__main__":
    unittest.main()
