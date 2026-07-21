#!/usr/bin/env python3
"""Shared Wave64 autonomous VLM/LLM client (Ollama-compatible).

Env precedence (URL):
  WAVE64_VLM_URL → OLLAMA_HOST → http://127.0.0.1:11434

Env precedence (vision model):
  WAVE64_VLM_MODEL → llava:13b

Env precedence (text/LLM model):
  WAVE64_LLM_MODEL → qwen2.5:7b-instruct

Never promotes VLM output to human_gold, threshold unfreeze, or product COMPLETE.
Never touches Row074 exclusive PCM.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_VLM_MODEL = "llava:13b"
DEFAULT_LLM_MODEL = "qwen2.5:7b-instruct"
DEFAULT_MODEL = DEFAULT_LLM_MODEL  # back-compat alias for text helpers
DEFAULT_TIMEOUT_S = 120
DEFAULT_BASE_URL = "http://127.0.0.1:11434"


class Wave64VlmClientError(RuntimeError):
    pass


def resolve_base_url(explicit: str | None = None) -> str:
    raw = (
        explicit
        or os.environ.get("WAVE64_VLM_URL")
        or os.environ.get("OLLAMA_HOST")
        or DEFAULT_BASE_URL
    )
    text = str(raw).strip()
    if text and not text.startswith(("http://", "https://")):
        text = f"http://{text}"
    return text.rstrip("/")


def resolve_vlm_model(explicit: str | None = None) -> str:
    """Resolve pod vision model for whole-image / visual review."""
    raw = explicit or os.environ.get("WAVE64_VLM_MODEL") or DEFAULT_VLM_MODEL
    text = str(raw).strip()
    return text or DEFAULT_VLM_MODEL


def resolve_llm_model(explicit: str | None = None) -> str:
    """Resolve pod text/LLM model (non-vision generate path)."""
    raw = explicit or os.environ.get("WAVE64_LLM_MODEL") or DEFAULT_LLM_MODEL
    text = str(raw).strip()
    return text or DEFAULT_LLM_MODEL


def resolve_vlm_endpoint(
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Compact endpoint receipt for visual-review helpers (observation only)."""
    return {
        "WAVE64_VLM_URL": resolve_base_url(base_url),
        "WAVE64_VLM_MODEL": resolve_vlm_model(model),
        "WAVE64_LLM_MODEL": resolve_llm_model(),
        "default_vlm_model": DEFAULT_VLM_MODEL,
        "product_completion_claimed": False,
        "row074_pcm_left_alone": True,
    }


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise Wave64VlmClientError(f"http_{exc.code}:{detail[:400]}") from exc
    except Exception as exc:  # noqa: BLE001 - surface transport failures as typed blockers
        raise Wave64VlmClientError(f"transport_error:{type(exc).__name__}:{exc}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise Wave64VlmClientError(f"non_json_response:{body[:200]}") from exc
    if not isinstance(parsed, dict):
        raise Wave64VlmClientError("response_not_object")
    return parsed


def probe_endpoint(base_url: str | None = None, *, timeout_s: float = 5.0) -> dict[str, Any]:
    base = resolve_base_url(base_url)
    version = _http_json("GET", f"{base}/api/version", timeout_s=timeout_s)
    tags = _http_json("GET", f"{base}/api/tags", timeout_s=timeout_s)
    models = []
    for item in tags.get("models") or []:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            models.append(item["name"])
    return {
        "base_url": base,
        "version": version.get("version"),
        "models": models,
        "reachable": True,
        "vlm_model": resolve_vlm_model(),
        "llm_model": resolve_llm_model(),
    }


def generate_text(
    prompt: str,
    *,
    base_url: str | None = None,
    model: str | None = None,
    system: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    temperature: float = 0.0,
    format_json: bool = True,
) -> dict[str, Any]:
    base = resolve_base_url(base_url)
    resolved_model = resolve_llm_model(model)
    payload: dict[str, Any] = {
        "model": resolved_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    if format_json:
        payload["format"] = "json"
    response = _http_json(
        "POST",
        f"{base}/api/generate",
        payload,
        timeout_s=timeout_s,
    )
    text = response.get("response")
    if not isinstance(text, str) or not text.strip():
        raise Wave64VlmClientError("empty_generate_response")
    parsed: dict[str, Any] | None = None
    try:
        candidate = json.loads(text)
        if isinstance(candidate, dict):
            parsed = candidate
    except json.JSONDecodeError:
        parsed = None
    return {
        "base_url": base,
        "model": resolved_model,
        "raw_text": text,
        "parsed_json": parsed,
        "eval_count": response.get("eval_count"),
        "total_duration_ns": response.get("total_duration"),
    }


def chat_with_images(
    prompt: str,
    images_b64: list[str],
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    temperature: float = 0.0,
    format_json: bool = True,
    seed: int | None = None,
    num_predict: int = 512,
) -> dict[str, Any]:
    """Ollama /api/chat vision path for whole-image visual review helpers."""
    if not images_b64:
        raise Wave64VlmClientError("images_required")
    base = resolve_base_url(base_url)
    resolved_model = resolve_vlm_model(model)
    options: dict[str, Any] = {"temperature": temperature, "num_predict": num_predict}
    if seed is not None:
        options["seed"] = seed
    payload: dict[str, Any] = {
        "model": resolved_model,
        "stream": False,
        "options": options,
        "messages": [{"role": "user", "content": prompt, "images": list(images_b64)}],
    }
    if format_json:
        payload["format"] = "json"
    response = _http_json(
        "POST",
        f"{base}/api/chat",
        payload,
        timeout_s=timeout_s,
    )
    message = response.get("message") if isinstance(response.get("message"), dict) else {}
    text = message.get("content") if isinstance(message, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise Wave64VlmClientError("empty_chat_response")
    parsed = extract_json_object(text)
    return {
        "base_url": base,
        "model": resolved_model,
        "endpoint": f"{base}/api/chat",
        "raw_text": text,
        "parsed_json": parsed,
        "eval_count": response.get("eval_count"),
        "total_duration_ns": response.get("total_duration"),
        "product_completion_claimed": False,
        "row074_pcm_left_alone": True,
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None
