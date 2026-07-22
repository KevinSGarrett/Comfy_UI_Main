from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import uuid
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Callable


class EnvironmentOverlayError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _verify_base_environment(base: Path, spec: dict[str, Any]) -> Path:
    base = base.resolve(strict=True)
    if str(base) != spec["root"]:
        raise EnvironmentOverlayError("base environment root mismatch")
    pyvenv = base / "pyvenv.cfg"
    if not pyvenv.is_file() or "include-system-site-packages = false" not in pyvenv.read_text(encoding="utf-8"):
        raise EnvironmentOverlayError("base environment must exclude system site packages")
    python = base / "bin/python"
    site_packages = base / "lib/python3.12/site-packages"
    required = [site_packages / relative for relative in spec["required_paths"]]
    if not python.is_file() or any(not path.exists() for path in required):
        raise EnvironmentOverlayError("base environment required path missing")
    return python


def _verify_wheels(wheelhouse: Path, specs: list[dict[str, Any]]) -> list[Path]:
    wheelhouse = wheelhouse.resolve(strict=True)
    expected = {item["filename"] for item in specs}
    actual = {path.name for path in wheelhouse.iterdir() if path.is_file()}
    if actual != expected:
        raise EnvironmentOverlayError("wheelhouse set mismatch")
    verified: list[Path] = []
    for item in specs:
        path = wheelhouse / item["filename"]
        if path.is_symlink() or path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
            raise EnvironmentOverlayError(f"wheel identity mismatch: {item['filename']}")
        verified.append(path)
    return verified


def _offline_install(_python: Path, target: Path, wheels: list[Path]) -> None:
    written: set[str] = set()
    for wheel in wheels:
        if not wheel.name.endswith("-py3-none-any.whl"):
            raise EnvironmentOverlayError(f"non-pure wheel forbidden: {wheel.name}")
        with zipfile.ZipFile(wheel) as archive:
            wheel_metadata = [name for name in archive.namelist() if name.endswith(".dist-info/WHEEL")]
            if len(wheel_metadata) != 1:
                raise EnvironmentOverlayError(f"wheel metadata mismatch: {wheel.name}")
            metadata = archive.read(wheel_metadata[0]).decode("utf-8")
            if "Root-Is-Purelib: true" not in metadata or "Tag: py3-none-any" not in metadata:
                raise EnvironmentOverlayError(f"wheel purity metadata mismatch: {wheel.name}")
            for member in archive.infolist():
                relative = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                if member.is_dir():
                    continue
                if relative.is_absolute() or ".." in relative.parts or stat.S_ISLNK(mode):
                    raise EnvironmentOverlayError(f"unsafe wheel member: {member.filename}")
                normalized = relative.as_posix()
                if normalized in written:
                    raise EnvironmentOverlayError(f"duplicate wheel member: {normalized}")
                written.add(normalized)
                destination = target.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)


def _tree_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def build_overlay(
    admission_path: Path,
    wheelhouse: Path,
    output_dir: Path,
    installer: Callable[[Path, Path, list[Path]], None] = _offline_install,
) -> dict[str, Any]:
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    if _canonical_sha256(admission["lock_material"]) != admission["lock_sha256"]:
        raise EnvironmentOverlayError("admission lock digest mismatch")
    output_dir = output_dir.resolve()
    if str(output_dir) != admission["target_root"]:
        raise EnvironmentOverlayError("target root mismatch")
    if output_dir.exists():
        raise EnvironmentOverlayError("target root already exists")
    python = _verify_base_environment(Path(admission["lock_material"]["base_environment"]["root"]), admission["lock_material"]["base_environment"])
    wheels = _verify_wheels(wheelhouse, admission["lock_material"]["wheels"])
    partial = output_dir.with_name(f".{output_dir.name}.partial-{uuid.uuid4().hex}")
    try:
        site_packages = partial / "site_packages"
        site_packages.mkdir(parents=True)
        installer(python, site_packages, wheels)
        files = _tree_manifest(site_packages)
        manifest = {
            "schema_version": "wave64.aqa.internvl_dependency_overlay_manifest.v1",
            "status": "IMMUTABLE_ADDON_OVERLAY_BUILT_NOT_IMPORTED",
            "lock_sha256": admission["lock_sha256"],
            "base_environment": admission["lock_material"]["base_environment"],
            "addon_site_packages": str(output_dir / "site_packages"),
            "wheel_artifacts": [{"filename": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)} for path in wheels],
            "installed_files": files,
            "installed_file_count": len(files),
            "installed_bytes": sum(item["bytes"] for item in files),
            "installed_tree_sha256": _canonical_sha256(files),
            "launch": {"python": str(python), "PYTHONPATH_prepend": str(output_dir / "site_packages")},
            "authority": {"offline_addon_install": True, "base_environment_mutated": False, "custom_code_import": False, "model_load": False, "gpu_use": False},
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
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_overlay(args.admission, args.wheelhouse, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
