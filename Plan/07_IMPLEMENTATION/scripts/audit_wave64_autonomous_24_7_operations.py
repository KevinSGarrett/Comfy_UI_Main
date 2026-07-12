from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-061";ITEM="ITEM-W64-061";STATUS="Blocked_Live_Operations_Safety_Gates_Not_Met_Local_Controls_Pass";NEXT="TRK-W64-062 / ITEM-W64-062"
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
def named_pass(value,name):
 if isinstance(value,dict):
  if value.get("name")==name and value.get("result")=="pass":return True
  return any(named_pass(v,name) for v in value.values())
 if isinstance(value,list):return any(named_pass(v,name) for v in value)
 return False
def main():
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S%z")
 operational=PLAN/"Instructions/Operations/OPERATIONAL_DONE_GATES.md";strategy=PLAN/"Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md";local_authority=PLAN/"Instructions/LOCAL_SOURCE_OF_TRUTH_AND_EC2_STALE_WORKSPACE_PROTOCOL.md"
 no_loop=load(QA/"no_loop_no_drift.json");hydration=load(QA/"hydration_resume_control.json");secret=load(QA/"secret_git_security.json");ttl=load(QA/"ec2_ttl_watchdog.json");final=load(QA/"final_end_to_end_certification.json")
 w64p=PLAN/"Instructions/QA/Evidence/Runtime_Readiness/W64_EC2_EMERGENCY_STOP_SCHEDULE_DRY_RUN_20260708T233332-0500.json";w66p=PLAN/"Instructions/QA/Evidence/Runtime_Readiness/W66_EC2_EMERGENCY_STOP_SCHEDULE_SELECTED_INPAINT_CURRENT_BUNDLE_DRY_RUN_20260709T173000-0500.json";sentp=PLAN/"Instructions/QA/Evidence/Runtime_Readiness/W66_QA_HELPER_SELECTED_QUEUE_SENTINEL_CURRENT_CONTRACT_FIXED_20260709T132000-0500.json";w64=load(w64p);w66=load(w66p);sent=load(sentp);sent_text=json.dumps(sent,separators=(",",":"))
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:tr=[x for x in csv.DictReader(f) if x.get("Tracker_ID")==TRK]
 preserved=secret["residual_checkpoint_blocker"]["preserved_paths"]
 gates={"bounded_resource_use":{"state":"pass_local_policy_live_blocked","local_scope":"bounded dry-runs, no EC2/generation, stop-after schedule contract","live_scope":"blocked_expired_auth_no_live_runtime_authority"},"latest_state_read":{"state":"pass","scope":"current hydration/no-loop/final-cert evidence"},"no_loop_gate":{"state":"pass","scope":"20/20 current anti-rerun checks and stop rules"},"checkpoint_gate":{"state":"blocked","scope":"five intentionally preserved worktree paths"},"emergency_stop_gate":{"state":"pass_dry_run_live_blocked","scope":"W64/W66 dry-run schedule plans pass; live schedule/watchdog/stopped-state proof absent"}}
 blockers=[{"blocker_id":"AWS_AUTH_EXPIRED_LIVE_RUNTIME_BLOCK","source":rel(QA/"ec2_ttl_watchdog.json")},{"blocker_id":"EMERGENCY_STOP_LIVE_PROOF_MISSING","source":rel(w66p)},{"blocker_id":"CHECKPOINT_DIRTY_WORKTREE_INTENTIONAL_5_PATHS","source":rel(QA/"secret_git_security.json")},{"blocker_id":"LIVE_RUNTIME_AUTHORITY_NOT_GRANTED","source":rel(strategy)},{"blocker_id":"FINAL_CERTIFICATION_STILL_BLOCKED_UPSTREAM","source":rel(QA/"final_end_to_end_certification.json")}]
 checks={"OPS-001_row061_tracker_contract_present":len(tr)==1,"OPS-002_required_gate_tuple_exact":set(tr[0]["Validation_Method"].split("|"))=={"bounded_resource_use","latest_state_read","no_loop_gate","checkpoint_gate","emergency_stop_gate"},"OPS-003_operational_done_gates_present":operational.exists(),"OPS-004_no_loop_current_pass":no_loop["status"]=="Completed_Current_No_Loop_No_Drift_Control_Pass","OPS-005_no_loop_20_of_20":no_loop["check_summary"]=={"checked":20,"passed":20,"failed":0},"OPS-006_hydration_current_pass":hydration["status"]=="Completed_Current_Hydration_Resume_Control_Pass","OPS-007_hydration_20_of_20":hydration["check_summary"]=={"checked":20,"passed":20,"failed":0},"OPS-008_checkpoint_status_blocked":secret["status"]=="Blocked_Intentional_Preserved_Worktree_Checkpoint","OPS-009_preserved_paths_5":len(preserved)==5,"OPS-010_ttl_live_blocked":ttl["status"]=="Blocked_AWS_Expired_Session_Live_Proof","OPS-011_ttl_20_of_20":ttl["check_summary"]=={"checked":20,"passed":20,"failed":0},"OPS-012_w64_dry_run":w64["execute"] is False and w64["result"]=="dry_run_emergency_stop_schedule_plan","OPS-013_w66_dry_run":w66["execute"] is False and w66["result"]=="dry_run_emergency_stop_schedule_plan","OPS-014_dry_runs_no_aws":w64["aws_contacted"] is False and w66["aws_contacted"] is False,"OPS-015_queue_sentinel_local_pass":sent["result"]=="pass_local_only","OPS-016_sentinel_no_ec2_generation":named_pass(sent,"runtime_lane_queue_no_ec2_or_generation") and named_pass(sent,"completed_smoke_disallows_additional_ec2_start") and named_pass(sent,"completed_smoke_disallows_additional_generation"),"OPS-017_final_cert_blocked":final["status"]=="Blocked_Final_End_To_End_Certification_Gates_Not_Met","OPS-018_final_cert_requires_row061":final["next_action"].startswith("Advance with safe local TRK-W64-061"),"OPS-019_local_authority_policy_present":local_authority.exists(),"OPS-020_live_authority_fail_closed":gates["checkpoint_gate"]["state"]=="blocked" and gates["emergency_stop_gate"]["state"].endswith("live_blocked") and ttl["status"].startswith("Blocked")}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 canonical=QA/"autonomous_24_7_operations.json";stamped=QA/f"AUTONOMOUS_24_7_OPERATIONS_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"autonomous_24_7_operations_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-061_autonomous_24_7_operations.json"
 payload={"schema_version":"1.0","evidence_id":stamped.stem,"created_iso":iso,"wave":64,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"row_complete":False,"qa_decision":"local_24_7_safety_controls_pass_live_authority_blocked","gate_results":gates,"local_policy_passes":["bounded dry-run resource policy","latest local hydration state","no-loop/no-drift control","emergency-stop schedule planning","local queue sentinel"],"live_proof_requirements":["fresh AWS identity/account proof","live emergency-stop schedule creation","live SSM watchdog start/verification","bounded runtime execution if separately authorized","final stopped-state verification","clean checkpoint proof"],"normalized_blockers":blockers,"preserved_paths":preserved,"source_hashes":[{"path":rel(p),"sha256":sha(p)} for p in (operational,strategy,local_authority,w64p,w66p,sentp,QA/"no_loop_no_drift.json",QA/"hydration_resume_control.json",QA/"secret_git_security.json",QA/"ec2_ttl_watchdog.json",QA/"final_end_to_end_certification.json")],"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"safety_boundary":{"aws_contacted":False,"ec2_started":False,"generation_executed":False,"git_mutated_by_audit":False,"automation_strategy_modified":False,"jira_mutated":False,"mask_or_wave71_touched":False},"next_action":f"Advance with safe local {NEXT} observability/evidence retention; keep Row061 live authority blocked until AWS, emergency-stop, and checkpoint proof clear."}
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report)]+[x["path"] for x in payload["source_hashes"]];payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"result":"pass_local_controls_live_blocked","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"gate_results":gates,"normalized_blockers":blockers,"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row061 {stamp}: five safety gates audited; local policy/no-loop/hydration/dry-run controls pass; live authority blocked by AWS, live stop proof, and five preserved paths; 20/20 checks."
 tags=["wave64_row061_local_controls_pass","live_24_7_authority_blocked","five_preserved_paths","emergency_stop_dry_run_only","advance_safe_row062"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")];ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"rows {tc} {ic}")
 block=f"""## Wave64 Row061 24/7 Operations Safety - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. Bounded local resource policy, latest-state hydration, no-loop controls, dry-run emergency-stop planning, and the local queue sentinel pass with 20/20 checks. Live 24/7 authority remains blocked by expired AWS authentication, absent live schedule/watchdog/stopped-state proof, five preserved checkpoint paths, and blocked upstream final certification. No AWS, EC2, generation, Git mutation, automation-strategy edit, mask, Jira, or Wave71+ action occurred.

Next safe local action: `{NEXT}` observability and evidence retention.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 with (HYD/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRK,"Audited 24/7 safety controls with local-pass/live-block separation.","; ".join(ep),"20/20 checks; live authority blocked",payload["qa_decision"],rel(canonical),f"Begin {NEXT}."])
 print(json.dumps({"status":STATUS,"gates":gates,"blockers":[x["blocker_id"] for x in blockers],"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
