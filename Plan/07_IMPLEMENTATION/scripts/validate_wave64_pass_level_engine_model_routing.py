#!/usr/bin/env python3
"""Validate Wave64 Rows149-220 contracts, routes, examples, and generated ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SCHEMA_NAMES = [
    "multimodal_contract_common.schema.json",
    "character_package_revision.schema.json",
    "scene_package.schema.json",
    "shot_pose_package.schema.json",
    "mask_factory_binding.schema.json",
    "engine_model_capability_card.schema.json",
    "engine_execution_stack_card.schema.json",
    "multimodal_pass_route_request.schema.json",
    "multimodal_pass_route_decision.schema.json",
    "cross_engine_bridge_contract.schema.json",
    "specialist_pass_contract.schema.json",
    "multimodal_pass_dag.schema.json",
    "multimodal_artifact_manifest.schema.json",
    "multimodal_orchestrator_event.schema.json",
    "autonomous_multimodal_job.schema.json",
]

EXAMPLE_BINDINGS = {
    "wave64_single_character_flux_to_sdxl_specialist.example.json": {
        "route_request": "multimodal_pass_route_request.schema.json",
        "route_decision": "multimodal_pass_route_decision.schema.json",
        "bridge_contract": "cross_engine_bridge_contract.schema.json",
        "specialist_pass": "specialist_pass_contract.schema.json",
    },
    "wave64_two_character_ownership_and_mask_binding.example.json": {
        "shot_pose_package": "shot_pose_package.schema.json",
        "mask_bindings[]": "mask_factory_binding.schema.json",
    },
    "wave64_video_segment_route_and_span_repair.example.json": {
        "route_request": "multimodal_pass_route_request.schema.json",
        "route_decision": "multimodal_pass_route_decision.schema.json",
    },
    "wave64_audio_stems_and_av_job.example.json": {
        "job": "autonomous_multimodal_job.schema.json",
    },
}


class ValidationFailure(Exception):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationFailure(f"invalid JSON {path}: {exc}") from exc


def load_contracts(root: Path) -> tuple[dict[str, dict[str, Any]], Registry]:
    schema_dir = root / "Plan/08_SCHEMAS"
    schemas: dict[str, dict[str, Any]] = {}
    registry = Registry()
    for name in SCHEMA_NAMES:
        path = schema_dir / name
        if not path.exists():
            raise ValidationFailure(f"missing schema: {path}")
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[name] = schema
        schema_id = schema.get("$id")
        if schema_id:
            registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return schemas, registry


def validator(schema: dict[str, Any], registry: Registry) -> Draft202012Validator:
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def validate_instance(instance: Any, schema_name: str, schemas: dict[str, dict[str, Any]], registry: Registry, label: str) -> None:
    errors = sorted(validator(schemas[schema_name], registry).iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        rendered = []
        for error in errors[:20]:
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            rendered.append(f"{label}:{location}: {error.message}")
        raise ValidationFailure("\n".join(rendered))


def validate_registry(
    root: Path,
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
) -> tuple[dict[str, int], dict[str, str]]:
    path = root / "Plan/10_REGISTRIES/wave64_multimodal_engine_model_capability_registry.json"
    data = load_json(path)
    cards = data.get("capability_cards", [])
    stacks = data.get("execution_stack_templates", [])
    card_ids: set[str] = set()
    card_by_id: dict[str, dict[str, Any]] = {}
    for index, card in enumerate(cards):
        validate_instance(card, "engine_model_capability_card.schema.json", schemas, registry, f"capability_card[{index}]")
        card_id = card["capability_card_id"]
        if card_id in card_ids:
            raise ValidationFailure(f"duplicate capability card id: {card_id}")
        card_ids.add(card_id)
        card_by_id[card_id] = card
        if card["authority_status"] in {"certified"} and not card["model"]["sha256"]:
            raise ValidationFailure(f"certified card lacks exact model hash: {card_id}")
    stack_ids: set[str] = set()
    stack_authority: dict[str, str] = {}
    for index, stack in enumerate(stacks):
        validate_instance(stack, "engine_execution_stack_card.schema.json", schemas, registry, f"execution_stack[{index}]")
        stack_id = stack["execution_stack_id"]
        if stack_id in stack_ids:
            raise ValidationFailure(f"duplicate execution stack id: {stack_id}")
        stack_ids.add(stack_id)
        stack_authority[stack_id] = stack["authority_status"]
        capability = card_by_id.get(stack["capability_card_id"])
        if capability is None:
            raise ValidationFailure(f"stack references unknown capability card: {stack_id}")
        if capability["engine_family"] != stack["engine_family"]:
            raise ValidationFailure(f"stack/card engine-family mismatch: {stack_id}")
        if stack["authority_status"] == "certified":
            if not stack["model"]["sha256"] or not stack["workflow"]["api_graph_sha256"]:
                raise ValidationFailure(f"certified stack lacks exact hashes: {stack_id}")
            if not stack.get("benchmark_certificate_ids"):
                raise ValidationFailure(f"certified stack lacks benchmark certificate: {stack_id}")
    return (
        {"capability_cards": len(cards), "execution_stacks": len(stacks)},
        stack_authority,
    )


def validate_route_decision(
    decision: dict[str, Any],
    label: str,
    stack_authority: dict[str, str] | None = None,
) -> None:
    evaluated = {candidate["execution_stack_id"]: candidate for candidate in decision["evaluated_candidates"]}
    ranked = decision["ranked_eligible_stack_ids"]
    for stack_id, candidate in evaluated.items():
        authority = (stack_authority or {}).get(stack_id)
        if candidate["eligible"] and authority is not None and authority != "certified":
            raise ValidationFailure(
                f"{label}: stack self-declared eligible but registry authority is {authority}: {stack_id}"
            )
        if not candidate["eligible"] and candidate["rank_score"] is not None:
            raise ValidationFailure(f"{label}: ineligible stack was ranked: {stack_id}")
        if candidate["eligible"] and candidate["rank_score"] is None:
            raise ValidationFailure(f"{label}: eligible stack lacks rank score: {stack_id}")
    for stack_id in ranked:
        if stack_id not in evaluated or not evaluated[stack_id]["eligible"]:
            raise ValidationFailure(f"{label}: ranked stack is absent or ineligible: {stack_id}")
    if decision["decision_status"] == "selected":
        selected = decision["selected_execution_stack_id"]
        if selected not in ranked or selected not in evaluated or not evaluated[selected]["eligible"]:
            raise ValidationFailure(f"{label}: selected stack did not pass hard eligibility")
        if stack_authority is not None and stack_authority.get(selected) != "certified":
            raise ValidationFailure(
                f"{label}: selected stack lacks certified registry authority: {selected}"
            )
    elif decision["selected_execution_stack_id"] is not None:
        raise ValidationFailure(f"{label}: blocked decision selected a stack")


def validate_bridge(bridge: dict[str, Any], label: str) -> None:
    required_forbidden = {"cross_family_latent", "cross_family_embedding", "lora_weight", "vae_weight", "text_encoder_weight", "controlnet_weight", "adapter_weight"}
    if set(bridge["forbidden_transfer_objects"]) != required_forbidden:
        raise ValidationFailure(f"{label}: cross-family forbidden-transfer set is incomplete")
    transfer_types = {entry["transfer_type"] for entry in bridge["transfer_objects"]}
    if any("latent" in kind or "lora" in kind or "weight" in kind for kind in transfer_types):
        raise ValidationFailure(f"{label}: engine-local assets appear in transfer objects")
    if bridge["source_execution_stack_id"] == bridge["target_execution_stack_id"]:
        raise ValidationFailure(f"{label}: cross-engine bridge uses the same stack")


def validate_shot_pose_semantics(package: dict[str, Any], label: str) -> None:
    instances = package["instances"]
    instance_ids = [entry["character_instance_id"] for entry in instances]
    person_indices = [entry["person_index"] for entry in instances]
    provider_indices = [entry["mask_provider_person_index"] for entry in instances]
    render_orders = [entry["render_order"] for entry in instances]
    for field, values in (
        ("character_instance_id", instance_ids),
        ("person_index", person_indices),
        ("mask_provider_person_index", provider_indices),
        ("render_order", render_orders),
    ):
        if len(values) != len(set(values)):
            raise ValidationFailure(f"{label}: duplicate {field}")
    for instance in instances:
        if instance["person_index"] != instance["mask_provider_person_index"]:
            raise ValidationFailure(
                f"{label}: legacy person_index must equal explicit mask provider index"
            )
        if instance["skeleton"]["taxonomy_id"] != package["skeleton_taxonomy_id"]:
            raise ValidationFailure(f"{label}: instance skeleton taxonomy mismatch")
    instance_set = set(instance_ids)
    for contact in package["contacts"]:
        owners = [entry["owner_instance_id"] for entry in contact["participants"]]
        if not set(owners).issubset(instance_set):
            raise ValidationFailure(f"{label}: contact references unknown owner")
        if len(owners) != len(set(owners)) and contact["kind"] == "person_person":
            raise ValidationFailure(f"{label}: person-person contact is not reciprocal")
        if contact["ownership_resolved"] is not True:
            raise ValidationFailure(f"{label}: contact ownership unresolved")
        if contact["constraints"]["reciprocal"] is not True:
            raise ValidationFailure(f"{label}: contact reciprocity not asserted")
    timebase = package["timebase"]
    if timebase["end_frame"] < timebase["start_frame"]:
        raise ValidationFailure(f"{label}: invalid frame range")
    expected_duration = (
        (timebase["end_frame"] - timebase["start_frame"] + 1)
        * timebase["denominator"] / timebase["numerator"]
    )
    if abs(package.get("duration_seconds", expected_duration) - expected_duration) > 1e-9:
        raise ValidationFailure(f"{label}: duration does not match inclusive frame range")
    for event in package["events"]:
        if not timebase["start_frame"] <= event["pts"] <= timebase["end_frame"]:
            raise ValidationFailure(f"{label}: event PTS outside shot range")


def validate_examples(
    root: Path,
    schemas: dict[str, dict[str, Any]],
    registry: Registry,
    stack_authority: dict[str, str],
) -> dict[str, int]:
    example_dir = root / "Plan/08_SCHEMAS/examples"
    counts = {"examples": 0, "validated_records": 0}
    for filename, bindings in EXAMPLE_BINDINGS.items():
        path = example_dir / filename
        if not path.exists():
            raise ValidationFailure(f"missing example: {path}")
        data = load_json(path)
        if data.get("status") != "contract_fixture_not_runtime_evidence":
            raise ValidationFailure(f"example falsely implies runtime evidence: {filename}")
        counts["examples"] += 1
        for key, schema_name in bindings.items():
            if key.endswith("[]"):
                field = key[:-2]
                records = data[field]
                for index, record in enumerate(records):
                    validate_instance(record, schema_name, schemas, registry, f"{filename}:{field}[{index}]")
                    counts["validated_records"] += 1
            else:
                record = data[key]
                validate_instance(record, schema_name, schemas, registry, f"{filename}:{key}")
                counts["validated_records"] += 1
                if key == "route_decision":
                    validate_route_decision(
                        record, f"{filename}:{key}", stack_authority
                    )
                if key == "bridge_contract":
                    validate_bridge(record, f"{filename}:{key}")
        if filename.startswith("wave64_two_character"):
            package = data["shot_pose_package"]
            validate_shot_pose_semantics(package, filename + ":shot_pose_package")
            binding_pairs = {(entry["character_instance_id"], entry["person_index"]) for entry in data["mask_bindings"]}
            expected_pairs = {(entry["character_instance_id"], entry["person_index"]) for entry in package["instances"]}
            if binding_pairs != expected_pairs:
                raise ValidationFailure("two-character fixture mask/pose ownership crosswalk does not match")
    return counts


def validate_sidecars(root: Path) -> dict[str, int]:
    item_path = root / "Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_ITEM_ROWS.csv"
    tracker_path = root / "Plan/Tracker/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_TRACKER_ROWS.csv"
    item_requirements = root / "Plan/Items/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_REQUIREMENTS.json"
    tracker_requirements = root / "Plan/Tracker/Waves/Wave64/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_REQUIREMENTS.json"
    for path in [item_path, tracker_path, item_requirements, tracker_requirements]:
        if not path.exists():
            raise ValidationFailure(f"missing generated sidecar: {path}")
    if item_requirements.read_bytes() != tracker_requirements.read_bytes():
        raise ValidationFailure("Items and Tracker requirement mirrors differ")
    with item_path.open("r", encoding="utf-8", newline="") as handle:
        items = list(csv.DictReader(handle))
    with tracker_path.open("r", encoding="utf-8", newline="") as handle:
        trackers = list(csv.DictReader(handle))
    expected_items = [f"ITEM-W64-{number:03d}" for number in range(149, 221)]
    expected_trackers = [f"TRK-W64-{number:03d}" for number in range(149, 221)]
    if [row["Item_ID"] for row in items] != expected_items:
        raise ValidationFailure("Items sidecar is not exactly Rows149-220")
    if [row["Tracker_ID"] for row in trackers] != expected_trackers:
        raise ValidationFailure("Tracker sidecar is not exactly Rows149-220")
    if any(row["Status"] != "Planned_Autonomous_Implementation_Required" for row in items + trackers):
        raise ValidationFailure("sidecar contains a false completion status")
    if len({row["Owner_Domain"] for row in items}) != 18:
        raise ValidationFailure("Items sidecar does not contain eighteen workstreams")
    if any(sum(1 for row in items if row["Owner_Domain"] == workstream) != 4 for workstream in {row["Owner_Domain"] for row in items}):
        raise ValidationFailure("Items workstreams do not contain four rows each")
    requirements = load_json(item_requirements)
    if requirements.get("content_based_suppression") is not False or requirements.get("runtime_complete") is not False:
        raise ValidationFailure("requirements authority flags are incorrect")
    return {"item_rows": len(items), "tracker_rows": len(trackers)}


def validate_preservation_manifest(root: Path) -> dict[str, int]:
    path = root / "Plan/Instructions/Hydration_Rehydration/WAVE64_ULTIMATE_MULTIMODAL_WORKFLOW_PRESERVATION_MANIFEST.json"
    data = load_json(path)
    if data.get("status") != "intentional_planning_package_preserve_do_not_clean":
        raise ValidationFailure("preservation manifest has the wrong status")
    if data.get("runtime_completion_claimed") is not False or data.get("content_based_suppression") is not False:
        raise ValidationFailure("preservation manifest authority flags are incorrect")
    checked = 0
    missing_baseline_references = 0
    for group in ["static_package_files", "generated_sidecars", "baseline_preserved_references"]:
        for record in data.get(group, []):
            if record.get("status") == "missing_in_this_root":
                if group == "baseline_preserved_references":
                    missing_baseline_references += 1
                    continue
                raise ValidationFailure(f"preservation manifest records a missing project file: {record.get('path')}")
            local = root / Path(record["path"].replace("\\", "/"))
            if not local.exists():
                raise ValidationFailure(f"preserved file is now missing: {record['path']}")
            payload = local.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != record["sha256"] or len(payload) != record["bytes"]:
                raise ValidationFailure(f"preserved file changed after manifest creation: {record['path']}")
            checked += 1
    return {
        "preserved_paths_verified": checked,
        "missing_baseline_references": missing_baseline_references,
    }


def validate_semantic_docs(root: Path) -> None:
    master = (root / "Plan/00_PROJECT_CONTROL/WAVE64_ULTIMATE_MODULAR_CHARACTER_TO_MULTIMODAL_WORKFLOW_MASTER_PLAN.md").read_text(encoding="utf-8")
    required = [
        "Hard eligibility filtering happens before quality/cost ranking",
        "Latent transfer is forbidden without an exact compatibility certificate",
        "Repairs require a material hypothesis",
        "Mode A means read-only package consumption",
        "Mode B means live prediction/refinement drafts",
        "whole-artifact regression QA",
        "content_based_suppression=false",
    ]
    for phrase in required:
        if phrase not in master:
            raise ValidationFailure(f"master plan missing required semantic invariant: {phrase}")
    prohibited = ["Mode A planning-only", "Mode B runtime-truth", "router selects one engine for an entire job", "retry policy defaults to increment seed"]
    for phrase in prohibited:
        if phrase in master:
            raise ValidationFailure(f"master plan contains prohibited semantic shortcut: {phrase}")


def validate_all(root: Path) -> dict[str, Any]:
    schemas, registry = load_contracts(root)
    result: dict[str, Any] = {"schemas": len(schemas)}
    registry_counts, stack_authority = validate_registry(root, schemas, registry)
    result.update(registry_counts)
    result.update(validate_examples(root, schemas, registry, stack_authority))
    result.update(validate_sidecars(root))
    result.update(validate_preservation_manifest(root))
    validate_semantic_docs(root)
    result["status"] = "pass"
    result["runtime_completion_claimed"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    try:
        result = validate_all(args.root.resolve())
    except ValidationFailure as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
