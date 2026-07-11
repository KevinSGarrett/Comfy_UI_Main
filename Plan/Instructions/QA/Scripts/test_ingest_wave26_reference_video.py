from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

try:
    import jsonschema
except Exception:  # pragma: no cover - fallback path when jsonschema unavailable
    jsonschema = None


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/scripts/ingest_wave26_reference_video.py"
MANIFEST_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/reference_video_manifest.schema.json"
FRAME_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/reference_video_frame_manifest.schema.json"
EVIDENCE_SCHEMA_PATH = PROJECT_ROOT / "Plan/08_SCHEMAS/wave26_reference_video_ingest_evidence.schema.json"
POWERSHELL_WRAPPER_PATH = (
    PROJECT_ROOT / "Plan/07_IMPLEMENTATION/templates/powershell/Run-Wave26-ReferenceVideoValidation.ps1"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_ingest(
    source_video: Path,
    output_dir: Path,
    profile: str,
    *,
    source_video_id: str = "refvid_test",
    audio_present: str | None = "false",
    sample_stride: int | None = None,
    strict_short_clip_gate: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--source-video",
        str(source_video),
        "--output-dir",
        str(output_dir),
        "--extraction-profile-id",
        profile,
        "--source-video-id",
        source_video_id,
    ]
    if audio_present is not None:
        cmd.extend(["--audio-present", audio_present])
    if sample_stride is not None:
        cmd.extend(["--sample-stride", str(sample_stride)])
    if strict_short_clip_gate:
        cmd.append("--strict-short-clip-gate")
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _create_synthetic_video(path: Path, *, frame_count: int, fps: float, width: int = 64, height: int = 48) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    assert writer.isOpened(), "VideoWriter failed to open"
    for index in range(frame_count):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :, 0] = (index * 13) % 256
        frame[:, :, 1] = (index * 7) % 256
        frame[:, :, 2] = (index * 3) % 256
        writer.write(frame)
    writer.release()
    assert path.exists() and path.stat().st_size > 0


def _load_manifest(output_dir: Path) -> dict[str, Any]:
    return json.loads((output_dir / "reference_video_manifest.json").read_text(encoding="utf-8"))


