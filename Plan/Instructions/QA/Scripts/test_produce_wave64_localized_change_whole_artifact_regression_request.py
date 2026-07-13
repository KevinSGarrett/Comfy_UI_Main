#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_localized_change_whole_artifact_regression_request.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_localized_change_whole_artifact_regression_request.schema.json"
INPUTS = (
    "baseline_row033_report", "candidate_row033_report", "row032_global_audio_report", "wave33_preview_qa",
    "baseline_artifact_manifest", "candidate_artifact_manifest", "failure_record", "retest_record",
    "whole_artifact_delta", "whole_artifact_review", "runtime_proof", "baseline_primary_media",
    "candidate_primary_media", "change_manifest",
)


def stable_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def binding(path: Path) -> dict[str, object]:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


class LocalizedRegressionRequestProducerTests(unittest.TestCase):
    def build(self, base: Path) -> dict[str, Path]:
        base.mkdir(parents=True, exist_ok=True)
        paths = {name: base / f"{name}.json" for name in INPUTS}
        paths.update({"metadata": base / "metadata.json", "output": base / "request.json", "output_report": base / "report.json"})
        for index, name in enumerate(INPUTS):
            write_json(paths[name], {"fixture": name, "index": index})
        attempts: list[object] = []
        metadata = {
            "regression_id": "reg-001", "change_id": "chg-001", "scene_id": "scene-001", "shot_id": "shot-001",
            "take_id": "take-001", "baseline_artifact_id": "base-artifact", "candidate_artifact_id": "candidate-artifact",
            "baseline_run_id": "base-run", "candidate_run_id": "candidate-run", "review_run_id": "review-run",
            "change_kind": "localized_edit", "audio_change_expected": False,
            "production_authority_claim": {"authority_id": "none", "bundle_id": "none"},
            "canonical_partitions": {
                "visual_domain": {"total_frames": 1, "width": 1, "height": 1, "timeline_start_frame": 0, "timeline_end_frame": 0},
                "audio_domain": {"total_samples": 1, "sample_rate_hz": 1, "channel_count": 1, "duration_seconds": 1.0},
                "visual_partitions": [{"partition_id": "v", "start_frame": 0, "end_frame": 0, "x": 0, "y": 0, "width": 1, "height": 1}],
                "audio_partitions": [{"partition_id": "a", "start_sample": 0, "end_sample": 0, "start_seconds": 0.0, "end_seconds": 1.0, "channel_start": 0, "channel_end": 0, "sample_rate_hz": 1, "channel_count": 1}],
            },
            "target_partition_ids": ["v"], "non_target_partition_ids": ["a"],
            "attempt_history": {
                "attempts": attempts, "attempt_history_digest": stable_sha256(attempts),
                "deeper_diagnosis": {"diagnosis_hash": "d" * 64, "binding": binding(paths["retest_record"])},
                "new_direction_hash": "e" * 64,
            },
        }
        write_json(paths["metadata"], metadata)
        return paths

    def args(self, paths: dict[str, Path]) -> list[str]:
        result = ["--metadata", str(paths["metadata"])]
        for name in INPUTS:
            result.extend((f"--{name.replace('_', '-')}", str(paths[name])))
        result.extend(("--output-report", str(paths["output_report"]), "--output", str(paths["output"]), "--root", str(ROOT)))
        return result

    def run_cli(self, paths: dict[str, Path], *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *self.args(paths), *extra], cwd=ROOT, text=True, capture_output=True)

    def test_emits_schema_valid_request_with_exact_bindings(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build(Path(temporary)); result = self.run_cli(paths)
            self.assertEqual(result.returncode, 0, result.stdout)
            request = json.loads(paths["output"].read_text())
            Draft202012Validator(json.loads(SCHEMA.read_text())).validate(request)
            self.assertEqual(set(request["bindings"]), {f"{name}_binding" for name in INPUTS})

    def test_rejects_partition_overlap_gap_and_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths=self.build(Path(temporary));meta=json.loads(paths["metadata"].read_text());meta["non_target_partition_ids"]=["v"];write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"gap");meta=json.loads(paths["metadata"].read_text());meta["non_target_partition_ids"]=[];write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"dup");meta=json.loads(paths["metadata"].read_text());meta["canonical_partitions"]["audio_partitions"][0]["partition_id"]="v";write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"numeric_gap");meta=json.loads(paths["metadata"].read_text());meta["canonical_partitions"]["visual_domain"]["total_frames"]=2;meta["canonical_partitions"]["visual_domain"]["timeline_end_frame"]=1;write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)

    def test_rejects_attempt_digest_and_retest_binding_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths=self.build(Path(temporary));meta=json.loads(paths["metadata"].read_text());meta["attempt_history"]["attempt_history_digest"]="0"*64;write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"binding");meta=json.loads(paths["metadata"].read_text());meta["attempt_history"]["deeper_diagnosis"]["binding"]["sha256"]="0"*64;write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"sequence");meta=json.loads(paths["metadata"].read_text());attempt={"attempt_number":2,"failure_classification":"x","severity":"high","diagnosis_id":"d","diagnosis_hash":"1"*64,"change_hash":"2"*64,"expected_result_hash":"3"*64,"change_summary_hash":"4"*64,"result":"failed","result_report_binding":binding(paths["whole_artifact_review"]),"similar_to_current":False,"new_direction_hash":"5"*64};meta["attempt_history"]["attempts"]=[attempt];meta["attempt_history"]["attempt_history_digest"]=stable_sha256([attempt]);write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)

    def test_rejects_duplicate_input_metadata_keys_and_output_collisions(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths=self.build(Path(temporary));paths["candidate_primary_media"]=paths["baseline_primary_media"];self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"unknown");meta=json.loads(paths["metadata"].read_text());meta["unknown"]=1;write_json(paths["metadata"],meta);self.assertEqual(self.run_cli(paths).returncode,2)
            paths=self.build(Path(temporary)/"collision");paths["output"].write_text("sentinel");self.assertEqual(self.run_cli(paths).returncode,2);self.assertEqual(paths["output"].read_text(),"sentinel")

    def test_rejects_duplicate_json_key_and_root_escape(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths=self.build(Path(temporary));paths["metadata"].write_text('{"regression_id":"a","regression_id":"b"}');self.assertEqual(self.run_cli(paths).returncode,2)
            outside=Path(tempfile.gettempdir())/"row034-outside.json";outside.write_text("{}");paths=self.build(Path(temporary)/"escape");paths["failure_record"]=outside;self.assertEqual(self.run_cli(paths).returncode,2);outside.unlink(missing_ok=True)

    def test_production_input_requires_exact_authority_object(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths=self.build(Path(temporary));result=self.run_cli(paths,"--production-input");self.assertEqual(result.returncode,2);self.assertIn("exact production authority object is required",result.stdout)

    def test_exact_production_authority_object_allows_production_packet(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            isolated = Path(temporary) / "isolated_root"
            scripts = isolated / "Plan/07_IMPLEMENTATION/scripts"; schemas = isolated / "Plan/08_SCHEMAS"; registries = isolated / "Plan/10_REGISTRIES"
            scripts.mkdir(parents=True); schemas.mkdir(parents=True); registries.mkdir(parents=True)
            source = SCRIPT.read_text(encoding="utf-8").replace('Path("C:/Comfy_UI_Main").resolve()', f'Path(r"{isolated}").resolve()')
            isolated_script = scripts / SCRIPT.name; isolated_script.write_text(source, encoding="utf-8")
            shutil.copy2(SCHEMA, schemas / SCHEMA.name)
            rules_path = registries / "wave64_localized_change_whole_artifact_regression_rules.json"
            shutil.copy2(ROOT / "Plan/10_REGISTRIES/wave64_localized_change_whole_artifact_regression_rules.json", rules_path)
            paths = self.build(isolated / "runtime_artifacts/fixture")
            write_json(paths["runtime_proof"], {"identity": {"producer_id": "producer-1"}})
            write_json(paths["whole_artifact_review"], {"reviewer_identity": {"reviewer_id": "reviewer-qa"}})
            write_json(paths["change_manifest"], {"change_summary_hash": "b" * 64})
            args = self.args(paths); args[-1] = str(isolated)
            first = subprocess.run([sys.executable, str(isolated_script), *args], cwd=isolated, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stdout)
            request = json.loads(paths["output"].read_text())
            expected = {**request["production_authority_claim"], **{key: request[key] for key in ("regression_id","change_id","scene_id","shot_id","take_id","baseline_artifact_id","candidate_artifact_id","baseline_run_id","candidate_run_id","review_run_id","change_kind","audio_change_expected")}, "current_attempt_number": 1, "attempt_history_digest": request["attempt_history"]["attempt_history_digest"], "canonical_partition_digest": stable_sha256(request["canonical_partitions"]), "producer_id": "producer-1", "reviewer_id": "reviewer-qa", "reviewer_role": "Codex Desktop autonomous QA", "change_summary_hash": "b" * 64, "input_bindings": {key: {**value, "path": Path(value["path"]).resolve().relative_to(isolated).as_posix()} for key, value in request["bindings"].items()}}
            rules = json.loads(rules_path.read_text()); rules["authority_rules"]["production_authority_exact_objects"] = [expected]; write_json(rules_path, rules)
            paths["output"].unlink()
            second = subprocess.run([sys.executable, str(isolated_script), *args, "--production-input"], cwd=isolated, text=True, capture_output=True)
            self.assertEqual(second.returncode, 0, second.stdout)


if __name__ == "__main__":
    unittest.main()
