#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

FAILURE_TO_ACTION = {
    'composition_failed': 'rerun_layout_or_camera_preview',
    'identity_failed': 'rerun_still_proxy_with_identity_lock',
    'pose_failed': 'rerun_control_or_pose_preview',
    'contact_failed': 'rerun_contact_keyframe_preview',
    'animatic_timing_failed': 'rerun_animatic_only',
    'budget_too_high': 'reduce_budget_or_split_render_scope',
    'preview_artifact_missing': 'block_final_render_and_regenerate_preview',
}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview-qa', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    qa = json.loads(Path(args.preview_qa).read_text(encoding='utf-8'))
    flags = qa.get('failure_flags', [])
    actions = [FAILURE_TO_ACTION.get(flag, 'rerun_preview') for flag in flags]
    if not actions and qa.get('promotion_decision') == 'pass_preview':
        actions = ['no_rerun']
    elif not actions:
        actions = ['rerun_preview']

    out = {
        'preview_id': qa.get('preview_id'),
        'failure_flags': flags,
        'recommended_actions': actions,
        'final_render_allowed': qa.get('promotion_decision') == 'pass_preview' and actions == ['no_rerun']
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
