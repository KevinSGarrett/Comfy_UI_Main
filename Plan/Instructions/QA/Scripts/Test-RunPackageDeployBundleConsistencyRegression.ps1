<#
.SYNOPSIS
Exercises fail-closed publish-evidence behavior for the package/deploy validator.

.DESCRIPTION
Runs dry-run/live positive cases and fail-closed negative cases against a local run
package and deploy bundle. All fixtures and child evidence stay under a unique
temporary directory. No external service or runtime is contacted.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$RunPackageManifestFile,
  [Parameter(Mandatory=$true)][string]$DeployBundleManifestFile,
  [Parameter(Mandatory=$true)][string]$PublishEvidenceFile,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $Path))
}

function ConvertTo-ProjectRelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $resolved.Substring($root.Length).Replace("\", "/")
  }
  return $resolved
}

function Read-JsonIfPresent {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  try {
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
  } catch {
    return $null
  }
}

function Invoke-Case {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [string]$DeployFile = $deployPath,
    [AllowNull()][string]$PublishFile,
    [Parameter(Mandatory=$true)][int]$ExpectedExitCode,
    [Parameter(Mandatory=$true)][string]$ExpectedResult,
    [AllowNull()][string]$ExpectedFailureCategory,
    [Parameter(Mandatory=$true)][string]$ExpectedPublishStatus,
    [string[]]$ExpectedWarnings = @()
  )

  $childOut = Join-Path $tempRoot "$Name.json"
  $arguments = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $validator,
    "-ProjectRoot", $ProjectRoot,
    "-RunPackageManifestFile", $runPath,
    "-DeployBundleManifestFile", $DeployFile,
    "-OutFile", $childOut,
    "-Strict"
  )
  if (-not [string]::IsNullOrWhiteSpace($PublishFile)) {
    $arguments += @("-PublishEvidenceFile", $PublishFile)
  }

  & powershell @arguments *> $null
  $exitCode = $LASTEXITCODE
  $payload = Read-JsonIfPresent -Path $childOut
  $safetyPass = (
    $null -ne $payload -and [bool]$payload.local_only -and
    -not [bool]$payload.aws_contacted -and -not [bool]$payload.github_api_contacted -and
    -not [bool]$payload.civitai_contacted -and -not [bool]$payload.s3_contacted -and
    -not [bool]$payload.comfyui_contacted -and -not [bool]$payload.ec2_started -and
    -not [bool]$payload.generation_executed -and -not [bool]$payload.target_runtime_proof -and
    -not [bool]$payload.certification_claimed
  )
  $warnings = if ($null -ne $payload) { @($payload.warnings) } else { @() }
  $warningsPass = (@($ExpectedWarnings | Where-Object { $_ -notin $warnings }).Count -eq 0 -and $warnings.Count -eq $ExpectedWarnings.Count)
  $failureCategory = if ($null -ne $payload) { [string]$payload.failure_category } else { "" }
  $expectedFailure = if ($null -eq $ExpectedFailureCategory) { "" } else { $ExpectedFailureCategory }
  $passed = (
    $exitCode -eq $ExpectedExitCode -and $null -ne $payload -and
    [string]$payload.result -eq $ExpectedResult -and
    $failureCategory -eq $expectedFailure -and
    [bool]$payload.strict -and
    [string]$payload.publish_evidence_status -eq $ExpectedPublishStatus -and
    $warningsPass -and $safetyPass
  )

  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($passed) { "pass" } else { "fail" })
    exit_code = $exitCode
    expected_exit_code = $ExpectedExitCode
    child_result = $(if ($null -ne $payload) { [string]$payload.result } else { $null })
    expected_result = $ExpectedResult
    failure_category = $(if ($null -ne $payload) { $payload.failure_category } else { $null })
    expected_failure_category = $ExpectedFailureCategory
    publish_evidence_status = $(if ($null -ne $payload) { $payload.publish_evidence_status } else { $null })
    expected_publish_evidence_status = $ExpectedPublishStatus
    warnings = $warnings
    expected_warnings = @($ExpectedWarnings)
    safety_pass = $safetyPass
  }
}

