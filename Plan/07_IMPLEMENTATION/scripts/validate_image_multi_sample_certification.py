#!/usr/bin/env python3
"""Validate the Wave64 Row018 multi-sample image certification contract."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA256 = re.compile(r'^[0-9a-f]{64}$')


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    args = parser.parse_args()
    obj = load(Path(args.input))
    errors: list[str] = []
    required = ('schema_version', 'lane_id', 'multi_seed_sample_set', 'aggregate_score', 'defect_rate_limit', 'consistency_status', 'portfolio_certification_record')
    errors.extend(f'missing: {key}' for key in required if key not in obj)
    if obj.get('schema_version') != 'row018.v1':
        errors.append('schema_version must be row018.v1')
    samples = obj.get('multi_seed_sample_set')
    if not isinstance(samples, list) or len(samples) < 3:
        errors.append('multi_seed_sample_set must contain at least three samples')
        samples = []
    scores: list[float] = []
    blocking_count = 0
    seeds: set[str] = set()
    prompts: set[str] = set()
    target_runtime_count = 0
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            errors.append(f'sample[{index}] must be an object')
            continue
        seeds.add(str(sample.get('seed')))
        prompt = sample.get('prompt_reference')
        if isinstance(prompt, str) and prompt.strip():
            prompts.add(prompt)
        else:
            errors.append(f'sample[{index}].prompt_reference is invalid')
        artifact = sample.get('artifact', {})
        if not isinstance(artifact.get('path'), str) or not artifact.get('path', '').strip() or not isinstance(artifact.get('sha256'), str) or not SHA256.fullmatch(artifact['sha256']):
            errors.append(f'sample[{index}].artifact is invalid')
        score = sample.get('visual_score')
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 5:
            errors.append(f'sample[{index}].visual_score is invalid')
        else:
            scores.append(float(score))
        defects = sample.get('blocking_defects')
        if not isinstance(defects, list):
            errors.append(f'sample[{index}].blocking_defects must be an array')
        elif defects:
            blocking_count += 1
        if sample.get('target_runtime_proof') is True:
            target_runtime_count += 1
    aggregate = obj.get('aggregate_score', {})
    actual_mean = sum(scores) / len(scores) if scores else 0.0
    actual_min = min(scores) if scores else 0.0
    if abs(float(aggregate.get('mean', -1)) - actual_mean) > 1e-6 or abs(float(aggregate.get('minimum', -1)) - actual_min) > 1e-6:
        errors.append('aggregate_score must match sample scores')
    defect = obj.get('defect_rate_limit', {})
    actual_rate = blocking_count / len(samples) if samples else 0.0
    if defect.get('sample_count') != len(samples) or defect.get('blocking_defect_sample_count') != blocking_count or abs(float(defect.get('rate', -1)) - actual_rate) > 1e-6:
        errors.append('defect_rate_limit must match sample defects')
    record = obj.get('portfolio_certification_record', {})
    if record.get('decision') == 'certified':
        if len(seeds) < 3 or len(prompts) < 2:
            errors.append('portfolio certification requires seed and prompt diversity')
        if any(sample.get('technical_status') != 'pass' for sample in samples):
            errors.append('portfolio certification requires every technical status to pass')
        if actual_mean < aggregate.get('required_mean', 4) or actual_min < aggregate.get('required_minimum', 3):
            errors.append('portfolio certification requires aggregate score thresholds')
        if actual_rate > defect.get('maximum_rate', 0) or blocking_count:
            errors.append('portfolio certification requires the defect-rate limit and zero blocking defects')
        if obj.get('consistency_status') != 'pass':
            errors.append('portfolio certification requires consistency pass')
        if target_runtime_count != len(samples) or record.get('target_runtime_sample_count') != len(samples):
            errors.append('portfolio certification requires target-runtime proof for every sample')
        if not isinstance(record.get('certified_scope'), str) or not record.get('certified_scope', '').strip():
            errors.append('portfolio certification requires a non-empty certified scope')
    if errors:
        print('FAIL')
        for error in errors:
            print(error)
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
