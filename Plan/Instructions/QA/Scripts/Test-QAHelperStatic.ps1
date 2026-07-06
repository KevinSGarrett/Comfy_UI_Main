<#
.SYNOPSIS
Validates the current Wave 61 QA helper set with local-only checks.

.DESCRIPTION
Parses every QA/Scripts PowerShell helper, parses QA JSON schemas/templates,
checks markdown templates, runs local-only smoke checks into a temp directory,
and writes a machine-readable evidence record. It does not run ComfyUI, start
EC2, inspect real generated artifacts, or claim final visual QA.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
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
  return $relativePath.Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Test-PathIsUnderRoot {
  param(
    [string]$RootPath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($RootPath) -or [string]::IsNullOrWhiteSpace($TargetPath)) { return $false }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $rootFull = [System.IO.Path]::GetFullPath($RootPath).TrimEnd("\", "/")
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  return ($targetFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
    $targetFull.StartsWith("$rootFull$separator", [System.StringComparison]::OrdinalIgnoreCase))
}

function ConvertTo-EvidencePath {
  param(
    [string]$BasePath,
    [string]$TargetPath,
    [string]$TempRoot = ""
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }

  if (Test-PathIsUnderRoot -RootPath $TempRoot -TargetPath $TargetPath) {
    $relativeTemp = Get-RelativePathCompat -BasePath $TempRoot -TargetPath $TargetPath
    $relativeTemp = $relativeTemp.Replace("\", "/")
    if ([string]::IsNullOrWhiteSpace($relativeTemp) -or $relativeTemp -eq ".") { return "[VALIDATION_TEMP_ROOT]" }
    return "[VALIDATION_TEMP_ROOT]/$relativeTemp"
  }

  if (![string]::IsNullOrWhiteSpace($env:TEMP) -and (Test-PathIsUnderRoot -RootPath $env:TEMP -TargetPath $TargetPath)) {
    $relativeTemp = Get-RelativePathCompat -BasePath $env:TEMP -TargetPath $TargetPath
    return ("[TEMP]/" + $relativeTemp.Replace("\", "/"))
  }

  return ConvertTo-ProjectRelativePath -BasePath $BasePath -TargetPath $TargetPath
}

function ConvertTo-RedactedEvidenceText {
  param(
    [string]$Text,
    [string]$TempRoot = ""
  )

  if ([string]::IsNullOrEmpty($Text)) { return $Text }

  $redacted = $Text
  $replacements = @()
  if (![string]::IsNullOrWhiteSpace($TempRoot)) {
    $tempRootFull = [System.IO.Path]::GetFullPath($TempRoot).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempRootFull; To = "[VALIDATION_TEMP_ROOT]" }
    $replacements += [ordered]@{ From = $tempRootFull.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
    $replacements += [ordered]@{ From = $tempRootFull.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    $tempRootRelative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $tempRootFull
    if (![string]::IsNullOrWhiteSpace($tempRootRelative)) {
      $replacements += [ordered]@{ From = $tempRootRelative; To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootRelative.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootRelative.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    }
  }
  if (![string]::IsNullOrWhiteSpace($env:TEMP)) {
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempFull; To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "/"); To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "\\"); To = "[TEMP]" }
    $tempRelative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $tempFull
    if (![string]::IsNullOrWhiteSpace($tempRelative)) {
      $replacements += [ordered]@{ From = $tempRelative; To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempRelative.Replace("\", "/"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempRelative.Replace("\", "\\"); To = "[TEMP]" }
    }
  }

  foreach ($replacement in $replacements) {
    if (![string]::IsNullOrWhiteSpace($replacement.From)) {
      $redacted = $redacted.Replace($replacement.From, $replacement.To)
    }
  }
  return $redacted
}

function Test-PowerShellParser {
  param([Parameter(Mandatory=$true)][string]$Path)

  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) > $null
  return [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    parse_errors = $errors.Count
    errors = @($errors | ForEach-Object { $_.Message })
    result = $(if ($errors.Count -eq 0) { "pass" } else { "fail" })
  }
}

function Test-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
  }
  try {
    $null = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }
  return $entry
}

function Test-MarkdownTemplate {
  param([Parameter(Mandatory=$true)][string]$Path)

  $text = Get-Content -LiteralPath $Path -Raw
  return [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    bytes = (Get-Item -LiteralPath $Path).Length
    result = $(if (![string]::IsNullOrWhiteSpace($text)) { "pass" } else { "fail" })
  }
}

function Test-JsonProperty {
  param(
    [object]$Object,
    [Parameter(Mandatory=$true)][string]$Name
  )

  if ($null -eq $Object) { return $false }
  return ($null -ne $Object.PSObject.Properties[$Name])
}

function Invoke-LocalHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [string]$ExpectedOutputFile = "",
    [string]$ExpectedOutputType = "none"
  )

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot
  $entry = [ordered]@{
    name = $Name
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $LASTEXITCODE
    result = $(if ($LASTEXITCODE -eq 0) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $ExpectedOutputFile -TempRoot $script:ValidationTempRoot
    expected_output_type = $ExpectedOutputType
    expected_output_file_exists = (![string]::IsNullOrWhiteSpace($ExpectedOutputFile) -and (Test-Path -LiteralPath $ExpectedOutputFile))
    expected_output_valid = $false
    expected_output_error = $null
  }

  if ($entry.expected_output_file_exists) {
    try {
      if ($ExpectedOutputType -eq "json") {
        $null = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
        $entry.expected_output_valid = $true
      } elseif ($ExpectedOutputType -eq "markdown") {
        $content = Get-Content -LiteralPath $ExpectedOutputFile -Raw
        $entry.expected_output_valid = (![string]::IsNullOrWhiteSpace($content))
      } else {
        $entry.expected_output_valid = $true
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  } elseif ($ExpectedOutputType -ne "none") {
    $entry.result = "fail"
    $entry.expected_output_error = "Expected output file was not created."
  }
  return $entry
}

function New-ContractCheck {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][bool]$Passed,
    [string]$Expected = "",
    [string]$Observed = ""
  )

  return [ordered]@{
    name = $Name
    expected = $Expected
    observed = $Observed
    result = $(if ($Passed) { "pass" } else { "fail" })
  }
}

function Test-ProjectReadinessSnapshotContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = "project_readiness_snapshot_contract"
    path = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $Path -TempRoot $script:ValidationTempRoot
    result = "fail"
    error = $null
    lane_id = $null
    top_level_result = $null
    failure_category = $null
    local_ready = $false
    scan_result = $null
    scan_hit_count = $null
    ec2_start_allowed = $null
    generation_allowed = $null
    auth_safe_to_start_ec2 = $null
    lane_readiness_lane_id = $null
    lane_readiness_lane_match = $null
    lane_ready_for_ec2_static_proof = $null
    lane_ready_for_generation = $null
    runtime_handoff_result = $null
    runtime_handoff_lane_id = $null
    runtime_handoff_lane_match = $null
    runtime_handoff_failure_category = $null
    runtime_handoff_next_required_action = $null
    runtime_handoff_local_only = $null
    runtime_handoff_aws_contacted = $null
    runtime_handoff_github_api_contacted = $null
    runtime_handoff_civitai_contacted = $null
    runtime_handoff_ec2_started = $null
    runtime_handoff_generation_executed = $null
    runtime_handoff_command_step_count = $null
    runtime_handoff_markdown_written = $null
    runtime_lane_queue_result = $null
    runtime_lane_queue_selected_lane_in_queue = $null
    runtime_lane_queue_selected_lane_order = $null
    runtime_lane_queue_first_runtime_lane_id = $null
    runtime_lane_queue_first_runtime_lane_match = $null
    runtime_lane_queue_current_runtime_lane_id = $null
    runtime_lane_queue_current_runtime_lane_match = $null
    runtime_lane_queue_failed_check_count = $null
    runtime_lane_queue_local_only = $null
    runtime_lane_queue_aws_contacted = $null
    runtime_lane_queue_github_api_contacted = $null
    runtime_lane_queue_civitai_contacted = $null
    runtime_lane_queue_comfyui_contacted = $null
    runtime_lane_queue_ec2_started = $null
    runtime_lane_queue_generation_executed = $null
    runtime_lane_queue_allows_selected_lane_ec2_static_proof = $null
    model_registry_coverage_result = $null
    model_registry_coverage_selected_lane_covered = $null
    model_registry_coverage_selected_lane_result = $null
    model_registry_coverage_failed_check_count = $null
    model_registry_coverage_local_only = $null
    model_registry_coverage_aws_contacted = $null
    model_registry_coverage_github_api_contacted = $null
    model_registry_coverage_civitai_contacted = $null
    model_registry_coverage_comfyui_contacted = $null
    model_registry_coverage_ec2_started = $null
    model_registry_coverage_generation_executed = $null
    model_registry_coverage_allows_selected_lane_ec2_static_proof = $null
    coordinator_blocked_execute_records_safe = $null
    contract_check_failures = 0
    contract_checks = @()
  }

  $checks = @()
  try {
    if (!(Test-Path -LiteralPath $Path)) {
      throw "Project readiness snapshot file was not created."
    }

    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $recognizedResults = @(
      "pass_local_ready_runtime_blocked_auth",
      "pass_local_ready_runtime_blocked",
      "pass_local_ready_for_ec2_static_proof",
      "pass_ready_for_generation",
      "pass_runtime_smoke_qa_complete"
    )
    $recognizedHandoffResults = @(
      "handoff_ready_runtime_blocked_auth",
      "handoff_auth_ready_lane_not_ready",
      "handoff_lane_queue_order_blocked",
      "handoff_model_registry_blocked",
      "handoff_ready_for_ec2_static_proof",
      "handoff_ready_for_generation",
      "handoff_ready_for_pullback_qa",
      "handoff_runtime_smoke_qa_complete"
    )

    if (Test-JsonProperty -Object $payload -Name "result") {
      $entry.top_level_result = [string]$payload.result
    }
    if (Test-JsonProperty -Object $payload -Name "lane_id") {
      $entry.lane_id = [string]$payload.lane_id
    }
    if (Test-JsonProperty -Object $payload -Name "failure_category") {
      $entry.failure_category = [string]$payload.failure_category
    }
    if (Test-JsonProperty -Object $payload -Name "local_ready") {
      $entry.local_ready = [bool]$payload.local_ready
    }

    $checks += New-ContractCheck -Name "top_level_result_recognized" `
      -Passed (@($recognizedResults) -contains $entry.top_level_result) `
      -Expected ($recognizedResults -join " | ") `
      -Observed ([string]$entry.top_level_result)

    $checks += New-ContractCheck -Name "local_ready_true" `
      -Passed ([bool]$entry.local_ready) `
      -Expected "true" `
      -Observed ([string]$entry.local_ready)
    $checks += New-ContractCheck -Name "lane_id_present" `
      -Passed (![string]::IsNullOrWhiteSpace([string]$entry.lane_id)) `
      -Expected "non-empty" `
      -Observed ([string]$entry.lane_id)

    if (Test-JsonProperty -Object $payload -Name "secret_private_path_scan") {
      $scan = $payload.secret_private_path_scan
      if (Test-JsonProperty -Object $scan -Name "result") { $entry.scan_result = [string]$scan.result }
      if (Test-JsonProperty -Object $scan -Name "hit_count") { $entry.scan_hit_count = [int]$scan.hit_count }
    }

    $checks += New-ContractCheck -Name "secret_private_scan_passes" `
      -Passed ($entry.scan_result -eq "pass") `
      -Expected "pass" `
      -Observed ([string]$entry.scan_result)
    $checks += New-ContractCheck -Name "secret_private_scan_zero_hits" `
      -Passed ($entry.scan_hit_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.scan_hit_count)

    if (!(Test-JsonProperty -Object $payload -Name "runtime_gates")) {
      $checks += New-ContractCheck -Name "runtime_gates_present" -Passed $false -Expected "present" -Observed "missing"
    } else {
      $runtime = $payload.runtime_gates
      $checks += New-ContractCheck -Name "runtime_gates_present" -Passed $true -Expected "present" -Observed "present"

      if (Test-JsonProperty -Object $runtime -Name "ec2_start_allowed") {
        $entry.ec2_start_allowed = [bool]$runtime.ec2_start_allowed
      }
      if (Test-JsonProperty -Object $runtime -Name "generation_allowed") {
        $entry.generation_allowed = [bool]$runtime.generation_allowed
      }
      if (Test-JsonProperty -Object $runtime -Name "auth_gate") {
        $authGate = $runtime.auth_gate
        if (Test-JsonProperty -Object $authGate -Name "safe_to_start_ec2") {
          $entry.auth_safe_to_start_ec2 = [bool]$authGate.safe_to_start_ec2
        }
      }
      if (Test-JsonProperty -Object $runtime -Name "lane_readiness") {
        $laneReadiness = $runtime.lane_readiness
        if (Test-JsonProperty -Object $laneReadiness -Name "lane_id") {
          $entry.lane_readiness_lane_id = [string]$laneReadiness.lane_id
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "lane_match") {
          $entry.lane_readiness_lane_match = [bool]$laneReadiness.lane_match
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "ready_for_ec2_static_proof") {
          $entry.lane_ready_for_ec2_static_proof = [bool]$laneReadiness.ready_for_ec2_static_proof
        }
        if (Test-JsonProperty -Object $laneReadiness -Name "ready_for_generation") {
          $entry.lane_ready_for_generation = [bool]$laneReadiness.ready_for_generation
        }
      }
      if (Test-JsonProperty -Object $runtime -Name "runtime_unblock_handoff") {
        $runtimeHandoff = $runtime.runtime_unblock_handoff
        $checks += New-ContractCheck -Name "runtime_handoff_present" -Passed $true -Expected "present" -Observed "present"
        if (Test-JsonProperty -Object $runtimeHandoff -Name "result") {
          $entry.runtime_handoff_result = [string]$runtimeHandoff.result
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "lane_id") {
          $entry.runtime_handoff_lane_id = [string]$runtimeHandoff.lane_id
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "lane_match") {
          $entry.runtime_handoff_lane_match = [bool]$runtimeHandoff.lane_match
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "failure_category") {
          $entry.runtime_handoff_failure_category = [string]$runtimeHandoff.failure_category
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "next_required_action") {
          $entry.runtime_handoff_next_required_action = [string]$runtimeHandoff.next_required_action
        }
        foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "ec2_started", "generation_executed", "markdown_written")) {
          if (Test-JsonProperty -Object $runtimeHandoff -Name $name) {
            $entry["runtime_handoff_$name"] = [bool]$runtimeHandoff.$name
          }
        }
        if (Test-JsonProperty -Object $runtimeHandoff -Name "command_step_count") {
          $entry.runtime_handoff_command_step_count = [int]$runtimeHandoff.command_step_count
        }
      } else {
        $checks += New-ContractCheck -Name "runtime_handoff_present" -Passed $false -Expected "present" -Observed "missing"
      }
      if (Test-JsonProperty -Object $runtime -Name "runtime_lane_queue") {
        $runtimeLaneQueue = $runtime.runtime_lane_queue
        $checks += New-ContractCheck -Name "runtime_lane_queue_present" -Passed $true -Expected "present" -Observed "present"
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "result") {
          $entry.runtime_lane_queue_result = [string]$runtimeLaneQueue.result
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "selected_lane_in_queue") {
          $entry.runtime_lane_queue_selected_lane_in_queue = [bool]$runtimeLaneQueue.selected_lane_in_queue
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "selected_lane_order") {
          $entry.runtime_lane_queue_selected_lane_order = [int]$runtimeLaneQueue.selected_lane_order
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "first_runtime_lane_id") {
          $entry.runtime_lane_queue_first_runtime_lane_id = [string]$runtimeLaneQueue.first_runtime_lane_id
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "first_runtime_lane_match") {
          $entry.runtime_lane_queue_first_runtime_lane_match = [bool]$runtimeLaneQueue.first_runtime_lane_match
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "current_runtime_lane_id") {
          $entry.runtime_lane_queue_current_runtime_lane_id = [string]$runtimeLaneQueue.current_runtime_lane_id
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "current_runtime_lane_match") {
          $entry.runtime_lane_queue_current_runtime_lane_match = [bool]$runtimeLaneQueue.current_runtime_lane_match
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "failed_check_count") {
          $entry.runtime_lane_queue_failed_check_count = [int]$runtimeLaneQueue.failed_check_count
        }
        foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")) {
          if (Test-JsonProperty -Object $runtimeLaneQueue -Name $name) {
            $entry["runtime_lane_queue_$name"] = [bool]$runtimeLaneQueue.$name
          }
        }
        if (Test-JsonProperty -Object $runtimeLaneQueue -Name "queue_allows_selected_lane_ec2_static_proof") {
          $entry.runtime_lane_queue_allows_selected_lane_ec2_static_proof = [bool]$runtimeLaneQueue.queue_allows_selected_lane_ec2_static_proof
        }
      } else {
        $checks += New-ContractCheck -Name "runtime_lane_queue_present" -Passed $false -Expected "present" -Observed "missing"
      }
      if (Test-JsonProperty -Object $runtime -Name "model_registry_coverage") {
        $modelRegistryCoverage = $runtime.model_registry_coverage
        $checks += New-ContractCheck -Name "model_registry_coverage_present" -Passed $true -Expected "present" -Observed "present"
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "result") {
          $entry.model_registry_coverage_result = [string]$modelRegistryCoverage.result
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "selected_lane_covered") {
          $entry.model_registry_coverage_selected_lane_covered = [bool]$modelRegistryCoverage.selected_lane_covered
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "selected_lane_result") {
          $entry.model_registry_coverage_selected_lane_result = [string]$modelRegistryCoverage.selected_lane_result
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "failed_check_count") {
          $entry.model_registry_coverage_failed_check_count = [int]$modelRegistryCoverage.failed_check_count
        }
        foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")) {
          if (Test-JsonProperty -Object $modelRegistryCoverage -Name $name) {
            $entry["model_registry_coverage_$name"] = [bool]$modelRegistryCoverage.$name
          }
        }
        if (Test-JsonProperty -Object $modelRegistryCoverage -Name "coverage_allows_selected_lane_ec2_static_proof") {
          $entry.model_registry_coverage_allows_selected_lane_ec2_static_proof = [bool]$modelRegistryCoverage.coverage_allows_selected_lane_ec2_static_proof
        }
      } else {
        $checks += New-ContractCheck -Name "model_registry_coverage_present" -Passed $false -Expected "present" -Observed "missing"
      }
      if (Test-JsonProperty -Object $runtime -Name "coordinator_safety") {
        $coordinatorSafety = $runtime.coordinator_safety
        if (Test-JsonProperty -Object $coordinatorSafety -Name "blocked_execute_records_safe") {
          $entry.coordinator_blocked_execute_records_safe = [bool]$coordinatorSafety.blocked_execute_records_safe
        }
      }
    }

    $checks += New-ContractCheck -Name "runtime_handoff_result_recognized" `
      -Passed (@($recognizedHandoffResults) -contains $entry.runtime_handoff_result) `
      -Expected ($recognizedHandoffResults -join " | ") `
      -Observed ([string]$entry.runtime_handoff_result)
    $checks += New-ContractCheck -Name "lane_readiness_matches_snapshot_lane" `
      -Passed ($entry.lane_readiness_lane_match -eq $true -and [string]$entry.lane_readiness_lane_id -eq [string]$entry.lane_id) `
      -Expected ("lane_readiness.lane_match=true; lane_readiness.lane_id={0}" -f $entry.lane_id) `
      -Observed ("lane_readiness.lane_match={0}; lane_readiness.lane_id={1}" -f $entry.lane_readiness_lane_match, $entry.lane_readiness_lane_id)
    $checks += New-ContractCheck -Name "runtime_handoff_matches_snapshot_lane" `
      -Passed ($entry.runtime_handoff_lane_match -eq $true -and [string]$entry.runtime_handoff_lane_id -eq [string]$entry.lane_id) `
      -Expected ("runtime_handoff.lane_match=true; runtime_handoff.lane_id={0}" -f $entry.lane_id) `
      -Observed ("runtime_handoff.lane_match={0}; runtime_handoff.lane_id={1}" -f $entry.runtime_handoff_lane_match, $entry.runtime_handoff_lane_id)
    $checks += New-ContractCheck -Name "runtime_handoff_local_only" `
      -Passed ($entry.runtime_handoff_local_only -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_handoff_local_only)
    $checks += New-ContractCheck -Name "runtime_handoff_no_external_contacts" `
      -Passed ($entry.runtime_handoff_aws_contacted -eq $false -and $entry.runtime_handoff_github_api_contacted -eq $false -and $entry.runtime_handoff_civitai_contacted -eq $false) `
      -Expected "aws_contacted=false; github_api_contacted=false; civitai_contacted=false" `
      -Observed ("aws_contacted={0}; github_api_contacted={1}; civitai_contacted={2}" -f $entry.runtime_handoff_aws_contacted, $entry.runtime_handoff_github_api_contacted, $entry.runtime_handoff_civitai_contacted)
    $checks += New-ContractCheck -Name "runtime_handoff_no_ec2_or_generation" `
      -Passed ($entry.runtime_handoff_ec2_started -eq $false -and $entry.runtime_handoff_generation_executed -eq $false) `
      -Expected "ec2_started=false; generation_executed=false" `
      -Observed ("ec2_started={0}; generation_executed={1}" -f $entry.runtime_handoff_ec2_started, $entry.runtime_handoff_generation_executed)
    $checks += New-ContractCheck -Name "runtime_handoff_has_full_command_sequence" `
      -Passed ($entry.runtime_handoff_command_step_count -ge 8) `
      -Expected ">= 8" `
      -Observed ([string]$entry.runtime_handoff_command_step_count)
    $checks += New-ContractCheck -Name "runtime_handoff_markdown_written" `
      -Passed ($entry.runtime_handoff_markdown_written -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_handoff_markdown_written)
    $checks += New-ContractCheck -Name "runtime_lane_queue_result_passes" `
      -Passed ($entry.runtime_lane_queue_result -eq "pass_local_only") `
      -Expected "pass_local_only" `
      -Observed ([string]$entry.runtime_lane_queue_result)
    $checks += New-ContractCheck -Name "runtime_lane_queue_contains_snapshot_lane" `
      -Passed ($entry.runtime_lane_queue_selected_lane_in_queue -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_lane_queue_selected_lane_in_queue)
    $checks += New-ContractCheck -Name "runtime_lane_queue_current_lane_matches_snapshot_lane" `
      -Passed (($entry.top_level_result -eq "pass_runtime_smoke_qa_complete" -and $entry.runtime_lane_queue_selected_lane_in_queue -eq $true) -or ($entry.runtime_lane_queue_current_runtime_lane_match -eq $true -and [string]$entry.runtime_lane_queue_current_runtime_lane_id -eq [string]$entry.lane_id -and $entry.runtime_lane_queue_selected_lane_in_queue -eq $true)) `
      -Expected ("active lane: current_runtime_lane_id={0}; completed lane: selected_lane_in_queue=true" -f $entry.lane_id) `
      -Observed ("current_runtime_lane_id={0}; current_runtime_lane_match={1}; selected_lane_order={2}; selected_lane_in_queue={3}" -f $entry.runtime_lane_queue_current_runtime_lane_id, $entry.runtime_lane_queue_current_runtime_lane_match, $entry.runtime_lane_queue_selected_lane_order, $entry.runtime_lane_queue_selected_lane_in_queue)
    $checks += New-ContractCheck -Name "runtime_lane_queue_failed_check_count_zero" `
      -Passed ($entry.runtime_lane_queue_failed_check_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.runtime_lane_queue_failed_check_count)
    $checks += New-ContractCheck -Name "runtime_lane_queue_local_only" `
      -Passed ($entry.runtime_lane_queue_local_only -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.runtime_lane_queue_local_only)
    $checks += New-ContractCheck -Name "runtime_lane_queue_no_external_contacts" `
      -Passed ($entry.runtime_lane_queue_aws_contacted -eq $false -and $entry.runtime_lane_queue_github_api_contacted -eq $false -and $entry.runtime_lane_queue_civitai_contacted -eq $false -and $entry.runtime_lane_queue_comfyui_contacted -eq $false) `
      -Expected "aws_contacted=false; github_api_contacted=false; civitai_contacted=false; comfyui_contacted=false" `
      -Observed ("aws_contacted={0}; github_api_contacted={1}; civitai_contacted={2}; comfyui_contacted={3}" -f $entry.runtime_lane_queue_aws_contacted, $entry.runtime_lane_queue_github_api_contacted, $entry.runtime_lane_queue_civitai_contacted, $entry.runtime_lane_queue_comfyui_contacted)
    $checks += New-ContractCheck -Name "runtime_lane_queue_no_ec2_or_generation" `
      -Passed ($entry.runtime_lane_queue_ec2_started -eq $false -and $entry.runtime_lane_queue_generation_executed -eq $false) `
      -Expected "ec2_started=false; generation_executed=false" `
      -Observed ("ec2_started={0}; generation_executed={1}" -f $entry.runtime_lane_queue_ec2_started, $entry.runtime_lane_queue_generation_executed)
    $checks += New-ContractCheck -Name "runtime_lane_queue_allows_snapshot_lane" `
      -Passed (($entry.top_level_result -eq "pass_runtime_smoke_qa_complete" -and $entry.runtime_lane_queue_selected_lane_in_queue -eq $true) -or $entry.runtime_lane_queue_allows_selected_lane_ec2_static_proof -eq $true) `
      -Expected "active lane allows EC2 static proof, or completed lane remains queued without needing EC2" `
      -Observed ([string]$entry.runtime_lane_queue_allows_selected_lane_ec2_static_proof)
    $checks += New-ContractCheck -Name "model_registry_coverage_result_passes" `
      -Passed ($entry.model_registry_coverage_result -eq "pass_local_only") `
      -Expected "pass_local_only" `
      -Observed ([string]$entry.model_registry_coverage_result)
    $checks += New-ContractCheck -Name "model_registry_coverage_contains_snapshot_lane" `
      -Passed ($entry.model_registry_coverage_selected_lane_covered -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.model_registry_coverage_selected_lane_covered)
    $checks += New-ContractCheck -Name "model_registry_coverage_snapshot_lane_passes" `
      -Passed ($entry.model_registry_coverage_selected_lane_result -eq "pass") `
      -Expected "pass" `
      -Observed ([string]$entry.model_registry_coverage_selected_lane_result)
    $checks += New-ContractCheck -Name "model_registry_coverage_failed_check_count_zero" `
      -Passed ($entry.model_registry_coverage_failed_check_count -eq 0) `
      -Expected "0" `
      -Observed ([string]$entry.model_registry_coverage_failed_check_count)
    $checks += New-ContractCheck -Name "model_registry_coverage_local_only" `
      -Passed ($entry.model_registry_coverage_local_only -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.model_registry_coverage_local_only)
    $checks += New-ContractCheck -Name "model_registry_coverage_no_external_contacts" `
      -Passed ($entry.model_registry_coverage_aws_contacted -eq $false -and $entry.model_registry_coverage_github_api_contacted -eq $false -and $entry.model_registry_coverage_civitai_contacted -eq $false -and $entry.model_registry_coverage_comfyui_contacted -eq $false) `
      -Expected "aws_contacted=false; github_api_contacted=false; civitai_contacted=false; comfyui_contacted=false" `
      -Observed ("aws_contacted={0}; github_api_contacted={1}; civitai_contacted={2}; comfyui_contacted={3}" -f $entry.model_registry_coverage_aws_contacted, $entry.model_registry_coverage_github_api_contacted, $entry.model_registry_coverage_civitai_contacted, $entry.model_registry_coverage_comfyui_contacted)
    $checks += New-ContractCheck -Name "model_registry_coverage_no_ec2_or_generation" `
      -Passed ($entry.model_registry_coverage_ec2_started -eq $false -and $entry.model_registry_coverage_generation_executed -eq $false) `
      -Expected "ec2_started=false; generation_executed=false" `
      -Observed ("ec2_started={0}; generation_executed={1}" -f $entry.model_registry_coverage_ec2_started, $entry.model_registry_coverage_generation_executed)
    $checks += New-ContractCheck -Name "model_registry_coverage_allows_snapshot_lane" `
      -Passed ($entry.model_registry_coverage_allows_selected_lane_ec2_static_proof -eq $true) `
      -Expected "true" `
      -Observed ([string]$entry.model_registry_coverage_allows_selected_lane_ec2_static_proof)

    switch ($entry.top_level_result) {
      "pass_local_ready_runtime_blocked_auth" {
        $checks += New-ContractCheck -Name "blocked_auth_has_failure_category" `
          -Passed (![string]::IsNullOrWhiteSpace([string]$entry.failure_category)) `
          -Expected "non-empty" `
          -Observed ([string]$entry.failure_category)
        $checks += New-ContractCheck -Name "blocked_auth_disallows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false -and $entry.auth_safe_to_start_ec2 -eq $false) `
          -Expected "ec2_start_allowed=false; auth.safe_to_start_ec2=false" `
          -Observed ("ec2_start_allowed={0}; auth.safe_to_start_ec2={1}" -f $entry.ec2_start_allowed, $entry.auth_safe_to_start_ec2)
        $checks += New-ContractCheck -Name "blocked_auth_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "blocked_auth_coordinator_records_safe" `
          -Passed ($entry.coordinator_blocked_execute_records_safe -eq $true) `
          -Expected "true" `
          -Observed ([string]$entry.coordinator_blocked_execute_records_safe)
        $checks += New-ContractCheck -Name "blocked_auth_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -eq "handoff_ready_runtime_blocked_auth" -and $entry.runtime_handoff_next_required_action -eq "complete_aws_browser_sso_login") `
          -Expected "handoff_ready_runtime_blocked_auth; complete_aws_browser_sso_login" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
      "pass_local_ready_runtime_blocked" {
        $checks += New-ContractCheck -Name "runtime_blocked_has_failure_category" `
          -Passed (![string]::IsNullOrWhiteSpace([string]$entry.failure_category)) `
          -Expected "non-empty" `
          -Observed ([string]$entry.failure_category)
        $checks += New-ContractCheck -Name "runtime_blocked_disallows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "runtime_blocked_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "runtime_blocked_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -in @("handoff_auth_ready_lane_not_ready", "handoff_lane_queue_order_blocked", "handoff_model_registry_blocked")) `
          -Expected "handoff_auth_ready_lane_not_ready | handoff_lane_queue_order_blocked | handoff_model_registry_blocked" `
          -Observed ([string]$entry.runtime_handoff_result)
      }
      "pass_local_ready_for_ec2_static_proof" {
        $checks += New-ContractCheck -Name "static_proof_ready_allows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $true -and $entry.lane_ready_for_ec2_static_proof -eq $true) `
          -Expected "ec2_start_allowed=true; lane.ready_for_ec2_static_proof=true" `
          -Observed ("ec2_start_allowed={0}; lane.ready_for_ec2_static_proof={1}" -f $entry.ec2_start_allowed, $entry.lane_ready_for_ec2_static_proof)
        $checks += New-ContractCheck -Name "static_proof_ready_disallows_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "static_proof_ready_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -eq "handoff_ready_for_ec2_static_proof" -and $entry.runtime_handoff_next_required_action -eq "run_ec2_static_proof") `
          -Expected "handoff_ready_for_ec2_static_proof; run_ec2_static_proof" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
      "pass_ready_for_generation" {
        $checks += New-ContractCheck -Name "generation_ready_allows_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $true) `
          -Expected "true" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "generation_ready_allows_generation" `
          -Passed ($entry.generation_allowed -eq $true -and $entry.lane_ready_for_generation -eq $true) `
          -Expected "generation_allowed=true; lane.ready_for_generation=true" `
          -Observed ("generation_allowed={0}; lane.ready_for_generation={1}" -f $entry.generation_allowed, $entry.lane_ready_for_generation)
        $checks += New-ContractCheck -Name "generation_ready_runtime_handoff_matches_gate" `
          -Passed ($entry.runtime_handoff_result -eq "handoff_ready_for_generation" -and $entry.runtime_handoff_next_required_action -eq "run_bounded_workflow_smoke") `
          -Expected "handoff_ready_for_generation; run_bounded_workflow_smoke" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
      "pass_runtime_smoke_qa_complete" {
        $checks += New-ContractCheck -Name "completed_smoke_disallows_additional_ec2_start" `
          -Passed ($entry.ec2_start_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.ec2_start_allowed)
        $checks += New-ContractCheck -Name "completed_smoke_disallows_additional_generation" `
          -Passed ($entry.generation_allowed -eq $false) `
          -Expected "false" `
          -Observed ([string]$entry.generation_allowed)
        $checks += New-ContractCheck -Name "completed_smoke_runtime_handoff_matches_gate" `
          -Passed (($entry.runtime_handoff_result -eq "handoff_runtime_smoke_qa_complete" -and $entry.runtime_handoff_next_required_action -eq "checkpoint_runtime_smoke_evidence_and_advance_next_goal") -or ($entry.runtime_handoff_local_only -eq $true -and $entry.runtime_handoff_ec2_started -eq $false -and $entry.runtime_handoff_generation_executed -eq $false)) `
          -Expected "preferred: handoff_runtime_smoke_qa_complete; allowed for previously completed lanes: stale local-only handoff with no EC2/generation" `
          -Observed ("{0}; {1}" -f $entry.runtime_handoff_result, $entry.runtime_handoff_next_required_action)
      }
    }

    $failedChecks = @($checks | Where-Object { $_.result -ne "pass" })
    $entry.contract_checks = $checks
    $entry.contract_check_failures = @($failedChecks).Count
    $entry.result = $(if ($entry.contract_check_failures -eq 0) { "pass" } else { "fail" })
  } catch {
    $entry.error = $_.Exception.Message
    $entry.contract_checks = $checks
    $entry.contract_check_failures = $(if (@($checks).Count -eq 0) { 1 } else { @($checks | Where-Object { $_.result -ne "pass" }).Count })
    $entry.result = "fail"
  }

  return $entry
}

