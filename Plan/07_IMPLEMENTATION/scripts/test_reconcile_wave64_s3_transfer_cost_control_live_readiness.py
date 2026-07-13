from __future__ import annotations

import unittest
import subprocess
import json
from unittest.mock import patch

from reconcile_wave64_s3_transfer_cost_control_live_readiness import (
    PrefixProbe,
    build_evidence,
    classify_readiness,
    run_aws,
)


def make_probe(*, complete: bool = True) -> dict:
    return {
        "mode": "read_only_live_probe",
        "local_static_readiness": {"ready": True, "checks": {}},
        "config_shape": {"missing_required_keys": [], "deploy_uri_parse_ok": True},
        "aws_read_ops": {
            "sts_get_caller_identity_ok": complete,
            "head_bucket_ok_count": 1,
            "head_bucket_total_count": 1,
            "list_prefix_checks": [
                {"name": "model", "required_for_completion": True, "list_call_ok": True, "has_object": True},
                {"name": "deploy", "required_for_completion": True, "list_call_ok": True, "has_object": True},
                {"name": "render", "required_for_completion": True, "list_call_ok": True, "has_object": True},
                {"name": "manifest", "required_for_completion": False, "list_call_ok": True, "has_object": False},
            ],
            "head_object_flux_exists": False,
        },
        "classification": {
            "result": "pass" if complete else "blocked",
            "blockers": [] if complete else ["aws_authentication_failed"],
            "residuals": ["manifest_prefix_empty", "exact_flux_object_missing"],
        },
    }


def make_prefixes(
    *,
    model_ok: bool = True,
    deploy_ok: bool = True,
    render_ok: bool = True,
    manifest_ok: bool = True,
    model_access: bool = True,
    deploy_access: bool = True,
    render_access: bool = True,
    manifest_access: bool = True,
) -> list[PrefixProbe]:
    return [
        PrefixProbe("model", True, model_access, model_ok),
        PrefixProbe("deploy", True, deploy_access, deploy_ok),
        PrefixProbe("render", True, render_access, render_ok),
        PrefixProbe("manifest", False, manifest_access, manifest_ok),
    ]


class ClassifyReadinessTests(unittest.TestCase):
    def test_pass_when_all_required_conditions_met(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=True,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(),
            flux_exists=True,
        )
        self.assertTrue(result["row041_complete"])
        self.assertEqual(result["result"], "pass")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["residuals"], [])

    def test_missing_exact_flux_is_residual_and_still_passes(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=True,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(),
            flux_exists=False,
        )
        self.assertTrue(result["row041_complete"])
        self.assertEqual(result["blockers"], [])
        self.assertIn("exact_flux_object_missing", result["residuals"])

    def test_empty_manifest_is_residual_and_still_passes(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=True,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(manifest_ok=False),
            flux_exists=True,
        )
        self.assertTrue(result["row041_complete"])
        self.assertEqual(result["blockers"], [])
        self.assertIn("manifest_prefix_empty", result["residuals"])

    def test_auth_failure_blocks(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=False,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(),
            flux_exists=True,
        )
        self.assertFalse(result["row041_complete"])
        self.assertIn("aws_authentication_failed", result["blockers"])

    def test_bucket_failure_blocks(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=True,
            bucket_access_ok=False,
            prefix_probes=make_prefixes(),
            flux_exists=True,
        )
        self.assertFalse(result["row041_complete"])
        self.assertIn("bucket_access_failed", result["blockers"])

    def test_missing_required_prefix_blocks(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=True,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(render_ok=False),
            flux_exists=True,
        )
        self.assertFalse(result["row041_complete"])
        self.assertIn("required_prefix_empty:render", result["blockers"])

    def test_required_prefix_access_failure_blocks(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=True,
            aws_auth_ok=True,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(deploy_access=False),
            flux_exists=True,
        )
        self.assertFalse(result["row041_complete"])
        self.assertIn("required_prefix_access_failed:deploy", result["blockers"])

    def test_config_shape_failure_blocks(self) -> None:
        result = classify_readiness(
            local_static_ready=True,
            config_shape_ok=False,
            aws_auth_ok=True,
            bucket_access_ok=True,
            prefix_probes=make_prefixes(),
            flux_exists=True,
        )
        self.assertFalse(result["row041_complete"])
        self.assertIn("config_shape_invalid", result["blockers"])

    def test_aws_timeout_fails_closed(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("aws", 30)):
            self.assertIsNone(run_aws(["sts", "get-caller-identity"]))

    def test_evidence_builder_passes_26_checks_without_sensitive_values(self) -> None:
        payload = build_evidence(make_probe(), "2026-07-12T23:59:00-05:00", "20260712T235900-0500")
        self.assertTrue(payload["row_complete"])
        self.assertEqual(payload["check_summary"], {"checked": 26, "passed": 26, "failed": 0})
        rendered = json.dumps(payload).lower()
        for forbidden in ("bucket-name", "s3://", "access_key", "secret_access", "029530099913"):
            self.assertNotIn(forbidden, rendered)

    def test_evidence_builder_fails_closed_when_probe_is_blocked(self) -> None:
        payload = build_evidence(make_probe(complete=False), "2026-07-12T23:59:00-05:00", "20260712T235900-0500")
        self.assertFalse(payload["row_complete"])
        self.assertGreater(payload["check_summary"]["failed"], 0)


if __name__ == "__main__":
    unittest.main()
