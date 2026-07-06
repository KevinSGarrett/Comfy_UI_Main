param(
  [string]$Root = "."
)
$required = @(
  "00_PROJECT_CONTROL/WAVE26_AI_PM_TASKS.md",
  "02_TARGET_ARCHITECTURE/WAVE26_GIF_VIDEO_KEYFRAME_PLANNER_ARCHITECTURE.md",
  "04_VIDEO_GIF_SYSTEM/WAVE26_GIF_EXPORT_PLAN.md",
  "06_QA_TESTING/WAVE26_KEYFRAME_AND_TIMELINE_QA_GATES.md",
  "10_REGISTRIES/wave26_keyframe_schema.json",
  "10_REGISTRIES/wave26_shot_plan_schema.json"
)
$missing = @()
foreach ($rel in $required) {
  $p = Join-Path $Root $rel
  if (-not (Test-Path $p)) { $missing += $rel }
}
if ($missing.Count -gt 0) {
  Write-Host "WAVE26 VALIDATION: FAIL"
  $missing | ForEach-Object { Write-Host "Missing: $_" }
  exit 1
}
Write-Host "WAVE26 VALIDATION: PASS"
Write-Host "Temporal planning files detected. Runtime proof remains required."
