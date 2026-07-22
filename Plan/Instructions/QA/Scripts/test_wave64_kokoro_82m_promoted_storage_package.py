from __future__ import annotations

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
    assert package["authority"]["storage_identity"] is True
    assert package["provider_binding"]["catalog_entry_present"] is False
    assert package["provider_binding"]["inference_from_filename_forbidden"] is True
    for field in ("provider_revision_binding", "license_binding", "dependency_environment", "model_load", "synthesis_quality", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
