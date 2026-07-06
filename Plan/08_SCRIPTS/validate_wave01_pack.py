import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "PROJECT_MANIFEST.json",
    "00_PROJECT_CONTROL/WAVE_01_DELIVERY_REPORT.md",
    "00_PROJECT_CONTROL/WAVE_01_AI_PM_TASKS.md",
    "01_CURRENT_SYSTEM_REVIEW/WAVE01_SOURCE_STATUS_AND_BOUNDARY.md",
    "02_TARGET_ARCHITECTURE/WAVE01_REPO_LOCAL_EC2_S3_ARCHITECTURE.md",
    "02_TARGET_ARCHITECTURE/WAVE01_COST_AWARE_RUNTIME_STRATEGY.md",
    "06_QA_TESTING/WAVE01_STRICT_QA_REVIEW_TEST_MATRIX.md",
    "07_IMPLEMENTATION/WAVE01_LOCAL_REPO_BOOTSTRAP_MANUAL.md",
    "07_IMPLEMENTATION/WAVE01_GITHUB_REPO_SETUP_MANUAL.md",
    "07_IMPLEMENTATION/WAVE01_MODEL_ASSET_STORAGE_MANUAL.md",
    "07_IMPLEMENTATION/WAVE01_EC2_RUNTIME_PROOF_GATE.md",
    "07_IMPLEMENTATION/scripts/wave01_init_local_repo.ps1",
    "07_IMPLEMENTATION/scripts/wave01_validate_local_repo.ps1",
    "07_IMPLEMENTATION/scripts/check_no_model_files_in_git.py",
    "07_IMPLEMENTATION/templates/repo/.gitignore",
    "07_IMPLEMENTATION/templates/repo/.gitattributes",
    "08_SCHEMAS/repo_manifest.schema.json",
    "08_SCHEMAS/ec2_runtime_proof_request.schema.json",
    "09_EXAMPLES/repo_manifest.example.json",
    "09_EXAMPLES/ec2_runtime_proof_request.example.json",
    "10_REGISTRIES/wave01_source_inventory.json",
    "10_REGISTRIES/wave01_repo_layout_registry.json"
]

FORBIDDEN_SUFFIXES = {".safetensors",".ckpt",".pt",".pth",".bin",".gguf",".onnx",".mp4",".mov",".avi",".mkv",".webm",".wav",".flac",".mp3",".zip",".7z",".rar"}

def main():
    failures = []
    for r in REQUIRED:
        if not (ROOT / r).exists():
            failures.append(f"missing required file: {r}")

    for p in ROOT.rglob("*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            failures.append(f"bad json: {p.relative_to(ROOT)} :: {e}")

    # Allow the output pack to contain no raw model/media binaries.
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in FORBIDDEN_SUFFIXES:
            # Previous zip itself is not expected inside the pack, and templates should not include these.
            failures.append(f"forbidden binary/archive in blueprint pack: {p.relative_to(ROOT)}")

    report = {
        "pack": "Wave01 cumulative",
        "root": str(ROOT),
        "required_files_checked": len(REQUIRED),
        "json_files_checked": len(list(ROOT.rglob("*.json"))),
        "failures": failures,
        "passed": not failures
    }
    out = ROOT / "11_RELEASES" / "WAVE01_VALIDATION_REPORT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if failures:
        for f in failures:
            print("FAIL", f)
        sys.exit(1)
    print("Wave01 pack validation passed.")

if __name__ == "__main__":
    main()
