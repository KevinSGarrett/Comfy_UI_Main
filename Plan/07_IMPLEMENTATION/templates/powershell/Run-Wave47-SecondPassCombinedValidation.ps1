param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\validate_wave47_second_pass_combined_integration.py" --root $Root --output ".\15_BLUEPRINT_PROJECTPLAN_COMBINATION\SECOND_PASS_WAVE38_47_DEEPENING\wave47_second_pass_validation_report.json"
