#!/usr/bin/env python3
"""LOCAL PRIMARY CSV mutator: RunPod-only authority correction Notes sync for 019/023."""
from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
NOW = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

E2E_TRACKER = ROOT / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv"
E2E_TRACKER_WAVES = ROOT / "Plan/Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"
E2E_ITEMS = ROOT / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv"
E2E_ITEMS_WAVES = ROOT / "Plan/Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"

EVID = "Plan/Instructions/QA/Evidence/Wave64"
RUNTIME_EVID = "Plan/Instructions/QA/Evidence/Runtime_Readiness"

BINDING_CORRECTION = (
    f"{EVID}/TRK-W64-019_023_RUNPOD_BINDING_AUTHORITY_CORRECTION_20260721T0004-0500.json"
)
EC2_ABORT = (
    f"{EVID}/TRK-W64-019_023_EC2_UNAUTHORIZED_ABORT_RUNPOD_ONLY_CORRECTION_20260721T000558-0500.json"
)
NEG_INV = f"{EVID}/TRK-W64-019_023_LOCAL_POD_WAN_TI2V_NEGATIVE_INVENTORY_20260720T233253-0500.json"
POD_CLASS_B = f"{EVID}/TRK-W64-019_023_POD_CLASS_B_VLM_SUBSTITUTE_20260721T041516Z.json"
POD_CLASS_AF = f"{EVID}/TRK-W64-019_023_POD_CLASS_A_F_BLOCKER_DISPOSITION_PACKET_20260720T225545-0500.json"
CLASS_B_LEDGER = f"{EVID}/TRK-W64-019_023_CLASS_B_BLOCKER_LEDGER_20260720.json"
FLUX_CANARY = f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_FLUX_CANARY_GENERATION_PASS_20260721T034826Z.json"
OLLAMA_VLM_SMOKE = (
    f"{RUNTIME_EVID}/RUNPOD_1q4ji0gg1fkhvt_OLLAMA_VLM_FLUX_CANARY_SMOKE_PASS_20260721T041729Z.json"
)

ROW010_BLOCKER = f"{EVID}/TRK-W64-010_CLASS_A_F_USER_AUTHORITY_FACE_REF_BLOCKER_PACKAGE_20260720.json"
ROW010_CALIB = f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_CALIB_20260721T035348Z.json"
ROW010_VLM_PANEL_V2 = f"{EVID}/TRK-W64-010_RUNPOD_C1_LOCK_LORA_VLM_IDENTITY_20260721T041746Z.json"
ROW010_FACE_TIGHTER_CALIB = f"{EVID}/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_CALIB_20260721T043424Z.json"
ROW010_FACE_TIGHTER_VLM = f"{EVID}/TRK-W64-010_RUNPOD_C1_FACE_TIGHTER_VLM_20260721T043808Z.json"

ROW017_READINESS = f"{EVID}/TRK-W64-017_FUTURE_PRODUCER_EMISSION_PROOF_READINESS_20260720.json"
ROW017_EMISSION = f"{EVID}/TRK-W64-017_RUNPOD_FUTURE_PRODUCER_EMISSION_PACKET_20260720T233704-0500.json"
ROW017_CLIMB = f"{EVID}/ROW017_RUNPOD_FUTURE_PRODUCER_EMISSION_CLIMB_20260720T233704-0500.json"
ROW017_VLM_DEEPEN = f"{EVID}/ROW017_RUNPOD_MICRO_MASK_V2_VLM_DEEPEN_20260720T233740-0500.json"
ROW017_VLM_OBS = f"{EVID}/TRK-W64-017_RUNPOD_MICRO_MASK_V2_VLM_OBSERVATION_20260720T233740-0500.json"
ROW017_GLOBAL_REVIEW = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/"
    "ROW017_RUNPOD_W69_INPAINT_MICRO_MASK_V2_20260720T233704-0500_GLOBAL_REVIEW.json"
)
ROW017_VISUAL_QA = (
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/"
    "ROW017_RUNPOD_W69_INPAINT_MICRO_MASK_V2_VISUAL_QA_20260720T233704-0500.json"
)

BINDING_PROVE = "bbabad86"
ABORT_PROVE = "8565aab2"
NEG_PROVE = "091cc7d9"
ROW010_LAND = "e0a7830e"
ROW010_PANEL = "f7081a0d"
ROW017_PROVE = ["89656c93", "de9fd957", "12b378b4"]
VLM_ENDPOINT = "WAVE64_VLM_URL=http://127.0.0.1:11434"
SYNC_MARKER = "synced_by_primary_csv_mutator_row019_023_runpod_only_authority_sync_20260721"