function New-SamplePng {
  param([Parameter(Mandatory=$true)][string]$Path)

  Add-Type -AssemblyName System.Drawing
  $bitmap = New-Object System.Drawing.Bitmap 64, 64
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.Clear([System.Drawing.Color]::FromArgb(32, 96, 160))
    $bitmap.SetPixel(0, 0, [System.Drawing.Color]::White)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$qaRoot = Join-Path $ProjectRoot "Plan\Instructions\QA"
$scriptsRoot = Join-Path $qaRoot "Scripts"
$schemasRoot = Join-Path $qaRoot "Schemas"
$templatesRoot = Join-Path $qaRoot "Templates"
$baseGenerationRoot = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation"
$tempRoot = Join-Path $env:TEMP "comfy_ui_qa_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\QA_Helper_Static_Validation\W61_QA_HELPER_CURRENT_VALIDATION_$stamp.json"
}

$scriptParseResults = @()
foreach ($script in Get-ChildItem -LiteralPath $scriptsRoot -Filter "*.ps1" -File | Sort-Object Name) {
  $scriptParseResults += Test-PowerShellParser -Path $script.FullName
}

$jsonParseResults = @()
foreach ($json in @(
  @(Get-ChildItem -LiteralPath $schemasRoot -Filter "*.json" -File | Sort-Object Name),
  @(Get-ChildItem -LiteralPath $templatesRoot -Filter "*.json" -File | Sort-Object Name)
)) {
  foreach ($file in @($json)) {
    if ($null -ne $file) {
      $jsonParseResults += Test-JsonFile -Path $file.FullName
    }
  }
}

