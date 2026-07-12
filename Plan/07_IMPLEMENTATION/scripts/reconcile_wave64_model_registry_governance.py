from __future__ import annotations

import argparse, csv, hashlib, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(r"C:\Comfy_UI_Main"); PLAN=ROOT/"Plan"; TZ=ZoneInfo("America/Chicago")
TRACKER="TRK-W64-044"; ITEM="ITEM-W64-044"; NEXT="TRK-W64-045 / ITEM-W64-045"; STATUS="Completed_Local_Model_Registry_Governance_Pass"
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
 ap=argparse.ArgumentParser();ap.add_argument("--coverage",required=True,type=Path);a=ap.parse_args();coverage=a.coverage.resolve()
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S-0500")
 qa=PLAN/"Instructions/QA/Evidence/Wave64";canonical=qa/"model_registry_governance.json";original=qa/"MODEL_REGISTRY_GOVERNANCE_20260708T234222-0500.json";stamped=qa/f"MODEL_REGISTRY_GOVERNANCE_RECONCILIATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;testlog=qa/"model_registry_governance_reconciliation_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-044_model_registry_governance.json"
 registry=PLAN/"Registries/Models/model_registry.jsonl";queue=PLAN/"Registries/Models/model_runtime_validation_queue.csv";validator=PLAN/"Instructions/QA/Scripts/Test-WorkflowModelRegistryCoverage.ps1";alignment=PLAN/"07_IMPLEMENTATION/scripts/implement_wave64_model_registry_current_alignment.py"
 c=load(coverage);records=[json.loads(x) for x in registry.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
 with queue.open("r",encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 flux=[x for x in records if x.get("workflow_lane")=="flux1_dev_primary_base"];fluxq=[x for x in rows if x.get("workflow_lane")=="flux1_dev_primary_base"]
 target=[x for x in records if x.get("workflow_lane") in ("sdxl_realvisxl_controlnet_depth_lane","sdxl_realvisxl_controlnet_lineart_lane")];targetq=[x for x in rows if x.get("workflow_lane") in ("sdxl_realvisxl_controlnet_depth_lane","sdxl_realvisxl_controlnet_lineart_lane")]
 if len(flux)!=1 or len(fluxq)!=1:raise SystemExit(f"Flux cardinality mismatch: registry={len(flux)}, queue={len(fluxq)}")
 tracker_path=PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv"
 with tracker_path.open("r",encoding="utf-8-sig",newline="") as f:tracker_rows=list(csv.DictReader(f))
 row45=[x for x in tracker_rows if x.get("Tracker_ID")=="TRK-W64-045"]
 coverage_local_only=(c.get("local_only") is True and c.get("aws_contacted") is False and c.get("github_api_contacted") is False and c.get("comfyui_contacted") is False and c.get("ec2_started") is False and c.get("generation_executed") is False)
 checks={"coverage_pass":c.get("result")=="pass_local_only","coverage_zero_failures":c.get("failed_check_count")==0,"registry_count_15":c.get("registry_record_count")==15==len(records),"queue_count_15":c.get("runtime_validation_queue_row_count")==15==len(rows),"lane_count_10":c.get("workflow_runtime_lane_count")==10,"all_lanes_pass":all(x.get("result")=="pass" for x in c.get("lane_results",[])),"flux_single_registry_record":len(flux)==1,"flux_single_queue_row":len(fluxq)==1,"flux_registry_queued":flux[0].get("runtime_validation_status")=="queued","flux_queue_queued":fluxq[0].get("status")=="queued","flux_not_installed":flux[0].get("storage_location")=="not_installed_license_acceptance_pending","flux_license_not_asserted":any("not asserted" in x for x in flux[0].get("known_issues",[])),"flux_promotion_prohibited":any("Promotion is prohibited" in x for x in flux[0].get("known_issues",[])),"flux_local_binary_absent":not (ROOT/flux[0]["local_path"]).exists(),"depth_lineart_four_records":len(target)==4,"depth_lineart_registry_runtime_complete":all(x.get("runtime_validation_status")=="runtime_smoke_complete" for x in target),"depth_lineart_four_queue_rows":len(targetq)==4,"depth_lineart_queue_runtime_complete":all(x.get("status")=="runtime_smoke_complete" for x in targetq),"coverage_proves_no_external_runtime_action":coverage_local_only,"next_tracker_row_exists":len(row45)==1 and row45[0].get("Workstream")=="civitai_metadata"}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 payload={"schema_version":"1.0","evidence_id":f"MODEL_REGISTRY_GOVERNANCE_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"row_complete":True,"qa_decision":"model_registry_governance_current_15_record_10_lane_pass_local_only","task":"Align current model registry governance with proven runtime lanes and fail-closed Flux authority.","coverage":{"path":rel(coverage),"sha256":sha(coverage),"result":c["result"],"failed_check_count":0,"registry_record_count":15,"runtime_validation_queue_row_count":15,"workflow_runtime_lane_count":10},"changes":{"depth_lineart_registry_records_promoted_to_target_runtime_vocabulary":4,"depth_lineart_queue_rows_promoted":4,"flux_fail_closed_registry_records_added":1,"flux_queued_validation_rows_added":1,"validator_lane_classifier_hardened":True,"verified_ec2_static_match_synonym_supported":True},"flux_boundary":{"registered":True,"installed":False,"license_acceptance_asserted":False,"runtime_proof":False,"promotion_allowed":False,"required_next":"Explicit noncommercial license acceptance, hash-verified install, model load, generation, technical QA, and visual QA."},"scope":{"local_only":True,"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"generation_executed":False,"masks_or_wave_gates_touched":False,"jira_mutated":False},"source_hashes":[{"path":rel(x),"sha256":sha(x)} for x in (registry,queue,validator,alignment)],"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"next_action":f"Advance to {NEXT} Civitai metadata/provenance duplicate-check; do not install Flux without explicit license acceptance."}
 paths=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(coverage),rel(registry),rel(queue),rel(validator)];payload["evidence_paths"]=paths
 for p in (canonical,stamped,mirror):write(p,payload)
 write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"evidence":paths,"flux_boundary":payload["flux_boundary"],"next_action":payload["next_action"]})
 note=f"Wave64 Row044 {stamp}: current coverage pass_local_only; 15 registry/15 queue/10 lanes/0 failures; Depth/Lineart target-runtime aligned; Flux registered queued and uninstalled behind license gate."
 tags=["wave64_row044_current_governance_pass","registry_15_queue_15_lanes_10","flux_fail_closed_license_pending","no_runtime_or_promotion"]
 tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":paths,"Coverage_Audit_Status":tags,"Notes":[note]});ic=[]
 for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":paths,"Coverage_Audit_Status":tags,"Notes":[note]}))
 if tc!=1 or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row044 Model Registry Governance - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}`. Current coverage is `pass_local_only`: 15 registry records, 15 validation rows, 10 lanes, zero failed checks. Depth/Lineart target-runtime records are aligned. Flux has a fail-closed authority record and queued validation row, but remains uninstalled and unpromoted; license acceptance is not asserted.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`; `{rel(coverage)}`.

Next: `{NEXT}` Civitai metadata/provenance duplicate-check; do not install Flux without explicit license acceptance.""";hyd=PLAN/"Instructions/Hydration_Rehydration"
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"):prepend(hyd/n,block)
 with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Aligned current registry governance and passed all ten lanes locally.","; ".join(paths),"20/20 checks; 15 registry; 15 queue; 10 lanes; Flux fail-closed",payload["qa_decision"],rel(canonical),f"Advance to {NEXT}."])
 print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
