#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2)+"\n",encoding="utf-8")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--evidence",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    ev=load(a.evidence); dry=bool(ev.get("dry_run")); results=[{"gate":"evidence_json_parse","status":"pass"}]
    results.append({"gate":"runtime_execution","status":"not_run_dry_run" if dry else ("pass" if ev.get("prompt_id") else "fail"),"failure_code":None if dry or ev.get("prompt_id") else "history_missing"})
    results.append({"gate":"outputs","status":"not_run_dry_run" if dry else ("pass" if ev.get("outputs") else "fail"),"failure_code":None if dry or ev.get("outputs") else "output_missing"})
    failed=[r for r in results if r["status"]=="fail"]
    rep={"run_id":ev.get("run_id"),"pass_id":ev.get("pass_id"),"status":"PASS" if not failed else "FAIL","qa_results":results,"failed_gates":failed,"next_action":"next_pass" if not failed else "rerun_or_stop_by_policy"}
    save(a.out,rep); print(json.dumps(rep,indent=2)); return 0 if not failed else 2
if __name__=="__main__": raise SystemExit(main())
