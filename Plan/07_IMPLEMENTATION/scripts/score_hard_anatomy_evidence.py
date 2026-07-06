#!/usr/bin/env python3
"""Score Wave 20 hard-anatomy evidence."""
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
    checks = {
        'local_anatomy_improved': bool(data.get('local_anatomy_improved', False)),
        'identity_preserved': bool(data.get('identity_preserved', False)),
        'pose_preserved': bool(data.get('pose_preserved', False)),
        'contact_preserved': bool(data.get('contact_preserved', False)),
        'frame_preserved': bool(data.get('frame_preserved', False)),
        'seam_blend_passed': bool(data.get('seam_blend_passed', False)),
    }
    local_score = float(data.get('local_score', 0.0))
    global_score = float(data.get('global_score', 0.0))
    report = {
        'evidence_version': 'wave20.v1',
        **checks,
        'local_score': local_score,
        'global_score': global_score,
        'pass': all(checks.values()) and local_score >= 0.82 and global_score >= 0.86,
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
