param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RequestJson = "09_EXAMPLES\wave10_app_mode_camera_request.example.json",
  [string]$OutputPlan = "runtime\camera_plans\wave10_camera_plan.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location $ProjectRoot
try {
  python "07_IMPLEMENTATION\scripts\compile_camera_plan.py" --request $RequestJson --out $OutputPlan
  python "07_IMPLEMENTATION\scripts\validate_camera_plan.py" --plan $OutputPlan --out "$OutputPlan.validation.json"
  python "07_IMPLEMENTATION\scripts\score_framing_composition.py" --plan $OutputPlan --out "$OutputPlan.framing_score.json"
  Write-Host "Wave10 camera validation completed."
}
finally {
  Pop-Location
}
