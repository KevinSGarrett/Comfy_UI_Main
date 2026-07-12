<#
.SYNOPSIS
Runs the Wave64 local image-engine router pass/block proof.

.DESCRIPTION
Executes the local router resolver against a RealVisXL request, an incompatible
Flux-LoRA-on-SDXL request, and a matrix-forbidden unproven SDXL LoRA request.
Current certification-blocked lane statuses must fail closed. This script is
local only and does not contact AWS, GitHub, Civitai, EC2, or ComfyUI.
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
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator).Replace("\", "/")
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
      stderr = (($stderr, "Timed out waiting for router resolver.") -join "`n").Trim()
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

function Get-OutputTail {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  if ($Text.Length -gt 1000) { return $Text.Substring($Text.Length - 1000) }
  return $Text
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

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Engine_Router\W64_IMAGE_ENGINE_ROUTER_VALIDATION_$stamp.json"
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
  throw "Python executable not found; cannot run Wave64 image-engine router."
}

$routerScript = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\scripts\resolve_wave64_image_engine_route.py"
$validRequest = Join-Path $ProjectRoot "Plan\09_EXAMPLES\wave64_image_engine_route_realvisxl_request.example.json"
$blockedRequest = Join-Path $ProjectRoot "Plan\09_EXAMPLES\wave64_image_engine_route_incompatible_lora_request.example.json"
$matrixBlockedRequest = Join-Path $ProjectRoot "Plan\09_EXAMPLES\wave64_image_engine_route_matrix_forbidden_sdxl_unproven_request.example.json"
$evidenceDir = Split-Path -Parent $OutFile
if ([string]::IsNullOrWhiteSpace($evidenceDir)) {
  $evidenceDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Engine_Router"
}
$validDecision = Join-Path $evidenceDir "W64_IMAGE_ENGINE_ROUTER_REALVISXL_DECISION_$stamp.json"
$blockedDecision = Join-Path $evidenceDir "W64_IMAGE_ENGINE_ROUTER_INCOMPATIBLE_LORA_DECISION_$stamp.json"
$matrixBlockedDecision = Join-Path $evidenceDir "W64_IMAGE_ENGINE_ROUTER_MATRIX_FORBIDDEN_DECISION_$stamp.json"

$validRun = Invoke-ProcessCapture -FileName $pythonCommand.Source -Arguments @($routerScript, "--root", $ProjectRoot, "--request", $validRequest, "--output", $validDecision)
$blockedRun = Invoke-ProcessCapture -FileName $pythonCommand.Source -Arguments @($routerScript, "--root", $ProjectRoot, "--request", $blockedRequest, "--output", $blockedDecision)
$matrixBlockedRun = Invoke-ProcessCapture -FileName $pythonCommand.Source -Arguments @($routerScript, "--root", $ProjectRoot, "--request", $matrixBlockedRequest, "--output", $matrixBlockedDecision)

$validJson = Read-JsonFile -Path $validDecision
$blockedJson = Read-JsonFile -Path $blockedDecision
$matrixBlockedJson = Read-JsonFile -Path $matrixBlockedDecision
$validCandidate = $validJson.candidate_results | Where-Object { $_.lane_id -eq "sdxl_realvisxl_base_lane" } | Select-Object -First 1
$blockedCandidate = $blockedJson.candidate_results | Where-Object { $_.lane_id -eq "sdxl_realvisxl_base_lane" } | Select-Object -First 1
$matrixBlockedCandidate = $matrixBlockedJson.candidate_results | Where-Object { $_.lane_id -eq "sdxl_realvisxl_base_lane" } | Select-Object -First 1
$validCheckByName = @{}
foreach ($check in $validCandidate.checks) { $validCheckByName[[string]$check.name] = $check }
$matrixBlockedCheckByName = @{}
foreach ($check in $matrixBlockedCandidate.checks) { $matrixBlockedCheckByName[[string]$check.name] = $check }

$checks = @()
$checks += New-Check -Name "valid_router_exit_zero" -Passed ($validRun.exit_code -eq 0) -Observed $validRun.exit_code -Expected 0
$checks += New-Check -Name "blocked_router_exit_zero" -Passed ($blockedRun.exit_code -eq 0) -Observed $blockedRun.exit_code -Expected 0
$checks += New-Check -Name "matrix_blocked_router_exit_zero" -Passed ($matrixBlockedRun.exit_code -eq 0) -Observed $matrixBlockedRun.exit_code -Expected 0
$checks += New-Check -Name "current_realvisxl_request_fails_closed" -Passed ([string]$validJson.result -eq "block_local_only") -Observed $validJson.result -Expected "block_local_only"
$checks += New-Check -Name "current_realvisxl_request_has_no_selected_lane" -Passed ($null -eq $validJson.selected_lane_id) -Observed $validJson.selected_lane_id -Expected $null
$checks += New-Check -Name "blocked_suffix_queue_status_rejected" -Passed ([string]$validCheckByName["queue_status_runtime_smoke_proven"].result -eq "fail") -Observed $validCheckByName["queue_status_runtime_smoke_proven"].observed -Expected "fail closed on blocked/fail/pending qualifier"
$checks += New-Check -Name "pending_requirement_status_rejected" -Passed ([string]$validCheckByName["requirements_status_runtime_smoke_qa_complete"].result -eq "fail") -Observed $validCheckByName["requirements_status_runtime_smoke_qa_complete"].observed -Expected "fail closed on pending qualifier"
$checks += New-Check -Name "realvisxl_checkpoint_allowed_by_matrix" -Passed ([string]$validCheckByName["matrix_checkpoint_family_allowed"].result -eq "pass") -Observed $validCheckByName["matrix_checkpoint_family_allowed"].observed -Expected "realvisxl_sdxl"
$checks += New-Check -Name "realvisxl_empty_lora_stack_allowed_by_matrix" -Passed ([string]$validCheckByName["matrix_lora_families_allowed"].result -eq "pass") -Observed $validCheckByName["matrix_lora_families_allowed"].observed -Expected @()
$checks += New-Check -Name "blocked_request_blocks_local_gate" -Passed ([string]$blockedJson.result -eq "block_local_only") -Observed $blockedJson.result -Expected "block_local_only"
$checks += New-Check -Name "blocked_request_has_no_selected_lane" -Passed ($null -eq $blockedJson.selected_lane_id) -Observed $blockedJson.selected_lane_id -Expected $null
$checks += New-Check -Name "blocked_request_reports_lora_family_mismatch" -Passed (@($blockedCandidate.blockers) -contains "lora_families_match_engine_family") -Observed @($blockedCandidate.blockers) -Expected "lora_families_match_engine_family"
$checks += New-Check -Name "matrix_forbidden_request_blocks_local_gate" -Passed ([string]$matrixBlockedJson.result -eq "block_local_only") -Observed $matrixBlockedJson.result -Expected "block_local_only"
$checks += New-Check -Name "matrix_forbidden_request_has_no_selected_lane" -Passed ($null -eq $matrixBlockedJson.selected_lane_id) -Observed $matrixBlockedJson.selected_lane_id -Expected $null
$checks += New-Check -Name "matrix_forbidden_same_normalized_family_is_rejected" -Passed ([string]$matrixBlockedCheckByName["lora_families_match_engine_family"].result -eq "pass" -and [string]$matrixBlockedCheckByName["matrix_lora_families_allowed"].result -eq "fail") -Observed $matrixBlockedCheckByName["matrix_lora_families_allowed"].observed -Expected "matrix rejects sdxl_unproven after broad family check passes"
$checks += New-Check -Name "decision_records_current_proof_source_hashes" -Passed (@($validJson.proof_sources.PSObject.Properties).Count -eq 4) -Observed @($validJson.proof_sources.PSObject.Properties.Name) -Expected "four current source hashes"
$checks += New-Check -Name "valid_request_did_not_contact_external_services" -Passed ($validJson.local_only -eq $true -and $validJson.ec2_started -eq $false -and $validJson.generation_executed -eq $false -and $validJson.contacts.aws -eq $false -and $validJson.contacts.civitai -eq $false -and $validJson.contacts.comfyui -eq $false -and $validJson.contacts.ec2 -eq $false -and $validJson.contacts.github_api -eq $false) -Observed $validJson.contacts -Expected "all false; no EC2/generation"
$checks += New-Check -Name "blocked_request_did_not_contact_external_services" -Passed ($blockedJson.local_only -eq $true -and $blockedJson.ec2_started -eq $false -and $blockedJson.generation_executed -eq $false -and $blockedJson.contacts.aws -eq $false -and $blockedJson.contacts.civitai -eq $false -and $blockedJson.contacts.comfyui -eq $false -and $blockedJson.contacts.ec2 -eq $false -and $blockedJson.contacts.github_api -eq $false) -Observed $blockedJson.contacts -Expected "all false; no EC2/generation"
$checks += New-Check -Name "matrix_blocked_request_did_not_contact_external_services" -Passed ($matrixBlockedJson.local_only -eq $true -and $matrixBlockedJson.ec2_started -eq $false -and $matrixBlockedJson.generation_executed -eq $false -and $matrixBlockedJson.contacts.aws -eq $false -and $matrixBlockedJson.contacts.civitai -eq $false -and $matrixBlockedJson.contacts.comfyui -eq $false -and $matrixBlockedJson.contacts.ec2 -eq $false -and $matrixBlockedJson.contacts.github_api -eq $false) -Observed $matrixBlockedJson.contacts -Expected "all false; no EC2/generation"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W64_IMAGE_ENGINE_ROUTER_VALIDATION_$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W64-009"
  artifact_type = "wave64_image_engine_router_validation"
  local_only = $true
  ec2_started = $false
  generation_executed = $false
  scripts = [ordered]@{
    router = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $routerScript
    validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $PSCommandPath
  }
  requests = [ordered]@{
    compatible = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $validRequest
    incompatible_lora = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $blockedRequest
    matrix_forbidden = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $matrixBlockedRequest
  }
  decisions = [ordered]@{
    compatible = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $validDecision
    incompatible_lora = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $blockedDecision
    matrix_forbidden = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $matrixBlockedDecision
  }
  runs = [ordered]@{
    compatible = [ordered]@{
      exit_code = $validRun.exit_code
      stdout_tail = Get-OutputTail -Text $validRun.stdout
      stderr_tail = Get-OutputTail -Text $validRun.stderr
    }
    incompatible_lora = [ordered]@{
      exit_code = $blockedRun.exit_code
      stdout_tail = Get-OutputTail -Text $blockedRun.stdout
      stderr_tail = Get-OutputTail -Text $blockedRun.stderr
    }
    matrix_forbidden = [ordered]@{
      exit_code = $matrixBlockedRun.exit_code
      stdout_tail = Get-OutputTail -Text $matrixBlockedRun.stdout
      stderr_tail = Get-OutputTail -Text $matrixBlockedRun.stderr
    }
  }
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  known_limits = @(
    "Local router validation does not perform a new ComfyUI generation.",
    "Local router validation does not start EC2 or prove new model binaries.",
    "This validates active base-generation image lanes; future video/audio/router families need separate gates."
  )
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
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
