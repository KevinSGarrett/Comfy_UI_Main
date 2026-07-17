#!/usr/bin/env python3
"""Validate the staged Wave64 Rows159-163 character and interaction slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = Path("Plan/10_REGISTRIES/wave64_character_publish_interaction_authority.json")
DEFAULT_SCHEMA = Path("Plan/08_SCHEMAS/wave64_character_publish_interaction_authority.schema.json")
REQUIRED_ADAPTER_ROLES = {"flux_family", "sdxl_family", "image_edit", "video", "audio"}
REQUIRED_PUBLICATION_DOMAINS = {
    "identity", "morphology", "view_coverage", "state_integrity", "voice",
    "adapter_compatibility", "multi_character_separation",
}
REQUIRED_MODALITIES = {"image", "mask", "video", "audio", "av"}
REQUIRED_RESOURCE_TYPES = {
    "edit", "mask", "prop", "dialogue", "control", "artifact", "wardrobe", "voice",
    "skeleton", "silhouette",
}


class AuthorityError(ValueError):
    """Raised when staged character publication or interaction authority is invalid."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_schema(registry: dict[str, Any], schema: dict[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(registry),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise AuthorityError(f"schema_validation_failed:{location}:{first.message}")


def validate_source(root: Path, registry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_ref = registry["source_compilation_contract"]
    source_path = Path(source_ref["path"])
    if source_path.is_absolute() or ".." in source_path.parts:
        raise AuthorityError("source_compilation_path_must_be_bounded_relative")
    absolute = (root / source_path).resolve()
    if root.resolve() not in absolute.parents:
        raise AuthorityError("source_compilation_path_outside_project")
    if not absolute.is_file():
        raise AuthorityError("source_compilation_contract_missing")
    if sha256_file(absolute) != source_ref["sha256"]:
        raise AuthorityError("source_compilation_contract_hash_mismatch")
    source = load_json(absolute)
    if source.get("runtime_completion_claimed") is not False or source.get("production_promotion_allowed") is not False:
        raise AuthorityError("source_compilation_false_runtime_or_promotion_claim")
    return source, source["character_package"]


def validate_adapters(registry: dict[str, Any], character: dict[str, Any]) -> dict[str, int]:
    cards = registry["adapter_cards"]
    ids = [card["adapter_id"] for card in cards]
    roles = [card["adapter_role"] for card in cards]
    if len(ids) != len(set(ids)):
        raise AuthorityError("duplicate_adapter_id")
    if set(roles) != REQUIRED_ADAPTER_ROLES or len(roles) != len(REQUIRED_ADAPTER_ROLES):
        raise AuthorityError("adapter_role_set_incomplete_or_duplicate")
    for card in cards:
        if (card["character_id"], card["character_revision"]) != (
            character["character_id"], character["character_revision"]
        ):
            raise AuthorityError(f"adapter_character_revision_mismatch:{card['adapter_id']}")
        if card["calibration_status"] == "passed":
            raise AuthorityError(f"synthetic_adapter_cannot_claim_calibration_pass:{card['adapter_id']}")
        if not card["component_hashes"] or not card["calibration_evidence_ids"] or not card["prohibited_pairings"]:
            raise AuthorityError(f"adapter_hash_evidence_or_pairing_missing:{card['adapter_id']}")
    return {"adapter_card_count": len(cards), "staged_adapter_count": len(cards)}


def validate_publication(registry: dict[str, Any], character: dict[str, Any]) -> dict[str, int]:
    gate = registry["publication_gate"]
    if (gate["character_id"], gate["character_revision"]) != (
        character["character_id"], character["character_revision"]
    ):
        raise AuthorityError("publication_character_revision_mismatch")
    if gate["immutable_revision_sha256"] != canonical_sha256(character):
        raise AuthorityError("publication_immutable_revision_hash_mismatch")
    if set(gate["required_domains"]) != REQUIRED_PUBLICATION_DOMAINS:
        raise AuthorityError("publication_required_domain_set_mismatch")
    results = gate["domain_results"]
    domains = [result["domain"] for result in results]
    if set(domains) != REQUIRED_PUBLICATION_DOMAINS or len(domains) != len(REQUIRED_PUBLICATION_DOMAINS):
        raise AuthorityError("publication_domain_results_incomplete_or_duplicate")
    non_pass = [result for result in results if result["status"] != "pass"]
    if not non_pass:
        raise AuthorityError("synthetic_publication_gate_requires_real_blocker")
    if gate["publication_allowed"] or gate["decision"] != "staged_blocked" or not gate["blocker_codes"]:
        raise AuthorityError("publication_gate_false_promotion")
    return {
        "publication_domain_count": len(results),
        "publication_non_pass_domain_count": len(non_pass),
        "publication_blocker_count": len(gate["blocker_codes"]),
    }


def validate_scene(registry: dict[str, Any], source: dict[str, Any], character: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    scene = registry["scene_compilation"]
    source_scene = source["scene_package"]
    source_shot = source["shot_pose_package"]
    scope = (scene["scene_id"], scene["shot_id"], scene["take_id"])
    if source_scene["scene_id"] != scope[0] or (
        source_shot["scene_id"], source_shot["shot_id"], source_shot["take_id"]
    ) != scope:
        raise AuthorityError("scene_compilation_source_scope_mismatch")
    if set(scene["output_modalities"]) != REQUIRED_MODALITIES:
        raise AuthorityError("scene_compilation_modality_set_incomplete")
    timebase = scene["timebase"]
    if timebase["end_frame"] < timebase["start_frame"]:
        raise AuthorityError("scene_timebase_invalid")

    instances: dict[str, dict[str, Any]] = {}
    resource_owner: dict[tuple[str, str], str] = {}
    for instance in scene["instances"]:
        instance_id = instance["character_instance_id"]
        if instance_id in instances:
            raise AuthorityError(f"duplicate_character_instance_id:{instance_id}")
        if (instance["character_id"], instance["character_revision"]) != (
            character["character_id"], character["character_revision"]
        ):
            raise AuthorityError(f"scene_instance_character_revision_mismatch:{instance_id}")
        resource_types = {resource["resource_type"] for resource in instance["resources"]}
        missing = REQUIRED_RESOURCE_TYPES - resource_types
        if missing:
            raise AuthorityError(f"scene_instance_resource_type_missing:{instance_id}:{sorted(missing)[0]}")
        for resource in instance["resources"]:
            if resource["owner_instance_id"] != instance_id:
                raise AuthorityError(f"resource_owner_mismatch:{resource['resource_id']}")
            key = (resource["resource_type"], resource["resource_id"])
            if key in resource_owner:
                raise AuthorityError(f"resource_ambiguously_owned:{resource['resource_type']}:{resource['resource_id']}")
            if resource["resource_type"] == "mask" and resource.get("authority") != "machine_draft":
                raise AuthorityError(f"synthetic_mask_authority_upgrade_forbidden:{resource['resource_id']}")
            resource_owner[key] = instance_id
        instances[instance_id] = instance

    for event in scene["expected_audio_events"]:
        if event["owner_instance_id"] not in instances:
            raise AuthorityError(f"audio_event_owner_unknown:{event['event_id']}")
        if event["start_frame"] < timebase["start_frame"] or event["end_frame"] > timebase["end_frame"] or event["end_frame"] < event["start_frame"]:
            raise AuthorityError(f"audio_event_timing_invalid:{event['event_id']}")
        dialogue_key = ("dialogue", event["event_id"])
        if resource_owner.get(dialogue_key) != event["owner_instance_id"]:
            raise AuthorityError(f"audio_event_dialogue_ownership_mismatch:{event['event_id']}")
    return instances, {
        "scene_instance_count": len(instances),
        "owned_resource_count": len(resource_owner),
        "expected_audio_event_count": len(scene["expected_audio_events"]),
    }


def validate_interactions(registry: dict[str, Any], instances: dict[str, dict[str, Any]]) -> dict[str, int]:
    scene = registry["scene_compilation"]
    plan = registry["interaction_plan"]
    if (plan["scene_id"], plan["shot_id"], plan["take_id"]) != (
        scene["scene_id"], scene["shot_id"], scene["take_id"]
    ):
        raise AuthorityError("interaction_plan_scope_mismatch")
    contacts = plan["contacts"]
    ids = [contact["contact_id"] for contact in contacts]
    if len(ids) != len(set(ids)):
        raise AuthorityError("duplicate_contact_id")
    start = scene["timebase"]["start_frame"]
    end = scene["timebase"]["end_frame"]
    for contact in contacts:
        if contact["start_frame"] < start or contact["end_frame"] > end or contact["end_frame"] < contact["start_frame"]:
            raise AuthorityError(f"contact_timing_invalid:{contact['contact_id']}")
        participant_regions: set[tuple[str, str]] = set()
        for participant in contact["participants"]:
            owner_id = participant["owner_instance_id"]
            instance = instances.get(owner_id)
            if instance is None:
                raise AuthorityError(f"contact_owner_unknown:{contact['contact_id']}:{owner_id}")
            owned_ids = set(instance["owned_regions"]) | {resource["resource_id"] for resource in instance["resources"]}
            if participant["region_id"] not in owned_ids:
                raise AuthorityError(f"contact_region_not_owned:{contact['contact_id']}:{participant['region_id']}")
            participant_regions.add((owner_id, participant["region_id"]))
        for deformation in contact["expected_deformations"]:
            key = (deformation["owner_instance_id"], deformation["region_id"])
            if key not in participant_regions:
                raise AuthorityError(f"contact_deformation_not_bound_to_participant:{contact['contact_id']}")
        if contact["production_eligible"]:
            raise AuthorityError(f"synthetic_contact_false_production_eligibility:{contact['contact_id']}")
    return {"contact_count": len(contacts)}


def validate_all(root: Path, registry: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(registry, schema)
    source, character = validate_source(root, registry)
    result: dict[str, Any] = {
        "status": "PASS",
        "classification": "WAVE64_CHARACTER_PUBLISH_INTERACTION_SLICE_PASS",
        "rows_covered": [159, 160, 161, 162, 163],
        "runtime_scope": "synthetic_staged_authority_validation",
        "runtime_completion_claimed": registry["runtime_completion_claimed"],
        "production_publication_allowed": registry["production_publication_allowed"],
        "model_execution_activated": registry["model_execution_activated"],
        "source_compilation_contract_sha256": registry["source_compilation_contract"]["sha256"],
    }
    result.update(validate_adapters(registry, character))
    result.update(validate_publication(registry, character))
    instances, scene_counts = validate_scene(registry, source, character)
    result.update(scene_counts)
    result.update(validate_interactions(registry, instances))
    return result


def build_evidence(root: Path, result: dict[str, Any], registry_path: Path, schema_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "evidence_type": "wave64_character_publish_interaction_slice_validation",
        **result,
        "authority": {
            "registry_path": registry_path.as_posix(),
            "registry_sha256": sha256_file(root / registry_path),
            "schema_path": schema_path.as_posix(),
            "schema_sha256": sha256_file(root / schema_path),
            "validator_path": "Plan/07_IMPLEMENTATION/scripts/validate_wave64_character_publish_interaction_authority.py",
            "validator_sha256": sha256_file(root / "Plan/07_IMPLEMENTATION/scripts/validate_wave64_character_publish_interaction_authority.py"),
        },
        "boundaries": {
            "synthetic_contract_only": True,
            "item_tracker_status_changed": False,
            "character_revision_published": False,
            "adapter_calibration_claimed": False,
            "maskfactory_authority_changed": False,
            "writes_gold": False,
            "wave71_plus_activated": False,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--evidence-out", type=Path)
    parser.add_argument("--tracker-evidence-out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = validate_all(root, load_json(root / args.registry), load_json(root / args.schema))
    if args.evidence_out or args.tracker_evidence_out:
        evidence = build_evidence(root, result, args.registry, args.schema)
        if args.evidence_out:
            write_json(root / args.evidence_out, evidence)
        if args.tracker_evidence_out:
            write_json(root / args.tracker_evidence_out, evidence)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
