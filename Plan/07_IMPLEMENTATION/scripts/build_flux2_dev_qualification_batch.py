#!/usr/bin/env python3
"""Build a five-unit FLUX.2 Dev qualification batch without executing it."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
LANE = "flux2_dev_primary_base"
T2I = Path("Workflows/base_generation/flux2_dev_primary_base/text_to_image.api.json")
EDIT = Path("Workflows/base_generation/flux2_dev_primary_base/single_reference_edit.api.json")
COMPLETED_SEEDS = {7261601, 7261602}
CASES = (
    ("adult_woman_portrait_seed7261701", "t2i", 7261701, 768, 1024, "hyperreal full-body editorial photograph of one adult woman with natural body proportions standing in a bright ceramics studio, relaxed contrapposto pose, visible hands and feet, detailed eyes and hair, realistic skin microtexture, indigo work jacket and charcoal trousers, clay tools and glazed vessels, coherent contact shadows and reflections, 50mm lens, crisp focus"),
    ("adult_man_landscape_seed7261702", "t2i", 7261702, 1024, 768, "hyperreal environmental portrait of one adult man seated at a steel fabrication bench, three-quarter body visible, natural anatomy and hands, short textured hair, realistic skin and fabric, olive overshirt and dark denim, brushed metal tools and safety glass, physically coherent workshop lighting and reflections, 35mm lens, crisp focus"),
    ("two_adults_wide_seed7261703", "t2i", 7261703, 1216, 832, "hyperreal wide editorial photograph of two distinct adult subjects, one woman and one man, collaborating across a walnut design table in a daylight architecture studio, both faces and hands clearly visible, distinct identity and wardrobe, natural anatomy, unambiguous object ownership, realistic skin hair fabric paper glass and wood, coherent contact shadows, 35mm lens, balanced composition"),
    ("adult_woman_portrait_seed7261704", "t2i", 7261704, 768, 1024, "hyperreal full-body editorial photograph of one adult woman with natural body proportions standing in a bright ceramics studio, relaxed contrapposto pose, visible hands and feet, detailed eyes and hair, realistic skin microtexture, indigo work jacket and charcoal trousers, clay tools and glazed vessels, coherent contact shadows and reflections, 50mm lens, crisp focus"),
    ("reference_environment_edit_seed7261705", "edit", 7261705, 1024, 1024, "Preserve the subject identity, anatomy, pose, camera, clothing, tools, glass objects, lighting direction, texture, and composition. Change only the weathered walnut workbench surface to pale honed Carrara marble with subtle gray veining and physically coherent reflections."),
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build(root: Path, out_dir: Path) -> dict[str, Any]:
    t2i, edit = load(root / T2I), load(root / EDIT)
    source_hashes = {T2I.as_posix(): digest(root / T2I), EDIT.as_posix(): digest(root / EDIT)}
    units: list[dict[str, Any]] = []
    for case_id, kind, seed, width, height, prompt in CASES:
        if seed in COMPLETED_SEEDS:
            raise ValueError("completed_seed_reuse_forbidden")
        graph = copy.deepcopy(t2i if kind == "t2i" else edit)
        if kind == "t2i":
            graph["4"]["inputs"]["text"] = prompt
            graph["7"]["inputs"].update({"width": width, "height": height})
            graph["8"]["inputs"]["noise_seed"] = seed
            graph["9"]["inputs"].update({"width": width, "height": height})
            graph["13"]["inputs"]["filename_prefix"] = f"flux2_dev_qualification/{case_id}"
        else:
            graph["7"]["inputs"]["text"] = prompt
            graph["12"]["inputs"]["noise_seed"] = seed
            graph["18"]["inputs"]["filename_prefix"] = f"flux2_dev_qualification/{case_id}"
        unit_dir = out_dir / case_id
        request_path = unit_dir / "prompt_request.json"
        write(request_path, {"client_id": f"flux2-qualification-{case_id}", "prompt": graph})
        request_hash = digest(request_path)
        manifest_path = unit_dir / "RUN_PACKAGE_MANIFEST.json"
        manifest = {
            "schema_version": "1.0", "run_id": case_id, "lane_id": LANE, "result": "pass_local_only",
            "local_only": True, "aws_contacted": False, "ec2_started": False, "generation_executed": False,
            "requires_gold_masks": False, "capability": "text_to_image" if kind == "t2i" else "single_reference_edit",
            "qualification_dimensions": {"subject_scope": "two_adults" if "two_adults" in case_id else ("adult_woman" if "woman" in case_id else ("adult_man" if "man" in case_id else "reference_edit")), "seed": seed, "width": width, "height": height, "edit_intent": "environment_material" if kind == "edit" else None},
            "generated_files": [{"path": project_relative(root, request_path), "sha256": request_hash, "purpose": "Bounded FLUX.2 qualification prompt request."}],
            "prompt_request": {"client_id": f"flux2-qualification-{case_id}", "node_count": len(graph), "sha256": request_hash},
            "source_workflow": {"path": (T2I if kind == "t2i" else EDIT).as_posix(), "sha256": source_hashes[(T2I if kind == "t2i" else EDIT).as_posix()]},
        }
        write(manifest_path, manifest)
        units.append({"case_id": case_id, "manifest_path": project_relative(root, manifest_path), "manifest_sha256": digest(manifest_path), "prompt_sha256": request_hash})
    index = {"schema_version": "1.0", "batch_id": "flux2_dev_broader_qualification_r001", "lane_id": LANE, "result": "pass_local_only", "execution_allowed": False, "unit_count": len(units), "source_workflows": source_hashes, "completed_seeds_excluded": sorted(COMPLETED_SEEDS), "coverage": {"subject_scopes": ["adult_woman", "adult_man", "two_adults", "reference_edit"], "resolutions": [[768, 1024], [1024, 768], [1216, 832], [1024, 1024]], "edit_intents": ["environment_material"], "repeated_prompt_distinct_seed": True}, "units": units}
    write(out_dir / "QUALIFICATION_BATCH_INDEX.json", index)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=ROOT); parser.add_argument("--out-dir", type=Path, default=Path("runtime_artifacts/flux2_dev_qualification_batch_r001")); args = parser.parse_args()
    root = args.root.resolve(); out = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    print(json.dumps(build(root, out), indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
