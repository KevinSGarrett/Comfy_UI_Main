from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "Plan"
VALIDATOR = PLAN / "07_IMPLEMENTATION/scripts/validate_physical_contact_graph_contract.py"
SCORER = PLAN / "07_IMPLEMENTATION/scripts/score_physical_contact_graph_evidence.py"
CONTRACT = PLAN / "09_EXAMPLES/wave22_physical_contact_graph.example.json"
EVIDENCE = PLAN / "09_EXAMPLES/wave22_contact_evidence.example.json"
CONTACT_EDGE_SCHEMA = PLAN / "08_SCHEMAS/contact_edge.schema.json"
CONTRACT_SCHEMA = PLAN / "08_SCHEMAS/physical_contact_graph.schema.json"
EVIDENCE_SCHEMA = PLAN / "08_SCHEMAS/contact_graph_evidence.schema.json"
CHECKS = (
    "source_target_ownership_pass",
    "pressure_intensity_pass",
    "occlusion_pass",
    "duration_pass",
    "audio_force_pass",
    "deformation_evidence_pass",
    "preservation_pass",
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR_MODULE = load_module(VALIDATOR, "wave22_contact_validator")
SCORER_MODULE = load_module(SCORER, "wave22_contact_scorer")


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class PhysicalContactGraphContractTests(unittest.TestCase):
    def contract(self) -> dict:
        return json.loads(CONTRACT.read_text(encoding="utf-8-sig"))

    def evidence(self) -> dict:
        return json.loads(EVIDENCE.read_text(encoding="utf-8-sig"))

    def validate(self, value: object) -> list[str]:
        errors, _ = VALIDATOR_MODULE.validate_contract(value)
        return errors

    def score(self, value: object) -> dict:
        return SCORER_MODULE.score_evidence(value)

    def test_example_contract_validates_in_cli(self):
        result = run(VALIDATOR, "--input", CONTRACT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "PASS")

    def test_example_contract_validates_against_schema(self):
        contract_schema = json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))
        edge_schema = json.loads(CONTACT_EDGE_SCHEMA.read_text(encoding="utf-8"))
        contract_schema["properties"]["contact_edges"]["items"] = edge_schema
        errors = list(Draft7Validator(contract_schema).iter_errors(self.contract()))
        self.assertEqual(errors, [])

    def test_required_root_and_exact_version_are_enforced(self):
        for field in ("contract_version", "contact_graph_id", "contact_edges"):
            with self.subTest(field=field):
                value = self.contract()
                del value[field]
                self.assertTrue(any(f"missing root field: {field}" in error for error in self.validate(value)))
        value = self.contract()
        value["contract_version"] = "wave22.v0"
        self.assertIn("contract_version must equal wave22.v1", self.validate(value))

    def test_root_and_edge_extensions_fail_closed(self):
        value = self.contract()
        value["unexpected"] = True
        self.assertIn("unexpected root field: unexpected", self.validate(value))
        value = self.contract()
        value["contact_edges"][0]["unexpected"] = True
        self.assertIn("contact_edges[0] unexpected field: unexpected", self.validate(value))

    def test_empty_and_non_string_identities_fail_closed(self):
        edge_fields = (
            "edge_id",
            "source_owner_id",
            "source_region_id",
            "target_owner_id",
            "target_region_id",
        )
        for field in edge_fields:
            for replacement in ("", "   ", None, 0, False, [], {}):
                with self.subTest(field=field, replacement=repr(replacement)):
                    value = self.contract()
                    value["contact_edges"][0][field] = replacement
                    self.assertTrue(
                        any(f"contact_edges[0].{field} must be a non-empty string" in error for error in self.validate(value))
                    )

    def test_registered_categorical_values_are_enforced(self):
        fields = (
            "contact_edge_type",
            "pressure",
            "intensity",
            "occlusion",
            "duration",
            "audio_force_class",
        )
        for field in fields:
            with self.subTest(field=field):
                value = self.contract()
                value["contact_edges"][0][field] = "not_registered"
                self.assertTrue(
                    any(f"contact_edges[0].{field} is not registered" in error for error in self.validate(value))
                )

    def test_duplicate_edge_ids_fail_closed(self):
        value = self.contract()
        value["contact_edges"].append(dict(value["contact_edges"][0]))
        self.assertIn("duplicate edge_id: edge_001", self.validate(value))

    def test_required_contact_boundary_masks_are_enforced(self):
        value = self.contract()
        del value["contact_edges"][0]["mask_ids"]
        self.assertIn(
            "contact_edges[0].mask_ids must be non-empty for contact_edge_type press",
            self.validate(value),
        )

    def test_mask_ids_must_be_non_empty_unique_strings(self):
        for masks in ([""], ["mask_a", "mask_a"], "mask_a", [1]):
            with self.subTest(masks=repr(masks)):
                value = self.contract()
                value["contact_edges"][0]["mask_ids"] = masks
                self.assertNotEqual(self.validate(value), [])

    def test_qa_goals_are_registered_non_empty_and_unique(self):
        for goals in ([], [""], ["unknown"], ["preservation_pass", "preservation_pass"], "preservation_pass"):
            with self.subTest(goals=repr(goals)):
                value = self.contract()
                value["qa_goals"] = goals
                self.assertNotEqual(self.validate(value), [])

    def test_exact_invalid_typed_edge_regression_is_rejected(self):
        value = {
            "contract_version": "wave22.v1",
            "contact_graph_id": "probe",
            "contact_edges": [
                {
                    "edge_id": None,
                    "source_owner_id": [],
                    "source_region_id": 0,
                    "target_owner_id": False,
                    "target_region_id": {},
                    "contact_edge_type": 123,
                    "pressure": "nonsense",
                    "intensity": None,
                    "occlusion": [],
                    "duration": -99,
                    "audio_force_class": {"bad": True},
                }
            ],
        }
        errors = self.validate(value)
        self.assertGreaterEqual(len(errors), 11)
        self.assertTrue(any("edge_id must be a non-empty string" in error for error in errors))
        self.assertTrue(any("duration must be a non-empty string" in error for error in errors))

    def test_cli_writes_structured_failure_report(self):
        value = self.contract()
        value["contact_edges"][0]["source_owner_id"] = ""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "contract.json"
            output = Path(tmp) / "report.json"
            source.write_text(json.dumps(value), encoding="utf-8")
            result = run(VALIDATOR, "--input", source, "--output", output)
            self.assertEqual(result.returncode, 1)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(report["passed"])
        self.assertEqual(report["classification"], "WAVE22_PHYSICAL_CONTACT_GRAPH_VALIDATION_FAIL")
        self.assertTrue(report["strict_types"])

    def test_malformed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            output = Path(tmp) / "report.json"
            source.write_text("{", encoding="utf-8")
            validation = run(VALIDATOR, "--input", source, "--output", output)
            self.assertEqual(validation.returncode, 1)
            self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["passed"])
            scoring = run(SCORER, "--input", source, "--output", output)
            self.assertEqual(scoring.returncode, 1)
            self.assertFalse(json.loads(output.read_text(encoding="utf-8"))["pass"])

    def test_all_exact_boolean_checks_pass(self):
        report = self.score(self.evidence())
        self.assertTrue(report["pass"])
        self.assertEqual(report["score"], 1.0)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["exact_boolean_truth_enforced"])

    def test_each_false_check_fails(self):
        for field in CHECKS:
            with self.subTest(field=field):
                value = self.evidence()
                value[field] = False
                report = self.score(value)
                self.assertFalse(report["pass"])
                self.assertLess(report["score"], 1.0)

    def test_each_authority_boolean_rejects_missing_and_lookalike_values(self):
        lookalikes = (None, "false", "true", 0, 1, [], {})
        for field in CHECKS:
            missing = self.evidence()
            del missing[field]
            with self.subTest(field=field, value="missing"):
                report = self.score(missing)
                self.assertFalse(report["pass"])
                self.assertTrue(any(field in error for error in report["errors"]))
            for replacement in lookalikes:
                with self.subTest(field=field, value=repr(replacement)):
                    value = self.evidence()
                    value[field] = replacement
                    report = self.score(value)
                    self.assertFalse(report["pass"])
                    self.assertIn(f"{field} must be an exact Boolean", report["errors"])

    def test_string_false_regression_fails_in_cli(self):
        value = {field: "false" for field in CHECKS}
        value["failure_flags"] = []
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "evidence.json"
            output = Path(tmp) / "score.json"
            source.write_text(json.dumps(value), encoding="utf-8")
            result = run(SCORER, "--input", source, "--output", output)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["pass"])
        self.assertEqual(report["score"], 0.0)
        self.assertEqual(len(report["errors"]), 7)

    def test_failure_flags_always_prevent_pass(self):
        for flag in ("wrong_owner", "diagnostic_unregistered_flag"):
            with self.subTest(flag=flag):
                value = self.evidence()
                value["failure_flags"] = [flag]
                report = self.score(value)
                self.assertFalse(report["pass"])
        hard = self.evidence()
        hard["failure_flags"] = ["wrong_owner"]
        self.assertEqual(self.score(hard)["hard_fail_flags"], ["wrong_owner"])

    def test_failure_flags_and_fields_are_strict(self):
        for flags in ("wrong_owner", [""], [1], ["wrong_owner", "wrong_owner"]):
            with self.subTest(flags=repr(flags)):
                value = self.evidence()
                value["failure_flags"] = flags
                self.assertFalse(self.score(value)["pass"])
        value = self.evidence()
        value["unexpected"] = True
        self.assertIn("unexpected evidence field: unexpected", self.score(value)["errors"])

    def test_evidence_schema_rejects_string_boolean_and_extra_fields(self):
        schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
        validator = Draft7Validator(schema)
        self.assertEqual(list(validator.iter_errors(self.evidence())), [])
        value = self.evidence()
        value["source_target_ownership_pass"] = "false"
        self.assertNotEqual(list(validator.iter_errors(value)), [])
        value = self.evidence()
        value["unexpected"] = True
        self.assertNotEqual(list(validator.iter_errors(value)), [])


if __name__ == "__main__":
    unittest.main()
