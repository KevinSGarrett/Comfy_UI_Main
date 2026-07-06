#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = [p for p in root.rglob('*') if p.is_file()]
    json_files = [p for p in files if p.suffix.lower() == '.json']
    scripts = [p for p in files if p.suffix.lower() == '.py']
    wave34_files = [str(p.relative_to(root)).replace('\\','/') for p in files if 'WAVE34' in p.name or 'wave34' in p.name]
    out = {
        'release_id': 'release_wave34_cumulative_final_integration',
        'release_type': 'cumulative_final_integration_architecture_pack',
        'pack_root': root.name,
        'file_count': len(files),
        'json_count': len(json_files),
        'script_count': len(scripts),
        'wave34_file_count': len(wave34_files),
        'wave34_files': sorted(wave34_files),
        'main_flow_inventory': '10_REGISTRIES/wave34_final_integration_inventory.json',
        'proof_boundaries': {
            'app_mode_export': 'required_later',
            'image_main_flow_runtime': 'requires_exact_output_evidence',
            'video_runtime': 'requires_generated_video_or_gif_evidence',
            'audio_runtime': 'requires_generated_audio_and_sync_evidence',
            'ec2_final_render': 'blocked_until_preview_QA_and_preflight_pass'
        },
        'validation_report_ref': '11_RELEASES/WAVE34_VALIDATION_REPORT.json',
        'handoff_ref': '11_RELEASES/WAVE34_FINAL_HANDOFF.md',
        'release_gate_decision_ref': '11_RELEASES/WAVE34_RELEASE_GATE_DECISION.json'
    }
    Path(args.output).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(args.output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
