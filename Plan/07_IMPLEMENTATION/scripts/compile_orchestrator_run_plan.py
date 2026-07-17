#!/usr/bin/env python3
"""Legacy Wave14 planning scaffold; never a Wave64 production entrypoint.

This compiler remains available only for historical dry-run plan validation.
The future durable event-driven controller must use the Wave64 canonical pass,
bundle, submission, receipt, reconciliation, QA, and promotion contracts.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def make_pass(pid,stage,order,engine,tpl,req,attempts,patches,qa,evidence=None):
    return {
        "pass_id":pid,
        "stage_id":stage,
        "order":order,
        "engine_family":engine,
        "workflow_template":tpl,
        "required":req,
        "max_attempts":attempts,
        "patches":patches,
        "qa_gates":qa,
        "evidence_dependencies": evidence or []
    }
def evidence_for(req,pid,stage):
    bindings=req.get("pass_evidence_bindings") or {}
    items=[]
    for key in (pid,stage):
        v=bindings.get(key)
        if isinstance(v,list): items.extend(v)
        elif v: items.append(v)
    return items
def compile_plan(req):
    execution_mode=req.get("execution_mode","dry_run_plan_only")
    if execution_mode not in {"dry_run_plan_only","legacy_planning_scaffold"}:
        raise ValueError("LEGACY_ORCHESTRATOR_COMPILER_PRODUCTION_INVOCATION_BLOCKED")
    now=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    rid=req.get("request_id",f"request_{now}")
    run=req.get("run_id",f"run_{now}_{hashlib.sha256(rid.encode()).hexdigest()[:8]}")
    mods=set(req.get("requested_modalities") or ["image"]); passes=[]
    passes.append(make_pass("p00_preflight","01_preflight",0,"none","preflight_only",True,1,[],["schema","object_info","model_manifest"],evidence_for(req,"p00_preflight","01_preflight")))
    if "image" in mods or "video" in mods:
        passes.append(make_pass("p01_base","02_base_composition",len(passes),req.get("engine_preference","auto"),"main_flow_base_lane",True,3,["prompt","seed","latent_size","save_prefix"],["decode","frame_composition"],evidence_for(req,"p01_base","02_base_composition")))
        if req.get("character_id") or req.get("reference_pack") or req.get("identity_strictness")=="strict":
            passes.append(make_pass("p02_identity","03_reference_identity",len(passes),"sdxl_realvisxl","identity_reference_lane",False,3,["reference_image","attention_mask"],["identity_continuity"],evidence_for(req,"p02_identity","03_reference_identity")))
        if req.get("pose_plan") or req.get("control_map_contract") or req.get("action"):
            passes.append(make_pass("p03_pose_control","04_pose_control",len(passes),"sdxl_realvisxl","control_map_lane",False,2,["control_image","control_strength"],["pose_action_blocking"],evidence_for(req,"p03_pose_control","04_pose_control")))
        if req.get("mask_factory_contract") or req.get("regional_edit") or req.get("local_detail"):
            passes.append(make_pass("p04_mask_factory","05_mask_factory",len(passes),"none","mask_factory",False,2,[],["mask_quality"],evidence_for(req,"p04_mask_factory","05_mask_factory")))
            passes.append(make_pass("p05_regional_detail","06_regional_inpaint_detail",len(passes),"sdxl_realvisxl","regional_inpaint_detail_lane",False,3,["mask","denoise","prompt"],["localized_edit","mask_bleed"],evidence_for(req,"p05_regional_detail","06_regional_inpaint_detail")))
        passes.append(make_pass("p06_upscale_polish","07_upscale_polish",len(passes),"upscale","upscale_polish_lane",True,2,["input_image","save_prefix"],["decode","artifact_check"],evidence_for(req,"p06_upscale_polish","07_upscale_polish")))
    if "video" in mods: passes.append(make_pass("p07_video_handoff","08_video_handoff",len(passes),"video_lane","video_runtime_request",True,2,["keyframes"],["video_runtime_boundary"],evidence_for(req,"p07_video_handoff","08_video_handoff")))
    if "audio" in mods: passes.append(make_pass("p08_audio_handoff","09_audio_handoff",len(passes),"audio_lane","audio_runtime_request",True,2,["voice_profile","timing"],["audio_runtime_boundary"],evidence_for(req,"p08_audio_handoff","09_audio_handoff")))
    passes.append(make_pass("p99_promotion","10_promotion",99,"none","promotion_manifest",True,1,[],["all_required_evidence"],evidence_for(req,"p99_promotion","10_promotion")))
    return {
        "run_id":run,
        "status":"compiled",
        "dry_run_first":bool(req.get("dry_run_only",True)),
        "execution_mode":execution_mode,
        "source_request_id":rid,
        "workflow_source":req.get("workflow_source","Wave42_Runtime_Bound__UI__WAVE42_MAIN_FLOW_20260702.json"),
        "created_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "ruleset":req.get("ruleset","Plan/10_REGISTRIES/wave14_pass_planner_rules.json"),
        "router_bindings":req.get("router_bindings","Plan/10_REGISTRIES/wave14_router_bindings.json"),
        "api_route_contracts":req.get("api_route_contracts","Plan/10_REGISTRIES/wave14_comfyui_api_route_contracts.json"),
        "global_evidence_dependencies":req.get("evidence_dependencies",[]),
        "passes":passes,
        "promotion_rule":"all required passes must have passing evidence",
        "request_summary":req
    }
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--request",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    plan=compile_plan(load(a.request)); save(a.out,plan); print(json.dumps({"status":"PASS","run_id":plan["run_id"],"passes":len(plan["passes"])},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
