#!/usr/bin/env python3
"""Run the prospective four-fixture Wav2Vec2 phoneme-alignment canary."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_ID = "W64-AQA-PKG-WAV2VEC2-PHONEME-ALIGNER"
UPSTREAM_REPOSITORY = "facebook/wav2vec2-lv-60-espeak-cv-ft"
UPSTREAM_REVISION = "ae45363bf3413b374fecd9dc8bc1df0e24c3b7f4"
EXPECTED_PROFILE = "comfyui_model_qualification"
TRANSCRIPT = "We hold the frame steady and move on the beat."
MIN_SPEECH_GREEDY_SIMILARITY = 0.45
MIN_SPEECH_ALIGNMENT_POSTERIOR = 0.10
MODEL_FILES: dict[str, tuple[int, str]] = {
    ".gitattributes": (
        1175,
        "fa057bb09b78fe6d33af5a01440be5e8c881cd8055de35ee5588ea759cf57bfc",
    ),
    "README.md": (
        3035,
        "81a55816a87034bcf0828d6181fa88abad32a0cbfcebc2ebc8b336664b69ba60",
    ),
    "config.json": (
        1856,
        "4609fb49b7e1d28aecb2840da1926c40bd915bc6f1120a940afacf7159bbfb13",
    ),
    "preprocessor_config.json": (
        212,
        "a2254a5b58f72cd4de3632f8eee64f3f098b7c1402128d2f419e7d00ae13e335",
    ),
    "pytorch_model.bin": (
        1263535127,
        "3173bde9e9ce490fa0f989e413c42f25bc1820c020adc1e6b9b87025b3cfcc5e",
    ),
    "special_tokens_map.json": (
        85,
        "bb7068de1150661a10b55f9e4b12a0e77af8bf91f5e45e1b58afaf1d0e17f675",
    ),
    "tokenizer_config.json": (
        321,
        "1273ec458332cc55226ec596904bae811420755ace7e5d69462b61c4f480b457",
    ),
    "vocab.json": (
        4637,
        "d732ab2456c0c017930001dc9af0b41b3b93d25b2eb9740bf9d925508d7d87d0",
    ),
}
FIXTURES: dict[str, dict[str, Any]] = {
    "clean_speech": {
        "sha256": "ff8325a1c2f8613d599af69284f5c4693d996a581230ccbbbb1aeba7affa9815",
        "bytes": 153646,
        "expect_speech": True,
    },
    "tone_only": {
        "sha256": "86b408e05408d396cfef2a3d9de30bcd2cf45c89bb5b94e276b333db584ca4d1",
        "bytes": 153646,
        "expect_speech": False,
    },
    "silence": {
        "sha256": "dddee7638516ce249409a281adef90982855aa32217c465dcbb093e128624e11",
        "bytes": 153646,
        "expect_speech": False,
    },
    "speech_plus_tone": {
        "sha256": "d9c78b7c20fcb46ef44dfb803467c6206448bd6b15539e180ce6a24a33eb94c8",
        "bytes": 153646,
        "expect_speech": True,
    },
}


class CanaryError(RuntimeError):
    """Raised when an immutable input or prospective gate is violated."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_exact_files(root: Path, expected: dict[str, tuple[int, str]]) -> None:
    if not root.is_dir() or root.is_symlink():
        raise CanaryError("model root is absent or unsafe")
    observed: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise CanaryError(f"model member symlink is forbidden: {path}")
        if path.is_file():
            observed[path.relative_to(root).as_posix()] = path
    if set(observed) != set(expected):
        raise CanaryError("model package file-set mismatch")
    for relative_path, (expected_bytes, expected_sha256) in expected.items():
        path = observed[relative_path]
        if path.stat().st_size != expected_bytes or sha256_file(path) != expected_sha256:
            raise CanaryError(f"model package identity mismatch: {relative_path}")


def validate_fixtures(root: Path) -> list[dict[str, Any]]:
    records = []
    for fixture_id, spec in FIXTURES.items():
        path = root / f"{fixture_id}.wav"
        if not path.is_file() or path.is_symlink():
            raise CanaryError(f"fixture is absent or unsafe: {fixture_id}")
        observed = sha256_file(path)
        if path.stat().st_size != spec["bytes"] or observed != spec["sha256"]:
            raise CanaryError(f"fixture identity mismatch: {fixture_id}")
        records.append(
            {
                "fixture_id": fixture_id,
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": observed,
                "expect_speech": spec["expect_speech"],
            }
        )
    return records