def _load_frame_records(output_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    frame_manifest = output_dir / "frame_manifest.jsonl"
    for line in frame_manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def _load_evidence(output_dir: Path) -> dict[str, Any]:
    return json.loads((output_dir / "wave26_reference_video_ingest_evidence.json").read_text(encoding="utf-8"))


def _validate_schema(instance: Any, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if jsonschema is not None:
        jsonschema.Draft202012Validator(schema).validate(instance)
        return
    required = schema.get("required", [])
    assert all(key in instance for key in required), f"Missing required keys for {schema_path.name}"


def _load_ingest_module() -> Any:
    spec = importlib.util.spec_from_file_location("ingest_wave26_reference_video", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _powershell_command() -> list[str] | None:
    for name in ("pwsh", "powershell.exe", "powershell"):
        executable = shutil.which(name)
        if executable is None:
            continue
        command = [executable, "-NoProfile"]
        if Path(executable).name.lower().startswith("powershell"):
            command.extend(["-ExecutionPolicy", "Bypass"])
        return command
    return None


def test_all_frames_success_schema_and_flags(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    out = tmp_path / "out_all_frames"
    _create_synthetic_video(source, frame_count=6, fps=6.0)

    result = _run_ingest(source, out, "all_frames_short_clip", source_video_id="refvid_all")
    assert result.returncode == 0, result.stderr or result.stdout

    manifest = _load_manifest(out)
    frames = _load_frame_records(out)
    evidence = _load_evidence(out)

    assert manifest["source_video_id"].startswith("refvid_all_")
    assert manifest["source_video_id"].endswith(_sha256(source)[:16])
    assert manifest["audio_present"] is False
    assert manifest["frame_count"] == 6
    assert manifest["extraction_profile_id"] == "all_frames_short_clip"
    assert len(frames) == 6
    assert [f["frame_index"] for f in frames] == list(range(6))
    assert all(f["qa_status"] == "decoded_png_hash_verified" for f in frames)

    for flag in evidence["claims"].values():
        assert flag is False

    _validate_schema(manifest, MANIFEST_SCHEMA_PATH)
    for frame in frames:
        _validate_schema(frame, FRAME_SCHEMA_PATH)
    _validate_schema(evidence, EVIDENCE_SCHEMA_PATH)


def test_sample_every_n_stride_and_ordering(tmp_path: Path) -> None:
    source = tmp_path / "source_stride.mp4"
    out = tmp_path / "out_stride"
    _create_synthetic_video(source, frame_count=10, fps=5.0)

    result = _run_ingest(source, out, "sample_every_n", source_video_id="refvid_stride", sample_stride=3)
    assert result.returncode == 0, result.stdout

    frames = _load_frame_records(out)
    indexes = [frame["frame_index"] for frame in frames]
    assert indexes == [0, 3, 6, 9]
    assert indexes == sorted(indexes)


def test_deterministic_outputs_across_runs(tmp_path: Path) -> None:
    source = tmp_path / "det_source.mp4"
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    _create_synthetic_video(source, frame_count=8, fps=8.0)

    first = _run_ingest(source, out_a, "sample_every_n", source_video_id="refvid_det", sample_stride=2)
    second = _run_ingest(source, out_b, "sample_every_n", source_video_id="refvid_det", sample_stride=2)
    assert first.returncode == 0
    assert second.returncode == 0

    assert _load_manifest(out_a) == _load_manifest(out_b)
    assert _load_evidence(out_a) == _load_evidence(out_b)

    frame_records_a = _load_frame_records(out_a)
    frame_records_b = _load_frame_records(out_b)
    assert frame_records_a == frame_records_b

    frame_hashes_a = sorted(_sha256(path) for path in (out_a / "frames").glob("*.png"))
    frame_hashes_b = sorted(_sha256(path) for path in (out_b / "frames").glob("*.png"))
    assert frame_hashes_a == frame_hashes_b


def test_corrupt_and_unsupported_inputs_fail_closed(tmp_path: Path) -> None:
    unsupported = tmp_path / "bad.txt"
    unsupported.write_text("not a video", encoding="utf-8")
    out_unsupported = tmp_path / "out_bad_extension"
    unsupported_result = _run_ingest(unsupported, out_unsupported, "all_frames_short_clip")
    assert unsupported_result.returncode == 1
    assert not out_unsupported.exists()

    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_text("corrupt", encoding="utf-8")
    out_corrupt = tmp_path / "out_corrupt"
    corrupt_result = _run_ingest(corrupt, out_corrupt, "all_frames_short_clip")
    assert corrupt_result.returncode == 1
    assert not out_corrupt.exists()


def test_invalid_stride_returns_exit_1(tmp_path: Path) -> None:
    source = tmp_path / "stride_invalid.mp4"
    out = tmp_path / "out_invalid_stride"
    _create_synthetic_video(source, frame_count=6, fps=6.0)

    result = _run_ingest(source, out, "sample_every_n", sample_stride=0)
    assert result.returncode == 1
    assert not out.exists()


def test_short_clip_duration_gate_enforced(tmp_path: Path) -> None:
    source = tmp_path / "long_clip.mp4"
    out = tmp_path / "out_long_clip"
    _create_synthetic_video(source, frame_count=90, fps=9.0)  # duration = 10s > max_recommended_seconds=8

    result = _run_ingest(source, out, "all_frames_short_clip")
    assert result.returncode == 1
    assert "duration gate failed" in (result.stdout + result.stderr)
    assert not out.exists()


@pytest.mark.parametrize(
    "profile",
    [
        "motion_peak_sampling",
        "contact_phase_sampling",
        "shot_boundary_sampling",
        "loop_candidate_sampling",
    ],
)
def test_blocked_profiles_exit_2_with_structured_blocker(tmp_path: Path, profile: str) -> None:
    source = tmp_path / f"blocked_{profile}.mp4"
    out = tmp_path / f"out_{profile}"
    _create_synthetic_video(source, frame_count=4, fps=4.0)

    result = _run_ingest(source, out, profile, audio_present=None)
    assert result.returncode == 2
    payload = json.loads(result.stdout.strip())
    assert payload["status"] == "blocked"
    assert payload["profile_id"] == profile
    assert set(payload["supported_profiles"]) == {"all_frames_short_clip", "sample_every_n"}
    assert not out.exists()


def test_hash_manifest_and_frame_paths_are_consistent(tmp_path: Path) -> None:
    source = tmp_path / "hash_source.mp4"
    out = tmp_path / "out_hash"
    _create_synthetic_video(source, frame_count=7, fps=7.0)

    result = _run_ingest(source, out, "sample_every_n", sample_stride=2, source_video_id="refvid_hash")
    assert result.returncode == 0

    manifest = _load_manifest(out)
    frames = _load_frame_records(out)
    evidence = _load_evidence(out)

    assert manifest["fingerprint"] == f"sha256:{_sha256(source)}"
    assert evidence["source_video"]["sha256"] == _sha256(source)
    assert [record["frame_index"] for record in frames] == [0, 2, 4, 6]
    for record in frames:
        frame_path = out / record["frame_path_or_asset_id"]
        assert frame_path.exists()
        assert record["png_sha256"] == _sha256(frame_path)


def test_transactional_cleanup_on_failure(tmp_path: Path) -> None:
    source = tmp_path / "cleanup_source.mp4"
    out = tmp_path / "out_cleanup"
    _create_synthetic_video(source, frame_count=4, fps=4.0)

    result = _run_ingest(source, out, "sample_every_n", sample_stride=-5)
    assert result.returncode == 1
    assert not out.exists()


def test_rejects_existing_output_directory_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "source_existing_dir.mp4"
    out = tmp_path / "out_existing"
    _create_synthetic_video(source, frame_count=6, fps=6.0)
    out.mkdir(parents=True, exist_ok=True)
    sentinel = out / "sentinel.txt"
    sentinel.write_text("keep-me", encoding="utf-8")

    result = _run_ingest(source, out, "sample_every_n", sample_stride=2)
    assert result.returncode == 1
    payload = json.loads(result.stdout.strip())
    assert payload["error_type"] == "output_path_exists"
    assert sentinel.read_text(encoding="utf-8") == "keep-me"


def test_rejects_existing_output_file_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "source_existing_file.mp4"
    out_file = tmp_path / "out_existing_file"
    _create_synthetic_video(source, frame_count=6, fps=6.0)
    out_file.write_text("keep-file", encoding="utf-8")

    result = _run_ingest(source, out_file, "sample_every_n", sample_stride=2)
    assert result.returncode == 1
    payload = json.loads(result.stdout.strip())
    assert payload["error_type"] == "output_path_exists"
    assert out_file.read_text(encoding="utf-8") == "keep-file"


def test_missing_audio_declaration_returns_exit_1(tmp_path: Path) -> None:
    source = tmp_path / "audio_missing.mp4"
    out = tmp_path / "out_audio_missing"
    _create_synthetic_video(source, frame_count=4, fps=4.0)

    result = _run_ingest(source, out, "all_frames_short_clip", audio_present=None)
    assert result.returncode == 1
    payload = json.loads(result.stdout.strip())
    assert payload["error_type"] == "missing_required_argument"
    assert "--audio-present true|false" in payload["message"]


@pytest.mark.parametrize("audio_value, expected", [("true", True), ("false", False)])
def test_audio_declaration_propagates_to_manifest_and_evidence(
    tmp_path: Path, audio_value: str, expected: bool
) -> None:
    source = tmp_path / f"audio_{audio_value}.mp4"
    out = tmp_path / f"out_audio_{audio_value}"
    _create_synthetic_video(source, frame_count=5, fps=5.0)

    result = _run_ingest(source, out, "sample_every_n", audio_present=audio_value, sample_stride=2)
    assert result.returncode == 0, result.stdout
    manifest = _load_manifest(out)
    evidence = _load_evidence(out)

    assert manifest["audio_present"] is expected
    assert evidence["ingest"]["audio_present"] is expected
    assert (
        evidence["ingest"]["audio_evidence_provenance"]
        == "explicit_cli_declaration_not_verified_by_opencv"
    )
    assert evidence["assumptions"]["audio"] == "explicit_cli_declaration_not_verified_by_opencv"


def test_source_video_id_binds_custom_label_to_source_hash(tmp_path: Path) -> None:
    source = tmp_path / "source_hash_bind.mp4"
    out = tmp_path / "out_hash_bind"
    _create_synthetic_video(source, frame_count=5, fps=5.0)

    result = _run_ingest(source, out, "sample_every_n", source_video_id="my_custom_label", sample_stride=2)
    assert result.returncode == 0
    manifest = _load_manifest(out)
    expected_suffix = _sha256(source)[:16]
    assert manifest["source_video_id"].startswith("my_custom_label_")
    assert manifest["source_video_id"].endswith(expected_suffix)


def test_frame_manifest_omits_empty_timeline_ids(tmp_path: Path) -> None:
    source = tmp_path / "timeline_ids.mp4"
    out = tmp_path / "out_timeline_ids"
    _create_synthetic_video(source, frame_count=5, fps=5.0)

    result = _run_ingest(source, out, "sample_every_n", sample_stride=2)
    assert result.returncode == 0
    frames = _load_frame_records(out)
    for frame in frames:
        assert "pose_state_id" not in frame
        assert "depth_state_id" not in frame
        assert "mask_state_id" not in frame
        assert "contact_state_id" not in frame


def test_manifest_and_frame_manifest_hashes_bound_into_evidence(tmp_path: Path) -> None:
    source = tmp_path / "hash_binding.mp4"
    out = tmp_path / "out_hash_binding"
    _create_synthetic_video(source, frame_count=5, fps=5.0)

    result = _run_ingest(source, out, "sample_every_n", sample_stride=2)
    assert result.returncode == 0
    evidence = _load_evidence(out)
    artifacts = evidence["artifacts"]
    manifest_path = out / "reference_video_manifest.json"
    frame_manifest_path = out / "frame_manifest.jsonl"

    assert artifacts["manifest_sha256"] == _sha256(manifest_path)
    assert artifacts["manifest_bytes"] == manifest_path.stat().st_size
    assert artifacts["frame_manifest_sha256"] == _sha256(frame_manifest_path)
    assert artifacts["frame_manifest_bytes"] == frame_manifest_path.stat().st_size


def test_orientation_evidence_shape_and_dimension_reporting(tmp_path: Path) -> None:
    source = tmp_path / "orientation.mp4"
    out = tmp_path / "out_orientation"
    _create_synthetic_video(source, frame_count=5, fps=5.0, width=80, height=60)

    result = _run_ingest(source, out, "sample_every_n", sample_stride=2)
    assert result.returncode == 0
    evidence = _load_evidence(out)
    ingest = evidence["ingest"]

    assert "orientation_metadata_degrees_reported_by_opencv" in ingest
    assert "orientation_auto_flag_reported_by_opencv" in ingest
    assert (
        evidence["assumptions"]["orientation"]
        == "opencv_properties_recorded_no_explicit_ingest_rotation"
    )
    assert ingest["decoded_width"] == 80
    assert ingest["decoded_height"] == 60
    assert ingest["reported_width"] >= 0
    assert ingest["reported_height"] >= 0


def test_schema_validator_rejects_deliberately_invalid_instance() -> None:
    ingest_module = _load_ingest_module()
    validator = ingest_module.load_schema_validator(EVIDENCE_SCHEMA_PATH)
    invalid = {"schema_version": "1.0.0", "status": "success"}

    with pytest.raises(ingest_module.IngestError) as exc_info:
        ingest_module.validate_instance(invalid, validator, "deliberate_invalid_evidence")
    assert exc_info.value.error_type == "schema_validation_failed"


def test_nonfinite_json_and_orientation_metadata_fail_closed(tmp_path: Path) -> None:
    ingest_module = _load_ingest_module()
    payload = tmp_path / "nonfinite.json"
    payload.write_text('{"value": NaN}\n', encoding="utf-8")

    with pytest.raises(ingest_module.IngestError):
        ingest_module.load_json(payload)
    assert ingest_module.finite_float_or_none(float("nan")) is None
    assert ingest_module.finite_float_or_none(float("inf")) is None
    assert ingest_module.finite_float_or_none(90.0) == 90.0


def test_frame_count_metadata_uses_tolerance_and_rejects_large_drift() -> None:
    ingest_module = _load_ingest_module()

    exact = ingest_module.assess_frame_count_consistency(reported=100, decoded=100)
    assert exact == {"status": "exact", "delta": 0, "tolerance_frames": 2}
    tolerated = ingest_module.assess_frame_count_consistency(reported=100, decoded=99)
    assert tolerated == {"status": "within_tolerance", "delta": -1, "tolerance_frames": 2}
    unavailable = ingest_module.assess_frame_count_consistency(reported=0, decoded=100)
    assert unavailable == {
        "status": "metadata_unavailable",
        "delta": None,
        "tolerance_frames": None,
    }
    with pytest.raises(ingest_module.IngestError):
        ingest_module.assess_frame_count_consistency(reported=100, decoded=95)


def test_decode_path_releases_capture_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ingest_module = _load_ingest_module()
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "dummy.mp4"
    source.write_bytes(b"dummy")
    holder: dict[str, Any] = {}

    class FakeCapture:
        def __init__(self) -> None:
            self.released = False
            holder["capture"] = self

        def isOpened(self) -> bool:
            return True

        def get(self, prop: int) -> float:
            if prop == cv2.CAP_PROP_FPS:
                return 10.0
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 64.0
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 48.0
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 1.0
            return 0.0

        def read(self) -> tuple[bool, Any]:
            return True, None

        def release(self) -> None:
            self.released = True

    monkeypatch.setattr(ingest_module.cv2, "VideoCapture", lambda _: FakeCapture())
    with pytest.raises(ingest_module.IngestError):
        ingest_module.decode_and_extract_frames(
            source_video=source,
            extracted_frames_dir=frames_dir,
            source_video_id="release_check",
            profile_id="sample_every_n",
            stride=1,
        )
    assert holder["capture"].released is True


@pytest.mark.skipif(_powershell_command() is None, reason="PowerShell not available")
def test_powershell_structural_mode_is_claim_bounded() -> None:
    powershell = _powershell_command()
    assert powershell is not None
    result = subprocess.run(
        [
            *powershell,
            "-File",
            str(POWERSHELL_WRAPPER_PATH),
            "-Root",
            str(PROJECT_ROOT / "Plan"),
            "-Mode",
            "structural",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Structural assets are present only; this mode does not claim decoded source-video handling." in result.stdout


@pytest.mark.skipif(_powershell_command() is None, reason="PowerShell not available")
def test_powershell_source_video_mode_requires_audio_present_flag() -> None:
    powershell = _powershell_command()
    assert powershell is not None
    result = subprocess.run(
        [
            *powershell,
            "-File",
            str(POWERSHELL_WRAPPER_PATH),
            "-Root",
            str(PROJECT_ROOT / "Plan"),
            "-Mode",
            "source_video",
            "-SourceVideo",
            "placeholder.mp4",
            "-OutputDir",
            "placeholder_out",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Mode=source_video requires -AudioPresent true|false" in result.stdout


@pytest.mark.skipif(_powershell_command() is None, reason="PowerShell not available")
def test_powershell_source_video_forwards_audio_and_preserves_exit_code(tmp_path: Path) -> None:
    powershell = _powershell_command()
    assert powershell is not None
    source = tmp_path / "wrapper_source.mp4"
    output_dir = tmp_path / "wrapper_output"
    _create_synthetic_video(source, frame_count=6, fps=6.0)

    command = [
        *powershell,
        "-File",
        str(POWERSHELL_WRAPPER_PATH),
        "-Root",
        str(PROJECT_ROOT / "Plan"),
        "-Mode",
        "source_video",
        "-SourceVideo",
        str(source),
        "-OutputDir",
        str(output_dir),
        "-ExtractionProfileId",
        "sample_every_n",
        "-SampleStride",
        "2",
        "-AudioPresent",
        "true",
        "-PythonExe",
        sys.executable,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _load_manifest(output_dir)["audio_present"] is True

    repeated = subprocess.run(
        [
            *command,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert repeated.returncode == 1
    assert "output_path_exists" in repeated.stdout
