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
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/produce_wave64_av_sync_measurement_packet.py"
SCHEMA = ROOT / "Plan/08_SCHEMAS/wave64_av_sync_measurement_packet.schema.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AvSyncPacketProducerTests(unittest.TestCase):
    def build_case(self, base: Path, *, synthetic: bool = True) -> dict[str, Path]:
        base.mkdir(parents=True, exist_ok=True)
        paths = {
            "source_video": base / "source.mkv",
            "source_audio_mix": base / "source.wav",
            "final_mux": base / "final.mkv",
            "wave30_event_manifest": base / "event.json",
            "wave30_mix_manifest": base / "mix.json",
            "anchor_measurement_proof": base / "anchor.json",
            "optional_dir": base / "optional",
            "output": base / "packet.json",
        }
        paths["source_video"].write_bytes(b"source-video")
        paths["source_audio_mix"].write_bytes(b"source-audio")
        paths["final_mux"].write_bytes(b"final-mux")
        paths["optional_dir"].mkdir()
        identity = {"run_id": "run", "scene_id": "scene", "shot_id": "shot", "is_synthetic": synthetic}
        event = {"schema_name": "wave30_audio_event_manifest", **identity}
        paths["wave30_event_manifest"].write_text(json.dumps(event) + "\n", encoding="utf-8")
        event_binding = {"path": str(paths["wave30_event_manifest"].resolve()), "sha256": sha256(paths["wave30_event_manifest"])}
        mix = {
            "schema_name": "wave30_audio_mix_manifest",
            **identity,
            "event_manifest_bindings": [event_binding],
            "mixdown_artifact": {
                "path": str(paths["source_audio_mix"].resolve()),
                "sha256": sha256(paths["source_audio_mix"]),
                "bytes": paths["source_audio_mix"].stat().st_size,
            },
        }
        paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
        origin = "synthetic_fixture" if synthetic else "technical_capture"
        anchor = {
            "schema_name": "wave64_av_sync_anchor_measurement_proof",
            "proof_kind": "anchor_measurement",
            **identity,
            "take_id": "take",
            "evidence_origin": origin,
            "source_video_sha256": sha256(paths["source_video"]),
            "source_audio_sha256": sha256(paths["source_audio_mix"]),
            "mux_sha256": sha256(paths["final_mux"]),
        }
        paths["anchor_measurement_proof"].write_text(json.dumps(anchor) + "\n", encoding="utf-8")
        return paths

    def args(self, paths: dict[str, Path]) -> list[str]:
        result: list[str] = []
        for name in (
            "source_video", "source_audio_mix", "final_mux", "wave30_event_manifest",
            "wave30_mix_manifest", "anchor_measurement_proof", "optional_dir", "output",
        ):
            result.extend((f"--{name.replace('_', '-')}", str(paths[name])))
        result.extend(("--run-id", "run", "--scene-id", "scene", "--shot-id", "shot", "--take-id", "take"))
        return result

    def run_cli(self, *args: str, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_emits_schema_valid_fail_closed_packet_with_null_optionals(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            result = self.run_cli(*self.args(paths))
            self.assertEqual(result.returncode, 0, result.stdout)
            packet = json.loads(paths["output"].read_text(encoding="utf-8"))
            Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(packet)
            self.assertFalse(packet["caller_claimed_overall_pass"])
            self.assertTrue(packet["is_synthetic"])
            self.assertTrue(all(packet[field] is None for field in (
                "playback_proof_binding", "runtime_proof_binding", "production_certification_bundle_binding"
            )))

    def test_binds_identity_and_lineage_valid_optional_proofs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            anchor_sha = sha256(paths["anchor_measurement_proof"])
            identity = {
                "run_id": "run", "scene_id": "scene", "shot_id": "shot", "take_id": "take",
                "is_synthetic": True, "evidence_origin": "synthetic_fixture",
                "source_video_sha256": sha256(paths["source_video"]),
                "source_audio_sha256": sha256(paths["source_audio_mix"]),
                "mux_sha256": sha256(paths["final_mux"]), "measurement_proof_sha256": anchor_sha,
            }
            optional = paths["optional_dir"]
            playback = {
                **identity,
                "schema_name": "wave64_av_sync_playback_proof",
                "proof_kind": "av_sync_playback_review",
            }
            runtime = {
                **identity,
                "schema_name": "wave64_production_runtime_proof",
                "proof_kind": "production_runtime",
            }
            (optional / "playback_proof.json").write_text(json.dumps(playback) + "\n", encoding="utf-8")
            (optional / "runtime_proof.json").write_text(json.dumps(runtime) + "\n", encoding="utf-8")
            bundle = {
                **identity,
                "schema_name": "wave64_av_sync_production_authority_bundle",
                "proof_kind": "production_av_sync_authority",
                "playback_proof_sha256": sha256(optional / "playback_proof.json"),
                "runtime_proof_sha256": sha256(optional / "runtime_proof.json"),
            }
            (optional / "production_certification_bundle.json").write_text(json.dumps(bundle) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 0)
            packet = json.loads(paths["output"].read_text(encoding="utf-8"))
            self.assertEqual(packet["runtime_proof_binding"]["sha256"], sha256(optional / "runtime_proof.json"))

    def test_rejects_manifest_identity_and_mix_lineage_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            event = json.loads(paths["wave30_event_manifest"].read_text(encoding="utf-8"))
            event["scene_id"] = "wrong"
            paths["wave30_event_manifest"].write_text(json.dumps(event) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "lineage")
            mix = json.loads(paths["wave30_mix_manifest"].read_text(encoding="utf-8"))
            mix["mixdown_artifact"]["sha256"] = "0" * 64
            paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "event-binding")
            mix = json.loads(paths["wave30_mix_manifest"].read_text(encoding="utf-8"))
            mix["event_manifest_bindings"][0]["sha256"] = "0" * 64
            paths["wave30_mix_manifest"].write_text(json.dumps(mix) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_anchor_identity_kind_and_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            anchor = json.loads(paths["anchor_measurement_proof"].read_text(encoding="utf-8"))
            anchor["take_id"] = "wrong"
            paths["anchor_measurement_proof"].write_text(json.dumps(anchor) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "kind")
            anchor = json.loads(paths["anchor_measurement_proof"].read_text(encoding="utf-8"))
            anchor["proof_kind"] = "wrong"
            paths["anchor_measurement_proof"].write_text(json.dumps(anchor) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "hash")
            anchor = json.loads(paths["anchor_measurement_proof"].read_text(encoding="utf-8"))
            anchor["mux_sha256"] = "0" * 64
            paths["anchor_measurement_proof"].write_text(json.dumps(anchor) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_malformed_or_lineage_invalid_optional_proof(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            proof = paths["optional_dir"] / "runtime_proof.json"
            proof.write_text("[]\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            proof.write_text(json.dumps({"run_id": "wrong"}) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_optional_role_and_measurement_hash_confusion(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            anchor = json.loads(paths["anchor_measurement_proof"].read_text(encoding="utf-8"))
            proof = {
                **anchor,
                "schema_name": "wave64_av_sync_playback_proof",
                "proof_kind": "production_runtime",
                "measurement_proof_sha256": sha256(paths["anchor_measurement_proof"]),
            }
            runtime_path = paths["optional_dir"] / "runtime_proof.json"
            runtime_path.write_text(json.dumps(proof) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            proof["schema_name"] = "wave64_production_runtime_proof"
            proof["measurement_proof_sha256"] = "0" * 64
            runtime_path.write_text(json.dumps(proof) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_production_bundle_without_both_independent_proofs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            anchor = json.loads(paths["anchor_measurement_proof"].read_text(encoding="utf-8"))
            bundle = {
                **anchor,
                "schema_name": "wave64_av_sync_production_authority_bundle",
                "proof_kind": "production_av_sync_authority",
                "measurement_proof_sha256": sha256(paths["anchor_measurement_proof"]),
            }
            (paths["optional_dir"] / "production_certification_bundle.json").write_text(
                json.dumps(bundle) + "\n", encoding="utf-8"
            )
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_rejects_bundle_hashes_that_do_not_match_present_proof_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            anchor = json.loads(paths["anchor_measurement_proof"].read_text(encoding="utf-8"))
            anchor_sha = sha256(paths["anchor_measurement_proof"])
            optional = paths["optional_dir"]
            playback = {
                **anchor,
                "schema_name": "wave64_av_sync_playback_proof",
                "proof_kind": "av_sync_playback_review",
                "measurement_proof_sha256": anchor_sha,
            }
            runtime = {
                **anchor,
                "schema_name": "wave64_production_runtime_proof",
                "proof_kind": "production_runtime",
                "measurement_proof_sha256": anchor_sha,
            }
            (optional / "playback_proof.json").write_text(json.dumps(playback) + "\n", encoding="utf-8")
            (optional / "runtime_proof.json").write_text(json.dumps(runtime) + "\n", encoding="utf-8")
            bundle = {
                **anchor,
                "schema_name": "wave64_av_sync_production_authority_bundle",
                "proof_kind": "production_av_sync_authority",
                "measurement_proof_sha256": anchor_sha,
                "playback_proof_sha256": "0" * 64,
                "runtime_proof_sha256": sha256(optional / "runtime_proof.json"),
            }
            (optional / "production_certification_bundle.json").write_text(json.dumps(bundle) + "\n", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)

    def test_production_flag_requires_non_synthetic_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary), synthetic=False)
            result = self.run_cli(*self.args(paths), "--production-input")
            self.assertEqual(result.returncode, 0, result.stdout)
            packet = json.loads(paths["output"].read_text(encoding="utf-8"))
            self.assertFalse(packet["is_synthetic"])
            self.assertEqual(packet["evidence_origin"], "technical_capture")

    def test_rejects_root_escape_duplicate_paths_and_existing_or_optional_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            paths = self.build_case(Path(temporary))
            self.assertEqual(self.run_cli(*self.args(paths), root=Path(temporary)).returncode, 2)
            paths["final_mux"] = paths["source_video"]
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            paths = self.build_case(Path(temporary) / "existing")
            paths["output"].write_text("keep", encoding="utf-8")
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertEqual(paths["output"].read_text(encoding="utf-8"), "keep")
            paths = self.build_case(Path(temporary) / "optional")
            paths["output"] = paths["optional_dir"] / "runtime_proof.json"
            self.assertEqual(self.run_cli(*self.args(paths)).returncode, 2)
            self.assertFalse(paths["output"].exists())


if __name__ == "__main__":
    unittest.main()
