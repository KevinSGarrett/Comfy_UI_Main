from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";TZ=ZoneInfo("America/Chicago");TRACKER="TRK-W64-048";ITEM="ITEM-W64-048";NEXT="TRK-W64-049 / ITEM-W64-049";STATUS="Completed_Current_No_Loop_No_Drift_Control_Pass"
def rel(p):return p.resolve().relative_to(ROOT.resolve()).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def add(old,vals):
 p=[x.strip() for x in (old or "").split(";") if x.strip()]
 for v in vals:
  if v not in p:p.append(v)
 return "; ".join(p)
def update(path,key,val,changes):
 with path.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);fields=r.fieldnames or [];rows=list(r)
 n=0
 for row in rows:
  if row.get(key)!=val:continue
  n+=1
  for field,new in changes.items():
   if field in fields:row[field]=add(row.get(field,""),new) if isinstance(new,list) else new
 with path.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
 return n
def prepend(path,block):
 old=path.read_text(encoding="utf-8-sig") if path.exists() else "";path.write_text(block.strip()+"\n\n"+old.lstrip(),encoding="utf-8")
def main():
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S-0500");qa=PLAN/"Instructions/QA/Evidence/Wave64";canonical=qa/"no_loop_no_drift.json";original=qa/"NO_LOOP_NO_DRIFT_20260708T235942-0500.json";stamped=qa/f"NO_LOOP_NO_DRIFT_RECONCILIATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;testlog=qa/"no_loop_no_drift_reconciliation_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-048_no_loop_no_drift.json"
 names=["github_actions_ci_package","s3_transfer_cost_control","ec2_ttl_watchdog","artifact_pullback_integrity","model_registry_governance","civitai_metadata","secret_git_security","hydration_resume_control"];paths=[qa/f"{n}.json" for n in names];rows=[load(p) for p in paths];by={int(x["tracker_id"].split("-")[-1]):x for x in rows}
 governance=qa/"blocker_known_issue_control.json";old_governance=load(governance)
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:row49=[x for x in csv.DictReader(f) if x.get("Tracker_ID")=="TRK-W64-049"]
 checks={"eight_current_evidence_files":len(rows)==8,"rows_040_through_047_exact":set(by)==set(range(40,48)),"row040_current_blocker_recorded":by[40]["status"]=="Blocked_Current_Model_Registry_Coverage_Alignment","row040_governance_gaps_superseded":by[44]["status"]=="Completed_Local_Model_Registry_Governance_Pass","row041_local_ready_preserved":by[41]["status"]=="Local_Ready_Only_AWS_Authentication_Expired","row042_live_blocker_active":by[42]["status"]=="Blocked_AWS_Expired_Session_Live_Proof","row043_old_artifact_blocker_superseded":by[43]["status"]=="Completed_Lane_Scoped_Artifact_Pullback_Integrity_Pass","row044_governance_pass":by[44].get("row_complete") is True,"row045_provenance_pass":by[45].get("row_complete") is True,"row046_checkpoint_blocker_active":by[46].get("row_complete") is False,"row047_hydration_pass":by[47].get("row_complete") is True,"row040_no_external_action":by[40]["safety_boundaries"]["aws_contacted"] is False and by[40]["safety_boundaries"]["ec2_started"] is False,"row041_no_live_aws_action":by[41]["live_aws_boundary"]["s3_publish_execute_run"] is False,"row042_dry_run_only":by[42]["external_actions"]["aws_contacted"] is False and by[42]["external_actions"]["ec2_started"] is False,"row043_no_new_generation_pullback":by[43]["scope_boundary"]["new_generation_or_pullback"] is False,"row044_local_only":by[44]["scope"]["local_only"] is True,"row045_no_network_lookup":by[45]["boundaries"]["network_contacted"] is False,"row046_ec2_blocked":by[46]["residual_checkpoint_blocker"]["ec2_start_allowed"] is False,"row047_no_external_mask_jira":all(v is False for v in by[47]["runtime_boundary"].values()),"row049_living_governance_refresh_justified":len(row49)==1 and row49[0].get("Workstream")=="blocker_known_issue_control" and old_governance.get("created_iso","")<by[47].get("created_at","")}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 payload={"schema_version":"1.0","evidence_id":f"NO_LOOP_NO_DRIFT_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"row_complete":True,"qa_decision":"current_no_loop_no_drift_pass_advance_to_row049","task":"Bind no-loop/no-drift control to current Row040-047 reconciliations and advance.","current_evidence":[{"tracker_id":x["tracker_id"],"item_id":x["item_id"],"path":rel(p),"sha256":sha(p),"status":x.get("status"),"qa_decision":x.get("qa_decision")} for p,x in zip(paths,rows)],"active_blockers":[{"row":"TRK-W64-042","blocker":"AWS authentication expired; live EventBridge/SSM/final-stop proof absent."},{"row":"TRK-W64-046","blocker":"Five intentionally preserved paths keep strict worktree checkpoint dirty."}],"superseded_blockers":[{"row":"TRK-W64-040","blocker":"Depth/Lineart vocabulary and Flux missing record/queue","superseded_by":"TRK-W64-044 current 15-record/10-lane governance pass"},{"row":"TRK-W64-043","blocker":"Pending runtime artifacts","superseded_by":"TRK-W64-043 lane-scoped 4/4 pullback reconciliation"}],"row049_semantics":{"mode":"living_governance_refresh","prior_evidence":rel(governance),"prior_created_iso":old_governance.get("created_iso"),"refresh_justification":"Rows040-048 materially changed the active and superseded blocker set after the prior Row049 evidence."},"stop_rules":{"completed_proofs_rerun":False,"blocked_aws_or_checkpoint_state_retried":False,"coverage_or_hydration_loop_allowed":False,"mask_or_wave_gate_rerun":False,"advance_required":True},"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"next_action":f"Run one current {NEXT} living governance refresh because blocker inputs changed; then advance past already-passed rows to the first unresolved concrete row."}
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(original)]+[rel(p) for p in paths];payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"active_blockers":payload["active_blockers"],"superseded_blockers":payload["superseded_blockers"],"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row048 {stamp}: current Rows040-047 bound; two active blockers isolated; old governance/artifact blockers superseded; no runtime/mask loops; advance Row049."
 tags=["wave64_row048_current_no_loop_pass","two_active_blockers_exact","superseded_blockers_not_reopened","advance_to_row049"]
 tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]});ic=[]
 for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}))
 if tc!=1 or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row048 No Loop No Drift - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}`. Current Rows040-047 show distinct movement without repeated AWS, EC2, mask, coverage, or hydration loops. Active blockers are limited to Row042 expired-auth live proof and Row046’s five preserved worktree paths. Older Depth/Lineart/Flux registry and Row043 artifact blockers are superseded by current governance and pullback evidence.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.

Next: `{NEXT}` blocker/known-issue governance; do not rerun Rows040-048 without changed inputs.""";hyd=PLAN/"Instructions/Hydration_Rehydration"
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"):prepend(hyd/n,block)
 with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Bound current no-loop control to Rows040-047 and advanced to Row049.","; ".join(ep),"20/20 checks; active/superseded blockers separated; no rerun loop",payload["qa_decision"],rel(canonical),f"Advance to {NEXT}."])
 print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
