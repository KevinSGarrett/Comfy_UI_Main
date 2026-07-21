#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def env_url() -> str:
    u = os.environ.get("WAVE64_VLM_URL") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
    if not u.startswith("http"):
        u = "http://" + u
    return u.rstrip("/")

def main() -> int:
    url = env_url()
    model = os.environ.get("WAVE64_VLM_MODEL", "llava:13b")
    img = Path(os.environ.get("FLUX_CANARY_PNG", "/workspace/comfy_output/Scenes_xxx_001/canary/FLUX_CANARY_20260721_034826_00001_.png"))
    art = Path(os.environ["ART_DIR"])
    raw = img.read_bytes(); sha = hashlib.sha256(raw).hexdigest(); b64 = base64.b64encode(raw).decode("ascii")
    prompt = ("You are a Wave64 Flux canary visual reviewer. Score this generated adult image. "
              "Return STRICT JSON only (no markdown) with keys: "
              '{"subject":"short","framing":"full_body|half_body|portrait|other","anatomy_ok":true,'
              '"artifacts":["list"],"identity_plausibility":0.0,"hyperreal_score":0.0,'
              '"overall_score":0.0,"verdict":"pass|fail|uncertain","notes":"<<=40 words"} '
              "Scores are 0..1 floats. Adult-only; do not invent minors.")
    payload = {"model": model, "stream": False, "format": "json",
               "options": {"temperature": 0, "seed": 424242, "num_predict": 512},
               "messages": [{"role": "user", "content": prompt, "images": [b64]}]}
    with urllib.request.urlopen(f"{url}/api/version", timeout=30) as resp:
        version = json.loads(resp.read().decode("utf-8"))
    t0 = time.perf_counter()
    req = urllib.request.Request(f"{url}/api/chat", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    latency = time.perf_counter() - t0
    content = (body.get("message") or {}).get("content", "")
    try:
        parsed = json.loads(content); parse_ok = isinstance(parsed, dict)
    except Exception as exc:
        parsed = {"raw": content, "parse_error": str(exc)}; parse_ok = False
    verdict = "FAIL"
    if parse_ok:
        v = str(parsed.get("verdict", "")).lower()
        try: score_f = float(parsed.get("overall_score"))
        except Exception: score_f = -1.0
        if v == "pass" and score_f >= 0.55: verdict = "PASS"
        elif v in {"pass", "uncertain"} and score_f >= 0.4: verdict = "PASS_WITH_NOTES"
        elif v: verdict = "SCORED_" + v.upper()
    out = {"schema_version":"1.0","created_iso":datetime.now(timezone.utc).isoformat(),"endpoint":url,"model":model,
           "ollama_version":version,"image":{"path":str(img),"sha256":sha,"bytes":len(raw)},
           "latency_s":round(latency,3),"parsed":parsed,"raw_content":content,"parse_ok":parse_ok,
           "smoke_verdict":verdict,"eval_count":body.get("eval_count"),"prompt_eval_count":body.get("prompt_eval_count")}
    (art/"flux_canary_vlm_smoke.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if verdict.startswith("PASS") else 2

if __name__ == "__main__":
    raise SystemExit(main())
