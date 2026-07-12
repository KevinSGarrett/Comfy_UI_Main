#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, tempfile
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

DEFAULT_THRESHOLDS={"min_force_confidence":0.7,"max_frame_drift":2,"max_seconds_drift":0.08,"max_wav_duration_drift_seconds":0.05,"max_clipping_ratio":0.0003,"min_rms_ratio":0.005}
OPTIONAL_FILES={"wave31_force_event_manifest_binding":"wave31_force_event_manifest.json","runtime_proof_binding":"runtime_proof.json","av_review_proof_binding":"av_review_proof.json","production_alignment_bundle_binding":"production_alignment_bundle.json"}

def load(path:Path)->Any:return json.loads(path.read_text(encoding="utf-8"),parse_constant=lambda value:(_ for _ in()).throw(ValueError(f"non-finite JSON: {value}")))
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def under(root:Path,raw:Path,label:str)->Path:
 path=raw.resolve() if raw.is_absolute() else(root/raw).resolve()
 try:path.relative_to(root.resolve())
 except ValueError as exc:raise ValueError(f"{label} must stay inside project root")from exc
 return path
def binding(path:Path)->dict[str,str]:return{"path":str(path),"sha256":sha(path)}
def atomic(path:Path,payload:Any)->None:
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.",dir=str(path.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8")as h:json.dump(payload,h,indent=2,sort_keys=True);h.write("\n");h.flush();os.fsync(h.fileno())
  os.replace(tmp,path)
 except Exception:
  if os.path.exists(tmp):os.unlink(tmp)
  raise

def produce(root:Path,visual:Path,force:Path,audio:Path,optional_dir:Path,output:Path,run_id:str,scene_id:str,shot_id:str,take_id:str,synthetic:bool)->dict[str,Any]:
 if output.exists():raise ValueError(f"output already exists: {output}")
 if output==optional_dir or optional_dir in output.parents:raise ValueError("output must not be inside optional artifact directory")
 for path,label in((visual,"visual contact manifest"),(force,"Wave22 force manifest"),(audio,"Wave30 audio manifest")):
  if not path.is_file():raise ValueError(f"{label} missing: {path}")
  if not isinstance(load(path),(dict,list)):raise ValueError(f"{label} must contain a JSON object or array")
 for value,label in((run_id,"run_id"),(scene_id,"scene_id"),(shot_id,"shot_id"),(take_id,"take_id")):
  if not value.strip():raise ValueError(f"{label} must be non-empty")
 optional:dict[str,dict[str,str]|None]={}
 for key,name in OPTIONAL_FILES.items():
  path=under(root,optional_dir/name,key);optional[key]=binding(path)if path.is_file()else None
 request={"schema_name":"wave64_foley_force_alignment_request","request_version":1,"run_id":run_id.strip(),"scene_id":scene_id.strip(),"shot_id":shot_id.strip(),"take_id":take_id.strip(),"is_synthetic":synthetic,
          "visual_contact_manifest_binding":binding(visual),"wave22_force_event_manifest_binding":binding(force),"wave30_audio_event_manifest_binding":binding(audio),**optional,"thresholds":dict(DEFAULT_THRESHOLDS)}
 schema=load(root/"Plan/08_SCHEMAS/wave64_foley_force_alignment_request.schema.json");Draft202012Validator(schema).validate(request);atomic(output,request);return request

def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--visual-contact-manifest",required=True);p.add_argument("--wave22-force-manifest",required=True);p.add_argument("--wave30-audio-manifest",required=True);p.add_argument("--optional-dir",required=True);p.add_argument("--output",required=True);p.add_argument("--run-id",required=True);p.add_argument("--scene-id",required=True);p.add_argument("--shot-id",required=True);p.add_argument("--take-id",required=True);p.add_argument("--production-input",action="store_true");p.add_argument("--root",default="C:/Comfy_UI_Main");a=p.parse_args()
 try:
  root=Path(a.root).resolve();visual=under(root,Path(a.visual_contact_manifest),"visual manifest");force=under(root,Path(a.wave22_force_manifest),"force manifest");audio=under(root,Path(a.wave30_audio_manifest),"audio manifest");optional=under(root,Path(a.optional_dir),"optional directory");output=under(root,Path(a.output),"output")
  request=produce(root,visual,force,audio,optional,output,a.run_id,a.scene_id,a.shot_id,a.take_id,not a.production_input)
 except Exception as exc:print(f"ERROR: {exc}");return 2
 print(json.dumps({"status":"pass","output":str(output),"missing_optional_count":sum(request[key]is None for key in OPTIONAL_FILES)},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
