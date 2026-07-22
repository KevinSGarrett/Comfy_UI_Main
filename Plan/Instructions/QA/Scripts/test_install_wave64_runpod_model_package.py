from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/install_wave64_runpod_model_package.py"
MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_runpod_qwen3_asr_17b_install_admission.json"
OMNI_MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_runpod_qwen3_omni_30b_a3b_thinking_install_admission.json"
ALIGNER_MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_wav2vec2_phoneme_aligner_install_admission.json"
ALIGNER_SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_wav2vec2_phoneme_aligner_install_admission.schema.json"
LATENTSYNC_MANIFEST = ROOT / "Plan/10_REGISTRIES/wave64_latentsync_1_6_install_admission.json"
LATENTSYNC_SCHEMA = ROOT / "Plan/08_SCHEMAS/runpod_autonomous_latentsync_1_6_install_admission.schema.json"
SPEC = importlib.util.spec_from_file_location("model_package_installer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture_manifest() -> tuple[dict, dict[str, bytes]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payloads: dict[str, bytes] = {}
    for index, record in enumerate(data["files"]):
        payload = f"fixture-{index}-{record['path']}".encode()
        payloads[record["path"]] = payload
        if record["identity_kind"] == "sha256":
            record["identity"] = hashlib.sha256(payload).hexdigest()
            record["bytes"] = len(payload)
        else:
            prefix = f"blob {len(payload)}\0".encode("ascii")
            record["identity"] = hashlib.sha1(prefix + payload).hexdigest()  # noqa: S324
    data["storage"]["weight_bytes"] = sum(
        record["bytes"] or 0 for record in data["files"] if record["identity_kind"] == "sha256"
    )
    data["storage"]["minimum_free_bytes_before_install"] = 1024
    return data, payloads


def fake_fetcher(payloads: dict[str, bytes], calls: list[str]):
    def fetch(url: str, destination: Path) -> None:
        name = urllib_name(url)
        calls.append(name)
        destination.write_bytes(payloads[name])

    return fetch


def urllib_name(url: str) -> str:
    from urllib.parse import unquote

    return unquote(url.split("/resolve/", 1)[1].split("/", 1)[1])


def test_atomic_install_and_verified_replay(tmp_path: Path) -> None:
    manifest, payloads = fixture_manifest()
    target = tmp_path / "published"
    calls: list[str] = []
    first = MODULE.install(
        manifest,
        target,
        fetch=fake_fetcher(payloads, calls),
        free_bytes=10_000,
        production_target=False,
    )
    assert first["replay"] == "NEW_ATOMIC_INSTALL"
    assert not (tmp_path / ".published.installing").exists()
    assert len(calls) == 12
    second = MODULE.install(
        manifest,
        target,
        fetch=fake_fetcher(payloads, calls),
        free_bytes=10_000,
        production_target=False,
    )
    assert second["replay"] == "REUSED_VERIFIED_INSTALL"
    assert len(calls) == 12
    assert not second["runtime_claims"]["model_loaded"]


def test_crash_resumes_verified_files_without_redownload(tmp_path: Path) -> None:
    manifest, payloads = fixture_manifest()
    target = tmp_path / "published"
    calls: list[str] = []
    with pytest.raises(MODULE.InstallError, match="injected crash"):
        MODULE.install(
            manifest,
            target,
            fetch=fake_fetcher(payloads, calls),
            free_bytes=10_000,
            production_target=False,
            crash_after_files=4,
        )
    assert len(calls) == 4
    result = MODULE.install(
        manifest,
        target,
        fetch=fake_fetcher(payloads, calls),
        free_bytes=10_000,
        production_target=False,
    )
    assert result["replay"] == "NEW_ATOMIC_INSTALL"
    assert len(calls) == 12


def test_hash_mismatch_and_low_space_fail_closed(tmp_path: Path) -> None:
    manifest, payloads = fixture_manifest()
    target = tmp_path / "published"
    bad_payloads = dict(payloads)
    bad_payloads[manifest["files"][0]["path"]] = b"tampered"
    with pytest.raises(MODULE.InstallError, match="content identity mismatch"):
        MODULE.install(
            manifest,
            target,
            fetch=fake_fetcher(bad_payloads, []),
            free_bytes=10_000,
            production_target=False,
        )
    with pytest.raises(MODULE.InstallError, match="insufficient free space"):
        MODULE.install(
            manifest,
            tmp_path / "other",
            fetch=fake_fetcher(payloads, []),
            free_bytes=100,
            production_target=False,
        )


def test_target_overwrite_and_authority_expansion_fail(tmp_path: Path) -> None:
    manifest, payloads = fixture_manifest()
    target = tmp_path / "published"
    target.mkdir()
    with pytest.raises(MODULE.InstallError, match="without a valid installation receipt"):
        MODULE.install(
            manifest,
            target,
            fetch=fake_fetcher(payloads, []),
            free_bytes=10_000,
            production_target=False,
        )
    expanded = copy.deepcopy(manifest)
    expanded["authority"]["forbidden"].remove("model_load")
    with pytest.raises(MODULE.InstallError, match="does not forbid model_load"):
        MODULE.install(
            expanded,
            tmp_path / "expanded",
            fetch=fake_fetcher(payloads, []),
            free_bytes=10_000,
            production_target=False,
        )


def test_production_target_is_exact(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with pytest.raises(MODULE.InstallError, match="CLI target differs"):
        MODULE.install(
            manifest,
            tmp_path / "wrong",
            fetch=lambda _url, _destination: None,
            free_bytes=20_000_000_000,
            production_target=True,
        )


def test_qwen3_omni_manifest_is_bound_for_production_storage_only() -> None:
    manifest = json.loads(OMNI_MANIFEST.read_text(encoding="utf-8"))
    manifest_hash = hashlib.sha256(MODULE.canonical_bytes(manifest)).hexdigest()
    assert manifest_hash in MODULE.ADMITTED_PRODUCTION_MANIFESTS
    MODULE._verify_manifest_shape(manifest)
    assert manifest["storage"]["weight_bytes"] == 63440997640
    assert "gpu_probe" in manifest["authority"]["forbidden"]


def test_wav2vec2_phoneme_aligner_manifest_is_bound_for_storage_only() -> None:
    import jsonschema

    manifest = json.loads(ALIGNER_MANIFEST.read_text(encoding="utf-8"))
    schema = json.loads(ALIGNER_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(manifest)
    manifest_hash = hashlib.sha256(MODULE.canonical_bytes(manifest)).hexdigest()
    assert manifest_hash == "84012eb3b62d7cbd4527d9dfb82fba1ee14a0f25a58173f4b6e57d35c16ef3bd"
    assert manifest_hash in MODULE.ADMITTED_PRODUCTION_MANIFESTS
    MODULE._verify_manifest_shape(manifest)
    assert manifest["source"]["revision"] == "ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4"
    assert manifest["storage"]["weight_bytes"] == 1263535127
    assert "forced_alignment_authority" in manifest["authority"]["forbidden"]


def test_latentsync_manifest_is_bound_for_storage_only() -> None:
    import jsonschema

    manifest = json.loads(LATENTSYNC_MANIFEST.read_text(encoding="utf-8"))
    schema = json.loads(LATENTSYNC_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(manifest)
    manifest_hash = hashlib.sha256(MODULE.canonical_bytes(manifest)).hexdigest()
    assert manifest_hash == "e9606b2e06b7a3283d893d6f15a882a7e2c488dc9f339cd24707c018d9d3bbc7"
    assert manifest_hash in MODULE.ADMITTED_PRODUCTION_MANIFESTS
    MODULE._verify_manifest_shape(manifest)
    assert manifest["source"]["revision"] == "c42c7e6c8e9c213626389fa7d9a3c444b8536353"
    assert manifest["storage"]["weight_bytes"] == 9635782864
    assert len(manifest["files"]) == 13
    assert "lip_sync_authority" in manifest["authority"]["forbidden"]
    assert "identity_preservation_authority" in manifest["authority"]["forbidden"]


def test_parallel_download_preserves_manifest_receipt_order(tmp_path: Path) -> None:
    manifest, payloads = fixture_manifest()
    target = tmp_path / "parallel"
    calls: list[str] = []
    result = MODULE.install(
        manifest,
        target,
        fetch=fake_fetcher(payloads, calls),
        free_bytes=10_000,
        production_target=False,
        download_workers=4,
    )
    assert result["replay"] == "NEW_ATOMIC_INSTALL"
    assert len(calls) == 12
    assert [item["path"] for item in result["files"]] == [
        item["path"] for item in manifest["files"]
    ]


def test_parallel_download_bounds_and_crash_mode_fail_closed(tmp_path: Path) -> None:
    manifest, payloads = fixture_manifest()
    fetch = fake_fetcher(payloads, [])
    with pytest.raises(MODULE.InstallError, match="between 1 and 8"):
        MODULE.install(
            manifest,
            tmp_path / "workers",
            fetch=fetch,
            free_bytes=10_000,
            production_target=False,
            download_workers=9,
        )
    with pytest.raises(MODULE.InstallError, match="requires serial"):
        MODULE.install(
            manifest,
            tmp_path / "crash",
            fetch=fetch,
            free_bytes=10_000,
            production_target=False,
            download_workers=2,
            crash_after_files=1,
        )
