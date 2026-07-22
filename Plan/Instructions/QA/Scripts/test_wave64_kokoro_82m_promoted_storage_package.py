from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_kokoro_82m_promoted_storage_package.json"


def test_exact_storage_and_provenance_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    paths = [item["path"] for item in package["files"]]
    assert paths == sorted(paths)
    assert len(paths) == len(set(paths)) == package["file_count"] == 3
    assert sum(item["bytes"] for item in package["files"]) == package["total_bytes"] == 327738002
    evidence_path = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence_path.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    provider = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert provider["repository"] == package["repository"] == "hexgrad/Kokoro-82M"
    assert provider["revision"] == package["revision"] == "f3ff3571791e39611d31c381e3a41a3af07b4987"
    assert provider["license_metadata"] == package["license_metadata"] == "apache-2.0"
    assert [(item["path"], item["bytes"], item["sha256"]) for item in provider["files"]] == [(item["path"], item["bytes"], item["sha256"]) for item in package["files"]]
    assert package["authority"]["storage_identity"] is True
    assert package["authority"]["provider_revision_binding"] is True
    assert package["authority"]["license_metadata_binding"] is True
    for field in ("license_acceptance", "dependency_environment", "model_load", "synthesis_quality", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
