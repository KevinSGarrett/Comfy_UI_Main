#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row089"
REQUIRED_MATERIALS = {
    "hardwood",
    "carpet",
    "tile",
    "skin",
    "fabric",
    "leather",
    "metal",
    "glass",
}
FIXTURE_PACKETS = (
    "materials_all_eight_required.json",
    "case_occlusion_abstain.json",
    "case_ambiguity_broader_class.json",
    "case_false_positive_disagreement_abstain.json",
)
SYNTHETIC_LEDGER = FIXTURE_DIR / "synthetic_per_class_benchmark_ledger.json"


def _load_compiler_module():
    spec = importlib.util.spec_from_file_location("compile_wave64_visual_material_recognition", COMPILER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMPILER_MOD = _load_compiler_module()


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

    def test_fixture_packets_cover_required_materials_and_edge_cases(self) -> None:
        for name in FIXTURE_PACKETS:
            self.assertTrue((FIXTURE_DIR / name).is_file(), msg=f"missing fixture {name}")

        _, all_eight = self._run_compile(
            COMPILER_MOD.load_fixture_packet("materials_all_eight_required.json"),
            expect_ok=True,
        )
        assert all_eight is not None
        covered = set(all_eight["metrics"]["required_classes_covered"])
        self.assertEqual(covered, REQUIRED_MATERIALS)
        self.assertEqual(all_eight["metrics"]["required_class_coverage_count"], 8)
        self.assertFalse(all_eight["row_complete"])
        self.assertFalse(all_eight["production_completion_allowed"])
        self.assertFalse(all_eight["authority_summary"]["material_certification_allowed"])

        _, occlusion = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_occlusion_abstain.json"),
            expect_ok=True,
        )
        assert occlusion is not None
        self.assertEqual(occlusion["metrics"]["abstention_count"], 1)
        self.assertEqual(
            occlusion["material_decisions"][0]["abstention_reason"],
            "region_occluded_visual_proof_absent",
        )
        self.assertFalse(occlusion["row_complete"])

        _, ambiguity = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_ambiguity_broader_class.json"),
            expect_ok=True,
        )
        assert ambiguity is not None
        self.assertEqual(ambiguity["metrics"]["broader_class_count"], 1)
        self.assertEqual(ambiguity["material_decisions"][0]["decision_state"], "broader_class")
        self.assertEqual(ambiguity["material_decisions"][0]["broader_class"], "hard_floor")
        self.assertTrue(ambiguity["material_decisions"][0]["fusion"]["disagreement"])
        self.assertFalse(ambiguity["row_complete"])

        _, false_positive = self._run_compile(
            COMPILER_MOD.load_fixture_packet("case_false_positive_disagreement_abstain.json"),
            expect_ok=True,
        )
        assert false_positive is not None
        self.assertEqual(false_positive["metrics"]["abstention_count"], 1)
        self.assertEqual(
            false_positive["material_decisions"][0]["abstention_reason"],
            "false_positive_independent_disagreement",
        )
        self.assertIsNone(false_positive["material_decisions"][0]["observed_class"])
        self.assertFalse(false_positive["row_complete"])

    def test_deterministic_replay_and_tamper_hash_check(self) -> None:
        packet = COMPILER_MOD.load_fixture_packet("materials_all_eight_required.json")
        first = COMPILER_MOD.compile_manifest(packet)
        second = COMPILER_MOD.compile_manifest(packet)
        # Wall-clock created_at may differ; content-addressed digest must replay.
        self.assertNotEqual(first.get("created_at"), "__sentinel__")
        second["created_at"] = "2000-01-01T00:00:00Z"
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(
            COMPILER_MOD.verify_manifest_integrity(first),
            first["manifest_sha256"],
        )
        self.assertEqual(
            COMPILER_MOD.verify_manifest_integrity(second),
            second["manifest_sha256"],
        )

        tampered = json.loads(json.dumps(first))
        tampered["material_decisions"][0]["confidence"] = 0.11
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_manifest_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

        hash_tampered = json.loads(json.dumps(first))
        hash_tampered["manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError) as ctx2:
            COMPILER_MOD.verify_manifest_integrity(hash_tampered)
        self.assertIn("tamper/replay mismatch", str(ctx2.exception))

    def test_synthetic_per_class_benchmark_ledger_binds_fixture_digests(self) -> None:
        self.assertTrue(SYNTHETIC_LEDGER.is_file(), msg="missing synthetic ledger fixture")
        ledger = COMPILER_MOD.build_synthetic_per_class_benchmark_ledger()
        checked_in = json.loads(SYNTHETIC_LEDGER.read_text(encoding="utf-8"))

        self.assertEqual(ledger, checked_in)
        self.assertEqual(
            COMPILER_MOD.verify_synthetic_benchmark_ledger_integrity(ledger),
            ledger["ledger_sha256"],
        )
        self.assertFalse(ledger["row_complete"])
        self.assertFalse(ledger["production_completion_allowed"])
        self.assertFalse(ledger["production_benchmark"])
        self.assertFalse(ledger["material_benchmark_pass"])
        self.assertFalse(ledger["visual_review_claimed"])
        self.assertFalse(ledger["rows085_088_acceptance_claimed"])
        self.assertEqual(ledger["authority_ceiling"], "fixture_synthetic_only")
        self.assertTrue(ledger["is_synthetic"])

        binding_by_name = {item["fixture_name"]: item for item in ledger["fixture_bindings"]}
        self.assertEqual(set(binding_by_name), set(FIXTURE_PACKETS))
        for name in FIXTURE_PACKETS:
            expected_file_digest = COMPILER_MOD.fixture_file_sha256(name)
            compiled = COMPILER_MOD.compile_manifest(COMPILER_MOD.load_fixture_packet(name))
            self.assertEqual(binding_by_name[name]["fixture_file_sha256"], expected_file_digest)
            self.assertEqual(
                binding_by_name[name]["compiled_manifest_sha256"],
                compiled["manifest_sha256"],
            )
            self.assertFalse(binding_by_name[name]["row_complete"])

        per_class = {item["material_class"]: item for item in ledger["per_class_expectations"]}
        self.assertEqual(set(per_class), REQUIRED_MATERIALS)
        for material_class, expectation in per_class.items():
            self.assertEqual(expectation["expected_decision_state"], "observed_class")
            self.assertEqual(expectation["expected_observed_class"], material_class)
            self.assertEqual(
                expectation["source_fixture"],
                "materials_all_eight_required.json",
            )

        edge_by_case = {item["case_id"]: item for item in ledger["edge_case_expectations"]}
        self.assertEqual(
            set(edge_by_case),
            {"occlusion_abstain", "ambiguity_broader_class", "false_positive_disagreement_abstain"},
        )
        self.assertEqual(edge_by_case["occlusion_abstain"]["expected_decision_state"], "abstain")
        self.assertEqual(
            edge_by_case["ambiguity_broader_class"]["expected_decision_state"],
            "broader_class",
        )
        self.assertEqual(
            edge_by_case["false_positive_disagreement_abstain"]["expected_decision_state"],
            "abstain",
        )

        tampered = json.loads(json.dumps(ledger))
        tampered["material_benchmark_pass"] = True
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_synthetic_benchmark_ledger_integrity(tampered)
        self.assertIn("tamper/replay mismatch", str(ctx.exception))

    def test_ledger_vs_compiled_manifest_expectation_verifier_rejects_digest_drift(self) -> None:
        receipt = COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations()
        self.assertEqual(receipt["status"], "ok")
        self.assertTrue(receipt["digest_drift_rejected"])
        self.assertFalse(receipt["row_complete"])
        self.assertFalse(receipt["production_benchmark"])
        self.assertFalse(receipt["material_benchmark_pass"])
        self.assertFalse(receipt["visual_review_claimed"])
        self.assertFalse(receipt["rows085_088_acceptance_claimed"])
        self.assertEqual(receipt["fixture_binding_count"], 4)
        self.assertEqual(receipt["per_class_expectation_count"], 8)
        self.assertEqual(receipt["edge_case_expectation_count"], 3)
        self.assertEqual(receipt["authority_ceiling"], "fixture_synthetic_only")

        cli = subprocess.run(
            [sys.executable, str(COMPILER), "--verify-synthetic-benchmark-ledger"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cli.returncode, 0, msg=cli.stderr + cli.stdout)
        cli_receipt = json.loads(cli.stdout)
        self.assertEqual(cli_receipt["ledger_sha256"], receipt["ledger_sha256"])
        self.assertFalse(cli_receipt["material_benchmark_pass"])

        ledger = COMPILER_MOD.load_synthetic_benchmark_ledger()
        drifted = json.loads(json.dumps(ledger))
        drifted["fixture_bindings"][0]["compiled_manifest_sha256"] = "0" * 64
        # Integrity hash still matches only when ledger_sha256 is recomputed; force
        # a consistent but digest-drifted ledger body so the verifier reaches drift.
        drifted_body = {key: value for key, value in drifted.items() if key != "ledger_sha256"}
        drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(drifted_body)
        with self.assertRaises(ValueError) as ctx:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(drifted)
        self.assertIn("compiled manifest digest drift", str(ctx.exception))

        file_drifted = json.loads(json.dumps(ledger))
        file_drifted["fixture_bindings"][0]["fixture_file_sha256"] = "1" * 64
        file_body = {key: value for key, value in file_drifted.items() if key != "ledger_sha256"}
        file_drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(file_body)
        with self.assertRaises(ValueError) as ctx2:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(file_drifted)
        self.assertIn("fixture file digest drift", str(ctx2.exception))

        expectation_drifted = json.loads(json.dumps(ledger))
        expectation_drifted["per_class_expectations"][0]["expected_decision_state"] = "abstain"
        expectation_body = {
            key: value for key, value in expectation_drifted.items() if key != "ledger_sha256"
        }
        expectation_drifted["ledger_sha256"] = COMPILER_MOD._canonical_sha256(expectation_body)
        with self.assertRaises(ValueError) as ctx3:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(
                expectation_drifted
            )
        self.assertIn("expected_decision_state mismatch", str(ctx3.exception))

        pass_claimed = json.loads(json.dumps(ledger))
        pass_claimed["material_benchmark_pass"] = True
        pass_body = {key: value for key, value in pass_claimed.items() if key != "ledger_sha256"}
        pass_claimed["ledger_sha256"] = COMPILER_MOD._canonical_sha256(pass_body)
        with self.assertRaises(ValueError) as ctx4:
            COMPILER_MOD.verify_synthetic_ledger_vs_compiled_manifest_expectations(pass_claimed)
        self.assertIn("material_benchmark_pass=false", str(ctx4.exception))


if __name__ == "__main__":
    unittest.main()
