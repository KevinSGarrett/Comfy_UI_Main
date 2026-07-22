from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "Plan/10_REGISTRIES/wave64_flux2_klein_4b_fp8_promoted_storage_package.json"


def test_exact_provider_evidence_and_authority_boundary() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    assert package["revision"] == "c30fa39e0d916333415ae96c66169d8cfdca3e63"
    assert package["file_count"] == 1
    assert package["files"][0]["bytes"] == package["total_bytes"] == 4070624520
    assert package["files"][0]["sha256"] == "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6"
    evidence = ROOT / package["provider_evidence"]["path"]
    assert hashlib.sha256(evidence.read_bytes()).hexdigest() == package["provider_evidence"]["sha256"]
    source = json.loads(evidence.read_text(encoding="utf-8"))
    candidate = next(item for item in source["authoritative_sources"] if item["role"] == "klein_preview_diffusion_model")
    assert candidate["repository"] == package["repository"]
    assert candidate["revision"] == package["revision"]
    assert candidate["published_sha256"] == package["files"][0]["sha256"]
    assert candidate["license"] == package["license_metadata"]
    assert package["authority"]["storage_identity"] is True
    for field in ("license_acceptance", "dependency_bundle", "model_load", "generation_quality", "operational_activation", "product_promotion"):
        assert package["authority"][field] is False
