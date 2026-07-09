#!/usr/bin/env python3
"""Validate a Wave 25 multi-character interaction contract."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED_EVENT_FIELDS = ['event_id','source_instance_id','target_instance_id','interaction_type','source_region','target_region','choreography_phase','occlusion_role']

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output')
    args = parser.parse_args()
    obj = json.loads(Path(args.input).read_text(encoding='utf-8'))
    errors = []
    if obj.get('contract_version') != 'wave25.v1':
        errors.append('contract_version must be wave25.v1')
    instances = obj.get('character_instances', [])
    instance_ids = set()
    if not isinstance(instances, list) or len(instances) < 2:
        errors.append('at least two character_instances are required')
    else:
        for idx, inst in enumerate(instances):
            if not isinstance(inst, dict):
                errors.append(f'character_instances[{idx}] must be an object')
                continue
            cid = inst.get('character_instance_id')
            if not cid:
                errors.append(f'character_instances[{idx}] missing character_instance_id')
                continue
            if cid in instance_ids:
                errors.append(f'duplicate character_instance_id: {cid}')
            instance_ids.add(cid)
    contact_masks = obj.get('contact_masks', [])
    contact_mask_ids = set()
    if contact_masks is not None and not isinstance(contact_masks, list):
        errors.append('contact_masks must be a list when supplied')
    else:
        for idx, mask in enumerate(contact_masks or []):
            if not isinstance(mask, dict):
                errors.append(f'contact_masks[{idx}] must be an object')
                continue
            mask_id = mask.get('contact_mask_id')
            if not mask_id:
                errors.append(f'contact_masks[{idx}] missing contact_mask_id')
                continue
            if mask_id in contact_mask_ids:
                errors.append(f'duplicate contact_mask_id: {mask_id}')
            contact_mask_ids.add(str(mask_id))

    graph_edges = obj.get('contact_graph_edges', [])
    graph_edge_ids = set()
    if graph_edges is not None and not isinstance(graph_edges, list):
        errors.append('contact_graph_edges must be a list when supplied')
    else:
        for idx, edge in enumerate(graph_edges or []):
            if not isinstance(edge, dict):
                errors.append(f'contact_graph_edges[{idx}] must be an object')
                continue
            edge_id = edge.get('edge_id')
            if not edge_id:
                errors.append(f'contact_graph_edges[{idx}] missing edge_id')
                continue
            if edge_id in graph_edge_ids:
                errors.append(f'duplicate contact_graph_edge edge_id: {edge_id}')
            graph_edge_ids.add(str(edge_id))

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
            for field in ['source_instance_id', 'target_instance_id']:
                value = event.get(field)
                if value and instance_ids and value not in instance_ids:
                    errors.append(f'event[{idx}] {field} references unknown instance: {value}')
            if not event.get('contact_mask_id'):
                errors.append(f'event[{idx}] missing field: contact_mask_id')
            elif contact_mask_ids and str(event.get('contact_mask_id')) not in contact_mask_ids:
                errors.append(f"event[{idx}] contact_mask_id references unknown contact mask: {event.get('contact_mask_id')}")
            source_edge_id = event.get('source_contact_edge_id')
            if graph_edge_ids and not source_edge_id:
                errors.append(f'event[{idx}] missing field: source_contact_edge_id')
            elif graph_edge_ids and str(source_edge_id) not in graph_edge_ids:
                errors.append(f'event[{idx}] source_contact_edge_id references unknown contact graph edge: {source_edge_id}')
            if not event.get('depth_order_assertion'):
                errors.append(f'event[{idx}] missing field: depth_order_assertion')
    depth_order = obj.get('depth_order', [])
    if depth_order:
        if not isinstance(depth_order, list):
            errors.append('depth_order must be a list when supplied')
        else:
            depth_ids = [str(item) for item in depth_order]
            if len(depth_ids) != len(set(depth_ids)):
                errors.append('depth_order contains duplicate instance ids')
            if instance_ids:
                missing = sorted(instance_ids.difference(set(depth_ids)))
                extra = sorted(set(depth_ids).difference(instance_ids))
                if missing:
                    errors.append(f'depth_order missing instances: {",".join(missing)}')
                if extra:
                    errors.append(f'depth_order contains unknown instances: {",".join(extra)}')
    merge_checks = obj.get('merge_prevention_checks', [])
    if merge_checks is not None and not isinstance(merge_checks, list):
        errors.append('merge_prevention_checks must be a list when supplied')
    report = {
        'validation_version': 'wave25.v1',
        'input': args.input,
        'passed': not errors,
        'errors': errors,
        'character_instance_count': len(instances) if isinstance(instances, list) else 0,
        'interaction_event_count': len(events) if isinstance(events, list) else 0,
        'depth_order_count': len(depth_order) if isinstance(depth_order, list) else 0,
        'contact_mask_count': len(contact_masks) if isinstance(contact_masks, list) else 0,
        'contact_graph_edge_count': len(graph_edges) if isinstance(graph_edges, list) else 0,
        'merge_prevention_check_count': len(merge_checks) if isinstance(merge_checks, list) else 0,
    }
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if errors:
        print('FAIL')
        for err in errors:
            print(f'- {err}')
        return 1
    print('PASS')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
