#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path

REQUIRED_DOCS = [
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/README.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE38_SECOND_PASS/WAVE38_SECOND_PASS_DEEPENING.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE38_SECOND_PASS/WAVE38_SOURCE_AUTHORITY_AND_CONFLICT_RULES.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE39_SECOND_PASS/WAVE39_SECOND_PASS_DEEPENING.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE39_SECOND_PASS/WAVE39_GAP_CLOSURE_DECISION_TREE.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE40_SECOND_PASS/WAVE40_DOMAIN_CONTRACTS_AND_DEPENDENCIES.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE41_SECOND_PASS/WAVE41_BACKLOG_MERGE_PRIORITIZATION_MODEL.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE42_SECOND_PASS/WAVE42_WORKFLOW_CONTROL_BINDING_REQUIREMENTS.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE43_SECOND_PASS/WAVE43_RUNTIME_PROOF_ESCALATION_AND_PULLBACK.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE44_SECOND_PASS/WAVE44_QA_CERTIFICATION_MATRIX.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE45_SECOND_PASS/WAVE45_TRACEABILITY_QUALITY_RULES.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE46_SECOND_PASS/WAVE46_IMPLEMENTATION_LANES_AND_ACCEPTANCE.md',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/WAVE47_SECOND_PASS/WAVE47_OPERATOR_MANUAL_AND_CONTINUATION_POLICY.md',
]
REQUIRED_JSON = [
    '08_SCHEMAS/wave38_second_pass_source_authority.schema.json',
    '08_SCHEMAS/wave39_second_pass_gap_closure.schema.json',
    '08_SCHEMAS/wave40_second_pass_domain_contract.schema.json',
    '08_SCHEMAS/wave41_second_pass_backlog_execution.schema.json',
    '08_SCHEMAS/wave42_second_pass_workflow_control_binding.schema.json',
    '08_SCHEMAS/wave43_second_pass_runtime_proof_escalation.schema.json',
    '08_SCHEMAS/wave44_second_pass_qa_certificate.schema.json',
    '08_SCHEMAS/wave45_second_pass_traceability_quality.schema.json',
    '08_SCHEMAS/wave46_second_pass_implementation_lane.schema.json',
    '08_SCHEMAS/wave47_second_pass_operator_handoff.schema.json',
    '08_SCHEMAS/wave47_second_pass_validation_report.schema.json',
    '10_REGISTRIES/wave38_47_second_pass_registry.json',
    '10_REGISTRIES/wave38_second_pass_authority_registry.json',
    '10_REGISTRIES/wave39_second_pass_gap_closure_registry.json',
    '10_REGISTRIES/wave40_second_pass_domain_contract_registry.json',
    '10_REGISTRIES/wave41_second_pass_execution_state_registry.json',
    '10_REGISTRIES/wave43_second_pass_proof_stage_registry.json',
    '10_REGISTRIES/wave44_second_pass_qa_certificate_registry.json',
    '10_REGISTRIES/wave45_second_pass_trace_quality_registry.json',
    '10_REGISTRIES/wave46_second_pass_implementation_lane_registry.json',
    '10_REGISTRIES/wave47_second_pass_continuation_policy_registry.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/wave38_second_pass_source_authority_records.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/wave39_second_pass_gap_closure_records.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/wave40_second_pass_domain_contracts.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/wave41_second_pass_execution_backlog.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/wave45_second_pass_trace_quality_records.json',
    '15_BLUEPRINT_PROJECTPLAN_COMBINATION/SECOND_PASS_WAVE38_47_DEEPENING/wave47_second_pass_operator_handoff_packet.json',
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
        'validation_id': 'wave47_second_pass_combined_integration_validation',
        'checked_waves': list(range(38, 48)),
        'checked_docs': len(REQUIRED_DOCS),
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
        print('FAIL: Wave47 second-pass combined integration validation failed')
        for item in missing + invalid_json + script_failures:
            print('-', item)
        return 1

    print('PASS: Waves 38-47 second-pass combined integration layer validated')
    print(f'Waves checked: 10')
    print(f'Docs checked: {len(REQUIRED_DOCS)}')
    print(f'JSON checked: {len(REQUIRED_JSON)}')
    print('Scripts checked: 1')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
