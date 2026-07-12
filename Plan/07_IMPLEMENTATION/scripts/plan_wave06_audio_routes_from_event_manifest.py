#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route_wave06_audio_engine import route_request  # noqa: E402


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _inside(root: Path, path: Path, label: str) -> Path:
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project root") from exc
    return resolved


def _proof_bindings(root: Path, proof_root: Path, token: str, kinds: list[str]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for kind in kinds:
        path = _inside(root, proof_root / token / f"{kind}.json", f"{kind} proof")
        bindings[kind] = {"path": str(path), "sha256": _sha(path) if path.is_file() else "0" * 64}
    return bindings


def _request_for_event(
    event: dict[str, Any], manifest: dict[str, Any], policy: dict[str, Any], usage_scope: str,
    root: Path, proof_root: Path, token: str,
) -> tuple[str, dict[str, Any]]:
    event_type = event["event_type"]
    route_type = policy["event_type_to_route_type"].get(event_type)
    if not route_type:
        raise ValueError("event_type_not_mapped")
    routing = event.get("routing")
    if not isinstance(routing, dict):
        raise ValueError("event_routing_not_object")
    override_field = policy["synchronized_av_override_field"]
    synchronized = routing.get(override_field, False)
    if not isinstance(synchronized, bool):
        raise ValueError("synchronized_av_override_not_boolean")
    target = policy["synchronized_av_target"] if synchronized else policy["audio_target"]
    if synchronized:
        route_type = target["route_type"]
    channels = event["artifact"]["channels"]
    layout = policy["channel_layout_by_channels"].get(str(channels))
    if layout is None:
        raise ValueError("unsupported_channel_layout_derivation")
    duration = float(event["end_seconds"]) - float(event["start_seconds"])
    if duration <= 0:
        raise ValueError("event_duration_not_positive")
    preferred_field = policy["preferred_engine_field"]
    preferred = routing.get(preferred_field)
    if preferred is not None and (not isinstance(preferred, str) or not preferred.strip()):
        raise ValueError("preferred_audio_engine_id_not_string")
    request: dict[str, Any] = {
        "output_type": target["output_type"], "route_type": route_type, "duration_seconds": round(duration, 6),
        "sample_rate_hz": event["artifact"]["sample_rate_hz"], "channels": channels, "channel_layout": layout,
        "target_output": target["target_output"], "target_container": target["target_container"],
        "usage_scope": usage_scope,
        "physical_action_present": event_type in set(policy["physical_action_event_types"]),
        "aligned_audio_event_present": True, "is_synthetic": bool(manifest["is_synthetic"]),
        "proof_bindings": _proof_bindings(root, proof_root, token, policy["proof_kinds"]),
    }
    if preferred is not None:
        request["preferred_engine_id"] = preferred.strip()
    return route_type, request


def build_plan(root: Path, event_path: Path, output: Path, proof_root: Path, usage_scope: str) -> dict[str, Any]:
    event_schema_path = root / "Plan/08_SCHEMAS/wave30_audio_event_manifest.schema.json"
    request_schema_path = root / "Plan/08_SCHEMAS/wave06_audio_engine_route_request.schema.json"
    decision_schema_path = root / "Plan/08_SCHEMAS/wave06_audio_engine_route_decision.schema.json"
    plan_schema_path = root / "Plan/08_SCHEMAS/wave06_audio_event_route_plan.schema.json"
    policy_path = root / "Plan/10_REGISTRIES/wave06_audio_event_route_bridge_policy.json"
    manifest, policy = _load(event_path), _load(policy_path)
    event_schema, request_schema = _load(event_schema_path), _load(request_schema_path)
    decision_schema, plan_schema = _load(decision_schema_path), _load(plan_schema_path)
    Draft202012Validator(event_schema).validate(manifest)
    if usage_scope not in {"internal_eval", "client_preview", "production"}:
        raise ValueError("invalid usage scope")
    temp = output.parent / f".{output.name}.tmp-{uuid.uuid4().hex}"
    if output.exists():
        raise ValueError(f"output directory already exists: {output}")
    temp.mkdir(parents=True)
    results: list[dict[str, Any]] = []
    try:
        for index, event in enumerate(manifest["audio_events"]):
            event_id, event_type = event["audio_event_id"], event["event_type"]
            token = f"{index:04d}_{hashlib.sha256(event_id.encode('utf-8')).hexdigest()[:16]}"
            try:
                route_type, request = _request_for_event(event, manifest, policy, usage_scope, root, proof_root, token)
            except Exception as exc:
                results.append({"audio_event_id": event_id, "event_type": event_type, "route_type": None,
                                "request": None, "decision": None, "router_exit_code": None,
                                "selected_engine_id": None, "route_mode": None,
                                "blockers": [f"bridge_derivation_failed:{exc}"]})
                continue
            Draft202012Validator(request_schema).validate(request)
            code, decision = route_request(root, request)
            Draft202012Validator(decision_schema).validate(decision)
            request_temp, decision_temp = temp / "requests" / f"{token}.json", temp / "decisions" / f"{token}.json"
            _write(request_temp, request); _write(decision_temp, decision)
            request_final, decision_final = output / "requests" / request_temp.name, output / "decisions" / decision_temp.name
            results.append({
                "audio_event_id": event_id, "event_type": event_type, "route_type": route_type,
                "request": {"path": str(request_final), "sha256": _sha(request_temp)},
                "decision": {"path": str(decision_final), "sha256": _sha(decision_temp)},
                "router_exit_code": code, "selected_engine_id": decision["selected_engine_id"],
                "route_mode": decision["route_mode"], "blockers": decision["blockers"],
            })
        selected = sum(1 for item in results if item["selected_engine_id"] is not None and item["router_exit_code"] == 0)
        blocked = len(results) - selected
        all_routed = blocked == 0 and len(results) == len(manifest["audio_events"])
        promotion_ready = all_routed and not bool(manifest["is_synthetic"]) and usage_scope == "production"
        plan = {
            "schema_name": "wave06_audio_event_route_plan", "plan_version": 1,
            "run_id": manifest["run_id"], "scene_id": manifest["scene_id"], "shot_id": manifest["shot_id"],
            "is_synthetic": bool(manifest["is_synthetic"]),
            "source_event_manifest": {"path": str(event_path), "sha256": _sha(event_path)},
            "bridge_policy": {"path": str(policy_path), "sha256": _sha(policy_path)},
            "usage_scope": usage_scope, "event_count": len(manifest["audio_events"]), "request_count": sum(item["request"] is not None for item in results),
            "selected_count": selected, "blocked_count": blocked, "events": results,
            "all_events_routed": all_routed, "block_final_av_promotion": not promotion_ready,
            "production_selection_claimed": promotion_ready,
            "status": "all_events_routed" if all_routed else "blocked",
        }
        Draft202012Validator(plan_schema).validate(plan)
        _write(temp / "route_plan.json", plan)
        os.replace(temp, output)
        return plan
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--proof-root")
    parser.add_argument("--usage-scope", default="internal_eval")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        event_path = _inside(root, Path(args.event_manifest), "event manifest")
        output = _inside(root, Path(args.output_dir), "output directory")
        proof_root = _inside(root, Path(args.proof_root), "proof root") if args.proof_root else output / "proofs"
        plan = build_plan(root, event_path, output, proof_root, args.usage_scope)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": plan["status"], "event_count": plan["event_count"], "blocked_count": plan["blocked_count"], "output_dir": str(output)}, sort_keys=True))
    return 0 if plan["all_events_routed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
