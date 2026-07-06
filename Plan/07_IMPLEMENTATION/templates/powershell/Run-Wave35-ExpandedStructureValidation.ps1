param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\validate_wave35_expanded_structure.py" --root $Root --output ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\wave35_expanded_structure_validation_report.json"
