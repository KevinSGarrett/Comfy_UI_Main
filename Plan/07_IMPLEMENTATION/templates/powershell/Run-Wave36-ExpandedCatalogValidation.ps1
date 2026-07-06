param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\generate_wave36_expanded_catalogs.py" --root $Root --output-dir ".\14_ORGANIZATION_SYSTEM\GENERATED_INDEXES\WAVE36_EXPANDED"
python ".\07_IMPLEMENTATION\scripts\validate_wave36_expanded_catalog_system.py" --root $Root --output ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\wave36_expanded_catalog_validation_report.json"
