from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";DONE=PLAN/"Instructions/QA/Evidence/Done_Certifications";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-059";ITEM="ITEM-W64-059";STATUS="Blocked_Full_Project_Release_Certification_Gates_Not_Met";NEXT="TRK-W64-060 / ITEM-W64-060"
def rel(p):return p.resolve().relative_to(ROOT.resolve()).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def add(s,vals):
 a=[x.strip() for x in (s or "").split(";") if x.strip()]
 for v in vals:
  if v not in a:a.append(v)
 return "; ".join(a)
def update(p,key,val,changes):
 with p.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);fields=r.fieldnames or [];rows=list(r)
 n=0
 for row in rows:
  if row.get(key)!=val:continue
  n+=1
  for k,v in changes.items():
   if k in fields:row[k]=add(row.get(k,""),v) if isinstance(v,list) else v
 with p.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
 return n
def prepend(p,b):p.write_text(b.strip()+"\n\n"+p.read_text(encoding="utf-8-sig").lstrip(),encoding="utf-8")
def main():
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S%z")
 files=sorted(p for p in DONE.iterdir() if p.is_file());inventory=[];invalid=[]
 for p in files:
  rec={"path":rel(p),"bytes":p.stat().st_size,"sha256":sha(p),"suffix":p.suffix.lower()}
  if p.suffix.lower()==".json":
   try:load(p);rec["json_valid"]=True
   except Exception as e:rec["json_valid"]=False;invalid.append({"path":rel(p),"error":str(e)})
  inventory.append(rec)
 inv_hash=hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 protocol=PLAN/"Instructions/QA/DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md";readiness=DONE/"W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.json";base=DONE/"W66_BASE_LANE_FINAL_CERTIFICATION_BLOCKER_AFTER_ROBUSTNESS_20260711T035500-0500.json";inpaint=DONE/"W66_INPAINT_BOUNDED_TARGET_RUNTIME_SMOKE_CERTIFICATE_20260711T031500-0500.json"
 advanced=load(QA/"advanced_additions_integration.json");organization=load(QA/"organization_system.json");blueprint=load(QA/"blueprint_projectplan_combination.json");ec2=load(QA/"ec2_ttl_watchdog.json");secret=load(QA/"secret_git_security.json");governance=load(QA/"blocker_known_issue_control.json");ready=load(readiness);basej=load(base);inp=load(inpaint)
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:tr=[x for x in csv.DictReader(f) if x.get("Tracker_ID")==TRK]
 protocol_text=protocol.read_text(encoding="utf-8-sig")
 normalized_blockers=[
  {"blocker_id":"BLOCKER-W64-AWS-EXPIRED-SESSION-001","source":rel(QA/"ec2_ttl_watchdog.json"),"scope":"new live AWS/EC2/S3 and target-runtime proof"},
  {"blocker_id":"BLOCKER-W64-GIT-DIRTY-WORKTREE-001","source":rel(QA/"secret_git_security.json"),"scope":"strict clean checkpoint"},
  {"blocker_id":"BLOCKER-W64-ADVANCED-DIRECT-PROOF-001","source":rel(QA/"advanced_additions_integration.json"),"scope":"advanced runtime/visual/audio/model/mask proof"},
  {"blocker_id":"BLOCKER-W64-ORGANIZATION-PLACEMENT-DEBT-001","source":rel(QA/"organization_system.json"),"scope":"85 tracked placement violations"},
  {"blocker_id":"BLOCKER-W64-RUNTIME-DEPENDENT-TRACE-LINKS-001","source":rel(QA/"blueprint_projectplan_combination.json"),"scope":"cw_006/cw_007/cw_008 runtime proof"},
  {"blocker_id":"BLOCKER-W66-FINAL-READINESS-001","source":rel(readiness),"scope":"nine of ten runtime lanes blocked from final readiness"},]
 gates={
  "done_cert_schema":{"result":"pass_audit_record_created","reason_codes":[]},
  "evidence_manifest":{"result":"pass_mixed_state_inventory_complete","reason_codes":["inventory_proves_mixed_pass_blocked_state"]},
  "qa_pass":{"result":"fail","reason_codes":["full_project_qa_not_passed","advanced_direct_visual_audio_qa_missing"]},
  "runtime_pass":{"result":"fail","reason_codes":["final_readiness_inputs_invalid","nine_runtime_lanes_blocked","aws_live_proof_expired"]},
  "review_pass":{"result":"fail","reason_codes":["base_lane_final_review_blocked","inpaint_bounded_scope_not_final_lane_review"]},
  "blockers_zero":{"result":"fail","reason_codes":[x["blocker_id"] for x in normalized_blockers]},}
 absolute={"implementation_complete":False,"test_run_complete":False,"qa_pass_or_conditional_pass":False,"artifact_inspection_complete":True,"tracker_update_complete":True,"itemized_list_update_complete":True,"known_issue_review_complete":True,"final_done_certification_record_created":True}
 checks={"CHK-001_inventory_file_count_eq_162":len(inventory)==162,"CHK-002_inventory_json_count_eq_55":sum(x["suffix"]==".json" for x in inventory)==55,"CHK-003_inventory_invalid_json_eq_0":not invalid,"CHK-004_tracker_row059_exists":len(tr)==1,"CHK-005_tracker_row059_status_not_complete":not tr[0]["Status"].startswith("Evidence_Passed"),"CHK-006_tracker_validation_exact":set(tr[0]["Validation_Method"].split("|"))=={"done_cert_schema","evidence_manifest","qa_pass","runtime_pass","review_pass","blockers_zero"},"CHK-007_protocol_has_8_requirements":all(x in protocol_text for x in ("implementation complete","test run complete","QA pass","artifact inspection complete","tracker update complete","itemized list update complete","known issue review complete","final done certification record created")),"CHK-008_protocol_allows_blocked":"- blocked" in protocol_text,"CHK-009_readiness_result_fail":str(ready["result"]).startswith("fail"),"CHK-010_ready_less_than_lane_count":ready["final_ready_lane_count"]<ready["lane_count"],"CHK-011_blocked_lanes_positive":ready["blocked_lane_count"]>0,"CHK-012_git_clean_false":ready["git_gate_summary"]["clean_worktree"] is False,"CHK-013_aws_blocker_present":ec2["status"]=="Blocked_AWS_Expired_Session_Live_Proof","CHK-014_dirty_blocker_present":secret["residual_checkpoint_blocker"]["clean_worktree"] is False,"CHK-015_base_final_blocked":basej["final_decision"]=="blocked" and basej["final_lane_certification"] is False,"CHK-016_inpaint_bounded_only":inp["final_decision"]=="pass_bounded_smoke_scope_only","CHK-017_inpaint_lane_cert_false":inp["final_lane_certification"] is False,"CHK-018_inpaint_route_cert_false":inp["full_route_certification"] is False,"CHK-019_no_full_project_claim":not any((advanced.get("row_complete"),organization.get("row_complete"),inp.get("full_route_certification"),basej.get("full_project_certification"))),"CHK-020_fail_closed_if_gate_fails":any(x["result"]=="fail" for x in gates.values())}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 canonical=QA/"release_done_certification.json";stamped=QA/f"RELEASE_DONE_CERTIFICATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"release_done_certification_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-059_release_done_certification.json"
 payload={"schema_version":"1.0","artifact_type":"release_done_certification_audit","certification_id":stamped.stem,"created_at":iso,"tracker_id":TRK,"item_id":ITEM,"title":"Full-project release done-certification audit","artifact_scope":"C:/Comfy_UI_Main full-project release readiness","implementation_summary":"Current fail-closed audit across done-cert inventory, runtime readiness, lane certificates, active blockers, Tracker, Items, and known issues.","status":STATUS,"row_complete":False,"final_decision":"blocked","certifier":"Codex Desktop autonomous release manager","inventory_summary":{"file_count":len(inventory),"json_count":sum(x["suffix"]==".json" for x in inventory),"invalid_json_count":len(invalid),"inventory_sha256":inv_hash},"required_gates":gates,"absolute_completion_requirements":absolute,"missing_absolute_requirements":[k for k,v in absolute.items() if not v],"lane_scope_preservation":{"preserved_proofs":[rel(inpaint)],"non_promotable_proofs":[{"path":rel(inpaint),"boundary":"bounded smoke only; not final lane or full route"},{"path":rel(base),"boundary":"blocked base final certification"}]},"global_blockers":normalized_blockers,"tests_performed":["20 deterministic release checks","162-file certification inventory parse/hash audit","lane-scope boundary review","Tracker/Items/known-issue review"],"qa_summary":"Full-project QA/review/runtime gates fail; bounded lane evidence preserved without scope promotion.","certification_boundary":"No full-project, final-image, mask, Wave71+, runtime-lane, or release certification is granted.","checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"safety_boundary":{"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"generation_executed":False,"release_promoted":False,"mask_or_jira_mutated":False},"next_action":f"Advance to {NEXT} final end-to-end certification audit while preserving all blockers and bounded lane proofs."}
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report),rel(protocol),rel(readiness),rel(base),rel(inpaint),rel(QA/"advanced_additions_integration.json"),rel(QA/"organization_system.json"),rel(QA/"blueprint_projectplan_combination.json"),rel(QA/"ec2_ttl_watchdog.json"),rel(QA/"secret_git_security.json"),rel(QA/"blocker_known_issue_control.json")];payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_at":iso,"tracker_id":TRK,"result":"pass_audit_decision_blocked","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_at":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"final_decision":"blocked","required_gates":gates,"missing_absolute_requirements":payload["missing_absolute_requirements"],"global_blockers":normalized_blockers,"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row059 {stamp}: 162 certification files/55 JSON valid; 20/20 audit checks; full release blocked by QA/runtime/review/blocker gates; bounded proofs preserved."
 tags=["wave64_row059_release_audit_current","full_release_fail_closed","bounded_lane_proofs_preserved","six_gate_audit","advance_row060_audit"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":"release_done_certification_audit_blocked_full_project_gates","Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")];ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"rows {tc} {ic}")
 block=f"""## Wave64 Row059 Release Done-Certification Audit - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}` with final decision `blocked`. The current audit parsed and hash-bound 162 done-certification files (55 valid JSON), ran 20 checks, and evaluated all six Row059 gates plus the protocol's eight absolute requirements. Full-project QA, runtime, review, and zero-blocker gates fail. Bounded inpaint and other lane-local proofs remain valid only at their certified scope; they do not grant final lane, full-route, mask, or full-project release certification.

Next: `{NEXT}` final end-to-end certification audit. No release promotion or external/runtime action occurred.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 with (HYD/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRK,"Ran current full-project release done-certification audit and preserved bounded lane proof scope.","; ".join(ep),"20/20 audit checks; final decision blocked",payload["final_decision"],rel(canonical),f"Begin {NEXT} audit."])
 print(json.dumps({"status":STATUS,"decision":"blocked","cert_files":len(inventory),"json_valid":55,"failed_gates":[k for k,v in gates.items() if v["result"]=="fail"],"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
