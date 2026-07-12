#!/usr/bin/env python3
"""Validate a Wave 19 clothing/prop/furniture contact contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EVIDENCE_GATES = [
    'contact_graph_check',
    'shadow_contact_check',
    'no_floating_check',
    'visual_reject_on_clip',
]


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--taxonomy')
    args = parser.parse_args()
    obj = load(Path(args.input))
    taxonomy_path = Path(args.taxonomy) if args.taxonomy else Path(__file__).resolve().parents[2] / '10_REGISTRIES/wave19_contact_type_taxonomy.json'
    known_types = set(load(taxonomy_path).get('contact_types', []))
    required = ['contract_version', 'source_image_id', 'contact_graph', 'mask_ids', 'required_evidence_gates']
    errors = [f'missing: {k}' for k in required if k not in obj]
    if obj.get('contract_version') != 'wave19.v1':
        errors.append('contract_version must be wave19.v1')
    if not isinstance(obj.get('source_image_id'), str) or not obj.get('source_image_id', '').strip():
        errors.append('source_image_id must be a non-empty string')
    graph = obj.get('contact_graph')
    if not isinstance(graph, list) or not graph:
        errors.append('contact_graph must contain at least one edge')
    else:
        for index, edge in enumerate(graph):
            if not isinstance(edge, dict):
                errors.append(f'contact_graph[{index}] must be an object')
                continue
            for key in ('source', 'target', 'type', 'behavior'):
                if not isinstance(edge.get(key), str) or not edge.get(key, '').strip():
                    errors.append(f'contact_graph[{index}].{key} must be a non-empty string')
            if edge.get('type') not in known_types:
                errors.append(f'contact_graph[{index}].type is not registered')
    masks = obj.get('mask_ids')
    if not isinstance(masks, list) or not masks or any(not isinstance(row, str) or not row.strip() for row in masks):
        errors.append('mask_ids must contain at least one non-empty string')
    if obj.get('required_evidence_gates') != REQUIRED_EVIDENCE_GATES:
        errors.append('required_evidence_gates must match the Wave19 gate contract')
    for key in ('character_ids', 'fabric_targets', 'prop_targets', 'furniture_targets', 'pass_order', 'qa_goals'):
        if key in obj and (not isinstance(obj[key], list) or any(not isinstance(row, str) or not row.strip() for row in obj[key])):
            errors.append(f'{key} must contain only non-empty strings')
    if errors:
        print('FAIL')
        for err in errors:
            print(err)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
