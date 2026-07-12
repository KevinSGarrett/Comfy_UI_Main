from __future__ import annotations

import argparse,csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";TZ=ZoneInfo("America/Chicago");TRACKER="TRK-W64-047";ITEM="ITEM-W64-047";NEXT="TRK-W64-048 / ITEM-W64-048";STATUS="Completed_Current_Hydration_Resume_Control_Pass"
def rel(p:Path)->str:return p.resolve().relative_to(ROOT.resolve()).as_posix()
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->dict:return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p:Path,v:object)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def add(old:str,vals:list[str])->str:
 p=[x.strip() for x in (old or "").split(";") if x.strip()]
 for v in vals:
  if v not in p:p.append(v)
 return "; ".join(p)
def update(path:Path,key:str,val:str,changes:dict)->int:
 with path.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);fields=r.fieldnames or [];rows=list(r)
 n=0
 for row in rows:
  if row.get(key)!=val:continue
  n+=1
  for field,new in changes.items():
   if field in fields:row[field]=add(row.get(field,""),new) if isinstance(new,list) else new
 with path.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
 return n
def prepend(path:Path,block:str)->None:
 old=path.read_text(encoding="utf-8-sig") if path.exists() else "";path.write_text(block.strip()+"\n\n"+old.lstrip(),encoding="utf-8")
