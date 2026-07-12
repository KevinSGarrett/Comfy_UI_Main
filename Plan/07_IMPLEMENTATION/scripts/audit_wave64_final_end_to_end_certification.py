from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";REL=PLAN/"11_RELEASES";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-060";ITEM="ITEM-W64-060";STATUS="Blocked_Final_End_To_End_Certification_Gates_Not_Met";NEXT="TRK-W64-061 / ITEM-W64-061"
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
 tracker=PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv"
 with tracker.open("r",encoding="utf-8-sig",newline="") as f:rows=[x for x in csv.DictReader(f) if x.get("Wave")=="64"]
 by={x["Tracker_ID"]:x for x in rows};passlike=lambda s:"Passed" in s or "Completed" in s
 pre={"row_count":len(rows),"pass_like_count":sum(passlike(x["Status"]) for x in rows),"blocked_count":sum(x["Status"].startswith("Blocked") for x in rows),"required_count":sum(x["Status"]=="Required_Tracked_Not_Complete_Until_Evidence_Passes" for x in rows)}
 unresolved=[{"tracker_id":x["Tracker_ID"],"workstream":x["Workstream"],"status":x["Status"],"evidence":x["Output_Artifact"]} for x in rows if not passlike(x["Status"])]
 release_files=sorted(p for p in REL.rglob("*") if p.is_file());release_inventory=[{"path":rel(p),"bytes":p.stat().st_size,"sha256":sha(p)} for p in release_files];release_bytes=sum(x["bytes"] for x in release_inventory);release_hash=hashlib.sha256(json.dumps(release_inventory,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 manifest=REL/"WAVE47_SECOND_PASS_COMBINED_RELEASE_MANIFEST.json";m=load(manifest);release_audit=load(QA/"release_done_certification.json");readiness=load(PLAN/"Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.json")
 media_ids=["TRK-W64-019","TRK-W64-020","TRK-W64-021","TRK-W64-022","TRK-W64-023","TRK-W64-024"]
 audio_ids=[f"TRK-W64-{i:03d}" for i in range(25,33)];multimodal_ids=["TRK-W64-033"]
 gates={"all_domain_rows_pass":{"result":"fail","reason_codes":["48_rows_not_pass_like_pre_audit","24_rows_blocked_pre_audit","22_rows_required_pre_audit"]},"media_reviews_pass":{"result":"fail","reason_codes":[by[x]["Status"] for x in media_ids]},"audio_reviews_pass":{"result":"fail","reason_codes":[by[x]["Status"] for x in audio_ids]},"runtime_evidence_pass":{"result":"fail","reason_codes":["final_readiness_inputs_invalid","nine_of_ten_lanes_blocked","runtime_dependent_requirements_unproven"]},"release_manifest_pass":{"result":"fail","reason_codes":["wave47_manifest_historical_waves_38_47_only","runtime_proof_status_unchanged","no_current_wave64_all_pass_manifest"]}}
 checks={"E2E-001_row_count_66":pre["row_count"]==66,"E2E-002_passlike_18":pre["pass_like_count"]==18,"E2E-003_blocked_24":pre["blocked_count"]==24,"E2E-004_required_22":pre["required_count"]==22,"E2E-005_row060_unique":sum(x["Tracker_ID"]==TRK for x in rows)==1,"E2E-006_gate_tuple_exact":set(by[TRK]["Validation_Method"].split("|"))=={"all_domain_rows_pass","media_reviews_pass","audio_reviews_pass","runtime_evidence_pass","release_manifest_pass"},"E2E-007_row060_pre_not_complete":by[TRK]["Status"]=="Required_Tracked_Not_Complete_Until_Evidence_Passes","E2E-008_all_domain_fails":len(unresolved)==48,"E2E-009_video_pipeline_blocked":by["TRK-W64-019"]["Status"].startswith("Blocked"),"E2E-010_video_temporal_blocked":by["TRK-W64-021"]["Status"].startswith("Blocked"),"E2E-011_audio_pipeline_blocked":by["TRK-W64-025"]["Status"].startswith("Blocked"),"E2E-012_audio_strict_blocked":by["TRK-W64-031"]["Status"].startswith("Blocked"),"E2E-013_global_audio_blocked":by["TRK-W64-032"]["Status"].startswith("Blocked"),"E2E-014_multimodal_blocked":by["TRK-W64-033"]["Status"].startswith("Blocked"),"E2E-015_runtime_readiness_fail":str(readiness["result"]).startswith("fail"),"E2E-016_nine_lanes_blocked":readiness["blocked_lane_count"]==9,"E2E-017_release_inventory_93":len(release_inventory)==93,"E2E-018_release_bytes_exact":release_bytes==1335764,"E2E-019_wave47_manifest_historical":m["second_pass_scope"]=="Waves 38-47" and m["runtime_proof_status"]=="unchanged_from_prior_runtime_boundaries","E2E-020_final_fail_closed":all(x["result"]=="fail" for x in gates.values()) and release_audit["final_decision"]=="blocked"}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 canonical=QA/"final_end_to_end_certification.json";stamped=QA/f"FINAL_END_TO_END_CERTIFICATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"final_end_to_end_certification_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-060_final_end_to_end_certification.json"
 payload={"schema_version":"1.0","artifact_type":"final_end_to_end_certification_audit","certification_id":stamped.stem,"created_at":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"row_complete":False,"final_decision":"blocked","certifier":"Codex Desktop autonomous release manager","pre_audit_tracker_state":pre,"post_audit_tracker_state":{"row_count":66,"pass_like_count":18,"blocked_count":25,"required_count":21},"unresolved_domain_rows":unresolved,"required_gates":gates,"release_inventory":{"file_count":len(release_inventory),"total_bytes":release_bytes,"source_tree_sha256":release_hash,"files":release_inventory},"release_manifest":{"path":rel(manifest),"sha256":sha(manifest),"authority":"historical_waves_38_47_only_not_current_wave64_release"},"normalized_blocker_groups":{"domain_rows_unresolved":len(unresolved),"media_rows":media_ids,"audio_rows":audio_ids,"multimodal_rows":multimodal_ids,"runtime_blocked_lanes":readiness["blocked_lane_count"],"release_done_audit":rel(QA/"release_done_certification.json")},"certification_boundary":"No Wave64, full-project, media, audio, runtime, mask, Wave71+, or release certification is granted.","checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"safety_boundary":{"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"generation_executed":False,"release_promoted":False,"mask_or_jira_mutated":False},"next_action":f"Advance with safe local {NEXT} 24/7 operations safety; keep final certification blocked until every domain/media/audio/runtime/release gate passes."}
 evidence_sources=[QA/"release_done_certification.json",QA/"video_pipeline_build.json",QA/"video_temporal_visual_review.json",QA/"audio_pipeline_build.json",QA/"audio_strict_review.json",QA/"global_audio_review_not_local_only.json",QA/"multimodal_cross_review.json",manifest,PLAN/"Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.json"]
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report)]+[rel(p) for p in evidence_sources];payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_at":iso,"tracker_id":TRK,"result":"pass_audit_decision_blocked","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_at":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"final_decision":"blocked","gates":gates,"tracker_state":payload["post_audit_tracker_state"],"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row060 {stamp}: pre 18 pass-like/24 blocked/22 required; post 18/25/21; five end-to-end gates fail; 20/20 audit checks prove blocked decision."
 tags=["wave64_row060_final_audit_current","all_five_e2e_gates_fail_closed","historical_manifest_not_current_release","post_state_18_25_21","advance_safe_row061"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":"final_end_to_end_certification_audit_blocked_all_five_gates","Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")];ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"rows {tc} {ic}")
 block=f"""## Wave64 Row060 Final End-to-End Certification Audit - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}` with final decision `blocked`. The pre-audit Wave64 matrix contained 66 rows: 18 pass-like, 24 blocked, and 22 still requiring direct evidence; after recording this audit it is 18 pass-like, 25 blocked, and 21 required. All five end-to-end gates fail. Video, audio, multimodal, runtime, and current release-manifest proof remain incomplete. The Wave47 manifest is historical Waves38-47 structure with runtime boundaries unchanged, not current Wave64 release authority.

Next safe local action: `{NEXT}` 24/7 operations safety. No release, runtime, mask, Wave71+, or full-project certification occurred.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 with (HYD/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRK,"Ran final end-to-end certification audit against all domain/media/audio/runtime/release gates.","; ".join(ep),"20/20 audit checks; final decision blocked",payload["final_decision"],rel(canonical),f"Begin safe local {NEXT}."])
 print(json.dumps({"status":STATUS,"decision":"blocked","pre":pre,"post":payload["post_audit_tracker_state"],"failed_gates":list(gates),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
