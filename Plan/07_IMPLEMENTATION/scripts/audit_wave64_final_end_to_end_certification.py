from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[3];PLAN=ROOT/"Plan";REL=PLAN/"11_RELEASES";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-060";ITEM="ITEM-W64-060";STATUS="Blocked_Final_End_To_End_Certification_Gates_Not_Met";NEXT="TRK-W64-006 / ITEM-W64-006"
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
def prepend(p,b):
 current=p.read_text(encoding="utf-8-sig").lstrip();marker="## Wave64 Row060 Targeted Final End-to-End Certification Refresh"
 if current.startswith(marker):
  i=current.find("\n## ",len(marker));current=current[i+1:] if i>=0 else ""
 p.write_text(b.strip()+"\n\n"+current,encoding="utf-8")
def main():
 canonical=QA/"final_end_to_end_certification.json";basis="rows019_025_and_row064_current_evidence"
 prior=load(canonical) if canonical.exists() else {}
 baseline_created_at=prior.get("prior_certification_created_at",prior.get("created_at"))
 if prior.get("refresh_basis")==basis:
  iso=prior["created_at"];stamp=prior["certification_id"].removeprefix("FINAL_END_TO_END_CERTIFICATION_")
 else:
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
 direct={f"row{i}":load(QA/name) for i,name in ((61,"autonomous_24_7_operations.json"),(62,"observability_evidence_logs.json"),(63,"failure_classification_rerun.json"),(64,"prompt_negative_prompt_qa.json"),(65,"realvisxl_lane_terminal_state.json"),(66,"future_lane_promotion.json"))}
 current_media_audio_names={19:"video_pipeline_build.json",20:"video_engine_routing.json",21:"video_temporal_visual_review.json",22:"video_reference_input.json",23:"video_frame_repair.json",24:"video_gif_loop_export.json",25:"audio_pipeline_build.json"}
 current_media_audio={f"row{i}":load(QA/name) for i,name in current_media_audio_names.items()}
 gates={"all_domain_rows_pass":{"result":"fail","reason_codes":[f"{len(unresolved)}_rows_not_pass_like_current",f"{pre['blocked_count']}_rows_blocked_current",f"{pre['required_count']}_rows_required_current"]},"media_reviews_pass":{"result":"fail","reason_codes":[by[x]["Status"] for x in media_ids]},"audio_reviews_pass":{"result":"fail","reason_codes":[by[x]["Status"] for x in audio_ids]},"runtime_evidence_pass":{"result":"fail","reason_codes":["final_readiness_inputs_invalid","nine_of_ten_lanes_blocked","row061_live_operations_authority_blocked","row064_prompt_runtime_alignment_blocked","row065_realvisxl_terminal_smoke_scope_only","row066_current_promotion_denied"]},"release_manifest_pass":{"result":"fail","reason_codes":["wave47_manifest_historical_waves_38_47_only","runtime_proof_status_unchanged","no_current_wave64_all_pass_manifest"]}}
 historical_domain=next(x for x in direct["row63"]["failure_ledger"] if x["blocker_id"]=="ROW060_ALL_DOMAIN_ROWS_PASS")
 historical_reconciliation={"historical_evidence":rel(QA/"failure_classification_rerun.json"),"historical_created_iso":direct["row63"]["created_iso"],"historical_unresolved_count":historical_domain["affected_count"],"current_unresolved_count":len(unresolved),"resolved_delta":historical_domain["affected_count"]-len(unresolved),"supersession_rule":"Current Row060 refresh supersedes the aggregate count only; Row063 remains append-only classification evidence and is not rewritten."}
 checks={"E2E-001_row_count_66":pre["row_count"]==66,"E2E-002_passlike_31":pre["pass_like_count"]==31,"E2E-003_blocked_35":pre["blocked_count"]==35,"E2E-004_required_0":pre["required_count"]==0,"E2E-005_row060_unique":sum(x["Tracker_ID"]==TRK for x in rows)==1,"E2E-006_gate_tuple_exact":set(by[TRK]["Validation_Method"].split("|"))=={"all_domain_rows_pass","media_reviews_pass","audio_reviews_pass","runtime_evidence_pass","release_manifest_pass"},"E2E-007_row060_current_blocked":by[TRK]["Status"]==STATUS,"E2E-008_all_domain_fails_35":len(unresolved)==35,"E2E-009_video_pipeline_blocked":by["TRK-W64-019"]["Status"].startswith("Blocked"),"E2E-010_audio_pipeline_blocked":by["TRK-W64-025"]["Status"].startswith("Blocked"),"E2E-011_multimodal_blocked":by["TRK-W64-033"]["Status"].startswith("Blocked"),"E2E-012_row061_direct_blocked":direct["row61"]["row_complete"] is False and by["TRK-W64-061"]["Status"].startswith("Blocked"),"E2E-013_row062_direct_blocked":direct["row62"]["row_complete"] is False and by["TRK-W64-062"]["Status"].startswith("Blocked"),"E2E-014_historical_48_to_current_35_reconciled":historical_reconciliation["historical_unresolved_count"]==48 and historical_reconciliation["current_unresolved_count"]==35 and historical_reconciliation["resolved_delta"]==13,"E2E-015_row064_direct_blocked":direct["row64"]["row_complete"] is False and by["TRK-W64-064"]["Status"].startswith("Blocked"),"E2E-016_runtime_readiness_exact_failure":readiness["result"]=="fail_final_certification_readiness_inputs_invalid" and readiness["blocked_lane_count"]==9 and readiness["final_ready_lane_count"]==1,"E2E-017_release_inventory_93":len(release_inventory)==93,"E2E-018_release_bytes_exact":release_bytes==1335764,"E2E-019_wave47_manifest_historical":m["second_pass_scope"]=="Waves 38-47" and m["runtime_proof_status"]=="unchanged_from_prior_runtime_boundaries","E2E-020_final_fail_closed":all(x["result"]=="fail" for x in gates.values()) and release_audit["final_decision"]=="blocked","E2E-021_rows019_025_direct_status_bound":all(current_media_audio[f"row{i}"]["tracker_id"]==f"TRK-W64-{i:03d}" and current_media_audio[f"row{i}"]["status_decision"]==by[f"TRK-W64-{i:03d}"]["Status"] for i in current_media_audio_names),"E2E-022_row064_post_snapshot_consumed":bool(baseline_created_at) and datetime.fromisoformat(direct["row64"]["created_iso"])>datetime.fromisoformat(baseline_created_at),"E2E-023_row065_scope_limited":direct["row65"]["row_complete"] is True and direct["row65"]["qa_decision"]=="terminal_runtime_smoke_chain_pass_reuse_required_scope_limited" and len(direct["row65"]["scope_limitations"])>=2,"E2E-024_row066_current_promotion_denied":direct["row66"]["row_complete"] is True and direct["row66"]["qa_decision"]=="promotion_control_pass_current_promotion_denied_no_request" and direct["row66"]["current_promotion_state"]["promotion_allowed"] is False and direct["row66"]["current_promotion_state"]["promoted_lane_count"]==0}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 stamped=QA/f"FINAL_END_TO_END_CERTIFICATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"final_end_to_end_certification_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-060_final_end_to_end_certification.json"
 payload={"schema_version":"1.0","artifact_type":"final_end_to_end_certification_audit","certification_id":stamped.stem,"created_at":iso,"refresh_basis":basis,"prior_certification_created_at":baseline_created_at,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"row_complete":False,"final_decision":"blocked","certifier":"Codex Desktop autonomous release manager","pre_audit_tracker_state":pre,"post_audit_tracker_state":None,"unresolved_domain_rows":unresolved,"required_gates":gates,"direct_row019_025_statuses":{x:current_media_audio[x]["status_decision"] for x in current_media_audio},"direct_row019_025_timestamps":{x:current_media_audio[x].get("timestamp",current_media_audio[x].get("created_at")) for x in current_media_audio},"direct_row061_066_statuses":{x:direct[x]["status"] for x in direct},"historical_snapshot_reconciliation":historical_reconciliation,"release_inventory":{"file_count":len(release_inventory),"total_bytes":release_bytes,"source_tree_sha256":release_hash,"files":release_inventory},"release_manifest":{"path":rel(manifest),"sha256":sha(manifest),"authority":"historical_waves_38_47_only_not_current_wave64_release"},"normalized_blocker_groups":{"domain_rows_unresolved":len(unresolved),"media_rows":media_ids,"audio_rows":audio_ids,"multimodal_rows":multimodal_ids,"runtime_blocked_lanes":readiness["blocked_lane_count"],"release_done_audit":rel(QA/"release_done_certification.json")},"certification_boundary":"No Wave64, full-project, media, audio, runtime, mask, Wave71+, or release certification is granted.","checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":len(checks),"passed":len(checks),"failed":0},"safety_boundary":{"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"generation_executed":False,"release_promoted":False,"mask_or_jira_mutated":False},"next_action":f"Advance in strict sequence to {NEXT} project-control autonomy; keep final certification blocked until every domain/media/audio/runtime/release gate passes."}
 evidence_sources=[QA/"release_done_certification.json"]+[QA/name for name in current_media_audio_names.values()]+[QA/name for name in ("audio_engine_routing.json","audio_voice_dialogue.json","audio_foley_force.json","audio_spatial_room.json","audio_av_sync.json","audio_strict_review.json","global_audio_review_not_local_only.json","multimodal_cross_review.json")]+[manifest,PLAN/"Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.json"]+[QA/name for name in ("autonomous_24_7_operations.json","observability_evidence_logs.json","failure_classification_rerun.json","prompt_negative_prompt_qa.json","realvisxl_lane_terminal_state.json","future_lane_promotion.json")]
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report)]+[rel(p) for p in evidence_sources];payload["evidence_paths"]=ep
 note=f"Wave64 Row060 targeted refresh {stamp}: current 31 pass-like/35 blocked/0 required; 35 unresolved; current Row019-025 and post-snapshot Row064 evidence consumed; five end-to-end gates fail; 25/25 checks prove blocked decision."
 tags=["wave64_row060_targeted_refresh_current","rows019_025_and_row064_current_evidence_consumed","all_five_e2e_gates_fail_closed","historical_manifest_not_current_release","current_state_31_35_0","advance_row006"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":"final_end_to_end_certification_audit_blocked_all_five_gates","Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")];ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"rows {tc} {ic}")
 post_states=[]
 for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv"):
  with p.open("r",encoding="utf-8-sig",newline="") as f:post_rows=[x for x in csv.DictReader(f) if x.get("Wave")=="64"]
  post_states.append({"row_count":len(post_rows),"pass_like_count":sum(passlike(x["Status"]) for x in post_rows),"blocked_count":sum(x["Status"].startswith("Blocked") for x in post_rows),"required_count":sum(x["Status"]=="Required_Tracked_Not_Complete_Until_Evidence_Passes" for x in post_rows)})
 if post_states!=[pre,pre]:raise SystemExit(f"post-state mismatch: {post_states} != {pre}")
 checks["E2E-025_post_write_tracker_state_verified"]=True
 payload["post_audit_tracker_state"]=post_states[0];payload["checks"]=[{"name":k,"result":"pass"} for k in checks];payload["check_summary"]={"checked":len(checks),"passed":len(checks),"failed":0}
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_at":iso,"tracker_id":TRK,"result":"pass_audit_decision_blocked","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_at":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"final_decision":"blocked","gates":gates,"tracker_state":payload["post_audit_tracker_state"],"evidence":ep,"next_action":payload["next_action"]})
 block=f"""## Wave64 Row060 Targeted Final End-to-End Certification Refresh - {iso}

`{TRK}` / `{ITEM}` remains `{STATUS}` with final decision `blocked`. The targeted refresh consumed the current direct Row019-025 artifacts plus the Row064 prompt/runtime evidence that postdates the prior Row060 snapshot, and measured the current 66-row matrix at 31 pass-like, 35 blocked, and zero merely-required rows, leaving 35 unresolved rows. Row063's historical classification ledger correctly retains its creation-time count of 48; this refresh supersedes that aggregate count with 35 after 13 rows gained direct pass-like evidence, without rewriting historical evidence. All five end-to-end gates still fail. Video, audio, multimodal, live operations, prompt/runtime alignment, and current release-manifest proof remain incomplete. Row065 proves one RealVisXL terminal smoke chain only; Row066 proves promotion control while authorizing zero promotions. The Wave47 manifest remains historical Waves38-47 structure, not current Wave64 release authority.

Next safe local action in strict sequence: `{NEXT}` project-control autonomy. No release, runtime, mask, Wave71+, or full-project certification occurred.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 proof=HYD/"PROOF_OF_MOVEMENT_LOG.csv";action=f"Refreshed final end-to-end certification for {basis}."
 with proof.open("r",encoding="utf-8-sig",newline="") as f:reader=csv.DictReader(f);proof_fields=reader.fieldnames or [];proof_rows=list(reader)
 matches=[r for r in proof_rows if r.get("Task")==TRK and r.get("Action")==action]
 if len(matches)>1:raise SystemExit(f"duplicate proof rows for {action}")
 proof_record={"Timestamp":iso,"Wave":"64","Task":TRK,"Action":action,"Files_Changed":"; ".join(ep),"Validation_Run":"25/25 audit checks; current 31/35/0; final decision blocked","Result":payload["final_decision"],"Evidence_Path":rel(canonical),"Next_Action":f"Begin {NEXT}."}
 if matches:matches[0].update(proof_record)
 else:proof_rows.append(proof_record)
 with proof.open("w",encoding="utf-8",newline="") as f:writer=csv.DictWriter(f,fieldnames=proof_fields,lineterminator="\n");writer.writeheader();writer.writerows(proof_rows)
 print(json.dumps({"status":STATUS,"decision":"blocked","pre":pre,"post":payload["post_audit_tracker_state"],"failed_gates":list(gates),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
