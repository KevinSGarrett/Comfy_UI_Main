#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def evidence_paths(items):
    paths=[]
    if isinstance(items,dict): items=[items]
    if not isinstance(items,list): return paths
    for item in items:
        if isinstance(item,str): paths.append(item)
        elif isinstance(item,dict):
            for key in ("path","evidence_path","manifest","runtime_evidence","visual_qa_evidence"):
                value=item.get(key)
                if isinstance(value,str) and value: paths.append(value)
    return paths
def path_exists(project_root,raw):
    p=Path(raw)
    if not p.is_absolute(): p=Path(project_root)/raw
    return p.exists(), str(p)
def validate(plan, project_root="."):
    errors=[]; warnings=[]; checked=[]
    for k in ["run_id","status","passes"]:
        if k not in plan: errors.append(f"missing plan key: {k}")
    if plan.get("status")!="compiled": errors.append("status must be compiled")
    if plan.get("dry_run_first") is not True: errors.append("dry_run_first must be true unless a separate runtime gate promotes execution")
    if not plan.get("execution_mode"): errors.append("missing execution_mode")
    for key in ("ruleset","router_bindings","api_route_contracts"):
        value=plan.get(key)
        if not value: errors.append(f"missing {key}")
        else:
            ok,resolved=path_exists(project_root,value); checked.append(resolved)
            if not ok: errors.append(f"{key} path missing: {value}")
    passes=plan.get("passes",[])
    if not isinstance(passes,list) or not passes: errors.append("passes must be non-empty list"); return errors,warnings,checked
    seen=set(); orders=[]
    for i,p in enumerate(passes):
        for k in ["pass_id","stage_id","order","required","max_attempts","qa_gates","evidence_dependencies"]:
            if k not in p: errors.append(f"pass[{i}] missing {k}")
        if p.get("pass_id") in seen: errors.append(f"duplicate pass_id {p.get('pass_id')}")
        seen.add(p.get("pass_id")); orders.append(p.get("order"))
        if p.get("max_attempts",0)<1: errors.append(f"{p.get('pass_id')} max_attempts < 1")
        if not isinstance(p.get("qa_gates"),list) or not p.get("qa_gates"): errors.append(f"{p.get('pass_id')} qa_gates must be non-empty list")
        ev=p.get("evidence_dependencies")
        if not isinstance(ev,list): errors.append(f"{p.get('pass_id')} evidence_dependencies must be a list")
        elif p.get("required") is True and not evidence_paths(ev):
            warnings.append(f"{p.get('pass_id')} is required but has no evidence dependency binding yet")
        for raw in evidence_paths(ev):
            ok,resolved=path_exists(project_root,raw); checked.append(resolved)
            if not ok: errors.append(f"{p.get('pass_id')} evidence path missing: {raw}")
    if orders != sorted(orders): errors.append("orders are not sorted")
    if not any(p.get("stage_id")=="01_preflight" for p in passes): errors.append("missing preflight")
    if not any(p.get("stage_id")=="10_promotion" for p in passes): errors.append("missing promotion")
    for raw in evidence_paths(plan.get("global_evidence_dependencies",[])):
        ok,resolved=path_exists(project_root,raw); checked.append(resolved)
        if not ok: errors.append(f"global evidence path missing: {raw}")
    if not any(evidence_paths(p.get("evidence_dependencies",[])) for p in passes):
        warnings.append("no pass-level evidence dependencies were supplied")
    return errors,warnings,checked
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--plan",required=True); ap.add_argument("--out"); ap.add_argument("--project-root",default="."); a=ap.parse_args()
    plan=load(a.plan); errors,warnings,checked=validate(plan,a.project_root); rep={"status":"PASS" if not errors else "FAIL","errors":errors,"warnings":warnings,"pass_count":len(plan.get("passes",[])),"checked_evidence_path_count":len(checked),"checked_evidence_paths":checked}
    if a.out: Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(rep,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(rep,indent=2)); return 0 if not errors else 2
if __name__=="__main__": raise SystemExit(main())
