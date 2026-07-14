#!/usr/bin/env python3
"""Reconcile Row025 against the approved read-only AWS runtime prefixes."""

from __future__ import annotations

import csv
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "Plan"
STAMP = "20260714T061622-0500"
TIMESTAMP = "2026-07-14T06:16:22-05:00"
STATUS = "Blocked_Audio_Production_Runtime_Proof_Missing"
BUCKET = "comfy-ui-main-runtime-029530099913-us-east-1"
PREFIXES = ("render-outputs/", "model-cache/", "deploy-bundles/")
AUDIO_EXTENSIONS = {".aac", ".aif", ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".opus", ".wav"}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | {".mp4", ".webm"}
CONTAINER_BOXES = {b"moov", b"trak", b"mdia", b"minf", b"stbl", b"edts", b"dinf", b"udta"}
EXPECTED_ROLE = "arn:aws:sts::029530099913:assumed-role/ComfyUIMainSessionRole/comfy-ui-main-session"
INSTANCE_ID = "i-0560bf8d143f93bb1"
NOTE = (
    "Wave64 Row025 AWS reconciliation 2026-07-14: approved read-only S3 prefixes contain zero "
    "standalone audio objects. Their only four media objects are the already pulled-back WAN MP4s; "
    "all four contain video handlers and no audio handlers. EC2 remained stopped and no runtime was rerun."
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def aws_json(*args: str) -> Any:
    command = ["aws", *args, "--output", "json"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"AWS read failed: {' '.join(command)}\n{result.stderr}")
    return json.loads(result.stdout)


def iter_boxes(data: bytes, start: int = 0, end: int | None = None):
    limit = len(data) if end is None else min(end, len(data))
    offset = start
    while offset + 8 <= limit:
        size = struct.unpack_from(">I", data, offset)[0]
        box_type = data[offset + 4 : offset + 8]
        header_end = offset + 8
        if size == 1:
            if offset + 16 > limit:
                return
            size = struct.unpack_from(">Q", data, offset + 8)[0]
            header_end = offset + 16
        elif size == 0:
            size = limit - offset
        if size < header_end - offset or offset + size > limit:
            return
        yield offset, offset + size, header_end, box_type
        offset += size


def mp4_handler_types(path: Path) -> set[str]:
    data = path.read_bytes()
    handlers: set[str] = set()

    def walk(start: int, end: int) -> None:
        for box_start, box_end, payload_start, box_type in iter_boxes(data, start, end):
            if box_type == b"hdlr" and payload_start + 12 <= box_end:
                handlers.add(data[payload_start + 8 : payload_start + 12].decode("ascii", errors="replace"))
            elif box_type in CONTAINER_BOXES:
                walk(payload_start, box_end)

    walk(0, len(data))
    return handlers


def list_prefix(prefix: str) -> list[dict[str, Any]]:
    payload = aws_json("s3api", "list-objects-v2", "--bucket", BUCKET, "--prefix", prefix)
    return list(payload.get("Contents") or [])


def find_local_media(key: str, pulled_back: Path) -> Path:
    name = Path(key).name
    run_ids = [part for part in key.split("/") if part.startswith("aws_gpu_workflow_smoke_")]
    matches = [path for path in pulled_back.rglob(name) if not run_ids or any(run_id in path.as_posix() for run_id in run_ids)]
    if len(matches) != 1:
        raise ValueError(f"Expected one pulled-back match for {key}, found {len(matches)}")
    return matches[0]


def update_csv(path: Path, id_field: str, row_id: str) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    matches = [row for row in rows if row.get(id_field) == row_id]
    if len(matches) != 1:
        raise ValueError(f"Expected one {row_id} row in {path}, found {len(matches)}")
    row = matches[0]
    row["Status"] = STATUS
    if "Status_Decision" in row:
        row["Status_Decision"] = STATUS
    if "Notes" in row and NOTE not in row["Notes"]:
        row["Notes"] = f"{row['Notes']} | {NOTE}".strip(" |")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepend_hydration(path: Path, evidence_path: str) -> None:
    marker = "## Wave64 Row025 AWS Audio Reconciliation"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    block = f"""{marker} - {TIMESTAMP}

`TRK-W64-025` / `ITEM-W64-025` remains `{STATUS}` after the bounded AWS reconciliation. The authenticated least-privilege project role queried only the configured `render-outputs/`, `model-cache/`, and `deploy-bundles/` prefixes. No standalone audio object exists. The only four media objects are the already pulled-back WAN MP4s; each local hash-bound counterpart contains a video handler and no audio handler. The approved EC2 instance remained stopped, and no generation or completed runtime proof was rerun.

The strict Wave30 pipeline, deterministic PCM mixer, 21-test suite, and synthetic structural proof remain valid. Production engine runtime, genuine playback review, BS.1770/true-peak authority, final audio certification, masks, Wave71+, and Jira remain unclaimed.

Next action: advance to `TRK-W64-026` / `ITEM-W64-026` using its existing fail-closed engine authority before selecting the next concrete non-duplicate audio implementation task.

Evidence: `{evidence_path}`.

"""
    path.write_text(block + current, encoding="utf-8")


def append_proof_log(path: Path, evidence_path: str) -> None:
    marker = "row025_aws_audio_inventory_reconciled_no_audio_handlers"
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    row = (
        f'{TIMESTAMP},64,TRK-W64-025,Reconciled approved S3 runtime prefixes and pulled-back media for genuine audio proof,'
        f'{evidence_path},3 prefixes; 0 standalone audio objects; 4 existing MP4s with video/no audio handler,'
        f'blocked,{evidence_path},Advance to TRK-W64-026 without rerunning completed media; {marker}\n'
    )
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(row)


def main() -> None:
    canonical_path = PLAN / "Instructions/QA/Evidence/Wave64/audio_pipeline_build.json"
    tracker_canonical_path = PLAN / "Tracker/Evidence/Wave64/audio_pipeline_build.json"
    report_path = PLAN / "Items/Reports/ITEM-W64-025_audio_pipeline_build.json"
    pulled_back = PLAN / "Instructions/Operations/Pulled_Back_Artifacts"
    evidence_path = PLAN / f"Instructions/QA/Evidence/Wave64/AUDIO_PIPELINE_AWS_RUNTIME_INVENTORY_{STAMP}.json"
    mirror_path = PLAN / f"Tracker/Evidence/AUDIO_PIPELINE_AWS_RUNTIME_INVENTORY_{STAMP}.json"
    required = [canonical_path, report_path, pulled_back]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Row025 inputs: {missing}")
    if evidence_path.exists() or mirror_path.exists():
        raise FileExistsError("Row025 AWS reconciliation evidence already exists")

    identity = aws_json("sts", "get-caller-identity")
    instance = aws_json(
        "ec2", "describe-instances", "--instance-ids", INSTANCE_ID,
        "--query", "Reservations[0].Instances[0].State.Name",
    )
    prefix_objects = {prefix: list_prefix(prefix) for prefix in PREFIXES}
    media = []
    audio_objects = []
    for prefix, objects in prefix_objects.items():
        for obj in objects:
            key = str(obj["Key"])
            suffix = Path(key).suffix.lower()
            if suffix in AUDIO_EXTENSIONS:
                audio_objects.append(key)
            if suffix not in MEDIA_EXTENSIONS:
                continue
            record = {"s3_key": key, "bytes": int(obj["Size"]), "last_modified": str(obj["LastModified"]), "extension": suffix}
            if suffix in {".mp4", ".webm"}:
                local = find_local_media(key, pulled_back)
                handlers = sorted(mp4_handler_types(local))
                record.update({
                    "local_path": rel(local), "local_bytes": local.stat().st_size,
                    "local_sha256": digest(local), "handler_types": handlers,
                    "video_handler_present": "vide" in handlers,
                    "audio_handler_present": "soun" in handlers,
                    "s3_local_size_match": local.stat().st_size == int(obj["Size"]),
                })
            media.append(record)

    checks = {
        "least_privilege_role_exact": identity.get("Arn") == EXPECTED_ROLE,
        "approved_instance_stopped": instance == "stopped",
        "three_approved_prefixes_queried": set(prefix_objects) == set(PREFIXES),
        "standalone_audio_object_count_zero": not audio_objects,
        "existing_media_object_count_four": len(media) == 4,
        "all_media_are_existing_wan_mp4": all(item["extension"] == ".mp4" and "wan22" in item["s3_key"] for item in media),
        "all_s3_media_pulled_back": all(item.get("local_path") for item in media),
        "all_s3_local_sizes_match": all(item.get("s3_local_size_match") is True for item in media),
        "all_mp4_video_handlers_present": all(item.get("video_handler_present") is True for item in media),
        "all_mp4_audio_handlers_absent": all(item.get("audio_handler_present") is False for item in media),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Row025 AWS reconciliation checks failed: {failed}")

    evidence = {
        "schema_version": "1.0", "evidence_id": f"W64-AUDIO-PIPELINE-AWS-RUNTIME-INVENTORY-{STAMP}",
        "timestamp": TIMESTAMP, "tracker_id": "TRK-W64-025", "item_id": "ITEM-W64-025",
        "status_decision": STATUS,
        "aws_authority": {"caller_arn": identity["Arn"], "account": identity["Account"], "bucket": BUCKET, "prefixes": list(PREFIXES), "instance_id": INSTANCE_ID, "instance_state": instance},
        "prefix_summary": {prefix: {"object_count": len(objects), "media_object_count": sum(Path(str(item["Key"])).suffix.lower() in MEDIA_EXTENSIONS for item in objects)} for prefix, objects in prefix_objects.items()},
        "standalone_audio_objects": audio_objects,
        "media_objects": media,
        "checks": checks, "check_summary": {"checked": len(checks), "passed": sum(checks.values()), "failed": len(failed)},
        "gate_results": {"genuine_audio_candidate_present": False, "genuine_audio_engine_runtime_proof": False, "genuine_audio_playback_review": False, "certification_loudness_authority": False, "final_audio_certification": False},
        "boundaries": {"read_only_aws_calls_only": True, "ec2_started": False, "generation_executed": False, "completed_media_rerun": False, "mask_or_wave71_touched": False, "jira_mutated": False},
        "result": "blocked_no_genuine_audio_in_local_or_approved_aws_runtime_sources",
        "next_action": "Advance to TRK-W64-026 using existing fail-closed engine authority, then select the next concrete non-duplicate audio implementation task.",
    }
    dump(evidence_path, evidence)
    dump(mirror_path, evidence)

    canonical = load(canonical_path)
    canonical["timestamp"] = TIMESTAMP
    canonical["aws_production_audio_inventory"] = {
        "evidence": rel(evidence_path), "prefixes_checked": 3, "standalone_audio_object_count": 0,
        "existing_video_only_mp4_count": 4, "genuine_runtime_candidate_present": False,
    }
    canonical["runtime"].update({"aws_contacted": True, "aws_read_only_inventory_executed": True, "ec2_started": False})
    canonical["blockers"][0]["reason"] = "Local authoritative roots and approved read-only S3 runtime prefixes contain no genuine audio candidate; the four existing WAN MP4s have video handlers and no audio handlers."
    canonical["result"] = evidence["result"]
    canonical["reconciliation_evidence"] = rel(evidence_path)
    dump(canonical_path, canonical)
    dump(tracker_canonical_path, canonical)

    report = load(report_path)
    report["timestamp"] = TIMESTAMP
    report["validation"].update({"aws_runtime_prefix_inventory": "pass", "aws_prefixes_checked": 3, "aws_audio_object_count": 0, "existing_video_only_mp4_count": 4})
    report["runtime"].update({"aws_contacted": True, "aws_read_only_inventory_executed": True, "ec2_started": False})
    report["blockers"] = canonical["blockers"]
    report["evidence"].append({"path": rel(evidence_path), "sha256": digest(evidence_path)})
    report["next_action"] = evidence["next_action"]
    dump(report_path, report)

    for path in (PLAN / "Tracker/wave64_end_to_end_strict_ai_tracker.csv", PLAN / "Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
        update_csv(path, "Tracker_ID", "TRK-W64-025")
    for path in (PLAN / "Items/wave64_end_to_end_strict_ai_itemized_list.csv", PLAN / "Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):
        update_csv(path, "Item_ID", "ITEM-W64-025")
    for name in ("CURRENT_SESSION_STATE.md", "CURRENT_PURSUING_GOAL.md", "NEXT_ACTION.md", "RESUME_HERE_NEXT_CODEX_SESSION.md"):
        prepend_hydration(PLAN / "Instructions/Hydration_Rehydration" / name, rel(evidence_path))
    append_proof_log(PLAN / "Instructions/Hydration_Rehydration/PROOF_OF_MOVEMENT_LOG.csv", rel(evidence_path))
    print(json.dumps({"status": STATUS, "checks": evidence["check_summary"], "media_objects": len(media), "audio_objects": len(audio_objects), "next_action": evidence["next_action"]}, indent=2))


if __name__ == "__main__":
    main()
