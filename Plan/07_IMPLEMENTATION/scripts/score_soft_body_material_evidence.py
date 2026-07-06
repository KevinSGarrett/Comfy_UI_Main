#!/usr/bin/env python3
"""Score Wave 21 soft-body material evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    scores = {
        'profile_match': float(data.get('profile_match', 0.0)),
        'region_ownership': float(data.get('region_ownership', 0.0)),
        'contact_geometry': float(data.get('contact_geometry', 0.0)),
        'deformation_plausibility': float(data.get('deformation_plausibility', 0.0)),
        'preservation': float(data.get('preservation', 0.0)),
        'temporal_continuity': float(data.get('temporal_continuity', 1.0)),
    }
    weights = {
        'profile_match': 0.20,
        'region_ownership': 0.15,
        'contact_geometry': 0.15,
        'deformation_plausibility': 0.20,
        'preservation': 0.15,
        'temporal_continuity': 0.15,
    }
    final = sum(scores[k] * weights[k] for k in weights)
    hard_fail_flags = set(data.get('hard_fail_flags', []))
    blocking = {'identity_drift', 'pose_drift', 'body_shape_unapproved_drift', 'mask_bleed', 'unsupported_compression', 'temporal_flicker', 'floating_contact'}
    report = {
        'evidence_version': 'wave21.v1',
        'scores': scores,
        'final_score': round(final, 4),
        'hard_fail_flags': sorted(hard_fail_flags),
        'pass': final >= 0.82 and not (hard_fail_flags & blocking),
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
