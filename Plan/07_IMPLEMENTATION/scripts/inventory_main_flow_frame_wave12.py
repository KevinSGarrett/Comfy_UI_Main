#!/usr/bin/env python3
"""Inventory frame-composition relevant nodes in a ComfyUI workflow JSON."""
import argparse
import json
from pathlib import Path

KEYWORDS = ("saveimage", "latent", "ipadapter", "controlnet", "inpaint", "canny", "pose", "camera", "preview")

def inventory(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    save = []
    latent = []
    relevant = []
    for n in nodes:
        t = n.get("type", "")
        title = n.get("title", "") or ""
        text = (t + " " + title).lower()
        if t == "SaveImage":
            save.append({"node_id": n.get("id"), "prefix": (n.get("widgets_values") or [""])[0]})
        if "LatentImage" in t:
            w = n.get("widgets_values") or []
            latent.append({"node_id": n.get("id"), "type": t, "widgets_values": w})
        if any(k in text for k in KEYWORDS):
            relevant.append({"node_id": n.get("id"), "type": t, "title": title, "mode": n.get("mode", 0)})
    return {"workflow": str(path), "node_count": len(nodes), "link_count": len(data.get("links", [])), "save_image_lanes": save, "latent_nodes": latent, "frame_relevant_nodes": relevant}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow_json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    report = inventory(Path(args.workflow_json))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
