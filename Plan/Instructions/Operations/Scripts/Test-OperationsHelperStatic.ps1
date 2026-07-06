<#
.SYNOPSIS
Validates current Wave 60 operations helpers with local-only checks.

.DESCRIPTION
Parses every Operations/Scripts PowerShell helper, parses Operations JSON
schemas/templates, runs local-only smoke checks into a temp directory, and writes
a machine-readable evidence record. It does not contact AWS, Civitai, GitHub, or
start EC2.
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
    $tempRootProjectRelative = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $tempRootFull
    if (![string]::IsNullOrWhiteSpace($tempRootProjectRelative)) {
      $replacements += [ordered]@{ From = $tempRootProjectRelative; To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootProjectRelative.Replace("/", "\"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootProjectRelative.Replace("\", "/"); To = "[VALIDATION_TEMP_ROOT]" }
      $replacements += [ordered]@{ From = $tempRootProjectRelative.Replace("\", "\\"); To = "[VALIDATION_TEMP_ROOT]" }
    }
  }
  if (![string]::IsNullOrWhiteSpace($env:TEMP)) {
    $tempFull = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd("\", "/")
    $replacements += [ordered]@{ From = $tempFull; To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "/"); To = "[TEMP]" }
    $replacements += [ordered]@{ From = $tempFull.Replace("\", "\\"); To = "[TEMP]" }
    $tempProjectRelative = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $tempFull
    if (![string]::IsNullOrWhiteSpace($tempProjectRelative)) {
      $replacements += [ordered]@{ From = $tempProjectRelative; To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempProjectRelative.Replace("/", "\"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempProjectRelative.Replace("\", "/"); To = "[TEMP]" }
      $replacements += [ordered]@{ From = $tempProjectRelative.Replace("\", "\\"); To = "[TEMP]" }
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

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne ($Object.PSObject.Properties[$Name])
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

function Invoke-LocalHelper {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [string[]]$Arguments = @(),
    [string]$ExpectedOutputFile = ""
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
    expected_output_file_exists = (![string]::IsNullOrWhiteSpace($ExpectedOutputFile) -and (Test-Path -LiteralPath $ExpectedOutputFile))
    expected_output_json_valid = $false
    expected_output_error = $null
    top_level_result = $null
    top_level_failure_category = $null
    execute_gates_pass = $null
    generation_executed = $null
    ec2_started = $null
  }
  if ($entry.expected_output_file_exists) {
    try {
      $payload = Get-Content -LiteralPath $ExpectedOutputFile -Raw | ConvertFrom-Json
      $entry.expected_output_json_valid = $true
      if (Has-Property -Object $payload -Name "result") {
        $entry.top_level_result = [string]$payload.result
      }
      if (Has-Property -Object $payload -Name "failure_category") {
        $entry.top_level_failure_category = $payload.failure_category
      }
      if (Has-Property -Object $payload -Name "execute_gates_pass") {
        $entry.execute_gates_pass = [bool]$payload.execute_gates_pass
      }
      if (Has-Property -Object $payload -Name "generation_executed") {
        $entry.generation_executed = [bool]$payload.generation_executed
      }
      if (Has-Property -Object $payload -Name "ec2_started") {
        $entry.ec2_started = [bool]$payload.ec2_started
      }
      if ($Name -in @("ec2_lane_static_proof_dry_run", "ec2_workflow_smoke_run_dry_run", "ec2_workflow_smoke_run_package_dry_run")) {
        foreach ($required in @("result", "failure_category", "local_git_checkpoint_gate", "execute_gates_pass", "blocked_reasons")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        foreach ($requiredGit in @("head", "origin_main", "expected_remote_head", "local_matches_origin", "clean", "result")) {
          if (-not (Has-Property -Object $payload.local_git_checkpoint_gate -Name $requiredGit)) {
            throw "$Name local_git_checkpoint_gate is missing: $requiredGit"
          }
        }
        if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
          throw "$Name output has an empty top-level result."
        }
        if (-not [bool]$payload.execute_gates_pass -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
          throw "$Name blocked output must include a top-level failure_category."
        }
      }
      if ($Name -eq "ec2_workflow_smoke_run_package_dry_run") {
        foreach ($required in @("run_package", "request_source", "smoke_request")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing package field: $required"
          }
        }
        if ([string]$payload.request_source -ne "run_package") {
          throw "$Name request_source must be run_package."
        }
        if (-not [bool]$payload.run_package.valid) {
          throw "$Name run_package.valid must be true."
        }
        if ([string]$payload.smoke_request.source -ne "run_package") {
          throw "$Name smoke_request.source must be run_package."
        }
        if ([string]::IsNullOrWhiteSpace([string]$payload.run_package.prompt_profile.profile_id)) {
          throw "$Name run package prompt profile id is missing."
        }
      }
      if ($Name -eq "runtime_unblock_handoff_smoke") {
        foreach ($required in @("result", "failure_category", "next_required_action", "local_only", "aws_contacted", "ec2_started", "generation_executed", "safety_invariants", "command_sequence", "markdown_written", "gate_summary")) {
          if (-not (Has-Property -Object $payload -Name $required)) {
            throw "$Name output is missing top-level field: $required"
          }
        }
        if (-not [bool]$payload.local_only) {
          throw "$Name must be local_only=true."
        }
        if ([bool]$payload.aws_contacted) {
          throw "$Name must not contact AWS."
        }
        if ([bool]$payload.ec2_started) {
          throw "$Name must not start EC2."
        }
        if ([bool]$payload.generation_executed) {
          throw "$Name must not execute generation."
        }
        if (-not (Has-Property -Object $payload.gate_summary -Name "run_package")) {
          throw "$Name gate_summary is missing run_package."
        }
        if (-not (Has-Property -Object $payload.gate_summary -Name "model_registry_coverage")) {
          throw "$Name gate_summary is missing model_registry_coverage."
        }
        if (-not [bool]$payload.gate_summary.model_registry_coverage.coverage_allows_selected_lane_ec2_static_proof) {
          throw "$Name model registry coverage gate must allow selected lane EC2 static proof."
        }
        if ([bool]$payload.gate_summary.run_package.supplied) {
          if (-not [bool]$payload.gate_summary.run_package.valid) {
            throw "$Name supplied run package must be valid."
          }
          $boundedStep = @($payload.command_sequence | Where-Object { [string]$_.name -eq "bounded_workflow_smoke" } | Select-Object -First 1)
          if ($boundedStep.Count -eq 0 -or [string]$boundedStep[0].command -notmatch "-RunPackageManifestFile") {
            throw "$Name bounded_workflow_smoke command must include -RunPackageManifestFile when a run package is supplied."
          }
        }
        $modelRegistryStep = @($payload.command_sequence | Where-Object { [string]$_.name -eq "model_registry_coverage_recheck" } | Select-Object -First 1)
        if ($modelRegistryStep.Count -eq 0 -or [string]$modelRegistryStep[0].command -notmatch "Test-WorkflowModelRegistryCoverage.ps1") {
          throw "$Name command_sequence must include model_registry_coverage_recheck."
        }
        if (-not [bool]$payload.markdown_written) {
          throw "$Name did not write its Markdown handoff."
        }
        if (@($payload.command_sequence).Count -lt 8) {
          throw "$Name command_sequence is missing expected post-auth steps."
        }
        foreach ($requiredSafety in @("approved_instance_id", "expected_aws_account", "do_not_start_ec2_unless_auth_safe", "do_not_start_ec2_unless_runtime_lane_queue_allows", "do_not_start_ec2_unless_git_checkpoint_clean", "do_not_start_ec2_unless_lane_ready", "stop_ec2_after_runtime_work")) {
          if (-not (Has-Property -Object $payload.safety_invariants -Name $requiredSafety)) {
            throw "$Name safety_invariants is missing: $requiredSafety"
          }
        }
        if (-not (Has-Property -Object $payload.safety_invariants -Name "do_not_start_ec2_unless_model_registry_coverage_passes")) {
          throw "$Name safety_invariants is missing model registry coverage gate."
        }
        if ([string]$payload.result -like "*blocked*" -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
          throw "$Name blocked result must include failure_category."
        }
      }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  }
  return $entry
}

function Invoke-PullbackManifestVerificationSmoke {
  param(
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [Parameter(Mandatory=$true)][string]$TempRoot
  )

  $pullbackRoot = Join-Path $TempRoot "pullback_verified"
  $imageDir = Join-Path $pullbackRoot "images"
  $null = New-Item -ItemType Directory -Force -Path $imageDir

  $imagePath = Join-Path $imageDir "sample.png"
  [System.IO.File]::WriteAllBytes($imagePath, [byte[]](137,80,78,71,13,10,26,10,0,0,0,0))
  $hash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
  $bytes = (Get-Item -LiteralPath $imagePath).Length

  $manifestPath = Join-Path $pullbackRoot "REMOTE_ARTIFACT_MANIFEST.json"
  $manifest = [ordered]@{
    run_id = "static_validation_pullback"
    files = @(
      [ordered]@{
        relative_path = "images/sample.png"
        size_bytes = [int64]$bytes
        sha256 = $hash
        artifact_type = "image"
        qa_required = $true
      }
    )
  }
  $manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

  $outFile = Join-Path $pullbackRoot "PULLBACK_RECORD.json"
  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath `
    -ProjectRoot $ProjectRoot `
    -RunId "static_validation_pullback" `
    -LocalDestination $pullbackRoot `
    -RemoteManifestFile $manifestPath `
    -OutFile $outFile 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $text = ConvertTo-RedactedEvidenceText -Text $text -TempRoot $script:ValidationTempRoot

  $entry = [ordered]@{
    name = "ec2_pullback_manifest_verification_smoke"
    script = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ScriptPath
    exit_code = $LASTEXITCODE
    result = $(if ($LASTEXITCODE -eq 0) { "pass" } else { "fail" })
    output_tail = $(if ($text.Length -gt 1000) { $text.Substring($text.Length - 1000) } else { $text })
    expected_output_file = ConvertTo-EvidencePath -BasePath $ProjectRoot -TargetPath $outFile -TempRoot $script:ValidationTempRoot
    expected_output_file_exists = (Test-Path -LiteralPath $outFile)
    expected_output_json_valid = $false
    expected_output_error = $null
    status = $null
    hashes_verified = $false
    file_count_remote = $null
    file_count_local = $null
    qa_required_count = 0
    manifest_counted_as_artifact = $false
  }

  if ($entry.expected_output_file_exists) {
    try {
      $record = Get-Content -LiteralPath $outFile -Raw | ConvertFrom-Json
      $entry.expected_output_json_valid = $true
      $entry.status = [string]$record.status
      $entry.hashes_verified = [bool]$record.hashes_verified
      $entry.file_count_remote = $record.file_count_remote
      $entry.file_count_local = $record.file_count_local
      $entry.qa_required_count = @($record.qa_required_files).Count
      $entry.manifest_counted_as_artifact = (@($record.files | Where-Object { [string]$_.relative_path -eq "REMOTE_ARTIFACT_MANIFEST.json" }).Count -gt 0)

      if (-not $entry.hashes_verified) { $entry.result = "fail"; $entry.expected_output_error = "hashes_verified was false." }
      if ([string]$entry.status -ne "pullback_hashes_verified") { $entry.result = "fail"; $entry.expected_output_error = "Unexpected status: $($entry.status)" }
      if ([int]$entry.file_count_remote -ne 1 -or [int]$entry.file_count_local -ne 1) { $entry.result = "fail"; $entry.expected_output_error = "Unexpected file counts remote=$($entry.file_count_remote) local=$($entry.file_count_local)" }
      if ([int]$entry.qa_required_count -ne 1) { $entry.result = "fail"; $entry.expected_output_error = "Unexpected QA required count: $($entry.qa_required_count)" }
      if ($entry.manifest_counted_as_artifact) { $entry.result = "fail"; $entry.expected_output_error = "Remote manifest was counted as a pulled artifact." }
    } catch {
      $entry.expected_output_error = $_.Exception.Message
      $entry.result = "fail"
    }
  } else {
    $entry.result = "fail"
    $entry.expected_output_error = "Expected pullback record was not created."
  }

  return $entry
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $file = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

function Test-AuthGateEvidenceContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
    top_level_result = $null
    top_level_failure_category = $null
    top_level_account_match = $null
    top_level_remote_login_status = $null
  }

  try {
    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($required in @("result", "failure_category", "account_match", "remote_login_status", "ec2_work_allowed", "safe_to_start_ec2")) {
      if (-not (Has-Property -Object $payload -Name $required)) {
        throw "Auth gate evidence is missing top-level field: $required"
      }
    }

    $entry.top_level_result = [string]$payload.result
    $entry.top_level_failure_category = $payload.failure_category
    $entry.top_level_account_match = [bool]$payload.account_match
    $entry.top_level_remote_login_status = [string]$payload.remote_login_status

    if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
      throw "Auth gate evidence has an empty top-level result."
    }
    if (-not [bool]$payload.safe_to_start_ec2 -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
      throw "Blocked auth gate evidence must include a top-level failure_category."
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

function Test-LaneReadinessEvidenceContract {
  param([Parameter(Mandatory=$true)][string]$Path)

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
    top_level_result = $null
    top_level_failure_category = $null
    local_pre_ec2_ready = $null
    ready_for_ec2_static_proof = $null
    ready_for_generation = $null
    auth_gate_result = $null
    auth_gate_failure_category = $null
  }

  try {
    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($required in @("result", "failure_category", "local_pre_ec2_ready", "ready_for_ec2_static_proof", "ready_for_generation", "auth_gate")) {
      if (-not (Has-Property -Object $payload -Name $required)) {
        throw "Lane readiness evidence is missing top-level field: $required"
      }
    }
    foreach ($requiredAuth in @("result", "failure_category", "account_match", "remote_login_status", "ec2_work_allowed", "safe_to_start_ec2")) {
      if (-not (Has-Property -Object $payload.auth_gate -Name $requiredAuth)) {
        throw "Lane readiness auth_gate is missing field: $requiredAuth"
      }
    }

    $entry.top_level_result = [string]$payload.result
    $entry.top_level_failure_category = $payload.failure_category
    $entry.local_pre_ec2_ready = [bool]$payload.local_pre_ec2_ready
    $entry.ready_for_ec2_static_proof = [bool]$payload.ready_for_ec2_static_proof
    $entry.ready_for_generation = [bool]$payload.ready_for_generation
    $entry.auth_gate_result = [string]$payload.auth_gate.result
    $entry.auth_gate_failure_category = $payload.auth_gate.failure_category

    if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
      throw "Lane readiness evidence has an empty top-level result."
    }
    if (-not [bool]$payload.ready_for_generation -and [string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
      throw "Blocked lane readiness evidence must include a top-level failure_category."
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

function Test-EC2CoordinatorGateEvidenceContract {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][ValidateSet("static_proof", "workflow_smoke")][string]$Kind
  )

  $entry = [ordered]@{
    name = Split-Path -Leaf $Path
    kind = $Kind
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    result = "fail"
    error = $null
    top_level_result = $null
    top_level_failure_category = $null
    execute_gates_pass = $null
    blocked_reason_count = $null
    ec2_started = $null
    command_status = $null
    generation_executed = $null
    auth_gate_result = $null
    auth_gate_failure_category = $null
    readiness_gate_result = $null
    readiness_gate_failure_category = $null
  }

  try {
    $payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    foreach ($required in @("result", "failure_category", "execute_gates_pass", "blocked_reasons", "auth_gate", "readiness_gate")) {
      if (-not (Has-Property -Object $payload -Name $required)) {
        throw "EC2 coordinator evidence is missing top-level field: $required"
      }
    }
    foreach ($requiredAuth in @("result", "failure_category", "ec2_work_allowed", "safe_to_start_ec2")) {
      if (-not (Has-Property -Object $payload.auth_gate -Name $requiredAuth)) {
        throw "EC2 coordinator auth_gate is missing field: $requiredAuth"
      }
    }
    foreach ($requiredReadiness in @("result", "failure_category", "local_pre_ec2_ready", "ready_for_ec2_static_proof", "ready_for_generation")) {
      if (-not (Has-Property -Object $payload.readiness_gate -Name $requiredReadiness)) {
        throw "EC2 coordinator readiness_gate is missing field: $requiredReadiness"
      }
    }

    $entry.top_level_result = [string]$payload.result
    $entry.top_level_failure_category = $payload.failure_category
    $entry.execute_gates_pass = [bool]$payload.execute_gates_pass
    $entry.blocked_reason_count = @($payload.blocked_reasons).Count
    $entry.auth_gate_result = [string]$payload.auth_gate.result
    $entry.auth_gate_failure_category = $payload.auth_gate.failure_category
    $entry.readiness_gate_result = [string]$payload.readiness_gate.result
    $entry.readiness_gate_failure_category = $payload.readiness_gate.failure_category

    if (Has-Property -Object $payload -Name "ec2_started") {
      $entry.ec2_started = [bool]$payload.ec2_started
    }
    if (Has-Property -Object $payload -Name "command_status") {
      $entry.command_status = [string]$payload.command_status
    }
    if (Has-Property -Object $payload -Name "generation_executed") {
      $entry.generation_executed = [bool]$payload.generation_executed
    }

    if ([string]::IsNullOrWhiteSpace($entry.top_level_result)) {
      throw "EC2 coordinator evidence has an empty top-level result."
    }
    if (-not $entry.execute_gates_pass) {
      if ([string]::IsNullOrWhiteSpace([string]$payload.failure_category)) {
        throw "Blocked EC2 coordinator evidence must include a top-level failure_category."
      }
      if ($entry.blocked_reason_count -eq 0) {
        throw "Blocked EC2 coordinator evidence must include blocked_reasons."
      }
    }
    if ($entry.top_level_result -like "*blocked_before_ec2_start*") {
      if (-not (Has-Property -Object $payload -Name "ec2_started")) {
        throw "Blocked-before-start EC2 coordinator evidence must include ec2_started."
      }
      if ([bool]$payload.ec2_started) {
        throw "Blocked-before-start EC2 coordinator evidence must not start EC2."
      }
      if ((Has-Property -Object $payload -Name "command_status") -and [string]$payload.command_status -ne "not_started") {
        throw "Blocked-before-start EC2 coordinator evidence must keep command_status=not_started."
      }
    }
    if ($Kind -eq "workflow_smoke") {
      if (-not (Has-Property -Object $payload -Name "generation_executed")) {
        throw "Workflow smoke coordinator evidence is missing generation_executed."
      }
      if (-not $entry.execute_gates_pass -and [bool]$payload.generation_executed) {
        throw "Blocked workflow smoke coordinator evidence must not execute generation."
      }
    }

    $entry.result = "pass"
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$operationsRoot = Join-Path $ProjectRoot "Plan\Instructions\Operations"
$scriptsRoot = Join-Path $operationsRoot "Scripts"
$schemasRoot = Join-Path $operationsRoot "Schemas"
$templatesRoot = Join-Path $operationsRoot "Templates"
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
$workflowRuntimeDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime"
$tempRoot = Join-Path $env:TEMP "comfy_ui_ops_static_validation_$stamp"
$script:ValidationTempRoot = $tempRoot
$null = New-Item -ItemType Directory -Force -Path $tempRoot

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W60_OPERATIONS_HELPER_CURRENT_VALIDATION_$stamp.json"
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

$localSmokeResults = @()
$modelRecordFile = Join-Path $tempRoot "model_registry_smoke.json"
$localSmokeResults += Invoke-LocalHelper -Name "model_registry_record_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-ModelRegistryRecord.ps1") `
  -Arguments @("-ModelName", "static-validation-placeholder", "-ModelType", "checkpoint", "-BaseModel", "SDXL", "-LocalPath", "C:\Comfy_UI_Main\__missing_static_validation_placeholder.safetensors") `
  -ExpectedOutputFile ""

$localSmokeResults += Invoke-LocalHelper -Name "github_checkpoint_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-GitHubCheckpoint.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-Message", "static validation dry run") `
  -ExpectedOutputFile ""

$staticProofDryRunFile = Join-Path $tempRoot "ec2_lane_static_proof_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_lane_static_proof_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2LaneStaticProof.ps1") `
  -Arguments @("-OutFile", $staticProofDryRunFile) `
  -ExpectedOutputFile $staticProofDryRunFile

$comfySmokeFile = Join-Path $tempRoot "comfy_workflow_smoke_dry_run.json"
$comfySmokeRequestFile = Join-Path $tempRoot "comfy_workflow_smoke_request.json"
$localSmokeResults += Invoke-LocalHelper -Name "comfy_workflow_smoke_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-ComfyWorkflowSmoke.ps1") `
  -Arguments @("-OutFile", $comfySmokeFile, "-OutRequestFile", $comfySmokeRequestFile) `
  -ExpectedOutputFile $comfySmokeFile

$pullbackDryRunFile = Join-Path $tempRoot "ec2_pullback_record_dry_run.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_pullback_record_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2PullbackRecord.ps1") `
  -Arguments @("-DryRun", "-OutFile", $pullbackDryRunFile) `
  -ExpectedOutputFile $pullbackDryRunFile

$localSmokeResults += Invoke-PullbackManifestVerificationSmoke `
  -ScriptPath (Join-Path $scriptsRoot "New-EC2PullbackRecord.ps1") `
  -TempRoot $tempRoot

$readinessFile = Join-Path $tempRoot "lane_runtime_readiness.json"
$localSmokeResults += Invoke-LocalHelper -Name "lane_runtime_readiness_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Test-LaneRuntimeReadiness.ps1") `
  -Arguments @("-OutFile", $readinessFile) `
  -ExpectedOutputFile $readinessFile

$coordinatorFile = Join-Path $tempRoot "ec2_workflow_smoke_run_dry_run.json"
$coordinatorRequestFile = Join-Path $tempRoot "ec2_workflow_smoke_run_request.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_smoke_run_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2WorkflowSmokeRun.ps1") `
  -Arguments @("-OutFile", $coordinatorFile, "-OutRequestFile", $coordinatorRequestFile, "-ReadinessFile", $readinessFile) `
  -ExpectedOutputFile $coordinatorFile

$packageCoordinatorFile = Join-Path $tempRoot "ec2_workflow_smoke_run_package_dry_run.json"
$packageCoordinatorRequestFile = Join-Path $tempRoot "ec2_workflow_smoke_run_package_request.json"
$hyperrealPackageManifest = Join-Path $ProjectRoot "runtime_artifacts\run_packages\sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1\RUN_PACKAGE_MANIFEST.json"
$localSmokeResults += Invoke-LocalHelper -Name "ec2_workflow_smoke_run_package_dry_run" `
  -ScriptPath (Join-Path $scriptsRoot "Invoke-EC2WorkflowSmokeRun.ps1") `
  -Arguments @("-OutFile", $packageCoordinatorFile, "-OutRequestFile", $packageCoordinatorRequestFile, "-ReadinessFile", $readinessFile, "-RunPackageManifestFile", $hyperrealPackageManifest) `
  -ExpectedOutputFile $packageCoordinatorFile

$runtimeUnblockHandoffFile = Join-Path $tempRoot "runtime_unblock_handoff.json"
$runtimeUnblockHandoffMarkdown = Join-Path $tempRoot "runtime_unblock_handoff.md"
$localSmokeResults += Invoke-LocalHelper -Name "runtime_unblock_handoff_smoke" `
  -ScriptPath (Join-Path $scriptsRoot "New-RuntimeUnblockHandoff.ps1") `
  -Arguments @("-ProjectRoot", $ProjectRoot, "-OutFile", $runtimeUnblockHandoffFile, "-MarkdownOutFile", $runtimeUnblockHandoffMarkdown, "-RunPackageManifestFile", $hyperrealPackageManifest) `
  -ExpectedOutputFile $runtimeUnblockHandoffFile

$latestBlockedStaticProof = Find-LatestFile -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_*.json"
$latestCoordinatorDryRun = Find-LatestFile -Directory $workflowRuntimeDir -Filter "W61_EC2_WORKFLOW_SMOKE_RUN_DRY_RUN_*.json"
$latestCoordinatorBlockedRun = Find-LatestFile -Directory $workflowRuntimeDir -Filter "W61_EC2_WORKFLOW_SMOKE_RUN_BLOCKED_EXECUTE_*.json"
$latestReadiness = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS_*.json"
$latestAuthGate = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE*.json"

$evidenceChecks = @()
foreach ($evidence in @($latestBlockedStaticProof, $latestCoordinatorDryRun, $latestCoordinatorBlockedRun, $latestReadiness)) {
  if ([string]::IsNullOrWhiteSpace($evidence)) { continue }
  $evidenceChecks += Test-JsonFile -Path $evidence
}

$evidenceContractChecks = @()
if (![string]::IsNullOrWhiteSpace($latestAuthGate)) {
  $evidenceContractChecks += Test-AuthGateEvidenceContract -Path $latestAuthGate
}
if (![string]::IsNullOrWhiteSpace($latestReadiness)) {
  $evidenceContractChecks += Test-LaneReadinessEvidenceContract -Path $latestReadiness
}
if (![string]::IsNullOrWhiteSpace($latestBlockedStaticProof)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestBlockedStaticProof -Kind "static_proof"
}
if (![string]::IsNullOrWhiteSpace($latestCoordinatorDryRun)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestCoordinatorDryRun -Kind "workflow_smoke"
}
if (![string]::IsNullOrWhiteSpace($latestCoordinatorBlockedRun)) {
  $evidenceContractChecks += Test-EC2CoordinatorGateEvidenceContract -Path $latestCoordinatorBlockedRun -Kind "workflow_smoke"
}

$scriptFailures = @($scriptParseResults | Where-Object { $_.result -ne "pass" })
$jsonFailures = @($jsonParseResults | Where-Object { $_.result -ne "pass" })
$smokeFailures = @($localSmokeResults | Where-Object { $_.result -ne "pass" -or ($_.expected_output_file -and -not $_.expected_output_json_valid) })
$evidenceFailures = @($evidenceChecks | Where-Object { $_.result -ne "pass" })
$evidenceContractFailures = @($evidenceContractChecks | Where-Object { $_.result -ne "pass" })

$record = [ordered]@{
  evidence_id = "EVID-W60-OPERATIONS-HELPER-CURRENT-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W60-010"
  artifact_type = "operations_helper_current_static_validation"
  tracker_ids = @("TRK-W60-010", "TRK-W61-006", "TRK-W61-007")
  item_ids = @("W60-010", "ITEM-W61-006", "ITEM-W61-007")
  qa_protocol_used = @(
    "README_OPERATIONS_WAVE60.md",
    "OPERATIONAL_DONE_GATES.md",
    "SECRETS_ENV_HANDLING_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/Instructions/Operations/Scripts/*.ps1",
    "Plan/Instructions/Operations/Schemas/*.json",
    "Plan/Instructions/Operations/Templates/*.json",
    "latest selected-lane runtime gate evidence",
    "runtime unblock handoff smoke"
  )
  validation_results = [ordered]@{
    script_count = @($scriptParseResults).Count
    script_parse_failures = @($scriptFailures).Count
    script_parse_results = $scriptParseResults
    json_file_count = @($jsonParseResults).Count
    json_parse_failures = @($jsonFailures).Count
    json_parse_results = $jsonParseResults
    local_smoke_count = @($localSmokeResults).Count
    local_smoke_failures = @($smokeFailures).Count
    local_smoke_results = $localSmokeResults
    evidence_check_count = @($evidenceChecks).Count
    evidence_check_failures = @($evidenceFailures).Count
    evidence_checks = $evidenceChecks
    evidence_contract_check_count = @($evidenceContractChecks).Count
    evidence_contract_check_failures = @($evidenceContractFailures).Count
    evidence_contract_checks = $evidenceContractChecks
  }
  skipped_live_execution = @(
    [ordered]@{ script = "Invoke-CivitaiModelLookup.ps1"; reason = "Would contact Civitai API; out of scope for local static validation." },
    [ordered]@{ script = "Start-ComfyUIGpuServer.ps1"; reason = "Could start EC2/cost resources; out of scope for local static validation." },
    [ordered]@{ script = "Stop-ComfyUIGpuServer.ps1"; reason = "Would contact AWS; out of scope for local static validation." },
    [ordered]@{ script = "Test-AwsAuthGate.ps1"; reason = "Would contact AWS login/STS; existing auth evidence is inspected instead." },
    [ordered]@{ script = "Test-AwsProfileAuthMatrix.ps1"; reason = "Would contact AWS STS for every configured profile; out of scope for local static validation." },
    [ordered]@{ script = "Test-AwsComfyGpuIdentity.ps1"; reason = "Would contact AWS; out of scope for local static validation." }
  )
  temp_root = "[VALIDATION_TEMP_ROOT]"
  temp_root_redacted = $true
  result = $(if ($scriptFailures.Count -eq 0 -and $jsonFailures.Count -eq 0 -and $smokeFailures.Count -eq 0 -and $evidenceFailures.Count -eq 0 -and $evidenceContractFailures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_issues = @(
    "Live AWS, Civitai, GitHub, EC2 start, ComfyUI runtime generation, artifact pullback, and visual QA remain separate runtime validations.",
    "AWS auth is still expired in current evidence; this validation intentionally does not refresh or require AWS credentials."
  )
  next_action = "After AWS browser login refresh, rerun auth gate and selected-lane readiness before EC2 static proof."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote operations helper static validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
