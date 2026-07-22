from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/review_wave64_python_custom_code.py"


def _module():
    spec = importlib.util.spec_from_file_location("custom_code_review", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_review_records_structure_without_executing_source(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "safe.py"
    source.write_text('"doc"\nimport torch\nVALUE = 3\nclass Model:\n    def forward(self):\n        return torch.zeros(1)\n', encoding="utf-8")
    receipt = module.review(tmp_path, [source.name])
    assert receipt["risk_findings"] == []
    assert receipt["top_level_executable"] == []
    assert receipt["authority"] == {"static_ast_review": True, "import": False, "execution": False}
    assert {item["name"] for item in receipt["files"][0]["definitions"]} == {"Model", "forward"}


def test_review_flags_risk_import_calls_and_top_level_execution(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "unsafe.py"
    source.write_text("import subprocess\nopen('x')\nVALUE = factory()\nif True:\n    eval('1')\n", encoding="utf-8")
    receipt = module.review(tmp_path, [source.name])
    assert {item["kind"] for item in receipt["risk_findings"]} == {"risk_import", "risk_call"}
    assert {item["name"] for item in receipt["risk_findings"]} == {"subprocess", "open", "eval"}
    assert {item["kind"] for item in receipt["top_level_executable"]} == {"Expr", "Assign", "If"}


def test_review_rejects_escape_and_symlink_targets(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    for filename in ("../outside.py", "alias.py"):
        if filename == "alias.py":
            try:
                (root / filename).symlink_to(outside)
            except OSError:
                continue
        try:
            module.review(root, [filename])
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe target was accepted: {filename}")