def git_short(rev: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", rev], cwd=ROOT, text=True
    ).strip()


def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))


def dump_json(rel: str, obj: dict) -> None:
    path = ROOT / rel.replace("/", "\\")
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_notes(tracker_id: str) -> str:
    with E2E_TRACKER.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Tracker_ID") == tracker_id:
                return row.get("Notes", "")
    raise RuntimeError(f"{tracker_id} missing from tracker CSV")


def rewrite_csv(path: Path, id_col: str, updates: dict[str, dict[str, str]]) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    assert fields
    for row in rows:
        key = row[id_col]
        if key in updates:
            row.update(updates[key])
    for key in updates:
        assert any(r[id_col] == key for r in rows), f"missing {key} in {path}"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def already_synced_019_023(notes: str, prove: list[str]) -> bool:
    return (
        "RunPod sole authorized GPU runtime" in notes
        and "f3f6cc84 recovery authority REVOKED" in notes
        and "EC2 live 3/3" not in notes
        and "WITH_EC2_RECOVERY_AUTHORITY" not in notes
        and prove[0] in notes
        and prove[1] in notes
        and "no COMPLETE" in notes
    )


def row010_needs_tip_sync(notes: str, tip: str) -> bool:
    if ROW010_LAND not in notes:
        return True
    match = re.search(r"Durable RunPod Ollama VLM/LLM reviewer UP \(e1401895/([0-9a-f]+)\)", notes)
    return match is None or match.group(1) != tip


def row017_needs_tip_sync(notes: str, tip: str) -> bool:
    if not all(sha in notes for sha in ROW017_PROVE):
        return True
    return tip not in notes


def build_row019_notes(prove: list[str]) -> str:
    return (
        f"Class F RunPod sole authorized GPU runtime Wan TI2V authority correction "
        f"({prove[0]}/{prove[1]}/20260721T0004-0500): RunPod 1q4ji0gg1fkhvt sole authorized "
        "runtime and Wan recovery surface "
        "(/workspace/ComfyUI/models/{diffusion_models,text_encoders,vae}/); unauthorized EC2 "
        "start+local scp ABORTED (f3f6cc84 recovery authority REVOKED; EC2 deferred not runtime); "
        "Wan TI2V 0/3 ABSENT on RunPod pod; local+pod negative inventory reaffirm "
        f"({NEG_PROVE}/20260720T233253-0500); Class F retained until 3/3 hash-bound on pod via "
        "RunPod-authorized paths only; proof_tier=RUNPOD_BINDING_AUTHORITY_CORRECTION_BOUNDED; "
        "row_complete=false; no COMPLETE; Row074 PCM left alone. "
        f"Evidence: {BINDING_CORRECTION}; {EC2_ABORT}; {NEG_INV}; {POD_CLASS_B}; "
        f"{POD_CLASS_AF}; {CLASS_B_LEDGER}; {FLUX_CANARY}"
    )


def build_row023_notes(prove: list[str]) -> str:
    return (
        f"Class F RunPod sole authorized GPU runtime Wan TI2V authority correction "
        f"({prove[0]}/{prove[1]}/20260721T0004-0500): immutable Row023 Wan reject reaffirmed; "
        "RunPod 1q4ji0gg1fkhvt sole authorized runtime and Wan recovery surface; unauthorized "
        "EC2 start+local scp ABORTED (f3f6cc84 recovery authority REVOKED; EC2 deferred not "
        "runtime); Wan TI2V 0/3 ABSENT on RunPod pod; Class F retained until 3/3 hash-bound on "
        "pod via RunPod-authorized paths only; "
        "proof_tier=RUNPOD_BINDING_AUTHORITY_CORRECTION_BOUNDED; row_complete=false; no COMPLETE; "
        f"Row074 PCM left alone. Evidence: {BINDING_CORRECTION}; {EC2_ABORT}; {NEG_INV}; "
        f"{POD_CLASS_B}; {POD_CLASS_AF}; {CLASS_B_LEDGER}; {FLUX_CANARY}"
    )


