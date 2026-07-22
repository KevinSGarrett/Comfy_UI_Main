#!/usr/bin/env python3
"""Build three admitted LatentSync source-only wheels in an isolated builder."""

from __future__ import annotations

import argparse
import ast
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile


EXPECTED_ADMISSION_SHA256 = "cbfdab14ce7ab4f703c6f175bc5e1c52f544aac692d8c4315afd86af5fd20871"
EXPECTED_BUILDER_LOCK_SHA256 = "06610318056d7345485f7623316882c20fbd07913aa05f28aa6ef79458db16a7"
EXPECTED_SOURCE_LOCK_SHA256 = "ac29c11ced5d4be9b22ff4c0fcec9a9d48361d9dfcb1996bf2fdd2a8526b9605"
EXPECTED_UV_VERSION = "0.11.30"
EXPECTED_BUILDER_DISTRIBUTIONS = {
    "cython": "3.2.8",
    "numpy": "1.26.4",
    "packaging": "26.2",
    "pip": "26.1.2",
    "setuptools": "83.0.0",
    "wheel": "0.46.3",
}
FORBIDDEN_IMPORT_ROOTS = {"requests", "socket", "subprocess", "urllib"}
FORBIDDEN_CALLS = {"eval", "exec", "os.popen", "os.system"}
RUNTIME_CLAIMS = {
    "package_imported": False,
    "project_code_imported": False,
    "runtime_environment_installed": False,
    "model_loaded": False,
    "tensor_allocated": False,
    "gpu_or_lease_polled": False,
    "inference_performed": False,
    "service_changed": False,
    "role_activated": False,
    "product_authority": False,
}


