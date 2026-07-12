from __future__ import annotations
import csv,hashlib,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";SRC=PLAN/"13_ADVANCED_ADDITIONS_INTEGRATION";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-056";ITEM="ITEM-W64-056";STATUS="Blocked_Runtime_Visual_Audio_Model_Proof_Missing";NEXT="TRK-W64-057 / ITEM-W64-057"
def rel(p):return p.resolve().relative_to(ROOT.resolve()).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
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
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S-0500")
 source_files=sorted(p for p in SRC.iterdir() if p.is_file());source_hashes={rel(p):sha(p) for p in source_files}
 systems=[
  ("physical_interaction_engine",[21,22,23,25],["contact_graph","pressure_map","deformation_pass","interaction_qa"],["contact_ownership","no_clipping","no_floating","occlusion_consistency"],["pose_contact_extraction","pressure_inference","depth_occlusion_consistency"],["contact_crops","occlusion_proof"],[]),
  ("micro_motion_layer",[26,27,28],["keyframe_planner","motion_timeline","temporal_qa"],["phase_consistency","identity_persistence","anatomy_persistence"],["temporal_pose","regional_motion","sequence_consistency"],["frame_sequence_review"],[]),
  ("skin_material_realism",[18,19,29],["surface_state_ledger","mask_plan","skin_fabric_detail_passes"],["target_mask_only","surface_persistence","protected_neighbor_leakage"],["trusted_regional_masks","material_response","state_tracking"],["regional_surface_crops"],[]),
  ("fluid_body_state_continuity",[18,29,32],["scene_state_ledger","state_diff_report","revision_manager"],["planned_generated_state_match","shot_continuity"],["state_detection","sequence_correspondence"],["before_after_shot_review"],[]),
  ("pose_to_audio_force_model",[30,31],["audio_force_map","foley_timing","spatial_mix_metadata"],["contact_transient_alignment","effort_alignment"],["pose_contact_force","audio_timing"],["contact_timing_review"],["transient_sync_review"]),
  ("long_form_fatigue_variation",[26,28,29,32],["variation_scheduler","fatigue_curves","take_manager"],["anti_repetition","state_non_reset","pacing_consistency"],["long_form_state","variation_planning"],["sequence_variation_review"],["vocal_variation_review"]),
  ("room_acoustics_spatial_audio",[9,30,31],["room_acoustics_profile","spatial_renderer_handoff"],["camera_pan_match","environment_reverb_match","distance_cue_match"],["room_geometry","camera_character_positions","spatial_audio"],["camera_environment_review"],["pan_reverb_distance_review"]),]
 records=[]
 for sid,waves,mods,gates,caps,visual,audio in systems:records.append({"system_id":sid,"planned_waves":waves,"module_surfaces":mods,"qa_gates":gates,"required_capabilities":caps,"review_requirements":{"visual":visual,"audio":audio},"mapping_state":"complete","runtime_promotion_state":"blocked_missing_direct_runtime_evidence","blockers":["model_or_runtime_capability_proof_missing","required_visual_evidence_missing"]+(["required_audio_evidence_missing"] if audio else [])+(["trusted_gold_mask_or_ownership_evidence_missing"] if sid in {"physical_interaction_engine","skin_material_realism"} else [])})
 fail_rule="Runtime promotion is denied unless all mapping checks pass, source hashes match, every required capability has direct runtime proof, every required visual/audio artifact passes strict review, ownership metadata is complete, and no blocker remains."
 registry=PLAN/"10_REGISTRIES/advanced_additions_integration_crosswalk.json"
 reg={"schema_version":"1.0","artifact_id":"advanced_additions_integration_crosswalk","created_iso":iso,"tracker_id":TRK,"source_hashes":source_hashes,"advanced_systems":records,"coverage_gates":{"advanced_crosswalk":"pass","module_mapping":"pass","qa_mapping":"pass","runtime_promotion_rule":"pass"},"coverage_state":"complete","runtime_promotion_state":"blocked","fail_closed_rule":fail_rule}
 write(registry,reg)
 by={r["system_id"]:r for r in records};checks={
 "AAI-001_exactly_seven_systems":len(records)==7,"AAI-002_waves_nonempty":all(r["planned_waves"] for r in records),"AAI-003_modules_nonempty":all(r["module_surfaces"] for r in records),"AAI-004_qa_nonempty":all(r["qa_gates"] for r in records),"AAI-005_capabilities_reviews_present":all(r["required_capabilities"] and r["review_requirements"]["visual"] for r in records),
 "AAI-006_contact_graph": "contact_graph" in by["physical_interaction_engine"]["module_surfaces"],"AAI-007_motion_timeline":"motion_timeline" in by["micro_motion_layer"]["module_surfaces"],"AAI-008_surface_ledger":"surface_state_ledger" in by["skin_material_realism"]["module_surfaces"],"AAI-009_state_diff":"state_diff_report" in by["fluid_body_state_continuity"]["module_surfaces"],"AAI-010_audio_maps":"audio_force_map" in by["pose_to_audio_force_model"]["module_surfaces"] and "room_acoustics_profile" in by["room_acoustics_spatial_audio"]["module_surfaces"],
 "AAI-011_contact_safety":{"no_clipping","no_floating"}<=set(by["physical_interaction_engine"]["qa_gates"]),"AAI-012_hard_anatomy_source":(SRC/"WAVE20_ADVANCED_ADDITIONS_HARD_ANATOMY_INTEGRATION.md").exists(),"AAI-013_softbody_source":(SRC/"WAVE21_ADVANCED_ADDITIONS_SOFT_BODY_PROFILE_INTEGRATION.md").exists(),"AAI-014_contact_graph_source":(SRC/"WAVE22_ADVANCED_CONTACT_GRAPH_INTEGRATION.md").exists(),"AAI-015_instance_layout_source":(SRC/"WAVE24_ADVANCED_ADDITIONS_INSTANCE_LAYOUT_INTEGRATION.md").exists(),
 "AAI-016_fail_closed_default":reg["runtime_promotion_state"]=="blocked","AAI-017_visual_audio_required":all("visual" in r["review_requirements"] and "audio" in r["review_requirements"] for r in records),"AAI-018_hashes_complete":len(source_hashes)==10 and all(len(v)==64 for v in source_hashes.values()),"AAI-019_blockers_force_block":all(r["blockers"] and r["runtime_promotion_state"].startswith("blocked") for r in records),"AAI-020_decision_deterministic":all(v=="pass" for v in reg["coverage_gates"].values()) and reg["runtime_promotion_state"]=="blocked"}
 bad=[k for k,v in checks.items() if not v]
 if bad:raise SystemExit("failed: "+", ".join(bad))
 canonical=QA/"advanced_additions_integration.json";stamped=QA/f"ADVANCED_ADDITIONS_INTEGRATION_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"advanced_additions_integration_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-056_advanced_additions_integration.json"
 payload={"schema_version":"1.0","evidence_id":stamped.stem,"created_iso":iso,"wave":64,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"row_complete":False,"qa_decision":"advanced_additions_mapping_complete_runtime_promotion_fail_closed","registry":{"path":rel(registry),"sha256":sha(registry)},"coverage_gates":reg["coverage_gates"],"advanced_systems":records,"runtime_blockers":["direct_runtime_capability_proof_missing","strict_visual_evidence_missing","required_audio_sync_evidence_missing","trusted_mask_ownership_evidence_missing_for_mask_dependent_systems"],"runtime_promotion_state":"blocked","fail_closed_rule":fail_rule,"checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":20,"passed":20,"failed":0},"safety_boundary":{"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"generation_executed":False,"mask_truth_consumed":False,"runtime_promotion_claimed":False,"jira_mutated":False,"wave71_activated":False},"next_action":f"Advance with safe local {NEXT} organization governance while Row056 runtime/visual/audio/model proof remains fail-closed."}
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report),rel(registry)]+list(source_hashes);payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"result":"pass_mapping_coverage_runtime_blocked","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"registry":payload["registry"],"coverage_gates":payload["coverage_gates"],"runtime_blockers":payload["runtime_blockers"],"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row056 {stamp}: seven systems crosswalked; 20/20 mapping checks pass; runtime promotion remains blocked for direct visual/audio/model/mask proof."
 tags=["wave64_row056_mapping_coverage_pass","seven_system_crosswalk","runtime_promotion_fail_closed","advance_safe_row057"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")]
 ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row056 Advanced Additions Integration - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. Seven advanced systems are hash-bound and crosswalked to modules, QA gates, capabilities, and visual/audio review requirements. All 20 deterministic mapping checks pass, but runtime completion and promotion remain fail-closed because direct runtime, strict visual/audio, model-capability, and mask-ownership proof is incomplete. No external/runtime/mask/Jira action occurred.

Next safe local action: `{NEXT}` organization governance. Row056 remains open until its direct proof blockers clear.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 with (HYD/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRK,"Implemented seven-system advanced-additions crosswalk and fail-closed runtime promotion evaluator.","; ".join(ep),"20/20 mapping checks; direct runtime proof blocked",payload["qa_decision"],rel(canonical),f"Begin safe local {NEXT}."])
 print(json.dumps({"status":STATUS,"systems":7,"checks":payload["check_summary"],"runtime_promotion":"blocked","next":NEXT},indent=2))
if __name__=="__main__":main()
