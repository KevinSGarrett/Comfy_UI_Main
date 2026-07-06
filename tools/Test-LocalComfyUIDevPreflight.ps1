<#
.SYNOPSIS
Checks whether a local ComfyUI development lane can reduce EC2 usage.

.DESCRIPTION
Performs local-only checks for GPU availability, likely local ComfyUI roots,
model directories, and selected-lane static validation. This is a development
preflight only; it never claims equivalence with the target EC2 A10G runtime.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$LocalComfyRoot = "",
  [string]$OutFile = "",
  [switch]$RequireRunnableComfyUI
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function ConvertTo-ProjectRelativePath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  try {
    $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
    $baseFull = [System.IO.Path]::GetFullPath($ProjectRoot)
    if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
    $targetFull = [System.IO.Path]::GetFullPath($Path)
    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("\", "/")
  } catch {
    return $Path
  }
}

function Add-Check {
  param(
    [System.Collections.ArrayList]$Checks,
    [string]$Name,
    [bool]$Passed,
    [object]$Observed = $null,
    [string]$Message = ""
  )
  [void]$Checks.Add([ordered]@{
    name = $Name
    passed = $Passed
    observed = $Observed
    message = $Message
    result = $(if ($Passed) { "pass" } else { "fail" })
  })
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$checks = New-Object System.Collections.ArrayList
$errors = New-Object System.Collections.ArrayList

$gpuRecord = [ordered]@{
  nvidia_smi_found = $false
  name = $null
  memory_total_mib = $null
  driver_version = $null
  raw = $null
}
try {
  $gpuRaw = (nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null | Select-Object -First 1)
  if (![string]::IsNullOrWhiteSpace($gpuRaw)) {
    $parts = @($gpuRaw -split ",")
    $gpuRecord.nvidia_smi_found = $true
    $gpuRecord.name = $parts[0].Trim()
    $gpuRecord.memory_total_mib = [int](($parts[1] -replace "[^0-9]", "").Trim())
    $gpuRecord.driver_version = $parts[2].Trim()
    $gpuRecord.raw = $gpuRaw
  }
} catch {
  [void]$errors.Add("nvidia-smi check failed: $($_.Exception.Message)")
}
Add-Check -Checks $checks -Name "nvidia_gpu_available" -Passed ([bool]$gpuRecord.nvidia_smi_found) -Observed $gpuRecord
Add-Check -Checks $checks -Name "gpu_memory_suitable_for_low_res_sdxl_dev" -Passed (($gpuRecord.memory_total_mib -as [int]) -ge 7000) -Observed $gpuRecord.memory_total_mib -Message "Use low resolution, batch size 1, low steps, and low-VRAM settings for local development."

$candidateRoots = New-Object System.Collections.ArrayList
if (![string]::IsNullOrWhiteSpace($LocalComfyRoot)) { [void]$candidateRoots.Add($LocalComfyRoot) }
foreach ($candidate in @(
  "C:\Comfy_UI\ComfyUI",
  "C:\Comfy_UI\ComfyUI_windows_portable\ComfyUI",
  "C:\Comfy_UI\portable\ComfyUI",
  "C:\Comfy_UI\Runtime\ComfyUI",
  "C:\Comfy_UI",
  "C:\Comfy_UI_Main\ComfyUI",
  "C:\Comfy_UI_Main\ComfyUI_windows_portable\ComfyUI"
)) {
  [void]$candidateRoots.Add($candidate)
}

$comfyCandidates = @()
foreach ($candidate in @($candidateRoots | Select-Object -Unique)) {
  $mainPath = Join-Path $candidate "main.py"
  $comfyCandidates += [ordered]@{
    path = $candidate
    exists = (Test-Path -LiteralPath $candidate)
    main_py_exists = (Test-Path -LiteralPath $mainPath)
  }
}
$localComfy = @($comfyCandidates | Where-Object { $_.main_py_exists } | Select-Object -First 1)
Add-Check -Checks $checks -Name "local_comfyui_main_py_found" -Passed ($localComfy.Count -gt 0) -Observed $comfyCandidates -Message "Provide -LocalComfyRoot if ComfyUI is installed outside the standard candidate paths."

$modelRoots = @(
  "C:\Comfy_UI\models",
  "C:\Comfy_UI\ComfyUI\models",
  "C:\Comfy_UI_Main\models"
) | ForEach-Object {
  [ordered]@{
    path = $_
    exists = (Test-Path -LiteralPath $_)
  }
}
Add-Check -Checks $checks -Name "local_model_directory_candidate_exists" -Passed (@($modelRoots | Where-Object { $_.exists }).Count -gt 0) -Observed $modelRoots

$staticValidation = [ordered]@{
  attempted = $false
  qa_status = "not_run"
  defect_count = $null
  error = $null
}
try {
  $laneDir = Join-Path $ProjectRoot "Workflows\base_generation\$LaneId"
  $staticScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"
  if (!(Test-Path -LiteralPath $laneDir)) { throw "Lane directory missing: $laneDir" }
  if (!(Test-Path -LiteralPath $staticScript)) { throw "Static validator missing: $staticScript" }
  $staticValidation.attempted = $true
  $staticText = & powershell -NoProfile -ExecutionPolicy Bypass -File $staticScript -ProjectRoot $ProjectRoot -LaneDir $laneDir
  if ($LASTEXITCODE -ne 0) { throw "Static validator exited with code $LASTEXITCODE" }
  $staticJson = $staticText | Out-String | ConvertFrom-Json
  $staticValidation.qa_status = [string]$staticJson.qa_status
  $staticValidation.defect_count = @($staticJson.defects).Count
} catch {
  $staticValidation.error = $_.Exception.Message
  [void]$errors.Add("static validation failed: $($_.Exception.Message)")
}
Add-Check -Checks $checks -Name "selected_lane_static_valid" -Passed ([string]$staticValidation.qa_status -eq "pass") -Observed $staticValidation

$failedChecks = @($checks | Where-Object { -not $_.passed })
$runnableLocalDev = (
  [bool]$gpuRecord.nvidia_smi_found -and
  (($gpuRecord.memory_total_mib -as [int]) -ge 7000) -and
  ($localComfy.Count -gt 0) -and
  ([string]$staticValidation.qa_status -eq "pass")
)
$result = $(if ($RequireRunnableComfyUI -and $localComfy.Count -eq 0) {
  "needs_local_comfyui_path"
} elseif ($runnableLocalDev) {
  "pass_local_dev_candidate"
} else {
  "needs_local_dev_prerequisite"
})

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  lane_id = $LaneId
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  local_gpu = $gpuRecord
  local_comfyui = [ordered]@{
    selected_root = $(if ($localComfy.Count -gt 0) { [string]$localComfy[0].path } else { $null })
    candidates = $comfyCandidates
  }
  local_model_roots = $modelRoots
  static_validation = $staticValidation
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  local_dev_can_reduce_ec2_starts = $runnableLocalDev
  local_dev_replaces_ec2_final_proof = $false
  ec2_final_proof_still_required = $true
  result = $result
  next_action = "Use local ComfyUI only for low-cost prompt/workflow iteration. Reserve EC2 for target-runtime object-info, model path/hash, generation, pullback, and QA proof."
  errors = @($errors)
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
}

$record | ConvertTo-Json -Depth 30
if ($RequireRunnableComfyUI -and $record.result -ne "pass_local_dev_candidate") {
  exit 1
}
