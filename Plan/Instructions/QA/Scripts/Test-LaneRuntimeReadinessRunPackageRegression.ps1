<#
.SYNOPSIS
Exercises fail-closed run-package evidence handling in lane runtime readiness.

.DESCRIPTION
Copies one valid local run package into a project-local temporary directory,
then runs positive and tampered cases. No network, cloud, ComfyUI, or runtime
operation is performed.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$RunPackageManifestFile,
  [Parameter(Mandatory=$true)][string]$AuthGateFile,
  [Parameter(Mandatory=$true)][string]$ProfileMatrixFile,
  [Parameter(Mandatory=$true)][string]$ModelRegistryCoverageFile,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path))
}

function Write-JsonNoBom {
  param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][object]$Payload)
  [System.IO.File]::WriteAllText($Path, ($Payload | ConvertTo-Json -Depth 40) + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}

function Set-GeneratedHash {
  param([Parameter(Mandatory=$true)][object]$Manifest, [Parameter(Mandatory=$true)][string]$FileName, [Parameter(Mandatory=$true)][string]$Path)
  $entry = @($Manifest.generated_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.path) -eq $FileName })[0]
  $entry.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function New-CaseFixture {
  param([Parameter(Mandatory=$true)][string]$Name)
  $caseDir = Join-Path $tempRoot $Name
  [System.IO.Directory]::CreateDirectory($caseDir) | Out-Null
  $manifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
  foreach ($packagedEntry in @($manifest.packaged_files)) {
    $sourcePath = Resolve-ProjectPath -Path ([string]$packagedEntry.source)
    $packagedPath = Resolve-ProjectPath -Path ([string]$packagedEntry.packaged)
    $sourceMatches = (
      (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash -eq
      (Get-FileHash -Algorithm SHA256 -LiteralPath $packagedPath).Hash
    )
    $packagedEntry.source_hash_match = $sourceMatches
    if (!$sourceMatches) {
      $packagedEntry | Add-Member -NotePropertyName profile_modified -NotePropertyValue $true -Force
    }
  }
  foreach ($fileName in @("static_validation.json", "smoke_dry_run.json", "prompt_request.json")) {
    Copy-Item -LiteralPath (Join-Path $sourcePackageDir $fileName) -Destination (Join-Path $caseDir $fileName)
    $entry = @($manifest.generated_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.path) -eq $fileName })[0]
    $entry.path = (Join-Path $caseDir $fileName)
    $entry.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $caseDir $fileName)).Hash.ToLowerInvariant()
  }
  $smokePath = Join-Path $caseDir "smoke_dry_run.json"
  $smoke = Get-Content -LiteralPath $smokePath -Raw | ConvertFrom-Json
  $smoke.request_body_path = Join-Path $caseDir "prompt_request.json"
  Write-JsonNoBom -Path $smokePath -Payload $smoke
  Set-GeneratedHash -Manifest $manifest -FileName "smoke_dry_run.json" -Path $smokePath
  $manifestPath = Join-Path $caseDir "RUN_PACKAGE_MANIFEST.json"
  Write-JsonNoBom -Path $manifestPath -Payload $manifest
  return [pscustomobject]@{ directory = $caseDir; manifest_path = $manifestPath; manifest = $manifest; auth_path = $authPath }
}

