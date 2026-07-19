#!/usr/bin/env python3
"""Fail-closed Wave64 Row097 sample-accurate mix/mux contract slice.

Library mix/mux refuses authority without accepted Rows091/093/094/095/096.
Fixture mode may emit deterministic schema-validated mix/mux receipts from
synthetic stem schedules without promoting library completion or claiming audio QA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path("Plan/08_SCHEMAS/sample_accurate_mix_mux_receipt.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row097_sample_accurate_mix_mux_registry.json"
)
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-097_sample_accurate_mix_mux.json"
)

DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-091": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-091_VISUAL_AUDIO_EVENT_MANIFEST_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-093": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-093_CANONICAL_CLIP_PREPARATION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-094": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-094_LAYERED_FOLEY_COMPOSITION_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-095": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-095_SPATIAL_AUDIO_RENDERER_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-096": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-096_ROOM_ACOUSTIC_RENDERER_CURRENT_DELTA_20260719.json"
    ),
}

ENGINE_REVISION = "wave64_row097_sample_accurate_mix_mux_engine_v0.1.0"
POLICY_REVISION = "wave64_row097_sample_accurate_mix_mux_v0.1.0"
TRACKER_ID = "TRK-W64-097"
ITEM_ID = "ITEM-W64-097"
SCHEMA_VERSION = "1.0.0"

ALLOWED_STEM_BUSES = (
    "dialogue",
    "foley",
    "ambience",
    "music",
    "room",
    "master",
)

REQUIRED_GATES = (
    "sample_schedule",
    "bus_processing",
    "loudness",
    "true_peak",
    "stem_manifest",
    "mux_lineage",
)

FIXTURE_NAMES = (
    "compatible_stems_mix_mux",
    "missing_expected_stem_blocked",
    "true_peak_exceedance_rejected",
    "endpoint_drift_rejected",
    "sample_schedule_mismatch_rejected",
    "duplicate_stem_bus_rejected",
)


class SampleAccurateMixMuxError(ValueError):
    """Raised when Row097 mix/mux violates fail-closed authority."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise SampleAccurateMixMuxError(f"{label}_outside_project_root") from exc
    return path


def _stable_hash(label: str) -> str:
    return sha256_bytes(f"wave64_row097_fixture:{label}".encode("utf-8"))


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise SampleAccurateMixMuxError("policy_registry_revision_mismatch")
    if tuple(payload.get("allowed_stem_buses") or ()) != ALLOWED_STEM_BUSES:
        raise SampleAccurateMixMuxError("policy_allowed_stem_buses_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise SampleAccurateMixMuxError("policy_required_gates_mismatch")
    if tuple(payload.get("bus_order") or ()) != ALLOWED_STEM_BUSES:
        raise SampleAccurateMixMuxError("policy_bus_order_mismatch")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    delta_path: Path,
    tracker_id: str,
    blocker_code: str,
    absent_code: str,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id.lower()}_delta")
    if not path.is_file():
        return {
            "tracker_id": tracker_id,
            "dependency_satisfied": False,
            "blocker_codes": [absent_code],
            "row_complete": False,
            "status": "",
            "path": str(path.relative_to(root)).replace("\\", "/"),
        }
    payload = load_json(path)
    row_complete = payload.get("row_complete") is True
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    row_suffix = tracker_id.rsplit("-", 1)[-1].lower()
    exact_acceptance = str(decision.get(f"row{row_suffix}_acceptance", "")).lower()
    coarse_markers = [
        exact_acceptance,
        str(decision.get("status", "")).lower(),
        str(payload.get("qa_decision", "")).lower(),
    ]
    accepted_markers = {"accepted", "pass", "passed"}
    acceptance_hit = any(marker in accepted_markers for marker in coarse_markers if marker)
    status_text = str(payload.get("status", "")).lower()
    hold_decision = payload.get("hold_decision")
    hold_text = ""
    if isinstance(hold_decision, dict):
        hold_text = str(hold_decision.get("decision", "")).lower()
    if status_text.startswith("hold") or hold_text.startswith("hold"):
        acceptance_hit = False
    if status_text.startswith("pass_") and row_complete:
        acceptance_hit = True
    dependency_satisfied = row_complete and acceptance_hit
    blocker_codes: list[str] = []
    if not dependency_satisfied:
        blocker_codes.append(blocker_code)
    return {
        "tracker_id": tracker_id,
        "dependency_satisfied": dependency_satisfied,
        "blocker_codes": blocker_codes,
        "row_complete": row_complete,
        "status": str(payload.get("status", "")),
        "path": str(path.relative_to(root)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def evaluate_all_dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for tracker_id, delta_path in DEPENDENCY_DELTAS.items():
        code = tracker_id.replace("-", "_") + "_DEPENDENCY_NOT_ACCEPTED"
        absent = tracker_id.replace("-", "_") + "_DELTA_ABSENT"
        out[tracker_id] = evaluate_dependency_admission(
            root,
            delta_path=delta_path,
            tracker_id=tracker_id,
            blocker_code=code,
            absent_code=absent,
        )
    return out


def recipe_sha256(recipe: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(recipe))


def derive_stem_pcm_sha256(
    source_pcm_sha256: str,
    *,
    stem_bus: str,
    start_sample: int,
    end_sample: int,
    gain_db: float,
    bus_gain_db: float,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "source_pcm_sha256": source_pcm_sha256,
                "stem_bus": stem_bus,
                "start_sample": start_sample,
                "end_sample": end_sample,
                "gain_db": gain_db,
                "bus_gain_db": bus_gain_db,
                "transform": "wave64_row097_deterministic_stem_v0",
            }
        )
    )


