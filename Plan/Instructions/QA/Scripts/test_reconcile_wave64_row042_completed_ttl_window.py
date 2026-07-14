#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/reconcile_wave64_row042_completed_ttl_window.py"
SPEC = importlib.util.spec_from_file_location("row042_completed", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class Row042CompletedWindowTests(unittest.TestCase):
    def build(self, root: Path) -> dict[str, Path]:
        window = "rw-row042-test-window"
        instance = "i-test"
        region = "us-east-1"
        schedule_path = root / "schedule.json"
        watchdog_path = root / "watchdog.json"
        runtime_path = root / "runtime.json"
        cleanup_path = root / "cleanup.json"
        visual_path = root / "visual.json"
        schedule = {
            "runtime_window_id": window, "tracker_id": MODULE.TRK, "item_id": MODULE.ITEM,
            "instance_id": instance, "region": region, "stop_after_minutes": 45,
            "operation": "new_ec2_emergency_stop_schedule", "execute": True, "aws_contacted": True,
            "schedule_name": "stop-test", "schedule_verified": True, "schedule_state": "ENABLED",
            "action_after_completion": "DELETE", "result": "emergency_stop_schedule_created_and_verified", "errors": [],
        }
        watchdog = {
            "runtime_window_id": window, "tracker_id": MODULE.TRK, "item_id": MODULE.ITEM,
            "instance_id": instance, "region": region, "stop_after_minutes": 45,
            "operation": "start_ec2_instance_stop_watchdog", "execute": True, "aws_contacted": True,
            "command_status": "Success", "stop_capability_verified": True, "command_id": "cmd", "watchdog_pid": "42",
            "result": "instance_stop_watchdog_started_and_capability_verified", "errors": [],
        }
        runtime = {
            "runtime_window_id": window, "instance_id": instance, "region": region, "max_ec2_runtime_minutes": 45,
            "mode": "execute", "result": "workflow_smoke_generation_complete", "execute_gates_pass": True,
            "blocked_reasons": [], "generation_executed": True, "ec2_started": True, "command_status": "Success",
            "stop_exit_code": 0, "final_state": "stopped", "stop_failure_category": None, "errors": [],
            "emergency_stop_gate": {"status": "pass", "path": str(schedule_path)},
            "instance_watchdog": {"status": "pass", "path": str(watchdog_path)},
        }
        cleanup = {
            "runtime_window_id": window, "instance_id": instance, "region": region, "schedule_name": "stop-test",
            "instance_state_query_exit_code": 0, "instance_final_state": "stopped", "schedule_delete_exit_code": 0,
            "schedule_absence_verified": True, "result": "runtime_cleanup_verified", "failure_category": None,
        }
        visual = {
            "result": "pass_runtime_smoke_visual_qa", "instance_final_state_independently_verified": "stopped",
            "runtime_evidence": runtime_path.relative_to(root).as_posix(),
            "integrity_boundary": {"runtime_generation_complete": True},
            "scope_boundary": ["This does not evaluate or promote body masks.", "This does not activate Wave71+."],
        }
        for path, payload in ((schedule_path, schedule), (watchdog_path, watchdog), (runtime_path, runtime), (cleanup_path, cleanup), (visual_path, visual)):
            write(path, payload)
        return {"schedule": schedule_path, "watchdog": watchdog_path, "runtime": runtime_path, "cleanup": cleanup_path, "visual_qa": visual_path}

    def evidence(self, root: Path, paths: dict[str, Path]) -> dict[str, object]:
        return MODULE.build_evidence(root, paths, "2026-07-14T12:00:00-05:00")

    def test_accepts_one_complete_existing_window_without_external_action(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary)
            evidence = self.evidence(root, self.build(root))
        self.assertTrue(evidence["row_complete"])
        self.assertEqual(evidence["status"], MODULE.STATUS)
        self.assertEqual(evidence["check_summary"], {"checked": 13, "passed": 13, "failed": 0})
        boundary = evidence["reconciliation_execution_boundary"]
        self.assertFalse(boundary["independent_runtime_telemetry"])
        self.assertFalse(boundary["declared_actions"]["aws_contacted"])
        self.assertFalse(evidence["claim_boundary"]["body_mask_or_geometry_authority"])

    def test_rejects_runtime_window_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["watchdog"].read_text()); payload["runtime_window_id"] = "other-window"; write(paths["watchdog"], payload)
            with self.assertRaisesRegex(ValueError, "runtime window mismatch"):
                self.evidence(root, paths)

    def test_rejects_unverified_schedule_or_watchdog(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["schedule"].read_text()); payload["schedule_state"] = "DISABLED"; write(paths["schedule"], payload)
            with self.assertRaisesRegex(ValueError, "schedule not verified enabled"):
                self.evidence(root, paths)
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["watchdog"].read_text()); payload["stop_capability_verified"] = False; write(paths["watchdog"], payload)
            with self.assertRaisesRegex(ValueError, "stop capability"):
                self.evidence(root, paths)

    def test_rejects_ttl_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["runtime"].read_text()); payload["max_ec2_runtime_minutes"] = 60; write(paths["runtime"], payload)
            with self.assertRaisesRegex(ValueError, "runtime TTL mismatch"):
                self.evidence(root, paths)

    def test_rejects_missing_runtime_or_cleanup_stop(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["runtime"].read_text()); payload["final_state"] = "running"; write(paths["runtime"], payload)
            with self.assertRaisesRegex(ValueError, "runtime final stop failed"):
                self.evidence(root, paths)
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["cleanup"].read_text()); payload["schedule_absence_verified"] = False; write(paths["cleanup"], payload)
            with self.assertRaisesRegex(ValueError, "schedule absence"):
                self.evidence(root, paths)

    def test_rejects_visual_qa_without_independent_stop_or_mask_boundary(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["visual_qa"].read_text()); payload["instance_final_state_independently_verified"] = "unknown"; write(paths["visual_qa"], payload)
            with self.assertRaisesRegex(ValueError, "independent stopped proof"):
                self.evidence(root, paths)
        with tempfile.TemporaryDirectory(dir=ROOT / "runtime_artifacts") as temporary:
            root = Path(temporary); paths = self.build(root)
            payload = json.loads(paths["visual_qa"].read_text()); payload["scope_boundary"] = ["This does not activate Wave71+."]; write(paths["visual_qa"], payload)
            with self.assertRaisesRegex(ValueError, "mask boundary"):
                self.evidence(root, paths)

    @unittest.skipUnless(all((ROOT / path).is_file() for path in MODULE.DEFAULT_SOURCES.values()), "local Row042 source chain unavailable")
    def test_current_local_row042_chain_passes(self) -> None:
        paths = {name: ROOT / path for name, path in MODULE.DEFAULT_SOURCES.items()}
        evidence = MODULE.build_evidence(ROOT, paths, "2026-07-14T12:00:00-05:00")
        self.assertTrue(evidence["row_complete"])


if __name__ == "__main__":
    unittest.main()