function Invoke-Case {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [scriptblock]$Mutate,
    [Parameter(Mandatory=$true)][int]$ExpectedExitCode,
    [Parameter(Mandatory=$true)][bool]$ExpectedManifestValid,
    [string]$ExpectedErrorPattern = "",
    [string]$ExpectedReadinessResult = "",
    [AllowNull()][object]$ExpectedStaticReady = $null
  )
  $fixture = New-CaseFixture -Name $Name
  if ($null -ne $Mutate) { & $Mutate $fixture }
  Write-JsonNoBom -Path $fixture.manifest_path -Payload $fixture.manifest
  $childOut = Join-Path $fixture.directory "readiness.json"
  $arguments = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $validator,
    "-ProjectRoot", $ProjectRoot,
    "-LaneId", $laneId,
    "-AuthGateFile", $fixture.auth_path,
    "-ProfileMatrixFile", $profilePath,
    "-ModelRegistryCoverageFile", $registryPath,
    "-RunPackageManifestFile", $fixture.manifest_path,
    "-OutFile", $childOut
  )
  & powershell @arguments *> $null
  $exitCode = $LASTEXITCODE
  $payload = if (Test-Path -LiteralPath $childOut) { Get-Content -LiteralPath $childOut -Raw | ConvertFrom-Json } else { $null }
  $errorText = if ($null -ne $payload) { @($payload.errors) -join "`n" } else { "" }
  $errorPass = [string]::IsNullOrWhiteSpace($ExpectedErrorPattern) -or $errorText -match $ExpectedErrorPattern
  if ([string]::IsNullOrWhiteSpace($ExpectedReadinessResult)) {
    $ExpectedReadinessResult = $(if ($ExpectedManifestValid) { "ready_for_ec2_static_proof" } else { "not_ready" })
  }
  if ($null -eq $ExpectedStaticReady) { $ExpectedStaticReady = $ExpectedManifestValid }
  $positivePass = if ($ExpectedManifestValid) {
    $null -ne $payload -and [bool]$payload.local_pre_ec2_ready -and
    [bool]$payload.ready_for_ec2_static_proof -eq [bool]$ExpectedStaticReady -and
    -not [bool]$payload.ready_for_generation -and [string]$payload.result -eq $ExpectedReadinessResult
  } else {
    $null -ne $payload -and -not [bool]$payload.local_pre_ec2_ready -and -not [bool]$payload.ready_for_ec2_static_proof -and
    -not [bool]$payload.ready_for_generation -and [string]$payload.result -eq "not_ready" -and
    [string]$payload.lane_evidence_selection.source -eq "run_package_manifest" -and
    $null -eq $payload.lane_evidence_selection.workflow_static_validation
  }
  $passed = (
    $exitCode -eq $ExpectedExitCode -and $null -ne $payload -and
    [bool]$payload.run_package_manifest.valid -eq $ExpectedManifestValid -and
    $errorPass -and $positivePass
  )
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($passed) { "pass" } else { "fail" })
    exit_code = $exitCode
    expected_exit_code = $ExpectedExitCode
    manifest_valid = $(if ($null -ne $payload) { [bool]$payload.run_package_manifest.valid } else { $null })
    expected_manifest_valid = $ExpectedManifestValid
    readiness_result = $(if ($null -ne $payload) { [string]$payload.result } else { $null })
    expected_readiness_result = $ExpectedReadinessResult
    error_pattern = $ExpectedErrorPattern
    errors = $(if ($null -ne $payload) { @($payload.errors) } else { @("child_output_missing") })
  }
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$sourceManifestPath = Resolve-ProjectPath -Path $RunPackageManifestFile
$sourcePackageDir = Split-Path -Parent $sourceManifestPath
$authPath = Resolve-ProjectPath -Path $AuthGateFile
$profilePath = Resolve-ProjectPath -Path $ProfileMatrixFile
$registryPath = Resolve-ProjectPath -Path $ModelRegistryCoverageFile
$validator = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1"
foreach ($required in @($sourceManifestPath, $authPath, $profilePath, $registryPath, $validator)) {
  if (!(Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required regression input missing: $required" }
}
$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
$laneId = [string]$sourceManifest.lane_id
$tempRoot = Join-Path $ProjectRoot ("runtime_artifacts\regression_temp\lane_readiness_run_package_{0}" -f ([guid]::NewGuid().ToString("N")))
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null

$tests = @()
$tests += Invoke-Case -Name "valid_manifest" -ExpectedExitCode 0 -ExpectedManifestValid $true
$tests += Invoke-Case -Name "lane_mismatch" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "lane_id does not match" -Mutate { param($f) $f.manifest.lane_id = "wrong_lane" }
$tests += Invoke-Case -Name "missing_generated_entry" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "exactly one generated_files entry" -Mutate { param($f) $f.manifest.generated_files = @($f.manifest.generated_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.path) -ne "prompt_request.json" }) }
$tests += Invoke-Case -Name "hash_mismatch" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "SHA-256 mismatch" -Mutate { param($f) (@($f.manifest.generated_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.path) -eq "static_validation.json" })[0]).sha256 = ("0" * 64) }
$tests += Invoke-Case -Name "path_escape" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "outside ProjectRoot" -Mutate { param($f) (@($f.manifest.generated_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.path) -eq "static_validation.json" })[0]).path = "..\outside\static_validation.json" }
$tests += Invoke-Case -Name "unsafe_boundary" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "local-only runtime boundaries" -Mutate { param($f) $f.manifest.aws_contacted = $true }
$tests += Invoke-Case -Name "undeclared_packaged_file_drift" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "drift is not declared profile_modified" -Mutate {
  param($f)
  $entry = @($f.manifest.packaged_files | Where-Object { [System.IO.Path]::GetFileName([string]$_.packaged) -eq "workflow.api.json" })[0]
  $copy = Join-Path $f.directory "packaged_workflow.api.json"
  Copy-Item -LiteralPath (Resolve-ProjectPath -Path ([string]$entry.packaged)) -Destination $copy
  Add-Content -LiteralPath $copy -Value " "
  $entry.packaged = $copy
  $entry.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $copy).Hash.ToLowerInvariant()
  $entry.source_hash_match = $false
  $entry | Add-Member -NotePropertyName profile_modified -NotePropertyValue $false -Force
}
$tests += Invoke-Case -Name "static_not_pass" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "static validation" -Mutate { param($f) $p=Join-Path $f.directory "static_validation.json"; $j=Get-Content -Raw $p|ConvertFrom-Json; $j.qa_status="fail"; Write-JsonNoBom $p $j; Set-GeneratedHash $f.manifest "static_validation.json" $p }
$tests += Invoke-Case -Name "smoke_execution_enabled" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "smoke dry-run" -Mutate { param($f) $p=Join-Path $f.directory "smoke_dry_run.json"; $j=Get-Content -Raw $p|ConvertFrom-Json; $j.execution_allowed=$true; Write-JsonNoBom $p $j; Set-GeneratedHash $f.manifest "smoke_dry_run.json" $p }
$tests += Invoke-Case -Name "prompt_empty" -ExpectedExitCode 2 -ExpectedManifestValid $false -ExpectedErrorPattern "no non-empty prompt" -Mutate { param($f) $p=Join-Path $f.directory "prompt_request.json"; $j=Get-Content -Raw $p|ConvertFrom-Json; $j.prompt=[pscustomobject]@{}; Write-JsonNoBom $p $j; Set-GeneratedHash $f.manifest "prompt_request.json" $p }
$tests += Invoke-Case -Name "blocked_auth_cross_gate" -ExpectedExitCode 0 -ExpectedManifestValid $true -ExpectedReadinessResult "local_pre_ec2_ready_runtime_blocked_auth" -ExpectedStaticReady $false -Mutate {
  param($f)
  $blockedAuth = Get-Content -LiteralPath $authPath -Raw | ConvertFrom-Json
  $blockedAuth.ec2_work_allowed = $false
  $blockedAuth.safe_to_start_ec2 = $false
  $blockedAuth.generation_allowed = $false
  $blockedAuth.result = "blocked_regression_fixture"
  $blockedAuth.failure_category = "blocked_regression_fixture"
  $blockedPath = Join-Path $f.directory "blocked_auth.json"
  Write-JsonNoBom -Path $blockedPath -Payload $blockedAuth
  $f.auth_path = $blockedPath
}

