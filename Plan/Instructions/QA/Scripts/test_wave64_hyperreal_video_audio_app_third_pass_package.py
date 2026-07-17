from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[4]
BUILDER = ROOT / "Plan/07_IMPLEMENTATION/scripts/build_wave64_hyperreal_video_audio_app_third_pass_package.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("wave64_hvaa_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return load_builder()


@pytest.fixture(scope="module")
def contracts(builder):
    schemas = builder.build_schemas()
    registry = Registry().with_resources(
        [(schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()]
    )
    return schemas, registry


def validator_for(schema, registry):
    return jsonschema.Draft202012Validator(
        schema, registry=registry, format_checker=jsonschema.FormatChecker()
    )


def schema_for_record_type(schemas, record_type):
    matches = [
        schema
        for schema in schemas.values()
        if schema.get("properties", {}).get("record_type", {}).get("const") == record_type
    ]
    assert len(matches) == 1, record_type
    return matches[0]


def test_builder_check_is_clean():
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["runtime_completion_claimed"] is False
    assert payload["runtime_execution_allowed"] is False
    assert payload["production_application_built"] is False


def test_rows_are_contiguous_unique_and_four_per_workstream(builder):
    rows = builder.build_rows()
    assert [row["row_number"] for row in rows] == list(range(261, 321))
    assert len({row["item_id"] for row in rows}) == 60
    assert len({row["tracker_id"] for row in rows}) == 60
    assert set(Counter(row["workstream_id"] for row in rows).values()) == {4}
    assert len({row["workstream_id"] for row in rows}) == 15


def test_row320_transitively_depends_on_every_new_row(builder):
    rows = builder.build_rows()
    item_ids = {row["item_id"] for row in rows}
    dependencies = {
        row["item_id"]: [dep for dep in row["dependencies"] if dep in item_ids]
        for row in rows
    }
    seen = set()
    stack = ["ITEM-W64-320"]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(dependencies[current])
    assert seen == item_ids


def test_rows_never_claim_runtime_completion(builder):
    for row in builder.build_rows():
        assert row["status"] == builder.STATUS
        assert row["runtime_completion_claimed"] is False


def test_item_and_tracker_csv_mirrors_cover_rows():
    item_path = ROOT / "Plan/Items/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_ITEM_ROWS.csv"
    tracker_path = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_TRACKER_ROWS.csv"
    with item_path.open(encoding="utf-8", newline="") as handle:
        items = list(csv.DictReader(handle))
    with tracker_path.open(encoding="utf-8", newline="") as handle:
        trackers = list(csv.DictReader(handle))
    assert len(items) == len(trackers) == 60
    assert [row["row_number"] for row in items] == [row["row_number"] for row in trackers]
    assert all(row["tracker_state"] == "planned_not_started" for row in trackers)


def test_requirements_mirrors_are_byte_identical():
    left = ROOT / "Plan/Items/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_REQUIREMENTS.json"
    right = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_REQUIREMENTS.json"
    assert left.read_bytes() == right.read_bytes()


def test_coverage_mirrors_are_byte_identical_and_truthful():
    left = ROOT / "Plan/Instructions/QA/Evidence/Wave64/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PLANNING_COVERAGE.json"
    right = ROOT / "Plan/Tracker/Evidence/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PLANNING_COVERAGE.json"
    assert left.read_bytes() == right.read_bytes()
    payload = json.loads(left.read_text(encoding="utf-8"))
    assert payload["rows"] == 60
    assert payload["runtime_completion_claimed"] is False
    assert payload["production_application_built"] is False
    assert payload["model_or_engine_qualification_performed"] is False


def test_all_schema_ids_are_unique_and_meta_valid(contracts):
    schemas, _ = contracts
    assert len({schema["$id"] for schema in schemas.values()}) == len(schemas)
    for name, schema in schemas.items():
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", name


def test_all_record_schemas_close_top_level_payloads(contracts):
    schemas, _ = contracts
    for name, schema in schemas.items():
        if name == "hyperreal_media_common.schema.json":
            continue
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert "provenance" in schema["required"]


def test_every_example_validates_against_exact_record_schema(builder, contracts):
    schemas, registry = contracts
    for name, example in builder.build_examples().items():
        schema = schema_for_record_type(schemas, example["record_type"])
        errors = list(validator_for(schema, registry).iter_errors(example))
        assert not errors, f"{name}: {errors}"


def test_planned_video_route_is_blocked(builder):
    route = builder.build_examples()["wave64_hyperreal_video_blocked_route.example.json"]
    assert route["decision"] == "blocked"
    assert route["selected_bundle_ref"] is None
    assert route["production_execution_allowed"] is False
    assert route["evaluated_candidates"][0]["eligible"] is False


def test_video_route_cannot_self_promote_uncertified_candidate(builder):
    route = copy.deepcopy(builder.build_examples()["wave64_hyperreal_video_blocked_route.example.json"])
    candidate = route["evaluated_candidates"][0]
    candidate["eligible"] = True
    candidate["pareto_frontier"] = True
    candidate["rank_score"] = 0.9
    candidate["confidence_low"] = 0.8
    route["selected_bundle_ref"] = candidate["bundle_ref"]
    route["decision"] = "selected"
    route["production_execution_allowed"] = True
    with pytest.raises(ValueError, match="certified"):
        builder.validate_video_route_record(route)


def test_production_video_route_requires_selected_bundle_schema(builder, contracts):
    schemas, registry = contracts
    route = copy.deepcopy(builder.build_examples()["wave64_hyperreal_video_blocked_route.example.json"])
    route["production_execution_allowed"] = True
    schema = schemas["hyperreal_video_engine_route_decision.schema.json"]
    assert list(validator_for(schema, registry).iter_errors(route))


def test_reversed_media_span_is_rejected(builder):
    span = copy.deepcopy(builder.build_examples()["wave64_hyperreal_audio_event_graph.example.json"]["canonical_clock"])
    span["start_pts"] = span["end_pts_exclusive"]
    with pytest.raises(ValueError, match="start_pts"):
        builder.validate_media_span(span)


def test_duplicate_audio_event_ids_are_rejected(builder):
    graph = copy.deepcopy(builder.build_examples()["wave64_hyperreal_audio_event_graph.example.json"])
    graph["events"][1]["event_id"] = graph["events"][0]["event_id"]
    with pytest.raises(ValueError, match="unique"):
        builder.validate_audio_event_graph_record(graph)


def test_unknown_audio_event_edge_is_rejected(builder):
    graph = copy.deepcopy(builder.build_examples()["wave64_hyperreal_audio_event_graph.example.json"])
    graph["edges"][0]["target_event_id"] = "missing"
    with pytest.raises(ValueError, match="unknown"):
        builder.validate_audio_event_graph_record(graph)


def test_cyclic_audio_causality_is_rejected(builder):
    graph = copy.deepcopy(builder.build_examples()["wave64_hyperreal_audio_event_graph.example.json"])
    a, b = [event["event_id"] for event in graph["events"]]
    graph["edges"] = [
        {"source_event_id": a, "target_event_id": b, "relation": "causes"},
        {"source_event_id": b, "target_event_id": a, "relation": "causes"},
    ]
    with pytest.raises(ValueError, match="cycle"):
        builder.validate_audio_event_graph_record(graph)


def test_audio_source_contract_uses_three_orthogonal_axes(contracts):
    schemas, _ = contracts
    schema = schemas["hyperreal_audio_source_route_decision.schema.json"]
    candidate = schema["properties"]["candidates"]["items"]
    assert {"origin_class", "realization_action", "derivation_state"}.issubset(candidate["required"])
    assert "source_method" not in candidate["properties"]


def test_offline_render_command_is_rejected(builder):
    command = copy.deepcopy(builder.build_examples()["wave64_hyperreal_application_command.example.json"])
    command["offline_created"] = True
    command["command"] = "request_final_render"
    with pytest.raises(ValueError, match="offline"):
        builder.validate_application_command_record(command)


def test_direct_legacy_promotion_command_is_rejected(builder):
    command = copy.deepcopy(builder.build_examples()["wave64_hyperreal_application_command.example.json"])
    command["command"] = "promote_artifact"
    with pytest.raises(ValueError, match="legacy"):
        builder.validate_application_command_record(command)


def test_browser_direct_comfyui_mutation_is_rejected(builder):
    command = copy.deepcopy(builder.build_examples()["wave64_hyperreal_application_command.example.json"])
    command["direct_comfyui_mutation"] = True
    with pytest.raises(ValueError, match="controller boundary"):
        builder.validate_application_command_record(command)


def test_app_mode_launcher_cannot_promote(contracts, builder):
    schemas, registry = contracts
    record = copy.deepcopy(builder.build_examples()["wave64_hyperreal_app_mode_launch_request.example.json"])
    record["production_promotion_allowed"] = True
    schema = schemas["hyperreal_app_mode_launch_request.schema.json"]
    assert list(validator_for(schema, registry).iter_errors(record))


def test_realtime_event_is_advisory(contracts, builder):
    schemas, registry = contracts
    record = copy.deepcopy(builder.build_examples()["wave64_hyperreal_realtime_event.example.json"])
    record["authoritative_for_transition"] = True
    schema = schemas["hyperreal_application_realtime_event.schema.json"]
    assert list(validator_for(schema, registry).iter_errors(record))


def test_multi_character_indices_are_unique(builder):
    record = copy.deepcopy(builder.build_examples()["wave64_hyperreal_multi_character_editor_projection.example.json"])
    record["instance_cards"][1]["provider_person_index"] = 0
    with pytest.raises(ValueError, match="provider_person_index"):
        builder.validate_multi_character_projection_record(record)


def test_av_repair_cannot_become_full_rerender(contracts, builder):
    schemas, registry = contracts
    repair = copy.deepcopy(builder.build_examples()["wave64_hyperreal_av_local_repair.example.json"])
    repair["full_av_rerender"] = True
    schema = schemas["hyperreal_av_local_repair_plan.schema.json"]
    assert list(validator_for(schema, registry).iter_errors(repair))


def test_av_repair_time_stretch_is_bounded(contracts, builder):
    schemas, registry = contracts
    repair = copy.deepcopy(builder.build_examples()["wave64_hyperreal_av_local_repair.example.json"])
    repair["repairs"][0]["maximum_time_stretch_ratio"] = 1.2
    schema = schemas["hyperreal_av_local_repair_plan.schema.json"]
    assert list(validator_for(schema, registry).iter_errors(repair))


def test_open_incident_must_block_promotion(contracts):
    schemas, registry = contracts
    schema = schemas["hyperreal_runtime_incident_projection.schema.json"]
    properties = schema["properties"]
    assert properties["promotion_blocked"]["type"] == "boolean"
    assert schema["allOf"]
    conditional = schema["allOf"][0]
    assert conditional["then"]["properties"]["promotion_blocked"] == {"const": True}


def test_production_certificate_schemas_do_not_permanently_force_false(contracts):
    schemas, _ = contracts
    for name in (
        "hyperreal_video_promotion_certificate.schema.json",
        "hyperreal_audio_av_promotion_certificate.schema.json",
        "hyperreal_application_release_manifest.schema.json",
    ):
        claim = schemas[name]["properties"]["runtime_completion_claimed"]
        assert claim == {"type": "boolean"}
        assert schemas[name]["allOf"]


def test_control_catalog_contains_no_dead_or_direct_runtime_controls(builder):
    registry = builder.build_registries()["wave64_operator_canonical_control_binding_registry.json"]
    assert registry["dead_controls"] == 0
    assert registry["raw_path_controls"] == 0
    assert registry["direct_comfyui_command_controls"] == 0
    ids = [control["control_id"] for control in registry["controls"]]
    assert len(ids) == len(set(ids))
    assert "release.promotion_request" in ids


def test_legacy_app_controls_remain_unmigrated_and_nonauthoritative(builder):
    registry = builder.build_registries()["wave64_legacy_app_control_crosswalk_registry.json"]
    assert registry["legacy_control_count_observed"] == 125
    assert registry["migration_complete"] is False
    assert registry["production_authority"] == "none_until_every_control_has_canonical_definition_binding_and_test"


def test_legacy_video_audio_scripts_are_not_production_entrypoints(builder):
    registry = builder.build_registries()["wave64_legacy_video_audio_authority_deprecation_registry.json"]
    assert registry["entries"]
    assert all(entry["production_entrypoint_allowed"] is False for entry in registry["entries"])


def test_disclosure_modes_do_not_grant_roles(builder):
    registry = builder.build_registries()["wave64_operator_role_capability_registry.json"]
    assert registry["disclosure_modes_are_not_roles"] is True
    assert registry["mode_change_grants_capability"] is False
    assert registry["browser_promotion_commit"] is False


def test_app_surface_decision_is_hybrid_and_controller_core_can_release_independently(builder):
    registry = builder.build_registries()["wave64_operator_surface_deployment_registry.json"]
    assert registry["decision"].startswith("hybrid_controller_console")
    assert registry["controller_console"]["required"] is True
    assert registry["frontend_extension"]["required"] is False
    schema = builder.build_schemas()["hyperreal_application_release_manifest.schema.json"]
    assert "controller_core" in schema["properties"]["release_tier"]["enum"]


def test_audio_delivery_registry_rejects_legacy_fixture_as_universal_authority(builder):
    registry = builder.build_registries()["wave64_audio_delivery_and_clock_profile_registry.json"]
    assert registry["legacy_16khz_mono_fixture_is_universal_authority"] is False
    assert all(profile["sample_rate_hz"] == 48000 for profile in registry["profiles"])


def test_preservation_manifest_hashes_every_entry():
    path = ROOT / "Plan/Instructions/Hydration_Rehydration/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_PRESERVATION_MANIFEST.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["runtime_completion_claimed"] is False
    assert len({entry["path"] for entry in manifest["entries"]}) == len(manifest["entries"])
    for entry in manifest["entries"]:
        content = (ROOT / entry["path"]).read_bytes()
        assert len(content) == entry["bytes"], entry["path"]
        assert hashlib.sha256(content).hexdigest() == entry["sha256"], entry["path"]


def test_master_plan_covers_hyperreal_video_audio_and_hybrid_app():
    text = (ROOT / "Plan/00_PROJECT_CONTROL/WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_MASTER_PLAN.md").read_text(encoding="utf-8")
    required = [
        "What hyperreal video means",
        "Video route and multipass policy",
        "What hyperreal audio means",
        "Voice and performance chain",
        "Mix, master, and AV",
        "Application product areas",
        "Timeline design",
        "No planning file",
    ]
    for phrase in required:
        assert phrase in text


def test_main_handoff_names_exact_task_and_preservation_boundary():
    text = (ROOT / "Plan/Instructions/Hydration_Rehydration/HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_MAIN_SESSION_HANDOFF.md").read_text(encoding="utf-8")
    assert "019f422f-88b1-7382-872b-21de2089e983" in text
    assert "Rows261-320" in text
    assert "Do not delete" in text
    assert "planning-contract coverage only" in text
