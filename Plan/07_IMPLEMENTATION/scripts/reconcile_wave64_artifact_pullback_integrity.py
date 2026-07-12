from __future__ import annotations

import csv, hashlib, json, subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(r"C:\Comfy_UI_Main"); PLAN=ROOT/"Plan"; TZ=ZoneInfo("America/Chicago")
TRACKER="TRK-W64-043"; ITEM="ITEM-W64-043"; NEXT="TRK-W64-044 / ITEM-W64-044"
STATUS="Completed_Lane_Scoped_Artifact_Pullback_Integrity_Pass"

def rel(p:Path)->str: return p.resolve().relative_to(ROOT.resolve()).as_posix()
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->dict: return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p:Path,v:object)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def add(old:str, values:list[str])->str:
    parts=[x.strip() for x in (old or "").split(";") if x.strip()]
    for value in values:
        if value not in parts: parts.append(value)
    return "; ".join(parts)
def update(path:Path,key:str,value:str,changes:dict)->int:
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f); fields=reader.fieldnames or []; rows=list(reader)
    count=0
    for row in rows:
        if row.get(key)!=value: continue
        count+=1
        for field,new in changes.items():
            if field in fields: row[field]=add(row.get(field,""),new) if isinstance(new,list) else new
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    return count
def prepend(path:Path,block:str)->None:
    old=path.read_text(encoding="utf-8-sig") if path.exists() else ""; path.write_text(block.strip()+"\n\n"+old.lstrip(),encoding="utf-8")
def blob(oid:str)->bytes: return subprocess.check_output(["git","cat-file","blob",oid],cwd=ROOT)

