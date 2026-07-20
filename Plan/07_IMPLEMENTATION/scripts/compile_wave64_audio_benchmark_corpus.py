#!/usr/bin/env python3
"""Fail-closed Wave64 Row109 audio benchmark/calibration/held-out/adversarial corpus.

Fixture/copies-only slice: compile synthetic annotated descriptors into a partitioned
corpus manifest with immutable truth bindings. No live full-library PCM decode.
Production completion remains false until genuine annotated media + visual QA exist.
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
SCHEMA_PATH = Path("Plan/08_SCHEMAS/audio_benchmark_corpus_manifest.schema.json")
POLICY_PATH = Path(
    "Plan/10_REGISTRIES/wave64_row109_audio_benchmark_corpus_policy_registry.json"
)
FIXTURE_DIR = Path("Plan/Instructions/QA/Evidence/Wave64/fixtures/row109")
BENCHMARK_DIR = Path("Plan/Instructions/QA/Evidence/Wave64/benchmarks/row109")
DEFAULT_EVIDENCE = Path(
    "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-109_audio_benchmark_corpus.json"
)
DEFAULT_MANIFEST = BENCHMARK_DIR / "audio_benchmark_corpus_manifest.json"
DEPENDENCY_DELTAS: dict[str, Path] = {
    "TRK-W64-067": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-067_PLANNING_AUTHORITY_CURRENT_DELTA_20260719.json"
    ),
    "TRK-W64-068": Path(
        "Plan/Instructions/QA/Evidence/Wave64/TRK-W64-068_RIGHTS_PROVENANCE_CURRENT_DELTA_20260719.json"
    ),
}

COMPILER_REVISION = "wave64_row109_audio_benchmark_corpus_compiler_v0.1.0"
POLICY_REVISION = "wave64_row109_audio_benchmark_corpus_policy_v0.1.0"
CORPUS_REVISION = "wave64_row109_synthetic_benchmark_corpus_v0.1.0"
TRACKER_ID = "TRK-W64-109"
ITEM_ID = "ITEM-W64-109"
SCHEMA_VERSION = "1.0.0"

REQUIRED_GATES = (
    "coverage_matrix",
    "annotation_authority",
    "partition_separation",
    "adversarial_cases",
    "truth_integrity",
)
REQUIRED_PARTITIONS = ("train", "calibration", "held_out_test", "adversarial")
REQUIRED_EVENT_FAMILIES = (
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
)
REQUIRED_MATERIALS = ("hardwood", "carpet", "tile", "concrete", "ambiguous_surface")
REQUIRED_FOOTWEAR = ("bare_foot", "soft_shoe", "sneaker", "boot", "hard_heel")
REQUIRED_ADVERSARIAL_ROLES = (
    "filename_semantic_mismatch",
    "generated_candidate_truth_contamination",
    "partition_leak_attempt",
    "wrong_material_timing_drift",
)
PARTITION_TRUTH_RULES = {
    "train": frozenset({"reference_truth"}),
    "calibration": frozenset({"reference_truth"}),
    "held_out_test": frozenset({"reference_truth"}),
    "adversarial": frozenset({"generated_candidate", "adversarial_decoy"}),
}


class AudioBenchmarkCorpusError(ValueError):
    """Raised when Row109 corpus policy violates fail-closed authority."""


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AudioBenchmarkCorpusError(f"{label}_outside_project_root") from exc
    return path


def load_policy(root: Path) -> dict[str, Any]:
    path = resolve_under(root, POLICY_PATH, "policy_registry")
    payload = load_json(path)
    if payload.get("revision") != POLICY_REVISION:
        raise AudioBenchmarkCorpusError("policy_registry_revision_mismatch")
    if tuple(payload.get("required_gates") or ()) != REQUIRED_GATES:
        raise AudioBenchmarkCorpusError("policy_required_gates_mismatch")
    if tuple(payload.get("required_partitions") or ()) != REQUIRED_PARTITIONS:
        raise AudioBenchmarkCorpusError("policy_required_partitions_mismatch")
    if tuple(payload.get("required_event_families") or ()) != REQUIRED_EVENT_FAMILIES:
        raise AudioBenchmarkCorpusError("policy_required_event_families_mismatch")
    if payload.get("media_policy", {}).get("pcm_decode_allowed") is not False:
        raise AudioBenchmarkCorpusError("policy_must_forbid_pcm_decode")
    if payload.get("media_policy", {}).get("live_full_library_scan_allowed") is not False:
        raise AudioBenchmarkCorpusError("policy_must_forbid_live_full_library_scan")
    return payload


def evaluate_dependency_admission(
    root: Path,
    *,
    tracker_id: str,
    delta_path: Path,
) -> dict[str, Any]:
    path = resolve_under(root, delta_path, f"{tracker_id}_delta")
    if not path.is_file():
        return {
            "tracker_id": tracker_id,
            "delta_path": str(delta_path).replace("\\", "/"),
            "delta_exists": False,
            "delta_sha256": None,
            "row_complete": False,
            "dependency_satisfied": False,
            "blocker_codes": [f"{tracker_id}_CURRENT_DELTA_ABSENT"],
        }
    payload = load_json(path)
    row_complete = bool(payload.get("row_complete") is True)
    # Accept planning/rights authority even when runtime completion remains false.
    accepted = row_complete or str(payload.get("status", "")).startswith("PASS_")
    decision = payload.get("decision") or {}
    if isinstance(decision, dict) and decision.get("status") == "accepted":
        accepted = True
    if payload.get("planning_authority_accepted") is True:
        accepted = True
    if payload.get("rights_decision_authority_accepted") is True:
        accepted = True
    blockers: list[str] = []
    if not accepted:
        blockers.append(f"{tracker_id}_NOT_EVIDENCE_ACCEPTED")
    return {
        "tracker_id": tracker_id,
        "delta_path": str(delta_path).replace("\\", "/"),
        "delta_exists": True,
        "delta_sha256": sha256_file(path),
        "row_complete": row_complete,
        "dependency_satisfied": accepted,
        "blocker_codes": blockers,
    }


def evaluate_all_dependency_admissions(root: Path) -> dict[str, dict[str, Any]]:
    return {
        tracker_id: evaluate_dependency_admission(
            root, tracker_id=tracker_id, delta_path=delta_path
        )
        for tracker_id, delta_path in DEPENDENCY_DELTAS.items()
    }


def _case_spec(
    *,
    case_id: str,
    partition: str,
    event_family: str,
    material: str,
    footwear: str,
    room: str,
    ownership: str,
    camera: str,
    truth_class: str,
    silent_event: bool = False,
    adversarial_role: str | None = None,
    generated_from_eval_pass: bool = False,
    filename_claim: str | None = None,
    timing_drift_ms: int = 0,
    wrong_material_claim: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "partition": partition,
        "event_family": event_family,
        "material": material,
        "footwear": footwear,
        "room": room,
        "ownership": ownership,
        "camera": camera,
        "truth_class": truth_class,
        "adversarial_role": adversarial_role,
        "annotation": {
            "annotator_role": "synthetic_fixture_authority",
            "silent_event": silent_event,
            "labels": {
                "event_family": event_family,
                "material": material,
                "footwear": footwear,
                "room": room,
                "ownership": ownership,
                "camera": camera,
                "filename_claim": filename_claim,
                "timing_drift_ms": timing_drift_ms,
                "wrong_material_claim": wrong_material_claim,
            },
            "generated_from_eval_pass": generated_from_eval_pass,
            "rights_bound": True,
        },
    }


def fixture_case_specs() -> list[dict[str, Any]]:
    """Deterministic synthetic corpus covering required families/partitions/adversarial roles."""
    materials = list(REQUIRED_MATERIALS)
    footwear = list(REQUIRED_FOOTWEAR)
    specs: list[dict[str, Any]] = []

    # Train: compact representative subset (not used for final calibration or held-out truth).
    for idx, family in enumerate(
        ("footstep", "heel_strike", "body_contact", "clothing", "prop")
    ):
        specs.append(
            _case_spec(
                case_id=f"train_{family}_{idx:02d}",
                partition="train",
                event_family=family,
                material=materials[idx % len(materials)],
                footwear=footwear[idx % len(footwear)],
                room="interior_dry",
                ownership="single_actor_visible",
                camera="fixed",
                truth_class="reference_truth",
            )
        )

    # Calibration + held-out: every required event family, disjoint case ids.
    for idx, family in enumerate(REQUIRED_EVENT_FAMILIES):
        material = materials[idx % len(materials)]
        shoe = footwear[idx % len(footwear)]
        silent = family == "intentional_silence"
        ownership = (
            "multi_actor_shared"
            if family == "multi_actor"
            else "occluded_partial"
            if family == "occlusion"
            else "single_actor_visible"
        )
        camera = "cut_boundary" if family == "cut_boundary" else "fixed"
        room = "interior_reverb" if family == "room_ambience" else "interior_dry"
        if family == "ambiguous_material":
            material = "ambiguous_surface"
        specs.append(
            _case_spec(
                case_id=f"cal_{family}_{idx:02d}",
                partition="calibration",
                event_family=family,
                material=material,
                footwear=shoe,
                room=room,
                ownership=ownership,
                camera=camera,
                truth_class="reference_truth",
                silent_event=silent,
            )
        )
        specs.append(
            _case_spec(
                case_id=f"holdout_{family}_{idx:02d}",
                partition="held_out_test",
                event_family=family,
                material=materials[(idx + 1) % len(materials)]
                if family != "ambiguous_material"
                else "ambiguous_surface",
                footwear=footwear[(idx + 1) % len(footwear)],
                room="exterior_dry" if family != "room_ambience" else "interior_reverb",
                ownership=ownership,
                camera="moving" if family not in {"cut_boundary", "intentional_silence"} else camera,
                truth_class="reference_truth",
                silent_event=silent,
            )
        )

    # Adversarial partition: required fail-closed roles (never reference truth).
    specs.extend(
        [
            _case_spec(
                case_id="adv_filename_semantic_mismatch_01",
                partition="adversarial",
                event_family="footstep",
                material="hardwood",
                footwear="sneaker",
                room="interior_dry",
                ownership="single_actor_visible",
                camera="fixed",
                truth_class="adversarial_decoy",
                adversarial_role="filename_semantic_mismatch",
                filename_claim="metal_door_slam.wav",
            ),
            _case_spec(
                case_id="adv_generated_candidate_truth_contamination_01",
                partition="adversarial",
                event_family="heel_strike",
                material="tile",
                footwear="hard_heel",
                room="interior_dry",
                ownership="single_actor_visible",
                camera="fixed",
                truth_class="generated_candidate",
                adversarial_role="generated_candidate_truth_contamination",
                generated_from_eval_pass=True,
            ),
            _case_spec(
                case_id="adv_partition_leak_attempt_01",
                partition="adversarial",
                event_family="body_contact",
                material="carpet",
                footwear="soft_shoe",
                room="interior_dry",
                ownership="single_actor_visible",
                camera="fixed",
                truth_class="adversarial_decoy",
                adversarial_role="partition_leak_attempt",
            ),
            _case_spec(
                case_id="adv_wrong_material_timing_drift_01",
                partition="adversarial",
                event_family="prop",
                material="metal",
                footwear="boot",
                room="interior_reverb",
                ownership="single_actor_visible",
                camera="fixed",
                truth_class="generated_candidate",
                adversarial_role="wrong_material_timing_drift",
                timing_drift_ms=120,
                wrong_material_claim="glass",
            ),
        ]
    )
    return specs


def truth_payload_for_case(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": spec["case_id"],
        "partition": spec["partition"],
        "event_family": spec["event_family"],
        "material": spec["material"],
        "footwear": spec["footwear"],
        "room": spec["room"],
        "ownership": spec["ownership"],
        "camera": spec["camera"],
        "truth_class": spec["truth_class"],
        "adversarial_role": spec.get("adversarial_role"),
        "annotation": {
            "silent_event": spec["annotation"]["silent_event"],
            "labels": spec["annotation"]["labels"],
            "generated_from_eval_pass": spec["annotation"]["generated_from_eval_pass"],
        },
    }


def materialize_fixture_files(root: Path) -> list[Path]:
    fixture_root = resolve_under(root, FIXTURE_DIR, "fixture_dir")
    cases_dir = fixture_root / "cases"
    desc_dir = fixture_root / "descriptors"
    written: list[Path] = []
    index: list[dict[str, str]] = []
    for spec in fixture_case_specs():
        case_name = f"{spec['case_id']}.json"
        case_path = cases_dir / case_name
        descriptor_rel = (
            Path("Plan/Instructions/QA/Evidence/Wave64/fixtures/row109/descriptors")
            / f"{spec['case_id']}.json"
        )
        descriptor_payload = {
            "descriptor_id": spec["case_id"],
            "kind": "synthetic_fixture_descriptor",
            "pcm_bytes": None,
            "decode_invoked": False,
            "live_full_library_scan": False,
            "event_family": spec["event_family"],
            "notes": "Synthetic annotation descriptor only; no PCM payload.",
        }
        desc_path = resolve_under(root, descriptor_rel, "descriptor")
        write_json(desc_path, descriptor_payload)
        written.append(desc_path)

        case_payload = deepcopy(spec)
        case_payload["media_locator"] = {
            "kind": "synthetic_fixture_descriptor",
            "descriptor_path": str(descriptor_rel).replace("\\", "/"),
            "pcm_bytes": None,
            "decode_invoked": False,
        }
        write_json(case_path, case_payload)
        written.append(case_path)
        index.append(
            {
                "case_id": spec["case_id"],
                "partition": spec["partition"],
                "fixture": f"cases/{case_name}",
            }
        )
    index_path = fixture_root / "corpus_case_index.json"
    write_json(
        index_path,
        {
            "schema_version": "1.0.0",
            "tracker_id": TRACKER_ID,
            "corpus_revision": CORPUS_REVISION,
            "authority": "synthetic_fixture_only",
            "pcm_decode_invoked": False,
            "live_full_library_scan": False,
            "case_count": len(index),
            "cases": index,
        },
    )
    written.append(index_path)
    return written


def load_fixture_cases(root: Path) -> list[dict[str, Any]]:
    fixture_root = resolve_under(root, FIXTURE_DIR, "fixture_dir")
    index_path = fixture_root / "corpus_case_index.json"
    if not index_path.is_file():
        raise AudioBenchmarkCorpusError("fixture_corpus_case_index_absent")
    index = load_json(index_path)
    cases: list[dict[str, Any]] = []
    for entry in index.get("cases") or []:
        rel = entry.get("fixture")
        if not rel:
            raise AudioBenchmarkCorpusError("fixture_index_entry_missing_fixture")
        path = resolve_under(root, FIXTURE_DIR / rel, "fixture_case")
        payload = load_json(path)
        payload["_source_fixture"] = str((FIXTURE_DIR / rel).as_posix())
        payload["_source_fixture_path"] = path
        cases.append(payload)
    if not cases:
        raise AudioBenchmarkCorpusError("fixture_cases_empty")
    return cases


def compile_case(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    source_path: Path = raw["_source_fixture_path"]
    source_fixture = raw["_source_fixture"]
    spec = {k: v for k, v in raw.items() if not k.startswith("_")}

    if spec.get("partition") not in REQUIRED_PARTITIONS:
        raise AudioBenchmarkCorpusError(f"unknown_partition:{spec.get('partition')}")
    if spec.get("truth_class") not in PARTITION_TRUTH_RULES[spec["partition"]]:
        raise AudioBenchmarkCorpusError(
            f"partition_truth_rule_violation:{spec['case_id']}:{spec['partition']}:{spec['truth_class']}"
        )
    annotation = spec.get("annotation") or {}
    if annotation.get("annotator_role") not in {
        "synthetic_fixture_authority",
        "human_gold",
    }:
        raise AudioBenchmarkCorpusError(f"annotation_authority_missing:{spec['case_id']}")
    if annotation.get("rights_bound") is not True:
        raise AudioBenchmarkCorpusError(f"rights_bound_required:{spec['case_id']}")
    if (
        annotation.get("generated_from_eval_pass") is True
        and spec.get("truth_class") == "reference_truth"
    ):
        raise AudioBenchmarkCorpusError(
            f"generated_candidate_cannot_contaminate_reference_truth:{spec['case_id']}"
        )

    media = spec.get("media_locator") or {}
    if media.get("kind") != "synthetic_fixture_descriptor":
        raise AudioBenchmarkCorpusError(f"unsupported_media_kind:{spec['case_id']}")
    if media.get("decode_invoked") is not False:
        raise AudioBenchmarkCorpusError(f"pcm_decode_forbidden:{spec['case_id']}")
    if media.get("pcm_bytes") is not None:
        raise AudioBenchmarkCorpusError(f"pcm_bytes_forbidden:{spec['case_id']}")
    descriptor_rel = Path(media["descriptor_path"])
    descriptor_path = resolve_under(root, descriptor_rel, "descriptor")
    if not descriptor_path.is_file():
        raise AudioBenchmarkCorpusError(f"descriptor_absent:{spec['case_id']}")
    descriptor = load_json(descriptor_path)
    if descriptor.get("decode_invoked") is not False:
        raise AudioBenchmarkCorpusError(f"descriptor_decode_forbidden:{spec['case_id']}")
    if descriptor.get("pcm_bytes") is not None:
        raise AudioBenchmarkCorpusError(f"descriptor_pcm_forbidden:{spec['case_id']}")

    truth_sha = sha256_bytes(canonical_json_bytes(truth_payload_for_case(spec)))
    return {
        "case_id": spec["case_id"],
        "partition": spec["partition"],
        "event_family": spec["event_family"],
        "material": spec["material"],
        "footwear": spec["footwear"],
        "room": spec["room"],
        "ownership": spec["ownership"],
        "camera": spec["camera"],
        "truth_class": spec["truth_class"],
        "adversarial_role": spec.get("adversarial_role"),
        "annotation": annotation,
        "media_locator": {
            "kind": "synthetic_fixture_descriptor",
            "descriptor_path": str(descriptor_rel).replace("\\", "/"),
            "descriptor_sha256": sha256_file(descriptor_path),
            "pcm_bytes": None,
            "decode_invoked": False,
        },
        "truth_sha256": truth_sha,
        "source_fixture": source_fixture.replace("\\", "/"),
        "source_fixture_sha256": sha256_file(source_path),
    }


def build_coverage_matrix(cases: list[dict[str, Any]]) -> dict[str, Any]:
    families = sorted({c["event_family"] for c in cases})
    materials = sorted({c["material"] for c in cases if c["truth_class"] == "reference_truth"})
    footwear = sorted({c["footwear"] for c in cases if c["truth_class"] == "reference_truth"})
    partitions_with_truth = sorted(
        {
            c["partition"]
            for c in cases
            if c["truth_class"] == "reference_truth"
            and c["partition"] in {"train", "calibration", "held_out_test"}
        }
    )
    cal_families = {c["event_family"] for c in cases if c["partition"] == "calibration"}
    hold_families = {c["event_family"] for c in cases if c["partition"] == "held_out_test"}
    overlap = sorted(cal_families & hold_families)
    coverage_complete = (
        set(REQUIRED_EVENT_FAMILIES).issubset(cal_families)
        and set(REQUIRED_EVENT_FAMILIES).issubset(hold_families)
        and set(REQUIRED_EVENT_FAMILIES).issubset(set(overlap))
        and set(REQUIRED_MATERIALS).issubset(set(materials))
        and set(REQUIRED_FOOTWEAR).issubset(set(footwear))
        and set(partitions_with_truth) >= {"train", "calibration", "held_out_test"}
    )
    return {
        "event_families_covered": families,
        "materials_covered": materials,
        "footwear_covered": footwear,
        "partitions_with_reference_truth": partitions_with_truth,
        "calibration_and_held_out_overlap_families": overlap,
        "coverage_complete": coverage_complete,
    }


def build_partition_manifest(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_partition: dict[str, list[dict[str, Any]]] = {p: [] for p in REQUIRED_PARTITIONS}
    for case in cases:
        by_partition[case["partition"]].append(case)

    case_ids = [c["case_id"] for c in cases]
    if len(case_ids) != len(set(case_ids)):
        raise AudioBenchmarkCorpusError("partition_separation_case_id_collision")

    # Held-out must not reuse calibration/train media descriptors.
    media_by_partition: dict[str, set[str]] = {}
    for partition, items in by_partition.items():
        media_by_partition[partition] = {
            item["media_locator"]["descriptor_sha256"] for item in items
        }
    leak = media_by_partition["held_out_test"] & (
        media_by_partition["train"] | media_by_partition["calibration"]
    )
    if leak:
        raise AudioBenchmarkCorpusError("partition_separation_media_leak_into_held_out")

    # Adversarial partition-leak decoy must not share ids with truth partitions.
    truth_ids = {
        c["case_id"]
        for c in cases
        if c["partition"] in {"train", "calibration", "held_out_test"}
    }
    adv_ids = {c["case_id"] for c in by_partition["adversarial"]}
    if truth_ids & adv_ids:
        raise AudioBenchmarkCorpusError("partition_separation_adversarial_id_collision")

    stats: dict[str, Any] = {}
    for partition in REQUIRED_PARTITIONS:
        items = by_partition[partition]
        stats[partition] = {
            "case_count": len(items),
            "case_ids": sorted(item["case_id"] for item in items),
            "truth_classes": sorted({item["truth_class"] for item in items}),
        }
        if stats[partition]["case_count"] < 1:
            raise AudioBenchmarkCorpusError(f"partition_empty:{partition}")
    stats["separation_ok"] = True
    return stats


def build_adversarial_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    adv = [c for c in cases if c["partition"] == "adversarial"]
    roles = sorted({c["adversarial_role"] for c in adv if c.get("adversarial_role")})
    blocked = 0
    for case in adv:
        if case["adversarial_role"] == "generated_candidate_truth_contamination":
            if case["truth_class"] != "generated_candidate":
                raise AudioBenchmarkCorpusError("contamination_case_must_be_generated_candidate")
            if case["annotation"].get("generated_from_eval_pass") is not True:
                raise AudioBenchmarkCorpusError("contamination_case_must_flag_eval_pass")
            blocked += 1
        if case["truth_class"] == "reference_truth":
            raise AudioBenchmarkCorpusError("adversarial_partition_cannot_hold_reference_truth")
    complete = set(REQUIRED_ADVERSARIAL_ROLES).issubset(set(roles)) and blocked >= 1
    return {
        "required_roles": list(REQUIRED_ADVERSARIAL_ROLES),
        "roles_present": roles,
        "blocked_contamination_count": blocked,
        "complete": complete,
    }


def build_truth_integrity(cases: list[dict[str, Any]]) -> dict[str, Any]:
    immutable = all(len(c["truth_sha256"]) == 64 for c in cases)
    no_contam = all(
        not (
            c["annotation"].get("generated_from_eval_pass") is True
            and c["truth_class"] == "reference_truth"
        )
        for c in cases
    )
    partition_ok = all(
        c["truth_class"] in PARTITION_TRUTH_RULES[c["partition"]] for c in cases
    )
    # Recompute truth hashes to prove immutability binding.
    for case in cases:
        expected = sha256_bytes(
            canonical_json_bytes(
                truth_payload_for_case(
                    {
                        "case_id": case["case_id"],
                        "partition": case["partition"],
                        "event_family": case["event_family"],
                        "material": case["material"],
                        "footwear": case["footwear"],
                        "room": case["room"],
                        "ownership": case["ownership"],
                        "camera": case["camera"],
                        "truth_class": case["truth_class"],
                        "adversarial_role": case.get("adversarial_role"),
                        "annotation": case["annotation"],
                    }
                )
            )
        )
        if expected != case["truth_sha256"]:
            raise AudioBenchmarkCorpusError(f"truth_sha256_mismatch:{case['case_id']}")
    integrity_ok = immutable and no_contam and partition_ok
    return {
        "immutable_truth_bound": immutable,
        "generated_cannot_contaminate_reference": no_contam,
        "partition_truth_rules_ok": partition_ok,
        "integrity_ok": integrity_ok,
    }


def validate_manifest(root: Path, manifest: dict[str, Any]) -> None:
    schema = load_json(resolve_under(root, SCHEMA_PATH, "schema"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda err: list(err.path),
    )
    if errors:
        raise AudioBenchmarkCorpusError("schema_validation_failed:" + errors[0].message)
    if manifest["pcm_decode_invoked"] is not False:
        raise AudioBenchmarkCorpusError("pcm_decode_must_be_false")
    if manifest["live_full_library_scan"] is not False:
        raise AudioBenchmarkCorpusError("live_full_library_scan_must_be_false")
    if manifest["library_authority"] is not False:
        raise AudioBenchmarkCorpusError("library_authority_must_be_false")
    if manifest["decision"]["product_completion"] is not False:
        raise AudioBenchmarkCorpusError("product_completion_must_be_false")
    if manifest["decision"]["runtime_completion"] is not False:
        raise AudioBenchmarkCorpusError("runtime_completion_must_be_false")


def compile_corpus_manifest(root: Path) -> dict[str, Any]:
    policy = load_policy(root)
    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    admissions = evaluate_all_dependency_admissions(root)
    raw_cases = load_fixture_cases(root)
    cases = [compile_case(root, raw) for raw in raw_cases]
    coverage = build_coverage_matrix(cases)
    partitions = build_partition_manifest(cases)
    adversarial = build_adversarial_summary(cases)
    truth = build_truth_integrity(cases)

    gates = {
        "coverage_matrix": bool(coverage["coverage_complete"]),
        "annotation_authority": all(
            c["annotation"]["annotator_role"]
            in {"synthetic_fixture_authority", "human_gold"}
            and c["annotation"]["rights_bound"] is True
            for c in cases
        ),
        "partition_separation": bool(partitions["separation_ok"]),
        "adversarial_cases": bool(adversarial["complete"]),
        "truth_integrity": bool(truth["integrity_ok"]),
    }
    if not all(gates.values()):
        raise AudioBenchmarkCorpusError(
            "fixture_gates_not_satisfied:"
            + ",".join(name for name, ok in gates.items() if not ok)
        )

    deps_ok = all(item["dependency_satisfied"] for item in admissions.values())
    status = "fixture_corpus_compiled" if deps_ok else "blocked"
    acceptance = "fixture_only" if deps_ok else "held"
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "record_type": "audio_benchmark_corpus_manifest",
        "compiler_revision": COMPILER_REVISION,
        "policy_revision": policy["revision"],
        "policy_sha256": sha256_file(policy_path),
        "corpus_revision": CORPUS_REVISION,
        "is_synthetic": True,
        "library_authority": False,
        "pcm_decode_invoked": False,
        "live_full_library_scan": False,
        "dependency_admissions": admissions,
        "required_gates": list(REQUIRED_GATES),
        "coverage_matrix": coverage,
        "partition_manifest": partitions,
        "adversarial_cases": adversarial,
        "truth_integrity": truth,
        "cases": sorted(cases, key=lambda item: item["case_id"]),
        "decision": {
            "status": status,
            "row109_acceptance": acceptance,
            "product_completion": False,
            "runtime_completion": False,
            "gates_satisfied": gates,
            "safe_next_action": (
                "Retain synthetic partition/truth gates; ingest genuine annotated clips "
                "under the same immutable truth contract; run combined frame/contact/audio "
                "review; then replace fixture-only acceptance without contaminating "
                "held-out reference truth."
            ),
        },
    }
    sealed = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    manifest["manifest_sha256"] = sha256_bytes(canonical_json_bytes(sealed))
    validate_manifest(root, manifest)
    return manifest


def verify_manifest_integrity(root: Path, manifest: dict[str, Any]) -> None:
    sealed = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected = sha256_bytes(canonical_json_bytes(sealed))
    if manifest.get("manifest_sha256") != expected:
        raise AudioBenchmarkCorpusError("manifest_sha256_mismatch")
    validate_manifest(root, manifest)


def attempt_truth_contamination(root: Path) -> None:
    """Probe helper: promoting generated_from_eval_pass into reference_truth must fail."""
    cases = load_fixture_cases(root)
    target = None
    for raw in cases:
        if raw.get("adversarial_role") == "generated_candidate_truth_contamination":
            target = deepcopy(raw)
            break
    if target is None:
        raise AudioBenchmarkCorpusError("contamination_probe_target_absent")
    target["partition"] = "held_out_test"
    target["truth_class"] = "reference_truth"
    try:
        compile_case(root, target)
    except AudioBenchmarkCorpusError as exc:
        if "generated_candidate_cannot_contaminate_reference_truth" in str(exc):
            return
        raise
    raise AudioBenchmarkCorpusError("contamination_probe_failed_to_block")


def build_hold_packet(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    admissions = manifest["dependency_admissions"]
    blocker_codes: list[str] = []
    for admission in admissions.values():
        blocker_codes.extend(admission["blocker_codes"])
    for code in (
        "GENUINE_ANNOTATED_MEDIA_CORPUS_ABSENT",
        "COMBINED_FRAME_CONTACT_AUDIO_REVIEW_ABSENT",
        "PRODUCTION_BENCHMARK_AUTHORITY_ABSENT",
        "HELD_OUT_RUNTIME_PROOF_ABSENT",
    ):
        if code not in blocker_codes:
            blocker_codes.append(code)

    policy_path = resolve_under(root, POLICY_PATH, "policy_registry")
    schema_path = resolve_under(root, SCHEMA_PATH, "schema")
    manifest_path = resolve_under(root, DEFAULT_MANIFEST, "manifest")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "TRK-W64-109_audio_benchmark_corpus",
        "tracker_id": TRACKER_ID,
        "item_id": ITEM_ID,
        "compiler_revision": COMPILER_REVISION,
        "policy_revision": POLICY_REVISION,
        "corpus_revision": CORPUS_REVISION,
        "row_complete": False,
        "implementation_completion_claimed": False,
        "runtime_completion_claimed": False,
        "production_authority": False,
        "status": (
            "HOLD_SYNTHETIC_FIXTURE_CORPUS_SLICE_PRESENT_"
            "GENUINE_ANNOTATED_MEDIA_AND_VISUAL_QA_ABSENT"
        ),
        "required_gates": list(REQUIRED_GATES),
        "dependency_admissions": admissions,
        "policy_registry": {
            "path": str(POLICY_PATH).replace("\\", "/"),
            "revision": POLICY_REVISION,
            "sha256": sha256_file(policy_path),
        },
        "schema": {
            "path": str(SCHEMA_PATH).replace("\\", "/"),
            "sha256": sha256_file(schema_path),
        },
        "fixture_corpus": {
            "authority": "synthetic_non_production",
            "fixture_dir": str(FIXTURE_DIR).replace("\\", "/"),
            "benchmark_dir": str(BENCHMARK_DIR).replace("\\", "/"),
            "manifest_path": str(DEFAULT_MANIFEST).replace("\\", "/"),
            "manifest_sha256": manifest["manifest_sha256"],
            "manifest_bytes": manifest_path.stat().st_size if manifest_path.is_file() else None,
            "case_count": len(manifest["cases"]),
            "pcm_decode_invoked": False,
            "live_full_library_scan": False,
            "determinism_note": (
                "Synthetic descriptors prove coverage-matrix, annotation-authority, "
                "partition-separation, adversarial contamination blocking, and immutable "
                "truth hashes without decoding library PCM or claiming production completion."
            ),
        },
        "gate_results": manifest["decision"]["gates_satisfied"],
        "coverage_matrix": manifest["coverage_matrix"],
        "partition_manifest": {
            key: {
                "case_count": value["case_count"],
                "truth_classes": value["truth_classes"],
            }
            if key != "separation_ok"
            else value
            for key, value in manifest["partition_manifest"].items()
        },
        "adversarial_cases": manifest["adversarial_cases"],
        "truth_integrity": manifest["truth_integrity"],
        "blocker_codes": blocker_codes,
        "decision": {
            "status": "blocked",
            "row109_acceptance": "fixture_only",
            "product_completion": False,
            "runtime_completion": False,
            "dependency_067_068_satisfied": all(
                item["dependency_satisfied"] for item in admissions.values()
            ),
            "safe_next_action": manifest["decision"]["safe_next_action"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument(
        "--mode",
        choices=("hold", "manifest", "write-fixtures", "probe-contamination"),
        default="hold",
    )
    parser.add_argument("--output", default="")
    parser.add_argument("--manifest-output", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if root != ROOT.resolve() and root != Path("C:/Comfy_UI_Main").resolve():
        raise AudioBenchmarkCorpusError("root_must_be_canonical_project_root")

    if args.mode == "write-fixtures":
        written = materialize_fixture_files(root)
        print(
            json.dumps(
                {"mode": "write-fixtures", "written": len(written), "fixture_dir": str(FIXTURE_DIR)},
                sort_keys=True,
            )
        )
        return 0

    if args.mode == "probe-contamination":
        attempt_truth_contamination(root)
        print(json.dumps({"mode": "probe-contamination", "result": "BLOCKED_AS_REQUIRED"}, sort_keys=True))
        return 0

    manifest = compile_corpus_manifest(root)
    manifest_output = resolve_under(root, Path(args.manifest_output), "manifest_output")
    write_json(manifest_output, manifest)
    verify_manifest_integrity(root, load_json(manifest_output))

    if args.mode == "manifest":
        output = manifest_output
        payload = manifest
    else:
        payload = build_hold_packet(root, manifest)
        if payload["row_complete"] is not False:
            raise AudioBenchmarkCorpusError("row_complete_must_remain_false")
        if payload["decision"]["product_completion"] is not False:
            raise AudioBenchmarkCorpusError("product_completion_must_remain_false")
        output = resolve_under(
            root,
            Path(args.output) if args.output else DEFAULT_EVIDENCE,
            "output",
        )
        write_json(output, payload)

    print(
        json.dumps(
            {
                "output": str(output),
                "manifest_output": str(manifest_output),
                "status": payload.get("status") or payload["decision"]["status"],
                "row_complete": payload.get("row_complete", False),
                "case_count": len(manifest["cases"]),
                "manifest_sha256": manifest["manifest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
