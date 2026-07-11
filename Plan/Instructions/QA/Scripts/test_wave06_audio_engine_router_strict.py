#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None


REPO_ROOT = Path(__file__).resolve().parents[4]
ROUTER_SCRIPT = REPO_ROOT / "Plan/07_IMPLEMENTATION/scripts/route_wave06_audio_engine.py"
REQUEST_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave06_audio_engine_route_request.schema.json"
DECISION_SCHEMA_PATH = REPO_ROOT / "Plan/08_SCHEMAS/wave06_audio_engine_route_decision.schema.json"
ROUTE_TYPES = [
    "dialogue_voice",
    "breath_body_effort",
    "foley_contact_fabric",
    "ambience_room_tone",
    "music",
    "synchronized_av",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _constraints_hash(request: dict[str, Any]) -> str:
    payload = {
        "output_type": request["output_type"],
        "route_type": request["route_type"],
        "duration_seconds": float(request["duration_seconds"]),
        "sample_rate_hz": request["sample_rate_hz"],
        "channels": request["channels"],
        "channel_layout": request["channel_layout"],
        "target_output": request["target_output"],
        "target_container": request["target_container"],
        "usage_scope": request["usage_scope"],
        "physical_action_present": request["physical_action_present"],
        "aligned_audio_event_present": request["aligned_audio_event_present"],
        "is_synthetic": request["is_synthetic"],
        "preferred_engine_id": request.get("preferred_engine_id"),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _build_request() -> dict[str, Any]:
    return {
        "output_type": "audio",
        "route_type": "dialogue_voice",
        "duration_seconds": 2.5,
        "sample_rate_hz": 48000,
        "channels": 2,
        "channel_layout": "stereo",
        "target_output": "wav",
        "target_container": "wav",
        "usage_scope": "internal_eval",
        "physical_action_present": False,
        "aligned_audio_event_present": True,
        "is_synthetic": False,
        "proof_bindings": {
            "capability": {"path": "placeholder", "sha256": "0" * 64},
            "license": {"path": "placeholder", "sha256": "0" * 64},
            "asset": {"path": "placeholder", "sha256": "0" * 64},
            "runtime": {"path": "placeholder", "sha256": "0" * 64},
            "qa": {"path": "placeholder", "sha256": "0" * 64},
        },
    }


def _build_proofs(request: dict[str, Any], tmpdir: Path, *, engine_id: str = "ltx2_audio_video") -> dict[str, Path]:
    constraints_hash = _constraints_hash(request)
    artifacts_dir = tmpdir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    license_artifact = artifacts_dir / "license.txt"
    license_artifact.write_text("LTX2 evaluation license terms\n", encoding="utf-8")
    asset_bundle = artifacts_dir / "asset_bundle.bin"
    asset_bundle.write_bytes(b"ltx2 bundle bytes")

    paths = {
        "capability": tmpdir / "capability.json",
        "license": tmpdir / "license.json",
        "asset": tmpdir / "asset.json",
        "runtime": tmpdir / "runtime.json",
        "qa": tmpdir / "qa.json",
    }

    capability = {
        "proof_kind": "capability",
        "engine_id": engine_id,
        "constraints_hash": constraints_hash,
        "verified_route_types": list(ROUTE_TYPES),
        "duration_seconds": {"min": 0.25, "max": 30.0},
        "sample_rates_hz": [44100, 48000],
        "channels": [1, 2],
        "channel_layouts": ["mono", "stereo"],
        "output_targets": ["wav", "flac", "aac", "pcm"],
        "container_formats": ["wav", "flac", "mp4"],
    }
    license_payload = {
        "proof_kind": "license",
        "engine_id": engine_id,
        "constraints_hash": constraints_hash,
        "license_id": "LTX2-EVAL-001",
        "license_artifact_path": str(license_artifact.relative_to(REPO_ROOT)),
        "license_artifact_sha256": _sha256(license_artifact),
        "allowed_usage_scopes": ["internal_eval", "client_preview"],
    }
    asset_payload = {
        "proof_kind": "asset",
        "engine_id": engine_id,
        "constraints_hash": constraints_hash,
        "asset_bundle_id": "ltx2-bundle-001",
        "asset_bundle_path": str(asset_bundle.relative_to(REPO_ROOT)),
        "asset_bundle_bytes": asset_bundle.stat().st_size,
        "asset_bundle_sha256": _sha256(asset_bundle),
        "install_state": "installed",
        "runtime_state": "ready",
    }
    runtime_payload = {
        "proof_kind": "runtime",
        "engine_id": engine_id,
        "constraints_hash": constraints_hash,
        "asset_bundle_id": asset_payload["asset_bundle_id"],
        "asset_bundle_sha256": asset_payload["asset_bundle_sha256"],
        "tested_duration_seconds": 3.0,
        "tested_sample_rate_hz": 48000,
        "tested_channels": 2,
        "tested_channel_layout": "stereo",
        "tested_output_target": "wav",
        "tested_container": "wav",
        "execution_passed": True,
    }
    _write_json(paths["runtime"], runtime_payload)
    qa_payload = {
        "proof_kind": "qa",
        "engine_id": engine_id,
        "constraints_hash": constraints_hash,
        "runtime_proof_sha256": _sha256(paths["runtime"]),
        "decode_passed": True,
        "duration_passed": True,
        "loudness_passed": True,
        "clipping_passed": True,
        "sync_passed": True,
        "route_review_passed": True,
    }
    _write_json(paths["capability"], capability)
    _write_json(paths["license"], license_payload)
    _write_json(paths["asset"], asset_payload)
    _write_json(paths["qa"], qa_payload)
    return paths


def _bind_request_to_proofs(request: dict[str, Any], proofs: dict[str, Path]) -> None:
    for proof_kind, proof_path in proofs.items():
        request["proof_bindings"][proof_kind]["path"] = str(proof_path)
        request["proof_bindings"][proof_kind]["sha256"] = _sha256(proof_path)


def _run_router(*, request_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROUTER_SCRIPT),
            "--root",
            str(REPO_ROOT),
            "--request",
            str(request_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class Wave06AudioEngineRouterStrictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("wave06_router_module", ROUTER_SCRIPT)
        if spec is None or spec.loader is None:
            raise RuntimeError("failed to import router script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.router_module = module
        cls.request_schema = json.loads(REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.decision_schema = json.loads(DECISION_SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_all_route_types_are_taxonomically_accepted(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            for route_type in ROUTE_TYPES:
                request = _build_request()
                request["route_type"] = route_type
                request["is_synthetic"] = True
                proofs = _build_proofs(request, tmpdir / route_type)
                _bind_request_to_proofs(request, proofs)
                request_path = tmpdir / f"request_{route_type}.json"
                output_path = tmpdir / f"decision_{route_type}.json"
                _write_json(request_path, request)
                result = _run_router(request_path=request_path, output_path=output_path)
                self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
                decision = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(decision["route_type"], route_type)
                self.assertIn("synthetic_input_no_engine_selection", decision["blockers"])

    def test_current_authority_prefilter_only_discovers_ltx2_candidate(self) -> None:
        request = _build_request()
        proofs = {
            "capability": {"path": "/tmp/missing_capability.json", "sha256": "0" * 64},
            "license": {"path": "/tmp/missing_license.json", "sha256": "0" * 64},
            "asset": {"path": "/tmp/missing_asset.json", "sha256": "0" * 64},
            "runtime": {"path": "/tmp/missing_runtime.json", "sha256": "0" * 64},
            "qa": {"path": "/tmp/missing_qa.json", "sha256": "0" * 64},
        }
        request["proof_bindings"] = proofs
        code, decision = self.router_module.route_request(REPO_ROOT, request)
        self.assertEqual(code, 2)
        self.assertEqual(decision["evaluated_candidates"], ["ltx2_audio_video"])

    def test_non_audio_engine_preference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            request["preferred_engine_id"] = "wan22_video"
            proofs = _build_proofs(request, tmpdir)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request.json"
            output_path = tmpdir / "decision.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("preferred_engine_not_audio_capable", decision["blockers"])
            self.assertIsNone(decision["selected_engine_id"])

    def test_missing_each_proof_class_blocks_with_specific_code(self) -> None:
        for missing_kind in ("capability", "license", "asset", "runtime", "qa"):
            with self.subTest(missing_kind=missing_kind):
                with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
                    tmpdir = Path(tmp)
                    request = _build_request()
                    proofs = _build_proofs(request, tmpdir)
                    _bind_request_to_proofs(request, proofs)
                    proofs[missing_kind].unlink()
                    request_path = tmpdir / "request.json"
                    output_path = tmpdir / "decision.json"
                    _write_json(request_path, request)
                    result = _run_router(request_path=request_path, output_path=output_path)
                    self.assertEqual(result.returncode, 2)
                    decision = json.loads(output_path.read_text(encoding="utf-8"))
                    self.assertIn(f"missing_{missing_kind}_proof", decision["blockers"])

    def test_fake_boolean_proof_and_malformed_proof_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            proofs = _build_proofs(request, tmpdir)
            proofs["runtime"].write_text("true\n", encoding="utf-8")
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request.json"
            output_path = tmpdir / "decision.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("malformed_runtime_proof", decision["blockers"])

    def test_strict_proof_types_and_artifact_bindings(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "false_string")
            runtime_payload = json.loads(proofs["runtime"].read_text(encoding="utf-8"))
            runtime_payload["execution_passed"] = "false"
            _write_json(proofs["runtime"], runtime_payload)
            qa_payload = json.loads(proofs["qa"].read_text(encoding="utf-8"))
            qa_payload["runtime_proof_sha256"] = _sha256(proofs["runtime"])
            _write_json(proofs["qa"], qa_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_false_string.json"
            output_path = tmpdir / "decision_false_string.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("malformed_runtime_execution_passed", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "numeric_strings")
            runtime_payload = json.loads(proofs["runtime"].read_text(encoding="utf-8"))
            runtime_payload["tested_duration_seconds"] = "3.0"
            _write_json(proofs["runtime"], runtime_payload)
            qa_payload = json.loads(proofs["qa"].read_text(encoding="utf-8"))
            qa_payload["runtime_proof_sha256"] = _sha256(proofs["runtime"])
            _write_json(proofs["qa"], qa_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_numeric_strings.json"
            output_path = tmpdir / "decision_numeric_strings.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("malformed_runtime_tested_duration_seconds", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "non_list_fields")
            capability_payload = json.loads(proofs["capability"].read_text(encoding="utf-8"))
            capability_payload["sample_rates_hz"] = 48000
            _write_json(proofs["capability"], capability_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_non_list_fields.json"
            output_path = tmpdir / "decision_non_list_fields.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("malformed_capability_sample_rates", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "bad_hash")
            request["proof_bindings"]["license"]["sha256"] = "ABCDEF" * 10 + "abcd"
            request_path = tmpdir / "request_bad_hash.json"
            output_path = tmpdir / "decision_bad_hash.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output_path.exists())

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "missing_license_artifact")
            license_payload = json.loads(proofs["license"].read_text(encoding="utf-8"))
            license_path = (REPO_ROOT / license_payload["license_artifact_path"]).resolve()
            license_path.unlink()
            _write_json(proofs["license"], license_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_missing_license_artifact.json"
            output_path = tmpdir / "decision_missing_license_artifact.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("missing_license_artifact", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "mismatch_license_artifact")
            license_payload = json.loads(proofs["license"].read_text(encoding="utf-8"))
            license_payload["license_artifact_sha256"] = "f" * 64
            _write_json(proofs["license"], license_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_mismatch_license_artifact.json"
            output_path = tmpdir / "decision_mismatch_license_artifact.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("license_artifact_sha256_mismatch", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "missing_asset_bundle")
            asset_payload = json.loads(proofs["asset"].read_text(encoding="utf-8"))
            bundle_path = (REPO_ROOT / asset_payload["asset_bundle_path"]).resolve()
            bundle_path.unlink()
            _write_json(proofs["asset"], asset_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_missing_asset_bundle.json"
            output_path = tmpdir / "decision_missing_asset_bundle.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("missing_asset_bundle_artifact", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "asset_bytes_mismatch")
            asset_payload = json.loads(proofs["asset"].read_text(encoding="utf-8"))
            asset_payload["asset_bundle_bytes"] = asset_payload["asset_bundle_bytes"] + 1
            _write_json(proofs["asset"], asset_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_asset_bytes_mismatch.json"
            output_path = tmpdir / "decision_asset_bytes_mismatch.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("asset_bundle_bytes_mismatch", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "asset_sha_mismatch")
            asset_payload = json.loads(proofs["asset"].read_text(encoding="utf-8"))
            asset_payload["asset_bundle_sha256"] = "e" * 64
            _write_json(proofs["asset"], asset_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_asset_sha_mismatch.json"
            output_path = tmpdir / "decision_asset_sha_mismatch.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("asset_bundle_sha256_mismatch", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "runtime_asset_sha_mismatch")
            runtime_payload = json.loads(proofs["runtime"].read_text(encoding="utf-8"))
            runtime_payload["asset_bundle_sha256"] = "d" * 64
            _write_json(proofs["runtime"], runtime_payload)
            qa_payload = json.loads(proofs["qa"].read_text(encoding="utf-8"))
            qa_payload["runtime_proof_sha256"] = _sha256(proofs["runtime"])
            _write_json(proofs["qa"], qa_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_runtime_asset_sha_mismatch.json"
            output_path = tmpdir / "decision_runtime_asset_sha_mismatch.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("runtime_asset_bundle_sha256_mismatch", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "qa_runtime_hash_mismatch")
            qa_payload = json.loads(proofs["qa"].read_text(encoding="utf-8"))
            qa_payload["runtime_proof_sha256"] = "9" * 64
            _write_json(proofs["qa"], qa_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_qa_runtime_hash_mismatch.json"
            output_path = tmpdir / "decision_qa_runtime_hash_mismatch.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("qa_runtime_hash_mismatch", decision["blockers"])
            self.assertIn("engine_promotion_status_not_approved", decision["blockers"])

    def test_unknown_proof_keys_hash_mismatch_and_constraint_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            proofs = _build_proofs(request, tmpdir)
            runtime_payload = json.loads(proofs["runtime"].read_text(encoding="utf-8"))
            runtime_payload["extra_key"] = True
            _write_json(proofs["runtime"], runtime_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_unknown_keys.json"
            output_path = tmpdir / "decision_unknown_keys.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("unknown_runtime_proof_keys", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "hash_case")
            _bind_request_to_proofs(request, proofs)
            request["proof_bindings"]["runtime"]["sha256"] = "f" * 64
            request_path = tmpdir / "request_hash_mismatch.json"
            output_path = tmpdir / "decision_hash_mismatch.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("runtime_proof_hash_mismatch", decision["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "constraints_case")
            runtime_payload = json.loads(proofs["runtime"].read_text(encoding="utf-8"))
            runtime_payload["constraints_hash"] = "f" * 64
            _write_json(proofs["runtime"], runtime_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_constraints_mismatch.json"
            output_path = tmpdir / "decision_constraints_mismatch.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("runtime_proof_constraints_hash_mismatch", decision["blockers"])

    def test_unsupported_duration_sample_rate_channels_output_and_usage_scope(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            proofs = _build_proofs(request, tmpdir)
            capability = json.loads(proofs["capability"].read_text(encoding="utf-8"))
            capability["duration_seconds"] = {"min": 10.0, "max": 11.0}
            _write_json(proofs["capability"], capability)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_duration.json"
            output_path = tmpdir / "decision_duration.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unsupported_duration", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "sample")
            capability = json.loads(proofs["capability"].read_text(encoding="utf-8"))
            capability["sample_rates_hz"] = [44100]
            _write_json(proofs["capability"], capability)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_sample.json"
            output_path = tmpdir / "decision_sample.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("unsupported_sample_rate", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "channels")
            capability = json.loads(proofs["capability"].read_text(encoding="utf-8"))
            capability["channels"] = [1]
            _write_json(proofs["capability"], capability)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_channels.json"
            output_path = tmpdir / "decision_channels.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("unsupported_channels", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "output")
            capability = json.loads(proofs["capability"].read_text(encoding="utf-8"))
            capability["output_targets"] = ["flac"]
            _write_json(proofs["capability"], capability)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_output.json"
            output_path = tmpdir / "decision_output.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("unsupported_output_target", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "scope")
            license_payload = json.loads(proofs["license"].read_text(encoding="utf-8"))
            license_payload["allowed_usage_scopes"] = ["client_preview"]
            _write_json(proofs["license"], license_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_scope.json"
            output_path = tmpdir / "decision_scope.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("unsupported_usage_scope", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

    def test_asset_runtime_and_qa_mismatch_block(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            proofs = _build_proofs(request, tmpdir)
            asset = json.loads(proofs["asset"].read_text(encoding="utf-8"))
            asset["runtime_state"] = "not_ready"
            _write_json(proofs["asset"], asset)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_asset.json"
            output_path = tmpdir / "decision_asset.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("asset_runtime_state_mismatch", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "runtime")
            runtime_payload = json.loads(proofs["runtime"].read_text(encoding="utf-8"))
            runtime_payload["tested_sample_rate_hz"] = 44100
            _write_json(proofs["runtime"], runtime_payload)
            qa_payload = json.loads(proofs["qa"].read_text(encoding="utf-8"))
            qa_payload["runtime_proof_sha256"] = _sha256(proofs["runtime"])
            _write_json(proofs["qa"], qa_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_runtime.json"
            output_path = tmpdir / "decision_runtime.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("runtime_sample_rate_mismatch", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

            request = _build_request()
            proofs = _build_proofs(request, tmpdir / "qa")
            qa_payload = json.loads(proofs["qa"].read_text(encoding="utf-8"))
            qa_payload["decode_passed"] = False
            _write_json(proofs["qa"], qa_payload)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request_qa.json"
            output_path = tmpdir / "decision_qa.json"
            _write_json(request_path, request)
            _run_router(request_path=request_path, output_path=output_path)
            self.assertIn("qa_gate_failed", json.loads(output_path.read_text(encoding="utf-8"))["blockers"])

    def test_physical_action_without_aligned_audio_is_always_blocked(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            request["physical_action_present"] = True
            request["aligned_audio_event_present"] = False
            proofs = _build_proofs(request, tmpdir)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request.json"
            output_path = tmpdir / "decision.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("missing_aligned_audio_event", decision["blockers"])
            self.assertTrue(decision["block_final_av_promotion"])

    def test_unknown_taxonomy_and_nonfinite_numbers_fail_with_exit_code_1(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            request["route_type"] = "unknown_taxonomy"
            proofs = _build_proofs(request, tmpdir)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "bad_taxonomy.json"
            output_path = tmpdir / "decision_taxonomy.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output_path.exists())

            nonfinite_path = tmpdir / "bad_nonfinite.json"
            nonfinite_path.write_text(
                '{"output_type":"audio","route_type":"dialogue_voice","duration_seconds":NaN,'
                '"sample_rate_hz":48000,"channels":2,"channel_layout":"stereo","target_output":"wav",'
                '"target_container":"wav","usage_scope":"internal_eval","physical_action_present":false,'
                '"aligned_audio_event_present":true,"is_synthetic":false,'
                '"proof_bindings":{"capability":{"path":"x","sha256":"'
                + ("0" * 64)
                + '"},"license":{"path":"x","sha256":"'
                + ("0" * 64)
                + '"},"asset":{"path":"x","sha256":"'
                + ("0" * 64)
                + '"},"runtime":{"path":"x","sha256":"'
                + ("0" * 64)
                + '"},"qa":{"path":"x","sha256":"'
                + ("0" * 64)
                + '"}}}',
                encoding="utf-8",
            )
            result = _run_router(request_path=nonfinite_path, output_path=tmpdir / "decision_nonfinite.json")
            self.assertEqual(result.returncode, 1)

            inf_path = tmpdir / "bad_infinite.json"
            inf_path.write_text(nonfinite_path.read_text(encoding="utf-8").replace("NaN", "Infinity"), encoding="utf-8")
            result = _run_router(request_path=inf_path, output_path=tmpdir / "decision_infinite.json")
            self.assertEqual(result.returncode, 1)

    def test_invalid_request_does_not_replace_existing_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            existing_output = tmpdir / "decision.json"
            _write_json(existing_output, {"existing": True})
            bad_request = tmpdir / "bad_request.json"
            bad_request.write_text("{}", encoding="utf-8")
            result = _run_router(request_path=bad_request, output_path=existing_output)
            self.assertEqual(result.returncode, 1)
            observed = json.loads(existing_output.read_text(encoding="utf-8"))
            self.assertEqual(observed, {"existing": True})

    def test_synthetic_request_never_selects_engine(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmpdir = Path(tmp)
            request = _build_request()
            request["is_synthetic"] = True
            request["output_type"] = "av"
            proofs = _build_proofs(request, tmpdir)
            _bind_request_to_proofs(request, proofs)
            request_path = tmpdir / "request.json"
            output_path = tmpdir / "decision.json"
            _write_json(request_path, request)
            result = _run_router(request_path=request_path, output_path=output_path)
            self.assertEqual(result.returncode, 2)
            decision = json.loads(output_path.read_text(encoding="utf-8"))
            if jsonschema is not None:
                jsonschema.validate(instance=decision, schema=self.decision_schema)
            self.assertIsNone(decision["selected_engine_id"])
            self.assertEqual(decision["route_mode"], "silent_video_plus_audio_plan_manifest")
            self.assertIn("synthetic_input_no_engine_selection", decision["blockers"])
            self.assertEqual(set(decision["required_next_proofs"]), {"capability", "license", "asset", "runtime", "qa"})

    def test_request_schema_and_decision_schema_contradiction_rejection(self) -> None:
        if jsonschema is None:
            self.skipTest("jsonschema is unavailable")

        good_request = _build_request()
        jsonschema.validate(instance=good_request, schema=self.request_schema)

        bad_request = dict(good_request)
        bad_request["extra_field"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad_request, schema=self.request_schema)

        contradictory = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "decision_version": 1,
            "output_type": "audio",
            "route_type": "dialogue_voice",
            "request_constraints_hash": "a" * 64,
            "selected_engine_id": None,
            "route_mode": "audio_engine_selected",
            "block_final_av_promotion": False,
            "is_synthetic": False,
            "blockers": [],
            "required_next_proofs": [],
            "evaluated_candidates": ["ltx2_audio_video"],
            "authority_bindings": {
                "registry_sha256": "b" * 64,
                "matrix_sha256": "c" * 64,
                "rules_sha256": "d" * 64,
                "notes_sha256": "e" * 64,
            },
            "proof_evaluation": {
                "capability": "pass",
                "license": "pass",
                "asset": "pass",
                "runtime": "pass",
                "qa": "pass",
            },
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=contradictory, schema=self.decision_schema)


if __name__ == "__main__":
    unittest.main()
