param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\validate_wave37_organization.py" --root $Root --output ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\wave37_organization_validation_report.json"
