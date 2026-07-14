[CmdletBinding()]
param([string]$ProjectRoot = "C:\Comfy_UI_Main")

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$issues = [Collections.Generic.List[string]]::new()

function Require-File([string]$relative) {
  $path = Join-Path $ProjectRoot $relative
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { $issues.Add("missing:$relative") }
  return $path
}

$policyPath = Require-File "Plan\Instructions\COMFYUI_DELIVERY_RECOVERY_AND_PORTFOLIO_CONTROL.md"
$registryPath = Require-File "Plan\10_REGISTRIES\comfyui_delivery_portfolio_registry.json"
$snapshotPath = Require-File "tools\New-ComfyUIDeliveryProgressSnapshot.ps1"

if (Test-Path -LiteralPath $registryPath) {
  try { $registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json } catch { $issues.Add("invalid_json:portfolio_registry") }
  if ($registry) {
    foreach ($modality in @("image", "video", "audio")) {
      if (!@($registry.lanes | Where-Object modality -eq $modality).Count) { $issues.Add("missing_modality:$modality") }
      if (!@($registry.lanes | Where-Object { $_.modality -eq $modality -and $_.classification -eq "required_production" }).Count) { $issues.Add("missing_required_production:$modality") }
    }
    $allowed = @("required_production", "required_fallback", "required_support", "experimental", "deferred", "retired")
    foreach ($lane in $registry.lanes) {
      if (!$lane.lane_id) { $issues.Add("lane_missing_id") }
      if ($lane.classification -notin $allowed) { $issues.Add("invalid_classification:$($lane.lane_id)") }
      if (!$lane.next_concrete_outcome) { $issues.Add("missing_next_outcome:$($lane.lane_id)") }
    }
  }
}

if (Test-Path -LiteralPath $policyPath) {
  $policy = Get-Content -LiteralPath $policyPath -Raw
  foreach ($term in @("DELIVERY_STAGNATION", "PORTFOLIO_STARVATION", "last_real_generation_at", "bookkeeping_effort_ratio", "separate versioned ComfyUI API workflows")) {
    if ($policy -notmatch [regex]::Escape($term)) { $issues.Add("policy_missing:$term") }
  }
}

$automationRoot = Join-Path $ProjectRoot "tools\ai_worker_handoffs\automations"
$projectTomls = @(Get-ChildItem -LiteralPath $automationRoot -Filter "comfy-ui-main-*.toml" -File |
  Where-Object { $_.Name -notmatch "wave42" })
if ($projectTomls.Count -lt 7) { $issues.Add("canonical_project_automation_count_lt_7") }
foreach ($file in $projectTomls) {
  $text = Get-Content -LiteralPath $file.FullName -Raw
  if ($text -notmatch "COMFYUI_DELIVERY_RECOVERY_AND_PORTFOLIO_CONTROL") { $issues.Add("automation_missing_delivery_policy:$($file.Name)") }
  if ($text -match "next concrete selected-inpaint") { $issues.Add("automation_stale_selected_inpaint_steering:$($file.Name)") }
}

if (Test-Path -LiteralPath $snapshotPath) {
  try {
    $snapshotJson = & $snapshotPath -ProjectRoot $ProjectRoot -WindowHours 24
    $snapshot = $snapshotJson | ConvertFrom-Json
    foreach ($field in @("delivery_classification", "new_media_artifact_count", "quality_metric_delta", "repeated_readiness_or_gate_count", "bookkeeping_effort_ratio", "starved_modalities")) {
      if ($field -notin $snapshot.psobject.Properties.Name) { $issues.Add("snapshot_missing:$field") }
    }
  } catch {
    $issues.Add("snapshot_execution_failed:$($_.Exception.Message)")
  }
}

$result = [ordered]@{
  schema_version = "1.0"
  generated_at = (Get-Date).ToString("o")
  classification = if ($issues.Count) { "DELIVERY_RECOVERY_CONTROLS_FAIL" } else { "DELIVERY_RECOVERY_CONTROLS_PASS" }
  pass = $issues.Count -eq 0
  issue_count = $issues.Count
  issues = @($issues)
}
$result | ConvertTo-Json -Depth 6
if ($issues.Count) { exit 1 }
