#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: land pod strict self-hosted LLM visual QA capability.

Capability / policy binding only — NOT product COMPLETE for 010/017/019/023/084.
Does not touch Row074 HOLD or Row076 PID. RunPod-only authority documented.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

E2E_TRACKER = ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"
E2E_TRACKER_WAVES = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"
E2E_ITEMS = ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"
E2E_ITEMS_WAVES = ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"

STAMP = "20260721T1100-0500"
EVID_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    f"POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_CAPABILITY_{STAMP}.json"
)
EVID_TRACKER = (
    "Plan/Tracker/Evidence/"
    f"POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_CAPABILITY_{STAMP}.json"
)
CONFIRM_REL = (
    "Plan/Instructions/QA/Evidence/Wave64/"
    f"POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_CONFIRMATION_{STAMP}.json"
)
CONFIRM_TRACKER = (
    "Plan/Tracker/Evidence/"
    f"POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_CONFIRMATION_{STAMP}.json"
)
FIXTURE_DIR = (
    "Plan/Instructions/QA/Evidence/Wave64/fixtures/"
    "pod_strict_visual_qa_selftest_20260721T1100"
)
PULLBACK_DIR = (
    "Plan/Instructions/Operations/Pulled_Back_Artifacts/"
    "runpod_strict_visual_qa_selftest_20260721T1100"
)
STRATEGY = "Plan/Instructions/POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_STRATEGY.md"
SCHEMA = "Plan/08_SCHEMAS/pod_strict_self_hosted_llm_visual_qa_receipt.schema.json"
EXAMPLE = "Plan/09_EXAMPLES/pod_strict_self_hosted_llm_visual_qa_receipt.example.json"
REVIEWER = "Plan/07_IMPLEMENTATION/scripts/wave64_pod_strict_visual_qa.py"
VALIDATOR = "Plan/07_IMPLEMENTATION/scripts/validate_wave64_pod_strict_visual_qa_receipt.py"
CLIENT = "Plan/07_IMPLEMENTATION/scripts/wave64_autonomous_vlm_client.py"
CLASS_E = "Plan/07_IMPLEMENTATION/scripts/validate_wave64_wan_ti2v_class_e_runtime_proof_claim.py"
HANDOFF = "Plan/00_PROJECT_CONTROL/MAIN_SESSION_INTEGRATION_HANDOFF_CURRENT.md"

SYNC_MARKER = "synced_by_primary_csv_mutator_pod_strict_self_hosted_llm_visual_qa"

STATUS_017 = (
    "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending_"
    "Strict_Pod_Llm_Visual_Qa_Capability_Landed"
)
STATUS_019 = (
    "Blocked_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_Class_A_Motion_Stronger_FAIL_"
    "Strict_Pod_Llm_Visual_Qa_Capability_Landed"
)
STATUS_023 = (
    "Blocked_Video_Frame_Repair_Product_Visual_Qa_Open_Bounded_Wan_Ti2v_"
    "Class_A_Motion_Stronger_FAIL_Strict_Pod_Llm_Visual_Qa_Capability_Landed"
)
DECISION = "pod_strict_self_hosted_llm_visual_qa_capability_landed_policy_binding"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def sha256_file(rel: str) -> str:
    path = ROOT / rel.replace("/", "\\")
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_notes(tracker_id: str) -> str:
    with E2E_TRACKER_WAVES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == tracker_id:
                return row.get("Notes", "")
    raise RuntimeError(f"{tracker_id} missing")


def rewrite_csv(path: Path, id_col: str, updates: dict[str, dict[str, str]]) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields
    for row in rows:
        key = row[id_col]
        if key in updates:
            assert "074" not in key
            assert "076" not in key
            for col, val in updates[key].items():
                if col in row:
                    row[col] = val
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    assert "TRK-W64-074" not in updates
    assert "ITEM-W64-074" not in updates
    assert "TRK-W64-076" not in updates
    assert "ITEM-W64-076" not in updates
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_notes(prior: str, *, tip: str, row: str) -> str:
    block = (
        f"[{NOW}] {SYNC_MARKER} tip={tip} row={row}: CAPABILITY LANDED / POLICY BINDING — "
        f"RunPod self-hosted strict visual QA (qwen2.5vl:32b / 33.5B Q4_K_M) required for "
        f"PRODUCT/CLASS_A/PROOF_LANDED/IDENTITY_GATE. Dual-gate: generation receipt != "
        f"visual approval; retain human_frame_read where gated. Weak qwen2.5vl:7b is "
        f"SMOKE/observation only (historical false PASS Wan motion 083156Z rejected by "
        f"strict self-test). Strategy={STRATEGY}; schema={SCHEMA}; reviewer={REVIEWER}; "
        f"confirmation={CONFIRM_REL}. row_complete=false; no product COMPLETE; Row074 "
        f"untouched; Row076 untouched; no Wan re-fetch; no 017 redo; no invent 084 gold. "
        f"Evidence={EVID_REL}"
    )
    if SYNC_MARKER in prior:
        return block
    return (prior.rstrip() + " || " + block).strip(" |")


