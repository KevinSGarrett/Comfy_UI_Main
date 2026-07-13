from __future__ import annotations

import json
import os
import subprocess
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from reconcile_wave64_ec2_ttl_watchdog_live_readiness import (
    STATUS_BLOCKED_AUTH,
    STATUS_BLOCKED_MISSING_PROOF,
    STATUS_BLOCKED_ROLE,
    STATUS_BLOCKED_RUNNING,
    STATUS_COMPLETED,
    Row042Metadata,
    build_evidence,
    classify_readiness,
    find_latest_execution_proof,
    pair_execution_proofs,
    parse_env_scheduler_role,
    redact_text,
    run_aws,
    run_live_probe,
)


class ClassifyReadinessTests(unittest.TestCase):
    def call_classify_readiness(self, **kwargs: object) -> dict[str, object]:
        defaults = {
            "auth_verified": True,
            "role_verified": True,
            "instance_state": "stopped",
            "schedule_present": False,
            "schedule_proof_present": True,
            "ssm_managed": True,
            "watchdog_proof_present": True,
        }
        defaults.update(kwargs)
        return classify_readiness(**defaults)

    def test_fully_proven_completion(self) -> None:
        result = self.call_classify_readiness()
        self.assertTrue(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_COMPLETED)
        self.assertEqual(result["blockers"], [])

    def test_completed_post_stop_allows_auto_deleted_schedule_and_offline_ssm(self) -> None:
        result = self.call_classify_readiness(
            schedule_present=False,
            schedule_proof_present=True,
            ssm_managed=False,
            watchdog_proof_present=True,
        )
        self.assertTrue(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_COMPLETED)

    def test_stopped_missing_schedule_and_ssm_is_blocked_missing_proof(self) -> None:
        result = self.call_classify_readiness(
            schedule_present=False,
            schedule_proof_present=False,
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        self.assertFalse(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_BLOCKED_MISSING_PROOF)
        self.assertIn("live_emergency_stop_schedule_missing", result["blockers"])
        self.assertIn("ssm_watchdog_proof_missing", result["blockers"])
        self.assertTrue(result["recommendations"])

    def test_auth_failure(self) -> None:
        result = self.call_classify_readiness(
            auth_verified=False,
            schedule_present=False,
            schedule_proof_present=False,
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        self.assertFalse(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_BLOCKED_AUTH)
        self.assertIn("aws_auth_not_verified", result["blockers"])

    def test_role_failure(self) -> None:
        result = self.call_classify_readiness(
            role_verified=False,
            schedule_present=False,
            schedule_proof_present=False,
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        self.assertFalse(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_BLOCKED_ROLE)
        self.assertIn("scheduler_role_not_verified", result["blockers"])

    def test_running_instance_without_controls(self) -> None:
        result = self.call_classify_readiness(
            instance_state="running",
            schedule_present=False,
            schedule_proof_present=True,
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        self.assertFalse(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_BLOCKED_RUNNING)
        self.assertIn("running_instance_without_ttl_controls", result["blockers"])


class ExecutionProofDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = Row042Metadata(
            region="us-east-1",
            instance_id="i-0123456789abcdef0",
            schedule_name="dry-run-name",
            stop_after_minutes=60,
            canonical_path=Path("canonical.json"),
            schedule_dry_run_path=Path("schedule.json"),
            watchdog_dry_run_path=Path("watchdog.json"),
        )

    def test_finds_only_verified_schedule_execution(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = {
                "operation": "new_ec2_emergency_stop_schedule",
                "result": "emergency_stop_schedule_created_and_verified",
                "execute": True,
                "aws_contacted": True,
                "instance_id": self.metadata.instance_id,
                "region": self.metadata.region,
                "stop_after_minutes": 60,
                "runtime_window_id": "row042-window-001",
                "tracker_id": "TRK-W64-042",
                "item_id": "ITEM-W64-042",
                "timestamp": "2026-07-13T09:00:00-05:00",
                "schedule_name": "live-stop",
                "schedule_verified": False,
            }
            (root / "invalid.json").write_text(json.dumps(invalid), encoding="utf-8")
            valid = {**invalid, "schedule_verified": True}
            (root / "valid.json").write_text(json.dumps(valid), encoding="utf-8")
            proof = find_latest_execution_proof(
                directory=root,
                operation="new_ec2_emergency_stop_schedule",
                accepted_results={"emergency_stop_schedule_created_and_verified"},
                metadata=self.metadata,
                now=datetime.fromisoformat("2026-07-13T09:15:00-05:00"),
            )
        self.assertIsNotNone(proof)
        self.assertEqual(proof["payload"]["schedule_name"], "live-stop")

    def test_rejects_watchdog_without_capability_or_pid(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "operation": "start_ec2_instance_stop_watchdog",
                "result": "instance_stop_watchdog_started_and_capability_verified",
                "execute": True,
                "aws_contacted": True,
                "instance_id": self.metadata.instance_id,
                "region": self.metadata.region,
                "stop_after_minutes": 60,
                "runtime_window_id": "row042-window-001",
                "tracker_id": "TRK-W64-042",
                "item_id": "ITEM-W64-042",
                "timestamp": "2026-07-13T09:05:00-05:00",
                "command_id": "command-id",
                "command_status": "Success",
                "watchdog_pid": None,
                "stop_capability_verified": False,
            }
            (root / "invalid.json").write_text(json.dumps(payload), encoding="utf-8")
            proof = find_latest_execution_proof(
                directory=root,
                operation="start_ec2_instance_stop_watchdog",
                accepted_results={"instance_stop_watchdog_started_and_capability_verified"},
                metadata=self.metadata,
                now=datetime.fromisoformat("2026-07-13T09:15:00-05:00"),
            )
        self.assertIsNone(proof)

    def test_rejects_cross_window_execution_proof_pair(self) -> None:
        schedule = {"payload": {"runtime_window_id": "row042-window-001"}, "execution_timestamp": datetime.fromisoformat("2026-07-13T09:00:00-05:00")}
        watchdog = {"payload": {"runtime_window_id": "row042-window-002"}, "execution_timestamp": datetime.fromisoformat("2026-07-13T09:05:00-05:00")}
        paired_schedule, paired_watchdog, window_id = pair_execution_proofs(schedule, watchdog)
        self.assertIsNone(paired_schedule)
        self.assertIsNone(paired_watchdog)
        self.assertIsNone(window_id)

    def test_accepts_exact_execution_proof_pair(self) -> None:
        schedule = {"payload": {"runtime_window_id": "row042-window-001"}, "execution_timestamp": datetime.fromisoformat("2026-07-13T09:00:00-05:00")}
        watchdog = {"payload": {"runtime_window_id": "row042-window-001"}, "execution_timestamp": datetime.fromisoformat("2026-07-13T09:05:00-05:00")}
        paired_schedule, paired_watchdog, window_id = pair_execution_proofs(schedule, watchdog)
        self.assertIs(paired_schedule, schedule)
        self.assertIs(paired_watchdog, watchdog)
        self.assertEqual(window_id, "row042-window-001")

    def test_rejects_same_id_proofs_outside_one_bounded_window(self) -> None:
        schedule = {"payload": {"runtime_window_id": "row042-window-001"}, "execution_timestamp": datetime.fromisoformat("2026-07-13T09:00:00-05:00")}
        watchdog = {"payload": {"runtime_window_id": "row042-window-001"}, "execution_timestamp": datetime.fromisoformat("2026-07-13T11:00:01-05:00")}
        self.assertEqual(pair_execution_proofs(schedule, watchdog), (None, None, None))

    def test_selection_uses_payload_timestamp_not_filesystem_mtime(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base = {
                "operation": "new_ec2_emergency_stop_schedule",
                "result": "emergency_stop_schedule_created_and_verified",
                "execute": True,
                "aws_contacted": True,
                "instance_id": self.metadata.instance_id,
                "region": self.metadata.region,
                "stop_after_minutes": 60,
                "runtime_window_id": "row042-window-001",
                "tracker_id": "TRK-W64-042",
                "item_id": "ITEM-W64-042",
                "schedule_verified": True,
            }
            older = root / "older.json"
            newer = root / "newer.json"
            older.write_text(json.dumps({**base, "timestamp": "2026-07-13T09:00:00-05:00", "schedule_name": "older"}), encoding="utf-8")
            newer.write_text(json.dumps({**base, "timestamp": "2026-07-13T09:10:00-05:00", "schedule_name": "newer"}), encoding="utf-8")
            os.utime(older, (newer.stat().st_atime + 100, newer.stat().st_mtime + 100))
            proof = find_latest_execution_proof(
                directory=root,
                operation="new_ec2_emergency_stop_schedule",
                accepted_results={"emergency_stop_schedule_created_and_verified"},
                metadata=self.metadata,
                now=datetime.fromisoformat("2026-07-13T09:15:00-05:00"),
            )
        self.assertIsNotNone(proof)
        self.assertEqual(proof["payload"]["schedule_name"], "newer")

    def test_rejects_execution_proof_older_than_current_window_bound(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "operation": "new_ec2_emergency_stop_schedule",
                "result": "emergency_stop_schedule_created_and_verified",
                "execute": True,
                "aws_contacted": True,
                "instance_id": self.metadata.instance_id,
                "region": self.metadata.region,
                "stop_after_minutes": 60,
                "runtime_window_id": "row042-window-001",
                "tracker_id": "TRK-W64-042",
                "item_id": "ITEM-W64-042",
                "timestamp": "2026-07-13T05:59:59-05:00",
                "schedule_name": "stale",
                "schedule_verified": True,
            }
            (root / "stale.json").write_text(json.dumps(payload), encoding="utf-8")
            proof = find_latest_execution_proof(
                directory=root,
                operation="new_ec2_emergency_stop_schedule",
                accepted_results={"emergency_stop_schedule_created_and_verified"},
                metadata=self.metadata,
                now=datetime.fromisoformat("2026-07-13T09:00:00-05:00"),
            )
        self.assertIsNone(proof)

    def test_rejects_execution_proof_for_another_tracker(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "operation": "new_ec2_emergency_stop_schedule",
                "result": "emergency_stop_schedule_created_and_verified",
                "execute": True,
                "aws_contacted": True,
                "instance_id": self.metadata.instance_id,
                "region": self.metadata.region,
                "stop_after_minutes": 60,
                "runtime_window_id": "row042-window-001",
                "tracker_id": "TRK-W66-999",
                "item_id": "ITEM-W66-999",
                "timestamp": "2026-07-13T09:00:00-05:00",
                "schedule_name": "wrong-tracker",
                "schedule_verified": True,
            }
            (root / "wrong_tracker.json").write_text(json.dumps(payload), encoding="utf-8")
            proof = find_latest_execution_proof(
                directory=root,
                operation="new_ec2_emergency_stop_schedule",
                accepted_results={"emergency_stop_schedule_created_and_verified"},
                metadata=self.metadata,
                now=datetime.fromisoformat("2026-07-13T09:15:00-05:00"),
            )
        self.assertIsNone(proof)


class LiveProbeTests(unittest.TestCase):
    def test_probe_uses_paired_live_schedule_and_requires_enabled_state(self) -> None:
        metadata = Row042Metadata(
            region="us-east-1",
            instance_id="i-0123456789abcdef0",
            schedule_name="dry-run-name",
            stop_after_minutes=60,
            canonical_path=Path("canonical.json"),
            schedule_dry_run_path=Path("schedule.json"),
            watchdog_dry_run_path=Path("watchdog.json"),
        )
        with TemporaryDirectory() as directory:
            root = Path(directory)
            common = {
                "execute": True,
                "aws_contacted": True,
                "instance_id": metadata.instance_id,
                "region": metadata.region,
                "stop_after_minutes": 60,
                "runtime_window_id": "row042-window-001",
                "tracker_id": "TRK-W64-042",
                "item_id": "ITEM-W64-042",
            }
            (root / "schedule.json").write_text(json.dumps({
                **common,
                "operation": "new_ec2_emergency_stop_schedule",
                "result": "emergency_stop_schedule_created_and_verified",
                "timestamp": datetime.now().astimezone().isoformat(),
                "schedule_name": "live-stop-name",
                "schedule_verified": True,
            }), encoding="utf-8")
            (root / "watchdog.json").write_text(json.dumps({
                **common,
                "operation": "start_ec2_instance_stop_watchdog",
                "result": "instance_stop_watchdog_started_and_capability_verified",
                "timestamp": datetime.now().astimezone().isoformat(),
                "command_id": "command-id",
                "command_status": "Success",
                "watchdog_pid": "4321",
                "stop_capability_verified": True,
            }), encoding="utf-8")

            def fake_aws(args: list[str]) -> dict[str, object]:
                if args[:2] == ["sts", "get-caller-identity"]:
                    return {"ok": True, "exit_code": 0, "payload": {}}
                if args[:2] == ["ec2", "describe-instances"]:
                    return {"ok": True, "exit_code": 0, "payload": {"Reservations": [{"Instances": [{"State": {"Name": "running"}}]}]}}
                if args[:2] == ["scheduler", "get-schedule"]:
                    self.assertIn("live-stop-name", args)
                    return {"ok": True, "exit_code": 0, "payload": {"State": "DISABLED"}}
                if args[:2] == ["ssm", "describe-instance-information"]:
                    return {"ok": True, "exit_code": 0, "payload": {"InstanceInformationList": [{}]}}
                if args[:2] == ["iam", "get-role"]:
                    return {"ok": True, "exit_code": 0, "payload": {}}
                raise AssertionError(f"unexpected AWS call: {args}")

            with (
                patch("reconcile_wave64_ec2_ttl_watchdog_live_readiness.RUNTIME_READINESS", root),
                patch("reconcile_wave64_ec2_ttl_watchdog_live_readiness.load_row042_metadata", return_value=metadata),
                patch("reconcile_wave64_ec2_ttl_watchdog_live_readiness.parse_env_scheduler_role", return_value={"env_file_present": True, "candidate_role_keys_present": ["COMFY_SCHEDULER_STOP_ROLE_ARN"], "role_arn_seen": True, "role_name": "role"}),
                patch("reconcile_wave64_ec2_ttl_watchdog_live_readiness.aws_call_json", side_effect=fake_aws),
            ):
                probe = run_live_probe()

        self.assertFalse(probe["aws_read_ops"]["schedule_present"])
        self.assertFalse(probe["aws_read_ops"]["scheduler_schedule_enabled"])
        self.assertEqual(probe["classification"]["status"], STATUS_BLOCKED_RUNNING)
        self.assertIn("running_instance_without_ttl_controls", probe["classification"]["blockers"])


class SafetyTests(unittest.TestCase):
    def test_blocked_evidence_builder_records_all_passing_reconciliation_checks(self) -> None:
        classification = classify_readiness(
            auth_verified=True,
            role_verified=True,
            instance_state="stopped",
            schedule_present=False,
            schedule_proof_present=False,
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        probe = {
            "mode": "read_only_live_probe",
            "aws_read_ops": {
                "sts_get_caller_identity_ok": True,
                "iam_get_role_ok": True,
                "ec2_describe_instances_ok": True,
                "instance_state": "stopped",
                "schedule_present": False,
                "schedule_proof_present": False,
                "ssm_describe_instance_information_ok": True,
                "ssm_managed": False,
                "watchdog_proof_present": False,
            },
            "classification": classification,
        }
        payload = build_evidence(probe, "2026-07-13T00:00:00-05:00", "20260713T000000-0500")
        self.assertFalse(payload["row_complete"])
        self.assertEqual(payload["status"], STATUS_BLOCKED_MISSING_PROOF)
        self.assertEqual(payload["check_summary"]["failed"], 0)
        self.assertGreaterEqual(payload["check_summary"]["checked"], 25)
        check_names = {check["name"] for check in payload["checks"]}
        self.assertIn("schedule_execution_proof_state_consistent", check_names)
        self.assertIn("running_instance_has_live_schedule", check_names)
        self.assertIn("ssm_watchdog_state_consistent", check_names)
        self.assertIn("live_blockers_logically_consistent", check_names)
        self.assertNotIn("exact_live_blockers_recorded", check_names)
        rendered = json.dumps(payload)
        self.assertNotIn("i-0560bf8d143f93bb1", rendered)
        self.assertNotIn("029530099913", rendered)

    def test_running_state_consistency_checks_defer_to_final_stopped_gate(self) -> None:
        classification = classify_readiness(
            auth_verified=True,
            role_verified=True,
            instance_state="running",
            schedule_present=False,
            schedule_proof_present=False,
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        probe = {
            "mode": "read_only_live_probe",
            "aws_read_ops": {
                "sts_get_caller_identity_ok": True,
                "iam_get_role_ok": True,
                "ec2_describe_instances_ok": True,
                "instance_state": "running",
                "schedule_present": False,
                "schedule_proof_present": False,
                "ssm_describe_instance_information_ok": True,
                "ssm_managed": False,
                "watchdog_proof_present": False,
            },
            "classification": classification,
        }
        payload = build_evidence(probe, "2026-07-13T00:00:00-05:00", "20260713T000000-0500")
        checks = {check["name"]: check["result"] for check in payload["checks"]}
        self.assertEqual(checks["schedule_execution_proof_state_consistent"], "pass")
        self.assertEqual(checks["ssm_watchdog_state_consistent"], "pass")
        self.assertEqual(checks["final_instance_state_stopped"], "fail")

    def test_completed_evidence_accepts_auto_deleted_schedule_after_final_stop(self) -> None:
        classification = classify_readiness(
            auth_verified=True,
            role_verified=True,
            instance_state="stopped",
            schedule_present=False,
            schedule_proof_present=True,
            ssm_managed=False,
            watchdog_proof_present=True,
        )
        probe = {
            "mode": "read_only_live_probe",
            "execution_proof": {
                "paired_runtime_window_id": "row042-window-001",
                "latest_candidates_pair": True,
            },
            "aws_read_ops": {
                "sts_get_caller_identity_ok": True,
                "iam_get_role_ok": True,
                "ec2_describe_instances_ok": True,
                "instance_state": "stopped",
                "schedule_present": False,
                "schedule_proof_present": True,
                "ssm_describe_instance_information_ok": True,
                "ssm_managed": False,
                "watchdog_proof_present": True,
            },
            "classification": classification,
        }
        payload = build_evidence(probe, "2026-07-13T00:00:00-05:00", "20260713T000000-0500")
        self.assertTrue(payload["row_complete"])
        self.assertEqual(payload["status"], STATUS_COMPLETED)
        self.assertEqual(payload["check_summary"]["failed"], 0)
        self.assertTrue(all(check["result"] == "pass" for check in payload["checks"]))

    def test_project_scheduler_role_key_is_recognized_without_exposing_arn(self) -> None:
        with TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "COMFY_SCHEDULER_STOP_ROLE_ARN=arn:aws:iam::123456789012:role/TestStopRole\n",
                encoding="utf-8",
            )
            parsed = parse_env_scheduler_role(env_path)
        self.assertTrue(parsed["role_arn_seen"])
        self.assertEqual(parsed["role_name"], "TestStopRole")
        self.assertNotIn("123456789012", json.dumps(parsed))

    def test_redaction_hides_identifiers_and_arns(self) -> None:
        sample = (
            "instance i-0560bf8d143f93bb1 role arn:aws:iam::029530099913:role/ComfyUIEmergencyStopSchedulerRole "
            "account 029530099913"
        )
        redacted = redact_text(sample)
        self.assertNotIn("i-0560bf8d143f93bb1", redacted)
        self.assertNotIn("arn:aws:iam::029530099913:role/ComfyUIEmergencyStopSchedulerRole", redacted)
        self.assertNotIn("029530099913", redacted)
        rendered = json.dumps({"value": redacted})
        self.assertNotIn("i-0560bf8d143f93bb1", rendered)
        self.assertNotIn("arn:aws:iam", rendered)
        self.assertNotIn("029530099913", rendered)

    def test_run_aws_uses_30_second_timeout(self) -> None:
        completed = subprocess.CompletedProcess(args=["aws", "sts"], returncode=0, stdout="{}", stderr="")
        with patch("subprocess.run", return_value=completed) as mocked:
            _ = run_aws(["sts", "get-caller-identity"])
        _, kwargs = mocked.call_args
        self.assertEqual(kwargs.get("timeout"), 30)

    def test_run_aws_timeout_fails_closed(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("aws", 30)):
            self.assertIsNone(run_aws(["sts", "get-caller-identity"]))


if __name__ == "__main__":
    unittest.main()
