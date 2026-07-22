from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = (
    ROOT
    / "Plan/Tracker/Evidence/W64_AQA_GOOGLE_DRIVE_ARCHIVE_RECONCILIATION_20260722.json"
)


def load_evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_inventory_reconciliation_is_exact_and_unique() -> None:
    evidence = load_evidence()
    inventory = evidence["payload_inventory"]
    accepted = evidence["accepted_archive_integrity"]
    assert inventory["rows_read"] == accepted["payload_files"] == 335
    assert inventory["payload_bytes_recomputed"] == accepted["payload_bytes"] == 395510389604
    assert inventory["invalid_size_rows"] == 0
    assert inventory["invalid_sha256_rows"] == 0
    assert inventory["duplicate_paths"] == 0
    assert inventory["duplicate_drive_object_ids"] == 0


def test_top_level_archive_totals_reconcile() -> None:
    accepted = load_evidence()["accepted_archive_integrity"]
    assert (
        accepted["local_archive"]["files"]
        + accepted["s3_nonmodel_archive"]["files"]
        + accepted["ec2_archive"]["drive_files"]
        == accepted["payload_files"]
    )
    assert (
        accepted["local_archive"]["bytes"]
        + accepted["s3_nonmodel_archive"]["archive_bytes"]
        + accepted["ec2_archive"]["drive_bytes"]
        == accepted["payload_bytes"]
    )


def test_ec2_and_cleanup_holds_fail_closed() -> None:
    evidence = load_evidence()
    ec2 = evidence["accepted_archive_integrity"]["ec2_archive"]
    cleanup = evidence["stale_docker_vhd_cleanup"]
    assert ec2["state"] == "PARTIAL_RETAINED"
    assert ec2["audited_large_files_remaining"] == 411
    assert ec2["delete_on_termination"]
    assert not ec2["termination_authorized"]
    assert cleanup["local_sha256_recomputed_equal"]
    assert cleanup["deletion_result"] == "BLOCKED_BY_EXECUTION_POLICY_BEFORE_PROCESS_START"
    assert cleanup["source_still_present"]
    assert cleanup["recovery_copy_retained"]


def test_archive_grants_no_runtime_or_product_authority() -> None:
    authority = load_evidence()["authority"]
    assert authority["accessible_local_archive_integrity_accepted"]
    assert authority["accessible_s3_nonmodel_archive_integrity_accepted"]
    assert not authority["ec2_archive_complete"]
    assert not authority["model_runtime_qualified_by_archive"]
    assert not authority["workflow_qualified_by_archive"]
    assert not authority["visual_audio_video_quality_qualified_by_archive"]
    assert not authority["product_promotion_by_archive"]
    assert not authority["source_cleanup_complete"]
    assert not authority["recurring_tasks_enabled"]
