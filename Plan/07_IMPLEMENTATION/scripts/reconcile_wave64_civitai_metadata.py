from __future__ import annotations

import csv, hashlib, json, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(r"C:\Comfy_UI_Main"); PLAN=ROOT/"Plan"; TZ=ZoneInfo("America/Chicago")
TRACKER="TRK-W64-045";ITEM="ITEM-W64-045";NEXT="TRK-W64-046 / ITEM-W64-046";STATUS="Completed_Local_Civitai_Metadata_Provenance_Pass"
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
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S-0500")
 qa=PLAN/"Instructions/QA/Evidence/Wave64";canonical=qa/"civitai_metadata.json";original=qa/"CIVITAI_METADATA_20260708T234544-0500.json";stamped=qa/f"CIVITAI_METADATA_RECONCILIATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;testlog=qa/"civitai_metadata_reconciliation_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-045_civitai_metadata.json"
 registry=PLAN/"Registries/Models/model_registry.jsonl";summary=PLAN/"Instructions/QA/Evidence/Model_Registry/W64_CIVITAI_REALVISXL_DETAIL_SUMMARY_20260708T234347-0500.json";model=PLAN/"Instructions/QA/Evidence/Model_Registry/W64_CIVITAI_MODEL_139562_CLEAN_20260708T234347-0500.json";version=PLAN/"Instructions/QA/Evidence/Model_Registry/W64_CIVITAI_MODEL_VERSION_789646_CLEAN_20260708T234347-0500.json";protocol=PLAN/"Instructions/Operations/CIVITAI_API_OPERATING_PROTOCOL.md";lookup=PLAN/"Instructions/Operations/Scripts/Invoke-CivitaiModelLookup.ps1"
 old=load(original);detail=load(summary);ver=load(version);records=[json.loads(x) for x in registry.read_text(encoding="utf-8-sig").splitlines() if x.strip()];civ=[x for x in records if x.get("source")=="civitai"];other=[x for x in records if x.get("source")!="civitai"]
 expected={"source_model_id":"139562","source_model_version_id":"789646","source_url":"https://civitai.com/models/139562?modelVersionId=789646","file_name":"realvisxlV50_v50Bakedvae.safetensors","sha256":"6a35a7855770ae9820a3c931d4964c3817b6d9e3c6f9c4dabb5b3a94e5643b80"}
 tuple_match=all(all(str(x.get(k,"" )).lower()==v.lower() for k,v in expected.items()) for x in civ)
 query=PLAN/"Instructions/QA/Evidence/Model_Registry/W64_CIVITAI_REALVISXL_QUERY_20260708T234325-0500.json";scanned_evidence=(original,summary,model,version,query)
 clean_text="\n".join(p.read_text(encoding="utf-8-sig",errors="replace") for p in scanned_evidence)
 secret_patterns={"authorization_bearer":r"(?i)authorization\s*[:=]\s*[\"']?bearer\s+[a-z0-9._-]{12,}","civitai_token_assignment":r"(?i)civitai[_-]?(?:api[_-]?)?(?:key|token)\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']","api_key_query_parameter":r"(?i)[?&](?:api[_-]?key|token)=[a-z0-9._-]{8,}","generic_secret_assignment":r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*[\"'][^\"'\r\n]{12,}[\"']"}
 secret_findings={name:len(re.findall(pattern,clean_text)) for name,pattern in secret_patterns.items()}
 primary=next(x for x in ver.get("files",[]) if x.get("primary") is True)
 with (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv").open("r",encoding="utf-8-sig",newline="") as f:next_rows=[x for x in csv.DictReader(f) if x.get("Tracker_ID")=="TRK-W64-046"]
 clean_model_match=str(detail.get("model_id"))=="139562";clean_version_match=str(detail.get("version_id"))=="789646";clean_file_match=primary.get("name")==expected["file_name"];clean_sha_match=primary.get("hashes",{}).get("SHA256","").lower()==expected["sha256"]
 provenance_drift=(len(records)!=15 or len(civ)!=7 or len(other)!=8 or not tuple_match or not clean_model_match or not clean_version_match or not clean_file_match or not clean_sha_match)
 checks={"registry_count_15":len(records)==15,"civitai_record_count_7":len(civ)==7,"non_civitai_record_count_8":len(other)==8,"non_civitai_sources_scoped_out":set(x.get("source") for x in other).issubset({"github","huggingface"}),"all_civitai_records_realvisxl":all(x.get("model_name")=="RealVisXL V5.0" for x in civ),"registry_tuple_matches":tuple_match,"clean_model_id_matches":clean_model_match,"clean_version_id_matches":clean_version_match,"clean_file_name_matches":clean_file_match,"clean_sha_matches":clean_sha_match,"source_url_recorded":all(bool(x.get("source_url")) for x in civ),"download_url_metadata_present":old["metadata_match"]["download_url_present"] is True,"scanned_evidence_no_authorization_bearer":secret_findings["authorization_bearer"]==0,"scanned_evidence_no_token_or_key_assignment":sum(secret_findings.values())==0,"scanned_evidence_set_complete":len(scanned_evidence)==5 and all(p.exists() for p in scanned_evidence),"no_binary_download_by_row":old["download_boundary"]["model_binary_downloaded_by_this_row"] is False,"no_unsafe_binary_commit":old["download_boundary"]["unsafe_model_binary_committed"] is False,"live_lookup_not_required_without_drift":not provenance_drift,"no_external_runtime_action":old["runtime_boundary"]["ec2_started"] is False and old["runtime_boundary"]["generation_executed"] is False,"next_tracker_row_exists":len(next_rows)==1}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 payload={"schema_version":"1.0","evidence_id":f"CIVITAI_METADATA_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"row_complete":True,"qa_decision":"civitai_metadata_current_registry_provenance_pass_no_rerun","task":"Reconcile Civitai provenance against the current 15-record registry without duplicate live lookup.","registry_scope":{"total_records":15,"civitai_records":7,"non_civitai_records":8,"non_civitai_sources":["github","huggingface"],"civitai_tuple":expected,"mismatches":[]},"clean_evidence":{"summary":rel(summary),"model":rel(model),"version":rel(version),"query":rel(query),"scanned_paths":[rel(p) for p in scanned_evidence],"primary_file_name":primary["name"],"primary_sha256":primary["hashes"]["SHA256"],"secret_findings":secret_findings,"secret_markers_found":sum(secret_findings.values()),"token_value_read_or_printed":False},"rerun_decision":{"live_civitai_lookup":False,"reason":"Current seven-record tuple matches clean evidence with no provenance or secret-safety drift.","trigger":"Rerun only if Civitai count or model/version/file/hash tuple changes, or new evidence regresses secret safety."},"boundaries":{"network_contacted":False,"token_accessed":False,"binary_downloaded":False,"ec2_started":False,"generation_executed":False,"masks_or_wave_gates_touched":False,"jira_mutated":False},"source_hashes":[{"path":rel(x),"sha256":sha(x)} for x in (registry,summary,model,version,query,protocol,lookup)],"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"next_action":f"Advance to {NEXT}; preserve this provenance evidence unless the source tuple changes."}
 paths=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(original),rel(summary),rel(model),rel(version),rel(registry)];payload["evidence_paths"]=paths
 for p in (canonical,stamped,mirror):write(p,payload)
 write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"evidence":paths,"rerun_decision":payload["rerun_decision"],"next_action":payload["next_action"]})
 note=f"Wave64 Row045 {stamp}: 7/15 Civitai records match RealVisXL model/version/file/hash clean evidence; 8 GitHub/Hugging Face records scoped out; zero secret markers; no live lookup."
 tags=["wave64_row045_civitai_provenance_pass","seven_civitai_records_exact_tuple","secret_safe_no_live_lookup","non_civitai_sources_scoped_out"]
 tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":paths,"Coverage_Audit_Status":tags,"Notes":[note]});ic=[]
 for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"):ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":paths,"Coverage_Audit_Status":tags,"Notes":[note]}))
 if tc!=1 or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row045 Civitai Provenance - {iso}

`{TRACKER}` / `{ITEM}` is `{STATUS}`. The current 15-record registry contains seven Civitai-backed RealVisXL records; all seven match model `139562`, version `789646`, the expected checkpoint filename, source URL, and SHA256. Eight GitHub/Hugging Face records are correctly outside Civitai scope. Clean evidence contains no secret markers, and no token or network lookup was used.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`; `{rel(summary)}`.

Next: `{NEXT}`; rerun Civitai only if the source tuple or secret-safety evidence changes.""";hyd=PLAN/"Instructions/Hydration_Rehydration"
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"):prepend(hyd/n,block)
 with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Reconciled current Civitai provenance without live lookup or token access.","; ".join(paths),"20/20 checks; 7 Civitai exact tuple; 8 non-Civitai scoped out; secret-clean",payload["qa_decision"],rel(canonical),f"Advance to {NEXT}."])
 print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