def load_selftest_summary() -> dict:
    bad = ROOT / FIXTURE_DIR.replace("/", "\\") / "known_bad_motion_083156Z_strict_receipt.json"
    good = ROOT / FIXTURE_DIR.replace("/", "\\") / "known_better_sharp_hand_still_strict_receipt.json"
    show = ROOT / FIXTURE_DIR.replace("/", "\\") / "ollama_show_qwen2.5vl_32b.txt"
    bad_o = json.loads(bad.read_text(encoding="utf-8"))
    good_o = json.loads(good.read_text(encoding="utf-8"))
    return {
        "known_bad": {
            "path": f"{FIXTURE_DIR}/known_bad_motion_083156Z_strict_receipt.json",
            "sha256": sha256_file(f"{FIXTURE_DIR}/known_bad_motion_083156Z_strict_receipt.json"),
            "strict_pod_llm_review": bad_o.get("strict_pod_llm_review"),
            "expectation_met": (bad_o.get("self_test") or {}).get("expectation_met"),
            "model": (bad_o.get("model") or {}).get("name"),
            "parameter_size": (bad_o.get("model") or {}).get("parameter_size"),
            "blocking_defect_codes": [d.get("code") for d in (bad_o.get("blocking_defects") or [])],
        },
        "known_better_still": {
            "path": f"{FIXTURE_DIR}/known_better_sharp_hand_still_strict_receipt.json",
            "sha256": sha256_file(
                f"{FIXTURE_DIR}/known_better_sharp_hand_still_strict_receipt.json"
            ),
            "strict_pod_llm_review": good_o.get("strict_pod_llm_review"),
            "note": (
                "High bars may REJECT even stronger stills; REJECT here is allowed and "
                "proves bars were not weakened for PASS chase."
            ),
            "model": (good_o.get("model") or {}).get("name"),
        },
        "ollama_show_text_sha256": sha256_file(f"{FIXTURE_DIR}/ollama_show_qwen2.5vl_32b.txt"),
        "ollama_show_excerpt": show.read_text(encoding="utf-8")[:500],
    }