def build_row010_notes(tip: str) -> str:
    return (
        "Class A/F USER_AUTHORITY face-ref blocker (b9085976/db81ab66): per-character reference "
        "crops absent and not inventable; proof_tier=OFFLINE_INVENTORY_BLOCKER_BOUNDED; "
        "RunPod personal-calibration panel-v2 VLM GATE CLEARED "
        f"({ROW010_PANEL}/041746Z): qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean "
        "0.5625 (n=4)/body_silhouette_mean 0.9/solo_lock_trait_alignment 0.95; "
        "runtime_pass_bounded=true; still NONCANONICAL; C1 lock+LoRA calib (035348Z/cf72e756) "
        "retained; RunPod personal-calibration face-tighter VLM BELOW_GATE "
        f"({ROW010_LAND}/043808Z): qwen2.5vl:7b side_by_side_panel_v2 face_consistency_mean 0.475 "
        "(n=4)/body_silhouette_mean 0.9/solo_lock_trait_alignment 0.95; runtime_pass_bounded=false; "
        "face-tighter calib (043424Z) retained; multi-character USER_AUTHORITY retained blocked; "
        "does NOT clear generic multi-character USER_AUTHORITY chain; row_complete=false; "
        "NEVER Complete. Blockers: USER_AUTHORITY_PER_CHARACTER_REFERENCE_CROPS_ABSENT|"
        "USER_AUTHORITY_FACE_BODY_REFERENCES_NOT_INVENTABLE|"
        "PORTABLE_MULTI_CHARACTER_REFERENCE_CHAIN_ABSENT|PERSONAL_CALIBRATION_CHARACTER1_EXCLUDED. "
        f"Evidence: {ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_PANEL_V2}; "
        f"{ROW010_FACE_TIGHTER_CALIB}; {ROW010_FACE_TIGHTER_VLM} "
        f"Durable RunPod Ollama VLM/LLM reviewer UP (e1401895/{tip}): {VLM_ENDPOINT} "
        f"(llava:13b / qwen2.5:7b-instruct); Flux canary VLM smoke PASS_WITH_NOTES. "
        f"Evidence: {OLLAMA_VLM_SMOKE}"
    )


def build_row017_notes(tip: str) -> str:
    deepen = load_json(ROW017_VLM_DEEPEN)
    visual_qa = load_json(ROW017_VISUAL_QA)
    output_sha = deepen["output_sha256"][:12]
    face_mean = float(visual_qa["difference_metrics"]["face_skin_region_mean_abs"])
    prove_chain = "/".join([*ROW017_PROVE, tip])
    return (
        "Class C cleared (70e12e70); Class E emission-proof readiness (cc68fd5a); RunPod "
        "w69_inpaint micro_mask_v2 future-producer GLOBAL_REVIEW pass "
        "VISUAL_QA_PASS_BOUNDED (20260720T233704-0500) + Ollama qwen2.5vl:7b VLM observation "
        f"vlm_ok ({prove_chain}/20260720T233740-0500); face_skin_region_mean_abs "
        f"{face_mean:.6f}; output sha {output_sha}...; Status remains "
        "Blocked_Canonical_Future_Localized_Producer_Global_Review_Contract_Pending; "
        "row_complete=false; NEVER Complete; leave Row074 alone. Blockers: "
        "CLASS_E_FUTURE_PRODUCER_GLOBAL_REVIEW_CONTRACT_PENDING|PRODUCT_CAMPAIGN_ACCEPTANCE_PENDING. "
        f"Evidence: {ROW017_READINESS}; {ROW017_EMISSION}; {ROW017_CLIMB}; "
        f"{ROW017_VLM_DEEPEN}; {ROW017_VLM_OBS}; {ROW017_GLOBAL_REVIEW}; {ROW017_VISUAL_QA}"
    )


