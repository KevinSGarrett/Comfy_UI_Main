param(
  [string]$Root = "."
)
$ErrorActionPreference = "Stop"
python ".\07_IMPLEMENTATION\scripts\generate_wave37_expanded_release_readiness.py" --root $Root --output ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\WAVE37_EXPANDED\wave37_expanded_release_readiness_report.json"
python ".\07_IMPLEMENTATION\scripts\generate_wave37_expanded_final_handoff_packet.py" --root $Root --readiness-report ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\WAVE37_EXPANDED\wave37_expanded_release_readiness_report.json" --output ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\WAVE37_EXPANDED\wave37_expanded_final_handoff_packet.json"
python ".\07_IMPLEMENTATION\scripts\validate_wave37_expanded_migration_governance_handoff.py" --root $Root --output ".\14_ORGANIZATION_SYSTEM\ORGANIZATION_VALIDATION\WAVE37_EXPANDED\wave37_expanded_validation_report.json"