$markdownTemplateResults = @()
foreach ($template in Get-ChildItem -LiteralPath $templatesRoot -Filter "*.md" -File | Sort-Object Name) {
  $markdownTemplateResults += Test-MarkdownTemplate -Path $template.FullName
}

$authoredLaneDirs = @()
if (Test-Path -LiteralPath $baseGenerationRoot) {
  foreach ($dir in Get-ChildItem -LiteralPath $baseGenerationRoot -Directory | Sort-Object Name) {
    $requiredLaneFiles = @(
      "workflow.api.json",
      "patch_points.json",
      "runtime_requirements.json",
      "smoke_test_request.json"
    )
    $hasRequiredFiles = $true
    foreach ($fileName in $requiredLaneFiles) {
      if (!(Test-Path -LiteralPath (Join-Path $dir.FullName $fileName))) {
        $hasRequiredFiles = $false
        break
      }
    }
    if ($hasRequiredFiles) {
      $authoredLaneDirs += $dir
    }
  }
}

$localSmokeResults = @()
$qaRecordFile = Join-Path $tempRoot "sample_qa_record.json"
$localSmokeResults += Invoke-LocalHelper -Name "initialize_qa_record_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Initialize-QARecord.ps1") `
  -Arguments @("-ArtifactId", "sample-artifact", "-ArtifactType", "static_validation_sample", "-OutFile", $qaRecordFile) `
  -ExpectedOutputFile $qaRecordFile `
  -ExpectedOutputType "json"

$doneCertFile = Join-Path $tempRoot "sample_done_certification.md"
$localSmokeResults += Invoke-LocalHelper -Name "done_certification_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-DoneCertification.ps1") `
  -Arguments @("-TaskId", "TRK-W61-SAMPLE", "-Title", "Static validation sample", "-OutFile", $doneCertFile) `
  -ExpectedOutputFile $doneCertFile `
  -ExpectedOutputType "markdown"

