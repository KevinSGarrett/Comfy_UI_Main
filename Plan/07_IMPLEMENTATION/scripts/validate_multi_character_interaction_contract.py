#!/usr/bin/env python3
"""Validate a Wave 25 multi-character interaction contract."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED_EVENT_FIELDS = ['event_id','source_instance_id','target_instance_id','interaction_type','source_region','target_region','choreography_phase','occlusion_role']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    errors = []
    if obj.get('contract_version') != 'wave25.v1':
        errors.append('contract_version must be wave25.v1')
    instances = obj.get('character_instances', [])
    if not isinstance(instances, list) or len(instances) < 2:
        errors.append('at least two character_instances are required')
    events = obj.get('interaction_events', [])
    if not isinstance(events, list) or not events:
        errors.append('interaction_events must be a non-empty list')
    else:
        for idx, event in enumerate(events):
            for field in REQUIRED_EVENT_FIELDS:
                if field not in event:
                    errors.append(f'event[{idx}] missing field: {field}')
            if event.get('source_instance_id') == event.get('target_instance_id'):
                errors.append(f'event[{idx}] source and target must be different instances')
    if errors:
        print('FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('PASS')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
