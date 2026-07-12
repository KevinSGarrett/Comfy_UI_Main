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
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_strict_audio_review_request.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_strict_audio_review_request.schema.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256(path)}


class StrictAudioRequestProducerTests(unittest.TestCase):
    def build_case(self, base: Path, *, synthetic: bool = True) -> dict[str, Path]:
        base.mkdir(parents=True, exist_ok=True)
        paths = {
            "mix_wav": base / "mix.wav",
            "wave30_event_manifest": base / "event.json",
            "wave30_mix_manifest": base / "mix.json",
            "wave30_qa_report": base / "qa.json",
            "prompt_reference": base / "prompt.json",
            "prompt_alignment_proof": base / "alignment.json",
            "optional_dir": base / "optional",
            "output": base / "request.json",
        }
        paths["mix_wav"].write_bytes(b"RIFF-audio")
        paths["optional_dir"].mkdir()
        identity = {"run_id": "run", "is_synthetic": synthetic}
        paths["wave30_event_manifest"].write_text(json.dumps({**identity, "audio_events": []}) + "\n", encoding="utf-8")
        event_link = link(paths["wave30_event_manifest"])
        mix = {
            **identity,
            "event_manifest_bindings": [event_link],
            "mixdown_artifact": {**link(paths["mix_wav"]), "bytes": paths["mix_wav"].stat().st_size},
        }
        paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
        qa = {
            **identity,
            "event_manifest_binding": event_link,
            "mix_manifest_binding": link(paths["wave30_mix_manifest"]),
        }
        paths["wave30_qa_report"].write_text(json.dumps(qa) + "\n", encoding="utf-8")
        prompt = {
            "schema_name": "wave64_prompt_reference",
            "prompt_kind": "speech",
            "expected_text": "hello",
            "expected_attributes": [{"name": "tone", "value": "calm"}],
            "video_pairing_required": False,
        }
        paths["prompt_reference"].write_text(json.dumps(prompt) + "\n", encoding="utf-8")
        alignment = {
            "schema_name": "wave64_prompt_alignment_proof",
            "proof_kind": "prompt_alignment",
            "audio_sha256": sha256(paths["mix_wav"]),
            "prompt_reference_sha256": sha256(paths["prompt_reference"]),
            "self_authorized": False,
            "is_synthetic": synthetic,
            "production_evidence": not synthetic,
        }
        paths["prompt_alignment_proof"].write_text(json.dumps(alignment) + "\n", encoding="utf-8")
        return paths

    def args(self, paths: dict[str, Path]) -> list[str]:
        result: list[str] = []
        for name in (
            "mix_wav", "wave30_event_manifest", "wave30_mix_manifest", "wave30_qa_report",
            "prompt_reference", "prompt_alignment_proof", "optional_dir", "output",
        ):
            result.extend((f"--{name.replace('_', '-')}", str(paths[name])))
        result.extend(("--run-id", "run"))
        return result

    def run_cli(self, *args: str, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_emits_schema_valid_request_without_optional_authority(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            result = self.run_cli(*self.args(paths))
            self.assertEqual(result.returncode, 0, result.stdout)
            request = json.loads(paths["output"].read_text(encoding="utf-8"))
            Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(request)
            self.assertTrue(request["is_synthetic"])
            self.assertTrue(all(field not in request for field in (
                "playback_proof_binding", "row030_av_sync_report_binding", "production_review_bundle_binding"
            )))

    def test_rejects_wave30_identity_and_cross_binding_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            event = json.loads(paths["wave30_event_manifest"].read_text(encoding="utf-8"))
            event["run_id"] = "wrong"
            paths["wave30_event_manifest"].write_text(json.dumps(event) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "event-link")
            mix = json.loads(paths["wave30_mix_manifest"].read_text(encoding="utf-8"))
            mix["event_manifest_bindings"][0]["sha256"] = "0" * 64
            paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "qa-link")
            qa = json.loads(paths["wave30_qa_report"].read_text(encoding="utf-8"))
            qa["mix_manifest_binding"]["sha256"] = "0" * 64
            paths["wave30_qa_report"].write_text(json.dumps(qa) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_mixdown_and_prompt_alignment_lineage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            mix = json.loads(paths["wave30_mix_manifest"].read_text(encoding="utf-8"))
            mix["mixdown_artifact"]["sha256"] = "0" * 64
            paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "bytes")
            mix = json.loads(paths["wave30_mix_manifest"].read_text(encoding="utf-8"))
            mix["mixdown_artifact"]["bytes"] += 1
            paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            for field in ("audio_sha256", "prompt_reference_sha256"):
                paths = self.build_case(Path(temporary) / field)
                alignment = json.loads(paths["prompt_alignment_proof"].read_text(encoding="utf-8"))
                alignment[field] = "0" * 64
                paths["prompt_alignment_proof"].write_text(json.dumps(alignment) + "\n", encoding="utf-8")
                self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_prompt_role_and_self_authorization(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            alignment = json.loads(paths["prompt_alignment_proof"].read_text(encoding="utf-8"))
            alignment["proof_kind"] = "playback_review"
            paths["prompt_alignment_proof"].write_text(json.dumps(alignment) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "self")
            alignment = json.loads(paths["prompt_alignment_proof"].read_text(encoding="utf-8"))
            alignment["self_authorized"] = True
            paths["prompt_alignment_proof"].write_text(json.dumps(alignment) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_binds_valid_playback_and_rejects_role_confusion(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            proof = {
                "schema_name": "wave64_playback_review_proof",
                "proof_kind": "playback_review",
                "audio_sha256": sha256(paths["mix_wav"]),
                "is_synthetic": True,
                "production_evidence": False,
                "self_authorized": False,
            }
            proof_path = paths["optional_dir"] / "playback_proof.json"
            proof_path.write_text(json.dumps(proof) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 0)
            paths = self.build_case(Path(temporary) / "bad")
            proof["proof_kind"] = "prompt_alignment"
            (paths["optional_dir"] / "playback_proof.json").write_text(json.dumps(proof) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "self-authorized")
            proof.update({"proof_kind": "playback_review", "audio_sha256": sha256(paths["mix_wav"]), "self_authorized": True})
            (paths["optional_dir"] / "playback_proof.json").write_text(json.dumps(proof) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_binds_valid_row030_and_production_bundle_and_relabel_mode(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            row030 = {
                "schema_name": "wave64_av_sync_certification_report",
                "artifact_bindings": {
                    "source_audio_mix_artifact": {
                        "path": str(paths["mix_wav"].resolve()),
                        "sha256": sha256(paths["mix_wav"]),
                        "bytes": paths["mix_wav"].stat().st_size,
                    }
                },
            }
            bundle = {"schema_name": "wave64_production_review_bundle", "proof_kind": "production_review"}
            (paths["optional_dir"] / "row030_av_sync_report.json").write_text(json.dumps(row030) + "\n", encoding="utf-8")
            (paths["optional_dir"] / "production_review_bundle.json").write_text(json.dumps(bundle) + "\n", encoding="utf-8")
            result = self.run_cli(*self.args(paths), "--capture-mode", "hand_authored_relabel")
            self.assertEqual(result.returncode, 0, result.stdout)
            request = json.loads(paths["output"].read_text(encoding="utf-8"))
            self.assertEqual(request["capture_mode"], "hand_authored_relabel")
            self.assertIn("row030_av_sync_report_binding", request)
            self.assertIn("production_review_bundle_binding", request)

    def test_production_flag_requires_non_synthetic_production_prompt_proof(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary), synthetic=False)
            result = self.run_cli(*self.args(paths), "--production-input")
            self.assertEqual(result.returncode, 0, result.stdout)
            alignment = json.loads(paths["prompt_alignment_proof"].read_text(encoding="utf-8"))
            alignment["production_evidence"] = False
            paths["prompt_alignment_proof"].write_text(json.dumps(alignment) + "\n", encoding="utf-8")
            paths["output"].unlink()
            self.assertEqual(self.run_cli(*self.args(paths), "--production-input").returncode, 2)

    def test_rejects_invalid_row030_and_production_bundle_roles(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            (paths["optional_dir"] / "row030_av_sync_report.json").write_text(
                json.dumps({"schema_name": "wrong"}) + "\n", encoding="utf-8"
            )
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "bundle")
            (paths["optional_dir"] / "production_review_bundle.json").write_text(
                json.dumps({"schema_name": "wave64_production_review_bundle", "proof_kind": "wrong"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_root_escape_duplicate_and_existing_or_optional_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            self.assertEqual(self.run_cli(*self.args(paths), root=Path(temporary)).returncode, 2)
            paths["prompt_reference"] = paths["wave30_event_manifest"]
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "existing")
            paths["output"].write_text("keep", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertEqual(paths["output"].read_text(encoding="utf-8"), "keep")
            paths = self.build_case(Path(temporary) / "optional")
            paths["output"] = paths["optional_dir"] / "playback_proof.json"
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertFalse(paths["output"].exists())


if __name__ == "__main__":
    unittest.main()
