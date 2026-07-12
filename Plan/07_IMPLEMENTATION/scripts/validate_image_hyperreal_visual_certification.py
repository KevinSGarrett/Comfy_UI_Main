#!/usr/bin/env python3
"""Validate the Wave64 Row016 image hyperreal visual certification contract."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

GATES = ('technical_image_qa', 'visual_review_scorecard', 'prompt_alignment', 'artifact_hash_manifest')
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def valid_score(value: object) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = load(Path(args.input))
    errors: list[str] = []
    required = ('schema_version', 'certification_scope', *GATES, 'promotion_decision', 'upstream_quality_rows')
    errors.extend(f'missing: {key}' for key in required if key not in obj)
    if obj.get('schema_version') != 'row016.v1':
        errors.append('schema_version must be row016.v1')
    if not isinstance(obj.get('certification_scope'), str) or not obj.get('certification_scope', '').strip():
        errors.append('certification_scope must be a non-empty string')
    for gate in GATES:
        value = obj.get(gate)
        if not isinstance(value, dict) or value.get('status') not in {'pass', 'partial', 'blocked', 'fail'}:
            errors.append(f'{gate}.status is invalid')
        paths = value.get('evidence_paths') if isinstance(value, dict) else None
        if not isinstance(paths, list) or any(not isinstance(path, str) or not path.strip() for path in paths):
            errors.append(f'{gate}.evidence_paths must contain only non-empty strings')
    scorecard = obj.get('visual_review_scorecard', {})
    for key in ('average_score', 'minimum_category_score'):
        if not valid_score(scorecard.get(key)):
            errors.append(f'visual_review_scorecard.{key} must be null or within 0..5')
    if not isinstance(scorecard.get('blocking_defects'), list):
        errors.append('visual_review_scorecard.blocking_defects must be an array')
    prompt = obj.get('prompt_alignment', {})
    if prompt.get('alignment_result') not in {'pass', 'partial', 'blocked', 'fail'}:
        errors.append('prompt_alignment.alignment_result is invalid')
    artifacts = obj.get('artifact_hash_manifest', {}).get('artifacts')
    if not isinstance(artifacts, list):
        errors.append('artifact_hash_manifest.artifacts must be an array')
        artifacts = []
    artifact_paths: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict) or not isinstance(artifact.get('path'), str) or not artifact.get('path', '').strip():
            errors.append(f'artifact_hash_manifest.artifacts[{index}].path is invalid')
            continue
        artifact_paths.add(artifact['path'])
        if not isinstance(artifact.get('sha256'), str) or not SHA256.fullmatch(artifact['sha256']):
            errors.append(f'artifact_hash_manifest.artifacts[{index}].sha256 is invalid')
    decision = obj.get('promotion_decision', {})
    if decision.get('decision') not in {'promoted', 'blocked', 'not_promoted'}:
        errors.append('promotion_decision.decision is invalid')
    promoted = decision.get('promoted_outputs')
    if not isinstance(promoted, list) or any(not isinstance(path, str) or not path.strip() for path in promoted):
        errors.append('promotion_decision.promoted_outputs must contain only non-empty strings')
        promoted = []
    upstream = obj.get('upstream_quality_rows')
    if not isinstance(upstream, list) or len(upstream) < 3:
        errors.append('upstream_quality_rows must contain at least three rows')
        upstream = []
    elif any(not isinstance(row, dict) or not isinstance(row.get('tracker_id'), str) or not isinstance(row.get('row_complete'), bool) or not isinstance(row.get('status'), str) for row in upstream):
        errors.append('upstream_quality_rows contains an invalid row')

    if decision.get('decision') == 'promoted':
        if any(obj.get(gate, {}).get('status') != 'pass' for gate in GATES):
            errors.append('promotion requires every Row016 gate to pass')
        average = scorecard.get('average_score')
        minimum = scorecard.get('minimum_category_score')
        if not isinstance(average, (int, float)) or isinstance(average, bool) or average < 4 or not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or minimum < 3 or scorecard.get('blocking_defects'):
            errors.append('promotion requires the strict visual score threshold and no blocking defects')
        if prompt.get('alignment_result') != 'pass' or not isinstance(prompt.get('prompt_reference'), str) or not prompt.get('prompt_reference', '').strip():
            errors.append('promotion requires explicit prompt alignment evidence')
        if not artifacts or not promoted or any(path not in artifact_paths for path in promoted):
            errors.append('promotion requires nonempty hash-bound promoted outputs')
        if not upstream or any(not isinstance(row, dict) or row.get('row_complete') is not True for row in upstream):
            errors.append('promotion requires complete upstream quality rows')
    if errors:
        print('FAIL')
        for error in errors:
            print(error)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
