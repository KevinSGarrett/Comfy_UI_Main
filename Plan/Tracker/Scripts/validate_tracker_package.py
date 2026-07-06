#!/usr/bin/env python3
from __future__ import annotations
import csv, json, sys
from pathlib import Path

PLAN_PREFIX = 'C:\\Comfy_UI_Main\\Plan'

def load_source_keys(path: Path):
    keys = set()
    with path.open(newline='', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            keys.add(row.get('Source_Key',''))
    return {k for k in keys if k}

def validate(root: Path):
    master = root / 'wave48_52_master_autonomous_tracker.csv'
    source_index = root / 'Coverage_Audit/ultra_blueprint_source_section_index.csv'
    schema = json.loads((root / 'Schemas/tracker_row_schema.json').read_text(encoding='utf-8'))
    required = schema['required_columns']
    errors = []
    row_count = 0
    waves = set()
    bad_human = 0
    bad_citation = 0
    bad_lines = 0
    tracker_source_keys = set()

    with master.open(newline='', encoding='utf-8-sig', errors='ignore') as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in required if c not in (reader.fieldnames or [])]
        if missing_cols:
            errors.append(f'missing columns: {missing_cols}')
        for row in reader:
            row_count += 1
            waves.add(row.get('Wave',''))
            if row.get('Human_Input_Allowed') != 'FALSE' or row.get('Human_Work_Allowed') != 'FALSE':
                bad_human += 1
            if not row.get('Citation_Full_Path','').startswith(PLAN_PREFIX):
                bad_citation += 1
            try:
                int(row.get('Citation_Line_Start','0'))
                int(row.get('Citation_Line_End','0'))
            except Exception:
                bad_lines += 1
            if row.get('Source_Key'):
                tracker_source_keys.add(row['Source_Key'])

    expected_waves = {'48','49','50','51','52'}
    if not expected_waves.issubset(waves):
        errors.append(f'missing expected waves: {sorted(expected_waves - waves)}')
    if bad_human:
        errors.append(f'human flags not false rows: {bad_human}')
    if bad_citation:
        errors.append(f'bad citation path rows: {bad_citation}')
    if bad_lines:
        errors.append(f'bad citation line rows: {bad_lines}')

    source_keys = load_source_keys(source_index)
    missing_source_keys = sorted(source_keys - tracker_source_keys)
    if missing_source_keys:
        errors.append(f'missing Ultra source coverage keys: {len(missing_source_keys)}')

    report = {
        'package': 'Tracker Waves 48-52 Coverage Verified',
        'row_count': row_count,
        'waves_present': sorted(waves),
        'ultra_source_section_records': len(source_keys),
        'ultra_source_keys_covered': len(source_keys - set(missing_source_keys)),
        'missing_ultra_source_keys': len(missing_source_keys),
        'bad_human_flag_rows': bad_human,
        'bad_citation_rows': bad_citation,
        'bad_line_rows': bad_lines,
        'errors': errors,
        'promotion_decision': 'pass' if not errors else 'fail'
    }
    (root / 'Reports/tracker_validation_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    raise SystemExit(validate(root))
