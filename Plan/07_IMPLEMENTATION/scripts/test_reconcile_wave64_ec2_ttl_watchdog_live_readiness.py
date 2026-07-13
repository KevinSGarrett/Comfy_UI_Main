from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import patch

from reconcile_wave64_ec2_ttl_watchdog_live_readiness import (
    STATUS_BLOCKED_AUTH,
    STATUS_BLOCKED_MISSING_PROOF,
    STATUS_BLOCKED_ROLE,
    STATUS_BLOCKED_RUNNING,
    STATUS_COMPLETED,
    build_evidence,
    classify_readiness,
    parse_env_scheduler_role,
    redact_text,
    run_aws,
)


class ClassifyReadinessTests(unittest.TestCase):
    def call_classify_readiness(self, **kwargs: object) -> dict[str, object]:
        defaults = {
            "auth_verified": True,
            "role_verified": True,
            "instance_state": "stopped",
            "schedule_present": True,
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

    def test_stopped_missing_schedule_and_ssm_is_blocked_missing_proof(self) -> None:
        result = self.call_classify_readiness(
            schedule_present=False,
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
            ssm_managed=False,
            watchdog_proof_present=False,
        )
        self.assertFalse(result["row042_complete"])
        self.assertEqual(result["status"], STATUS_BLOCKED_RUNNING)
        self.assertIn("running_instance_without_ttl_controls", result["blockers"])


class SafetyTests(unittest.TestCase):
    def test_blocked_evidence_builder_records_24_passing_reconciliation_checks(self) -> None:
        classification = classify_readiness(
            auth_verified=True,
            role_verified=True,
            instance_state="stopped",
            schedule_present=False,
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
                "ssm_describe_instance_information_ok": True,
                "ssm_managed": False,
                "watchdog_proof_present": False,
            },
            "classification": classification,
        }
        payload = build_evidence(probe, "2026-07-13T00:00:00-05:00", "20260713T000000-0500")
        self.assertFalse(payload["row_complete"])
        self.assertEqual(payload["status"], STATUS_BLOCKED_MISSING_PROOF)
        self.assertEqual(payload["check_summary"], {"checked": 24, "passed": 24, "failed": 0})
        check_names = {check["name"] for check in payload["checks"]}
        self.assertIn("live_schedule_state_consistent", check_names)
        self.assertIn("ssm_watchdog_state_consistent", check_names)
        self.assertIn("live_blockers_logically_consistent", check_names)
        self.assertNotIn("exact_live_blockers_recorded", check_names)
        rendered = json.dumps(payload)
        self.assertNotIn("i-0560bf8d143f93bb1", rendered)
        self.assertNotIn("029530099913", rendered)

    def test_project_scheduler_role_key_is_recognized_without_exposing_arn(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

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