function New-DeployFixture {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][scriptblock]$Mutate
  )
  $fixtureDir = Join-Path $tempRoot "d_$Name"
  Copy-Item -LiteralPath (Split-Path -Parent $deployPath) -Destination $fixtureDir -Recurse
  $fixtureManifest = Join-Path $fixtureDir (Split-Path -Leaf $deployPath)
  $fixture = Get-Content -LiteralPath $fixtureManifest -Raw | ConvertFrom-Json
  & $Mutate $fixture
  [System.IO.File]::WriteAllText($fixtureManifest, ($fixture | ConvertTo-Json -Depth 30), $utf8NoBom)
  return $fixtureManifest
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$runPath = Resolve-ProjectPath -Path $RunPackageManifestFile
$deployPath = Resolve-ProjectPath -Path $DeployBundleManifestFile
$publishPath = Resolve-ProjectPath -Path $PublishEvidenceFile
$validator = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RunPackageDeployBundleConsistency.ps1"
foreach ($required in @($runPath, $deployPath, $publishPath, $validator)) {
  if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
    throw "Required regression input missing: $required"
  }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("rpdr_{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 8)))
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$invalidJsonPath = Join-Path $tempRoot "invalid_publish.json"
[System.IO.File]::WriteAllText($invalidJsonPath, "{ invalid json", $utf8NoBom)
$invalidPayloadPath = Join-Path $tempRoot "invalid_publish_payload.json"
[System.IO.File]::WriteAllText($invalidPayloadPath, "null", $utf8NoBom)
$mismatchPath = Join-Path $tempRoot "mismatched_publish.json"
$mismatch = Get-Content -LiteralPath $publishPath -Raw | ConvertFrom-Json
$mismatch.bundle_id = "intentional_regression_mismatch"
[System.IO.File]::WriteAllText($mismatchPath, ($mismatch | ConvertTo-Json -Depth 20), $utf8NoBom)
$livePublishPath = Join-Path $tempRoot "live_publish.json"
$livePublish = Get-Content -LiteralPath $publishPath -Raw | ConvertFrom-Json
$livePublish.result = "deploy_bundle_uploaded_to_s3"
$livePublish.local_only = $false
$livePublish.aws_contacted = $true
$livePublish.upload.attempted = $true
$livePublish.upload.bundle_rc = 0
$livePublish.upload.manifest_rc = 0
[System.IO.File]::WriteAllText($livePublishPath, ($livePublish | ConvertTo-Json -Depth 20), $utf8NoBom)
$failedLivePublishPath = Join-Path $tempRoot "failed_live_publish.json"
$failedLivePublish = Get-Content -LiteralPath $livePublishPath -Raw | ConvertFrom-Json
$failedLivePublish.upload.bundle_rc = 1
[System.IO.File]::WriteAllText($failedLivePublishPath, ($failedLivePublish | ConvertTo-Json -Depth 20), $utf8NoBom)
$missingSafetyFlagsPath = Join-Path $tempRoot "missing_safety_flags.json"
$missingSafetyFlags = Get-Content -LiteralPath $livePublishPath -Raw | ConvertFrom-Json
$missingSafetyFlags.PSObject.Properties.Remove("ec2_started")
$missingSafetyFlags.PSObject.Properties.Remove("generation_executed")
[System.IO.File]::WriteAllText($missingSafetyFlagsPath, ($missingSafetyFlags | ConvertTo-Json -Depth 20), $utf8NoBom)
$ec2StartedPath = Join-Path $tempRoot "ec2_started.json"
$ec2Started = Get-Content -LiteralPath $livePublishPath -Raw | ConvertFrom-Json
$ec2Started.ec2_started = $true
[System.IO.File]::WriteAllText($ec2StartedPath, ($ec2Started | ConvertTo-Json -Depth 20), $utf8NoBom)
$generationExecutedPath = Join-Path $tempRoot "generation_executed.json"
$generationExecuted = Get-Content -LiteralPath $livePublishPath -Raw | ConvertFrom-Json
$generationExecuted.generation_executed = $true
[System.IO.File]::WriteAllText($generationExecutedPath, ($generationExecuted | ConvertTo-Json -Depth 20), $utf8NoBom)
$missingPath = Join-Path $tempRoot "missing_publish.json"

$requiredMissingDeploy = New-DeployFixture -Name "m" -Mutate {
  param($fixture)
  $fixture.PSObject.Properties.Remove("required_input_assets")
}
$requiredCountMismatchDeploy = New-DeployFixture -Name "c" -Mutate {
  param($fixture)
  $fixture.required_input_asset_count = [int]$fixture.required_input_asset_count + 1
}
$requiredDuplicateDeploy = New-DeployFixture -Name "d" -Mutate {
  param($fixture)
  $fixture.required_input_assets = @($fixture.required_input_assets) + @($fixture.required_input_assets[0])
  $fixture.required_input_asset_count = @($fixture.required_input_assets).Count
}
$requiredUnsafeDeploy = New-DeployFixture -Name "u" -Mutate {
  param($fixture)
  $fixture.required_input_assets[0].bundle_path = "../escape.png"
}
$requiredNotInFilesDeploy = New-DeployFixture -Name "n" -Mutate {
  param($fixture)
  $fixture.required_input_assets[0].bundle_path = "runtime_inputs/missing.png"
}
$requiredHashMismatchDeploy = New-DeployFixture -Name "h" -Mutate {
  param($fixture)
  $fixture.required_input_assets[0].sha256 = "0" * 64
}

$tests = @()
$tests += Invoke-Case -Name "valid_publish_strict_pass" -PublishFile $publishPath -ExpectedExitCode 0 -ExpectedResult "pass_local_only" -ExpectedFailureCategory $null -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "valid_live_publish_strict_pass" -PublishFile $livePublishPath -ExpectedExitCode 0 -ExpectedResult "pass_local_only" -ExpectedFailureCategory $null -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "failed_live_upload_rejected" -PublishFile $failedLivePublishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_linkage_mismatch" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "missing_safety_flags_rejected" -PublishFile $missingSafetyFlagsPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_linkage_mismatch" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "ec2_started_rejected" -PublishFile $ec2StartedPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_linkage_mismatch" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "generation_executed_rejected" -PublishFile $generationExecutedPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_linkage_mismatch" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "omitted_publish_strict_failure" -PublishFile $null -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "strict_warning_failure" -ExpectedPublishStatus "not_supplied" -ExpectedWarnings @("publish_evidence_not_supplied")
$tests += Invoke-Case -Name "missing_publish_structured_failure" -PublishFile $missingPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_evidence_missing" -ExpectedPublishStatus "missing"
$tests += Invoke-Case -Name "invalid_publish_json_structured_failure" -PublishFile $invalidJsonPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_evidence_json_invalid" -ExpectedPublishStatus "invalid_json"
$tests += Invoke-Case -Name "invalid_publish_payload_structured_failure" -PublishFile $invalidPayloadPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_evidence_payload_invalid" -ExpectedPublishStatus "invalid_payload"
$tests += Invoke-Case -Name "mismatched_publish_linkage_failure" -PublishFile $mismatchPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "publish_linkage_mismatch" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "required_input_assets_missing_rejected" -DeployFile $requiredMissingDeploy -PublishFile $publishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "required_input_assets_missing" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "required_input_assets_count_mismatch_rejected" -DeployFile $requiredCountMismatchDeploy -PublishFile $publishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "required_input_assets_count_mismatch" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "required_input_assets_duplicate_rejected" -DeployFile $requiredDuplicateDeploy -PublishFile $publishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "required_input_assets_duplicate" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "required_input_assets_unsafe_path_rejected" -DeployFile $requiredUnsafeDeploy -PublishFile $publishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "required_input_assets_path_unsafe" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "required_input_assets_not_in_bundle_rejected" -DeployFile $requiredNotInFilesDeploy -PublishFile $publishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "required_input_assets_not_in_bundle_files" -ExpectedPublishStatus "parsed"
$tests += Invoke-Case -Name "required_input_assets_hash_mismatch_rejected" -DeployFile $requiredHashMismatchDeploy -PublishFile $publishPath -ExpectedExitCode 1 -ExpectedResult "fail" -ExpectedFailureCategory "required_input_assets_hash_mismatch" -ExpectedPublishStatus "parsed"

$failed = @($tests | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "run_package_deploy_bundle_consistency_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  failure_category = $(if ($failed.Count -eq 0) { $null } else { "regression_case_failed" })
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  validator = ConvertTo-ProjectRelativePath -Path $validator
  run_package_manifest = ConvertTo-ProjectRelativePath -Path $runPath
  deploy_bundle_manifest = ConvertTo-ProjectRelativePath -Path $deployPath
  publish_evidence = ConvertTo-ProjectRelativePath -Path $publishPath
  lane_id = [string](Get-Content -LiteralPath $runPath -Raw | ConvertFrom-Json).lane_id
  test_count = $tests.Count
  passing_test_count = @($tests | Where-Object { [string]$_.result -eq "pass" }).Count
  failed_test_count = $failed.Count
  tests = @($tests)
  target_runtime_proof = $false
  certification_claimed = $false
  boundary = "Local validator regression only. No upload, EC2, ComfyUI generation, target-runtime proof, or certification occurred."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_RUN_PACKAGE_DEPLOY_BUNDLE_CONSISTENCY_REGRESSION_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $outPath)) | Out-Null
[System.IO.File]::WriteAllText($outPath, ($record | ConvertTo-Json -Depth 20) + [Environment]::NewLine, $utf8NoBom)

$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd("\") + "\"
$tempResolved = [System.IO.Path]::GetFullPath($tempRoot)
if ($tempResolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $tempResolved -Recurse -Force
}

$record | ConvertTo-Json -Depth 20
if ($failed.Count -gt 0) { exit 1 }
exit 0
