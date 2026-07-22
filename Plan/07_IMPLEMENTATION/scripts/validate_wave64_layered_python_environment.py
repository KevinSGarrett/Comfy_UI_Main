from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def _distributions(paths: list[Path]) -> dict[str, importlib.metadata.Distribution]:
    found: dict[str, importlib.metadata.Distribution] = {}
    for distribution in importlib.metadata.Distribution.discover(path=[str(path) for path in paths]):
        name = canonicalize_name(distribution.metadata["Name"])
        if name in found:
            raise ValueError(f"duplicate distribution: {name}")
        found[name] = distribution
    return found


def validate_layer(base_site_packages: Path, overlay_site_packages: Path, selected: list[str]) -> dict[str, Any]:
    base_site_packages = base_site_packages.resolve(strict=True)
    overlay_site_packages = overlay_site_packages.resolve(strict=True)
    base = _distributions([base_site_packages])
    overlay = _distributions([overlay_site_packages])
    overlap = set(base) & set(overlay)
    if overlap:
        raise ValueError(f"duplicate distribution across layers: {sorted(overlap)}")
    selected_names = [canonicalize_name(name) for name in selected]
    if set(overlay) != set(selected_names):
        raise ValueError("overlay distribution set mismatch")
    combined = {**base, **overlay}
    requirements: list[dict[str, Any]] = []
    errors: list[str] = []
    for name in selected_names:
        distribution = overlay[name]
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
                continue
            required_name = canonicalize_name(requirement.name)
            installed = combined.get(required_name)
            installed_version = installed.version if installed is not None else None
            satisfied = installed is not None and (not requirement.specifier or installed_version in requirement.specifier)
            requirements.append(
                {
                    "package": name,
                    "requirement": str(requirement),
                    "resolved_name": required_name,
                    "resolved_version": installed_version,
                    "satisfied": satisfied,
                }
            )
            if not satisfied:
                errors.append(f"{name}: unsatisfied {requirement}")
    return {
        "schema_version": "wave64.layered_python_environment_validation.v1",
        "base_site_packages": str(base_site_packages),
        "overlay_site_packages": str(overlay_site_packages),
        "base_distribution_count": len(base),
        "overlay_distributions": [{"name": name, "version": overlay[name].version} for name in selected_names],
        "requirements": requirements,
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
        "authority": {"metadata_dependency_closure": not errors, "package_import": False, "model_load": False, "gpu_use": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-site-packages", type=Path, required=True)
    parser.add_argument("--overlay-site-packages", type=Path, required=True)
    parser.add_argument("--selected", action="append", required=True)
    args = parser.parse_args()
    result = validate_layer(args.base_site_packages, args.overlay_site_packages, args.selected)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