def main()->None:
    now=datetime.now(TZ); iso=now.replace(microsecond=0).isoformat(); stamp=now.strftime("%Y%m%dT%H%M%S-0500")
    qa=PLAN/"Instructions/QA/Evidence/Wave64"; canonical=qa/"artifact_pullback_integrity.json"; original=qa/"ARTIFACT_PULLBACK_INTEGRITY_20260708T233714-0500.json"
    stamped=qa/f"ARTIFACT_PULLBACK_INTEGRITY_RECONCILIATION_{stamp}.json"; mirror=PLAN/"Tracker/Evidence"/stamped.name
    testlog=qa/"artifact_pullback_integrity_reconciliation_test_log.json"; report=PLAN/"Items/Reports/ITEM-W64-043_artifact_pullback_integrity.json"
    row37=qa/"workflow_runtime_smoke.json"; row38=qa/"ec2_runtime_proof.json"; w=load(row37); e=load(row38)
    run=ROOT/"Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500"
    manifest=run/"REMOTE_ARTIFACT_MANIFEST.json"; pullback=run/"PULLBACK_RECORD.json"; image=run/"images/9_codex_hyperreal_editorial_portrait_00002_.png"; log=run/"logs/comfyui.log"; history=run/"reports/history.json"; prompt=run/"workflows/prompt_request.json"
    wt=w["target_runtime_chain"]; et=e["target_runtime_chain"]; integrity=e["integrity_boundary"]
    history_bytes=blob(integrity["history_original_git_blob"]); prompt_bytes=blob(integrity["prompt_original_git_blob"])
    prompt_crlf=prompt_bytes.replace(b"\r\n",b"\n").replace(b"\n",b"\r\n")
    h_remote=next(x["recorded_remote_sha256"] for x in wt["pulled_artifacts"] if x["role"]=="history_report")
    p_remote=next(x["recorded_remote_sha256"] for x in wt["pulled_artifacts"] if x["role"]=="prompt_request")
    checks={
      "row037_lane_complete":w.get("row_complete") is True,"row038_lane_complete":e.get("row_complete") is True,
      "manifest_exists":manifest.exists(),"pullback_record_exists":pullback.exists(),"generated_image_exists":image.exists(),"runtime_log_exists":log.exists(),"history_exists":history.exists(),"prompt_request_exists":prompt.exists(),
      "manifest_hash_matches_row038":sha(manifest)==et["artifact_manifest"]["sha256"],"pullback_hash_matches_row037":sha(pullback)==wt["pullback"]["sha256"],
      "remote_local_count_match":wt["pullback"]["remote_file_count"]==4 and wt["pullback"]["local_file_count"]==4,
      "pullback_hashes_verified":wt["pullback"]["hashes_verified_at_pullback"] is True,
      "image_matches_remote_manifest":sha(image)==et["pulled_output"]["sha256"] and et["pulled_output"]["matches_remote_manifest"] is True,
      "log_matches_remote_manifest":sha(log)==et["pulled_log"]["sha256"] and et["pulled_log"]["matches_remote_manifest"] is True,
      "history_original_blob_matches_remote":hashlib.sha256(history_bytes).hexdigest()==h_remote,
      "prompt_original_blob_crlf_matches_remote":hashlib.sha256(prompt_crlf).hexdigest()==p_remote,
      "current_text_copy_drift_disclosed":integrity["current_history_and_prompt_text_copies_match_remote_manifest"] is False,
      "visual_qa_passed":et["visual_qa"]["qa_score"]>=et["visual_qa"]["pass_threshold"],
      "final_review_closed":et["final_review"]["closes_work_order"] is True,
      "full_project_certification_not_claimed":et["final_review"]["full_project_certification_allowed"] is False}
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit("failed preconditions: "+", ".join(bad))
    payload={"schema_version":"1.0","evidence_id":f"ARTIFACT_PULLBACK_INTEGRITY_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"lane_id":w["lane_id"],"run_id":"aws_gpu_workflow_smoke_20260706T110424-0500","status":STATUS,"row_complete":True,"qa_decision":"artifact_pullback_integrity_lane_scoped_pass_existing_verified_chain",
      "superseded_blocker":{"path":rel(original),"decision":"superseded_for_this_lane","reason":"The July 8 pending dry-run blocker predates the completed W61 generation, 4/4 pullback, QA, and final-review chain reconciled by Rows037/038."},
      "pullback":{"manifest":{"path":rel(manifest),"sha256":sha(manifest)},"record":{"path":rel(pullback),"sha256":sha(pullback),"status":"pullback_hashes_verified"},"remote_file_count":4,"local_file_count":4,"count_match":True,"hashes_verified_at_pullback":True,"image":{"path":rel(image),"sha256":sha(image),"matches_remote":True},"log":{"path":rel(log),"sha256":sha(log),"matches_remote":True}},
      "text_integrity_caveat":{"current_checkout_history_sha256":sha(history),"current_checkout_prompt_sha256":sha(prompt),"current_copies_match_remote":False,"original_git_commit":integrity["original_git_commit"],"history_blob":integrity["history_original_git_blob"],"history_original_sha256":hashlib.sha256(history_bytes).hexdigest(),"history_matches_remote":True,"prompt_blob":integrity["prompt_original_git_blob"],"prompt_original_crlf_sha256":hashlib.sha256(prompt_crlf).hexdigest(),"prompt_matches_remote_after_crlf_checkout":True,"authority":"Historical pullback integrity is proven by recoverable original Git bytes; current edited text copies are not claimed as remote-identical."},
      "qa_followup":{"visual_qa":et["visual_qa"],"final_review":et["final_review"]},"source_reconciliations":[rel(row37),rel(row38)],
      "scope_boundary":{"lane_scoped_only":True,"new_generation_or_pullback":False,"aws_contacted":False,"ec2_started":False,"full_project_certification":False,"masks_or_wave_gates_touched":False,"jira_mutated":False},
      "checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":len(checks),"passed":len(checks),"failed":0},"next_action":f"Advance to {NEXT} model-registry governance duplicate-check without rerunning this completed pullback."}
    paths=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(manifest),rel(pullback),rel(row37),rel(row38)]; payload["evidence_paths"]=paths
    for p in (canonical,stamped,mirror): write(p,payload)
    write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]})
    write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"evidence":paths,"caveat":payload["text_integrity_caveat"]["authority"],"next_action":payload["next_action"]})
    note=f"Wave64 Row043 {stamp}: lane-scoped 4/4 pullback, manifest/image/log hashes, QA and final review pass; original history/prompt Git blobs match remote hashes; current edited text copies not claimed identical."
    tags=["wave64_row043_lane_scoped_pullback_complete","remote_local_4_of_4_hash_verified","original_git_blob_integrity_preserved","full_project_certification_not_claimed"]
    tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":paths,"Coverage_Audit_Status":tags,"Notes":[note]})
    ic=[]
    for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"): ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":paths,"Coverage_Audit_Status":tags,"Notes":[note]}))
    if tc!=1 or ic!=[1,1]: raise SystemExit(f"row update mismatch {tc} {ic}")
    block=f"""## Wave64 Row043 Artifact Pullback Reconciliation - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}` for `aws_gpu_workflow_smoke_20260706T110424-0500`. Existing evidence proves manifest presence, 4/4 remote/local count parity, pullback hash verification, image/log hash parity, visual QA 86/80, and final review closure. Current checked-out history/prompt text copies differ after a later one-token edit; the original Git blobs remain recoverable and reproduce the recorded remote hashes, so historical integrity passes without claiming current-copy parity or full-project certification.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`; `{rel(manifest)}`; `{rel(pullback)}`.

Next: `{NEXT}` model-registry governance duplicate-check; do not rerun this completed pullback."""
    hyd=PLAN/"Instructions/Hydration_Rehydration"
    for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"): prepend(hyd/n,block)
    with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f: csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Closed lane-scoped pullback integrity from existing 4/4 hash-bound artifacts and recoverable original Git blobs.","; ".join(paths),"20/20 checks; count/hash parity; QA/final review; current text-copy caveat",payload["qa_decision"],rel(canonical),f"Advance to {NEXT}; no pullback rerun."])
    print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))

if __name__=="__main__": main()
