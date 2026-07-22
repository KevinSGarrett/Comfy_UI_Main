#!/usr/bin/env python3
"""Run one lease-bound partition of the frozen expanded Wav2Vec2 matrix."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import canary_wave64_wav2vec2_phoneme_alignment as base  # noqa: E402


class ExpandedAlignmentError(RuntimeError):
    """Raised when an admitted identity, partition, or gate is violated."""


EXPECTED_ENVIRONMENT_ROOT = (
    "/workspace/w64_aqa/environments/wav2vec2-phoneme-aligner/"
    "phonemizer-fork-3.3.2_espeakng-loader-0.2.4_py311/"
    "7abfff8a8d3252776a10556648f4b9fb37f6cf734eebf4333004b57ccd2c484a"
)
EXPECTED_ENVIRONMENT_TREE = "92834c7a92d1acf3bde825fdd6f74b752451bbf350e83b8809585c5734e77e6b"
EXPECTED_ACTIVATION_RECEIPT_SHA256 = "c0a148e6ebddbb7089df7679b68f2afaa1ddb8ed38d54d47473b64ccf5b3c956"
EXPECTED_ACCEPTED_CANARY_SHA256 = "404dbd97bbef08b966f6a39434b7256b97e42dc0c1a7c9cd56949f4f48878a93"
EXPECTED_PLAN_SHA256 = "a8bd9b6bdeaf16be3ab1dd83f6cdf73dcec717ba25f03986bc3bf84071be50d4"
EXPECTED_PARTITIONS = {
    "calibration": [
        "align_qwen_english",
        "align_ambience_refusal",
        "align_foley_refusal",
    ],
    "held_out": [
        "align_natural_english",
        "align_spanish_diagnostic",
        "align_code_switch_diagnostic",
        "align_transcript_mismatch_refusal",
        "align_overlap_refusal",
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_admission(admission: dict[str, Any], plan_path: Path) -> None:
    if admission.get("status") != "EXPANDED_ALIGNMENT_PARTITION_EXECUTION_ADMITTED_RUNTIME_PENDING":
        raise ExpandedAlignmentError("execution admission status mismatch")
    if (
        admission.get("plan", {}).get("sha256") != EXPECTED_PLAN_SHA256
        or sha256(plan_path) != EXPECTED_PLAN_SHA256
    ):
        raise ExpandedAlignmentError("expanded plan identity mismatch")
    model = admission.get("model", {})
    if (
        model.get("package_id") != base.PACKAGE_ID
        or model.get("repository") != base.UPSTREAM_REPOSITORY
        or model.get("revision") != base.UPSTREAM_REVISION
        or model.get("weight_sha256") != base.MODEL_FILES["pytorch_model.bin"][1]
        or model.get("accepted_canary_sha256") != EXPECTED_ACCEPTED_CANARY_SHA256
    ):
        raise ExpandedAlignmentError("accepted model identity mismatch")
    environment = admission.get("environment", {})
    if (
        environment.get("root") != EXPECTED_ENVIRONMENT_ROOT
        or environment.get("tree_manifest_sha256") != EXPECTED_ENVIRONMENT_TREE
        or environment.get("activation_receipt_sha256")
        != EXPECTED_ACTIVATION_RECEIPT_SHA256
    ):
        raise ExpandedAlignmentError("accepted environment identity mismatch")
    lease = admission.get("lease", {})
    if (
        lease.get("project") != "comfyui_main"
        or lease.get("profile") != "comfyui_model_qualification"
        or lease.get("mode") != "exclusive"
        or lease.get("minimum_reserved_peak_gib", 0) < 4
        or lease.get("required_free_vram_mib", 0) < 4096
        or not 0 < lease.get("cleanup_tolerance_mib", 0) <= 1024
    ):
        raise ExpandedAlignmentError("execution lease scope mismatch")
    partitions = admission.get("partitions", {})
    if any(partitions.get(name) != case_ids for name, case_ids in EXPECTED_PARTITIONS.items()):
        raise ExpandedAlignmentError("execution partition identity mismatch")
    if partitions.get("held_out_requires_calibration_receipt") is not True:
        raise ExpandedAlignmentError("held-out calibration receipt gate is absent")
    if partitions.get("unchanged_rerun_forbidden") is not True:
        raise ExpandedAlignmentError("unchanged rerun prohibition is absent")
    authority = admission.get("authority", {})
    allowed_true = {"exact_package_reuse", "partitioned_alignment_execution"}
    if any(authority.get(name) is not True for name in allowed_true):
        raise ExpandedAlignmentError("required execution authority is absent")
    if any(value is not False for name, value in authority.items() if name not in allowed_true):
        raise ExpandedAlignmentError("admission exceeds partitioned alignment authority")


def validate_lease(
    receipt: dict[str, Any], admission: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    expected = admission["lease"]
    if "lease_token" in receipt or "token" in receipt:
        raise ExpandedAlignmentError("lease receipt must not contain a token")
    if receipt.get("valid") is not True:
        raise ExpandedAlignmentError("coordinator receipt is not valid")
    fields = {"project": expected["project"], "profile": expected["profile"], "lease_mode": expected["mode"]}
    for name, value in fields.items():
        if receipt.get(name) != value:
            raise ExpandedAlignmentError(f"coordinator receipt {name} mismatch")
    if float(receipt.get("reserved_peak_gib", 0)) < expected["minimum_reserved_peak_gib"]:
        raise ExpandedAlignmentError("coordinator reservation is too small")
    expiry = datetime.fromisoformat(str(receipt.get("expires_at", "")).replace("Z", "+00:00"))
    if expiry <= (now or datetime.now(timezone.utc)):
        raise ExpandedAlignmentError("coordinator receipt is expired")
    names = ("valid", "lease_id", "project", "profile", "lease_mode", "reserved_peak_gib", "safety_reserve_gib", "expires_at")
    return {name: receipt[name] for name in names}


def validate_fixtures(plan: dict[str, Any], fixture_root: Path) -> dict[str, Path]:
    expected = {f"{source['source_id']}.wav": source for source in plan["sources"]}
    observed = {path.name: path for path in fixture_root.iterdir() if path.is_file()}
    if set(observed) != set(expected) or any(path.is_symlink() for path in observed.values()):
        raise ExpandedAlignmentError("expanded fixture file set mismatch or unsafe member")
    result = {}
    for name, source in expected.items():
        path = observed[name]
        if path.stat().st_size != source["bytes"] or sha256(path) != source["sha256"]:
            raise ExpandedAlignmentError(f"expanded fixture identity mismatch: {name}")
        result[source["source_id"]] = path
    return result


def select_cases(admission: dict[str, Any], plan: dict[str, Any], partition: str) -> list[dict[str, Any]]:
    expected = admission["partitions"].get(partition)
    if expected is None:
        raise ExpandedAlignmentError("partition is not admitted")
    by_id = {case["case_id"]: case for case in plan["alignment_cases"]}
    if any(case_id not in by_id for case_id in expected):
        raise ExpandedAlignmentError("admission references an unknown alignment case")
    return [by_id[case_id] for case_id in expected]


def validate_calibration_receipt(
    receipt: dict[str, Any], admission: dict[str, Any]
) -> float:
    if receipt.get("status") != "PASS_CALIBRATION_PARTITION_AND_PROCESS_EXIT_CLEANUP":
        raise ExpandedAlignmentError("held-out execution requires a passing calibration receipt")
    if receipt.get("partition") != "calibration":
        raise ExpandedAlignmentError("calibration receipt partition mismatch")
    if receipt.get("plan_sha256") != admission["plan"]["sha256"]:
        raise ExpandedAlignmentError("calibration receipt plan identity mismatch")
    if receipt.get("package", {}).get("revision") != admission["model"]["revision"]:
        raise ExpandedAlignmentError("calibration receipt model identity mismatch")
    matched = [item for item in receipt.get("results", []) if item.get("case_id") == "align_qwen_english"]
    if len(matched) != 1 or matched[0].get("passed") is not True:
        raise ExpandedAlignmentError("calibration receipt lacks the matched-source control")
    return float(matched[0]["greedy_similarity"])


def policy_result(case: dict[str, Any], result: dict[str, Any], matched_similarity: float | None) -> tuple[bool, bool]:
    policy = case["policy"]
    speech_gate = result.get("speech_gate") is True
    if policy == "REQUIRE_COMPLETE_MONOTONIC_TRANSCRIPT_BOUND_SPANS":
        return speech_gate, speech_gate
    if policy == "REQUIRE_NO_SPEECH_ALIGNMENT":
        return not speech_gate, False
    if policy == "REQUIRE_MATCH_SCORE_DROP_AT_LEAST_0_15_FROM_MATCHED_SOURCE":
        if matched_similarity is None:
            raise ExpandedAlignmentError("mismatch policy requires a matched calibration baseline")
        passed = matched_similarity - float(result.get("greedy_similarity", 1.0)) >= 0.15
        return passed, False
    if policy == "REQUIRE_SINGLE_SPEAKER_ALIGNMENT_AUTHORITY_REFUSAL":
        return result.get("speaker_class", "").startswith("two_project_generated_speakers"), False
    if policy == "MEASURE_LANGUAGE_SCOPED_COVERAGE_NO_AUTHORITY":
        return result.get("inference_complete") is True, False
    raise ExpandedAlignmentError(f"unsupported alignment policy: {policy}")


def run_worker(
    admission: dict[str, Any],
    plan: dict[str, Any],
    fixture_root: Path,
    partition: str,
    lease: dict[str, Any],
    calibration_receipt: dict[str, Any] | None,
) -> tuple[dict[str, Any], int]:
    model_root = Path(admission["model"]["root"])
    environment_root = Path(admission["environment"]["root"])
    base.validate_exact_model_package(model_root)
    fixtures = validate_fixtures(plan, fixture_root)
    cases = select_cases(admission, plan, partition)
    matched_similarity = None
    if partition == "held_out":
        if calibration_receipt is None:
            raise ExpandedAlignmentError("held-out execution requires a calibration receipt")
        matched_similarity = validate_calibration_receipt(calibration_receipt, admission)
    sys.path.insert(0, str(environment_root.resolve(strict=True)))
    os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false", "PYTHONDONTWRITEBYTECODE": "1"})
    before = base.gpu_snapshot()
    if before["free_mib"] < admission["lease"]["required_free_vram_mib"]:
        raise ExpandedAlignmentError("free VRAM is below the admitted minimum")
    model = None
    results: list[dict[str, Any]] = []
    error = None
    loaded = None
    started = time.monotonic()
    try:
        import espeakng_loader
        import torch
        import torchaudio
        from phonemizer.backend import EspeakBackend
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
        from phonemizer.separator import Separator
        from torchaudio.functional import forced_align, merge_tokens
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC, Wav2Vec2PhonemeCTCTokenizer

        EspeakWrapper.set_library(espeakng_loader.get_library_path())
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
        tokenizer = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(str(model_root), local_files_only=True, do_phonemize=False)
        extractor = Wav2Vec2FeatureExtractor.from_pretrained(str(model_root), local_files_only=True)
        model = Wav2Vec2ForCTC.from_pretrained(str(model_root), local_files_only=True).to("cuda:0").eval()
        torch.cuda.synchronize()
        loaded = base.gpu_snapshot()
        sources = {source["source_id"]: source for source in plan["sources"]}
        probe_transcript = sources["qwen_l02_english"]["transcript"]
        for case in cases:
            source = sources[case["source_id"]]
            transcript = case.get("override_transcript") or source.get("transcript") or probe_transcript
            language = "es" if source["language"] == "es" else "en-us"
            backend = EspeakBackend(language, preserve_punctuation=False, with_stress=False)
            words = base.word_tokens(transcript, backend, Separator(phone=" ", word="", syllable=""))
            target_tokens = [token for word in words for token in word["phoneme_tokens"]]
            target_ids = tokenizer.convert_tokens_to_ids(target_tokens)
            waveform, sample_rate = torchaudio.load(str(fixtures[source["source_id"]]))
            waveform = waveform.mean(dim=0)
            if sample_rate != 16000:
                waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)
            inputs = extractor(waveform.numpy(), sampling_rate=16000, return_tensors="pt")
            with torch.inference_mode():
                logits = model(inputs.input_values.to("cuda:0")).logits
                log_probs = logits.log_softmax(dim=-1)
            torch.cuda.synchronize()
            greedy_ids = base.ctc_collapse(logits[0].argmax(dim=-1).cpu().tolist(), tokenizer.pad_token_id)
            similarity = base.normalized_similarity(greedy_ids, target_ids)
            record: dict[str, Any] = {"case_id": case["case_id"], "source_id": source["source_id"], "partition": partition, "policy": case["policy"], "speaker_class": source["speaker_class"], "language": source["language"], "transcript_used": transcript, "greedy_similarity": similarity, "target_contains_unknown_token": tokenizer.unk_token_id in target_ids, "inference_complete": True, "alignment_authority": False}
            try:
                if tokenizer.unk_token_id in target_ids:
                    raise ExpandedAlignmentError("target phoneme sequence contains unknown model tokens")
                aligned, scores = forced_align(log_probs.cpu(), torch.tensor([target_ids], dtype=torch.int32), blank=tokenizer.pad_token_id)
                spans = merge_tokens(aligned[0], scores[0], blank=tokenizer.pad_token_id)
                duration = waveform.numel() / 16000.0
                token_records, word_records, monotonic = base.spans_to_records(spans, target_tokens, words, duration / logits.shape[1])
                posterior = sum(item["posterior"] for item in token_records) / len(token_records)
                record.update({"mean_aligned_token_posterior": posterior, "alignment_complete_and_monotonic": monotonic, "phoneme_spans": token_records, "word_spans": word_records, "speech_gate": monotonic and similarity >= base.MIN_SPEECH_GREEDY_SIMILARITY and posterior >= base.MIN_SPEECH_ALIGNMENT_POSTERIOR})
            except Exception as exc:  # noqa: BLE001 - per-case refusal/failure is retained.
                record.update({"alignment_error": f"{type(exc).__name__}: {exc}", "speech_gate": False})
            passed, authority = policy_result(case, record, matched_similarity)
            record.update({"passed": passed, "alignment_authority": authority})
            results.append(record)
        passed = all(item["passed"] for item in results)
    except Exception as exc:  # noqa: BLE001 - runtime failure must be retained.
        error = f"{type(exc).__name__}: {exc}"
        passed = False
    finally:
        if model is not None:
            del model
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        except Exception:  # noqa: BLE001 - process exit is authoritative cleanup.
            pass
    evidence = {"schema_version": "wave64.aqa.wav2vec2_expanded_alignment_partition.v1", "program_id": "W64-AQA", "partition": partition, "status": f"PASS_{partition.upper()}_PARTITION" if passed else f"FAIL_{partition.upper()}_PARTITION", "plan_sha256": admission["plan"]["sha256"], "package": admission["model"], "lease": lease, "results": results, "runtime": {"duration_seconds": time.monotonic() - started, "gpu_before": before, "gpu_loaded": loaded, "gpu_after_in_process_cleanup": base.gpu_snapshot()}, "error": error, "authority": {"exact_partition_control_behavior": passed, "general_forced_alignment": False, "multilingual_alignment": False, "overlap_alignment": False, "audio_event_recognition": False, "operational_activation": False, "product_promotion": False}}
    return evidence, 0 if passed else 1


def finalize(worker: dict[str, Any], before: dict[str, Any], after: dict[str, Any], returncode: int, tolerance: int) -> tuple[dict[str, Any], int]:
    delta = after["used_mib"] - before["used_mib"]
    passed = returncode == 0 and worker.get("status", "").startswith("PASS_") and delta <= tolerance
    worker["runtime"].update({"gpu_before_worker_process": before, "gpu_after_worker_process_exit": after, "process_exit_cleanup_delta_mib": delta, "process_exit_cleanup_pass": delta <= tolerance, "worker_returncode": returncode})
    partition = worker["partition"].upper()
    worker["status"] = f"PASS_{partition}_PARTITION_AND_PROCESS_EXIT_CLEANUP" if passed else f"FAIL_{partition}_PARTITION_RUNTIME_OR_PROCESS_EXIT_CLEANUP"
    worker["authority"]["exact_partition_control_behavior"] = passed
    return worker, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--partition", choices=("calibration", "held_out"), required=True)
    parser.add_argument("--lease-receipt", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    lease = validate_lease(json.loads(args.lease_receipt.read_text(encoding="utf-8")), admission)
    validate_admission(admission, args.plan)
    calibration = json.loads(args.calibration_receipt.read_text(encoding="utf-8")) if args.calibration_receipt else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.inner_worker:
        result, code = run_worker(admission, plan, args.fixture_root, args.partition, lease, calibration)
    else:
        validate_fixtures(plan, args.fixture_root)
        before = base.gpu_snapshot()
        worker_path = args.output.parent / f".{args.output.name}.{uuid.uuid4().hex}.worker"
        command = [sys.executable, str(Path(__file__).resolve()), "--inner-worker", "--admission", str(args.admission), "--plan", str(args.plan), "--fixture-root", str(args.fixture_root), "--partition", args.partition, "--lease-receipt", str(args.lease_receipt), "--output", str(worker_path)]
        if args.calibration_receipt:
            command.extend(["--calibration-receipt", str(args.calibration_receipt)])
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=900)
        if not worker_path.is_file():
            raise ExpandedAlignmentError(f"worker emitted no evidence: {completed.stderr[-1000:]}")
        try:
            worker = json.loads(worker_path.read_text(encoding="utf-8"))
        finally:
            worker_path.unlink(missing_ok=True)
        time.sleep(2)
        result, code = finalize(worker, before, base.gpu_snapshot(), completed.returncode, admission["lease"]["cleanup_tolerance_mib"])
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
