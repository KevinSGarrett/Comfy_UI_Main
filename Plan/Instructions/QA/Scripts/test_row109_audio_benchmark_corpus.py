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
COMPILER = ROOT / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_audio_benchmark_corpus.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/audio_benchmark_corpus_manifest.schema.json"
POLICY = ROOT / "Plan/10_REGISTRIES/wave64_row109_audio_benchmark_corpus_policy_registry.json"
FIXTURE_DIR = ROOT / "Plan/Instructions/QA/Evidence/Wave64/fixtures/row109"
BENCHMARK_MANIFEST = (
    ROOT
    / "Plan/Instructions/QA/Evidence/Wave64/benchmarks/row109/audio_benchmark_corpus_manifest.json"
)
EVIDENCE = ROOT / "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-109_audio_benchmark_corpus.json"

REQUIRED_GATES = (
    "coverage_matrix",
    "annotation_authority",
    "partition_separation",
    "adversarial_cases",
    "truth_integrity",
)
REQUIRED_FAMILIES = {
    "footstep",
    "heel_strike",
    "body_contact",
    "clothing",
    "prop",
    "room_ambience",
    "occlusion",
    "multi_actor",
    "cut_boundary",
    "ambiguous_material",
    "intentional_silence",
}
REQUIRED_ADVERSARIAL = {
    "filename_semantic_mismatch",
    "generated_candidate_truth_contamination",
    "partition_leak_attempt",
    "wrong_material_timing_drift",
}


