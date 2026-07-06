#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_WAVES = list(range(38, 48))
REQUIRED_DOCS = [
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/README.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/00_SOURCE_IMPORTS/source_inventory_summary.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/00_SOURCE_IMPORTS/tracker_and_reality_csv_summary.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE38_SOURCE_INTAKE_AND_CANONICAL_BLUEPRINT_MERGE/WAVE38_SOURCE_INTAKE_PROTOCOL.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE39_BLUEPRINT_TO_SYSTEM_CROSSWALK_AND_GAP_RESOLUTION/WAVE39_CROSSWALK_METHOD.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE40_UNIFIED_ARCHITECTURE_RESPONSIBILITY_MODEL/WAVE40_UNIFIED_ARCHITECTURE_TREE.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE41_UNIFIED_BACKLOG_AND_WAVE_EXECUTION_CONTRACT/WAVE41_BACKLOG_EXECUTION_CONTRACT.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE42_WORKFLOW_COMFYUI_AND_APP_MODE_INTEGRATION_BRIDGE/WAVE42_WORKFLOW_APP_RUNTIME_BRIDGE.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE43_LOCAL_EC2_AND_RUNTIME_PROOF_INTEGRATION/WAVE43_LOCAL_EC2_PROOF_CHAIN.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE44_UNIFIED_QA_CERTIFICATION_AND_EVIDENCE_SYSTEM/WAVE44_QA_CERTIFICATION_UNIFICATION.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE45_CATALOG_REGISTRY_SEARCH_AND_TRACEABILITY_MERGE/WAVE45_TRACEABILITY_GRAPH.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE46_COMBINED_MIGRATION_AND_IMPLEMENTATION_EXECUTION_PLAYBOOK/WAVE46_EXECUTION_PLAYBOOK.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE47_COMBINED_FINAL_HANDOFF_AND_OPERATING_MANUAL/WAVE47_COMBINED_OPERATING_MANUAL.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE47_COMBINED_FINAL_HANDOFF_AND_OPERATING_MANUAL/WAVE47_FINAL_HANDOFF_CHECKLIST.md',
]
REQUIRED_JSON = [
    '08_SCHEMAS/wave38_source_intake.schema.json',
    '08_SCHEMAS/wave39_requirement_crosswalk.schema.json',
    '08_SCHEMAS/wave40_unified_architecture_node.schema.json',
    '08_SCHEMAS/wave41_unified_backlog_item.schema.json',
    '08_SCHEMAS/wave42_workflow_app_bridge.schema.json',
    '08_SCHEMAS/wave43_runtime_proof_chain.schema.json',
    '08_SCHEMAS/wave44_qa_certification_unified.schema.json',
    '08_SCHEMAS/wave45_traceability_record.schema.json',
    '08_SCHEMAS/wave46_execution_playbook_step.schema.json',
    '08_SCHEMAS/wave47_combined_handoff_packet.schema.json',
    '08_SCHEMAS/wave47_combined_validation_report.schema.json',
    '10_REGISTRIES/wave38_47_combination_wave_registry.json',
    '10_REGISTRIES/wave38_source_layer_registry.json',
    '10_REGISTRIES/wave39_gap_class_registry.json',
    '10_REGISTRIES/wave40_unified_architecture_layer_registry.json',
    '10_REGISTRIES/wave41_unified_backlog_status_registry.json',
    '10_REGISTRIES/wave42_workflow_app_bridge_registry.json',
    '10_REGISTRIES/wave43_runtime_proof_boundary_registry.json',
    '10_REGISTRIES/wave44_unified_qa_layer_registry.json',
    '10_REGISTRIES/wave45_traceability_registry.json',
    '10_REGISTRIES/wave46_execution_phase_registry.json',
    '10_REGISTRIES/wave47_combined_release_gate_registry.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE38_SOURCE_INTAKE_AND_CANONICAL_BLUEPRINT_MERGE/wave38_source_intake_records.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE39_BLUEPRINT_TO_SYSTEM_CROSSWALK_AND_GAP_RESOLUTION/wave39_unified_requirement_crosswalk.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE40_UNIFIED_ARCHITECTURE_RESPONSIBILITY_MODEL/wave40_unified_architecture_map.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE41_UNIFIED_BACKLOG_AND_WAVE_EXECUTION_CONTRACT/wave41_unified_combined_backlog.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE44_UNIFIED_QA_CERTIFICATION_AND_EVIDENCE_SYSTEM/wave44_unified_qa_certification_packet.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE45_CATALOG_REGISTRY_SEARCH_AND_TRACEABILITY_MERGE/wave45_combined_traceability_index.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE46_COMBINED_MIGRATION_AND_IMPLEMENTATION_EXECUTION_PLAYBOOK/wave46_execution_steps.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/WAVE47_COMBINED_FINAL_HANDOFF_AND_OPERATING_MANUAL/wave47_combined_final_handoff_packet.json',
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    missing = []
    invalid_json = []
    script_failures = []

    for wave in REQUIRED_WAVES:
        for suffix in ['AI_PM_TASKS', 'CURRENT_STATUS', 'DELIVERY_REPORT']:
            rel = f'00_PROJECT_CONTROL/WAVE{wave}_{suffix}.md'
            if not (root / rel).exists():
                missing.append(rel)

    for rel in REQUIRED_DOCS:
        if not (root / rel).exists():
            missing.append(rel)

    for rel in REQUIRED_JSON:
        p = root / rel
        if not p.exists():
            missing.append(rel)
        else:
            try:
                json.loads(p.read_text(encoding='utf-8'))
            except Exception as exc:
                invalid_json.append(f'{rel}: {exc}')

    try:
        py_compile.compile(str(Path(__file__)), doraise=True)
    except Exception as exc:
        script_failures.append(f'validator compile failed: {exc}')

    report = {
        'validation_id': 'wave47_combined_integration_validation',
        'checked_waves': REQUIRED_WAVES,
        'checked_docs': len(REQUIRED_DOCS) + len(REQUIRED_WAVES) * 3,
        'checked_json': len(REQUIRED_JSON),
        'checked_scripts': 1,
        'missing_items': missing,
        'invalid_json': invalid_json,
        'script_failures': script_failures,
        'promotion_decision': 'pass' if not missing and not invalid_json and not script_failures else 'fail'
    }

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    if report['promotion_decision'] != 'pass':
        print('FAIL: Wave47 combined integration validation failed')
        for item in missing + invalid_json + script_failures:
            print('-', item)
        return 1

    print('PASS: Waves 38-47 blueprint/project-plan combination layer validated')
    print(f'Waves checked: {len(REQUIRED_WAVES)}')
    print(f'Docs checked: {report["checked_docs"]}')
    print(f'JSON checked: {len(REQUIRED_JSON)}')
    print('Scripts checked: 1')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