def validate_lease(lease_id: str, profile: str, expires_at: str) -> dict[str, Any]:
    if not lease_id or profile != EXPECTED_PROFILE:
        raise CanaryError("exact shared capacity lease identity/profile is required")
    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if expiry <= datetime.now(timezone.utc):
        raise CanaryError("shared capacity lease is expired")
    return {
        "lease_id": lease_id,
        "project": "comfyui_main",
        "profile": profile,
        "expires_at": expires_at,
        "token_retained": False,
    }


def ctc_collapse(ids: list[int], blank_id: int) -> list[int]:
    output: list[int] = []
    previous: int | None = None
    for token_id in ids:
        if token_id != blank_id and token_id != previous:
            output.append(token_id)
        previous = token_id
    return output


def edit_distance(left: list[int], right: list[int]) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_value in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_value != right_value),
                )
            )
        previous = current
    return previous[-1]


def normalized_similarity(left: list[int], right: list[int]) -> float:
    denominator = max(len(left), len(right), 1)
    return max(0.0, 1.0 - (edit_distance(left, right) / denominator))


def word_tokens(transcript: str, backend: Any, separator: Any) -> list[dict[str, Any]]:
    words = re.findall(r"[A-Za-z']+", transcript)
    phonemized = backend.phonemize(words, separator=separator, strip=True)
    records = []
    for word, phones in zip(words, phonemized, strict=True):
        tokens = [token for token in phones.split(" ") if token]
        if not tokens:
            raise CanaryError(f"word produced no phonemes: {word}")
        records.append({"word": word, "phoneme_tokens": tokens})
    return records


