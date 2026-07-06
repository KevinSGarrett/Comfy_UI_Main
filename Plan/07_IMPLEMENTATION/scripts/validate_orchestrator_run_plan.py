#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def validate(plan):
    errors=[]
    for k in ["run_id","status","passes"]:
        if k not in plan: errors.append(f"missing plan key: {k}")
    passes=plan.get("passes",[])
    if not isinstance(passes,list) or not passes: errors.append("passes must be non-empty list"); return errors
    seen=set(); orders=[]
    for i,p in enumerate(passes):
        for k in ["pass_id","stage_id","order","required","max_attempts"]:
            if k not in p: errors.append(f"pass[{i}] missing {k}")
        if p.get("pass_id") in seen: errors.append(f"duplicate pass_id {p.get('pass_id')}")
        seen.add(p.get("pass_id")); orders.append(p.get("order"))
        if p.get("max_attempts",0)<1: errors.append(f"{p.get('pass_id')} max_attempts < 1")
    if orders != sorted(orders): errors.append("orders are not sorted")
    if not any(p.get("stage_id")=="01_preflight" for p in passes): errors.append("missing preflight")
    if not any(p.get("stage_id")=="10_promotion" for p in passes): errors.append("missing promotion")
    return errors
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--plan",required=True); ap.add_argument("--out"); a=ap.parse_args()
    plan=load(a.plan); errors=validate(plan); rep={"status":"PASS" if not errors else "FAIL","errors":errors,"pass_count":len(plan.get("passes",[]))}
    if a.out: Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(rep,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(rep,indent=2)); return 0 if not errors else 2
if __name__=="__main__": raise SystemExit(main())