class BuildError(RuntimeError):
    """A fail-closed source-wheel build error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise BuildError(
            f"command failed ({completed.returncode}): {command!r}\n{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def normalized_name(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(".", "-")


def safe_member_path(name: str) -> bool:
    pure = PurePosixPath(name)
    return bool(name) and not pure.is_absolute() and ".." not in pure.parts


def load_admission(path: Path, builder_lock_path: Path, source_lock_path: Path) -> dict:
    if sha256_file(path) != EXPECTED_ADMISSION_SHA256:
        raise BuildError("admission hash mismatch")
    if sha256_file(builder_lock_path) != EXPECTED_BUILDER_LOCK_SHA256:
        raise BuildError("builder lock hash mismatch")
    if sha256_file(source_lock_path) != EXPECTED_SOURCE_LOCK_SHA256:
        raise BuildError("source dependency lock hash mismatch")
    admission = json.loads(path.read_text(encoding="utf-8"))
    if admission.get("status") != "SOURCE_WHEEL_BUILD_ADMITTED_EXECUTION_PENDING":
        raise BuildError("source-wheel build is not admitted")
    authority = admission.get("authority", {})
    allowed_true = {
        "exact_sdist_download",
        "isolated_builder_create",
        "exact_sdist_build_execution",
        "wheel_publish",
    }
    if any(authority.get(name) is not True for name in allowed_true):
        raise BuildError("required source-wheel authority missing")
    if any(value is not False for name, value in authority.items() if name not in allowed_true):
        raise BuildError("admission exceeds source-wheel build authority")
    return admission


def validate_paths(admission: dict) -> tuple[Path, Path, Path]:
    target = Path(admission["targets"]["wheelhouse_root"])
    receipt = Path(admission["targets"]["receipt_path"])
    if not target.as_posix().startswith("/workspace/w64_aqa/wheelhouse/LatentSync-1.6/"):
        raise BuildError("unsafe wheelhouse target")
    if target.name != EXPECTED_BUILDER_LOCK_SHA256:
        raise BuildError("wheelhouse target is not builder-lock addressed")
    staging = target.with_name(f".{target.name}.building")
    if not receipt.as_posix().startswith("/workspace/w64_aqa/control/receipts/"):
        raise BuildError("unsafe receipt target")
    if any(path.is_symlink() for path in (target, staging, receipt)):
        raise BuildError("target, staging, or receipt path is a symlink")
    return target, staging, receipt


def distribution_manifest(python: Path | str) -> list[dict[str, str]]:
    values = json.loads(run(["uv", "pip", "list", "--python", str(python), "--format", "json"]))
    return sorted(
        ({"name": normalized_name(item["name"]), "version": item["version"]} for item in values),
        key=lambda item: (item["name"], item["version"]),
    )


def distribution_signature(python: Path | str) -> str:
    payload = json.dumps(distribution_manifest(python), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def download_source(source: dict, destination: Path) -> dict:
    parsed = urllib.parse.urlparse(source["url"])
    if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
        raise BuildError("source URL is outside the allowlist")
    request = urllib.request.Request(source["url"], headers={"User-Agent": "W64-AQA/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "files.pythonhosted.org":
            raise BuildError("source redirect left the allowlist")
        with destination.open("xb") as handle:
            shutil.copyfileobj(response, handle)
    digest = sha256_file(destination)
    if digest != source["sha256"]:
        raise BuildError(f"{source['name']}: source hash mismatch")
    return {"name": source["name"], "version": source["version"], "sha256": digest, "bytes": destination.stat().st_size}


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def scan_build_script(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise BuildError(f"cannot statically parse {path.name}: {exc}") from exc
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                    findings.append(f"import:{alias.name}")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
            findings.append(f"import:{node.module}")
        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in FORBIDDEN_CALLS or name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                findings.append(f"call:{name}")
    return sorted(set(findings))


def audit_and_extract(source_archive: Path, destination: Path) -> dict:
    with tarfile.open(source_archive, "r:gz") as archive:
        members = archive.getmembers()
        if not members:
            raise BuildError("empty source archive")
        for member in members:
            if not safe_member_path(member.name):
                raise BuildError("unsafe source archive path")
            if member.issym() or member.islnk() or member.isdev():
                raise BuildError("source archive link or device entry rejected")
        archive.extractall(destination, filter="data")
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise BuildError("source archive must contain one root directory")
    root_setup = roots[0] / "setup.py"
    if not root_setup.is_file() or root_setup.is_symlink():
        raise BuildError("source archive root setup.py is missing or unsafe")
    scripts = sorted(roots[0].rglob("setup.py"))
    findings = sorted(
        {
            f"{script.relative_to(roots[0]).as_posix()}:{finding}"
            for script in scripts
            for finding in scan_build_script(script)
        }
    )
    if findings:
        raise BuildError(f"source build script static gate failed: {findings}")
    return {
        "archive_member_count": len(members),
        "root": roots[0].name,
        "root_setup_script": "setup.py",
        "scanned_setup_scripts": [
            script.relative_to(roots[0]).as_posix() for script in scripts
        ],
        "static_findings": findings,
    }


def inspect_wheel(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        for info in infos:
            if not safe_member_path(info.filename):
                raise BuildError("unsafe wheel archive path")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise BuildError("wheel symlink entry rejected")
        metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        record_paths = [name for name in archive.namelist() if name.endswith(".dist-info/RECORD")]
        if len(metadata_paths) != 1 or len(record_paths) != 1:
            raise BuildError("wheel METADATA or RECORD identity mismatch")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
    return {
        "filename": path.name,
        "name": normalized_name(metadata["Name"]),
        "version": metadata["Version"],
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "entry_count": len(infos),
        "record_present": True,
        "symlink_count": 0,
    }


def tree_manifest(root: Path) -> dict:
    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.is_symlink():
            raise BuildError("wheelhouse contains a non-regular file")
        size = path.stat().st_size
        digest.update(f"F\0{path.name}\0{size}\0{sha256_file(path)}\n".encode())
        count += 1
        total += size
    return {"sha256": digest.hexdigest(), "file_count": count, "total_bytes": total}


def write_receipt_temp(path: Path, receipt: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.installing")
    if path.exists() or temporary.exists() or path.is_symlink() or temporary.is_symlink():
        raise BuildError("receipt target already exists")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def verify_replay(target: Path, receipt_path: Path) -> dict:
    if not target.is_dir() or not receipt_path.is_file():
        raise BuildError("partial prior wheel build cannot be reused")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("wheelhouse_tree") != tree_manifest(target):
        raise BuildError("existing wheelhouse tree does not match receipt")
    wheels = sorted((inspect_wheel(path) for path in target.glob("*.whl")), key=lambda item: item["name"])
    if receipt.get("wheels") != wheels:
        raise BuildError("existing wheel manifest does not match receipt")
    return {"status": "REUSED_VERIFIED_SOURCE_WHEELS", "receipt": str(receipt_path)}


def build(admission_path: Path, builder_lock_path: Path, source_lock_path: Path, active_python: str) -> dict:
    admission = load_admission(admission_path, builder_lock_path, source_lock_path)
    target, staging, receipt_path = validate_paths(admission)
    if target.exists() or receipt_path.exists():
        return verify_replay(target, receipt_path)
    if staging.exists():
        raise BuildError("stale wheel-build staging path requires independent disposition")

    builder = admission["builder"]
    base = Path(builder["python_executable"])
    if run([str(base), "--version"]) != f"Python {builder['python_version']}":
        raise BuildError("base Python version mismatch")
    if sha256_file(base) != builder["python_sha256"]:
        raise BuildError("base Python hash mismatch")
    if run(["uv", "--version"]).split()[:2] != ["uv", EXPECTED_UV_VERSION]:
        raise BuildError("uv version mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(target.parent).free
    if free_bytes < builder["minimum_free_bytes"]:
        raise BuildError("insufficient free space for source-wheel build")
    active_before = distribution_signature(active_python)

    receipt_temp: Path | None = None
    try:
        sources_dir = staging / "sources"
        extracted_dir = staging / "extracted"
        wheels_dir = staging / "wheels"
        builder_dir = staging / "builder"
        for path in (sources_dir, extracted_dir, wheels_dir):
            path.mkdir(parents=True, exist_ok=False)
        source_rows: list[dict] = []
        audit_rows: list[dict] = []
        extracted_roots: list[Path] = []
        for source in admission["sources"]:
            archive = sources_dir / source["filename"]
            source_rows.append(download_source(source, archive))
            package_extract = extracted_dir / source["name"]
            package_extract.mkdir()
            audit = audit_and_extract(archive, package_extract)
            audit_rows.append({"name": source["name"], **audit})
            extracted_roots.append(package_extract / audit["root"])

        run(["uv", "venv", "--python", str(base), str(builder_dir)])
        builder_python = builder_dir / "bin/python"
        staged_builder_lock = staging / "pylock.builder.toml"
        shutil.copyfile(builder_lock_path, staged_builder_lock)
        if sha256_file(staged_builder_lock) != EXPECTED_BUILDER_LOCK_SHA256:
            raise BuildError("staged builder lock hash mismatch")
        run(["uv", "pip", "sync", "--python", str(builder_python), str(staged_builder_lock)])
        run(["uv", "pip", "check", "--python", str(builder_python)])
        distributions = distribution_manifest(builder_python)
        observed = {row["name"]: row["version"] for row in distributions}
        if observed != EXPECTED_BUILDER_DISTRIBUTIONS:
            raise BuildError("isolated builder distribution set mismatch")

        for root in extracted_roots:
            run([
                str(builder_python),
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheels_dir),
                str(root),
            ])
        wheel_paths = sorted(wheels_dir.glob("*.whl"))
        if len(wheel_paths) != 3:
            raise BuildError("source-wheel build did not produce exactly three wheels")
        wheels = sorted((inspect_wheel(path) for path in wheel_paths), key=lambda item: item["name"])
        expected = {source["name"]: source["version"] for source in admission["sources"]}
        if {row["name"]: row["version"] for row in wheels} != expected:
            raise BuildError("built wheel name or version mismatch")

        active_after = distribution_signature(active_python)
        if active_before != active_after:
            raise BuildError("active Python distribution metadata changed")
        for child in list(staging.iterdir()):
            if child != wheels_dir:
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        for wheel in list(wheels_dir.iterdir()):
            os.replace(wheel, staging / wheel.name)
        wheels_dir.rmdir()
        wheelhouse_tree = tree_manifest(staging)
        receipt = {
            "schema_version": "wave64.aqa.latentsync_source_wheel_build_receipt.v1",
            "program_id": "W64-AQA",
            "package_id": "W64-AQA-PKG-LATENTSYNC-1.6",
            "status": "SOURCE_WHEELS_BUILT_HASHED_METADATA_VERIFIED_RUNTIME_INSTALL_PENDING",
            "admission_sha256": EXPECTED_ADMISSION_SHA256,
            "builder_lock_sha256": EXPECTED_BUILDER_LOCK_SHA256,
            "source_dependency_lock_sha256": EXPECTED_SOURCE_LOCK_SHA256,
            "wheelhouse_root": str(target),
            "free_bytes_before": free_bytes,
            "prior_attempts": [
                {
                    "controller_commit": "b3d95949",
                    "result": "FAIL_CLOSED_BEFORE_BUILD_EXECUTION",
                    "reason": "insightface archive contains a safe nested third-party setup.py in addition to the required root setup.py",
                    "staging_removed": True,
                    "wheelhouse_published": False,
                },
                {
                    "controller_commit": "127563b8",
                    "result": "FAIL_CLOSED_BEFORE_BUILD_EXECUTION",
                    "reason": "uv requires the staged PEP 751 lock basename to begin with pylock.",
                    "staging_removed": True,
                    "wheelhouse_published": False,
                },
            ],
            "builder": {
                "python_version": builder["python_version"],
                "python_sha256": builder["python_sha256"],
                "uv_version": EXPECTED_UV_VERSION,
                "distributions": distributions,
                "pip_check": "PASS_6_PACKAGES_COMPATIBLE",
            },
            "sources": source_rows,
            "static_audits": audit_rows,
            "wheels": wheels,
            "wheelhouse_tree": wheelhouse_tree,
            "active_environment": {
                "python": active_python,
                "metadata_signature_before": active_before,
                "metadata_signature_after": active_after,
                "unchanged": True,
            },
            "runtime_claims": RUNTIME_CLAIMS,
        }
        receipt_temp = write_receipt_temp(receipt_path, receipt)
        os.replace(staging, target)
        os.replace(receipt_temp, receipt_path)
        receipt_temp = None
        return {"status": "CREATED_VERIFIED_SOURCE_WHEELS", "receipt": str(receipt_path)}
    except Exception:
        if receipt_temp and receipt_temp.exists() and not receipt_temp.is_symlink():
            receipt_temp.unlink()
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--builder-lock", type=Path, required=True)
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--active-python", default="python3")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.admission, args.builder_lock, args.source_lock, args.active_python), sort_keys=True))
    except (BuildError, OSError, ValueError, json.JSONDecodeError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
