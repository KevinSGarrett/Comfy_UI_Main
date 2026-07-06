#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DEFAULT_DOMAINS = [
    'identity','character_count','body_state','pose','camera','lighting','environment',
    'props','clothing','hair','skin_surface','mask','region_ownership','contact',
    'deformation','micro_motion','video_temporal','audio','spatial_audio','promotion_evidence'
]

def normalize_status(planned, generated):
    if planned is None and generated is None:
        return 'not_applicable'
    if planned is None and generated is not None:
        return 'extra'
    if planned is not None and generated is None:
        return 'missing'
    if planned == generated:
        return 'matched'
    if isinstance(planned, dict) and isinstance(generated, dict):
        shared = set(planned).intersection(generated)
        if shared and all(planned[k] == generated[k] for k in shared):
            return 'partial_match'
    return 'mismatch'

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--planned', required=True)
    parser.add_argument('--generated', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    planned = json.loads(Path(args.planned).read_text(encoding='utf-8'))
    generated = json.loads(Path(args.generated).read_text(encoding='utf-8'))

    p_domains = planned.get('state_domains', {})
    g_domains = generated.get('observed_state_domains', {})
    domains = sorted(set(DEFAULT_DOMAINS).union(p_domains).union(g_domains))
    domain_diffs = []
    blocking = False

    for domain in domains:
        status = normalize_status(p_domains.get(domain), g_domains.get(domain))
        if status in {'mismatch','missing','uncertain'}:
            blocking = True
        domain_diffs.append({
            'domain': domain,
            'status': status,
            'planned': p_domains.get(domain),
            'generated': g_domains.get(domain)
        })

    if all(d['status'] in {'matched','not_applicable'} for d in domain_diffs):
        overall = 'matched'
        decision = 'promote'
        rerun = 'none'
    elif blocking:
        overall = 'mismatch_or_missing'
        decision = 'repair'
        failed = [d['domain'] for d in domain_diffs if d['status'] in {'mismatch','missing','uncertain'}]
        if set(failed).issubset({'audio','spatial_audio'}):
            rerun = 'audio_layer_repair'
        elif len(failed) == 1 and failed[0] in {'mask','region_ownership','skin_surface','deformation'}:
            rerun = 'local_region_repair'
        elif len(failed) <= 2:
            rerun = 'shot_rerun'
        else:
            rerun = 'segment_rerun'
    else:
        overall = 'partial_match'
        decision = 'repair'
        rerun = 'metadata_repair'

    out = {
        'diff_id': f"diff_{generated.get('take_id', 'unknown')}",
        'plan_id': planned.get('plan_id'),
        'run_id': generated.get('run_id'),
        'take_id': generated.get('take_id'),
        'domain_diffs': domain_diffs,
        'overall_status': overall,
        'rerun_recommendation': rerun,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