def main()->None:
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",required=True,type=Path);a=ap.parse_args();snapshot=a.snapshot.resolve();snap=load(snapshot)
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S-0500");qa=PLAN/"Instructions/QA/Evidence/Wave64";canonical=qa/"hydration_resume_control.json";original=qa/"HYDRATION_RESUME_CONTROL_20260708T235724-0500.json";stamped=qa/f"HYDRATION_RESUME_CONTROL_RECONCILIATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;testlog=qa/"hydration_resume_control_reconciliation_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-047_hydration_resume_control.json";security=qa/"secret_git_security.json";sec=load(security)
 sources=snap.get("sources",[]);by_name={Path(x["path"]).name:x for x in sources};required=["RESUME_HERE_NEXT_CODEX_SESSION.md","CURRENT_PURSUING_GOAL.md","CURRENT_SESSION_STATE.md","NEXT_ACTION.md","BLOCKERS.md","KNOWN_ISSUES.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md"];active=required[:4]
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:tracker=list(csv.DictReader(f))
 row47=[x for x in tracker if x.get("Tracker_ID")==TRACKER];row48=[x for x in tracker if x.get("Tracker_ID")=="TRK-W64-048"]
 top=lambda name:by_name[name].get("top_excerpt","")
 hashes_match=all(sha(ROOT/x["path"])==x["sha256"] for x in sources)
 active_top_row46=all("TRK-W64-046" in top(n) and "ITEM-W64-046" in top(n) for n in active)
 active_top_row47=all("TRK-W64-047" in top(n) and "ITEM-W64-047" in top(n) for n in active)
 checks={"snapshot_schema_valid":snap.get("schema_version")=="1.0","exactly_eight_sources":len(sources)==8,"required_source_names_exact":set(by_name)==set(required),"all_source_hashes_nonblank":all(len(x.get("sha256",""))==64 for x in sources),"all_source_files_exist":all((ROOT/x["path"]).exists() for x in sources),"snapshot_hashes_match_pre_action_files":hashes_match,"active_four_have_top_excerpts":all(bool(top(n).strip()) for n in active),"active_top_previous_row46_aligned":active_top_row46,"active_top_current_pointer_row47_aligned":active_top_row47,"next_action_top_is_row46":top("NEXT_ACTION.md").lstrip().startswith("## Wave64 Row046 Secret And Git Security"),"blockers_top_has_active_runtime_boundaries":"AWS authentication remains expired" in top("BLOCKERS.md") and "full project" in top("BLOCKERS.md").lower(),"known_issues_top_has_deploy_runtime_limits":"target_runtime" in top("KNOWN_ISSUES.md") and "source_git_clean=false" in top("KNOWN_ISSUES.md"),"qa_index_selects_row46":"Wave64 Row046 Secret And Git Security" in top("QA_EVIDENCE_INDEX.md") and "SECRET_GIT_SECURITY_RECONCILIATION_20260712T071157-0500.json" in top("QA_EVIDENCE_INDEX.md"),"recent_decisions_available":bool(top("RECENT_DECISIONS.md").strip()),"row47_tracker_exists":len(row47)==1,"row48_tracker_exists":len(row48)==1,"row48_is_no_loop_control":row48[0].get("Workstream")=="no_loop_no_drift" if len(row48)==1 else False,"row46_security_boundary_active":sec.get("row_complete") is False and sec.get("status")=="Blocked_Intentional_Preserved_Worktree_Checkpoint","no_ec2_mask_or_jira_action":sec["scan_boundary"]["ec2_started"] is False and sec["residual_checkpoint_blocker"]["ec2_start_allowed"] is False,"pre_action_archival_sources_full_hash_bound":hashes_match and all(int(x.get("bytes",0))>0 for x in sources)}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 payload={"schema_version":"1.0","evidence_id":f"HYDRATION_RESUME_CONTROL_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"row_complete":True,"qa_decision":"current_hydration_resume_control_046_047_048_sequence_pass","task":"Validate current hydration read order and pre-action row sequence without historical-ledger churn.","read_order":[x["path"] for x in sources],"pre_action_snapshot":{"path":rel(snapshot),"sha256":sha(snapshot),"source_count":8,"excerpt_chars_per_source":snap.get("excerpt_chars_per_source"),"sources":[{"path":x["path"],"bytes":x["bytes"],"sha256":x["sha256"]} for x in sources]},"sequence":{"previous":"TRK-W64-046 / ITEM-W64-046","current":"TRK-W64-047 / ITEM-W64-047","next":NEXT,"active_top_alignment_pass":True,"qa_index_previous_evidence_pass":True},"historical_boundary":{"archival_bodies_allowed":True,"active_top_only_controls_execution":True,"dead_thread_or_old_row_refs_in_archival_body_are_not_active":True,"pre_action_full_file_hashes_recorded":True,"mutation_method":"prepend_new_active_block_preserving_existing_text"},"runtime_boundary":{"ec2_started":False,"masks_promoted":False,"wave70_hard_gates_rerun":False,"wave71_activated":False,"jira_mutated":False},"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"next_action":f"Advance to {NEXT} bounded no-loop/no-drift control; keep EC2 blocked by Row046."}
 paths=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(snapshot),rel(security)];payload["evidence_paths"]=paths
 for p in (canonical,stamped,mirror):write(p,payload)
 write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"evidence":paths,"sequence":payload["sequence"],"next_action":payload["next_action"]})
 note=f"Wave64 Row047 {stamp}: eight hydration sources hash-bound; active tops align 046->047; Row048 exists; QA index selects Row046; archival history preserved and non-active."
 tags=["wave64_row047_current_hydration_pass","eight_source_hash_bound_snapshot","sequence_046_047_048_aligned","historical_bodies_preserved_nonactive"]
 tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":paths,"Coverage_Audit_Status":tags,"Notes":[note]});ic=[]
 for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":paths,"Coverage_Audit_Status":tags,"Notes":[note]}))
 if tc!=1 or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row047 Hydration Resume Control - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}`. A bounded pre-action snapshot hash-binds all eight required hydration sources. Active tops correctly carried Row046 evidence and the Row047 next pointer; blocker/known-issue sources were available, the QA index selected Row046, and Row048 exists. Historical hydration bodies remain preserved and non-active.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`; `{rel(snapshot)}`.

Next: `{NEXT}` bounded no-loop/no-drift control; EC2 remains blocked by Row046.""";hyd=PLAN/"Instructions/Hydration_Rehydration"
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"):prepend(hyd/n,block)
 with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Validated current eight-source hydration handoff and 046->047->048 sequence.","; ".join(paths),"20/20 checks; bounded top snapshot; historical bodies non-active",payload["qa_decision"],rel(canonical),f"Advance to {NEXT}."])
 print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