$imageDryRunFile = Join-Path $tempRoot "image_qa_dry_run.json"
$imageDryRunChecklist = Join-Path $tempRoot "image_qa_dry_run_checklist.md"
$localSmokeResults += Invoke-LocalHelper -Name "image_artifact_qa_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-ImageArtifactQARecord.ps1") `
  -Arguments @("-DryRun", "-OutFile", $imageDryRunFile, "-ChecklistOutFile", $imageDryRunChecklist) `
  -ExpectedOutputFile $imageDryRunFile `
  -ExpectedOutputType "json"

$sampleImage = Join-Path $tempRoot "sample_image.png"
New-SamplePng -Path $sampleImage
$imageTechnicalFile = Join-Path $tempRoot "image_qa_technical.json"
$imageTechnicalChecklist = Join-Path $tempRoot "image_qa_technical_checklist.md"
$localSmokeResults += Invoke-LocalHelper -Name "image_artifact_qa_technical_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ImageArtifactQARecord.ps1") `
  -Arguments @("-ImagePath", $sampleImage, "-ArtifactId", "static_validation_sample_image", "-OutFile", $imageTechnicalFile, "-ChecklistOutFile", $imageTechnicalChecklist, "-MinimumWidth", "1", "-MinimumHeight", "1") `
  -ExpectedOutputFile $imageTechnicalFile `
  -ExpectedOutputType "json"

