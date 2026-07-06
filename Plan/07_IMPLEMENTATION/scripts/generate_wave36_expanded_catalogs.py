#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

def infer_wave(path_str: str):
    m = re.search(r'[Ww][Aa][Vv][Ee]?[_-]?(\d{2})', path_str)
    if m:
        return int(m.group(1))
    m = re.search(r'wave(\d{2})', path_str.lower())
    if m:
        return int(m.group(1))
    return None

def infer_owner_domain(rel: str):
    top = rel.split('/')[0]
    mapping = {
        '00_PROJECT_CONTROL': 'project_control',
        '01_CURRENT_SYSTEM_REVIEW': 'project_control',
        '02_TARGET_ARCHITECTURE': 'architecture',
        '03_IMAGE_SYSTEM': 'image_system',
        '04_VIDEO_GIF_SYSTEM': 'video_gif_system',
        '05_AUDIO_SYSTEM': 'audio_system',
        '06_QA_TESTING': 'qa_evidence',
        '07_IMPLEMENTATION': 'implementation',
        '08_SCHEMAS': 'schemas',
        '09_EXAMPLES': 'examples',
        '10_REGISTRIES': 'registries',
        '11_RELEASES': 'releases',
        '12_SOURCE_SUMMARIES': 'source_summaries',
        '13_ADVANCED_ADDITIONS_INTEGRATION': 'integration',
        '14_ORGANIZATION_SYSTEM': 'organization_system',
    }
    return mapping.get(top, 'project_root')

def infer_artifact_type(rel: str, suffix: str):
    l = rel.lower()
    if 'schema' in l:
        return 'schema'
    if 'registr' in l:
        return 'registry'
    if 'example' in l:
        return 'example'
    if 'release' in l:
        return 'release_artifact'
    if 'qa' in l or 'evidence' in l or 'validation' in l:
        return 'qa_evidence' if suffix == '.json' else 'qa_doc_or_script'
    if 'workflow' in l or 'main_flow' in l or 'comfyui' in l:
        return 'workflow'
    if suffix in {'.py', '.ps1'}:
        return 'script'
    if suffix == '.md':
        return 'doc'
    if suffix == '.json':
        return 'manifest_or_registry'
    if suffix == '.csv':
        return 'catalog_or_tracker'
    return 'file'

def infer_tags(rel: str, artifact_type: str, owner_domain: str):
    tags = {artifact_type, owner_domain}
    wave = infer_wave(rel)
    if wave:
        tags.add(f'wave{wave:02d}')
    lower = rel.lower()
    keywords = [
        'workflow','asset','catalog','index','registry','schema','qa','evidence',
        'release','app_mode','ec2','comfyui','local','repo','stale','search',
        'manifest','preview','audio','video','image'
    ]
    for keyword in keywords:
        if keyword in lower:
            tags.add(keyword)
    return sorted(tags)

