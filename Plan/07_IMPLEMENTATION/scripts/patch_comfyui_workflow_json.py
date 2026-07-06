#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,datetime as dt,hashlib,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256(); 
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def idx(wf): return {int(n["id"]):n for n in wf.get("nodes",[]) if "id" in n}
def apply(wf,patch):
    node=idx(wf).get(int(patch["node_id"]))
    if node is None: raise KeyError(f"node not found {patch['node_id']}")
    old=None; kind=patch.get("kind")
    if kind=="widget_value":
        vals=node.setdefault("widgets_values",[]); wi=int(patch["widget_index"])
        if wi>=len(vals): raise IndexError(f"widget index {wi} out of range")
        old=vals[wi]; vals[wi]=patch.get("value")
    elif kind=="input_link":
        for inp in node.get("inputs",[]):
            if inp.get("name")==patch["input_name"]:
                old=inp.get("link"); inp["link"]=patch.get("value"); break
        else: raise KeyError(f"input not found {patch['input_name']}")
    else: raise ValueError(f"unsupported patch kind {kind}")
    return {"patch_id":patch.get("patch_id"),"node_id":node["id"],"node_type":node.get("type"),"kind":kind,"old_value":old,"new_value":patch.get("value"),"status":"applied"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workflow",required=True); ap.add_argument("--patches",required=True); ap.add_argument("--out-workflow",required=True); ap.add_argument("--out-manifest",required=True); a=ap.parse_args()
    source=load(a.workflow); patched=copy.deepcopy(source); results=[]
    for p in load(a.patches).get("patches",[]):
        try: results.append(apply(patched,p))
        except Exception as e:
            rep={"status":"FAIL","error":str(e),"source_sha256":sha(a.workflow),"patches":results}
            save(a.out_manifest,rep); print(json.dumps(rep,indent=2)); return 2
    save(a.out_workflow,patched); rep={"status":"PASS","created_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source_sha256":sha(a.workflow),"out_workflow":a.out_workflow,"out_sha256":sha(a.out_workflow),"patches":results}
    save(a.out_manifest,rep); print(json.dumps({"status":"PASS","patch_count":len(results)},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
