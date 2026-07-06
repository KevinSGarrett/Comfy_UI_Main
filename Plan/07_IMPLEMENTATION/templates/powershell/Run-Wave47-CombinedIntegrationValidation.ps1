param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\validate_wave47_combined_integration.py" --root $Root --output ".\15_BLUEPRINT_PROJECTPLAN_COMBINATION\WAVE47_COMBINED_FINAL_HANDOFF_AND_OPERATING_MANUAL\wave47_combined_validation_report.json"
