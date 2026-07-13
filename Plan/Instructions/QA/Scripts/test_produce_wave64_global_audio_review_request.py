#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_global_audio_review_request.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_global_audio_review_request.schema.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(path: Path) -> dict[str, object]:
    return {"path": str(path.resolve()), "sha256": sha(path), "bytes": path.stat().st_size}


class GlobalAudioRequestProducerTests(unittest.TestCase):
    def build(self, base: Path, *, synthetic: bool = True) -> dict[str, Path]:
        base.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {"optional_dir": base / "optional", "output": base / "request.json", "output_report": base / "report.json"}
        paths["optional_dir"].mkdir()
        for side, run in (("baseline", "base"), ("candidate", "cand")):
            for suffix, ext in (("mix_wav", "wav"), ("row031_strict_report", "json"), ("wave30_event_manifest", "json"), ("wave30_mix_manifest", "json"), ("wave30_qa_report", "json")):
                paths[f"{side}_{suffix}"] = base / f"{side}_{suffix}.{ext}"
            paths[f"{side}_mix_wav"].write_bytes(f"RIFF-{side}".encode())
            event = {"run_id": run, "is_synthetic": synthetic, "audio_events": [{"audio_event_id": "target"}, {"audio_event_id": "background"}]}
            paths[f"{side}_wave30_event_manifest"].write_text(json.dumps(event) + "\n", encoding="utf-8")
            event_link = {k: bind(paths[f"{side}_wave30_event_manifest"])[k] for k in ("path", "sha256")}
            mix = {"run_id": run, "is_synthetic": synthetic, "event_manifest_bindings": [event_link], "mixdown_artifact": bind(paths[f"{side}_mix_wav"])}
            paths[f"{side}_wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
            mix_link = {k: bind(paths[f"{side}_wave30_mix_manifest"])[k] for k in ("path", "sha256")}
            qa = {"run_id": run, "is_synthetic": synthetic, "event_manifest_binding": event_link, "mix_manifest_binding": mix_link}
            paths[f"{side}_wave30_qa_report"].write_text(json.dumps(qa) + "\n", encoding="utf-8")
            row031 = {
                "schema_name": "wave64_strict_audio_review_report", "run_id": run, "is_synthetic": synthetic,
                "capture_mode": "technical_capture", "artifact_bindings": {
                    "mix_wav": bind(paths[f"{side}_mix_wav"]), "wave30_event_manifest": bind(paths[f"{side}_wave30_event_manifest"]),
                    "wave30_mix_manifest": bind(paths[f"{side}_wave30_mix_manifest"]), "wave30_qa_report": bind(paths[f"{side}_wave30_qa_report"]),
                },
            }
            paths[f"{side}_row031_strict_report"].write_text(json.dumps(row031) + "\n", encoding="utf-8")
        return paths

    def args(self, p: dict[str, Path]) -> list[str]:
        result: list[str] = []
        for side in ("baseline", "candidate"):
            for suffix in ("mix_wav", "row031_strict_report", "wave30_event_manifest", "wave30_mix_manifest", "wave30_qa_report"):
                result.extend((f"--{side}-{suffix.replace('_', '-')}", str(p[f"{side}_{suffix}"])))
        result.extend(("--review-run-id", "review", "--baseline-run-id", "base", "--candidate-run-id", "cand", "--change-kind", "audio_localized", "--audio-change-expected", "--target-event-id", "target", "--allowed-window", "0.1:0.3", "--optional-dir", str(p["optional_dir"]), "--output-report", str(p["output_report"]), "--output", str(p["output"])))
        return result

    def run_cli(self, *args: str, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args], cwd=ROOT, text=True, capture_output=True)

    def test_emits_schema_valid_request_and_derives_non_targets(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p = self.build(Path(temporary)); result = self.run_cli(*self.args(p)); self.assertEqual(result.returncode, 0, result.stdout)
            request = json.loads(p["output"].read_text()); Draft202012Validator(json.loads(SCHEMA.read_text())).validate(request)
            self.assertEqual(request["localized_change_declaration"]["non_target_audio_event_ids"], ["background"])
            self.assertNotIn("production_bundle_binding", request)

    def test_rejects_identity_event_set_and_wave30_lineage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p = self.build(Path(temporary)); event=json.loads(p["baseline_wave30_event_manifest"].read_text());event["run_id"]="wrong";p["baseline_wave30_event_manifest"].write_text(json.dumps(event));self.assertEqual(self.run_cli(*self.args(p)).returncode,2)
            p=self.build(Path(temporary)/"events");event=json.loads(p["candidate_wave30_event_manifest"].read_text());event["audio_events"].pop();p["candidate_wave30_event_manifest"].write_text(json.dumps(event));self.assertEqual(self.run_cli(*self.args(p)).returncode,2)
            p=self.build(Path(temporary)/"lineage");mix=json.loads(p["candidate_wave30_mix_manifest"].read_text());mix["mixdown_artifact"]["sha256"]="0"*64;p["candidate_wave30_mix_manifest"].write_text(json.dumps(mix));self.assertEqual(self.run_cli(*self.args(p)).returncode,2)

    def test_rejects_row031_lineage_and_capture_mode_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));row=json.loads(p["candidate_row031_strict_report"].read_text());row["artifact_bindings"]["mix_wav"]["sha256"]="0"*64;p["candidate_row031_strict_report"].write_text(json.dumps(row));self.assertEqual(self.run_cli(*self.args(p)).returncode,2)
            p=self.build(Path(temporary)/"mode");self.assertEqual(self.run_cli(*self.args(p),"--capture-mode","hand_authored_relabel").returncode,2)

    def test_rejects_unknown_duplicate_targets_and_invalid_windows(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));self.assertEqual(self.run_cli(*self.args(p),"--target-event-id","missing").returncode,2)
            p=self.build(Path(temporary)/"dup");self.assertEqual(self.run_cli(*self.args(p),"--target-event-id","target").returncode,2)
            p=self.build(Path(temporary)/"window");args=self.args(p);args[args.index("0.1:0.3")]="0.3:0.1";self.assertEqual(self.run_cli(*args).returncode,2)

    def test_visual_no_audio_change_emits_empty_target_and_windows(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));args=self.args(p);start=args.index("--change-kind");args[start+1]="visual_localized";args.remove("--audio-change-expected");i=args.index("--target-event-id");del args[i:i+2];i=args.index("--allowed-window");del args[i:i+2]
            result=self.run_cli(*args);self.assertEqual(result.returncode,0,result.stdout);request=json.loads(p["output"].read_text());self.assertEqual(request["localized_change_declaration"]["target_audio_event_ids"],[])

    def test_visual_audio_change_and_production_paths_are_emitted(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));args=self.args(p);args[args.index("audio_localized")]="visual_localized";result=self.run_cli(*args);self.assertEqual(result.returncode,0,result.stdout)
            p=self.build(Path(temporary)/"production",synthetic=False);result=self.run_cli(*self.args(p),"--production-input");self.assertEqual(result.returncode,0,result.stdout);self.assertFalse(json.loads(p["output"].read_text())["is_synthetic"])

    def test_audio_localized_requires_audio_change_expected_flag(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));args=self.args(p);args.remove("--audio-change-expected");self.assertEqual(self.run_cli(*args).returncode,2)

    def test_binds_valid_production_bundle_and_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));event=json.loads(p["baseline_wave30_event_manifest"].read_text());event["scene_id"]="scene";p["baseline_wave30_event_manifest"].write_text(json.dumps(event));mix=json.loads(p["baseline_wave30_mix_manifest"].read_text());mix["event_manifest_bindings"]=[{k:bind(p["baseline_wave30_event_manifest"])[k] for k in ("path","sha256")}];p["baseline_wave30_mix_manifest"].write_text(json.dumps(mix));qa=json.loads(p["baseline_wave30_qa_report"].read_text());qa["event_manifest_binding"]={k:bind(p["baseline_wave30_event_manifest"])[k] for k in ("path","sha256")};qa["mix_manifest_binding"]={k:bind(p["baseline_wave30_mix_manifest"])[k] for k in ("path","sha256")};p["baseline_wave30_qa_report"].write_text(json.dumps(qa));row=json.loads(p["baseline_row031_strict_report"].read_text());row["artifact_bindings"]["wave30_event_manifest"]=bind(p["baseline_wave30_event_manifest"]);row["artifact_bindings"]["wave30_mix_manifest"]=bind(p["baseline_wave30_mix_manifest"]);row["artifact_bindings"]["wave30_qa_report"]=bind(p["baseline_wave30_qa_report"]);p["baseline_row031_strict_report"].write_text(json.dumps(row));bundle={"schema_name":"wave64_global_audio_production_bundle","schema_version":1,"bundle_id":"bundle","scene_id":"scene","baseline_authority_id":"baseline_board","bundle_authority_id":"bundle_board","baseline_run_id":"base","candidate_run_id":"cand","review_run_id":"review","synthetic_only":False,"baseline_mix_wav_sha256":sha(p["baseline_mix_wav"]),"baseline_row031_sha256":sha(p["baseline_row031_strict_report"]),"candidate_mix_wav_sha256":sha(p["candidate_mix_wav"]),"candidate_row031_sha256":sha(p["candidate_row031_strict_report"]),"candidate_wave30_qa_sha256":sha(p["candidate_wave30_qa_report"])};(p["optional_dir"]/"production_bundle.json").write_text(json.dumps(bundle));self.assertEqual(self.run_cli(*self.args(p)).returncode,0)
            p=self.build(Path(temporary)/"bad");bundle["candidate_mix_wav_sha256"]="0"*64;(p["optional_dir"]/"production_bundle.json").write_text(json.dumps(bundle));self.assertEqual(self.run_cli(*self.args(p)).returncode,2)

    def test_rejects_root_escape_duplicate_runs_and_output_collisions(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            p=self.build(Path(temporary));self.assertEqual(self.run_cli(*self.args(p),root=Path(temporary)).returncode,2)
            p=self.build(Path(temporary)/"runs");args=self.args(p);args[args.index("cand")]="base";self.assertEqual(self.run_cli(*args).returncode,2)
            p=self.build(Path(temporary)/"existing");p["output"].write_text("keep");self.assertEqual(self.run_cli(*self.args(p)).returncode,2);self.assertEqual(p["output"].read_text(),"keep")
            p=self.build(Path(temporary)/"report");p["output_report"].write_text("keep");self.assertEqual(self.run_cli(*self.args(p)).returncode,2)


if __name__ == "__main__": unittest.main()
