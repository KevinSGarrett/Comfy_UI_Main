#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[4];SCRIPT=ROOT/"Plan/07_IMPLEMENTATION/scripts/produce_wave64_foley_force_alignment_request.py";SCHEMA=ROOT/"Plan/08_SCHEMAS/wave64_foley_force_alignment_request.schema.json"
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
class FoleyRequestProducerTests(unittest.TestCase):
 def case(self,b:Path)->tuple[Path,Path,Path,Path]:
  b.mkdir(parents=True,exist_ok=True);paths=[b/"visual.json",b/"force.json",b/"audio.json"]
  for i,p in enumerate(paths):p.write_text(json.dumps({"kind":i})+"\n")
  optional=b/"optional";optional.mkdir();return paths[0],paths[1],paths[2],optional
 def run_cli(self,*args:str)->subprocess.CompletedProcess[str]:return subprocess.run([sys.executable,str(SCRIPT),"--root",str(ROOT),*args],cwd=ROOT,text=True,capture_output=True)
 def args(self,v:Path,f:Path,a:Path,d:Path,o:Path)->list[str]:return["--visual-contact-manifest",str(v),"--wave22-force-manifest",str(f),"--wave30-audio-manifest",str(a),"--optional-dir",str(d),"--output",str(o),"--run-id","run","--scene-id","scene","--shot-id","shot","--take-id","take"]
 def test_emits_schema_valid_request_with_fixed_thresholds_and_null_optionals(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);v,f,a,d=self.case(b);o=b/"request.json";r=self.run_cli(*self.args(v,f,a,d,o));self.assertEqual(r.returncode,0,r.stdout);q=json.loads(o.read_text());Draft202012Validator(json.loads(SCHEMA.read_text())).validate(q);self.assertEqual(q["thresholds"]["max_frame_drift"],2);self.assertTrue(all(q[k]is None for k in("wave31_force_event_manifest_binding","runtime_proof_binding","av_review_proof_binding","production_alignment_bundle_binding")))
 def test_discovers_optional_artifacts_by_fixed_name(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);v,f,a,d=self.case(b);names={"wave31_force_event_manifest_binding":"wave31_force_event_manifest.json","runtime_proof_binding":"runtime_proof.json","av_review_proof_binding":"av_review_proof.json","production_alignment_bundle_binding":"production_alignment_bundle.json"}
   for i,name in enumerate(names.values()):(d/name).write_text(json.dumps({"proof":i})+"\n")
   o=b/"request.json";self.run_cli(*self.args(v,f,a,d,o));request=json.loads(o.read_text())
   for key,name in names.items():self.assertEqual(request[key]["sha256"],sha(d/name))
 def test_rejects_missing_or_invalid_required_json_and_root_escape(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);v,f,a,d=self.case(b);v.unlink();self.assertEqual(self.run_cli(*self.args(v,f,a,d,b/"one.json")).returncode,2);v.write_text("bad");self.assertEqual(self.run_cli(*self.args(v,f,a,d,b/"two.json")).returncode,2)
   outside=Path(tempfile.gettempdir())/"outside_force.json";outside.write_text("{}");self.assertEqual(self.run_cli(*self.args(v,outside,a,d,b/"three.json")).returncode,2);outside.unlink(missing_ok=True)
   v,f,a,d=self.case(b/"audio");a.unlink();self.assertEqual(self.run_cli(*self.args(v,f,a,d,b/"four.json")).returncode,2);a.write_text("bad");self.assertEqual(self.run_cli(*self.args(v,f,a,d,b/"five.json")).returncode,2);a.write_text("{}")
   outside_dir=Path(tempfile.gettempdir())/"outside_foley_optional";outside_dir.mkdir(exist_ok=True);self.assertEqual(self.run_cli(*self.args(v,f,a,outside_dir,b/"six.json")).returncode,2)
   outside_output=Path(tempfile.gettempdir())/"outside_foley_request.json";outside_output.unlink(missing_ok=True);self.assertEqual(self.run_cli(*self.args(v,f,a,d,outside_output)).returncode,2);self.assertFalse(outside_output.exists())
 def test_rejects_output_under_optional_directory(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);v,f,a,d=self.case(b);o=d/"runtime_proof.json";self.assertEqual(self.run_cli(*self.args(v,f,a,d,o)).returncode,2);self.assertFalse(o.exists())
 def test_existing_output_is_preserved(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);v,f,a,d=self.case(b);o=b/"request.json";o.write_text("keep");self.assertEqual(self.run_cli(*self.args(v,f,a,d,o)).returncode,2);self.assertEqual(o.read_text(),"keep")
 def test_production_input_flag_emits_non_synthetic_request(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);v,f,a,d=self.case(b);o=b/"request.json";result=self.run_cli(*self.args(v,f,a,d,o),"--production-input");self.assertEqual(result.returncode,0,result.stdout);self.assertFalse(json.loads(o.read_text())["is_synthetic"])
if __name__=="__main__":unittest.main()
