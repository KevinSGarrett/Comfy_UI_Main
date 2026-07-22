from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = (
    ROOT
    / "Plan/07_IMPLEMENTATION/scripts/canary_wave64_qwen3_omni_audio_semantic_runtime.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("qwen3_omni_audio_canary", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_payload() -> dict:
    return {
        "transcript": "Once upon a midnight.",
        "language": "English",
        "speech_intelligible": True,
        "clipping_or_distortion": "No obvious clipping.",
        "background_audio": "Quiet background.",
        "audible_events": ["spoken phrase"],
        "quality_observations": ["speech is intelligible"],
        "semantic_summary": "A voice says a short phrase.",
        "confidence": 0.91,
    }


def test_extract_json_object_ignores_thinking_prefix() -> None:
    module = load_module()
    payload = valid_payload()
    value = f"<think>brief internal text</think>\n{json.dumps(payload)}\n"
    assert module.extract_json_object(value) == payload


def test_semantic_gate_passes_exact_schema_and_phrase() -> None:
    module = load_module()
    result = module.validate_semantic_payload(
        valid_payload(), "once upon a midnight"
    )
    assert result["passed"] is True
    assert result["schema_keys_exact"] is True
    assert result["expected_phrase_present"] is True


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (lambda data: data.pop("confidence"), "missing"),
        (lambda data: data.update(extra="not allowed"), "extra"),
        (lambda data: data.update(confidence=1.5), "type"),
        (lambda data: data.update(speech_intelligible="yes"), "type"),
    ],
)
def test_semantic_gate_fails_closed_on_schema_drift(mutation, expected_error) -> None:
    module = load_module()
    payload = valid_payload()
    mutation(payload)
    result = module.validate_semantic_payload(payload, "once upon a midnight")
    assert result["passed"] is False
    if expected_error == "missing":
        assert result["missing_keys"]
    elif expected_error == "extra":
        assert result["extra_keys"]
    else:
        assert result["type_errors"]


def test_semantic_gate_rejects_hallucinated_transcript() -> None:
    module = load_module()
    payload = valid_payload()
    payload["transcript"] = "unrelated hallucinated sentence"
    result = module.validate_semantic_payload(payload, "once upon a midnight")
    assert result["expected_phrase_present"] is False
    assert result["passed"] is False


def test_device_map_summary_counts_cpu_and_gpu_targets() -> None:
    module = load_module()
    result = module.summarize_device_map(
        {"layer.0": 0, "layer.1": "cpu", "layer.2": 0}
    )
    assert result == {"target_counts": {"0": 2, "cpu": 1}, "module_count": 3}


def test_generation_result_unwrap_accepts_transformers_5_2_direct_shape() -> None:
    module = load_module()

    class Result:
        sequences = object()

    result = Result()
    assert module.unwrap_text_generation_result(result) is result


def test_generation_result_unwrap_accepts_qwen_compatible_tuple_shape() -> None:
    module = load_module()

    class Result:
        sequences = object()

    result = Result()
    assert module.unwrap_text_generation_result((result, None)) is result


@pytest.mark.parametrize("value", ["sequences", (object(), None), (object(), 1)])
def test_generation_result_unwrap_rejects_ambiguous_shapes(value) -> None:
    module = load_module()
    with pytest.raises(module.CanaryError, match="unsupported Qwen3-Omni"):
        module.unwrap_text_generation_result(value)


def test_process_exit_cleanup_can_accept_scoped_semantic_worker() -> None:
    module = load_module()
    evidence = {
        "runtime": {},
        "semantic_review": {"gate": {"passed": True}},
        "error": None,
        "authority": {
            "process_exit_cleanup": False,
            "exact_fixture_structured_audio_observation": False,
        },
    }
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 660},
        host_memory_before_worker=400 * 1024**3,
        host_memory_after_worker_exit=399 * 1024**3,
        offload_dir_removed=True,
        worker_returncode=0,
        worker_stdout="receipt written",
        worker_stderr="",
    )
    assert exit_code == 0
    assert finalized["status"] == (
        "PASS_EXACT_FIXTURE_AUDIO_SEMANTIC_AND_PROCESS_EXIT_CLEANUP"
    )
    assert finalized["runtime"]["process_exit_cleanup_delta_mib"] == 12
    assert finalized["authority"]["process_exit_cleanup"] is True