def main() -> int:
    tip = git_short()
    selftest = load_selftest_summary()
    assert selftest["known_bad"]["strict_pod_llm_review"] == "REJECT"
    assert selftest["known_bad"]["expectation_met"] is True

    evidence_obj = {
        "schema_version": "wave64.pod_strict_visual_qa.capability.v1",
        "stamp": STAMP,
        "created_utc": NOW,
        "git_tip_at_mutator": tip,
        "status_claim": "capability_landed_policy_binding",
        "product_complete_claimed": False,
        "row_complete": False,
        "was_already_in_place": False,
        "implemented_now": True,
        "authority": {
            "host": "runpod",
            "pod_id": "1q4ji0gg1fkhvt",
            "ssh": "root@195.26.233.100 -p 52077",
            "endpoint": "WAVE64_VLM_URL=http://127.0.0.1:11434",
            "ec2_forbidden": True,
            "local_comfy_runtime_forbidden": True,
        },
        "strict_model": {
            "name": "qwen2.5vl:32b",
            "parameters": "33.5B",
            "quantization": "Q4_K_M",
            "size_gb_approx": 21,
            "env": "WAVE64_STRICT_VLM_MODEL",
            "num_ctx_default": 8192,
            "fail_closed_if_missing": True,
        },
        "smoke_model": {
            "name": "qwen2.5vl:7b",
            "env": "WAVE64_VLM_SMOKE_MODEL",
            "lane_only": "SMOKE",
            "forbidden_for_product": True,
        },
        "historical_weak_pass": {
            "artifact": "runpod_wan_ti2v_class_e_motion_20260721T083156Z",
            "weak_model": "qwen2.5vl:7b",
            "weak_verdict": "PASS",
            "strict_self_test_verdict": "REJECT",
            "human_later": "FAIL near-static / mushy hands",
        },
        "dual_gate": {
            "generation_receipt_is_not_visual_approval": True,
            "strict_pod_llm_review_required_for_product": True,
            "human_frame_read_retained_where_gated": True,
            "class_e_proof_min_bytes": 250000,
        },
        "vram_policy": {
            "gpu": "NVIDIA RTX 6000 Ada Generation ~48GB",
            "comfy_unload_before_strict_review": True,
            "num_ctx_cap_for_coexistence": 8192,
            "sequential_only_with_wan_or_flux_resident": True,
            "unload_vlm_after_review": True,
        },
        "files": {
            "strategy": STRATEGY,
            "schema": SCHEMA,
            "example": EXAMPLE,
            "reviewer": REVIEWER,
            "receipt_validator": VALIDATOR,
            "client": CLIENT,
            "class_e_claim_validator": CLASS_E,
            "handoff": HANDOFF,
            "fixture_dir": FIXTURE_DIR,
            "pullback_dir": PULLBACK_DIR,
            "confirmation": CONFIRM_REL,
        },
        "file_hashes_sha256": {
            STRATEGY: sha256_file(STRATEGY),
            SCHEMA: sha256_file(SCHEMA),
            REVIEWER: sha256_file(REVIEWER),
            VALIDATOR: sha256_file(VALIDATOR),
            CLIENT: sha256_file(CLIENT),
            CLASS_E: sha256_file(CLASS_E),
        },
        "self_test": selftest,
        "tracker_rows_touched": ["TRK-W64-010", "TRK-W64-017", "TRK-W64-019", "TRK-W64-023"],
        "boundaries": {
            "row074_left_alone": True,
            "row076_left_alone": True,
            "no_wan_weight_refetch": True,
            "no_017_primary_redo": True,
            "no_invent_084_gold": True,
            "no_false_product_complete": True,
        },
        "decision": DECISION,
        "synced_by": SYNC_MARKER,
    }
    dump_json(EVID_REL, evidence_obj)
    dump_json(EVID_TRACKER, evidence_obj)

    confirmation = {
        "schema_version": "wave64.pod_strict_visual_qa.confirmation.v1",
        "stamp": STAMP,
        "created_utc": NOW,
        "git_tip_at_mutator": tip,
        "status": "implemented_now",
        "was_already_in_place": False,
        "model_used_for_strict_review": "qwen2.5vl:32b",
        "model_show": selftest["ollama_show_excerpt"],
        "self_test_reject_known_bad": selftest["known_bad"],
        "self_test_known_better_still": selftest["known_better_still"],
        "code_paths_wired": [
            REVIEWER,
            VALIDATOR,
            CLIENT,
            CLASS_E,
            SCHEMA,
            STRATEGY,
            HANDOFF,
        ],
        "capability_evidence": EVID_REL,
        "product_complete_claimed": False,
        "hashes": evidence_obj["file_hashes_sha256"],
        "fixture_hashes": {
            selftest["known_bad"]["path"]: selftest["known_bad"]["sha256"],
            selftest["known_better_still"]["path"]: selftest["known_better_still"]["sha256"],
            f"{FIXTURE_DIR}/ollama_show_qwen2.5vl_32b.txt": selftest["ollama_show_text_sha256"],
        },
    }
    dump_json(CONFIRM_REL, confirmation)
    dump_json(CONFIRM_TRACKER, confirmation)

    tip_notes = {
        "TRK-W64-017": build_notes(read_notes("TRK-W64-017"), tip=tip, row="017"),
        "TRK-W64-019": build_notes(read_notes("TRK-W64-019"), tip=tip, row="019"),
        "TRK-W64-023": build_notes(read_notes("TRK-W64-023"), tip=tip, row="023"),
        "TRK-W64-010": build_notes(read_notes("TRK-W64-010"), tip=tip, row="010"),
    }

    tracker_updates = {
        "TRK-W64-017": {
            "Status": STATUS_017,
            "Notes": tip_notes["TRK-W64-017"],
            "Evidence_Path": EVID_REL,
            "Status_Decision": DECISION,
        },
        "TRK-W64-019": {
            "Status": STATUS_019,
            "Notes": tip_notes["TRK-W64-019"],
            "Evidence_Path": EVID_REL,
            "Status_Decision": DECISION,
        },
        "TRK-W64-023": {
            "Status": STATUS_023,
            "Notes": tip_notes["TRK-W64-023"],
            "Evidence_Path": EVID_REL,
            "Status_Decision": DECISION,
        },
        "TRK-W64-010": {
            "Notes": tip_notes["TRK-W64-010"],
            # Status intentionally unchanged — no COMPLETE / no false product claim
        },
    }
    for path in (E2E_TRACKER, E2E_TRACKER_WAVES):
        rewrite_csv(path, "Tracker_ID", tracker_updates)

    item_updates = {
        "ITEM-W64-017": {
            "Status": STATUS_017,
            "Notes": tip_notes["TRK-W64-017"],
        },
        "ITEM-W64-019": {
            "Status": STATUS_019,
            "Notes": tip_notes["TRK-W64-019"],
        },
        "ITEM-W64-023": {
            "Status": STATUS_023,
            "Notes": tip_notes["TRK-W64-023"],
        },
        "ITEM-W64-010": {
            "Notes": tip_notes["TRK-W64-010"],
        },
    }
    for path in (E2E_ITEMS, E2E_ITEMS_WAVES):
        rewrite_csv(path, "Item_ID", item_updates)

    # Timestamped handoff copy
    src = ROOT / HANDOFF.replace("/", "\\")
    dst = ROOT / (
        "Plan/00_PROJECT_CONTROL/MAIN_SESSION_INTEGRATION_HANDOFF_20260721T1105-0500.md"
    )
    shutil.copy2(src, dst)

    print(
        json.dumps(
            {
                "ok": True,
                "evidence": EVID_REL,
                "confirmation": CONFIRM_REL,
                "tip": tip,
                "known_bad_reject": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
