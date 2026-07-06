#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2)+"\n",encoding="utf-8")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--qa-report",required=True); ap.add_argument("--policy",required=True); ap.add_argument("--attempt",type=int,default=1); ap.add_argument("--out",required=True); a=ap.parse_args()
    rep=load(a.qa_report); pol=load(a.policy); codes=[g.get("failure_code") for g in rep.get("failed_gates",[]) if g.get("failure_code")]
    maxa=int(pol.get("max_attempts_per_pass",3)); stops=set(pol.get("stop_conditions",[])); allowed=bool(codes) and a.attempt<maxa and not any(c in stops for c in codes)
    rules={r.get("failure_code"):r.get("adjustments",[]) for r in pol.get("parameter_adjustment_rules",[])}
    changes=[{"failure_code":c,"adjustment":adj} for c in codes for adj in rules.get(c,["increment seed"])]
    out={"run_id":rep.get("run_id"),"failed_pass_id":rep.get("pass_id"),"attempt":a.attempt,"failure_codes":codes,"rerun_allowed":allowed,"max_attempts":maxa,"rerun_patch_changes":changes,"next_action":"compile_rerun_patch_set" if allowed else "stop_or_manual_fix"}
    save(a.out,out); print(json.dumps(out,indent=2)); return 0 if allowed else 1
if __name__=="__main__": raise SystemExit(main())
