[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

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
$hydrationGuardPath = Require-File "tools\Test-ComfyUIHydrationIntegrityGuard.ps1"

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
  foreach ($term in @("DELIVERY_STAGNATION", "PORTFOLIO_STARVATION", "candidate_media_latest_write_at", "verified_new_delivery_count", "bookkeeping_effort_ratio", "separate versioned ComfyUI API workflows")) {
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
    foreach ($field in @("delivery_classification", "candidate_media_latest_write_at", "candidate_media_artifact_count", "verified_new_delivery_count", "verified_new_delivery", "quality_metric_delta", "repeated_readiness_or_gate_count", "bookkeeping_effort_ratio", "starved_modalities")) {
      if ($field -notin $snapshot.psobject.Properties.Name) { $issues.Add("snapshot_missing:$field") }
    }
  } catch {
    $issues.Add("snapshot_execution_failed:$($_.Exception.Message)")
  }
}

if (Test-Path -LiteralPath $hydrationGuardPath) {
  try {
    $hydration = (& $hydrationGuardPath -ProjectRoot $ProjectRoot -NoExit) | ConvertFrom-Json
    if (!$hydration.pass) { $issues.Add("hydration_integrity_guard_failed:$($hydration.issue_count)") }
  } catch {
    $issues.Add("hydration_integrity_guard_execution_failed:$($_.Exception.Message)")
  }
}

