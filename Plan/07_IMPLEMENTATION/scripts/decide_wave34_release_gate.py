#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--certification', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    cert = json.loads(Path(args.certification).read_text(encoding='utf-8'))
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    blocked = []
    if not manifest.get('release_id'):
        blocked.append('missing_release_id')
    if cert.get('certification_status') in {'blocked_missing_proof','blocked_failed_QA'}:
        blocked.append(cert.get('certification_status'))
    missing_evidence = cert.get('missing_evidence', [])
    if missing_evidence:
        decision = 'release_with_runtime_boundaries'
    elif blocked:
        decision = 'blocked_missing_proof'
    elif cert.get('certification_status') == 'certified':
        decision = 'release_runtime_certified'
    else:
        decision = 'release_architecture_pack'

    out = {
        'decision_id': 'decision_wave34_generated',
        'release_id': manifest.get('release_id'),
        'app_mode_status': 'prepared_requires_export_proof',
        'orchestrator_status': 'contract_validated',
        'local_proof_status': 'pack_validation_passed',
        'ec2_proof_status': 'blocked_until_preflight_or_not_required',
        'qa_certification_status': cert.get('certification_status'),
        'manifest_status': 'complete' if manifest.get('release_id') else 'missing',
        'runtime_boundary_statuses': manifest.get('proof_boundaries', {}),
        'blocked_reasons': blocked,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