def test_process_exit_cleanup_rejects_retained_offload_directory() -> None:
    module = load_module()
    evidence = {
        "runtime": {},
        "semantic_review": {"gate": {"passed": True}},
        "error": None,
        "authority": {
            "process_exit_cleanup": False,
            "exact_fixture_structured_audio_observation": False,
        },
    }
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 648},
        host_memory_before_worker=400 * 1024**3,
        host_memory_after_worker_exit=400 * 1024**3,
        offload_dir_removed=False,
        worker_returncode=0,
        worker_stdout="",
        worker_stderr="",
    )
    assert exit_code == 1
    assert finalized["authority"]["process_exit_cleanup"] is False


def test_host_cleanup_prefers_cgroup_return_over_global_noise() -> None:
    module = load_module()
    gib = 1024**3
    before = {"mem_available_bytes": 400 * gib, "cached_bytes": 20 * gib, "sreclaimable_bytes": gib, "cgroup_current_bytes": 40 * gib, "cgroup_anon_bytes": 35 * gib, "cgroup_file_bytes": 5 * gib}
    after = {"mem_available_bytes": 368 * gib, "cached_bytes": 50 * gib, "sreclaimable_bytes": gib, "cgroup_current_bytes": 41 * gib, "cgroup_anon_bytes": 35 * gib, "cgroup_file_bytes": 6 * gib}
    result = module.classify_host_cleanup(before, after)
    assert result["passed"] is True
    assert result["disposition"] == "PASS_CGROUP_MEMORY_RETURNED_TO_BASELINE"


def test_host_cleanup_is_indeterminate_not_leak_when_all_signals_drift() -> None:
    module = load_module()
    gib = 1024**3
    before = {"mem_available_bytes": 400 * gib, "cgroup_current_bytes": 40 * gib, "cgroup_anon_bytes": 35 * gib}
    after = {"mem_available_bytes": 368 * gib, "cgroup_current_bytes": 70 * gib, "cgroup_anon_bytes": 65 * gib}
    result = module.classify_host_cleanup(before, after)
    assert result["passed"] is False
    assert result["disposition"] == "INDETERMINATE_SHARED_HOST_MEMORY_DELTA"
    assert result["global_memavailable_is_not_process_leak_authority"] is True


def test_finalize_distinguishes_indeterminate_host_cleanup() -> None:
    module = load_module()
    gib = 1024**3
    evidence = {"runtime": {}, "semantic_review": {"gate": {"passed": True}}, "error": None, "authority": {"process_exit_cleanup": False, "exact_fixture_structured_audio_observation": False}}
    before = {"mem_available_bytes": 400 * gib, "cgroup_current_bytes": 40 * gib, "cgroup_anon_bytes": 35 * gib}
    after = {"mem_available_bytes": 368 * gib, "cgroup_current_bytes": 70 * gib, "cgroup_anon_bytes": 65 * gib}
    finalized, exit_code = module.finalize_process_exit_cleanup(
        evidence,
        gpu_before_worker={"used_mib": 648},
        gpu_after_worker_exit={"used_mib": 648},
        host_memory_before_worker=400 * gib,
        host_memory_after_worker_exit=368 * gib,
        offload_dir_removed=True,
        worker_returncode=0,
        worker_stdout="",
        worker_stderr="",
        host_snapshot_before=before,
        host_snapshot_after=after,
    )
    assert exit_code == 1
    assert finalized["status"] == "INDETERMINATE_HOST_CLEANUP_EXACT_SEMANTIC_AND_GPU_CLEANUP_PASS"
    assert finalized["authority"]["process_exit_cleanup"] is False