def _load_compiler_module():
    spec = importlib.util.spec_from_file_location(
        "compile_wave64_audio_benchmark_corpus", COMPILER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _load_compiler_module()


class Row109AudioBenchmarkCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def test_policy_freezes_required_gates_and_forbids_pcm(self) -> None:
        self.assertEqual(tuple(self.policy["required_gates"]), REQUIRED_GATES)
        self.assertFalse(self.policy["media_policy"]["pcm_decode_allowed"])
        self.assertFalse(self.policy["media_policy"]["live_full_library_scan_allowed"])
        self.assertEqual(
            self.policy["revision"],
            "wave64_row109_audio_benchmark_corpus_policy_v0.1.0",
        )
        self.assertEqual(
            set(self.policy["media_policy"]["allowed_media_kinds"]),
            {"synthetic_fixture_descriptor", "genuine_annotated_media_copy"},
        )
        self.assertEqual(
            self.policy["media_policy"]["genuine_bind_requires"]["annotator_role"],
            "human_gold",
        )
        self.assertEqual(
            self.policy["media_policy"]["genuine_corpus_min_counts"]["calibration"],
            11,
        )

    def test_fixture_index_and_case_packets_present(self) -> None:
        index_path = FIXTURE_DIR / "corpus_case_index.json"
        self.assertTrue(index_path.is_file())
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(index["case_count"], 30)
        self.assertFalse(index["pcm_decode_invoked"])
        for entry in index["cases"]:
            case_path = FIXTURE_DIR / entry["fixture"]
            self.assertTrue(case_path.is_file(), entry["fixture"])
            case = json.loads(case_path.read_text(encoding="utf-8"))
            self.assertEqual(case["case_id"], entry["case_id"])
            self.assertEqual(case["media_locator"]["kind"], "synthetic_fixture_descriptor")
            self.assertIsNone(case["media_locator"]["pcm_bytes"])
            self.assertFalse(case["media_locator"]["decode_invoked"])

    def test_compile_manifest_passes_schema_and_gates(self) -> None:
        manifest = MOD.compile_corpus_manifest(ROOT)
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(manifest),
            key=lambda err: list(err.path),
        )
        self.assertEqual(errors, [])
        self.assertTrue(manifest["coverage_matrix"]["coverage_complete"])
        self.assertTrue(manifest["partition_manifest"]["separation_ok"])
        self.assertTrue(manifest["adversarial_cases"]["complete"])
        self.assertTrue(manifest["truth_integrity"]["integrity_ok"])
        self.assertFalse(manifest["pcm_decode_invoked"])
        self.assertFalse(manifest["live_full_library_scan"])
        self.assertFalse(manifest["decision"]["product_completion"])
        self.assertFalse(manifest["decision"]["runtime_completion"])
        self.assertTrue(all(manifest["decision"]["gates_satisfied"].values()))
        cal = {
            c["event_family"]
            for c in manifest["cases"]
            if c["partition"] == "calibration"
        }
        hold = {
            c["event_family"]
            for c in manifest["cases"]
            if c["partition"] == "held_out_test"
        }
        self.assertTrue(REQUIRED_FAMILIES.issubset(cal))
        self.assertTrue(REQUIRED_FAMILIES.issubset(hold))
        roles = {
            c["adversarial_role"]
            for c in manifest["cases"]
            if c["partition"] == "adversarial"
        }
        self.assertTrue(REQUIRED_ADVERSARIAL.issubset(roles))

    def test_partition_separation_rejects_held_out_media_leak(self) -> None:
        manifest = MOD.compile_corpus_manifest(ROOT)
        cases = [dict(c) for c in manifest["cases"]]
        hold = next(c for c in cases if c["partition"] == "held_out_test")
        cal = next(c for c in cases if c["partition"] == "calibration")
        hold["media_locator"] = dict(cal["media_locator"])
        with self.assertRaises(MOD.AudioBenchmarkCorpusError) as ctx:
            MOD.build_partition_manifest(cases)
        self.assertIn("partition_separation_media_leak_into_held_out", str(ctx.exception))

    def test_truth_contamination_probe_blocks(self) -> None:
        MOD.attempt_truth_contamination(ROOT)

    def test_dependency_067_068_admissions_satisfied(self) -> None:
        admissions = MOD.evaluate_all_dependency_admissions(ROOT)
        self.assertTrue(admissions["TRK-W64-067"]["dependency_satisfied"])
        self.assertTrue(admissions["TRK-W64-068"]["dependency_satisfied"])
        self.assertTrue(admissions["TRK-W64-067"]["delta_exists"])
        self.assertTrue(admissions["TRK-W64-068"]["delta_exists"])

    def test_cli_hold_emits_non_complete_evidence(self) -> None:
        # Outputs must remain under the canonical project root (compiler fail-closed).
        with tempfile.TemporaryDirectory(dir=str(FIXTURE_DIR)) as tmp:
            out = Path(tmp) / "evidence.json"
            manifest_out = Path(tmp) / "manifest.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(COMPILER),
                    "--mode",
                    "hold",
                    "--output",
                    str(out),
                    "--manifest-output",
                    str(manifest_out),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(payload["row_complete"])
            self.assertFalse(payload["implementation_completion_claimed"])
            self.assertFalse(payload["runtime_completion_claimed"])
            self.assertFalse(payload["production_authority"])
            self.assertEqual(payload["decision"]["status"], "blocked")
            self.assertTrue(payload["decision"]["dependency_067_068_satisfied"])
            self.assertIn("GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT", payload["blocker_codes"])
            manifest = json.loads(manifest_out.read_text(encoding="utf-8"))
            MOD.verify_manifest_integrity(ROOT, manifest)

    def test_checked_in_evidence_and_benchmark_manifest_consistent(self) -> None:
        self.assertTrue(EVIDENCE.is_file())
        self.assertTrue(BENCHMARK_MANIFEST.is_file())
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        manifest = json.loads(BENCHMARK_MANIFEST.read_text(encoding="utf-8"))
        self.assertFalse(evidence["row_complete"])
        self.assertEqual(
            evidence["fixture_corpus"]["manifest_sha256"], manifest["manifest_sha256"]
        )
        self.assertFalse(evidence["fixture_corpus"]["pcm_decode_invoked"])
        self.assertFalse(evidence["fixture_corpus"]["live_full_library_scan"])
        MOD.verify_manifest_integrity(ROOT, manifest)

    def test_genuine_corpus_gate_absent_on_synthetic_only_compile(self) -> None:
        manifest = MOD.compile_corpus_manifest(ROOT)
        gate = MOD.evaluate_genuine_annotated_media_corpus(manifest["cases"])
        self.assertFalse(gate["present"])
        self.assertEqual(gate["case_count"], 0)
        self.assertEqual(gate["blocker_code"], "GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT")
        self.assertIn("no_genuine_annotated_media_copy_cases", gate["reasons"])
        self.assertTrue(manifest["is_synthetic"])
        hold = MOD.build_hold_packet(ROOT, manifest)
        self.assertIn("GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT", hold["blocker_codes"])
        self.assertFalse(hold["genuine_annotated_media_corpus"]["present"])
        self.assertFalse(hold["row_complete"])

    def test_genuine_media_path_fails_closed_when_copy_absent(self) -> None:
        cases = MOD.load_fixture_cases(ROOT)
        raw = next(c for c in cases if c["partition"] == "train")
        probe = {
            k: v for k, v in raw.items() if not str(k).startswith("_")
        }
        probe["annotation"] = dict(probe["annotation"])
        probe["annotation"]["annotator_role"] = "human_gold"
        probe["media_locator"] = {
            "kind": "genuine_annotated_media_copy",
            "copy_path": (
                "Plan/Instructions/QA/Evidence/Wave64/media/row109/"
                "absent_step1_probe_clip.wav"
            ),
            "media_sha256": "0" * 64,
            "rights_decision_sha256": "a" * 64,
            "pcm_bytes": None,
            "decode_invoked": False,
            "live_full_library_scan": False,
        }
        probe["_source_fixture"] = raw["_source_fixture"]
        probe["_source_fixture_path"] = raw["_source_fixture_path"]
        with self.assertRaises(MOD.AudioBenchmarkCorpusError) as ctx:
            MOD.compile_case(ROOT, probe)
        self.assertIn("genuine_annotated_media_copy_absent", str(ctx.exception))

    def test_genuine_media_requires_human_gold_and_rejects_pcm_decode(self) -> None:
        cases = MOD.load_fixture_cases(ROOT)
        raw = next(c for c in cases if c["partition"] == "calibration")
        base = {
            k: v for k, v in raw.items() if not str(k).startswith("_")
        }
        base["_source_fixture"] = raw["_source_fixture"]
        base["_source_fixture_path"] = raw["_source_fixture_path"]
        base["annotation"] = dict(base["annotation"])
        base["annotation"]["annotator_role"] = "synthetic_fixture_authority"
        base["media_locator"] = {
            "kind": "genuine_annotated_media_copy",
            "copy_path": (
                "Plan/Instructions/QA/Evidence/Wave64/media/row109/"
                "absent_step1_probe_clip.wav"
            ),
            "media_sha256": "0" * 64,
            "rights_decision_sha256": "a" * 64,
            "pcm_bytes": None,
            "decode_invoked": False,
            "live_full_library_scan": False,
        }
        with self.assertRaises(MOD.AudioBenchmarkCorpusError) as ctx:
            MOD.compile_case(ROOT, base)
        self.assertIn("genuine_media_requires_human_gold", str(ctx.exception))

        base["annotation"]["annotator_role"] = "human_gold"
        base["media_locator"]["decode_invoked"] = True
        with self.assertRaises(MOD.AudioBenchmarkCorpusError) as ctx:
            MOD.compile_case(ROOT, base)
        self.assertIn("pcm_decode_forbidden", str(ctx.exception))

    def test_schema_accepts_genuine_media_locator_shape(self) -> None:
        locator = {
            "kind": "genuine_annotated_media_copy",
            "copy_path": (
                "Plan/Instructions/QA/Evidence/Wave64/media/row109/example.wav"
            ),
            "media_sha256": "b" * 64,
            "rights_decision_sha256": "c" * 64,
            "pcm_bytes": None,
            "decode_invoked": False,
            "live_full_library_scan": False,
        }
        media_schema = self.schema["$defs"]["corpus_case"]["properties"]["media_locator"]
        errors = sorted(
            Draft202012Validator(media_schema).iter_errors(locator),
            key=lambda err: list(err.path),
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            self.schema["properties"]["is_synthetic"],
            {"type": "boolean"},
        )


if __name__ == "__main__":
    unittest.main()