def recompute_stem_manifest_sha256(ordered_stems: list[dict[str, Any]]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "stems": [
                    {
                        "stem_bus": item["stem_bus"],
                        "stem_pcm_sha256": item["stem_pcm_sha256"],
                        "start_sample": item["start_sample"],
                        "end_sample": item["end_sample"],
                        "gain_db": item["gain_db"],
                        "bus_gain_db": item["bus_gain_db"],
                    }
                    for item in ordered_stems
                ],
                "engine_revision": ENGINE_REVISION,
            }
        )
    )


def recompute_mix_pcm_sha256(
    ordered_stem_pcm: list[str],
    *,
    mix_recipe_sha256: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "ordered_stem_pcm_sha256": ordered_stem_pcm,
                "mix_recipe_sha256": mix_recipe_sha256,
                "mix": "wave64_row097_deterministic_bus_sum_v0",
            }
        )
    )


def recompute_mux_container_sha256(
    *,
    video_timeline_sha256: str,
    mix_pcm_sha256: str,
    video_frame_count: int,
    audio_sample_count: int,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "video_timeline_sha256": video_timeline_sha256,
                "mix_pcm_sha256": mix_pcm_sha256,
                "video_frame_count": video_frame_count,
                "audio_sample_count": audio_sample_count,
                "mux": "wave64_row097_deterministic_mux_v0",
            }
        )
    )


def recompute_mux_lineage_sha256(
    *,
    video_timeline_sha256: str,
    stem_manifest_sha256: str,
    mix_pcm_sha256: str,
    mux_container_sha256: str,
    mix_recipe_sha256: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "engine_revision": ENGINE_REVISION,
                "policy_revision": POLICY_REVISION,
                "video_timeline_sha256": video_timeline_sha256,
                "stem_manifest_sha256": stem_manifest_sha256,
                "mix_pcm_sha256": mix_pcm_sha256,
                "mux_container_sha256": mux_container_sha256,
                "mix_recipe_sha256": mix_recipe_sha256,
            }
        )
    )


def expected_audio_sample_count(
    *,
    video_frame_count: int,
    sample_rate_hz: int,
    frame_rate_numerator: int,
    frame_rate_denominator: int,
) -> int:
    return int(
        video_frame_count
        * sample_rate_hz
        * frame_rate_denominator
        // frame_rate_numerator
    )


