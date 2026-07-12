#!/usr/bin/env python3
from __future__ import annotations

import hashlib, json, subprocess, sys, tempfile, unittest, wave
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[4];SCRIPT=ROOT/"Plan/07_IMPLEMENTATION/scripts/produce_wave30_voice_dialogue_continuity_request.py";SCHEMA=ROOT/"Plan/08_SCHEMAS/wave30_voice_dialogue_continuity_request.schema.json"
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

class VoiceRequestProducerTests(unittest.TestCase):
 def case(self,base:Path)->tuple[Path,Path,Path]:
  base.mkdir(parents=True,exist_ok=True);profile=base/"profile.json";profile.write_text(json.dumps({"voice_profile_id":"vp","character_id":"char","status":"active"}))
  lines=[]
  for i,frames in enumerate((1600,2400)):
   audio=base/f"line{i}.wav"
   with wave.open(str(audio),"wb")as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes((b"\x01\x00" if i==0 else b"\x02\x00")*frames)
   lines.append({"line_id":f"l{i}","character_id":"char","voice_profile_id":"vp","text":f"line {i}","start_time":i*0.1,"end_time":i*0.1+frames/16000,"emotion":"calm","intensity":"low","sync_required":True,"output_file":str(audio)})
  contract=base/"contract.json";contract.write_text(json.dumps({"schema_name":"wave30_voice_dialogue_contract","dialogue_contract_version":1,"lines":lines}));proofs=base/"proofs";proofs.mkdir();return profile,contract,proofs
 def run_cli(self,*args:str)->subprocess.CompletedProcess[str]:return subprocess.run([sys.executable,str(SCRIPT),"--root",str(ROOT),*args],cwd=ROOT,text=True,capture_output=True)
 def test_emits_schema_valid_request_with_null_missing_proofs(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);p,c,d=self.case(b);o=b/"request.json";r=self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(o),"--run-id","run")
   self.assertEqual(r.returncode,0,r.stdout);q=json.loads(o.read_text());Draft202012Validator(json.loads(SCHEMA.read_text())).validate(q);self.assertEqual(len(q["line_audio_bindings"]),2);self.assertTrue(all(v is None for v in q["proof_bindings"].values()))
 def test_discovers_and_hash_binds_available_proofs(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);p,c,d=self.case(b);proof=d/"asr_proof.json";proof.write_text("{}\n");o=b/"request.json";self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(o),"--run-id","run")
   self.assertEqual(json.loads(o.read_text())["proof_bindings"]["asr_proof"]["sha256"],sha(proof))
 def test_rejects_duplicate_audio_and_ownership_mismatch(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);p,c,d=self.case(b);x=json.loads(c.read_text());x["lines"][1]["output_file"]=x["lines"][0]["output_file"];c.write_text(json.dumps(x));o=b/"request.json";self.assertEqual(self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(o),"--run-id","run").returncode,2)
   p,c,d=self.case(b/"fresh");x=json.loads(c.read_text());x["lines"][0]["character_id"]="wrong";c.write_text(json.dumps(x));self.assertEqual(self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(b/"bad.json"),"--run-id","run").returncode,2)
 def test_rejects_invalid_wav_and_root_escape(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);p,c,d=self.case(b);x=json.loads(c.read_text());Path(x["lines"][0]["output_file"]).write_text("bad");c.write_text(json.dumps(x));self.assertEqual(self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(b/"request.json"),"--run-id","run").returncode,2)
   outside=Path(tempfile.gettempdir())/"outside_voice.json";outside.write_text("{}");self.assertEqual(self.run_cli("--voice-profile",str(outside),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(b/"other.json"),"--run-id","run").returncode,2);outside.unlink(missing_ok=True)
 def test_existing_output_is_preserved(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);p,c,d=self.case(b);o=b/"request.json";o.write_text("keep");r=self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(o),"--run-id","run");self.assertEqual(r.returncode,2);self.assertEqual(o.read_text(),"keep")
 def test_rejects_boolean_contract_version_and_output_under_proof_dir(self)->None:
  with tempfile.TemporaryDirectory(dir=ROOT/"runtime_artifacts")as t:
   b=Path(t);p,c,d=self.case(b);x=json.loads(c.read_text());x["dialogue_contract_version"]=True;c.write_text(json.dumps(x));self.assertEqual(self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(b/"request.json"),"--run-id","run").returncode,2)
   p,c,d=self.case(b/"fresh");self.assertEqual(self.run_cli("--voice-profile",str(p),"--dialogue-contract",str(c),"--proof-dir",str(d),"--output",str(d/"future.json"),"--run-id","run").returncode,2);self.assertFalse((d/"future.json").exists())

if __name__=="__main__":unittest.main()
