#!/usr/bin/env python3
"""Run one exact, lease-bound MIT AST AudioSet calibration partition."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import wave
from typing import Any


class CanaryError(RuntimeError):
    """Raised when an immutable identity or execution boundary fails."""


MODEL_FILES = {
    ".gitattributes": (1477, "git_blob_sha1", "c7d9f3332a950355d5a77d85000f05e6f45435ea"),
    "README.md": (1165, "git_blob_sha1", "fc4ece98b629cab4731db057bebdc4240fda9239"),
    "config.json": (26763, "git_blob_sha1", "9b822c630bc1a61312ac702cca4d8fb5a524e729"),
    "model.safetensors": (346404948, "sha256", "ae0c1e2ad4e1381d851fa9bf298ba13ebc9c5a914cdee2dbe427a6583869924d"),
    "preprocessor_config.json": (297, "git_blob_sha1", "d93e9e561c374604096fd5868c97e08130638f72"),
    ".w64_aqa_install_receipt.json": (1546, "sha256", "45acf496dee55bce1bfe906e5083347bb6c84b8946ce670b9e92f151a4afe6fa"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()  # noqa: S324


def validate_model_package(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir() or root.is_symlink():
        raise CanaryError("model root is absent or unsafe")
    observed = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise CanaryError(f"model member symlink is forbidden: {path}")
        if path.is_file():
            observed[path.relative_to(root).as_posix()] = path
    if set(observed) != set(MODEL_FILES):
        raise CanaryError("model package file-set mismatch")
    records = []
    for name, (size, kind, expected) in MODEL_FILES.items():
        path = observed[name]
        identity = sha256_file(path) if kind == "sha256" else git_blob_sha1(path)
        if path.stat().st_size != size or identity != expected:
            raise CanaryError(f"model package identity mismatch: {name}")
        records.append({"path": name, "bytes": size, "identity_kind": kind, "identity": identity})
    return records


def validate_lease(receipt: dict[str, Any], admission: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    expected = admission["lease"]
    if "lease_token" in receipt or "token" in receipt:
        raise CanaryError("lease receipt must not contain a token")
    if receipt.get("valid") is not True:
        raise CanaryError("coordinator receipt is not valid")
    for field in ("project", "profile"):
        if receipt.get(field) != expected[field]:
            raise CanaryError(f"coordinator receipt {field} mismatch")
    if receipt.get("lease_mode") != expected["mode"]:
        raise CanaryError("coordinator receipt lease_mode mismatch")
    if float(receipt.get("reserved_peak_gib", 0)) < expected["minimum_reserved_peak_gib"]:
        raise CanaryError("coordinator reservation is too small")
    expiry = datetime.fromisoformat(str(receipt.get("expires_at", "")).replace("Z", "+00:00"))
    if expiry <= (now or datetime.now(timezone.utc)):
        raise CanaryError("coordinator receipt is expired")
    return {key: receipt[key] for key in ("valid", "lease_id", "project", "profile", "lease_mode", "reserved_peak_gib", "safety_reserve_gib", "expires_at")}


def gpu_snapshot() -> dict[str, Any]:
    completed = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu", "--format=csv,noheader,nounits"],
        check=True, capture_output=True, text=True, timeout=20,
    )
    rows = [row.strip() for row in completed.stdout.splitlines() if row.strip()]
    if len(rows) != 1:
        raise CanaryError("exactly one GPU is required")
    name, total, used, free, utilization = [part.strip() for part in rows[0].split(",")]
    return {"name": name, "total_mib": int(total), "used_mib": int(used), "free_mib": int(free), "utilization_percent": int(utilization)}


def host_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise CanaryError("MemAvailable is absent")


def validate_capacity(admission: dict[str, Any], gpu: dict[str, Any], host_bytes: int) -> None:
    lease = admission["lease"]
    if gpu["free_mib"] < lease["required_free_vram_mib"]:
        raise CanaryError("free VRAM is below the admitted minimum")
    if host_bytes < lease["minimum_host_available_bytes"]:
        raise CanaryError("available host memory is below the admitted minimum")


def validate_environment(admission: dict[str, Any]) -> dict[str, str]:
    expected = admission["environment"]
    if Path(sys.prefix).as_posix() != expected["root"]:
        raise CanaryError("canary is not running in the admitted environment")
    versions = {name: importlib.metadata.version(name) for name in expected["required_distributions"]}
    if versions != expected["required_distributions"]:
        raise CanaryError("installed distribution versions do not match admission")
    observed_python = ".".join(str(value) for value in sys.version_info[:3])
    if observed_python != expected["python"]:
        raise CanaryError("Python version does not match admission")
    return versions


def load_plan(admission: dict[str, Any], project_root: Path) -> dict[str, Any]:
    path = project_root / admission["plan"]["path"]
    if not path.is_file() or sha256_file(path) != admission["plan"]["sha256"]:
        raise CanaryError("expanded event plan identity mismatch")
    plan = json.loads(path.read_text(encoding="utf-8"))
    if [case["case_id"] for case in plan["event_cases"]] != admission["plan"]["case_ids"]:
        raise CanaryError("event case order or membership mismatch")
    return plan


def validate_partition(plan: dict[str, Any], partition: str, calibration: dict[str, Any] | None, admission: dict[str, Any]) -> list[dict[str, Any]]:
    cases = [case for case in plan["event_cases"] if case["partition"] == partition]
    if partition == "held_out":
        if not calibration or calibration.get("status") != "PASS_EXACT_EVENT_CALIBRATION_PARTITION":
            raise CanaryError("held-out partition requires a passing calibration receipt")
        if calibration.get("plan_sha256") != admission["plan"]["sha256"] or calibration.get("model_revision") != admission["model"]["revision"]:
            raise CanaryError("calibration receipt identity mismatch")
    return cases


def family_match(family: str, label: str) -> bool:
    normalized = label.casefold().replace("_", " ").replace("-", " ")
    aliases = {
        "room ambience": ("inside, small room", "inside, large room", "room tone", "ambient"),
        "background noise": ("background noise", "noise"),
        "cloth movement": ("rustle", "rustling", "clothing", "fabric"),
        "body movement": ("walk", "movement", "shuffle"),
        "rustling": ("rustle", "rustling"),
        "speech": ("speech", "conversation", "narration", "male speech", "female speech"),
        "overlapping speech": ("conversation", "speech", "babbling", "chatter"),
    }
    return any(token in normalized for token in aliases[family])


def decode_pcm(path: Path) -> tuple[Any, int]:
    import numpy as np
    with wave.open(str(path), "rb") as handle:
        channels, width, rate, frames = handle.getnchannels(), handle.getsampwidth(), handle.getframerate(), handle.getnframes()
        raw = handle.readframes(frames)
    if width == 2:
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        values = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        packed = values[:, 0] | (values[:, 1] << 8) | (values[:, 2] << 16)
        audio = ((packed ^ 0x800000) - 0x800000).astype(np.float32) / 8388608.0
    else:
        raise CanaryError(f"unsupported PCM sample width: {width}")
    return audio.reshape(-1, channels).mean(axis=1), rate


def run_worker(admission: dict[str, Any], lease: dict[str, Any], project_root: Path, partition: str, calibration: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification

    files = validate_model_package(Path(admission["model"]["root"]))
    versions = validate_environment(admission)
    plan = load_plan(admission, project_root)
    cases = validate_partition(plan, partition, calibration, admission)
    validate_lease(lease, admission)
    before = gpu_snapshot()
    host_before = host_available_bytes()
    validate_capacity(admission, before, host_before)
    os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false", "PYTHONDONTWRITEBYTECODE": "1"})
    model_root = Path(admission["model"]["root"])
    sources = {source["source_id"]: source for source in plan["sources"]}
    model = None
    results = []
    loaded = None
    error = None
    started = time.monotonic()
    try:
        extractor = ASTFeatureExtractor.from_pretrained(model_root, local_files_only=True)
        model = ASTForAudioClassification.from_pretrained(model_root, local_files_only=True, use_safetensors=True).to("cuda:0", dtype=torch.float16).eval()
        torch.cuda.synchronize()
        loaded = gpu_snapshot()
        for case in cases:
            source = sources[case["source_id"]]
            path = project_root / source["relative_path"]
            if not path.is_file() or path.is_symlink() or path.stat().st_size != source["bytes"] or sha256_file(path) != source["sha256"]:
                raise CanaryError(f"source identity mismatch: {source['source_id']}")
            audio, rate = decode_pcm(path)
            inputs = extractor(audio, sampling_rate=rate, return_tensors="pt")
            with torch.inference_mode():
                logits = model(inputs["input_values"].to("cuda:0", dtype=torch.float16)).logits[0].float().cpu()
            probabilities = torch.softmax(logits, dim=-1)
            top = torch.topk(probabilities, k=admission["execution"]["top_k"])
            predictions = [{"rank": index + 1, "label": model.config.id2label[int(label)], "score": float(score)} for index, (score, label) in enumerate(zip(top.values, top.indices, strict=True))]
            family_hits = {family: [item["rank"] for item in predictions if family_match(family, item["label"])] for family in case["required_label_families"]}
            top3_pass = any(ranks and min(ranks) <= admission["execution"]["calibration_top_k_gate"] for ranks in family_hits.values())
            results.append({"case": case, "source": {"source_id": source["source_id"], "sha256": source["sha256"], "bytes": source["bytes"]}, "predictions": predictions, "family_hits": family_hits, "calibration_top3_gate": top3_pass})
        passed = all(item["calibration_top3_gate"] for item in results) if partition == "calibration" else True
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        passed = False
    finally:
        if model is not None:
            del model
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    status = "PASS_EXACT_EVENT_CALIBRATION_PARTITION" if passed and partition == "calibration" else "PASS_EXACT_EVENT_HELD_OUT_MEASUREMENT" if passed else "FAIL_EVENT_PARTITION_OR_RUNTIME"
    return {"schema_version": "wave64.aqa.mit_ast_event_canary_worker.v1", "program_id": "W64-AQA", "status": status, "partition": partition, "plan_sha256": admission["plan"]["sha256"], "model_revision": admission["model"]["revision"], "model_files": files, "environment_versions": versions, "lease": validate_lease(lease, admission), "cases": results, "runtime": {"duration_seconds": time.monotonic() - started, "gpu_before": before, "gpu_loaded": loaded, "gpu_after_in_process_cleanup": gpu_snapshot(), "host_available_before_bytes": host_before}, "error": error, "authority": {"exact_partition_measurement": passed, "general_audio_event_recognition": False, "beats_equivalence": False, "operational_activation": False, "product_promotion": False}}, 0 if passed else 1


def finalize(worker: dict[str, Any], before: dict[str, Any], after: dict[str, Any], returncode: int, tolerance: int) -> tuple[dict[str, Any], int]:
    cleanup_delta = after["used_mib"] - before["used_mib"]
    passed = returncode == 0 and worker.get("error") is None and cleanup_delta <= tolerance and worker["status"].startswith("PASS_")
    worker["schema_version"] = "wave64.aqa.mit_ast_event_canary.v1"
    worker["runtime"].update({"gpu_before_worker": before, "gpu_after_worker_exit": after, "process_exit_cleanup_delta_mib": cleanup_delta, "process_exit_cleanup_pass": cleanup_delta <= tolerance, "worker_returncode": returncode})
    if not passed:
        worker["status"] = "FAIL_EVENT_PARTITION_RUNTIME_OR_PROCESS_EXIT_CLEANUP"
        worker["authority"]["exact_partition_measurement"] = False
    return worker, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--lease-receipt", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--partition", choices=("calibration", "held_out"), required=True)
    parser.add_argument("--calibration-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; canary evidence is immutable")
    admission = json.loads(args.admission.read_text(encoding="utf-8"))
    lease = json.loads(args.lease_receipt.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration_receipt.read_text(encoding="utf-8")) if args.calibration_receipt else None
    validate_lease(lease, admission)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.inner_worker:
        result, code = run_worker(admission, lease, args.project_root, args.partition, calibration)
    else:
        validate_model_package(Path(admission["model"]["root"]))
        plan = load_plan(admission, args.project_root)
        validate_partition(plan, args.partition, calibration, admission)
        before = gpu_snapshot()
        worker_path = args.output.parent / f".{args.output.name}.{uuid.uuid4().hex}.worker"
        command = [sys.executable, str(Path(__file__).resolve()), "--inner-worker", "--admission", str(args.admission), "--lease-receipt", str(args.lease_receipt), "--project-root", str(args.project_root), "--partition", args.partition, "--output", str(worker_path)]
        if args.calibration_receipt:
            command.extend(["--calibration-receipt", str(args.calibration_receipt)])
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=admission["execution"]["timeout_seconds"])
        if not worker_path.is_file():
            raise CanaryError(f"worker emitted no evidence: {completed.stderr[-1000:]}")
        try:
            worker = json.loads(worker_path.read_text(encoding="utf-8"))
        finally:
            worker_path.unlink(missing_ok=True)
        time.sleep(admission["execution"]["post_exit_wait_seconds"])
        result, code = finalize(worker, before, gpu_snapshot(), completed.returncode, admission["execution"]["cleanup_tolerance_mib"])
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output)}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
