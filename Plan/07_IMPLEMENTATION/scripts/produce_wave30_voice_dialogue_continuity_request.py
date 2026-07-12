#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import wave
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PROOF_FILES = {
    "asr_proof": "asr_proof.json",
    "speaker_proof": "speaker_proof.json",
    "emotion_proof": "emotion_proof.json",
    "playback_review_proof": "playback_review_proof.json",
    "production_runtime_proof": "production_runtime_proof.json",
    "production_proof_bundle_binding": "production_proof_bundle.json",
}
LINE_KEYS = {"line_id", "character_id", "voice_profile_id", "text", "start_time", "end_time", "emotion", "intensity", "sync_required", "output_file"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")))


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def _under(root: Path, raw: Path, label: str) -> Path:
    path = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try: path.relative_to(root.resolve())
    except ValueError as exc: raise ValueError(f"{label} must stay inside project root") from exc
    return path


def _binding(path: Path) -> dict[str, str]: return {"path": str(path), "sha256": _sha(path)}


def _atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        if os.path.exists(temp_name): os.unlink(temp_name)
        raise


def produce(root: Path, profile_path: Path, contract_path: Path, proof_dir: Path, output: Path, run_id: str, synthetic: bool) -> dict[str, Any]:
    if output.exists(): raise ValueError(f"output already exists: {output}")
    if output == proof_dir or proof_dir in output.parents: raise ValueError("output must not be inside proof directory")
    if not run_id.strip(): raise ValueError("run_id must be non-empty")
    for path, label in ((profile_path, "voice profile"), (contract_path, "dialogue contract")):
        if not path.is_file(): raise ValueError(f"{label} missing: {path}")
    profile, contract = _load(profile_path), _load(contract_path)
    if not isinstance(profile, dict) or not isinstance(contract, dict): raise ValueError("profile and contract must be JSON objects")
    profile_id, character_id = profile.get("voice_profile_id"), profile.get("character_id")
    if not isinstance(profile_id, str) or not profile_id.strip() or not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("voice profile requires non-empty voice_profile_id and character_id")
    contract_version = contract.get("dialogue_contract_version")
    if contract.get("schema_name") != "wave30_voice_dialogue_contract" or isinstance(contract_version, bool) or not isinstance(contract_version, int) or contract_version != 1:
        raise ValueError("dialogue contract schema/version mismatch")
    lines = contract.get("lines")
    if not isinstance(lines, list) or not lines: raise ValueError("dialogue contract lines must be non-empty")
    line_bindings, seen_ids, seen_paths, seen_hashes = [], set(), set(), set()
    for index, line in enumerate(lines):
        if not isinstance(line, dict) or set(line) != LINE_KEYS: raise ValueError(f"dialogue line {index} has invalid fields")
        line_id = line["line_id"]
        if not isinstance(line_id, str) or not line_id.strip() or line_id in seen_ids: raise ValueError(f"invalid or duplicate line_id: {line_id}")
        seen_ids.add(line_id)
        if line["character_id"] != character_id or line["voice_profile_id"] != profile_id: raise ValueError(f"line profile ownership mismatch: {line_id}")
        start, end = line["start_time"], line["end_time"]
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or float(end) <= float(start):
            raise ValueError(f"invalid line timing: {line_id}")
        audio = _under(root, Path(line["output_file"]), f"line {line_id} output")
        if not audio.is_file() or audio.suffix.lower() != ".wav": raise ValueError(f"line WAV missing: {line_id}")
        try:
            with wave.open(str(audio), "rb") as wav:
                if wav.getcomptype() != "NONE" or wav.getnframes() <= 0 or wav.getframerate() <= 0: raise ValueError("not decodable PCM")
        except wave.Error as exc: raise ValueError(f"line WAV invalid: {line_id}: {exc}") from exc
        digest = _sha(audio)
        if audio in seen_paths or digest in seen_hashes: raise ValueError(f"line WAV reused across lines: {line_id}")
        seen_paths.add(audio); seen_hashes.add(digest)
        line_bindings.append({"line_id": line_id, "path": str(audio), "sha256": digest, "bytes": audio.stat().st_size})
    proofs: dict[str, dict[str, str] | None] = {}
    for key, filename in PROOF_FILES.items():
        path = _under(root, proof_dir / filename, key)
        proofs[key] = _binding(path) if path.is_file() else None
    request = {"schema_name": "wave30_voice_dialogue_continuity_request", "request_version": 1,
               "run_id": run_id.strip(), "is_synthetic": synthetic, "voice_profile_binding": _binding(profile_path),
               "dialogue_contract_binding": _binding(contract_path), "line_audio_bindings": line_bindings, "proof_bindings": proofs}
    schema = _load(root / "Plan/08_SCHEMAS/wave30_voice_dialogue_continuity_request.schema.json")
    Draft202012Validator(schema).validate(request)
    _atomic(output, request)
    return request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice-profile", required=True); parser.add_argument("--dialogue-contract", required=True)
    parser.add_argument("--proof-dir", required=True); parser.add_argument("--output", required=True); parser.add_argument("--run-id", required=True)
    parser.add_argument("--production-input", action="store_true"); parser.add_argument("--root", default="C:/Comfy_UI_Main")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve(); profile = _under(root, Path(args.voice_profile), "voice profile")
        contract = _under(root, Path(args.dialogue_contract), "dialogue contract"); proof_dir = _under(root, Path(args.proof_dir), "proof directory")
        output = _under(root, Path(args.output), "output")
        request = produce(root, profile, contract, proof_dir, output, args.run_id, not args.production_input)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps({"status": "pass", "output": str(output), "line_count": len(request["line_audio_bindings"]), "missing_proof_count": sum(value is None for value in request["proof_bindings"].values())}, sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
