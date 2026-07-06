#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,urllib.request
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def get(url):
    with urllib.request.urlopen(url,timeout=60) as r:
        raw=r.read().decode("utf-8"); return json.loads(raw) if raw else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--execution-result",required=True); ap.add_argument("--server-url",default="http://127.0.0.1:8188"); ap.add_argument("--out",required=True); ap.add_argument("--execute",action="store_true"); a=ap.parse_args()
    res=load(a.execution_result); ev={"created_at":dt.datetime.now(dt.timezone.utc).isoformat(),"run_id":res.get("run_id"),"pass_id":res.get("pass_id"),"prompt_id":res.get("prompt_id"),"dry_run":not a.execute,"history_status":"not_requested","history":None,"outputs":[],"error":None}
    if not a.execute: ev["history_status"]="DRY_RUN_NOT_COLLECTED"; save(a.out,ev); print(json.dumps(ev,indent=2)); return 0
    if not ev["prompt_id"]: ev["history_status"]="MISSING_PROMPT_ID"; ev["error"]="Cannot collect without prompt_id"; save(a.out,ev); print(json.dumps(ev,indent=2)); return 2
    try: ev["history"]=get(a.server_url.rstrip()+f"/history/{ev['prompt_id']}"); ev["history_status"]="COLLECTED"; save(a.out,ev); print(json.dumps({"status":"PASS","out":a.out},indent=2)); return 0
    except Exception as e: ev["history_status"]="COLLECTION_FAILED"; ev["error"]=str(e); save(a.out,ev); print(json.dumps(ev,indent=2)); return 2
if __name__=="__main__": raise SystemExit(main())