foreach ($laneDir in @($authoredLaneDirs)) {
  $workflowStaticFile = Join-Path $tempRoot ("workflow_static_validation_{0}.json" -f $laneDir.Name)
  $localSmokeResults += Invoke-LocalHelper -Name ("workflow_static_validation_smoke_{0}" -f $laneDir.Name) `
    -ScriptPath (Join-Path $scriptsRoot "Test-ComfyWorkflowStatic.ps1") `
    -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneDir", $laneDir.FullName, "-OutFile", $workflowStaticFile) `
    -ExpectedOutputFile $workflowStaticFile `
    -ExpectedOutputType "json"

  $laneReadinessFile = Join-Path $tempRoot ("lane_runtime_readiness_{0}.json" -f $laneDir.Name)
  $localSmokeResults += Invoke-LocalHelper -Name ("lane_runtime_readiness_smoke_{0}" -f $laneDir.Name) `
    -ScriptPath (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1") `
    -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneId", $laneDir.Name, "-OutFile", $laneReadinessFile) `
    -ExpectedOutputFile $laneReadinessFile `
    -ExpectedOutputType "json"
}

$authoredLaneEvidenceCoverageFile = Join-Path $tempRoot "authored_lane_evidence_coverage.json"
$localSmokeResults += Invoke-LocalHelper -Name "authored_lane_evidence_coverage_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-AuthoredLaneEvidenceCoverage.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $authoredLaneEvidenceCoverageFile) `
  -ExpectedOutputFile $authoredLaneEvidenceCoverageFile `
  -ExpectedOutputType "json"

$runtimeLaneQueueFile = Join-Path $tempRoot "runtime_lane_queue_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "runtime_lane_queue_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-RuntimeLaneQueue.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-CoverageFile", $authoredLaneEvidenceCoverageFile, "-OutFile", $runtimeLaneQueueFile) `
  -ExpectedOutputFile $runtimeLaneQueueFile `
  -ExpectedOutputType "json"

$projectReadinessLaneId = "sdxl_low_risk_fallback_lane"
try {
  if (Test-Path -LiteralPath $runtimeLaneQueueFile) {
    $runtimeQueueJson = Get-Content -LiteralPath $runtimeLaneQueueFile -Raw | ConvertFrom-Json
    if ((Test-JsonProperty -Object $runtimeQueueJson -Name "current_runtime_lane_id") -and
      ![string]::IsNullOrWhiteSpace([string]$runtimeQueueJson.current_runtime_lane_id)) {
      $projectReadinessLaneId = [string]$runtimeQueueJson.current_runtime_lane_id
    } elseif ((Test-JsonProperty -Object $runtimeQueueJson -Name "first_runtime_lane_id") -and
      ![string]::IsNullOrWhiteSpace([string]$runtimeQueueJson.first_runtime_lane_id)) {
      $projectReadinessLaneId = [string]$runtimeQueueJson.first_runtime_lane_id
    }
  }
} catch {
  $projectReadinessLaneId = "sdxl_low_risk_fallback_lane"
}

$modelRegistryCoverageFile = Join-Path $tempRoot "workflow_model_registry_coverage.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_model_registry_coverage_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-WorkflowModelRegistryCoverage.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $modelRegistryCoverageFile) `
  -ExpectedOutputFile $modelRegistryCoverageFile `
  -ExpectedOutputType "json"

$imageEngineRouterFile = Join-Path $tempRoot "image_engine_router_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "image_engine_router_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ImageEngineRouter.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $imageEngineRouterFile) `
  -ExpectedOutputFile $imageEngineRouterFile `
  -ExpectedOutputType "json"

$workflowRunPackageRouterGateFile = Join-Path $tempRoot "workflow_run_package_router_gate.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_run_package_router_gate_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-WorkflowRunPackageRouterGate.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $workflowRunPackageRouterGateFile) `
  -ExpectedOutputFile $workflowRunPackageRouterGateFile `
  -ExpectedOutputType "json"

$workflowRunPackageMatrixFile = Join-Path $tempRoot "workflow_run_package_matrix.json"
$localSmokeResults += Invoke-LocalHelper -Name "workflow_run_package_matrix_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-WorkflowRunPackageMatrix.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $workflowRunPackageMatrixFile) `
  -ExpectedOutputFile $workflowRunPackageMatrixFile `
  -ExpectedOutputType "json"

$ec2DeployBundleMatrixFile = Join-Path $tempRoot "ec2_deploy_bundle_matrix.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_deploy_bundle_matrix_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-EC2DeployBundleMatrix.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $ec2DeployBundleMatrixFile) `
  -ExpectedOutputFile $ec2DeployBundleMatrixFile `
  -ExpectedOutputType "json"

$ec2WorkflowMatrixQualityRunPlanFile = Join-Path $tempRoot "ec2_workflow_matrix_quality_run_plan.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_matrix_quality_run_plan_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-EC2WorkflowMatrixQualityRunPlan.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $ec2WorkflowMatrixQualityRunPlanFile) `
  -ExpectedOutputFile $ec2WorkflowMatrixQualityRunPlanFile `
  -ExpectedOutputType "json"

$itemsTrackerValidationFile = Join-Path $tempRoot "items_tracker_package_validation.json"
$localSmokeResults += Invoke-LocalHelper -Name "items_tracker_package_validation_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ItemsTrackerPackageStatic.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $itemsTrackerValidationFile) `
  -ExpectedOutputFile $itemsTrackerValidationFile `
  -ExpectedOutputType "json"

$projectReadinessFile = Join-Path $tempRoot "project_readiness_snapshot.json"
$localSmokeResults += Invoke-LocalHelper -Name "project_readiness_snapshot_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "Test-ProjectReadinessSnapshot.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-LaneId", $projectReadinessLaneId, "-OutFile", $projectReadinessFile) `
  -ExpectedOutputFile $projectReadinessFile `
  -ExpectedOutputType "json"

$projectReadinessContract = Test-ProjectReadinessSnapshotContract -Path $projectReadinessFile

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$jsonFailures = @($jsonParseResults | Where-Object { $_.result -ne "pass" })
$markdownFailures = @($markdownTemplateResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($localSmokeResults | Where-Object { $_.result -ne "pass" -or ($_.expected_output_type -ne "none" -and -not $_.expected_output_valid) })
$contractFailures = @()
if ($projectReadinessContract.result -ne "pass") {
  $contractFailures += $projectReadinessContract
}

$qaHelperKnownIssues = @(
  "Live image/video/audio artifact QA remains pending for actual generated artifacts.",
  "The sample image technical smoke does not count as generated artifact visual review.",
  "The project readiness snapshot is local-only and does not refresh AWS browser/SSO auth.",
  "ComfyUI runtime execution, model loading, EC2 static proof, artifact pullback, and final visual QA remain separate runtime validations."
)
$qaHelperNextAction = "After AWS browser login refresh, run EC2 static proof, bounded smoke generation, artifact pullback, and real image QA."
if ($projectReadinessContract.top_level_result -eq "pass_runtime_smoke_qa_complete") {
  $qaHelperKnownIssues = @(
    "Selected lane runtime smoke, pullback hash verification, technical QA, and visual QA are complete.",
    "The QA helper is a local-only regression check and does not perform a new live GPU run.",
    "Completed lane proof is not final portfolio, video, audio, or full-project certification."
  )
  $qaHelperNextAction = "Checkpoint completed runtime-smoke evidence and advance to the next lane, module, or deeper QA target without rerunning EC2 for this same proof."
}

$record = [ordered]@{
  evidence_id = "EVID-W61-QA-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-011"
  artifact_type = "qa_helper_current_static_validation"
  tracker_ids = @("TRK-W61-011", "TRK-W61-002", "TRK-W61-006")
  item_ids = @("ITEM-W61-011", "ITEM-W61-002", "ITEM-W61-006")
  qa_protocol_used = @(
    "README_QA_WAVE61.md",
    "STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md",
    "IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md",
    "COMFYUI_WORKFLOW_TESTING_PROTOCOL.md",
    "DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/QA/Scripts/*.ps1",
    "Plan/Instructions/QA/Schemas/*.json",
    "Plan/Instructions/QA/Templates/*.json",
    "Plan/Instructions/QA/Templates/*.md",
    "all authored base-generation workflow static validation smokes",
    "all authored base-generation lane runtime readiness smokes",
    "all authored base-generation local pre-EC2 evidence coverage smoke",
    "runtime lane queue validation smoke",
    "image artifact QA dry-run and technical sample smoke",
    "Items/Tracker package validator smoke",
    "project readiness snapshot smoke",
    "project readiness snapshot contract checks"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    json_file_count = @($jsonParseResults).Count
    json_parse_failures = @($jsonFailures).Count
    json_parse_results = $jsonParseResults
    markdown_template_count = @($markdownTemplateResults).Count
    markdown_template_failures = @($markdownFailures).Count
    markdown_template_results = $markdownTemplateResults
    authored_base_generation_lane_count = @($authoredLaneDirs).Count
    authored_base_generation_lanes = @($authoredLaneDirs | ForEach-Object { $_.Name })
    local_smoke_count = @($localSmokeResults).Count
    local_smoke_failures = @($smokeFailures).Count
    local_smoke_results = $localSmokeResults
    project_readiness_contract_failures = @($contractFailures).Count
    project_readiness_contract = $projectReadinessContract
  }
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $jsonFailures.Count -eq 0 -and $markdownFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $contractFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = $qaHelperKnownIssues
  next_action = $qaHelperNextAction
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote QA helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
