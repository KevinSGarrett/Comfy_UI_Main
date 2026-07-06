#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,json,urllib.request,urllib.error
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def http_json(method,url,payload=None):
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(url,data=data,method=method,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r:
        raw=r.read().decode("utf-8"); return json.loads(raw) if raw else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workflow",required=True); ap.add_argument("--run-id",required=True); ap.add_argument("--pass-id",required=True); ap.add_argument("--server-url",default="http://127.0.0.1:8188"); ap.add_argument("--out-request",required=True); ap.add_argument("--out-result",required=True); ap.add_argument("--execute",action="store_true"); a=ap.parse_args()
    wf=load(a.workflow); req={"run_id":a.run_id,"pass_id":a.pass_id,"server_url":a.server_url,"workflow":wf,"dry_run":not a.execute,"created_at":dt.datetime.now(dt.timezone.utc).isoformat()}; save(a.out_request,req)
    if not a.execute:
        res={"run_id":a.run_id,"pass_id":a.pass_id,"status":"DRY_RUN_NOT_EXECUTED","dry_run":True,"prompt_id":None,"error":None}; save(a.out_result,res); print(json.dumps(res,indent=2)); return 0
    try:
        oi=http_json("GET",a.server_url.rstrip()+"/object_info"); out=http_json("POST",a.server_url.rstrip()+"/prompt",{"prompt":wf})
        res={"run_id":a.run_id,"pass_id":a.pass_id,"status":"SUBMITTED","dry_run":False,"prompt_id":out.get("prompt_id"),"object_info_node_count":len(oi) if isinstance(oi,dict) else None,"response":out,"error":None}
        save(a.out_result,res); print(json.dumps(res,indent=2)); return 0
    except Exception as e:
        res={"run_id":a.run_id,"pass_id":a.pass_id,"status":"EXECUTION_FAILED","dry_run":False,"prompt_id":None,"error":str(e)}; save(a.out_result,res); print(json.dumps(res,indent=2)); return 2
if __name__=="__main__": raise SystemExit(main())
