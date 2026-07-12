from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";SRC=PLAN/"15_BLUEPRINT_PROJECTPLAN_COMBINATION";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-058";ITEM="ITEM-W64-058";STATUS="Evidence_Passed_Blueprint_ProjectPlan_Traceability_Runtime_Boundaries_Preserved";NEXT="TRK-W64-059 / ITEM-W64-059"
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
 files=sorted(p for p in SRC.rglob("*") if p.is_file());inventory=[{"path":rel(p),"bytes":p.stat().st_size,"sha256":sha(p)} for p in files];total=sum(x["bytes"] for x in inventory);tree_hash=hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 paths={
  "readme":SRC/"README.md","source_intake":SRC/"WAVE38_SOURCE_INTAKE_AND_CANONICAL_BLUEPRINT_MERGE/wave38_source_intake_records.json","crosswalk":SRC/"WAVE39_BLUEPRINT_TO_SYSTEM_CROSSWALK_AND_GAP_RESOLUTION/wave39_unified_requirement_crosswalk.json","backlog":SRC/"WAVE41_UNIFIED_BACKLOG_AND_WAVE_EXECUTION_CONTRACT/wave41_unified_combined_backlog.json","qa":SRC/"WAVE44_UNIFIED_QA_CERTIFICATION_AND_EVIDENCE_SYSTEM/wave44_unified_qa_certification_packet.json","trace":SRC/"WAVE45_CATALOG_REGISTRY_SEARCH_AND_TRACEABILITY_MERGE/wave45_combined_traceability_index.json","wave47_validation":SRC/"WAVE47_COMBINED_FINAL_HANDOFF_AND_OPERATING_MANUAL/wave47_combined_validation_report.json","authority":SRC/"SECOND_PASS_WAVE38_47_DEEPENING/wave38_second_pass_source_authority_records.json","gaps":SRC/"SECOND_PASS_WAVE38_47_DEEPENING/wave39_second_pass_gap_closure_records.json","trace_quality":SRC/"SECOND_PASS_WAVE38_47_DEEPENING/wave45_second_pass_trace_quality_records.json"}
 source_artifacts=[{"artifact_id":k,"path":rel(p),"sha256":sha(p),"authority":"historical_structural_context_hash_bound_for_row058"} for k,p in paths.items()]
 cross=load(paths["crosswalk"]);backlog=load(paths["backlog"]);trace=load(paths["trace"]);qa=load(paths["qa"]);gaps=load(paths["gaps"])["records"];quality=load(paths["trace_quality"])["records"]
 traces={x["requirement_id"]:x for x in trace["traceability"]};backlogs={x["related_wave"]:x for x in backlog["backlog"]};links=[]
 for c in cross["crosswalk"]:
  waves=c["covered_by_wave"];candidate=[w for w in waves if 38<=w<=47];b=backlogs.get(candidate[0]) if candidate else None;t=traces.get(c["crosswalk_id"]);proof=bool(b and b.get("proof_required")) or c.get("gap_class")=="needs_runtime_proof"
  matches=[]
  for name in c.get("covered_by_artifact",[]):matches += [rel(p) for p in SRC.rglob(Path(name).name)]
  links.append({"crosswalk_id":c["crosswalk_id"],"source_requirement":c["source_requirement"],"source_paths":[rel(paths["crosswalk"]),rel(paths["authority"])],"item_id":ITEM,"tracker_id":TRK,"backlog_id":b.get("backlog_id") if b else None,"trace_id":t.get("trace_id") if t else None,"implementation_artifacts":sorted(set(matches)),"qa_mapping":{"packet":rel(paths["qa"]),"pass_fail_status":qa["pass_fail_status"]},"release_mapping":{"trace_release_decision":t.get("release_decision") if t else None,"decision_boundary":"blocked_until_evidence" if proof else "structure_ready"},"proof_required":proof,"status":"mapped_structure_only_runtime_blocked" if proof else "mapped_structure_ready","blockers":["direct_runtime_evidence_required"] if proof else []})
 registry=PLAN/"10_REGISTRIES/blueprint_projectplan_current_traceability.json";reg={"schema_version":"1.0","registry_id":"blueprint_projectplan_current_traceability","created_iso":iso,"scope_row_id":TRK,"inventory_anchor":{"source_root":rel(SRC),"file_count":len(inventory),"total_bytes":total,"source_tree_sha256":tree_hash,"files":inventory},"source_artifacts":source_artifacts,"requirement_links":links,"historical_boundary":"Wave38-47 pass reports are structural historical context only and cannot prove current Wave64 state without this Row058 hash/evaluator record.","decision":{"traceability_status":"pass","runtime_dependent_links":"blocked_until_evidence","full_release_claimed":False},"fail_closed_rules":["missing_source_or_hash_mismatch","crosswalk_backlog_trace_id_mismatch","proof_required_without_evidence","release_boundary_crossed_without_qa","tracker_or_item_mapping_missing"]};write(registry,reg)
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:tr=[x for x in csv.DictReader(f) if x.get("Tracker_ID")==TRK]
 with (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv").open("r",encoding="utf-8-sig",newline="") as f:it=[x for x in csv.DictReader(f) if x.get("Item_ID")==ITEM]
 ids=[x["crosswalk_id"] for x in links];checks={"BPT-001_source_root_exists":SRC.exists(),"BPT-002_inventory_84":len(inventory)==84,"BPT-003_inventory_bytes":total==92991003,"BPT-004_inventory_hash_complete":all(len(x["sha256"])==64 for x in inventory),"BPT-005_ten_authority_hashes":len(source_artifacts)==10 and all(len(x["sha256"])==64 for x in source_artifacts),"BPT-006_crosswalk_count":cross["crosswalk_count"]==len(cross["crosswalk"])==11,"BPT-007_backlog_count":backlog["backlog_count"]==len(backlog["backlog"])==10,"BPT-008_trace_count":trace["traceability_count"]==len(trace["traceability"])==11,"BPT-009_crosswalk_ids_exact":ids==[f"cw_{i:03d}" for i in range(1,12)] and len(set(ids))==11,"BPT-010_trace_refs_exact":set(traces)==set(ids),"BPT-011_qa_runtime_boundary":qa["pass_fail_status"]=="structure_pass_runtime_evidence_later","BPT-012_cw007_blocked":next(x for x in links if x["crosswalk_id"]=="cw_007")["release_mapping"]["decision_boundary"]=="blocked_until_evidence" and any(x.get("gap_id")=="gap_002" for x in gaps) and any(x.get("trace_id")=="second_pass_trace_002" for x in quality),"BPT-013_no_false_proof_pass":all(x["release_mapping"]["decision_boundary"]=="blocked_until_evidence" for x in links if x["proof_required"]),"BPT-014_tracker_unique":len(tr)==1,"BPT-015_tracker_gate_tuple":set(tr[0]["Validation_Method"].split("|"))=={"source_traceability","items_mapping","tracker_mapping","release_mapping"},"BPT-016_item_unique":len(it)==1,"BPT-017_source_path_normalized":Path(tr[0]["Source_Path"]).resolve()==(SRC/"README.md").resolve(),"BPT-018_release_fail_closed":not reg["decision"]["full_release_claimed"],"BPT-019_blocker_codes_cited":all((not x["proof_required"]) or x["blockers"] for x in links),"BPT-020_deterministic_mapping":len(links)==11 and all(x["item_id"]==ITEM and x["tracker_id"]==TRK and x["trace_id"] for x in links)}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 canonical=QA/"blueprint_projectplan_combination.json";stamped=QA/f"BLUEPRINT_PROJECTPLAN_COMBINATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"blueprint_projectplan_combination_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-058_blueprint_projectplan_combination.json"
 blocked=[x["crosswalk_id"] for x in links if x["proof_required"]];payload={"schema_version":"1.0","evidence_id":stamped.stem,"created_iso":iso,"wave":64,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"row_complete":True,"qa_decision":"blueprint_projectplan_current_traceability_pass_runtime_boundaries_preserved","gates":{"source_traceability":"pass","items_mapping":"pass","tracker_mapping":"pass","release_mapping":"pass_fail_closed"},"registry":{"path":rel(registry),"sha256":sha(registry)},"inventory":{"file_count":len(inventory),"total_bytes":total,"source_tree_sha256":tree_hash},"requirement_link_count":len(links),"runtime_blocked_requirement_ids":blocked,"historical_validation_authority":"structural_context_only_not_current_proof","full_release_claimed":False,"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"safety_boundary":{"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"runtime_proof_claimed":False,"release_promoted":False,"mask_or_jira_mutated":False},"next_action":f"Advance to {NEXT} release/done-certification audit; preserve runtime-proof blocks for {', '.join(blocked)}."}
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report),rel(registry)]+[x["path"] for x in source_artifacts];payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"gates":payload["gates"],"runtime_blocked_requirement_ids":blocked,"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row058 {stamp}: 84-file/11-requirement traceability registry; four gates and 20/20 checks pass; runtime-dependent links {blocked} remain blocked; no release claim."
 tags=["wave64_row058_current_traceability_pass","eleven_requirement_links","historical_pass_not_current_proof","runtime_boundaries_preserved","advance_row059"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")];ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"rows {tc} {ic}")
 block=f"""## Wave64 Row058 Blueprint Project-Plan Traceability - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. A current hash-bound registry covers all 84 combination-layer files and maps all 11 crosswalk requirements to Item, Tracker, implementation, QA, and release-decision surfaces. All four gates and 20 checks pass. Historical Wave38-47 pass reports remain structural context only. Runtime-dependent requirements `{', '.join(blocked)}` remain `blocked_until_evidence`; no runtime or full-release claim occurred.

Next: `{NEXT}` release/done-certification audit.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 with (HYD/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRK,"Implemented current blueprint/project-plan traceability across source, Items, Tracker, QA, implementation, and release decisions.","; ".join(ep),"20/20 checks; runtime boundaries preserved",payload["qa_decision"],rel(canonical),f"Begin {NEXT}."])
 print(json.dumps({"status":STATUS,"files":len(inventory),"requirements":len(links),"runtime_blocked":blocked,"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
