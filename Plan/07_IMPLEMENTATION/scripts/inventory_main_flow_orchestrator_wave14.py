#!/usr/bin/env python3
from __future__ import annotations
import argparse,collections,hashlib,json
from pathlib import Path
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(p,o): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--workflow",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    wf=load(a.workflow); nodes=wf.get("nodes",[]); cnt=collections.Counter(n.get("type") for n in nodes)
    masks=[{"node_id":n.get("id"),"node_type":n.get("type"),"input_name":i.get("name"),"link":i.get("link")} for n in nodes for i in (n.get("inputs",[]) or []) if i.get("type")=="MASK"]
    out={"source":a.workflow,"source_sha256":sha(a.workflow),"workflow_id":wf.get("id"),"node_count":len(nodes),"link_count":len(wf.get("links",[])),"node_type_counts":dict(cnt.most_common()),"save_image_lanes":[{"node_id":n.get("id"),"prefix":(n.get("widgets_values") or [""])[0] if n.get("widgets_values") else ""} for n in nodes if n.get("type")=="SaveImage"],"ksampler_targets":[{"node_id":n.get("id"),"widgets_values":n.get("widgets_values")} for n in nodes if n.get("type")=="KSampler"],"clip_text_targets":[{"node_id":n.get("id")} for n in nodes if n.get("type")=="CLIPTextEncode"],"mask_input_slots":masks,"orchestrator_ready_for_static_patch_planning":True,"runtime_execution_proven":False}
    save(a.out,out); print(json.dumps({"status":"PASS","node_count":len(nodes),"save_image_lanes":len(out["save_image_lanes"])},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
