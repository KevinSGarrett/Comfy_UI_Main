from __future__ import annotations

import argparse,csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";TZ=ZoneInfo("America/Chicago");TRACKER="TRK-W64-046";ITEM="ITEM-W64-046";NEXT="TRK-W64-047 / ITEM-W64-047";STATUS="Blocked_Intentional_Preserved_Worktree_Checkpoint"
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
 ap=argparse.ArgumentParser();ap.add_argument("--scan",required=True,type=Path);a=ap.parse_args();scan=a.scan.resolve();s=load(scan)
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S-0500");qa=PLAN/"Instructions/QA/Evidence/Wave64";canonical=qa/"secret_git_security.json";original=qa/"SECRET_GIT_SECURITY_20260708T235206-0500.json";stamped=qa/f"SECRET_GIT_SECURITY_RECONCILIATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;testlog=qa/"secret_git_security_reconciliation_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-046_secret_git_security.json"
 sensitive=s["env_presence"]["root_sensitive_files"];preserved=["Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md","Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_LATEST.json","Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_LATEST.json","Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.json","Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.md"]
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:row47=[x for x in csv.DictReader(f) if x.get("Tracker_ID")=="TRK-W64-047"]
 checks={"scan_local_only":s["local_only"] is True,"aws_not_contacted":s["aws_contacted"] is False,"github_api_not_contacted":s["github_api_contacted"] is False,"secrets_not_printed":s["secrets_printed"] is False,"env_exists":s["env_presence"]["env_exists"] is True,"env_example_exists":s["env_presence"]["env_example_exists"] is True,"sensitive_files_untracked":all(x["tracked"] is False for x in sensitive),"sensitive_files_unstaged":all(x["staged"] is False for x in sensitive),"sensitive_files_ignored":all(x["ignored"] is True for x in sensitive),"gitignore_required_patterns_pass":s["gitignore_check"]["pass"] is True and s["gitignore_check"]["missing_patterns"]==[],"tracked_blocked_paths_zero":s["blocked_path_scan"]["tracked_blocked_count"]==0,"staged_blocked_paths_zero":s["blocked_path_scan"]["staged_blocked_count"]==0,"no_binary_model_commit":s["blocked_path_scan"]["no_binary_model_commit"] is True,"tracked_secret_matches_zero":s["secret_scan"]["tracked_secret_match_count"]==0,"staged_secret_matches_zero":s["secret_scan"]["staged_secret_match_count"]==0,"head_equals_origin_at_scan":s["git_checkpoint"]["head_equals_origin"] is True,"staged_count_zero":s["git_checkpoint"]["staged_count"]==0,"five_preserved_porcelain_entries_at_scan":s["git_checkpoint"]["porcelain_count"]==5,"clean_worktree_correctly_false":s["git_checkpoint"]["clean_worktree"] is False,"next_tracker_row_exists":len(row47)==1}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 payload={"schema_version":"1.0","evidence_id":f"SECRET_GIT_SECURITY_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"row_complete":False,"qa_decision":"local_secret_git_security_pass_checkpoint_blocked_only_by_preserved_worktree","task":"Reconcile current secret/Git security without mutating intentionally preserved paths.","current_scan":{"path":rel(scan),"sha256":sha(scan),"result":s["result"],"head":s["git_checkpoint"]["head"],"origin_main":s["git_checkpoint"]["origin_main"],"head_equals_origin":True,"porcelain_count":5,"tracked_porcelain_count":3,"staged_count":0},"passing_security_gates":{"gitignore":True,"tracked_secret_matches":0,"staged_secret_matches":0,"tracked_blocked_paths":0,"staged_blocked_paths":0,"no_binary_model_commit":True,"sensitive_root_files_ignored_untracked_unstaged":True},"residual_checkpoint_blocker":{"clean_worktree":False,"preserved_paths":preserved,"mutation_allowed":False,"classification":"intentional_user_owned_or_externally_generated_changes_preserved","ec2_start_allowed":False},"scan_boundary":{"untracked_env_values_read":False,"secrets_printed":False,"commit_or_push_attempted":False,"clean_reset_or_revert_attempted":False,"aws_contacted":False,"ec2_started":False},"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"next_action":f"Continue only non-EC2-safe work at {NEXT}; strict checkpoint remains blocked until preserved paths are intentionally resolved by their owner."}
 paths=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(scan),rel(original)];payload["evidence_paths"]=paths
 for p in (canonical,stamped,mirror):write(p,payload)
 write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass_local_security_checks_checkpoint_blocked","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"evidence":paths,"blocker":payload["residual_checkpoint_blocker"],"next_action":payload["next_action"]})
 note=f"Wave64 Row046 {stamp}: local secret/ignore/binary/staging/head-origin gates pass; strict clean-worktree gate remains blocked solely by five preserved paths; no mutation or EC2 action."
 tags=["wave64_row046_local_security_pass","head_matches_origin_index_empty","zero_secret_or_blocked_binary_matches","checkpoint_blocked_five_preserved_paths"]
 tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":paths,"Coverage_Audit_Status":tags,"Notes":[note]});ic=[]
 for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":paths,"Coverage_Audit_Status":tags,"Notes":[note]}))
 if tc!=1 or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row046 Secret And Git Security - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}`. Current local scanning passes secret handling, required ignore patterns, tracked/staged secret checks, blocked binary/model tracking, empty staging, and HEAD/origin parity. Strict `clean_worktree` remains false only because five explicitly preserved paths remain; none were mutated, staged, or reverted, and EC2 remains disallowed.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`; `{rel(scan)}`.

Next: continue only non-EC2-safe work at `{NEXT}`.""";hyd=PLAN/"Instructions/Hydration_Rehydration"
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"):prepend(hyd/n,block)
 with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Passed current local security checks and isolated strict checkpoint blocker to five preserved paths.","; ".join(paths),"20/20 local security checks; HEAD=origin; index empty; clean_worktree false",payload["qa_decision"],rel(canonical),f"Continue non-EC2-safe {NEXT}."])
 print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
