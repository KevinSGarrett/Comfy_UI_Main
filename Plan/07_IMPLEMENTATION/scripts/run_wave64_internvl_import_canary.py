from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable


class ImportCanaryError(RuntimeError):
    pass


def _deny_external_side_effects(event: str, _args: tuple[Any, ...]) -> None:
    if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
        raise ImportCanaryError(f"external side effect blocked: {event}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _verify_admission(admission: dict[str, Any]) -> tuple[Path, Path]:
    if _canonical_sha256(admission["lock_material"]) != admission["lock_sha256"]:
        raise ImportCanaryError("admission lock digest mismatch")
    material = admission["lock_material"]
    source_root = Path(material["source_root"]).resolve(strict=True)
    overlay_root = Path(material["environment"]["root"]).resolve(strict=True)
    if _sha256(overlay_root / "OVERLAY_MANIFEST.json") != material["environment"]["manifest_sha256"]:
        raise ImportCanaryError("environment manifest mismatch")
    for item in material["custom_code_files"]:
        path = source_root / item["filename"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
            raise ImportCanaryError(f"custom code identity mismatch: {item['filename']}")
    if str(Path(sys.executable).resolve()) != material["environment"]["python"]:
        raise ImportCanaryError("interpreter identity mismatch")
    return source_root, overlay_root


def _pycache_snapshot(source_root: Path) -> list[dict[str, Any]]:
    return [
        {"path": path.relative_to(source_root).as_posix(), "bytes": path.stat().st_size, "sha256": _sha256(path)}
        for cache in sorted(source_root.rglob("__pycache__"))
        for path in sorted(cache.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def _execute_imports(package_name: str) -> dict[str, Any]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        import torch
        import transformers

        cuda_initialized_before = torch.cuda.is_initialized()
        configuration = importlib.import_module(f"{package_name}.configuration_internvl_chat")
        vision = importlib.import_module(f"{package_name}.modeling_intern_vit")
        chat = importlib.import_module(f"{package_name}.modeling_internvl_chat")
        cuda_initialized_after = torch.cuda.is_initialized()
    return {
        "resolved_classes": {
            "InternVLChatConfig": f"{configuration.InternVLChatConfig.__module__}.{configuration.InternVLChatConfig.__name__}",
            "InternVisionModel": f"{vision.InternVisionModel.__module__}.{vision.InternVisionModel.__name__}",
            "InternVLChatModel": f"{chat.InternVLChatModel.__module__}.{chat.InternVLChatModel.__name__}",
            "Qwen3ForCausalLM": f"{transformers.Qwen3ForCausalLM.__module__}.{transformers.Qwen3ForCausalLM.__name__}",
        },
        "versions": {"python": sys.version.split()[0], "torch": torch.__version__, "transformers": transformers.__version__},
        "has_flash_attn": vision.has_flash_attn,
        "cuda_initialized_before": cuda_initialized_before,
        "cuda_initialized_after": cuda_initialized_after,
        "stdout_lines": [line for line in stdout.getvalue().splitlines() if line],
        "stderr_lines": [line for line in stderr.getvalue().splitlines() if line],
    }


def run_canary(admission_path: Path, executor: Callable[[str], dict[str, Any]] = _execute_imports) -> dict[str, Any]:
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    source_root, overlay_root = _verify_admission(admission)
    material = admission["lock_material"]
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "CUDA_VISIBLE_DEVICES": "",
        }
    )
    sys.dont_write_bytecode = True
    sys.addaudithook(_deny_external_side_effects)
    sys.path.insert(0, str(overlay_root / "site_packages"))
    sys.path.insert(1, str(source_root.parent))
    pycache_before = _pycache_snapshot(source_root)
    result = executor(source_root.name)
    pycache_after = _pycache_snapshot(source_root)
    _verify_admission(admission)
    expected = material["expected_result"]
    if result["resolved_classes"] != expected["resolved_classes"]:
        raise ImportCanaryError("class resolution mismatch")
    if result["versions"] != expected["versions"]:
        raise ImportCanaryError("runtime version mismatch")
    if result["has_flash_attn"] is not False:
        raise ImportCanaryError("FlashAttention must remain disabled")
    if result["cuda_initialized_before"] is not False or result["cuda_initialized_after"] is not False:
        raise ImportCanaryError("CUDA initialized during import canary")
    if result["stdout_lines"] != expected["stdout_lines"] or result["stderr_lines"] != []:
        raise ImportCanaryError("unexpected import output")
    if pycache_after != pycache_before:
        raise ImportCanaryError("source tree bytecode mutation detected")
    return {
        "schema_version": "wave64.aqa.internvl_import_canary_receipt.v1",
        "result": "PASS",
        "lock_sha256": admission["lock_sha256"],
        "source_root": str(source_root),
        "environment_root": str(overlay_root),
        **result,
        "source_pycache_unchanged": True,
        "authority": {"custom_code_import": True, "class_resolution": True, "config_instantiation": False, "model_instantiation": False, "weight_access": False, "model_load": False, "gpu_use": False, "inference": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_canary(args.admission), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
