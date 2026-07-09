from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
PLAN_ROOT = PROJECT_ROOT / "Plan"
OUT_DIR = PLAN_ROOT / "Instructions/QA/Evidence/Security"
TZ = ZoneInfo("America/Chicago")
NOW = datetime.now(TZ)
STAMP = NOW.strftime("%Y%m%dT%H%M%S-0500")
OUT = OUT_DIR / f"W64_SECRET_GIT_SECURITY_CHECKS_{STAMP}.json"

BLOCKED_SUFFIXES = (
    ".env",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".onnx",
    ".bin",
    ".gguf",
    ".mp4",
    ".mov",
    ".avi",
    ".wav",
    ".flac",
    ".mp3",
)
SECRET_RULES = {
    "github_classic_token": re.compile(r"ghp_[A-Za-z0-9_]{30,}"),
    "github_fine_grained_token": re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    "aws_access_key_id": re.compile(r"(?<![A-Z0-9])(AKIA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])"),
    "aws_secret_assignment": re.compile(r"(?i)\bAWS_SECRET_ACCESS_KEY\s*=\s*[^#\s]+"),
    "civitai_secret_assignment": re.compile(r"(?i)\bCIVITAI_(API_)?(TOKEN|KEY)\s*=\s*(?!$|<|\"|'|\s|REDACTED|placeholder|your_|CHANGEME|example)[^#\s]+"),
    "bearer_token_literal": re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def run_git(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git_lines(args: list[str]) -> list[str]:
    result = run_git(args)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def blocked_paths(paths: list[str]) -> list[str]:
    found = []
    for path in paths:
        lower = path.lower()
        name = Path(path).name.lower()
        if name == ".env" or any(lower.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
            found.append(path)
    return sorted(set(found))


def tracked_secret_findings(paths: list[str]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for name, pattern in SECRET_RULES.items():
        grep = run_git(["grep", "-n", "-I", "-E", pattern.pattern, "HEAD"])
        if grep.returncode not in (0, 1):
            continue
        for line in grep.stdout.splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 2 and parts[1].isdigit():
                file_part = parts[0].removeprefix("HEAD:")
                findings.append({"file": file_part, "line": int(parts[1]), "rule": name})
    return findings


def main() -> None:
    tracked = git_lines(["ls-files"])
    staged = git_lines(["diff", "--cached", "--name-only"])
    status = git_lines(["status", "--porcelain"])
    status_tracked_only = git_lines(["status", "--porcelain", "--untracked-files=no"])
    head = run_git(["rev-parse", "HEAD"]).stdout.strip()
    origin = run_git(["rev-parse", "origin/main"]).stdout.strip()
    gitignore_text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8-sig")
    required_ignore_patterns = [
        ".env",
        "*.env",
        ".env.*",
        "!.env.example",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "secrets/",
        "private/",
        "*.safetensors",
        "*.ckpt",
        "*.pt",
        "*.pth",
        "*.mp4",
        "*.wav",
    ]
    missing_ignore_patterns = [pattern for pattern in required_ignore_patterns if pattern not in gitignore_text]
    root_sensitive_files = []
    for path in PROJECT_ROOT.iterdir():
        if path.is_file() and (path.name == ".env" or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}):
            root_sensitive_files.append(
                {
                    "name": path.name,
                    "path": rel(path),
                    "bytes": path.stat().st_size,
                    "tracked": rel(path) in tracked,
                    "staged": rel(path) in staged,
                    "ignored": run_git(["check-ignore", "-q", rel(path)]).returncode == 0,
                }
            )

    tracked_blocked = blocked_paths(tracked)
    staged_blocked = blocked_paths(staged)
    tracked_secret_matches = tracked_secret_findings(tracked)
    staged_secret_matches = [finding for finding in tracked_secret_matches if finding["file"] in staged]

    record = {
        "schema_version": "1.0",
        "created_iso": NOW.replace(microsecond=0).isoformat(),
        "local_only": True,
        "aws_contacted": False,
        "github_api_contacted": False,
        "ec2_started": False,
        "generation_executed": False,
        "secrets_printed": False,
        "project_root": str(PROJECT_ROOT),
        "env_presence": {
            "env_exists": (PROJECT_ROOT / ".env").exists(),
            "env_example_exists": (PROJECT_ROOT / ".env.example").exists(),
            "root_sensitive_files": root_sensitive_files,
        },
        "gitignore_check": {
            "path": ".gitignore",
            "required_patterns": required_ignore_patterns,
            "missing_patterns": missing_ignore_patterns,
            "pass": len(missing_ignore_patterns) == 0,
        },
        "git_checkpoint": {
            "head": head,
            "origin_main": origin,
            "head_equals_origin": head == origin,
            "clean_worktree": len(status) == 0,
            "porcelain_count": len(status),
            "tracked_porcelain_count": len(status_tracked_only),
            "staged_count": len(staged),
        },
        "blocked_path_scan": {
            "tracked_blocked_count": len(tracked_blocked),
            "tracked_blocked_paths": tracked_blocked,
            "staged_blocked_count": len(staged_blocked),
            "staged_blocked_paths": staged_blocked,
            "no_binary_model_commit": len([path for path in tracked_blocked if path.lower().endswith((".safetensors", ".ckpt", ".pt", ".pth", ".onnx", ".bin", ".gguf"))]) == 0,
        },
        "secret_scan": {
            "scope": "tracked HEAD content and staged file intersection only; untracked .env value content intentionally not read",
            "tracked_secret_match_count": len(tracked_secret_matches),
            "tracked_secret_findings": tracked_secret_matches,
            "staged_secret_match_count": len(staged_secret_matches),
            "staged_secret_findings": staged_secret_matches,
        },
        "result": "pass_local_security_checks_except_checkpoint" if len(missing_ignore_patterns) == 0 and not staged_blocked and not staged_secret_matches and head == origin else "blocked_secret_git_security",
        "known_limits": [
            "Does not print or inspect untracked .env secret values.",
            "Does not commit, push, fetch, clean, reset, or unstage files.",
            "Dirty worktree is reported as a checkpoint blocker, not automatically resolved.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "result": record["result"], "porcelain_count": len(status), "staged_count": len(staged), "tracked_secret_match_count": len(tracked_secret_matches)}, indent=2))


if __name__ == "__main__":
    main()
