#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/reconcile_wave64_row064_prompt_lane_authority.py"
SPEC = importlib.util.spec_from_file_location("row064_lane_authority", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


LANES = {
    "sdxl_low_risk_fallback_lane": 1,
    "sdxl_realvisxl_base_lane": 15,
    "sdxl_realvisxl_controlnet_canny_lane": 26,
    "sdxl_realvisxl_controlnet_depth_lane": 6,
    "sdxl_realvisxl_controlnet_lineart_lane": 10,
    "sdxl_realvisxl_controlnet_normal_lane": 7,
    "sdxl_realvisxl_controlnet_openpose_lane": 10,
    "sdxl_realvisxl_inpaint_detail_lane": 34,
}


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload, encoding="utf-8")


class Row064LaneAuthorityTests(unittest.TestCase):
    def fixture(self, root: Path) -> dict[str, Path]:
        records = []
        runtime_remaining = 4
        index = 0
        for lane, count in LANES.items():
            for _ in range(count):
                path = root / f"PromptProfiles/profile_{index:03d}.json"
                write(path, {"profile_id": f"profile_{index:03d}"})
                linked = runtime_remaining > 0
                runtime_remaining -= int(linked)
                records.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "artifact_type": "prompt_profile", "profile_id": f"profile_{index:03d}", "target_lane_id": lane, "lane_authority_present": lane in {"sdxl_low_risk_fallback_lane", "sdxl_realvisxl_base_lane"}, "runtime_evidence_paths": ["runtime.json", "visual.json"] if linked else [], "approval_state": "blocked_pending_representative_runtime_output"})
                index += 1
        for kind in ("non_prompt_operation_profile", "non_prompt_operation_profile", "certification_matrix"):
            path = root / f"PromptProfiles/non_prompt_{index}.json"
            write(path, {"kind": kind})
            records.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "artifact_type": kind, "lane_authority_present": False, "runtime_evidence_paths": [], "approval_state": "not_applicable_non_prompt_artifact"})
            index += 1
        prior = root / "prior.json"
        write(prior, {"schema_version": "1.0", "evidence_id": "prior", "tracker_id": MODULE.TRK, "item_id": MODULE.ITEM, "row_complete": False, "inventory_summary": {"prompt_profiles": 109, "direct_runtime_evidence_links": 4}, "lane_counts": LANES, "profile_index": records, "normalized_blockers": [{"blocker_id": "PROMPT_TARGET_LANE_AUTHORITY_MISSING", "count": 93}, {"blocker_id": "REPRESENTATIVE_RUNTIME_OUTPUT_LINK_MISSING", "count": 105}, {"blocker_id": "WAVE71_PLUS_PROFILE_ACTIVATION_DEFERRED", "count": 14, "paths": ["deferred"]},], "check_summary": {"checked": 20, "passed": 20, "failed": 0}})
        portfolio = root / "portfolio.json"
        write(portfolio, {"authority": "authority.md", "lanes": [{"lane_id": lane, "modality": "image", "workflow_graph_complete": True, "classification": "required", "state": "bounded", "scope": "test"} for lane in LANES]})
        stages = root / "stages.json"
        write(stages, {"stages": [{"stage": "test_stage", "lane_ids": list(LANES)}]})
        protocol = root / "protocol.md"
        write(protocol, "representative test output aligns with intent, or pending runtime test is explicitly recorded")
        return {"prior": prior, "portfolio": portfolio, "stages": stages, "protocol": protocol}

    def evaluate(self, root: Path, sources: dict[str, Path]):
        return MODULE.build(root, sources, "2026-07-14T12:45:00-05:00")

    def mutate(self, path: Path, callback) -> None:
        value = json.loads(path.read_text())
        callback(value)
        write(path, value)

    def add_exact_runtime_pair(self, root: Path, profile: str, *, runtime_result: str = "pass_local_run_package_generation_smoke") -> tuple[Path, Path]:
        runtime = root / "Plan/Instructions/QA/Evidence/Workflow_Runtime/exact_runtime.json"
        visual = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA/EXACT_PROFILE_VISUAL_QA.json"
        write(runtime, {"result": runtime_result})
        write(visual, {"result": "pass_with_notes_strict_visual_qa", "samples": [{"profile": profile, "runtime_evidence": runtime.relative_to(root).as_posix()}]})
        return runtime, visual

    def test_happy_path_maps_all_indexed_profiles_without_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry, evidence = self.evaluate(root, self.fixture(root))
            self.assertEqual(registry["summary"]["lane_authority_present"], 109)
            self.assertEqual(registry["summary"]["lane_authority_missing"], 0)
            self.assertEqual(registry["summary"]["approved_profiles"], 0)
            self.assertFalse(evidence["row_complete"])

    def test_additive_profile_is_inventoried_but_not_consumed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            write(root / "PromptProfiles/user_addition.json", {"draft": True})
            registry, evidence = self.evaluate(root, sources)
            self.assertEqual(registry["summary"]["additive_prompt_json_files_not_consumed"], 1)
            self.assertFalse(registry["additive_catalog_boundary"]["content_consumed_as_authority"])
            self.assertEqual(MODULE.blocker_map(evidence)["PROMPT_CATALOG_ADDITIONS_NOT_YET_INTAKE_VALIDATED"]["count"], 1)

    def test_rejects_indexed_profile_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            write(root / "PromptProfiles/profile_000.json", {"changed": True})
            with self.assertRaisesRegex(ValueError, "indexed profile hash drift"):
                self.evaluate(root, sources)

    def test_rejects_missing_portfolio_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["portfolio"], lambda value: value["lanes"].pop())
            with self.assertRaisesRegex(ValueError, "all eight prompt lanes"):
                self.evaluate(root, sources)

    def test_rejects_non_image_portfolio_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["portfolio"], lambda value: value["lanes"][0].update({"modality": "video"}))
            with self.assertRaisesRegex(ValueError, "not image modality"):
                self.evaluate(root, sources)

    def test_rejects_incomplete_workflow_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["portfolio"], lambda value: value["lanes"][0].update({"workflow_graph_complete": False}))
            with self.assertRaisesRegex(ValueError, "workflow graph is incomplete"):
                self.evaluate(root, sources)

    def test_rejects_missing_pipeline_stage_lane(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["stages"], lambda value: value["stages"][0]["lane_ids"].pop())
            with self.assertRaisesRegex(ValueError, "does not map all eight"):
                self.evaluate(root, sources)

    def test_rejects_prior_runtime_gap_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(sources["prior"], lambda value: value["normalized_blockers"][1].update({"count": 104}))
            with self.assertRaisesRegex(ValueError, "prior 105-runtime gap"):
                self.evaluate(root, sources)

    def test_preserves_four_runtime_links_and_wave71_deferral(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry, evidence = self.evaluate(root, self.fixture(root))
            self.assertEqual(registry["summary"]["exact_profile_runtime_bindings"], 4)
            blockers = MODULE.blocker_map(evidence)
            self.assertEqual(blockers["REPRESENTATIVE_RUNTIME_OUTPUT_LINK_MISSING"]["count"], 105)
            self.assertEqual(blockers["WAVE71_PLUS_PROFILE_ACTIVATION_DEFERRED"]["count"], 14)

    def test_adds_only_exact_hash_bound_runtime_visual_pair_without_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            profile = "PromptProfiles/profile_004.json"
            runtime, visual = self.add_exact_runtime_pair(root, profile)
            registry, evidence = self.evaluate(root, sources)
            record = next(item for item in evidence["profile_index"] if item.get("path") == profile)
            self.assertEqual(registry["summary"]["exact_profile_runtime_bindings"], 5)
            self.assertEqual(registry["summary"]["profile_runtime_bindings_pending"], 104)
            self.assertEqual(record["runtime_evidence_paths"], sorted([runtime.relative_to(root).as_posix(), visual.relative_to(root).as_posix()]))
            self.assertEqual(record["runtime_evidence_binding_basis"], "exact_profile_runtime_pair_in_structured_visual_qa")
            self.assertEqual(record["approval_state"], "blocked_pending_representative_runtime_output")
            self.assertFalse(record["runtime_evidence_bindings"][0]["profile_approval_inferred"])
            self.assertEqual(MODULE.blocker_map(evidence)["REPRESENTATIVE_RUNTIME_OUTPUT_LINK_MISSING"]["count"], 104)

    def test_does_not_link_missing_or_nonpassing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.add_exact_runtime_pair(root, "PromptProfiles/profile_004.json", runtime_result="blocked_missing_runtime")
            registry, _ = self.evaluate(root, sources)
            self.assertEqual(registry["summary"]["exact_profile_runtime_bindings"], 4)

    def test_does_not_link_wave71_deferred_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            self.mutate(
                sources["prior"],
                lambda value: value["profile_index"][4].update({"wave71_plus_named": True}),
            )
            self.add_exact_runtime_pair(root, "PromptProfiles/profile_004.json")
            registry, _ = self.evaluate(root, sources)
            self.assertEqual(registry["summary"]["exact_profile_runtime_bindings"], 4)

    def test_links_object_shaped_paths_with_structured_visual_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            profile = "PromptProfiles/profile_004.json"
            runtime = root / "Plan/Instructions/QA/Evidence/Workflow_Runtime/object_runtime.json"
            visual = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA/OBJECT_SHAPED_QA.json"
            write(runtime, {"result": "pass_local_run_package_generation_smoke"})
            write(
                visual,
                {
                    "result": "pass_with_notes",
                    "inputs": {
                        "profile": {"path": profile, "sha256": "profile-hash"},
                        "runtime_evidence": {
                            "path": runtime.relative_to(root).as_posix(),
                            "sha256": "runtime-hash",
                        },
                    },
                    "checks": {"visual_subject_readable": True},
                },
            )
            registry, evidence = self.evaluate(root, sources)
            record = next(item for item in evidence["profile_index"] if item.get("path") == profile)
            self.assertEqual(registry["summary"]["exact_profile_runtime_bindings"], 5)
            self.assertIn(visual.relative_to(root).as_posix(), record["runtime_evidence_paths"])

    def test_links_nested_sample_with_visual_result_without_visual_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.fixture(root)
            profile = "PromptProfiles/profile_004.json"
            runtime = root / "Plan/Instructions/QA/Evidence/Workflow_Runtime/nested_runtime.json"
            visual = root / "Plan/Instructions/QA/Evidence/Image_Artifact_QA/MULTISEED_ROBUSTNESS_QA.json"
            write(runtime, {"result": "complete_runtime_execution"})
            write(
                visual,
                {
                    "result": "pass_with_notes",
                    "samples": [
                        {
                            "profile": profile,
                            "runtime_evidence": runtime.relative_to(root).as_posix(),
                            "visual_result": "pass_with_notes_fullbody_scope",
                        }
                    ],
                },
            )
            registry, _ = self.evaluate(root, sources)
            self.assertEqual(registry["summary"]["exact_profile_runtime_bindings"], 5)

    def test_does_not_zip_ambiguous_parallel_profile_runtime_lists(self) -> None:
        payload = {
            "profiles": ["PromptProfiles/a.json", "PromptProfiles/b.json"],
            "runtime_evidence_paths": ["runtime-a.json", "runtime-b.json"],
            "visual_review": {},
        }
        self.assertEqual(MODULE.profile_runtime_pairs(payload), set())

    def test_does_not_zip_profiles_to_separate_technical_evidence(self) -> None:
        payload = {
            "prompt_profiles": ["PromptProfiles/a.json", "PromptProfiles/b.json"],
            "technical_evidence": [
                {"runtime_evidence": "runtime-a.json"},
                {"runtime_evidence": "runtime-b.json"},
            ],
            "visual_review": {},
        }
        self.assertEqual(MODULE.profile_runtime_pairs(payload), set())

    def test_coverage_replacement_removes_stale_gap_tag(self) -> None:
        value = MODULE.replace_coverage("covered; ninety_three_lane_authority_gaps", ["all_109_indexed_prompt_lanes_authoritative"])
        self.assertNotIn("ninety_three", value)
        self.assertIn("all_109", value)

    def test_ledger_note_normalization_is_idempotent(self) -> None:
        duplicated = f"existing; {MODULE.LEGACY_LEDGER_NOTE}; {MODULE.LEGACY_LEDGER_NOTE}"
        once = MODULE.normalize_ledger_note(duplicated)
        self.assertEqual(MODULE.normalize_ledger_note(once), once)
        self.assertEqual(once.count(MODULE.LEDGER_NOTE), 1)
        self.assertNotIn(MODULE.LEGACY_LEDGER_NOTE, once)


if __name__ == "__main__":
    unittest.main()