def main() -> None:
    tip = git_short()
    prove_019 = [BINDING_PROVE, ABORT_PROVE, tip]

    binding = load_json(BINDING_CORRECTION)
    abort = load_json(EC2_ABORT)
    assert binding.get("runtime_authority") == "runpod_remote_only"
    assert binding.get("row_complete") is False
    assert binding.get("constraints", {}).get("row074_untouched") is True
    assert abort.get("row074_touched") is False
    assert abort.get("corrected_recovery_path", {}).get("sole_runtime") == "RunPod"

    e2e_tracker_updates: dict[str, dict[str, str]] = {}
    e2e_item_updates: dict[str, dict[str, str]] = {}
    synced: list[str] = []

    notes019 = read_notes("TRK-W64-019")
    if not already_synced_019_023(notes019, prove_019):
        row019_notes = build_row019_notes(prove_019)
        row023_notes = build_row023_notes(prove_019)
        row019_evidence = (
            f"{BINDING_CORRECTION}; {EC2_ABORT}; {NEG_INV}; {POD_CLASS_B}; "
            f"{POD_CLASS_AF}; {CLASS_B_LEDGER}"
        )
        row023_evidence = f"{row019_evidence}; {FLUX_CANARY}"
        e2e_tracker_updates["TRK-W64-019"] = {
            "Notes": row019_notes,
            "Evidence_Path": row019_evidence,
        }
        e2e_tracker_updates["TRK-W64-023"] = {
            "Notes": row023_notes,
            "Evidence_Path": row023_evidence,
        }
        e2e_item_updates["ITEM-W64-019"] = {"Notes": row019_notes}
        e2e_item_updates["ITEM-W64-023"] = {"Notes": row023_notes}
        synced.append("019/023 RunPod-only authority")

    notes010 = read_notes("TRK-W64-010")
    if row010_needs_tip_sync(notes010, tip):
        row010_notes = build_row010_notes(tip)
        row010_evidence = (
            f"{ROW010_BLOCKER}; {ROW010_CALIB}; {ROW010_VLM_PANEL_V2}; "
            f"{ROW010_FACE_TIGHTER_CALIB}; {ROW010_FACE_TIGHTER_VLM}; {OLLAMA_VLM_SMOKE}"
        )
        e2e_tracker_updates["TRK-W64-010"] = {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes,
            "Evidence_Path": row010_evidence,
        }
        e2e_item_updates["ITEM-W64-010"] = {
            "Status": "Blocked_Identity_Reference_Proof_Missing_Separation_And_Merge_Rejection_Pass",
            "Notes": row010_notes,
        }
        synced.append("010 tip SHA")

    notes017 = read_notes("TRK-W64-017")
    if row017_needs_tip_sync(notes017, tip):
        row017_notes = build_row017_notes(tip)
        row017_evidence = (
            f"{ROW017_READINESS}; {ROW017_EMISSION}; {ROW017_CLIMB}; "
            f"{ROW017_VLM_DEEPEN}; {ROW017_VLM_OBS}; {ROW017_GLOBAL_REVIEW}; {ROW017_VISUAL_QA}"
        )
        e2e_tracker_updates["TRK-W64-017"] = {
            "Notes": row017_notes,
            "Evidence_Path": row017_evidence,
        }
        e2e_item_updates["ITEM-W64-017"] = {"Notes": row017_notes}
        synced.append("017 tip SHA")

    if not e2e_tracker_updates:
        print("tip", tip)
        print("no-op: RunPod-only authority and 010/017 tip Notes already synced")
        print("Row074 untouched")
        return

    rewrite_csv(E2E_TRACKER, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_TRACKER_WAVES, "Tracker_ID", e2e_tracker_updates)
    rewrite_csv(E2E_ITEMS, "Item_ID", e2e_item_updates)
    rewrite_csv(E2E_ITEMS_WAVES, "Item_ID", e2e_item_updates)

    ledger_vocab = {
        "note": (
            f"Mechanical CSV mutator Row019/023 RunPod-only authority sync from "
            f"{','.join(prove_019)}; Wan 0/3 on RunPod pod; EC2 recovery revoked; no COMPLETE."
        ),
        "product_completion": False,
        "synced_at": NOW,
        "prove_commits": prove_019,
    }
    for rel in (
        BINDING_CORRECTION,
        "Plan/Tracker/Evidence/Wave64/"
        "TRK-W64-019_023_RUNPOD_BINDING_AUTHORITY_CORRECTION_20260721T0004-0500.json",
        EC2_ABORT,
        "Plan/Tracker/Evidence/Wave64/"
        "TRK-W64-019_023_EC2_UNAUTHORIZED_ABORT_RUNPOD_ONLY_CORRECTION_20260721T000558-0500.json",
    ):
        packet = load_json(rel)
        packet["csv_sync"] = SYNC_MARKER
        packet["csv_sync_tip"] = tip
        packet["ledger_vocabulary_sync"] = ledger_vocab
        if packet.get("constraints", {}).get("csv_sync") == "deferred_evidence_only":
            packet["constraints"]["csv_sync"] = SYNC_MARKER
        dump_json(rel, packet)

    print("tip", tip)
    print("synced:", ", ".join(synced))
    print("Row074 untouched")


if __name__ == "__main__":
    main()
