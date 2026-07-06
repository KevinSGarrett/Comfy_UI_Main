#!/usr/bin/env python3
"""Create a placeholder continuity report from manual/automated score inputs.

This script intentionally does not claim computer-vision identity proof. It records
scores supplied by downstream QA tools or manual review.
"""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path

GOALS = ['face_identity_match','body_silhouette_match','hair_match','skin_marker_preservation','outfit_continuity','multi_character_separation']

def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file(): return None
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--character-id', required=True)
    ap.add_argument('--character-version', required=True)
    ap.add_argument('--artifact-path', required=True)
    ap.add_argument('--pass-id', default='unknown_pass')
    ap.add_argument('--score', action='append', default=[], help='goal=value, e.g. face_identity_match=0.91')
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    scores={g: None for g in GOALS}
    failures=[]
    for item in args.score:
        if '=' not in item:
            failures.append({'code':'bad_score_arg','message':item}); continue
        k,v=item.split('=',1)
        try: scores[k]=float(v)
        except ValueError: failures.append({'code':'bad_score_value','message':item})
    for k,v in scores.items():
        if v is not None and v < 0.80:
            failures.append({'code':'low_score','goal':k,'score':v})
    artifact=Path(args.artifact_path)
    if not artifact.exists():
        failures.append({'code':'artifact_missing','message':str(artifact)})
    status='pass' if not failures and any(v is not None for v in scores.values()) else 'blocked' if any(f.get('code')=='artifact_missing' for f in failures) else 'warn'
    report={
        'report_id': f'continuity_{args.character_id}_{args.character_version}_{args.pass_id}',
        'character_id': args.character_id,
        'character_version': args.character_version,
        'artifact_path': args.artifact_path,
        'artifact_sha256': sha256_file(artifact),
        'pass_id': args.pass_id,
        'status': status,
        'scores': scores,
        'failures': failures,
        'promotion_allowed': status == 'pass'
    }
    out=Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status':status,'promotion_allowed':report['promotion_allowed'],'out':str(out)}, indent=2))
    return 0 if status in {'pass','warn','blocked'} else 1

if __name__ == '__main__':
    raise SystemExit(main())
