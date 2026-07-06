#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,py_compile
from pathlib import Path
REQ=["00_PROJECT_CONTROL/WAVE14_AI_PM_TASKS.md","02_TARGET_ARCHITECTURE/WAVE14_AUTONOMOUS_PASS_PLANNER_ORCHESTRATOR_ARCHITECTURE.md","02_TARGET_ARCHITECTURE/WAVE14_WORKFLOW_JSON_PATCHING_STRATEGY.md","06_QA_TESTING/WAVE14_ORCHESTRATOR_QA_GATES.md","07_IMPLEMENTATION/scripts/compile_orchestrator_run_plan.py","07_IMPLEMENTATION/scripts/patch_comfyui_workflow_json.py","07_IMPLEMENTATION/scripts/run_comfyui_pass_dryrun_first.py","08_SCHEMAS/orchestrator_run_plan.schema.json","10_REGISTRIES/wave14_pass_stage_taxonomy.json","10_REGISTRIES/wave14_workflow_patch_targets.json","10_REGISTRIES/wave14_rerun_policy.json","10_REGISTRIES/wave14_main_flow_orchestrator_inventory.json","09_EXAMPLES/wave14_orchestrator_run_plan.example.json"]
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--out"); a=ap.parse_args(); root=Path(a.root).resolve(); errors=[]
    for r in REQ:
        if not (root/r).exists(): errors.append(f"missing {r}")
    jc=0
    for jf in root.rglob("*.json"):
        try: load(jf); jc+=1
        except Exception as e: errors.append(f"json parse failed {jf.relative_to(root)}: {e}")
    scripts=[root/"07_IMPLEMENTATION/scripts"/x for x in ["compile_orchestrator_run_plan.py","validate_orchestrator_run_plan.py","patch_comfyui_workflow_json.py","run_comfyui_pass_dryrun_first.py","collect_comfyui_history_evidence.py","score_orchestrator_pass_evidence.py","rerun_failed_orchestrator_passes.py","inventory_main_flow_orchestrator_wave14.py","run_wave14_local_validation.py"]]
    pc=0
    for s in scripts:
        try: py_compile.compile(str(s),doraise=True); pc+=1
        except Exception as e: errors.append(f"python compile failed {s.relative_to(root)}: {e}")
    inv=load(root/"10_REGISTRIES/wave14_main_flow_orchestrator_inventory.json"); stages=load(root/"10_REGISTRIES/wave14_pass_stage_taxonomy.json"); targets=load(root/"10_REGISTRIES/wave14_workflow_patch_targets.json"); routes=load(root/"10_REGISTRIES/wave14_comfyui_api_route_contracts.json")
    if inv.get("node_count")!=356: errors.append(f"expected 356 nodes got {inv.get('node_count')}")
    if len(inv.get("save_image_lanes",[]))!=8: errors.append("expected 8 SaveImage lanes")
    if len(stages)<10: errors.append("expected at least 10 pass stages")
    if len(targets)<20: errors.append("expected at least 20 patch targets")
    if not any(r.get("route")=="/prompt" and "POST" in r.get("method","") for r in routes): errors.append("missing /prompt POST route")
    rep={"status":"PASS" if not errors else "FAIL","errors":errors,"json_files_checked":jc,"new_python_scripts_checked":pc,"main_flow_nodes":inv.get("node_count"),"main_flow_links":inv.get("link_count"),"save_image_lanes":len(inv.get("save_image_lanes",[])),"ksampler_targets":len(inv.get("ksampler_patch_targets",[])),"clip_text_targets":len(inv.get("clip_text_patch_targets",[])),"mask_input_slots":len(inv.get("mask_input_slots",[])),"pass_stages":len(stages),"workflow_patch_targets":len(targets),"comfyui_route_contracts":len(routes),"runtime_execution_proven":False,"ec2_required_now":False}
    out=Path(a.out) if a.out else root/"11_RELEASES/WAVE14_VALIDATION_REPORT.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(rep,indent=2,ensure_ascii=False)); return 0 if not errors else 2
if __name__=="__main__": raise SystemExit(main())