def _normalize_stem_input(raw: dict[str, Any]) -> dict[str, Any]:
    bus = str(raw["stem_bus"])
    if bus not in ALLOWED_STEM_BUSES:
        raise SampleAccurateMixMuxError(f"unknown_stem_bus:{bus}")
    start = int(raw["start_sample"])
    end = int(raw["end_sample"])
    if end <= start:
        raise SampleAccurateMixMuxError(f"invalid_stem_span:{bus}")
    gain_db = float(raw["gain_db"])
    bus_gain_db = float(raw["bus_gain_db"])
    source_pcm = str(raw["source_pcm_sha256"])
    return {
        "stem_bus": bus,
        "asset_id": str(raw["asset_id"]),
        "source_pcm_sha256": source_pcm,
        "stem_pcm_sha256": derive_stem_pcm_sha256(
            source_pcm,
            stem_bus=bus,
            start_sample=start,
            end_sample=end,
            gain_db=gain_db,
            bus_gain_db=bus_gain_db,
        ),
        "start_sample": start,
        "end_sample": end,
        "gain_db": gain_db,
        "bus_gain_db": bus_gain_db,
        "admitted": False,
    }


def evaluate_sample_schedule(
    stems: list[dict[str, Any]],
    *,
    audio_sample_count: int,
    endpoint_drift_samples: int,
    drift_tolerance: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    reason_codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    for item in stems:
        if item["start_sample"] < 0 or item["end_sample"] > audio_sample_count:
            reason_codes.append("SAMPLE_SCHEDULE_MISMATCH")
            exclusions.append(
                {
                    "stem_bus": item["stem_bus"],
                    "reason_codes": ["SAMPLE_SCHEDULE_MISMATCH"],
                }
            )
    if abs(int(endpoint_drift_samples)) > int(drift_tolerance):
        reason_codes.append("ENDPOINT_DRIFT")
        exclusions.append(
            {"stem_bus": "master", "reason_codes": ["ENDPOINT_DRIFT"]}
        )
    unique = sorted(set(reason_codes))
    return (
        {"status": "pass" if not unique else "fail", "reason_codes": unique},
        exclusions,
        unique,
    )


def evaluate_stem_manifest_presence(
    expected_stems: list[str],
    stems: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    reason_codes: list[str] = []
    exclusions: list[dict[str, Any]] = []
    buses = [item["stem_bus"] for item in stems]
    if len(buses) != len(set(buses)):
        reason_codes.append("DUPLICATE_STEM_BUS")
        seen: set[str] = set()
        for bus in buses:
            if bus in seen:
                exclusions.append(
                    {"stem_bus": bus, "reason_codes": ["DUPLICATE_STEM_BUS"]}
                )
            seen.add(bus)
    expected = list(expected_stems)
    provided = set(buses)
    for bus in expected:
        if bus not in provided:
            reason_codes.append("MISSING_EXPECTED_STEM")
            exclusions.append(
                {"stem_bus": bus, "reason_codes": ["MISSING_EXPECTED_STEM"]}
            )
    for bus in provided:
        if bus not in expected:
            reason_codes.append("UNEXPECTED_STEM")
            exclusions.append(
                {"stem_bus": bus, "reason_codes": ["UNEXPECTED_STEM"]}
            )
    unique = sorted(set(reason_codes))
    return (
        {"status": "pass" if not unique else "fail", "reason_codes": unique},
        exclusions,
        unique,
    )


def evaluate_bus_processing(stems: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    reason_codes: list[str] = []
    for item in stems:
        if item["stem_bus"] == "master" and float(item["bus_gain_db"]) > 0.0:
            reason_codes.append("MASTER_BUS_GAIN_POSITIVE")
        if item["stem_bus"] == "dialogue" and float(item["bus_gain_db"]) < -24.0:
            reason_codes.append("DIALOGUE_BUS_OVER_ATTENUATED")
    unique = sorted(set(reason_codes))
    return (
        {"status": "pass" if not unique else "fail", "reason_codes": unique},
        unique,
    )


def evaluate_loudness(
    measured_lufs: float | None,
    *,
    target_lufs: float,
) -> tuple[dict[str, Any], list[str]]:
    if measured_lufs is None:
        return (
            {"status": "fail", "reason_codes": ["LOUDNESS_UNMEASURED"]},
            ["LOUDNESS_UNMEASURED"],
        )
    # Fixture band: +/- 2 LU around target.
    if abs(float(measured_lufs) - float(target_lufs)) > 2.0:
        return (
            {"status": "fail", "reason_codes": ["LOUDNESS_OUT_OF_BAND"]},
            ["LOUDNESS_OUT_OF_BAND"],
        )
    return ({"status": "pass", "reason_codes": []}, [])


def evaluate_true_peak(
    measured_true_peak_dbtp: float | None,
    *,
    ceiling_dbtp: float,
) -> tuple[dict[str, Any], list[str]]:
    if measured_true_peak_dbtp is None:
        return (
            {"status": "fail", "reason_codes": ["TRUE_PEAK_UNMEASURED"]},
            ["TRUE_PEAK_UNMEASURED"],
        )
    if float(measured_true_peak_dbtp) > float(ceiling_dbtp):
        return (
            {"status": "fail", "reason_codes": ["TRUE_PEAK_EXCEEDANCE"]},
            ["TRUE_PEAK_EXCEEDANCE"],
        )
    return ({"status": "pass", "reason_codes": []}, [])


def seal_receipt(record: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(record)
    sealed.pop("receipt_sha256", None)
    sealed["receipt_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    return sealed


def validate_mix_mux_semantics(record: dict[str, Any]) -> None:
    stems = record.get("stems") or []
    expected = record.get("expected_stems") or []
    gate_results = record.get("gate_results") or {}
    if set(gate_results.keys()) != set(REQUIRED_GATES):
        raise SampleAccurateMixMuxError("gate_result_set_mismatch")
    decision = record.get("decision") or {}
    route = decision.get("route")
    mix = record.get("mix_recipe") or {}
    mux = record.get("mux") or {}
    if route == "mix_mux":
        buses = [item.get("stem_bus") for item in stems]
        if len(buses) != len(set(buses)):
            raise SampleAccurateMixMuxError("duplicate_stem_bus_in_receipt")
        for gate in REQUIRED_GATES:
            if gate_results[gate]["status"] != "pass":
                raise SampleAccurateMixMuxError(f"mix_mux_with_failed_gate:{gate}")
        if set(buses) != set(expected):
            raise SampleAccurateMixMuxError("mix_mux_stem_set_mismatch")
        ordered = sorted(stems, key=lambda item: ALLOWED_STEM_BUSES.index(item["stem_bus"]))
        for item in ordered:
            if item.get("admitted") is not True:
                raise SampleAccurateMixMuxError("mix_mux_with_unadmitted_stem")
            recomputed = derive_stem_pcm_sha256(
                item["source_pcm_sha256"],
                stem_bus=item["stem_bus"],
                start_sample=item["start_sample"],
                end_sample=item["end_sample"],
                gain_db=item["gain_db"],
                bus_gain_db=item["bus_gain_db"],
            )
            if recomputed != item["stem_pcm_sha256"]:
                raise SampleAccurateMixMuxError("stem_pcm_recompute_mismatch")
        mix_body = {
            "sample_rate_hz": mix["sample_rate_hz"],
            "channels": mix["channels"],
            "target_lufs": mix["target_lufs"],
            "true_peak_ceiling_dbtp": mix["true_peak_ceiling_dbtp"],
            "minimum_headroom_db": mix["minimum_headroom_db"],
            "ordered_stem_buses": mix["ordered_stem_buses"],
            "measured_lufs": mix["measured_lufs"],
            "measured_true_peak_dbtp": mix["measured_true_peak_dbtp"],
        }
        if recipe_sha256(mix_body) != mix["recipe_sha256"]:
            raise SampleAccurateMixMuxError("mix_recipe_sha256_recompute_mismatch")
        stem_manifest = recompute_stem_manifest_sha256(ordered)
        if stem_manifest != mux["stem_manifest_sha256"]:
            raise SampleAccurateMixMuxError("stem_manifest_recompute_mismatch")
        mix_pcm = recompute_mix_pcm_sha256(
            [item["stem_pcm_sha256"] for item in ordered],
            mix_recipe_sha256=mix["recipe_sha256"],
        )
        if mix_pcm != mux["mix_pcm_sha256"]:
            raise SampleAccurateMixMuxError("mix_pcm_recompute_mismatch")
        container = recompute_mux_container_sha256(
            video_timeline_sha256=record["video_timeline_sha256"],
            mix_pcm_sha256=mix_pcm,
            video_frame_count=int(mux["video_frame_count"]),
            audio_sample_count=int(mux["audio_sample_count"]),
        )
        if container != mux["mux_container_sha256"]:
            raise SampleAccurateMixMuxError("mux_container_recompute_mismatch")
        lineage = recompute_mux_lineage_sha256(
            video_timeline_sha256=record["video_timeline_sha256"],
            stem_manifest_sha256=stem_manifest,
            mix_pcm_sha256=mix_pcm,
            mux_container_sha256=container,
            mix_recipe_sha256=mix["recipe_sha256"],
        )
        if lineage != mux["mux_lineage_sha256"]:
            raise SampleAccurateMixMuxError("mux_lineage_recompute_mismatch")
        if mux.get("reconstructable") is not True:
            raise SampleAccurateMixMuxError("mix_mux_not_marked_reconstructable")
        if decision.get("blocker_codes"):
            raise SampleAccurateMixMuxError("mix_mux_with_blocker_codes")
    elif route == "blocked":
        if not decision.get("blocker_codes"):
            raise SampleAccurateMixMuxError("blocked_without_blocker_codes")
        if mux.get("reconstructable") is True:
            raise SampleAccurateMixMuxError("blocked_marked_reconstructable")
        if mux.get("mux_lineage_sha256") is not None:
            raise SampleAccurateMixMuxError("blocked_with_mux_lineage")
        if mux.get("mix_pcm_sha256") is not None:
            raise SampleAccurateMixMuxError("blocked_with_mix_pcm")
    else:
        raise SampleAccurateMixMuxError(f"unknown_route:{route}")
    if record.get("library_authority") is True:
        raise SampleAccurateMixMuxError("library_authority_true_forbidden")
    if decision.get("product_completion") is True:
        raise SampleAccurateMixMuxError("product_completion_true_forbidden")


def validate_mix_mux_receipt(root: Path, record: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    Draft202012Validator(schema).validate(record)
    validate_mix_mux_semantics(record)
    sealed = seal_receipt({k: v for k, v in record.items() if k != "receipt_sha256"})
    if sealed["receipt_sha256"] != record.get("receipt_sha256"):
        raise SampleAccurateMixMuxError("receipt_sha256_mismatch")


def build_mix_mux_record(
    root: Path,
    *,
    timeline_id: str,
    video_timeline_sha256: str,
    expected_stems: list[str],
    stems_input: list[dict[str, Any]],
    video_frame_count: int,
    endpoint_drift_samples: int,
    measured_lufs: float | None,
    measured_true_peak_dbtp: float | None,
    is_synthetic: bool,
) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    stems = [_normalize_stem_input(item) for item in stems_input]
    defaults = policy["mix_defaults"]
    sample_rate = int(defaults["sample_rate_hz"])
    channels = int(defaults["channels"])
    target_lufs = float(defaults["target_lufs"])
    ceiling = float(defaults["true_peak_ceiling_dbtp"])
    headroom = float(defaults["minimum_headroom_db"])
    drift_tolerance = int(defaults["endpoint_drift_tolerance_samples"])
    frame_num = int(defaults["frame_rate_numerator"])
    frame_den = int(defaults["frame_rate_denominator"])
    audio_sample_count = expected_audio_sample_count(
        video_frame_count=video_frame_count,
        sample_rate_hz=sample_rate,
        frame_rate_numerator=frame_num,
        frame_rate_denominator=frame_den,
    )

    manifest_gate, manifest_exclusions, manifest_codes = evaluate_stem_manifest_presence(
        expected_stems, stems
    )
    schedule_gate, schedule_exclusions, schedule_codes = evaluate_sample_schedule(
        stems,
        audio_sample_count=audio_sample_count,
        endpoint_drift_samples=endpoint_drift_samples,
        drift_tolerance=drift_tolerance,
    )
    bus_gate, bus_codes = evaluate_bus_processing(stems)
    loudness_gate, loudness_codes = evaluate_loudness(
        measured_lufs, target_lufs=target_lufs
    )
    peak_gate, peak_codes = evaluate_true_peak(
        measured_true_peak_dbtp, ceiling_dbtp=ceiling
    )

    blocker_codes = sorted(
        set(manifest_codes + schedule_codes + bus_codes + loudness_codes + peak_codes)
    )
    exclusions = manifest_exclusions + schedule_exclusions
    ordered_roles = [bus for bus in ALLOWED_STEM_BUSES if bus in expected_stems]
    mix_body = {
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "target_lufs": target_lufs,
        "true_peak_ceiling_dbtp": ceiling,
        "minimum_headroom_db": headroom,
        "ordered_stem_buses": ordered_roles,
        "measured_lufs": measured_lufs,
        "measured_true_peak_dbtp": measured_true_peak_dbtp,
    }
    mix_sha = recipe_sha256(mix_body)
    mix_ok = not blocker_codes and all(
        gate["status"] == "pass"
        for gate in (manifest_gate, schedule_gate, bus_gate, loudness_gate, peak_gate)
    )

    gate_results = {
        "sample_schedule": schedule_gate,
        "bus_processing": bus_gate,
        "loudness": loudness_gate,
        "true_peak": peak_gate,
        "stem_manifest": {
            "status": "skipped",
            "reason_codes": ["MIX_MUX_BLOCKED"],
        },
        "mux_lineage": {
            "status": "skipped",
            "reason_codes": ["MIX_MUX_BLOCKED"],
        },
    }
    # Preserve early stem-set failures on the stem_manifest gate name.
    if manifest_gate["status"] == "fail":
        gate_results["stem_manifest"] = manifest_gate

    mux = {
        "video_frame_count": video_frame_count,
        "audio_sample_count": audio_sample_count,
        "endpoint_drift_samples": int(endpoint_drift_samples),
        "stem_manifest_sha256": None,
        "mix_pcm_sha256": None,
        "mux_container_sha256": None,
        "mux_lineage_sha256": None,
        "reconstructable": False,
    }

    if mix_ok:
        ordered = sorted(stems, key=lambda item: ALLOWED_STEM_BUSES.index(item["stem_bus"]))
        for item in ordered:
            item["admitted"] = True
        stem_manifest = recompute_stem_manifest_sha256(ordered)
        mix_pcm = recompute_mix_pcm_sha256(
            [item["stem_pcm_sha256"] for item in ordered],
            mix_recipe_sha256=mix_sha,
        )
        container = recompute_mux_container_sha256(
            video_timeline_sha256=video_timeline_sha256,
            mix_pcm_sha256=mix_pcm,
            video_frame_count=video_frame_count,
            audio_sample_count=audio_sample_count,
        )
        lineage = recompute_mux_lineage_sha256(
            video_timeline_sha256=video_timeline_sha256,
            stem_manifest_sha256=stem_manifest,
            mix_pcm_sha256=mix_pcm,
            mux_container_sha256=container,
            mix_recipe_sha256=mix_sha,
        )
        mux = {
            "video_frame_count": video_frame_count,
            "audio_sample_count": audio_sample_count,
            "endpoint_drift_samples": int(endpoint_drift_samples),
            "stem_manifest_sha256": stem_manifest,
            "mix_pcm_sha256": mix_pcm,
            "mux_container_sha256": container,
            "mux_lineage_sha256": lineage,
            "reconstructable": True,
        }
        gate_results["stem_manifest"] = {"status": "pass", "reason_codes": []}
        gate_results["mux_lineage"] = {"status": "pass", "reason_codes": []}
        stems = ordered
        route = "mix_mux"
        status = "mixed"
        reason = "all_required_gates_passed_for_synthetic_or_fixture_mix_mux"
        acceptance = "fixture_only" if is_synthetic else "held"
    else:
        route = "blocked"
        status = "blocked"
        reason = "fail_closed_mix_mux_schedule_loudness_or_stem_blocker"
        acceptance = "held"

    record = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "sample_accurate_mix_mux_receipt",
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "policy_sha256": sha256_file(policy_path),
        "timeline_id": timeline_id,
        "video_timeline_sha256": video_timeline_sha256,
        "expected_stems": list(expected_stems),
        "is_synthetic": is_synthetic,
        "library_authority": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "gate_results": gate_results,
        "stems": stems,
        "exclusions": exclusions,
        "mix_recipe": {**mix_body, "recipe_sha256": mix_sha},
        "mux": mux,
        "decision": {
            "route": route,
            "status": status,
            "blocker_codes": blocker_codes,
            "product_completion": False,
            "row097_acceptance": acceptance,
            "reason": reason,
        },
    }
    sealed = seal_receipt(record)
    validate_mix_mux_receipt(root, sealed)
    return sealed


def _stem(
    bus: str,
    *,
    start: int = 0,
    end: int = 48000,
    gain_db: float = -3.0,
    bus_gain_db: float = 0.0,
) -> dict[str, Any]:
    return {
        "stem_bus": bus,
        "asset_id": f"fixture:{bus}",
        "source_pcm_sha256": _stable_hash(f"source:{bus}"),
        "start_sample": start,
        "end_sample": end,
        "gain_db": gain_db,
        "bus_gain_db": bus_gain_db,
    }


def fixture_mix_packet(name: str) -> dict[str, Any]:
    # 30 fps * 2 seconds * 48000 Hz => 96000 samples.
    frames = 60
    audio_end = 96000
    if name == "compatible_stems_mix_mux":
        return {
            "timeline_id": "tl_compatible_mix_mux",
            "video_timeline_sha256": _stable_hash("video:compatible"),
            "expected_stems": ["dialogue", "foley", "ambience", "room"],
            "stems": [
                _stem("dialogue", end=audio_end, gain_db=-2.0, bus_gain_db=0.0),
                _stem("foley", start=1200, end=24000, gain_db=-4.0),
                _stem("ambience", end=audio_end, gain_db=-12.0),
                _stem("room", end=audio_end, gain_db=-9.0),
            ],
            "video_frame_count": frames,
            "endpoint_drift_samples": 0,
            "measured_lufs": -16.0,
            "measured_true_peak_dbtp": -1.2,
        }
    if name == "missing_expected_stem_blocked":
        return {
            "timeline_id": "tl_missing_stem",
            "video_timeline_sha256": _stable_hash("video:missing"),
            "expected_stems": ["dialogue", "foley", "ambience"],
            "stems": [
                _stem("dialogue", end=audio_end),
                _stem("ambience", end=audio_end, gain_db=-12.0),
            ],
            "video_frame_count": frames,
            "endpoint_drift_samples": 0,
            "measured_lufs": -16.0,
            "measured_true_peak_dbtp": -1.5,
        }
    if name == "true_peak_exceedance_rejected":
        return {
            "timeline_id": "tl_true_peak",
            "video_timeline_sha256": _stable_hash("video:peak"),
            "expected_stems": ["dialogue", "foley"],
            "stems": [
                _stem("dialogue", end=audio_end, gain_db=0.0),
                _stem("foley", end=48000, gain_db=0.0),
            ],
            "video_frame_count": frames,
            "endpoint_drift_samples": 0,
            "measured_lufs": -15.5,
            "measured_true_peak_dbtp": 0.3,
        }
    if name == "endpoint_drift_rejected":
        return {
            "timeline_id": "tl_endpoint_drift",
            "video_timeline_sha256": _stable_hash("video:drift"),
            "expected_stems": ["dialogue", "ambience"],
            "stems": [
                _stem("dialogue", end=audio_end),
                _stem("ambience", end=audio_end, gain_db=-10.0),
            ],
            "video_frame_count": frames,
            "endpoint_drift_samples": 8,
            "measured_lufs": -16.0,
            "measured_true_peak_dbtp": -1.4,
        }
    if name == "sample_schedule_mismatch_rejected":
        return {
            "timeline_id": "tl_schedule_mismatch",
            "video_timeline_sha256": _stable_hash("video:schedule"),
            "expected_stems": ["dialogue", "foley"],
            "stems": [
                _stem("dialogue", end=audio_end),
                _stem("foley", start=0, end=audio_end + 512),
            ],
            "video_frame_count": frames,
            "endpoint_drift_samples": 0,
            "measured_lufs": -16.0,
            "measured_true_peak_dbtp": -1.3,
        }
    if name == "duplicate_stem_bus_rejected":
        return {
            "timeline_id": "tl_duplicate_bus",
            "video_timeline_sha256": _stable_hash("video:duplicate"),
            "expected_stems": ["dialogue", "foley"],
            "stems": [
                _stem("dialogue", end=audio_end),
                _stem("dialogue", end=48000, gain_db=-6.0),
                _stem("foley", end=24000),
            ],
            "video_frame_count": frames,
            "endpoint_drift_samples": 0,
            "measured_lufs": -16.0,
            "measured_true_peak_dbtp": -1.1,
        }
    raise SampleAccurateMixMuxError(f"unknown_fixture:{name}")


def extract_fixture_record(root: Path, name: str) -> dict[str, Any]:
    packet = fixture_mix_packet(name)
    return build_mix_mux_record(
        root,
        timeline_id=packet["timeline_id"],
        video_timeline_sha256=packet["video_timeline_sha256"],
        expected_stems=packet["expected_stems"],
        stems_input=packet["stems"],
        video_frame_count=packet["video_frame_count"],
        endpoint_drift_samples=packet["endpoint_drift_samples"],
        measured_lufs=packet["measured_lufs"],
        measured_true_peak_dbtp=packet["measured_true_peak_dbtp"],
        is_synthetic=True,
    )


def build_library_blocker_packet(root: Path) -> dict[str, Any]:
    admissions = evaluate_all_dependency_admissions(root)
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    if not all(item["dependency_satisfied"] for item in admissions.values()):
        blocker_codes.append("ROW097_DEPENDENCIES_NOT_ACCEPTED")
    for code in (
        "DEDICATED_LIBRARY_MIX_MUX_RUNTIME_ABSENT",
        "PRODUCTION_STEM_AND_SPATIAL_ROOM_BINDING_ABSENT",
        "GENUINE_AUDIO_QA_AND_RUNTIME_PROOF_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    fixture_records = [extract_fixture_record(root, name) for name in FIXTURE_NAMES]
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-097_sample_accurate_mix_mux",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "engine_revision": ENGINE_REVISION,
        "policy_revision": POLICY_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "library_authority": False,
        "status": "HOLD_DEPENDENCIES_AND_LIBRARY_MIX_MUX_RUNTIME_ABSENT",
        "required_gates": list(REQUIRED_GATES),
        "allowed_stem_buses": list(ALLOWED_STEM_BUSES),
        "dependency_admissions": admissions,
        "policy_registry": {
            "path": str(POLICY_PATH).replace("\\", "/"),
            "revision": policy["revision"],
            "authority": policy.get("authority"),
            "sha256": sha256_file(policy_path),
        },
        "schema": {
            "path": str(SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(resolve_under(root, SCHEMA_PATH, "schema")),
        },
        "fixture_calibration": {
            "authority": "synthetic_non_library",
            "fixture_count": len(fixture_records),
            "records": fixture_records,
            "determinism_note": (
                "Fixture records prove sample schedule, bus processing, loudness, "
                "true-peak, stem-manifest recomputation, and mux-lineage stability; "
                "they do not accept Row097 library completion or substitute for genuine audio QA."
            ),
        },
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row097_acceptance": "held",
            "product_completion": False,
            "runtime_completion": False,
            "safe_next_action": (
                "Accept Rows091, 093, 094, 095, and 096; bind production stems with "
                "spatial/room renders to a sample-accurate schedule; execute mix/mux with "
                "loudness and true-peak gates; seal stem-manifest and mux lineage hashes; "
                "pass waveform/spectrogram/AV review; then replace this hold packet."
            ),
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mode", choices=("library", "fixture"), default="library")
    parser.add_argument("--fixture", default="compatible_stems_mix_mux")
    parser.add_argument("--output", default=str(DEFAULT_EVIDENCE))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise SampleAccurateMixMuxError("root_must_be_canonical_project_root")
    output = resolve_under(root, Path(args.output), "output")
    if args.mode == "fixture":
        payload = extract_fixture_record(root, args.fixture)
    else:
        payload = build_library_blocker_packet(root)
        if payload["decision"]["status"] != "blocked":
            raise SampleAccurateMixMuxError(
                "library_mode_must_remain_fail_closed_until_dependencies_accepted"
            )
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "status": payload.get("status") or payload["decision"]["route"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
