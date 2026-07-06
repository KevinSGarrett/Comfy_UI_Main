<#
.SYNOPSIS
Validates that workflow run packages can be guarded by the image router.

.DESCRIPTION
Runs New-WorkflowRunPackage.ps1 in a temp package root for a compatible
RealVisXL route and an intentionally mismatched low-risk package request. This
is local-only and does not contact AWS, GitHub API, Civitai, ComfyUI, or EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator).Replace("\", "/")
}

function Invoke-ProcessCapture {
  param(
    [Parameter(Mandatory=$true)][string]$FileName,
    [Parameter(Mandatory=$true)][string[]]$Arguments,
    [int]$TimeoutSeconds = 120
  )

  $processInfo = New-Object System.Diagnostics.ProcessStartInfo
  $processInfo.FileName = $FileName
  $processInfo.UseShellExecute = $false
  $processInfo.RedirectStandardOutput = $true
  $processInfo.RedirectStandardError = $true
  $processInfo.RedirectStandardInput = $true
  $quotedArgs = @()
  foreach ($argument in $Arguments) {
    if ($argument -match '[\s"]') {
      $quotedArgs += '"' + ($argument -replace '"', '\"') + '"'
    } else {
      $quotedArgs += $argument
    }
  }
  $processInfo.Arguments = ($quotedArgs -join " ")

  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $processInfo
  $null = $process.Start()
  $process.StandardInput.Close()
  $stdout = $process.StandardOutput.ReadToEnd()
  $stderr = $process.StandardError.ReadToEnd()
  if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    try { $process.Kill() } catch {}
    return [ordered]@{
      exit_code = 124
      stdout = $stdout.Trim()
      stderr = (($stderr, "Timed out waiting for package router gate.") -join "`n").Trim()
    }
  }

  return [ordered]@{
    exit_code = $process.ExitCode
    stdout = $stdout.Trim()
    stderr = $stderr.Trim()
  }
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function New-Check {
  param(
    [string]$Name,
    [bool]$Passed,
    [object]$Observed,
    [object]$Expected
  )
  return [ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Get-OutputTail {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  if ($Text.Length -gt 1200) { return $Text.Substring($Text.Length - 1200) }
  return $Text
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Run_Package\W66_WORKFLOW_RUN_PACKAGE_ROUTER_GATE_$stamp.json"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "comfy_workflow_package_router_gate_$stamp"
New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

$packageScript = Join-Path $ProjectRoot "tools\New-WorkflowRunPackage.ps1"
$routeRequest = Join-Path $ProjectRoot "Plan\09_EXAMPLES\wave64_image_engine_route_realvisxl_request.example.json"
$positiveRunId = "router_gate_positive_realvisxl_$stamp"
$negativeRunId = "router_gate_negative_low_risk_$stamp"

$positiveRun = Invoke-ProcessCapture -FileName "powershell" -Arguments @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $packageScript,
  "-ProjectRoot",
  $ProjectRoot,
  "-PackageRoot",
  $tempRoot,
  "-LaneId",
  "sdxl_realvisxl_base_lane",
  "-AllowNonFirstLane",
  "-RouteRequestFile",
  $routeRequest,
  "-RunId",
  $positiveRunId
)

$positiveManifestPath = Join-Path $tempRoot "$positiveRunId\RUN_PACKAGE_MANIFEST.json"
$positiveManifest = Read-JsonFile -Path $positiveManifestPath

$negativeRun = Invoke-ProcessCapture -FileName "powershell" -Arguments @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-File",
  $packageScript,
  "-ProjectRoot",
  $ProjectRoot,
  "-PackageRoot",
  $tempRoot,
  "-LaneId",
  "sdxl_low_risk_fallback_lane",
  "-RouteRequestFile",
  $routeRequest,
  "-RunId",
  $negativeRunId
)

$negativeText = (($negativeRun.stdout, $negativeRun.stderr) -join "`n")
$checks = @()
$checks += New-Check -Name "positive_package_exit_zero" -Passed ($positiveRun.exit_code -eq 0) -Observed $positiveRun.exit_code -Expected 0
$checks += New-Check -Name "positive_manifest_passes" -Passed ([string]$positiveManifest.result -eq "pass_local_only") -Observed $positiveManifest.result -Expected "pass_local_only"
$checks += New-Check -Name "positive_route_gate_supplied" -Passed ($positiveManifest.route_gate.supplied -eq $true) -Observed $positiveManifest.route_gate.supplied -Expected $true
$checks += New-Check -Name "positive_route_gate_passes" -Passed ([string]$positiveManifest.route_gate.result -eq "pass_local_only") -Observed $positiveManifest.route_gate.result -Expected "pass_local_only"
$checks += New-Check -Name "positive_route_gate_matches_lane" -Passed ([string]$positiveManifest.route_gate.selected_lane_id -eq "sdxl_realvisxl_base_lane") -Observed $positiveManifest.route_gate.selected_lane_id -Expected "sdxl_realvisxl_base_lane"
$checks += New-Check -Name "positive_package_no_external_contact" -Passed ($positiveManifest.local_only -eq $true -and $positiveManifest.aws_contacted -eq $false -and $positiveManifest.github_api_contacted -eq $false -and $positiveManifest.civitai_contacted -eq $false -and $positiveManifest.comfyui_contacted -eq $false -and $positiveManifest.ec2_started -eq $false -and $positiveManifest.generation_executed -eq $false) -Observed ([ordered]@{ local_only = $positiveManifest.local_only; aws = $positiveManifest.aws_contacted; github_api = $positiveManifest.github_api_contacted; civitai = $positiveManifest.civitai_contacted; comfyui = $positiveManifest.comfyui_contacted; ec2_started = $positiveManifest.ec2_started; generation_executed = $positiveManifest.generation_executed }) -Expected "local only; all contacts false; no EC2/generation"
$checks += New-Check -Name "negative_package_exit_nonzero" -Passed ($negativeRun.exit_code -ne 0) -Observed $negativeRun.exit_code -Expected "nonzero"
$checks += New-Check -Name "negative_blocks_lane_mismatch" -Passed ($negativeText -match "Route gate selected 'sdxl_realvisxl_base_lane' but package lane is 'sdxl_low_risk_fallback_lane'") -Observed (Get-OutputTail -Text $negativeText) -Expected "router lane mismatch error"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W66-WORKFLOW-RUN-PACKAGE-ROUTER-GATE-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W64-009"
  artifact_type = "workflow_run_package_router_gate_validation"
  local_only = $true
  ec2_started = $false
  generation_executed = $false
  scripts = [ordered]@{
    package_builder = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $packageScript
    validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $PSCommandPath
  }
  route_request = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $routeRequest
  validation_temp_root = "[VALIDATION_TEMP_ROOT]"
  positive = [ordered]@{
    exit_code = $positiveRun.exit_code
    manifest_path = "[VALIDATION_TEMP_ROOT]/$positiveRunId/RUN_PACKAGE_MANIFEST.json"
    selected_lane_id = [string]$positiveManifest.route_gate.selected_lane_id
    selected_model_file = [string]$positiveManifest.route_gate.selected_model_file
    result = [string]$positiveManifest.result
  }
  negative = [ordered]@{
    exit_code = $negativeRun.exit_code
    output_tail = Get-OutputTail -Text $negativeText
  }
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "Use -RouteRequestFile on future image run packages so package lane selection cannot bypass router/model compatibility proof."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}
$record | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $OutFile -Encoding UTF8
$record | ConvertTo-Json -Depth 80
if ($record.result -ne "pass_local_only") {
  exit 1
}