function Write-Json([string]$path, $value) {
  $parent = Split-Path -Parent $path
  if (!(Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
  [IO.File]::WriteAllText($path, ($value | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding($false)))
}

function New-SnapshotTestRoot([string]$label) {
  $root = Join-Path $ProjectRoot ("runtime_artifacts\delivery_snapshot_test_workspaces\{0}_{1}" -f $label, [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $root -Force | Out-Null
  Write-Json (Join-Path $root "Plan\10_REGISTRIES\comfyui_delivery_portfolio_registry.json") ([ordered]@{
      portfolio_starvation_hours = 24
      lanes = @([ordered]@{
          lane_id = "test_image_lane"
          modality = "image"
          classification = "required_production"
          production_lane_certified = $false
          recovery_priority = 1
          next_concrete_outcome = "test"
        })
    })
  New-Item -ItemType Directory -Path (Join-Path $root "Plan\Instructions\QA\Evidence\Workflow_Runtime") -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $root "Plan\Instructions\Operations\Pulled_Back_Artifacts\delivery_test") -Force | Out-Null
  return $root
}

function New-TestMedia([string]$root, [string]$name, [byte[]]$bytes) {
  $path = Join-Path $root ("Plan\Instructions\Operations\Pulled_Back_Artifacts\delivery_test\" + $name)
  [IO.File]::WriteAllBytes($path, $bytes)
  (Get-Item -LiteralPath $path).LastWriteTime = Get-Date
  return $path
}

function New-DeliveryEvidence([string]$root, [string]$name, [string]$mediaPath, [string]$sha256, [bool]$directQa = $false) {
  $relative = $mediaPath.Substring($root.Length).TrimStart("\").Replace("\", "/")
  $record = [ordered]@{
    schema_version = "test"
    execution_timestamp = (Get-Date).ToString("o")
    result = "pass_test_execution"
    generation_executed = !$directQa
    direct_qa_passed = $directQa
    output = [ordered]@{ type = "output"; path = $relative; sha256 = $sha256 }
  }
  Write-Json (Join-Path $root ("Plan\Instructions\QA\Evidence\Workflow_Runtime\" + $name)) $record
}

if (Test-Path -LiteralPath $snapshotPath) {
  $testRoots = [Collections.Generic.List[string]]::new()
  try {
    $root = New-SnapshotTestRoot "touched"
    $testRoots.Add($root)
    New-TestMedia $root "touched_historical.png" ([byte[]](1, 2, 3, 4)) | Out-Null
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.candidate_media_artifact_count -ne 1) { $issues.Add("snapshot_fixture_touched_not_observed") }
    if ($result.verified_new_delivery_count -ne 0) { $issues.Add("snapshot_fixture_touched_false_verified") }
    if ($result.delivery_classification -eq "DELIVERY_ADVANCING") { $issues.Add("snapshot_fixture_touched_false_advancing") }

    $root = New-SnapshotTestRoot "unrelated"
    $testRoots.Add($root)
    New-TestMedia $root "unrelated.png" ([byte[]](5, 6, 7, 8)) | Out-Null
    Write-Json (Join-Path $root "Plan\Instructions\QA\Evidence\Workflow_Runtime\unrelated_runtime.json") ([ordered]@{
        execution_timestamp = (Get-Date).ToString("o")
        result = "pass_test_execution"
        generation_executed = $true
        output = [ordered]@{ path = "missing.png"; sha256 = ("a" * 64) }
      })
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 0) { $issues.Add("snapshot_fixture_unrelated_false_verified") }

    $root = New-SnapshotTestRoot "duplicates"
    $testRoots.Add($root)
    $bytes = [byte[]](9, 10, 11, 12)
    $first = New-TestMedia $root "duplicate_a.png" $bytes
    $second = New-TestMedia $root "duplicate_b.png" $bytes
    $sha = (Get-FileHash -LiteralPath $first -Algorithm SHA256).Hash.ToLowerInvariant()
    New-DeliveryEvidence $root "duplicate_a_runtime.json" $first $sha
    New-DeliveryEvidence $root "duplicate_b_runtime.json" $second $sha
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 1) { $issues.Add("snapshot_fixture_duplicate_hash_not_deduped") }

    $root = New-SnapshotTestRoot "valid"
    $testRoots.Add($root)
    $mediaPath = New-TestMedia $root "valid.png" ([byte[]](13, 14, 15, 16))
    $sha = (Get-FileHash -LiteralPath $mediaPath -Algorithm SHA256).Hash.ToLowerInvariant()
    New-DeliveryEvidence $root "valid_direct_qa.json" $mediaPath $sha $true
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 1) { $issues.Add("snapshot_fixture_valid_pair_not_verified") }
    if ($result.delivery_classification -ne "DELIVERY_ADVANCING") { $issues.Add("snapshot_fixture_valid_pair_not_advancing") }
    if ($result.verified_new_delivery[0].media_sha256 -ne $sha) { $issues.Add("snapshot_fixture_valid_hash_mismatch") }

    $root = New-SnapshotTestRoot "recovery"
    $testRoots.Add($root)
    $mediaPath = New-TestMedia $root "restored.png" ([byte[]](17, 18, 19, 20))
    $sha = (Get-FileHash -LiteralPath $mediaPath -Algorithm SHA256).Hash.ToLowerInvariant()
    New-DeliveryEvidence $root "RECOVERED_RUNTIME_EVIDENCE.json" $mediaPath $sha
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 0) { $issues.Add("snapshot_fixture_recovery_false_verified") }

    $root = New-SnapshotTestRoot "diagnostic"
    $testRoots.Add($root)
    $mediaPath = New-TestMedia $root "candidate_mask_preview.png" ([byte[]](21, 22, 23, 24))
    $sha = (Get-FileHash -LiteralPath $mediaPath -Algorithm SHA256).Hash.ToLowerInvariant()
    New-DeliveryEvidence $root "diagnostic_runtime.json" $mediaPath $sha
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 0) { $issues.Add("snapshot_fixture_diagnostic_false_verified") }

    $root = New-SnapshotTestRoot "negated"
    $testRoots.Add($root)
    $mediaPath = New-TestMedia $root "negated.png" ([byte[]](25, 26, 27, 28))
    $sha = (Get-FileHash -LiteralPath $mediaPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $relative = $mediaPath.Substring($root.Length).TrimStart("\").Replace("\", "/")
    Write-Json (Join-Path $root "Plan\Instructions\QA\Evidence\Workflow_Runtime\negated_runtime.json") ([ordered]@{
        execution_timestamp = (Get-Date).ToString("o")
        result = "not_completed"
        generation_executed = $true
        output = [ordered]@{ type = "output"; path = $relative; sha256 = $sha }
      })
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 0) { $issues.Add("snapshot_fixture_negated_state_false_verified") }

    $root = New-SnapshotTestRoot "rollback"
    $testRoots.Add($root)
    $mediaPath = New-TestMedia $root "rollback.png" ([byte[]](29, 30, 31, 32))
    $sha = (Get-FileHash -LiteralPath $mediaPath -Algorithm SHA256).Hash.ToLowerInvariant()
    New-DeliveryEvidence $root "ROLLBACK_BACKFILL_RUNTIME.json" $mediaPath $sha
    $result = (& $snapshotPath -ProjectRoot $root -WindowHours 24) | ConvertFrom-Json
    if ($result.verified_new_delivery_count -ne 0) { $issues.Add("snapshot_fixture_rollback_false_verified") }
  } catch {
    $issues.Add("snapshot_fixture_execution_failed:$($_.Exception.Message)")
  } finally {
    foreach ($root in $testRoots) {
      if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
    }
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
$json = $result | ConvertTo-Json -Depth 6
if ($OutFile) {
  $parent = Split-Path -Parent $OutFile
  if ($parent -and !(Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
  [IO.File]::WriteAllText($OutFile, $json, (New-Object Text.UTF8Encoding($false)))
}
$json
if ($issues.Count) { exit 1 }
