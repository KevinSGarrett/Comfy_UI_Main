#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED_ARCHITECTURE_KEYS = [
    'schemas_valid',
    'registries_valid',
    'scripts_valid',
    'release_manifest_present',
    'handoff_present',
    'runtime_boundaries_recorded'
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    status = json.loads(Path(args.status).read_text(encoding='utf-8'))
    checks = status.get('checks', {})
    missing = [k for k in REQUIRED_ARCHITECTURE_KEYS if not checks.get(k, False)]
    runtime_claims = status.get('runtime_claims', {})
    runtime_evidence = status.get('runtime_evidence', {})
    bad_claims = []
    for key, claimed in runtime_claims.items():
        if claimed and not runtime_evidence.get(key):
            bad_claims.append(key)

    if bad_claims:
        decision = 'blocked_missing_proof'
    elif missing:
        decision = 'repair_required'
    else:
        decision = 'release_architecture_pack'

    out = {
        'proof_gate_id': status.get('proof_gate_id', 'wave34_proof_gate'),
        'missing_architecture_checks': missing,
        'runtime_claims_without_evidence': bad_claims,
        'promotion_decision': decision
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
