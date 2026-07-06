<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Generated: 2026-07-06T04:53:12Z
-->

# ITEMS_DIRECTORY_FILE_INDEX

## 1. Purpose

This file is the package-time exhaustive index of the `Items` directory from the coverage-verified Items package.
Codex uses this directory as the source-of-truth for itemized scope and backlog decomposition.

## 2. Scope

```text
C:\Comfy_UI_Main\Plan\Items
```

## 3. Summary

- Indexed files: **27**
- Generated: `2026-07-06T04:53:12Z`
- Machine-readable versions are stored in `Plan\Instructions\Indexes\Generated`.

### Source/status counts

| Source status | Count |
|---|---:|
| `items_scope_source_of_truth` | 20 |
| `items_validation_evidence` | 7 |

### Update-policy counts

| Codex update policy | Count |
|---|---:|
| `preserve_as_validation_evidence` | 6 |
| `update_when_scope_items_or_item_state_change` | 21 |

## 4. Exhaustive file index

Codex must treat this as a package-time index. On the live Windows machine, regenerate the index after extraction using `Plan\Instructions\Scripts\Generate-Project-Indexes.ps1` to capture files that exist locally but were not present in the uploaded packages.

| # | Relative path from `C:\Comfy_UI_Main` | Purpose | Source status | Codex update policy |
|---:|---|---|---|---|
| 1 | `Plan\Items\COVERAGE_VERIFICATION_README.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 2 | `Plan\Items\Coverage_Audit\ultra_blueprint_coverage_after.csv` | Items coverage-audit evidence proving blueprint source coverage. | `items_validation_evidence` | `preserve_as_validation_evidence` |
| 3 | `Plan\Items\Coverage_Audit\ultra_blueprint_coverage_before.csv` | Items coverage-audit evidence proving blueprint source coverage. | `items_validation_evidence` | `preserve_as_validation_evidence` |
| 4 | `Plan\Items\Coverage_Audit\ultra_blueprint_coverage_summary.json` | Items coverage-audit evidence proving blueprint source coverage. | `items_validation_evidence` | `preserve_as_validation_evidence` |
| 5 | `Plan\Items\Coverage_Audit\ultra_blueprint_source_section_index.csv` | Items coverage-audit evidence proving blueprint source coverage. | `items_validation_evidence` | `preserve_as_validation_evidence` |
| 6 | `Plan\Items\Data_Dictionaries\items_data_dictionary.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 7 | `Plan\Items\Manifests\items_package_manifest.json` | Machine-readable Items validation, manifest, or coverage data. | `items_validation_evidence` | `update_when_scope_items_or_item_state_change` |
| 8 | `Plan\Items\README.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 9 | `Plan\Items\RELEASE_NOTES.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 10 | `Plan\Items\Reports\items_summary_report.json` | Items package validation or coverage report. | `items_validation_evidence` | `preserve_as_validation_evidence` |
| 11 | `Plan\Items\Reports\items_validation_report.json` | Items package validation or coverage report. | `items_validation_evidence` | `preserve_as_validation_evidence` |
| 12 | `Plan\Items\Schemas\item_row_schema.json` | Machine-readable Items validation, manifest, or coverage data. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 13 | `Plan\Items\Scripts\Run-Validate-ItemsPackage.ps1` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 14 | `Plan\Items\Scripts\__pycache__\validate_items_package.cpython-313.pyc` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 15 | `Plan\Items\Scripts\validate_items_package.py` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 16 | `Plan\Items\Source_Citations\items_source_citation_index.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 17 | `Plan\Items\Waves\Wave53\WAVE53_ITEMS_SOURCE_CITED_TAXONOMY.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 18 | `Plan\Items\Waves\Wave53\wave53_item_rows.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 19 | `Plan\Items\Waves\Wave54\WAVE54_ITEMS_IMPLEMENTATION_REQUIREMENTS.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 20 | `Plan\Items\Waves\Wave54\wave54_item_rows.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 21 | `Plan\Items\Waves\Wave55\WAVE55_ITEMS_QA_TESTING_VISUAL_REVIEW.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 22 | `Plan\Items\Waves\Wave55\wave55_item_rows.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 23 | `Plan\Items\Waves\Wave56\WAVE56_ITEMS_AUTONOMOUS_RUNTIME_NO_HUMAN.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 24 | `Plan\Items\Waves\Wave56\wave56_item_rows.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 25 | `Plan\Items\Waves\Wave57\WAVE57_ITEMS_VALIDATION_HANDOFF_CERTIFICATION.md` | Items package documentation or source-of-truth backlog reference. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 26 | `Plan\Items\Waves\Wave57\wave57_item_rows.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
| 27 | `Plan\Items\wave53_57_master_itemized_list.csv` | Itemized task/backlog/scope table for autonomous build work. | `items_scope_source_of_truth` | `update_when_scope_items_or_item_state_change` |
