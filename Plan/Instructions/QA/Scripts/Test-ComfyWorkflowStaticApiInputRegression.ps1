<#
.SYNOPSIS
Regression-tests API-only LoadImage input validation.

.DESCRIPTION
Runs the static workflow validator against both Normal lane copies, then injects
the UI-only LoadImage upload field into a temporary lane and verifies fail-closed
classification. This script is local-only and does not contact ComfyUI or AWS.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$validator = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"
$lanePaths = @(
  "Workflows\base_generation\sdxl_realvisxl_controlnet_normal_lane",
  "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_realvisxl_controlnet_normal_lane"
)

if (!(Test-Path -LiteralPath $validator -PathType Leaf)) {
  throw "Static workflow validator missing: $validator"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("comfy_workflow_static_api_input_" + [guid]::NewGuid().ToString("N"))
$results = @()
try {
  foreach ($relativeLane in $lanePaths) {
    $lane = Join-Path $ProjectRoot $relativeLane
    $resultFile = Join-Path $tempRoot ((Split-Path -Leaf $lane) + "_clean.json")
    $null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resultFile)
    $null = & powershell -NoProfile -File $validator -ProjectRoot $ProjectRoot -LaneDir $lane -OutFile $resultFile
    $exitCode = $LASTEXITCODE
    $record = Get-Content -LiteralPath $resultFile -Raw | ConvertFrom-Json
    $passed = ($exitCode -eq 0 -and [string]$record.qa_status -eq "pass")
    $results += [ordered]@{
      name = "clean_lane_passes"
      lane = $relativeLane.Replace("\", "/")
      exit_code = $exitCode
      qa_status = [string]$record.qa_status
      result = $(if ($passed) { "pass" } else { "fail" })
    }
  }

  $sourceLane = Join-Path $ProjectRoot $lanePaths[0]
  $mutatedLane = Join-Path $tempRoot "mutated_lane"
  $null = New-Item -ItemType Directory -Force -Path $mutatedLane
  Get-ChildItem -LiteralPath $sourceLane | Copy-Item -Destination $mutatedLane -Recurse -Force
  $mutatedWorkflowPath = Join-Path $mutatedLane "workflow.api.json"
  $mutatedWorkflow = Get-Content -LiteralPath $mutatedWorkflowPath -Raw | ConvertFrom-Json
  $mutatedWorkflow."11".inputs | Add-Member -NotePropertyName "upload" -NotePropertyValue "image"
  [System.IO.File]::WriteAllText(
    $mutatedWorkflowPath,
    ($mutatedWorkflow | ConvertTo-Json -Depth 40),
    (New-Object System.Text.UTF8Encoding($false))
  )

  $mutatedResultFile = Join-Path $tempRoot "mutated_result.json"
  $null = & powershell -NoProfile -File $validator -ProjectRoot $ProjectRoot -LaneDir $mutatedLane -OutFile $mutatedResultFile
  $mutatedExitCode = $LASTEXITCODE
  $mutatedRecord = Get-Content -LiteralPath $mutatedResultFile -Raw | ConvertFrom-Json
  $defectCodes = @($mutatedRecord.defects | ForEach-Object { [string]$_.code })
  $mutatedPassed = (
    $mutatedExitCode -eq 2 -and
    [string]$mutatedRecord.qa_status -eq "fail" -and
    $defectCodes -contains "load_image_ui_only_upload_input"
  )
  $results += [ordered]@{
    name = "ui_only_upload_fails_closed"
    lane = "temporary_mutation"
    exit_code = $mutatedExitCode
    qa_status = [string]$mutatedRecord.qa_status
    defect_codes = $defectCodes
    result = $(if ($mutatedPassed) { "pass" } else { "fail" })
  }
} finally {
  if (Test-Path -LiteralPath $tempRoot) {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
  }
}

$failures = @($results | Where-Object result -ne "pass")
$stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W64_COMFY_WORKFLOW_STATIC_API_INPUT_REGRESSION_$stamp.json"
}
$record = [ordered]@{
  evidence_id = "W64-COMFY-WORKFLOW-STATIC-API-INPUT-REGRESSION-$stamp"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failures.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  checked = $results.Count
  passed = @($results | Where-Object result -eq "pass").Count
  cases = $results
  failures = $failures
  next_action = $(if ($failures.Count -eq 0) { "Use API-only workflow inputs when rebuilding the Normal run package." } else { "Repair the static API-input validator before the next live runtime window." })
}
$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) { $null = New-Item -ItemType Directory -Force -Path $outDir }
[System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 12), (New-Object System.Text.UTF8Encoding($false)))
$record | ConvertTo-Json -Depth 12
if ($failures.Count -gt 0) { exit 2 }
