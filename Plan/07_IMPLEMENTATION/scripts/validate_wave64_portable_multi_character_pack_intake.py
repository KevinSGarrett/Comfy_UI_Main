#!/usr/bin/env python3
"""Fail-closed portable multi-character reference pack intake gate (Row010).

Does NOT invent faces or promote character1_*/ztest. Scans tracked pack roots
and emits ABSENT/INCOMPLETE/READY evidence for >=2 distinct character_ids with
hash-bound USER_AUTHORITY face (+ optional body) refs.

Run anytime; no GPU required. Never claims COMPLETE / GATE CLEARED.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
PACK_ROOTS = [
    ROOT / "character_reference_packs",
    ROOT / "character_packs",
    ROOT / "CharacterPacks",
    ROOT / "media" / "character_reference",
]
FORBIDDEN_NAME = re.compile(r"(character1_|ztest|personal_calibration_noncanonical)", re.I)
FACE_HINT = re.compile(r"(face_front|face_ref|USER_AUTHORITY.*face|identity.*face)", re.I)
BODY_HINT = re.compile(r"(body_|fullbody|USER_AUTHORITY.*(body|rear|side|front))", re.I)
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    characters: dict[str, dict] = {}
    scanned_roots = []
    rejected_paths = []

    for root in PACK_ROOTS:
        exists = root.is_dir()
        scanned_roots.append({"path": str(root.relative_to(ROOT)).replace("\\", "/"), "exists": exists})
        if not exists:
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMG_EXT:
                continue
            rel = str(path.relative_to(ROOT)).replace("\\", "/")
            if FORBIDDEN_NAME.search(rel):
                rejected_paths.append({"path": rel, "reason": "forbidden_nonportable_name"})
                continue
            # character_id = first directory under pack root
            try:
                cid = path.relative_to(root).parts[0]
            except Exception:
                continue
            if FORBIDDEN_NAME.search(cid):
                rejected_paths.append({"path": rel, "reason": "forbidden_character_id"})
                continue
            entry = characters.setdefault(
                cid,
                {"character_id": cid, "faces": [], "bodies": [], "other": []},
            )
            rec = {
                "path": rel,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            name = path.name
            if FACE_HINT.search(name) or FACE_HINT.search(rel):
                entry["faces"].append(rec)
            elif BODY_HINT.search(name) or BODY_HINT.search(rel):
                entry["bodies"].append(rec)
            else:
                entry["other"].append(rec)

    qualifying = [
        c
        for c in characters.values()
        if len(c["faces"]) >= 1 and c["faces"][0]["bytes"] > 0
    ]
    status = "READY_FOR_COMPARISON_BINDING" if len(qualifying) >= 2 else "ABSENT_OR_INCOMPLETE"
    exact_blocker = None
    if len(qualifying) < 2:
        exact_blocker = (
            "PORTABLE_MULTI_CHARACTER_REFERENCE_PACK_ABSENT|"
            "NEED_GE_2_CHARACTER_IDS_WITH_HASH_BOUND_USER_AUTHORITY_FACE"
        )

    evidence = {
        "schema_version": "1.0",
        "evidence_id": f"TRK-W64-010_PORTABLE_MULTI_CHAR_PACK_INTAKE_GATE_{now}",
        "tracker_id": "TRK-W64-010",
        "item_id": "ITEM-W64-010",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "row_complete": False,
        "product_completion_claimed": False,
        "gate_cleared": False,
        "exact_blocker": exact_blocker,
        "requirement": {
            "min_character_ids": 2,
            "required_per_character": ["USER_AUTHORITY face_front (or face_ref) with sha256"],
            "optional_per_character": ["supporting body/side/rear USER_AUTHORITY refs"],
            "forbidden": ["invented faces", "character1_*", "ztest", "personal_calibration_noncanonical alone"],
        },
        "scanned_roots": scanned_roots,
        "character_count": len(characters),
        "qualifying_character_count": len(qualifying),
        "characters": characters,
        "rejected_paths": rejected_paths[:50],
        "explicit_non_claims": ["COMPLETE", "GATE_CLEARED", "invented_assets"],
        "safe_next_action": (
            "Human/external: stage >=2 distinct character_id USER_AUTHORITY face/body refs "
            "under character_reference_packs/<character_id>/ with real files; re-run this gate; "
            "then authorize comparison-crop binding + strict 32b identity climb on RunPod."
        ),
    }

    out_qa = (
        ROOT
        / "Plan/Instructions/QA/Evidence/Wave64"
        / f"TRK-W64-010_PORTABLE_MULTI_CHAR_PACK_INTAKE_GATE_{now}.json"
    )
    out_trk = ROOT / "Plan/Tracker/Evidence" / out_qa.name
    out_qa.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    out_trk.write_text(out_qa.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"status": status, "qualifying": len(qualifying), "out": str(out_qa)}, indent=2))
    return 0 if status == "READY_FOR_COMPARISON_BINDING" else 2


if __name__ == "__main__":
    raise SystemExit(main())
