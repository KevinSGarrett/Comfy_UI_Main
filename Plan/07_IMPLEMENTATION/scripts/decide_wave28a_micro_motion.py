#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def decide(exertion: str, fatigue: str, reference_video: bool) -> list[dict]:
    events = []
    if reference_video:
        events.append({'event_type': 'reference_video_micro_motion_extract', 'amplitude': 'source_bound'})
    if exertion in {'none', 'low'} and fatigue in {'fresh', 'warming_up'}:
        events.append({'event_type': 'breathing', 'amplitude': 'very_low', 'frequency': 'calm'})
        events.append({'event_type': 'blink', 'amplitude': 'very_low', 'frequency': 'natural'})
    if exertion in {'medium', 'high'}:
        events.append({'event_type': 'breathing', 'amplitude': 'low_to_medium', 'frequency': 'active'})
        events.append({'event_type': 'hair_or_fabric_follow_through', 'amplitude': 'low', 'frequency': 'motion_bound'})
    if fatigue in {'tired', 'exhausted'}:
        events.append({'event_type': 'breathing', 'amplitude': 'medium', 'frequency': 'heavy_or_recovering'})
        events.append({'event_type': 'small_tremble_or_posture_settle', 'amplitude': 'low', 'frequency': 'irregular'})
    return events

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    src = json.loads(Path(args.input).read_text(encoding='utf-8'))
    exertion = src.get('exertion_level', 'none')
    fatigue = src.get('fatigue_level', 'fresh')
    reference_video = bool(src.get('reference_video_present', False))
    out = {
        'decision_id': src.get('decision_id'),
        'scene_phase': src.get('scene_phase'),
        'exertion_level': exertion,
        'fatigue_level': fatigue,
        'reference_video_present': reference_video,
        'micro_motion_events': decide(exertion, fatigue, reference_video),
        'decision_reason': 'Micro-motion chosen from exertion/fatigue/reference-video state, not random prompt wording.'
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
