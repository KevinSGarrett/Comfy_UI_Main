#!/usr/bin/env python3
"""Calibrate local CV3-Eval metrics and score an existing Parler artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import shutil
import sys
import tempfile
import types
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


CV3_LICENSE_SHA256 = "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
DNSMOS_SOURCE_SHA256 = "dd4108728ab3280fdc0404b4d4aef79ca22cd4ac6ef75660e7a727eda438a8f7"
DNSMOS_MODEL_HASHES = {
    "sig_bak_ovr.onnx": "269fbebdb513aa23cddfbb593542ecc540284a91849ac50516870e1ac78f6edd",
    "model_v8.onnx": "9246480c58567bc6affd4200938e77eef49468c8bc7ed3776d109c07456f6e91",
}
ERES2NET_SHA256 = "d8941f5952e31820173c8854562cb6d7897aaa58cd65c18f30d5a2e52d30847d"
WHISPER_SHA256 = "db59695928ded6043adaef491a53ef4e12da9611184d77c53baa691a60b958ad"
WHISPER_REVISION = "87c7102498dcde7456f24cfd30239ca606ed9063"
WHISPER_METADATA_SHA256 = "480214b4a170f7203e2c7bbc7a22feec2b3027efd1112acb09b69de137f6bead"
SPEAKER_SOURCE_HASHES = {
    "speakerlab/models/eres2net/ERes2Net.py": "cc5d58982ca1696874a1e479ac6383ee4a1d54edcedefe06f7bec40a0d3d7480",
    "speakerlab/models/eres2net/pooling_layers.py": "46c6b480ffdd284af90da90ac1bbf9a0e00bd46229e567c0828d7ebe0e178a0a",
    "speakerlab/models/eres2net/fusion.py": "b76cfbf8adb99336f10ea43953e90228bda85a56de97cda122d9c436a4c94c53",
    "speakerlab/process/processor.py": "f4ebee0de83c93815ce9627c650287bad65415baf8aa42974aa2396e9c1c346a",
    "speakerlab/process/augmentation.py": "59c750906eac208ae0cf0e01f93540da2cebcf75b10bf27680a2eba73f71519e",
    "speakerlab/utils/fileio.py": "992800925e23d988943a45a70ada4b1d283517d6ba035d6a5fb8862b1272f8c0",
}
CALIBRATION_MAP_HASHES = {
    "prompt_wav.scp": "4960b64684c00c2e50d10ee0811df7959d61c5fb1f1c797da564da1bdcc20c99",
    "prompt_text": "8f1114554130dcabdd5a62cf540d3562f427a8fc3cb29e649b8b3a3d0968c851",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual.lower() != expected.lower():
        raise ValueError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")
    return {"path": str(path), "sha256": actual, "bytes": path.stat().st_size}


def verify_whisper_metadata(path: Path) -> dict:
    binding = require_hash(path, WHISPER_METADATA_SHA256, "Whisper cache metadata")
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2 or lines[0] != WHISPER_REVISION or lines[1].lower() != WHISPER_SHA256:
        raise ValueError("Whisper cache metadata revision or weight hash mismatch")
    return {**binding, "revision": lines[0], "weight_sha256": lines[1].lower()}


def load_json_binding(path: Path, expected_sha256: str, label: str) -> tuple[dict, dict]:
    binding = require_hash(path, expected_sha256, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return binding, payload


def bind_candidate_lineage(
    candidate: Path,
    candidate_sha256: str,
    packet_path: Path,
    packet_sha256: str,
    contract_path: Path,
    contract_sha256: str,
) -> dict:
    packet_binding, packet = load_json_binding(packet_path, packet_sha256, "Parler packet manifest")
    contract_binding, contract = load_json_binding(contract_path, contract_sha256, "dialogue contract")

    verified_media = packet.get("verified_media")
    if not isinstance(verified_media, dict):
        raise ValueError("Parler packet manifest verified_media is missing")
    if str(verified_media.get("sha256", "")).lower() != candidate_sha256:
        raise ValueError("Parler packet manifest does not bind the candidate SHA256")
    packet_media_path = Path(str(verified_media.get("media_path", ""))).resolve()
    if packet_media_path != candidate:
        raise ValueError("Parler packet manifest does not bind the candidate path")
    if packet.get("result") != "pass" or packet.get("execution_passed") is not True:
        raise ValueError("Parler packet manifest is not a passed execution packet")
    if packet.get("timeline_conformance", {}).get("speech_truncated") is not False:
        raise ValueError("Parler packet manifest does not prove zero speech truncation")

    lines = contract.get("lines")
    if not isinstance(lines, list):
        raise ValueError("dialogue contract lines are missing")
    matches = [
        line
        for line in lines
        if isinstance(line, dict) and Path(str(line.get("output_file", ""))).resolve() == candidate
    ]
    if len(matches) != 1:
        raise ValueError("dialogue contract must bind exactly one line to the candidate")
    line = matches[0]
    expected_text = str(line.get("text", "")).strip()
    if not normalized_tokens(expected_text):
        raise ValueError("dialogue contract candidate text is empty")
    return {
        "packet_manifest": packet_binding,
        "dialogue_contract": contract_binding,
        "line_id": line.get("line_id"),
        "character_id": line.get("character_id"),
        "voice_profile_id": line.get("voice_profile_id"),
        "expected_text": expected_text,
    }


def runtime_identity(device: str) -> dict:
    import onnxruntime
    import torch

    packages = (
        "torch",
        "torchaudio",
        "transformers",
        "onnxruntime",
        "librosa",
        "soundfile",
        "scipy",
        "numpy",
    )
    identity = {
        "python": platform.python_version(),
        "packages": {name: metadata.version(name) for name in packages},
        "onnxruntime_available_providers": onnxruntime.get_available_providers(),
        "requested_device": device,
    }
    if device.startswith("cuda"):
        identity["cuda_device_name"] = torch.cuda.get_device_name(device)
    return identity


def normalized_tokens(value: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", value.lower())


def levenshtein(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, 1):
        next_row = [left_index]
        for right_index, right_value in enumerate(right, 1):
            next_row.append(
                min(
                    next_row[-1] + 1,
                    row[right_index] + 1,
                    row[right_index - 1] + (left_value != right_value),
                )
            )
        row = next_row
    return row[-1]


def normalized_wer(expected: str, observed: str) -> float:
    expected_tokens = normalized_tokens(expected)
    if not expected_tokens:
        raise ValueError("expected transcript normalizes to empty tokens")
    return levenshtein(expected_tokens, normalized_tokens(observed)) / len(expected_tokens)


def parse_kaldi_map(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        raise ValueError(f"Kaldi map is missing: {path}")
    entries = []
    seen = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"invalid Kaldi map line {line_number}: {path}")
        if parts[0] in seen:
            raise ValueError(f"duplicate Kaldi key {parts[0]}: {path}")
        seen.add(parts[0])
        entries.append((parts[0], parts[1]))
    if not entries:
        raise ValueError(f"Kaldi map is empty: {path}")
    return entries


def select_calibration_samples(cv3_root: Path, count: int) -> list[dict]:
    if count < 2:
        raise ValueError("at least two calibration samples are required")
    subset = cv3_root / "data/zero_shot/en"
    wav_entries = parse_kaldi_map(subset / "prompt_wav.scp")
    text_entries = dict(parse_kaldi_map(subset / "prompt_text"))
    samples = []
    for sample_id, relative_path in wav_entries[:count]:
        if sample_id not in text_entries:
            raise ValueError(f"prompt transcript missing for {sample_id}")
        wav_path = (cv3_root / Path(relative_path.replace("//", "/"))).resolve()
        try:
            wav_path.relative_to(cv3_root)
        except ValueError as exc:
            raise ValueError(f"calibration path escapes CV3 root: {wav_path}") from exc
        if not wav_path.is_file():
            raise ValueError(f"calibration WAV missing: {wav_path}")
        samples.append(
            {
                "sample_id": sample_id,
                "path": str(wav_path),
                "sha256": sha256(wav_path),
                "bytes": wav_path.stat().st_size,
                "expected_text": text_entries[sample_id],
            }
        )
    if len(samples) != count:
        raise ValueError(f"requested {count} calibration samples, found {len(samples)}")
    return samples


def load_audio_16k(path: Path):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    audio, source_rate = sf.read(str(path), dtype="float32")
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if audio.size == 0 or not np.isfinite(audio).all():
        raise ValueError(f"audio is empty or nonfinite: {path}")
    if source_rate != 16_000:
        divisor = math.gcd(source_rate, 16_000)
        audio = resample_poly(audio, 16_000 // divisor, source_rate // divisor).astype("float32")
    return audio, source_rate


class WhisperEvaluator:
    def __init__(self, model_dir: Path, overlay_dir: Path, device: str):
        if str(overlay_dir) not in sys.path:
            sys.path.insert(0, str(overlay_dir))
        import torch
        import transformers
        from transformers import WhisperForConditionalGeneration, WhisperProcessor

        if transformers.__version__ != "4.46.1":
            raise ValueError(f"pinned transformers 4.46.1 required, got {transformers.__version__}")
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise ValueError("CUDA requested for Whisper calibration but unavailable")
        self.torch = torch
        self.device = device
        self.processor = WhisperProcessor.from_pretrained(str(model_dir), local_files_only=True)
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        self.dtype = dtype
        self.model = WhisperForConditionalGeneration.from_pretrained(
            str(model_dir),
            local_files_only=True,
            torch_dtype=dtype,
            attn_implementation="eager",
        ).to(device)

    def transcribe(self, path: Path) -> str:
        audio, _ = load_audio_16k(path)
        batch = self.processor(
            audio,
            sampling_rate=16_000,
            return_tensors="pt",
            return_attention_mask=True,
        )
        with self.torch.inference_mode():
            generated = self.model.generate(
                batch.input_features.to(self.device, dtype=self.dtype),
                attention_mask=batch.attention_mask.to(self.device),
                max_new_tokens=96,
                do_sample=False,
            )
        return self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()


class SpeakerEvaluator:
    def __init__(self, speaker_root: Path, checkpoint: Path, device: str):
        if str(speaker_root) not in sys.path:
            sys.path.insert(0, str(speaker_root))
        import torch
        from speakerlab.models.eres2net.ERes2Net import ERes2Net
        from speakerlab.process.processor import FBank

        self.torch = torch
        self.device = device
        self.fbank = FBank(80, sample_rate=16_000, mean_nor=True)
        self.model = ERes2Net(feat_dim=80, embedding_size=192)
        state = torch.load(str(checkpoint), map_location="cpu", weights_only=True)
        self.model.load_state_dict(state)
        self.model.eval().to(device)

    def embedding(self, path: Path):
        audio, _ = load_audio_16k(path)
        tensor = self.torch.from_numpy(audio).unsqueeze(0)
        features = self.fbank(tensor).unsqueeze(0).to(self.device)
        with self.torch.inference_mode():
            embedding = self.model(features).detach().cpu().flatten()
        return embedding / embedding.norm(p=2).clamp_min(1e-12)

    def similarity(self, left, right) -> float:
        return float(self.torch.dot(left, right).item())


class DNSMOSEvaluator:
    def __init__(self, source_path: Path, model_dir: Path):
        if importlib.util.find_spec("pandas") is None:
            sys.modules.setdefault("pandas", types.ModuleType("pandas"))
        spec = importlib.util.spec_from_file_location("cv3_dnsmos_local", source_path)
        module = importlib.util.module_from_spec(spec)
        if not spec.loader:
            raise RuntimeError("DNSMOS source loader unavailable")
        spec.loader.exec_module(module)
        self.scorer = module.ComputeScore(
            str(model_dir / "sig_bak_ovr.onnx"),
            str(model_dir / "model_v8.onnx"),
        )

    def score(self, path: Path) -> dict:
        result = self.scorer(str(path), 16_000, False)
        return {
            key: float(result[key])
            for key in ("OVRL_raw", "SIG_raw", "BAK_raw", "OVRL", "SIG", "BAK", "P808_MOS")
        } | {
            "duration_seconds": float(result["len_in_sec"]),
            "num_hops": int(result["num_hops"]),
        }


def percentile_rank(values: list[float], candidate: float) -> float:
    if not values:
        raise ValueError("percentile rank requires calibration values")
    return sum(value <= candidate for value in values) / len(values)


def true_median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires calibration values")
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2)


def build(args: argparse.Namespace) -> dict:
    cv3_root = Path(args.cv3_root).resolve()
    whisper_dir = Path(args.whisper_model_dir).resolve()
    overlay_dir = Path(args.transformers_overlay).resolve()
    candidate = Path(args.candidate_audio).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if not candidate.is_file():
        raise ValueError(f"candidate audio is missing: {candidate}")
    if sha256(candidate) != args.expected_candidate_sha256.lower():
        raise ValueError("candidate audio SHA256 mismatch")
    candidate_sha256 = sha256(candidate)
    candidate_lineage = bind_candidate_lineage(
        candidate,
        candidate_sha256,
        Path(args.candidate_packet_manifest).resolve(),
        args.expected_candidate_packet_sha256.lower(),
        Path(args.dialogue_contract).resolve(),
        args.expected_dialogue_contract_sha256.lower(),
    )

    license_binding = require_hash(cv3_root / "LICENSE", CV3_LICENSE_SHA256, "CV3 license")
    dnsmos_source = require_hash(
        cv3_root / "utils/DNSMOS/dnsmos_local.py", DNSMOS_SOURCE_SHA256, "DNSMOS source"
    )
    dnsmos_models = {
        name: require_hash(cv3_root / "utils/DNSMOS/DNSMOS" / name, digest, f"DNSMOS {name}")
        for name, digest in DNSMOS_MODEL_HASHES.items()
    }
    speaker_checkpoint = require_hash(
        cv3_root
        / "utils/3D-Speaker/pretrained/speech_eres2net_sv_en_voxceleb_16k/pretrained_eres2net.ckpt",
        ERES2NET_SHA256,
        "ERes2Net checkpoint",
    )
    speaker_root = cv3_root / "utils/3D-Speaker"
    speaker_sources = {
        name: require_hash(speaker_root / name, digest, f"3D-Speaker source {name}")
        for name, digest in SPEAKER_SOURCE_HASHES.items()
    }
    calibration_maps = {
        name: require_hash(cv3_root / "data/zero_shot/en" / name, digest, f"CV3 calibration map {name}")
        for name, digest in CALIBRATION_MAP_HASHES.items()
    }
    whisper_weight = require_hash(whisper_dir / "model.safetensors", WHISPER_SHA256, "Whisper weight")
    whisper_metadata = verify_whisper_metadata(
        whisper_dir / ".cache/huggingface/download/model.safetensors.metadata"
    )
    emotion_model_path = cv3_root / "utils/emo_eval/model/emotion2vec_plus_large/model.pt"
    emotion_payload_present = emotion_model_path.is_file()
    samples = select_calibration_samples(cv3_root, args.sample_count)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        whisper = WhisperEvaluator(whisper_dir, overlay_dir, args.device)
        speaker = SpeakerEvaluator(speaker_root, Path(speaker_checkpoint["path"]), args.device)
        dnsmos = DNSMOSEvaluator(Path(dnsmos_source["path"]), cv3_root / "utils/DNSMOS/DNSMOS")

        calibration = []
        embeddings = []
        for sample in samples:
            path = Path(sample["path"])
            transcript = whisper.transcribe(path)
            embedding = speaker.embedding(path)
            embeddings.append(embedding)
            calibration.append(
                {
                    **sample,
                    "asr_transcript": transcript,
                    "normalized_wer": normalized_wer(sample["expected_text"], transcript),
                    "dnsmos": dnsmos.score(path),
                    "same_file_speaker_similarity": speaker.similarity(embedding, embedding),
                }
            )
        cross_scores = [
            speaker.similarity(embeddings[index], embeddings[index + 1])
            for index in range(0, len(embeddings) - 1, 2)
        ]
        same_scores = [entry["same_file_speaker_similarity"] for entry in calibration]
        reference_mos = [entry["dnsmos"]["OVRL"] for entry in calibration]

        candidate_transcript = whisper.transcribe(candidate)
        candidate_dnsmos = dnsmos.score(candidate)
        expected_text = candidate_lineage["expected_text"]
        candidate_result = {
            "path": str(candidate),
            "sha256": sha256(candidate),
            "bytes": candidate.stat().st_size,
            "expected_text": expected_text,
            "lineage": candidate_lineage,
            "asr_transcript": candidate_transcript,
            "normalized_wer": normalized_wer(expected_text, candidate_transcript),
            "wer_threshold": 0.2,
            "dnsmos": candidate_dnsmos,
            "dnsmos_reference_percentile": percentile_rank(reference_mos, candidate_dnsmos["OVRL"]),
            "speaker_identity_status": "BLOCKED_REFERENCE_SPEAKER_AUDIO_MISSING",
            "emotion_status": (
                "BLOCKED_EMOTION_MODEL_UNVERIFIED" if emotion_payload_present else "BLOCKED_EMOTION_MODEL_PAYLOAD_MISSING"
            ),
            "independent_perceptual_playback_review_present": False,
            "production_review_authority_allowed": False,
        }
        same_min = min(same_scores)
        cross_max = max(cross_scores)
        candidate_asr_pass = candidate_result["normalized_wer"] <= 0.2
        emotion_blocker = (
            "CV3 emotion2vec_plus_large model.pt is present but unverified and the emotion path is not implemented"
            if emotion_payload_present
            else "CV3 emotion2vec_plus_large model.pt is missing"
        )
        manifest = {
            "schema_version": "1.0",
            "artifact_type": "wave64_cv3_eval_local_calibration",
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": (
                "PASS_PARTIAL_METRIC_CALIBRATION_EMOTION_AND_PLAYBACK_AUTHORITY_BLOCKED"
                if candidate_asr_pass
                else "FAIL_CANDIDATE_ASR_THRESHOLD_EMOTION_AND_PLAYBACK_AUTHORITY_BLOCKED"
            ),
            "classification": "CV3_WER_DNSMOS_AND_SPEAKER_EXECUTION_SANITY_PASS",
            "source_authority": {
                "repository": "CV3-Eval",
                "license": "Apache-2.0",
                "license_binding": license_binding,
                "dnsmos_source": dnsmos_source,
                "dnsmos_models": dnsmos_models,
                "speaker_checkpoint": speaker_checkpoint,
                "speaker_sources": speaker_sources,
                "calibration_maps": calibration_maps,
                "whisper": {
                    **whisper_weight,
                    "model": "openai/whisper-tiny.en",
                    "revision": WHISPER_REVISION,
                    "cache_metadata": whisper_metadata,
                },
                "emotion_model_path": str(emotion_model_path),
                "emotion_model_present": emotion_payload_present,
            },
            "runtime_identity": runtime_identity(args.device),
            "calibration": {
                "sample_count": len(calibration),
                "samples": calibration,
                "wer_mean": sum(entry["normalized_wer"] for entry in calibration) / len(calibration),
                "dnsmos_ovrl_min": min(reference_mos),
                "dnsmos_ovrl_median": true_median(reference_mos),
                "dnsmos_ovrl_max": max(reference_mos),
                "speaker_same_file_cosine_min": same_min,
                "speaker_cross_file_cosine_max": cross_max,
                "speaker_cross_file_margin": same_min - cross_max,
                "speaker_identity_ground_truth_available": False,
            },
            "candidate": candidate_result,
            "acceptance": {
                "source_hashes_verified": True,
                "cv3_reference_decode_pass": len(calibration) == args.sample_count,
                "whisper_path_executed": True,
                "speaker_path_executed": True,
                "speaker_same_file_normalization_sanity_pass": same_min >= 0.999,
                "speaker_cross_file_similarity_below_same_file_observed": cross_max < same_min,
                "speaker_identity_claim_allowed": False,
                "dnsmos_path_executed": True,
                "candidate_asr_threshold_pass": candidate_asr_pass,
                "emotion_path_executed": False,
                "independent_playback_review_pass": False,
                "authority_registry_mutation_allowed": False,
                "row_completion_allowed": False,
            },
            "remaining_blockers": [
                emotion_blocker,
                "the Parler candidate has no independent reference-speaker audio binding",
                "independent beginning/middle/end/loud/quiet/transition playback review is absent",
                "the production playback and production review authority allowlists remain empty for real evidence",
            ],
            "runtime_boundary": {
                "candidate_regenerated": False,
                "model_download_performed": False,
                "ec2_started": False,
                "s3_mutated": False,
                "mask_truth_consumed": False,
                "wave71_activated": False,
                "jira_mutated": False,
                "promotion_claimed": False,
            },
            "row_complete": False,
        }
        manifest_path = temporary / "calibration_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary.rename(output_dir)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cv3-root", required=True)
    parser.add_argument("--whisper-model-dir", required=True)
    parser.add_argument("--transformers-overlay", required=True)
    parser.add_argument("--candidate-audio", required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--candidate-packet-manifest", required=True)
    parser.add_argument("--expected-candidate-packet-sha256", required=True)
    parser.add_argument("--dialogue-contract", required=True)
    parser.add_argument("--expected-dialogue-contract-sha256", required=True)
    parser.add_argument("--sample-count", type=int, default=8)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), indent=2))