$fallbackDir = Join-Path $tempRoot "lane_scan_fallback"
[System.IO.Directory]::CreateDirectory($fallbackDir) | Out-Null
$fallbackOut = Join-Path $fallbackDir "readiness.json"
& powershell -NoProfile -ExecutionPolicy Bypass -File $validator -ProjectRoot $ProjectRoot -LaneId $laneId -AuthGateFile $authPath -ProfileMatrixFile $profilePath -ModelRegistryCoverageFile $registryPath -OutFile $fallbackOut *> $null
$fallbackExit = $LASTEXITCODE
$fallbackPayload = if (Test-Path -LiteralPath $fallbackOut) { Get-Content -LiteralPath $fallbackOut -Raw | ConvertFrom-Json } else { $null }
$fallbackPass = (
  $null -ne $fallbackPayload -and -not [bool]$fallbackPayload.run_package_manifest.supplied -and
  [string]$fallbackPayload.lane_evidence_selection.source -eq "lane_scan" -and
  $fallbackExit -in @(0, 2)
)
$tests += [pscustomobject][ordered]@{
  name = "lane_scan_fallback_contract"
  result = $(if ($fallbackPass) { "pass" } else { "fail" })
  exit_code = $fallbackExit
  expected_exit_code = "0_or_2_by_available_lane_evidence"
  manifest_valid = $(if ($null -ne $fallbackPayload) { [bool]$fallbackPayload.run_package_manifest.valid } else { $null })
  expected_manifest_valid = $false
  readiness_result = $(if ($null -ne $fallbackPayload) { [string]$fallbackPayload.result } else { $null })
  expected_readiness_result = "lane_scan_result"
  error_pattern = ""
  errors = $(if ($null -ne $fallbackPayload) { @($fallbackPayload.errors) } else { @("child_output_missing") })
}

$outsideRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("lane_readiness_outside_{0}" -f ([guid]::NewGuid().ToString("N")))
[System.IO.Directory]::CreateDirectory($outsideRoot) | Out-Null
$outsideManifest = Join-Path $outsideRoot "RUN_PACKAGE_MANIFEST.json"
Copy-Item -LiteralPath $sourceManifestPath -Destination $outsideManifest
$handoffOut = Join-Path $tempRoot "outside_manifest_handoff.json"
$handoffMarkdown = Join-Path $tempRoot "outside_manifest_handoff.md"
$handoffHelper = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-RuntimeUnblockHandoff.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $handoffHelper -ProjectRoot $ProjectRoot -LaneId $laneId -RunPackageManifestFile $outsideManifest -OutFile $handoffOut -MarkdownOutFile $handoffMarkdown *> $null
$handoffExit = $LASTEXITCODE
$handoffPayload = if (Test-Path -LiteralPath $handoffOut) { Get-Content -LiteralPath $handoffOut -Raw | ConvertFrom-Json } else { $null }
$handoffErrors = if ($null -ne $handoffPayload) { @($handoffPayload.gate_summary.run_package.errors) } else { @("child_output_missing") }
$handoffPass = (
  $handoffExit -eq 0 -and $null -ne $handoffPayload -and
  [bool]$handoffPayload.gate_summary.run_package.supplied -and
  -not [bool]$handoffPayload.gate_summary.run_package.valid -and
  ($handoffErrors -join "`n") -match "outside ProjectRoot" -and
  [bool]$handoffPayload.local_only -and -not [bool]$handoffPayload.aws_contacted -and
  -not [bool]$handoffPayload.ec2_started -and -not [bool]$handoffPayload.generation_executed
)
$tests += [pscustomobject][ordered]@{
  name = "handoff_rejects_outside_manifest"
  result = $(if ($handoffPass) { "pass" } else { "fail" })
  exit_code = $handoffExit
  expected_exit_code = 0
  manifest_valid = $(if ($null -ne $handoffPayload) { [bool]$handoffPayload.gate_summary.run_package.valid } else { $null })
  expected_manifest_valid = $false
  readiness_result = $(if ($null -ne $handoffPayload) { [string]$handoffPayload.result } else { $null })
  expected_readiness_result = "handoff_fail_closed"
  error_pattern = "outside ProjectRoot"
  errors = $handoffErrors
}
if (([System.IO.Path]::GetFullPath($outsideRoot)).StartsWith(([System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())), [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $outsideRoot -Recurse -Force
}

$siblingRoot = $ProjectRoot.TrimEnd("\", "/") + "_sibling_regression_" + ([guid]::NewGuid().ToString("N"))
[System.IO.Directory]::CreateDirectory($siblingRoot) | Out-Null
$siblingManifest = Join-Path $siblingRoot "RUN_PACKAGE_MANIFEST.json"
Copy-Item -LiteralPath $sourceManifestPath -Destination $siblingManifest
$siblingReadinessOut = Join-Path $tempRoot "sibling_manifest_readiness.json"
& powershell -NoProfile -ExecutionPolicy Bypass -File $validator -ProjectRoot $ProjectRoot -LaneId $laneId -AuthGateFile $authPath -ProfileMatrixFile $profilePath -ModelRegistryCoverageFile $registryPath -RunPackageManifestFile $siblingManifest -OutFile $siblingReadinessOut *> $null
$siblingReadinessExit = $LASTEXITCODE
$siblingReadiness = if (Test-Path -LiteralPath $siblingReadinessOut) { Get-Content -LiteralPath $siblingReadinessOut -Raw | ConvertFrom-Json } else { $null }
$siblingHandoffOut = Join-Path $tempRoot "sibling_manifest_handoff.json"
$siblingHandoffMarkdown = Join-Path $tempRoot "sibling_manifest_handoff.md"
& powershell -NoProfile -ExecutionPolicy Bypass -File $handoffHelper -ProjectRoot $ProjectRoot -LaneId $laneId -RunPackageManifestFile $siblingManifest -OutFile $siblingHandoffOut -MarkdownOutFile $siblingHandoffMarkdown *> $null
$siblingHandoffExit = $LASTEXITCODE
$siblingHandoff = if (Test-Path -LiteralPath $siblingHandoffOut) { Get-Content -LiteralPath $siblingHandoffOut -Raw | ConvertFrom-Json } else { $null }
$siblingErrors = @()
if ($null -ne $siblingReadiness) { $siblingErrors += @($siblingReadiness.run_package_manifest.errors) }
if ($null -ne $siblingHandoff) { $siblingErrors += @($siblingHandoff.gate_summary.run_package.errors) }
$siblingPass = (
  $siblingReadinessExit -eq 2 -and $null -ne $siblingReadiness -and
  -not [bool]$siblingReadiness.run_package_manifest.valid -and
  $siblingHandoffExit -eq 0 -and $null -ne $siblingHandoff -and
  -not [bool]$siblingHandoff.gate_summary.run_package.valid -and
  @($siblingErrors | Where-Object { [string]$_ -match "outside ProjectRoot" }).Count -eq 2
)
$tests += [pscustomobject][ordered]@{
  name = "both_helpers_reject_sibling_prefix_manifest"
  result = $(if ($siblingPass) { "pass" } else { "fail" })
  exit_code = "$siblingReadinessExit/$siblingHandoffExit"
  expected_exit_code = "2/0"
  manifest_valid = $false
  expected_manifest_valid = $false
  readiness_result = $(if ($null -ne $siblingReadiness) { [string]$siblingReadiness.result } else { $null })
  expected_readiness_result = "both_helpers_fail_closed"
  error_pattern = "outside ProjectRoot twice"
  errors = $siblingErrors
}
$expectedSiblingPrefix = $ProjectRoot.TrimEnd("\", "/") + "_sibling_regression_"
if (([System.IO.Path]::GetFullPath($siblingRoot)).StartsWith($expectedSiblingPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $siblingRoot -Recurse -Force
}

$failed = @($tests | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_runtime_readiness_run_package_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  cloud_mutated = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  lane_id = $laneId
  test_count = $tests.Count
  passing_test_count = @($tests | Where-Object { [string]$_.result -eq "pass" }).Count
  failed_test_count = $failed.Count
  tests = $tests
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W64_LANE_RUNTIME_READINESS_RUN_PACKAGE_REGRESSION_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $outPath)) | Out-Null
Write-JsonNoBom -Path $outPath -Payload $record

$tempBase = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "runtime_artifacts\regression_temp")).TrimEnd("\") + "\"
$tempResolved = [System.IO.Path]::GetFullPath($tempRoot)
if ($tempResolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $tempResolved -Recurse -Force
}

$record | ConvertTo-Json -Depth 30
if ($failed.Count -gt 0) { exit 1 }
exit 0
