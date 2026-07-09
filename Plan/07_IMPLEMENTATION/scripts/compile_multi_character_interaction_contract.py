#!/usr/bin/env python3
"""Compile a Wave 25 multi-character interaction contract."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    out = {
        'contract_version': 'wave25.v1',
        'scene_id': src.get('scene_id'),
        'profile_id': src.get('profile_id'),
        'contact_graph_evidence': src.get('contact_graph_evidence'),
        'contact_graph_id': src.get('contact_graph_id'),
        'instance_layout_evidence': src.get('instance_layout_evidence'),
        'mask_factory_evidence': src.get('mask_factory_evidence'),
        'character_instances': src.get('character_instances', []),
        'interaction_events': src.get('interaction_events', []),
        'contact_graph_edges': src.get('contact_graph_edges', []),
        'depth_order': src.get('depth_order', []),
        'contact_masks': src.get('contact_masks', []),
        'occlusion_layers': src.get('occlusion_layers', []),
        'merge_prevention_checks': src.get('merge_prevention_checks', []),
        'qa_scoring_rules': src.get('qa_scoring_rules'),
        'certification_boundary': src.get('certification_boundary'),
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
