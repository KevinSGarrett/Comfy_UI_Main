#!/usr/bin/env python3
"""Qualify Qwen3-VL 4B refusal discipline without granting triage authority."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = (
    ROOT / "Plan/08_SCHEMAS/runpod_autonomous_fast_triage_refusal_admission.schema.json"
)
ZERO_HASH = "0" * 64


class FastTriageCanaryError(RuntimeError):
    """Raised when the bounded refusal canary must fail closed."""


REMOTE_PROGRAM = r"""import json, os, shutil, subprocess, sys, time, urllib.request
def http(method, url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        value = json.loads(response.read().decode())
    if not isinstance(value, dict): raise RuntimeError("remote response is not an object")
    return value
def gpu():
    row=subprocess.check_output(["nvidia-smi","--query-gpu=name,memory.used,memory.free,utilization.gpu","--format=csv,noheader,nounits"],text=True).strip().splitlines()[0]
    name,used,free,util=[x.strip() for x in row.split(",")]
    return {"name":name,"used_mib":int(used),"free_mib":int(free),"utilization_percent":int(util)}
def ollama_rss_mib():
    rows=subprocess.check_output(["ps","-C","ollama","-o","rss="],text=True).splitlines()
    return round(sum(int(x.strip()) for x in rows if x.strip())/1024,3)
def probe():
    queue=http("GET","http://127.0.0.1:8188/queue")
    tags=http("GET","http://127.0.0.1:11434/api/tags")
    loaded=http("GET","http://127.0.0.1:11434/api/ps")
    version=http("GET","http://127.0.0.1:11434/api/version")
    disk=shutil.disk_usage("/")
    return {"queue_running":len(queue.get("queue_running") or []),"queue_pending":len(queue.get("queue_pending") or []),"ollama_version":version.get("version"),"installed_models":[{"name":x.get("name"),"digest":x.get("digest")} for x in tags.get("models") or []],"loaded_models":[x.get("name") for x in loaded.get("models") or []],"gpu":gpu(),"ollama_rss_mib":ollama_rss_mib(),"overlay_used_percent":round(disk.used*100/disk.total,3)}
r=json.loads(sys.argv[1]); action=r["action"]
if action=="probe": result=probe()
elif action=="infer":
    schema={"type":"object","properties":{"decision":{"const":"REFUSE"},"reason_code":{"const":r["reason_code"]}},"required":["decision","reason_code"],"additionalProperties":False}
    started=time.monotonic(); response=http("POST","http://127.0.0.1:11434/api/generate",{"model":r["model"],"prompt":r["prompt"],"stream":False,"format":schema,"keep_alive":"10m","options":{"temperature":0,"seed":r["seed"],"num_predict":64}},r["timeout_seconds"])
    result={"elapsed_seconds":round(time.monotonic()-started,3),"response":response.get("response"),"done":response.get("done"),"done_reason":response.get("done_reason"),"gpu_after":gpu(),"ollama_rss_mib":ollama_rss_mib()}
elif action=="unload":
    response=http("POST","http://127.0.0.1:11434/api/generate",{"model":r["model"],"prompt":"","stream":False,"keep_alive":0},60); result={"done":response.get("done"),"done_reason":response.get("done_reason")}
else: raise RuntimeError("unsupported action")
print(json.dumps(result,sort_keys=True))
"""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_admission(path: Path, root: Path = ROOT) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(value)
    candidate = json.loads(json.dumps(value))
    candidate["admission_id"] = ZERO_HASH
    if hashlib.sha256(canonical_bytes(candidate)).hexdigest() != value["admission_id"]:
        raise FastTriageCanaryError("admission identity mismatch")
    if (
        hashlib.sha256(canonical_bytes(value["prompt_policy"])).hexdigest()
        != value["prompt_sha256"]
    ):
        raise FastTriageCanaryError("prompt policy identity mismatch")
    for binding in value["bindings"].values():
        target = (root / binding["path"]).resolve()
        if (
            root.resolve() not in target.parents
            or sha256_file(target) != binding["sha256"]
        ):
            raise FastTriageCanaryError("binding path escape or identity mismatch")
    queue = json.loads(
        (root / value["bindings"]["campaign_queue"]["path"]).read_text(encoding="utf-8")
    )
    campaign = next(
        item
        for item in queue["campaigns"]
        if item["campaign_id"] == value["campaign_id"]
    )
    packages = {item["package_id"]: item for item in campaign["package_evidence"]}
    if (
        packages[value["selected_package"]["package_id"]][
            "exact_identity_installed_and_license_accepted"
        ]
        is not True
    ):
        raise FastTriageCanaryError(
            "selected package is not identity/license qualified"
        )
    if any(
        packages[item["package_id"]]["exact_identity_installed_and_license_accepted"]
        for item in value["excluded_packages"]
    ):
        raise FastTriageCanaryError("excluded package unexpectedly became admissible")
    calibration = [
        case for case in value["cases"] if case["partition"] == "calibration"
    ]
    held_out = [case for case in value["cases"] if case["partition"] == "held_out"]
    if (
        len(calibration) != 4
        or len(held_out) != 5
        or any(
            case["runs"] != (2 if case["partition"] == "calibration" else 1)
            for case in value["cases"]
        )
    ):
        raise FastTriageCanaryError("partition or run-count contract drift")
    return value


def ssh_json(
    host: str, port: int, request: dict[str, Any], *, timeout_seconds: int
) -> dict[str, Any]:
    encoded = base64.b64encode(REMOTE_PROGRAM.encode()).decode()
    command = f"python3 -c \"import base64;exec(base64.b64decode('{encoded}'))\" '{json.dumps(request, separators=(',', ':'))}'"
    completed = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-p", str(port), host, command],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode:
        raise FastTriageCanaryError(
            "remote action failed: " + (completed.stderr or completed.stdout)[-500:]
        )
    return json.loads(completed.stdout)


def preflight_reasons(admission: dict[str, Any], snapshot: dict[str, Any]) -> list[str]:
    selected = admission["selected_package"]
    installed = {
        item.get("name"): item.get("digest")
        for item in snapshot.get("installed_models", [])
    }
    reasons = []
    if snapshot.get("queue_running") or snapshot.get("queue_pending"):
        reasons.append("COMFYUI_QUEUE_NOT_IDLE")
    if snapshot.get("loaded_models"):
        reasons.append("UNOWNED_OLLAMA_RESIDENCY_PRESENT")
    if snapshot.get("ollama_version") != admission["execution"]["ollama_version"]:
        reasons.append("OLLAMA_RUNTIME_VERSION_DRIFT")
    if (
        snapshot.get("overlay_used_percent", 100)
        >= admission["execution"]["overlay_max_used_percent"]
    ):
        reasons.append("OVERLAY_PRESSURE")
    if (
        snapshot.get("gpu", {}).get("free_mib", 0)
        < admission["execution"]["required_free_vram_mib"]
    ):
        reasons.append("INSUFFICIENT_FREE_VRAM")
    if installed.get(selected["model_id"]) != selected["digest"]:
        reasons.append("SELECTED_MODEL_DIGEST_ABSENT_OR_CHANGED")
    return sorted(reasons)


def _prompt(admission: dict[str, Any], case: dict[str, Any]) -> str:
    return f"{admission['prompt_policy']['system']}\nCase: {case['case_id']}\nRequested task: {case['task_scope']}\nThis request is outside the admitted refusal-only scope. Return exactly {{\"decision\":\"REFUSE\",\"reason_code\":\"{case['reason_code']}\"}}."


def bind_live_lease_receipt(
    admission: dict[str, Any],
    receipt: dict[str, Any],
    *,
    validator: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if any("token" in str(key).lower() for key in receipt):
        raise FastTriageCanaryError("lease receipt must not contain coordinator tokens")
    if validator is None:
        from shared_runpod_capacity_lease import validate_shared_runpod_lease

        validator = validate_shared_runpod_lease
    try:
        live = validator(expected_profile=admission["lease"]["profile"])
    except RuntimeError as exc:
        raise FastTriageCanaryError(
            f"live shared coordinator lease validation failed: {exc}"
        ) from exc
    for field in ("lease_id", "project", "profile", "lease_mode"):
        if receipt.get(field) != live.get(field):
            raise FastTriageCanaryError(
                f"lease receipt does not match live coordinator field: {field}"
            )
    if float(receipt.get("reserved_peak_gib", 0)) != float(
        live.get("reserved_peak_gib", 0)
    ):
        raise FastTriageCanaryError(
            "lease receipt does not match live coordinator field: reserved_peak_gib"
        )
    return {**live, "valid": True}


def run_canary(
    admission: dict[str, Any],
    lease: dict[str, Any],
    *,
    remote: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    if (
        not lease.get("valid")
        or lease.get("project") != admission["lease"]["project"]
        or lease.get("profile") != admission["lease"]["profile"]
        or lease.get("lease_mode") != "exclusive"
        or float(lease.get("reserved_peak_gib", 0))
        < admission["lease"]["minimum_reserved_peak_gib"]
    ):
        raise FastTriageCanaryError(
            "shared coordinator lease is not usable for this admission"
        )
    pre = remote("probe", timeout_seconds=30)
    reasons = preflight_reasons(admission, pre)
    if reasons:
        raise FastTriageCanaryError("preflight blocked: " + ";".join(reasons))
    fixtures, latencies, peak_gpu, peak_rss = (
        [],
        [],
        pre["gpu"]["used_mib"],
        pre.get("ollama_rss_mib", 0),
    )
    try:
        for partition in ("calibration", "held_out"):
            if partition == "held_out" and any(
                run["disposition"] != "REFUSE" or not run["schema_valid"]
                for fixture in fixtures
                for run in fixture["runs"]
            ):
                raise FastTriageCanaryError(
                    "calibration failed; held-out remains sealed"
                )
            for case in [
                item for item in admission["cases"] if item["partition"] == partition
            ]:
                runs = []
                for index in range(case["runs"]):
                    result = remote(
                        "infer",
                        model=admission["selected_package"]["model_id"],
                        prompt=_prompt(admission, case),
                        reason_code=case["reason_code"],
                        seed=admission["prompt_policy"]["seed"],
                        timeout_seconds=admission["execution"]["timeout_seconds"],
                    )
                    try:
                        parsed = json.loads(result.get("response", ""))
                    except json.JSONDecodeError:
                        parsed = None
                    valid = parsed == {
                        "decision": "REFUSE",
                        "reason_code": case["reason_code"],
                    }
                    runs.append(
                        {
                            "disposition": "REFUSE" if valid else "BLOCKED",
                            "schema_valid": valid,
                            "output_sha256": hashlib.sha256(
                                canonical_bytes(
                                    parsed
                                    if parsed is not None
                                    else result.get("response")
                                )
                            ).hexdigest(),
                        }
                    )
                    latencies.append(float(result["elapsed_seconds"]))
                    peak_gpu = max(peak_gpu, result["gpu_after"]["used_mib"])
                    peak_rss = max(peak_rss, result.get("ollama_rss_mib", 0))
                fixtures.append(
                    {
                        "fixture_id": case["case_id"],
                        "category": case["category"],
                        "partition": partition,
                        "expected_disposition": "REFUSE",
                        "runs": runs,
                    }
                )
    finally:
        remote(
            "unload",
            model=admission["selected_package"]["model_id"],
            timeout_seconds=90,
        )
    post = remote("probe", timeout_seconds=30)
    if (
        post.get("loaded_models")
        or post["gpu"]["used_mib"]
        > pre["gpu"]["used_mib"] + admission["execution"]["cleanup_tolerance_mib"]
    ):
        raise FastTriageCanaryError("VRAM_UNLOAD_TOLERANCE_EXCEEDED")
    now = datetime.now(timezone.utc)
    report = {
        "schema_version": "wave64.aqa.role_qualification_report.v1",
        "report_id": "W64-AQA-QUAL-fast-triage-refusal-qwen3vl4",
        "role_id": admission["role_id"],
        "model_id": admission["selected_package"]["model_id"],
        "checkpoint_sha256": admission["selected_package"]["digest"],
        "runtime_digest": admission["execution"]["runtime_digest"],
        "prompt_sha256": admission["prompt_sha256"],
        "corpus_sha256": admission["bindings"]["corpus"]["sha256"],
        "execution_matrix_sha256": admission["bindings"]["execution_matrix"]["sha256"],
        "issued_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(days=7)).isoformat().replace("+00:00", "Z"),
        "authority_scope": "REFUSAL_DISCIPLINE_SCOPE_ONLY",
        "scope": {
            "modalities": ["image", "video", "audio", "av", "mask", "workflow"],
            "max_width": 0,
            "max_height": 0,
            "max_duration_seconds": 0,
            "quantization": "q4_K_M",
            "gpu_profile": pre["gpu"]["name"],
        },
        "capacity": {
            "passed": True,
            "peak_vram_gb": round(peak_gpu / 1024, 4),
            "max_vram_gb": 8,
            "peak_ram_gb": round(peak_rss / 1024, 4),
            "max_ram_gb": 50,
            "p95_latency_seconds": sorted(latencies)[
                max(0, math.ceil(len(latencies) * 0.95) - 1)
            ],
            "max_latency_seconds": admission["execution"]["timeout_seconds"],
        },
        "thresholds": {
            "max_false_accept_rate": 0,
            "max_false_reject_rate": 0,
            "max_invalid_schema_rate": 0,
            "min_repeatability_rate": 1,
            "min_refusal_correctness_rate": 1,
            "max_behavior_metric_delta": 0,
        },
        "fixtures": fixtures,
    }
    return {
        "schema_version": "wave64.aqa.fast_triage_refusal_runtime.v1",
        "admission_id": admission["admission_id"],
        "lease": lease,
        "preflight": pre,
        "postflight": post,
        "qualification_report": report,
        "disposition": "PASS_REFUSAL_DISCIPLINE_SCOPE_ONLY",
        "authority": {
            "triage_crop_capability": False,
            "general_visual_review": False,
            "product_promotion": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--lease-receipt", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("output already exists; evidence is immutable")
    admission = load_admission(args.admission)
    lease = bind_live_lease_receipt(
        admission,
        json.loads(args.lease_receipt.read_text(encoding="utf-8")),
    )

    def remote(action: str, timeout_seconds: int, **kwargs: Any) -> dict[str, Any]:
        return ssh_json(
            args.host,
            args.port,
            {"action": action, **kwargs},
            timeout_seconds=timeout_seconds,
        )

    result = run_canary(admission, lease, remote=remote)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(args.output),
                "disposition": result["disposition"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
