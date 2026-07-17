from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT=Path(__file__).resolve().parents[4];SCRIPT=ROOT/"Plan/07_IMPLEMENTATION/scripts/run_wave64_resource_cache_telemetry_slice.py"
SPEC=importlib.util.spec_from_file_location("wave64_resource_cache",SCRIPT);assert SPEC and SPEC.loader
RUNTIME=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=RUNTIME;SPEC.loader.exec_module(RUNTIME)
def registry():return RUNTIME.load_json(ROOT/RUNTIME.DEFAULT_REGISTRY)
def schema():return RUNTIME.load_json(ROOT/RUNTIME.DEFAULT_SCHEMA)
def fixture():return RUNTIME.execute_fixture(registry())


def test_registry_and_sources_validate():RUNTIME.validate_registry(ROOT,registry(),schema())
def test_fixture_passes_bounded_runtime_controls():
    result=fixture();assert result["classification"]=="WAVE64_RESOURCE_CACHE_TELEMETRY_SLICE_PASS";assert result["rows_covered"]==[205,206,207,208];assert result["admission_decision"]["decision"]=="admit";assert result["production_runtime_allowed"] is False


def test_source_hash_drift_rejected():
    c=registry();c["source_authorities"][0]["sha256"]="0"*64
    with pytest.raises(RUNTIME.ResourceControlError,match="bound_hash_mismatch:worker_lease_schema"):RUNTIME.validate_registry(ROOT,c,schema())
def test_source_path_escape_rejected():
    c=registry();c["source_authorities"][0]["path"]="../outside.json"
    with pytest.raises(RUNTIME.ResourceControlError,match="bound_path_not_relative"):RUNTIME.validate_registry(ROOT,c,schema())
def test_duplicate_source_name_rejected():
    c=registry();c["source_authorities"][7]["name"]="worker_lease_schema"
    with pytest.raises(RUNTIME.ResourceControlError,match="duplicate_source_authority_name"):RUNTIME.validate_registry(ROOT,c,schema())


def base_envelope():return {"certified":True,"lease_active":True,"measurements_current":True,"capabilities":["image"],"vram_mb":100,"ram_mb":100,"disk_mb":100}
def base_request():return {"stack_id":"a","workload_class":"image","required_capabilities":["image"],"vram_mb":10,"ram_mb":10,"disk_mb":10,"incompatible_with":[],"oom_retries":0,"material_hypothesis":"baseline","priority":1,"wait_ticks":2}


@pytest.mark.parametrize("field",["certified","lease_active","measurements_current"])
def test_uncertified_unleased_or_stale_envelope_rejected(field):
    e=base_envelope();e[field]=False;assert RUNTIME.admit(e,base_request(),[],registry()["resource_scheduler_policy"])["decision"]=="reject"
def test_missing_capability_rejected():
    r=base_request();r["required_capabilities"]=["video"];assert RUNTIME.admit(base_envelope(),r,[],registry()["resource_scheduler_policy"])["reason"]=="CAPABILITY_MISSING"
def test_vram_overflow_rejected():assert fixture()["oversized_rejection"]["reason"]=="VRAM_MB_ENVELOPE_EXCEEDED"
def test_incompatible_coresidency_rejected():assert fixture()["coresidency_rejection"]["reason"]=="INCOMPATIBLE_CORESIDENCY"
def test_audio_isolation_rejected():
    r=base_request();r["workload_class"]="audio";resident=[dict(base_request())];assert RUNTIME.admit(base_envelope(),r,resident,registry()["resource_scheduler_policy"])["reason"]=="AUDIO_ISOLATION_REQUIRED"
def test_oom_loop_rejected():assert fixture()["oom_loop_rejection"]["reason"]=="OOM_RETRY_LOOP_PREVENTED"
def test_priority_aging_is_applied():assert fixture()["admission_decision"]["effective_priority"]==54


def bindings():return {name:hashlib.sha256(name.encode()).hexdigest() for name in RUNTIME.CACHE_PARTS}
def test_cache_key_requires_exact_seven_bindings():
    b=bindings();b.pop("runtime")
    with pytest.raises(RUNTIME.ResourceControlError,match="cache_key_binding_invalid"):RUNTIME.cache_key(b)
def test_valid_cache_hit_is_hash_and_lineage_bound():assert fixture()["cache_hit"]=={"decision":"hit","reason":"HASH_AND_LINEAGE_PASS"}
@pytest.mark.parametrize("state",sorted(RUNTIME.UNSAFE_CACHE))
def test_all_unsafe_cache_states_reject(state):assert fixture()["unsafe_cache_rejections"][state]=="reject"
def test_payload_corruption_rejected():
    b=bindings();entry={"state":"valid","cache_key":RUNTIME.cache_key(b),"payload_sha256":"0"*64,"lineage_complete":True,"replay_policy":"deterministic"};assert RUNTIME.validate_cache(entry,b,b"payload")["reason"]=="CORRUPT"
def test_stochastic_replay_policy_rejected():
    b=bindings();payload=b"x";entry={"state":"valid","cache_key":RUNTIME.cache_key(b),"payload_sha256":hashlib.sha256(payload).hexdigest(),"lineage_complete":True,"replay_policy":"stochastic"};assert RUNTIME.validate_cache(entry,b,payload)["decision"]=="reject"


def test_telemetry_requires_exact_metric_set():
    with pytest.raises(RUNTIME.ResourceControlError,match="telemetry_metric_set_mismatch"):RUNTIME.degraded_decision({"memory":1})
def test_degraded_mode_is_explicit_and_preserves_gates():
    d=fixture()["degraded_decision"];assert set(d["actions"])=={"block_unhealthy_service","defer_low_priority","evict_optional_models","reduce_concurrency"};assert d["quality_gates_unchanged"] and d["authority_gates_unchanged"] and d["recorded"]
def test_false_boundary_rejected():
    c=registry();c["boundaries"]["gpu_allocated"]=True
    with pytest.raises(RUNTIME.ResourceControlError,match="schema_validation_failed"):RUNTIME.validate_registry(ROOT,c,schema())
def test_evidence_mirrors(tmp_path):
    e=RUNTIME.build_evidence(ROOT,fixture(),RUNTIME.DEFAULT_REGISTRY,RUNTIME.DEFAULT_SCHEMA);q=tmp_path/"q.json";t=tmp_path/"t.json";RUNTIME.write_json(q,e);RUNTIME.write_json(t,e);assert q.read_bytes()==t.read_bytes();assert not any(e["boundaries"].values())
