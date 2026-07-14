#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/reconcile_wave64_row062_legacy_observability_metadata.py"
SPEC = importlib.util.spec_from_file_location("row062_reconcile", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload, encoding="utf-8")


class Row062ReconciliationTests(unittest.TestCase):
    def build(self, root: Path) -> dict[str, Path]:
        prior_path = root / "prior.json"
        policy_path = root / "policy.md"
        lookup_path = root / "lookup.json"
        prior_records = [
            {"run_id": Path(name).stem, "log_retention": "missing", "command_ids": [], "failures": ["missing_log_path_or_absent_reason"], "verdict": "fail"}
            for name in MODULE.RECORDS
        ] + [{"run_id": f"smoke-{index}", "log_retention": "present", "command_ids": [f"command-{index}"], "failures": [], "verdict": "pass"} for index in range(6)]
        write(prior_path, {"tracker_id": MODULE.TRK, "item_id": MODULE.ITEM, "row_complete": False, "retention_policy_path": "policy.md", "aggregate": {"records": 10, "parseable": 10}, "records": prior_records, "normalized_blockers": [{"blocker_id": "LEGACY_RUN_RECORD_LOG_RETENTION_METADATA_MISSING", "count": 4}, {"blocker_id": "LEGACY_RUN_RECORD_COMMAND_ID_MISSING", "count": 1}]})
        write(policy_path, "log_absent_reason must not rewrite must not invent at least 30 days credentials, tokens, signed URLs, or secret values")
        record_dir = root / "Plan/Instructions/Operations/Run_Records"
        for index, name in enumerate(MODULE.RECORDS):
            run_id = Path(name).stem
            commands = [{"name": "work", "status": "pass"}]
            if run_id != MODULE.INVENTORY_RUN:
                commands[0]["command_id"] = f"{index + 1:08x}-1111-4111-8111-111111111111"
            write(record_dir / name, {"run_id": run_id, "task_id": "EC2_RUNTIME_INVENTORY_20260706T020209-0500" if run_id == MODULE.INVENTORY_RUN else f"task-{index}", "start_time_local": "2026-07-06T02:02:09-05:00", "end_time_local": "2026-07-06T02:10:57-05:00", "commands_run": commands})
        write(lookup_path, {"tracker_id": MODULE.TRK, "item_id": MODULE.ITEM, "operation": "read_only_ssm_command_history_lookup", "result": "pass_exact_historical_inventory_command_recovered", "aws_identity_arn": "arn:aws:sts::1:assumed-role/ComfyUIMainSessionRole/comfy-ui-main-session", "matched_commands": [{"command_id": MODULE.COMMAND_ID, "requested_datetime": "2026-07-06T02:05:43.624000-05:00", "status": "Success", "comment": "ComfyUI bounded runtime inventory", "document_name": "AWS-RunShellScript", "instance_ids": ["i-0560bf8d143f93bb1"]}], "instance_state_verification": {"instance_id": "i-0560bf8d143f93bb1", "state": "stopped"}, "boundaries": {"aws_contacted": True, "read_only_queries_only": True, "ec2_started_or_stopped": False, "ssm_command_sent": False, "s3_mutated": False, "generation_executed": False, "jira_mutated": False, "mask_or_wave71_touched": False}})
        return {"prior": prior_path, "policy": policy_path, "lookup": lookup_path}

    def evaluate(self, root: Path, sources: dict[str, Path]):
        return MODULE.build(root, sources, "2026-07-14T12:21:01-05:00")

    def mutate(self, path: Path, callback) -> None:
        payload = json.loads(path.read_text())
        callback(payload)
        write(path, payload)

    def test_happy_path_closes_row_and_preserves_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sidecar, evidence = self.evaluate(root, self.build(root))
            self.assertTrue(evidence["row_complete"])
            self.assertEqual(evidence["aggregate"]["command_ids_missing"], 0)
            self.assertEqual(sidecar["explicit_log_absence_count"], 4)
            self.assertFalse(sidecar["historical_records_modified"])
            self.assertEqual(len(evidence["records"]), 10)
            self.assertTrue(evidence["canonical_schema_continuity"]["per_record_index_preserved"])

    def test_rejects_wrong_command_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            self.mutate(sources["lookup"], lambda value: value["matched_commands"][0].update({"command_id": "0" * 36}))
            with self.assertRaisesRegex(ValueError, "command ID invalid"):
                self.evaluate(root, sources)

    def test_rejects_command_outside_run_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            self.mutate(sources["lookup"], lambda value: value["matched_commands"][0].update({"requested_datetime": "2026-07-06T03:00:00-05:00"}))
            with self.assertRaisesRegex(ValueError, "outside run window"):
                self.evaluate(root, sources)

    def test_rejects_multiple_ssm_history_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            self.mutate(sources["lookup"], lambda value: value["matched_commands"].append(dict(value["matched_commands"][0])))
            with self.assertRaisesRegex(ValueError, "exactly one command"):
                self.evaluate(root, sources)

    def test_rejects_second_legacy_command_id_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            path = root / "Plan/Instructions/Operations/Run_Records" / MODULE.RECORDS[0]
            self.mutate(path, lambda value: value["commands_run"][0].pop("command_id"))
            with self.assertRaisesRegex(ValueError, "non-inventory legacy command ID missing"):
                self.evaluate(root, sources)

    def test_rejects_running_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            self.mutate(sources["lookup"], lambda value: value["instance_state_verification"].update({"state": "running"}))
            with self.assertRaisesRegex(ValueError, "not verified stopped"):
                self.evaluate(root, sources)

    def test_rejects_mutating_lookup_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            self.mutate(sources["lookup"], lambda value: value["boundaries"].update({"ssm_command_sent": True}))
            with self.assertRaisesRegex(ValueError, "mutation boundary violated"):
                self.evaluate(root, sources)

    def test_rejects_existing_untracked_log_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            path = root / "Plan/Instructions/Operations/Run_Records" / MODULE.RECORDS[0]
            self.mutate(path, lambda value: value.update({"log_path": "unknown.log"}))
            with self.assertRaisesRegex(ValueError, "already has log metadata"):
                self.evaluate(root, sources)

    def test_rejects_prior_gap_count_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.build(root)
            self.mutate(sources["prior"], lambda value: value["normalized_blockers"][0].update({"count": 3}))
            with self.assertRaisesRegex(ValueError, "four-log gap"):
                self.evaluate(root, sources)

    def test_ledger_note_append_is_idempotent(self) -> None:
        once = MODULE.append_unique("existing", MODULE.LEDGER_NOTE)
        self.assertEqual(MODULE.append_unique(once, MODULE.LEDGER_NOTE), once)


if __name__ == "__main__":
    unittest.main()
