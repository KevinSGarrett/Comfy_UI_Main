from __future__ import annotations

import hashlib
import json
import tempfile
import types
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Comfy_UI_Main")
VALIDATOR_PATH = PROJECT_ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave64_script_validation_checks.py"


def load_validator():
    module = types.ModuleType("row052_script_validator")
    module.__file__ = str(VALIDATOR_PATH)
    source = VALIDATOR_PATH.read_text(encoding="utf-8")
    exec(compile(source, str(VALIDATOR_PATH), "exec"), module.__dict__)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    module = load_validator()
    cases: list[dict[str, object]] = []

    def record(name: str, actual: bool, expected: bool) -> None:
        cases.append({"name": name, "expected": expected, "actual": actual, "pass": actual is expected})

    with tempfile.TemporaryDirectory(prefix="row052_parser_only_") as temp_dir:
        root = Path(temp_dir)
        valid = root / "valid.py"
        invalid = root / "invalid.py"
        encoded = root / "encoded.py"
        valid.write_text("value = 1\n", encoding="utf-8")
        invalid.write_text("def broken(:\n    pass\n", encoding="utf-8")
        encoded.write_bytes("# -*- coding: latin-1 -*-\nlabel = 'caf\xe9'\n".encode("latin-1"))

        cache_dir = root / "__pycache__"
        cache_dir.mkdir()
        sentinel = cache_dir / "existing.pyc"
        sentinel.write_bytes(b"existing-bytecode-sentinel")
        sentinel_hash_before = sha256(sentinel)
        source_hashes_before = {path.name: sha256(path) for path in (valid, invalid, encoded)}

        valid_result = module.validate_python([valid, encoded], bytecode_root=root)
        invalid_result = module.validate_python([invalid], bytecode_root=root)
        source_hashes_after = {path.name: sha256(path) for path in (valid, invalid, encoded)}
        cache_files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*.pyc"))

        record("valid_python_ast_parse_pass", valid_result["parse_error_count"] == 0, True)
        record("pep263_encoding_honored", valid_result["file_count"] == 2, True)
        record("invalid_python_syntax_rejected", invalid_result["parse_error_count"] == 1, True)
        record("invalid_error_is_syntax_error", invalid_result["errors"][0]["error"].startswith("SyntaxError:"), True)
        record("parser_method_is_ast_only", valid_result["parser_method"] == "compile_ast_only_with_tokenize_open", True)
        record("valid_run_bytecode_inventory_unchanged", valid_result["bytecode_inventory"]["unchanged"] is True, True)
        record("invalid_run_bytecode_inventory_unchanged", invalid_result["bytecode_inventory"]["unchanged"] is True, True)
        record("no_new_pyc_created", cache_files == ["__pycache__/existing.pyc"], True)
        record("preexisting_pyc_byte_exact", sha256(sentinel) == sentinel_hash_before, True)
        record("source_files_byte_exact", source_hashes_after == source_hashes_before, True)

    payload = {
        "status": "PASS" if all(case["pass"] for case in cases) else "FAIL",
        "classification": "ROW052_PARSER_ONLY_NO_BYTECODE_REGRESSION_PASS",
        "validator_path": VALIDATOR_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "case_count": len(cases),
        "failure_count": sum(not bool(case["pass"]) for case in cases),
        "cases": cases,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
