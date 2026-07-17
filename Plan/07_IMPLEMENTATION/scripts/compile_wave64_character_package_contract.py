#!/usr/bin/env python3
"""Compile and validate the synthetic Wave64 Rows154-158 package slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = Path("Plan/10_REGISTRIES/wave64_character_package_compilation_fixture.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_character_package_compilation_contract.schema.json")
EMBEDDED_SCHEMAS = {
    "character_package": Path("Plan/08_SCHEMAS/character_package_revision.schema.json"),
    "scene_package": Path("Plan/08_SCHEMAS/scene_package.schema.json"),
    "shot_pose_package": Path("Plan/08_SCHEMAS/shot_pose_package.schema.json"),
    "pass_specification": Path("Plan/08_SCHEMAS/multimodal_pass_specification.schema.json"),
    "artifact_manifest": Path("Plan/08_SCHEMAS/multimodal_artifact_manifest.schema.json"),
}
COMMON_SCHEMAS = (
    Path("Plan/08_SCHEMAS/model_intelligence_common.schema.json"),
    Path("Plan/08_SCHEMAS/multimodal_contract_common.schema.json"),
)
REQUIRED_STATE_TYPES = {
    "morphology", "surface", "hair", "makeup", "wardrobe", "accessory", "material", "voice"
}
FORBIDDEN_CHARACTER_KEY = re.compile(r"(^|_)(path|uri|node_id|node_ids|comfy_node_id)($|_)")
WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class CompilationError(ValueError):
    """Raised when a package cannot be compiled without hidden or mutable state."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema_registry(root: Path) -> Registry:
    resources: list[tuple[str, Resource[Any]]] = []
    for relative in (*COMMON_SCHEMAS, *EMBEDDED_SCHEMAS.values()):
        schema = load_json(root / relative)
        schema_id = schema.get("$id")
        if schema_id:
            resources.append((schema_id, Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def validate_schema(instance: Any, schema: dict[str, Any], registry: Registry, label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CompilationError(f"schema_validation_failed:{label}:{location}:{first.message}")


def walk(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, (*path, str(index)))


def validate_no_hidden_character_paths(contract: dict[str, Any]) -> None:
    for section_name in ("character_package", "reference_intake", "character_states"):
        for path, value in walk(contract[section_name], (section_name,)):
            key = path[-1] if path else ""
            if FORBIDDEN_CHARACTER_KEY.search(key):
                raise CompilationError(f"fixed_character_path_or_node_key_forbidden:{'.'.join(path)}")
            if isinstance(value, str) and WINDOWS_PATH.match(value):
                raise CompilationError(f"fixed_character_path_forbidden:{'.'.join(path)}")


def validate_payload_hashes(value: Any, path: tuple[str, ...] = ()) -> int:
    count = 0
    if isinstance(value, dict):
        if "payload" in value and "payload_sha256" in value:
            expected = sha256_value(value["payload"])
            if value["payload_sha256"] != expected:
                raise CompilationError(f"payload_hash_mismatch:{'.'.join(path) or '$'}")
            count += 1
        for key, child in value.items():
            count += validate_payload_hashes(child, (*path, str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            count += validate_payload_hashes(child, (*path, str(index)))
    return count


def collect_character_reference_ids(package: dict[str, Any], states: list[dict[str, Any]]) -> set[str]:
    refs = set(package["identity_core"]["approved_reference_artifact_ids"])
    refs.update(package["body_morphology"]["view_reference_artifact_ids"])
    for profile_name in ("skin", "hair", "makeup"):
        profile = package["surface_profile"].get(profile_name)
        if profile:
            refs.update(profile.get("reference_artifact_ids", []))
    for descriptor in package["surface_profile"].get("marks_and_imperfections", []):
        refs.update(descriptor["reference_artifact_ids"])
    for wardrobe in package["wardrobe_states"]:
        refs.update(wardrobe.get("reference_artifact_ids", []))
        for descriptor in (*wardrobe["garments"], *wardrobe.get("accessories", [])):
            refs.update(descriptor["reference_artifact_ids"])
    for binding in package.get("voice_bindings", []):
        refs.update(binding.get("reference_artifact_ids", []))
    for state in states:
        refs.update(state["reference_artifact_ids"])
    return refs


def validate_reference_and_states(contract: dict[str, Any]) -> dict[str, int]:
    package = contract["character_package"]
    intake = contract["reference_intake"]
    states = contract["character_states"]
    if (intake["character_id"], intake["character_revision"]) != (
        package["character_id"], package["character_revision"]
    ):
        raise CompilationError("reference_intake_character_revision_mismatch")

    accepted = {asset["artifact_id"]: asset for asset in intake["accepted_assets"]}
    rejected = {asset["artifact_id"]: asset for asset in intake["rejected_assets"]}
    if len(accepted) != len(intake["accepted_assets"]) or len(rejected) != len(intake["rejected_assets"]):
        raise CompilationError("duplicate_reference_artifact_id")
    if set(accepted).intersection(rejected):
        raise CompilationError("reference_cannot_be_accepted_and_rejected")
    reference_hashes = [asset["sha256"] for asset in (*accepted.values(), *rejected.values())]
    if len(reference_hashes) != len(set(reference_hashes)):
        raise CompilationError("duplicate_reference_content_hash")
    for conflict in intake["conflicts"]:
        if not set(conflict["artifact_ids"]).issubset(set(accepted) | set(rejected)):
            raise CompilationError(f"reference_conflict_unknown_artifact:{conflict['conflict_id']}")
        if conflict["resolution_status"] == "open_blocking":
            raise CompilationError(f"reference_conflict_open_blocking:{conflict['conflict_id']}")
    intake_voice_bindings = {
        binding["voice_binding_id"]: binding for binding in intake["voice_reference_bindings"]
    }
    if len(intake_voice_bindings) != len(intake["voice_reference_bindings"]):
        raise CompilationError("duplicate_voice_reference_binding_id")
    for binding in intake["voice_reference_bindings"]:
        if not set(binding["artifact_ids"]).issubset(accepted):
            raise CompilationError(f"voice_binding_requires_accepted_reference:{binding['voice_binding_id']}")
    for binding in package.get("voice_bindings", []):
        intake_binding = intake_voice_bindings.get(binding["voice_binding_id"])
        if intake_binding is None:
            raise CompilationError(f"voice_binding_missing_reference_authority:{binding['voice_binding_id']}")
        if set(binding.get("reference_artifact_ids", [])) != set(intake_binding["artifact_ids"]):
            raise CompilationError(f"voice_binding_reference_set_mismatch:{binding['voice_binding_id']}")

    required_refs = collect_character_reference_ids(package, states)
    missing = sorted(required_refs - set(accepted))
    if missing:
        raise CompilationError(f"character_reference_not_accepted:{missing[0]}")

    state_types = [state["state_type"] for state in states]
    if set(state_types) != REQUIRED_STATE_TYPES or len(state_types) != len(REQUIRED_STATE_TYPES):
        raise CompilationError("character_state_type_set_incomplete_or_duplicate")
    state_ids = [state["state_id"] for state in states]
    if len(state_ids) != len(set(state_ids)):
        raise CompilationError("duplicate_character_state_id")
    for state in states:
        if state["owner_character_id"] != package["character_id"]:
            raise CompilationError(f"character_state_owner_mismatch:{state['state_id']}")
        if any(key in state["payload"] for key in ("identity_core", "character_id", "character_revision")):
            raise CompilationError(f"character_state_attempts_identity_mutation:{state['state_id']}")

    return {
        "accepted_reference_count": len(accepted),
        "rejected_reference_count": len(rejected),
        "coverage_gap_count": len(intake["coverage_gaps"]),
        "reference_conflict_count": len(intake["conflicts"]),
        "character_state_count": len(states),
    }


def validate_scope_and_lineage(contract: dict[str, Any]) -> dict[str, int]:
    package = contract["character_package"]
    scene = contract["scene_package"]
    shot = contract["shot_pose_package"]
    pass_spec = contract["pass_specification"]
    binding = contract["scope_binding"]
    expected_scope = (binding["scene_id"], binding["shot_id"], binding["take_id"])
    if scene["scene_id"] != expected_scope[0] or (
        shot["scene_id"], shot["shot_id"], shot["take_id"]
    ) != expected_scope:
        raise CompilationError("scene_shot_take_scope_mismatch")
    if pass_spec["pass_specification_id"] != binding["pass_specification_id"]:
        raise CompilationError("pass_scope_binding_mismatch")

    participants = {entry["character_instance_id"]: entry for entry in scene["participants"]}
    instances = {entry["character_instance_id"]: entry for entry in shot["instances"]}
    if set(participants) != set(instances):
        raise CompilationError("scene_and_shot_character_instances_mismatch")
    wardrobe_ids = {state["wardrobe_state_id"] for state in package["wardrobe_states"]}
    voice_ids = {binding["voice_binding_id"] for binding in package.get("voice_bindings", [])}
    for instance_id, participant in participants.items():
        shot_instance = instances[instance_id]
        if (participant["character_id"], participant["character_revision"]) != (
            shot_instance["character_id"], shot_instance["character_revision"]
        ):
            raise CompilationError(f"scene_shot_character_revision_mismatch:{instance_id}")
        if (participant["character_id"], participant["character_revision"]) != (
            package["character_id"], package["character_revision"]
        ):
            raise CompilationError(f"participant_character_package_mismatch:{instance_id}")
        if participant["wardrobe_state_id"] not in wardrobe_ids:
            raise CompilationError(f"participant_wardrobe_state_unknown:{instance_id}")
        if participant.get("voice_binding_id") and participant["voice_binding_id"] not in voice_ids:
            raise CompilationError(f"participant_voice_binding_unknown:{instance_id}")
    targets = set(binding["target_owner_instance_ids"])
    if not targets.issubset(instances):
        raise CompilationError("pass_target_owner_unknown")

    known_artifacts: set[str] = set()
    required_source_packages = {
        package["character_package_id"], scene["scene_package_id"], shot["shot_pose_package_id"]
    }
    for artifact in contract["artifact_manifests"]:
        if (artifact["scene_id"], artifact["shot_id"], artifact["take_id"]) != expected_scope:
            raise CompilationError(f"artifact_scope_mismatch:{artifact['artifact_id']}")
        if artifact["pass_id"] != pass_spec["pass_specification_id"]:
            raise CompilationError(f"artifact_pass_mismatch:{artifact['artifact_id']}")
        if not required_source_packages.issubset(set(artifact["source_package_ids"])):
            raise CompilationError(f"artifact_source_packages_incomplete:{artifact['artifact_id']}")
        for parent in artifact["parent_artifact_ids"]:
            if parent not in known_artifacts:
                raise CompilationError(f"artifact_parent_not_prior_or_unknown:{artifact['artifact_id']}:{parent}")
        for owner in artifact["ownership_scope"]:
            if owner["owner"]["owner_type"] == "character_instance" and owner["owner"]["owner_id"] not in targets:
                raise CompilationError(f"artifact_owner_outside_pass_target:{artifact['artifact_id']}")
        for file_record in artifact["files"]:
            expected_uri = f"cas://sha256/{file_record['sha256']}"
            if file_record["path_or_uri"] != expected_uri:
                raise CompilationError(f"artifact_file_not_content_addressed:{artifact['artifact_id']}")
        if artifact["promotion_state"] != "not_eligible" or artifact["qa_decision"] != "block":
            raise CompilationError(f"synthetic_artifact_false_promotion:{artifact['artifact_id']}")
        if artifact["artifact_id"] in known_artifacts:
            raise CompilationError(f"duplicate_artifact_id:{artifact['artifact_id']}")
        known_artifacts.add(artifact["artifact_id"])
    return {
        "scene_participant_count": len(participants),
        "pass_target_count": len(targets),
        "artifact_manifest_count": len(known_artifacts),
    }


def compile_contract(root: Path, contract: dict[str, Any], contract_schema: dict[str, Any]) -> dict[str, Any]:
    registry = schema_registry(root)
    validate_schema(contract, contract_schema, registry, "compilation_contract")
    for key in ("character_package", "scene_package", "shot_pose_package", "pass_specification"):
        validate_schema(contract[key], load_json(root / EMBEDDED_SCHEMAS[key]), registry, key)
    artifact_schema = load_json(root / EMBEDDED_SCHEMAS["artifact_manifest"])
    for index, artifact in enumerate(contract["artifact_manifests"]):
        validate_schema(artifact, artifact_schema, registry, f"artifact_manifests.{index}")
    validate_no_hidden_character_paths(contract)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_CHARACTER_PACKAGE_COMPILATION_SLICE_PASS",
        "rows_covered": [154, 155, 156, 157, 158],
        "runtime_scope": "synthetic_contract_compilation",
        "runtime_completion_claimed": contract["runtime_completion_claimed"],
        "production_promotion_allowed": contract["production_promotion_allowed"],
        "payload_hash_count": validate_payload_hashes(contract),
        "compiled_contract_sha256": sha256_value(contract),
        "envelope_sha256": {
            key: sha256_value(contract[key])
            for key in ("character_package", "scene_package", "shot_pose_package", "pass_specification")
        },
    }
    result.update(validate_reference_and_states(contract))
    result.update(validate_scope_and_lineage(contract))
    return result


def build_evidence(root: Path, result: dict[str, Any], contract_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_character_package_compilation_slice_validation",
        **result,
        "authority": {
            "contract_path": contract_path.as_posix(),
            "contract_sha256": sha256_file(root / contract_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "compiler_path": "Plan/07_IMPLEMENTATION/scripts/compile_wave64_character_package_contract.py",
            "compiler_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/compile_wave64_character_package_contract.py"),
        },
        "boundaries": {
            "synthetic_contract_only": True,
            "item_tracker_status_changed": False,
            "model_execution_activated": False,
            "maskfactory_authority_changed": False,
            "promotion_authority_granted": False,
            "wave71_plus_activated": False,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = compile_contract(root, load_json(root / args.contract), load_json(root / args.schema))
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.contract, args.schema)
        if args.evidence_out:
            write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out:
            write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