def spans_to_records(
    spans: list[Any],
    tokens: list[str],
    words: list[dict[str, Any]],
    frame_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    if len(spans) != len(tokens):
        raise CanaryError("forced-alignment span count does not match target tokens")
    token_records = []
    for token, span in zip(tokens, spans, strict=True):
        token_records.append(
            {
                "token": token,
                "start_seconds": span.start * frame_seconds,
                "end_seconds": span.end * frame_seconds,
                "posterior": math.exp(float(span.score)),
            }
        )
    monotonic = all(
        record["end_seconds"] > record["start_seconds"]
        and (index == 0 or record["start_seconds"] >= token_records[index - 1]["end_seconds"])
        for index, record in enumerate(token_records)
    )
    word_records = []
    cursor = 0
    for word in words:
        count = len(word["phoneme_tokens"])
        selected = token_records[cursor : cursor + count]
        cursor += count
        word_records.append(
            {
                "word": word["word"],
                "start_seconds": selected[0]["start_seconds"],
                "end_seconds": selected[-1]["end_seconds"],
                "mean_posterior": sum(item["posterior"] for item in selected) / count,
                "phoneme_count": count,
            }
        )
    return token_records, word_records, monotonic and cursor == len(token_records)


def gpu_snapshot() -> dict[str, Any]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    rows = [row.strip() for row in completed.stdout.splitlines() if row.strip()]
    if len(rows) != 1:
        raise CanaryError("exactly one GPU is required")
    name, total, used, free, utilization = [part.strip() for part in rows[0].split(",")]
    return {
        "name": name,
        "total_mib": int(total),
        "used_mib": int(used),
        "free_mib": int(free),
        "utilization_percent": int(utilization),
    }


def run_worker(
    *,
    model_root: Path,
    fixture_root: Path,
    environment_root: Path,
    lease: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    validate_exact_files(model_root, MODEL_FILES)
    fixtures = validate_fixtures(fixture_root)
    sys.path.insert(0, str(environment_root.resolve(strict=True)))
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    before = gpu_snapshot()
    model = None
    results: list[dict[str, Any]] = []
    versions: dict[str, str] = {}
    error = None
    loaded = None
    peak = None
    started = time.monotonic()
    try:
        import espeakng_loader
        import torch
        import torchaudio
        import transformers
        from phonemizer.backend import EspeakBackend
        from phonemizer.backend.espeak.wrapper import EspeakWrapper
        from phonemizer.separator import Separator
        from torchaudio.functional import forced_align, merge_tokens
        from transformers import (
            Wav2Vec2FeatureExtractor,
            Wav2Vec2ForCTC,
            Wav2Vec2PhonemeCTCTokenizer,
        )

        versions = {
            "torch": torch.__version__,
            "torchaudio": torchaudio.__version__,
            "transformers": transformers.__version__,
        }
        if not torch.cuda.is_available():
            raise CanaryError("CUDA is unavailable")
        EspeakWrapper.set_library(espeakng_loader.get_library_path())
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
        backend = EspeakBackend("en-us", preserve_punctuation=False, with_stress=False)
        separator = Separator(phone=" ", word="", syllable="")
        words = word_tokens(TRANSCRIPT, backend, separator)
        target_tokens = [token for word in words for token in word["phoneme_tokens"]]
        tokenizer = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(
            str(model_root), local_files_only=True, do_phonemize=False
        )
        target_ids = tokenizer.convert_tokens_to_ids(target_tokens)
        if tokenizer.unk_token_id in target_ids:
            raise CanaryError("reference phoneme sequence contains unknown model tokens")
        feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
            str(model_root), local_files_only=True
        )
        load_started = time.monotonic()
        model = Wav2Vec2ForCTC.from_pretrained(str(model_root), local_files_only=True)
        model.to("cuda:0").eval()
        torch.cuda.synchronize()
        load_seconds = time.monotonic() - load_started
        loaded = gpu_snapshot()
        for fixture in fixtures:
            waveform, sample_rate = torchaudio.load(fixture["path"])
            waveform = waveform.mean(dim=0)
            if sample_rate != 16000:
                waveform = torchaudio.functional.resample(waveform, sample_rate, 16000)
            duration_seconds = waveform.numel() / 16000.0
            inputs = feature_extractor(
                waveform.numpy(), sampling_rate=16000, return_tensors="pt"
            )
            input_values = inputs.input_values.to("cuda:0")
            attention_mask = inputs.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to("cuda:0")
            inference_started = time.monotonic()
            with torch.inference_mode():
                logits = model(input_values, attention_mask=attention_mask).logits
                log_probs = logits.log_softmax(dim=-1)
            torch.cuda.synchronize()
            inference_seconds = time.monotonic() - inference_started
            peak = gpu_snapshot()
            greedy_ids = ctc_collapse(
                logits[0].argmax(dim=-1).detach().cpu().tolist(), tokenizer.pad_token_id
            )
            similarity = normalized_similarity(greedy_ids, target_ids)
            aligned, scores = forced_align(
                log_probs.detach().cpu(),
                torch.tensor([target_ids], dtype=torch.int32),
                blank=tokenizer.pad_token_id,
            )
            spans = merge_tokens(aligned[0], scores[0], blank=tokenizer.pad_token_id)
            token_records, word_records, monotonic = spans_to_records(
                spans,
                target_tokens,
                words,
                duration_seconds / logits.shape[1],
            )
            mean_posterior = sum(item["posterior"] for item in token_records) / len(
                token_records
            )
            speech_gate = (
                monotonic
                and similarity >= MIN_SPEECH_GREEDY_SIMILARITY
                and mean_posterior >= MIN_SPEECH_ALIGNMENT_POSTERIOR
            )
            passed = speech_gate if fixture["expect_speech"] else not speech_gate
            results.append(
                {
                    **fixture,
                    "input_sample_rate_hz": sample_rate,
                    "model_sample_rate_hz": 16000,
                    "duration_seconds": duration_seconds,
                    "logit_frames": logits.shape[1],
                    "inference_seconds": inference_seconds,
                    "greedy_token_ids": greedy_ids,
                    "greedy_tokens": tokenizer.convert_ids_to_tokens(greedy_ids),
                    "target_token_ids": target_ids,
                    "target_tokens": target_tokens,
                    "greedy_similarity": similarity,
                    "mean_aligned_token_posterior": mean_posterior,
                    "alignment_complete_and_monotonic": monotonic,
                    "speech_gate": speech_gate,
                    "passed": passed,
                    "phoneme_spans": token_records,
                    "word_spans": word_records,
                }
            )
        gate_pass = all(result["passed"] for result in results)
    except Exception as exc:  # noqa: BLE001 - runtime failure must be retained.
        error = f"{type(exc).__name__}: {exc}"
        load_seconds = None
        gate_pass = False
    finally:
        if model is not None:
            del model
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except Exception:  # noqa: BLE001 - process exit is the final cleanup gate.
            pass
    after = gpu_snapshot()
    evidence = {
        "schema_version": "wave64.aqa.wav2vec2_phoneme_alignment_canary.v1",
        "program_id": "W64-AQA",
        "package": {
            "package_id": PACKAGE_ID,
            "repository": UPSTREAM_REPOSITORY,
            "revision": UPSTREAM_REVISION,
            "model_root": str(model_root),
            "file_count": len(MODEL_FILES),
            "weight_sha256": MODEL_FILES["pytorch_model.bin"][1],
        },
        "lease": lease,
        "prospective_thresholds": {
            "minimum_speech_greedy_similarity": MIN_SPEECH_GREEDY_SIMILARITY,
            "minimum_speech_alignment_posterior": MIN_SPEECH_ALIGNMENT_POSTERIOR,
            "negative_control_policy": "speech gate must be false",
            "post_result_tuning_allowed": False,
        },
        "transcript": TRANSCRIPT,
        "status": "PASS_EXACT_FOUR_FIXTURE_MATRIX" if gate_pass else "FAIL_MATRIX_OR_RUNTIME",
        "fixtures": results,
        "runtime": {
            "versions": versions,
            "device": "cuda:0",
            "dtype": "float32",
            "duration_seconds": time.monotonic() - started,
            "load_seconds": load_seconds,
            "gpu_before": before,
            "gpu_loaded": loaded,
            "gpu_peak_observed": peak,
            "gpu_after_in_process_cleanup": after,
        },
        "error": error,
        "authority": {
            "package_identity": True,
            "current_pod_model_load": error is None,
            "current_pod_audio_inference": error is None,
            "exact_matrix_alignment": gate_pass,
            "general_forced_alignment": False,
            "speaker_identity": False,
            "general_audio_semantics": False,
            "operational_activation": False,
            "product_promotion": False,
        },
    }
    return evidence, 0 if gate_pass else 1


def run_isolated(
    *,
    model_root: Path,
    fixture_root: Path,
    environment_root: Path,
    lease: dict[str, Any],
    output_path: Path,
) -> tuple[dict[str, Any], int]:
    validate_exact_files(model_root, MODEL_FILES)
    validate_fixtures(fixture_root)
    before = gpu_snapshot()
    worker_output = output_path.parent / f".{output_path.name}.{uuid.uuid4().hex}.worker"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--inner-worker",
        "--model-root",
        str(model_root),
        "--fixture-root",
        str(fixture_root),
        "--environment-root",
        str(environment_root),
        "--lease-id",
        lease["lease_id"],
        "--lease-profile",
        lease["profile"],
        "--lease-expires-at",
        lease["expires_at"],
        "--output",
        str(worker_output),
    ]
    completed = subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=900
    )
    try:
        if not worker_output.is_file():
            raise CanaryError(
                "isolated worker emitted no evidence; "
                f"returncode={completed.returncode}; stderr={completed.stderr[-1000:]}"
            )
        evidence = json.loads(worker_output.read_text(encoding="utf-8"))
    finally:
        worker_output.unlink(missing_ok=True)
    time.sleep(2)
    after = gpu_snapshot()
    delta = after["used_mib"] - before["used_mib"]
    cleanup_pass = delta <= 1024
    evidence["schema_version"] = "wave64.aqa.wav2vec2_phoneme_alignment_canary.v2"
    evidence["runtime"].update(
        {
            "gpu_before_worker_process": before,
            "gpu_after_worker_process_exit": after,
            "process_exit_cleanup_delta_mib": delta,
            "process_exit_cleanup_pass": cleanup_pass,
            "worker_returncode": completed.returncode,
            "worker_stdout": completed.stdout[-4000:],
            "worker_stderr": completed.stderr[-4000:],
        }
    )
    matrix_pass = evidence["status"] == "PASS_EXACT_FOUR_FIXTURE_MATRIX"
    passed = matrix_pass and cleanup_pass and completed.returncode == 0
    evidence["status"] = (
        "PASS_EXACT_MATRIX_AND_PROCESS_EXIT_CLEANUP"
        if passed
        else "FAIL_MATRIX_RUNTIME_OR_PROCESS_EXIT_CLEANUP"
    )
    evidence["authority"]["exact_matrix_alignment"] = passed
    return evidence, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--lease-id", required=True)
    parser.add_argument("--lease-profile", required=True)
    parser.add_argument("--lease-expires-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; runtime evidence is immutable")
    try:
        lease = validate_lease(
            args.lease_id, args.lease_profile, args.lease_expires_at
        )
        if args.inner_worker:
            evidence, exit_code = run_worker(
                model_root=args.model_root,
                fixture_root=args.fixture_root,
                environment_root=args.environment_root,
                lease=lease,
            )
        else:
            evidence, exit_code = run_isolated(
                model_root=args.model_root,
                fixture_root=args.fixture_root,
                environment_root=args.environment_root,
                lease=lease,
                output_path=args.output,
            )
    except (CanaryError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": evidence["status"], "output": str(args.output)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
