#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DOMAIN_TO_SCOPE = {
    'audio': 'audio_layer_repair',
    'spatial_audio': 'audio_layer_repair',
    'mask': 'local_region_repair',
    'region_ownership': 'local_region_repair',
    'skin_surface': 'local_region_repair',
    'deformation': 'local_region_repair',
    'video_temporal': 'span_repair',
    'pose': 'shot_rerun',
    'camera': 'shot_rerun',
    'identity': 'shot_rerun',
    'character_count': 'shot_rerun',
}

SCOPE_ORDER = [
    'none','metadata_repair','local_region_repair','single_frame_repair','span_repair',
    'audio_layer_repair','shot_rerun','segment_rerun','full_scene_rerun'
]

def choose_scope(failed_domains: list[str]) -> str:
    if not failed_domains:
        return 'none'
    scopes = [DOMAIN_TO_SCOPE.get(d, 'shot_rerun') for d in failed_domains]
    return max(scopes, key=lambda s: SCOPE_ORDER.index(s))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--diff', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    diff = json.loads(Path(args.diff).read_text(encoding='utf-8'))
    failed = [d['domain'] for d in diff.get('domain_diffs', []) if d.get('status') in {'mismatch','missing','uncertain'}]
    preserved = [d['domain'] for d in diff.get('domain_diffs', []) if d.get('status') == 'matched']
    scope = choose_scope(failed)
    out = {
        'rerun_id': f"rerun_{diff.get('take_id', 'unknown')}",
        'source_diff_id': diff.get('diff_id'),
        'failed_domains': failed,
        'preserved_domains': preserved,
        'rerun_scope': scope,
        'rerun_reason': 'state_diff_detected_failed_domains',
        'expected_fix': 'repair failed domains while preserving matched domains',
        'blocked_risks': [f'do_not_change_{d}' for d in preserved[:12]],
        'qa_targets': ['state_match','preservation','evidence_complete']
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