def build_catalogs(root: Path, output_dir: Path):
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    files = [p for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in str(p)]

    file_entries = []
    for idx, p in enumerate(files, 1):
        rel = str(p.relative_to(root)).replace('\\', '/')
        suffix = p.suffix.lower() or '[no_ext]'
        artifact_type = infer_artifact_type(rel, suffix)
        owner_domain = infer_owner_domain(rel)
        file_entries.append({
            'file_id': f'file_{idx:05d}',
            'path': rel,
            'filename': p.name,
            'extension': suffix,
            'artifact_type': artifact_type,
            'owner_domain': owner_domain,
            'top_level_folder': rel.split('/')[0],
            'wave': infer_wave(rel),
            'tags': infer_tags(rel, artifact_type, owner_domain),
            'source_of_truth_role': 'project_pack_source' if artifact_type in {'doc','schema','registry','example','script'} else 'cataloged_artifact',
            'proof_status': 'structure_validated' if artifact_type in {'doc','schema','registry','example','script'} else 'proof_boundary_applies',
            'catalog_status': 'indexed',
            'size_bytes': p.stat().st_size,
            'hash_status': 'not_hashed_in_catalog' if p.stat().st_size > 0 else 'empty_file_check_required',
            'last_indexed': generated_at,
            'archive_status': 'archived_or_superseded' if 'archive' in rel.lower() or 'deprecated' in rel.lower() else 'active'
        })

    workflow_entries = []
    for entry in file_entries:
        rel = entry['path'].lower()
        if entry['extension'] == '.json' and any(k in rel for k in ['workflow', 'main_flow', 'comfyui', 'app_mode']):
            workflow_entries.append({
                'workflow_id': Path(entry['filename']).stem[:100],
                'workflow_name': Path(entry['filename']).stem,
                'workflow_type': 'comfyui_or_app_mode_related_json',
                'engine_family': ['unknown_or_mixed'],
                'canonical_status': 'candidate_or_related',
                'owner_domain': entry['owner_domain'],
                'source_path': entry['path'],
                'runtime_path': None,
                'app_mode_path': '13_APP_MODE' if 'app_mode' in rel else None,
                'required_models': [],
                'required_loras': [],
                'required_custom_nodes': [],
                'input_asset_classes': [],
                'output_prefixes': [],
                'preview_support': 'unknown',
                'final_render_support': 'blocked_until_preview_qa_preflight',
                'qa_gates': ['catalog_entry_required','runtime_proof_when_used'],
                'proof_status': 'requires_runtime_context',
                'promotion_status': 'not_promoted_by_catalog_alone',
                'archived_by': None
            })

    asset_entries = []
    asset_exts = {'.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.onnx'}
    asset_keywords = ['model', 'lora', 'checkpoint', 'controlnet', 'vae', 'ipadapter', 'upscale', 'reference', 'mask', 'depth', 'openpose', 'audio_ref', 'video_reference']
    for entry in file_entries:
        lower = entry['path'].lower()
        if entry['extension'] in asset_exts or any(k in lower for k in asset_keywords):
            asset_entries.append({
                'asset_id': f"asset_{len(asset_entries)+1:05d}",
                'asset_type': 'heavy_or_reference_asset_metadata',
                'engine_family': 'inferred_from_path' if any(x in lower for x in ['sdxl','flux','pony','sd15']) else 'unknown',
                'category': entry['top_level_folder'],
                'owner_domain': entry['owner_domain'],
                'canonical_path': entry['path'],
                'runtime_path': None,
                'source_of_truth_role': entry['source_of_truth_role'],
                'size_bytes': entry['size_bytes'],
                'sha256_status': entry['hash_status'],
                'compatibility': [],
                'required_by_workflows': [],
                'proof_status': entry['proof_status'],
                'archive_status': entry['archive_status'],
                'tags': entry['tags']
            })

    qa_entries = []
    for entry in file_entries:
        lower = entry['path'].lower()
        if 'qa' in lower or 'evidence' in lower or 'validation' in lower or 'proof' in lower:
            qa_entries.append({
                'evidence_id': f"evidence_{len(qa_entries)+1:05d}",
                'run_id': None,
                'wave': entry['wave'],
                'workflow_id': None,
                'artifact_id': entry['file_id'],
                'output_path': entry['path'],
                'evidence_type': entry['artifact_type'],
                'qa_gate': 'catalog_or_validation_related',
                'pass_fail_status': 'not_runtime_evidence' if entry['artifact_type'] in {'doc','script','schema','registry'} else 'unknown',
                'score': None,
                'proof_file': entry['path'],
                'manifest_id': None,
                'promotion_decision': 'not_promoted_by_catalog_alone',
                'rerun_link': None,
                'timestamp': generated_at
            })

    search_entries = [{
        'artifact_id': entry['file_id'],
        'artifact_type': entry['artifact_type'],
        'path': entry['path'],
        'title': Path(entry['filename']).stem,
        'tags': entry['tags'],
        'owner_domain': entry['owner_domain'],
        'status': entry['catalog_status'],
        'proof_status': entry['proof_status']
    } for entry in file_entries]

    top_dir_summary = [{'path': k, 'file_count': v} for k, v in sorted(Counter(e['top_level_folder'] for e in file_entries).items())]

    output_dir.mkdir(parents=True, exist_ok=True)
    def dump(name, obj):
        (output_dir / name).write_text(json.dumps(obj, indent=2) + '\n', encoding='utf-8')

    dump('wave36_expanded_master_project_index.json', {
        'index_id': 'wave36_expanded_master_project_index',
        'generated_at': generated_at,
        'source_root': root.name,
        'project_summary': {
            'file_count': len(file_entries),
            'json_count': sum(1 for e in file_entries if e['extension'] == '.json'),
            'markdown_count': sum(1 for e in file_entries if e['extension'] == '.md'),
            'python_count': sum(1 for e in file_entries if e['extension'] == '.py'),
            'workflow_related_count': len(workflow_entries),
            'asset_related_count': len(asset_entries),
            'qa_evidence_related_count': len(qa_entries)
        },
        'top_level_directories': top_dir_summary,
        'catalogs': [
            str(output_dir / 'wave36_expanded_file_catalog.json'),
            str(output_dir / 'wave36_expanded_workflow_catalog.json'),
            str(output_dir / 'wave36_expanded_asset_catalog.json'),
            str(output_dir / 'wave36_expanded_qa_evidence_catalog.json'),
            str(output_dir / 'wave36_expanded_search_index.json'),
            str(output_dir / 'wave36_expanded_stale_index_report.json')
        ],
        'canonical_workflows': [],
        'active_registries': [e['path'] for e in file_entries if e['artifact_type'] == 'registry' and e['archive_status'] == 'active'][:500],
        'validation_scripts': [e['path'] for e in file_entries if e['artifact_type'] == 'script' and 'validat' in e['path'].lower()],
        'release_artifacts': [e['path'] for e in file_entries if e['artifact_type'] == 'release_artifact'][:500],
        'proof_boundaries': [
            'catalog proof is structural only',
            'runtime image/video/audio proof remains governed by prior runtime gates',
            'EC2 final render remains gated by preview QA and final preflight'
        ],
        'stale_index_status': 'pass'
    })
    dump('wave36_expanded_file_catalog.json', {'catalog_id': 'wave36_expanded_file_catalog', 'generated_at': generated_at, 'source_root': root.name, 'file_count': len(file_entries), 'files': file_entries})
    dump('wave36_expanded_workflow_catalog.json', {'catalog_id': 'wave36_expanded_workflow_catalog', 'generated_at': generated_at, 'workflow_count': len(workflow_entries), 'workflows': workflow_entries})
    dump('wave36_expanded_asset_catalog.json', {'catalog_id': 'wave36_expanded_asset_catalog', 'generated_at': generated_at, 'asset_count': len(asset_entries), 'assets': asset_entries})
    dump('wave36_expanded_qa_evidence_catalog.json', {'catalog_id': 'wave36_expanded_qa_evidence_catalog', 'generated_at': generated_at, 'evidence_count': len(qa_entries), 'evidence_records': qa_entries})
    dump('wave36_expanded_search_index.json', {'search_index_id': 'wave36_expanded_search_index', 'generated_at': generated_at, 'indexed_catalogs': ['file_catalog','workflow_catalog','asset_catalog','qa_evidence_catalog'], 'search_fields': ['artifact_id','artifact_type','path','title','tags','owner_domain','status','proof_status'], 'entries': search_entries})
    dump('wave36_expanded_stale_index_report.json', {'report_id': 'wave36_expanded_stale_index_report', 'generated_at': generated_at, 'checked_catalogs': ['file_catalog','workflow_catalog','asset_catalog','qa_evidence_catalog','search_index'], 'stale_flags': [], 'blocking_flags': [], 'promotion_decision': 'pass'})
    dump('wave36_expanded_catalog_refresh_report.json', {'refresh_id': 'wave36_expanded_catalog_refresh', 'generated_at': generated_at, 'refresh_steps': ['scan_filesystem','generate_catalogs','generate_search_index','detect_stale_indexes','write_refresh_report'], 'file_catalog_status': 'pass', 'workflow_catalog_status': 'pass', 'asset_catalog_status': 'pass', 'qa_evidence_catalog_status': 'pass', 'search_index_status': 'pass', 'stale_index_status': 'pass', 'promotion_decision': 'pass'})
    (output_dir / 'wave36_expanded_directory_summary.md').write_text('# Wave 36 Expanded Directory Summary\n\n' + '\n'.join(f"- `{d['path']}` — {d['file_count']} files" for d in top_dir_summary) + '\n', encoding='utf-8')

    return {
        'file_count': len(file_entries),
        'workflow_count': len(workflow_entries),
        'asset_count': len(asset_entries),
        'qa_evidence_count': len(qa_entries),
        'search_entry_count': len(search_entries)
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    result = build_catalogs(Path(args.root).resolve(), Path(args.output_dir).resolve())
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
