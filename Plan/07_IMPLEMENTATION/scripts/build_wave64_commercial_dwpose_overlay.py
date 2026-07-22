from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable


class OverlayBuildError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_files(directory: Path, specs: list[dict[str, Any]]) -> list[Path]:
    expected = {item["filename"] for item in specs}
    actual = {path.name for path in directory.iterdir() if path.is_file()}
    if actual != expected:
        raise OverlayBuildError(f"artifact set mismatch in {directory}")
    verified: list[Path] = []
    for item in specs:
        path = (directory / item["filename"]).resolve()
        if path.parent != directory.resolve() or path.is_symlink() or path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
            raise OverlayBuildError(f"artifact identity mismatch: {item['filename']}")
        verified.append(path)
    return verified


def _offline_install(python: Path, site_packages: Path, wheels: list[Path]) -> None:
    environment = os.environ.copy()
    environment.update({"PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INDEX": "1"})
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", "--target", str(site_packages), *map(str, wheels)],
        check=True,
        env=environment,
    )


def build_overlay(
    wheelhouse: Path,
    model_dir: Path,
    output_dir: Path,
    lock_path: Path,
    staging_package_path: Path,
    node_path: Path,
    python: Path = Path(sys.executable),
    installer: Callable[[Path, Path, list[Path]], None] = _offline_install,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise OverlayBuildError("output directory already exists")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    staging = json.loads(staging_package_path.read_text(encoding="utf-8"))
    wheels = _verify_files(wheelhouse.resolve(), staging["wheels"])
    models = _verify_files(model_dir.resolve(), staging["models"])
    if {item["filename"] for item in lock["wheels"]} != {item["filename"] for item in staging["wheels"]}:
        raise OverlayBuildError("runtime lock and staging package wheel sets differ")
    partial = output_dir.with_name(f".{output_dir.name}.partial-{uuid.uuid4().hex}")
    try:
        site_packages = partial / "site_packages"
        node_target = partial / "custom_nodes/wave64_commercial_dwpose"
        model_target = node_target / "models"
        site_packages.mkdir(parents=True)
        model_target.mkdir(parents=True)
        installer(python.resolve(), site_packages, wheels)
        shutil.copy2(node_path, node_target / "__init__.py")
        shutil.copy2(lock_path, node_target / "runtime_lock.json")
        for model in models:
            shutil.copy2(model, model_target / model.name)
        manifest = {
            "schema_version": "wave64.commercial_dwpose.overlay_manifest.v1",
            "status": "OFFLINE_OVERLAY_BUILT_NOT_IMPORTED",
            "site_packages": str(output_dir / "site_packages"),
            "custom_node": str(output_dir / "custom_nodes/wave64_commercial_dwpose"),
            "node_sha256": _sha256(node_target / "__init__.py"),
            "wheel_artifacts": [{"filename": path.name, "sha256": _sha256(path)} for path in wheels],
            "model_artifacts": [{"filename": path.name, "sha256": _sha256(path)} for path in models],
            "launch_environment": {"PYTHONPATH_prepend": str(output_dir / "site_packages"), "WAVE64_DWPOSE_OVERLAY_SITE_PACKAGES": str(output_dir / "site_packages")},
            "authority": {"offline_install": True, "custom_node_import": False, "onnx_session": False, "gpu_use": False, "object_info": False},
        }
        (partial / "OVERLAY_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        partial.rename(output_dir)
        return manifest
    except Exception:
        if partial.exists() and partial.parent == output_dir.parent:
            shutil.rmtree(partial)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--staging-package", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    build_overlay(args.wheelhouse, args.model_dir, args.output_dir, args.lock, args.staging_package, args.node, args.python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
