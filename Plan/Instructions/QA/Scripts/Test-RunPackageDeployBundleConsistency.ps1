<#
.SYNOPSIS
Validates a current workflow run package, deploy bundle, and optional publish dry-run as one local contract.

.DESCRIPTION
Detects packaged-source drift even when a later deploy manifest records clean
Git state. The validator is read-only except for its report and never contacts
AWS, GitHub, Civitai, ComfyUI, or EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$RunPackageManifestFile,
  [Parameter(Mandatory=$true)][string]$DeployBundleManifestFile,
  [string]$PublishEvidenceFile = "",
  [string]$OutFile = "",
  [switch]$Strict
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

function Get-Sha256 {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected, [string]$FailureCategory)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
    failure_category = $(if ($Passed) { $null } else { $FailureCategory })
  }
}

function Test-FlagFalse {
  param([object]$Payload, [string]$Name)
  return ($null -ne $Payload.PSObject.Properties[$Name] -and -not [bool]$Payload.$Name)
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$runManifestPath = Resolve-ProjectPath -Path $RunPackageManifestFile
$deployManifestPath = Resolve-ProjectPath -Path $DeployBundleManifestFile
foreach ($required in @($runManifestPath, $deployManifestPath)) {
  if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
    throw "Required manifest missing: $required"
  }
}
$publishEvidenceSupplied = -not [string]::IsNullOrWhiteSpace($PublishEvidenceFile)
$publishPath = $null
$publishInputStatus = "not_supplied"
$publishReadError = $null
if ($publishEvidenceSupplied) {
  $publishPath = Resolve-ProjectPath -Path $PublishEvidenceFile
  if (-not (Test-Path -LiteralPath $publishPath -PathType Leaf)) {
    $publishInputStatus = "missing"
  } else {
    $publishInputStatus = "present"
  }
}

$run = Get-Content -LiteralPath $runManifestPath -Raw | ConvertFrom-Json
$deploy = Get-Content -LiteralPath $deployManifestPath -Raw | ConvertFrom-Json
$publish = $null
if ($publishInputStatus -eq "present") {
  try {
    $parsedPublish = Get-Content -LiteralPath $publishPath -Raw | ConvertFrom-Json
    if ($null -eq $parsedPublish -or $parsedPublish -isnot [pscustomobject]) {
      $publishInputStatus = "invalid_payload"
      $publishReadError = "Publish evidence JSON must contain one object."
    } else {
      $publish = $parsedPublish
      $publishInputStatus = "parsed"
    }
  } catch {
    $publishInputStatus = "invalid_json"
    $publishReadError = "Publish evidence is not valid JSON."
  }
}
$runDir = Split-Path -Parent $runManifestPath
$deployDir = Split-Path -Parent $deployManifestPath
$contentRoot = Join-Path $deployDir "content"
$checks = [System.Collections.Generic.List[object]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

[void]$checks.Add((New-Check -Name "run_package_local_contract" -Passed (
  [string]$run.result -eq "pass_local_only" -and [bool]$run.local_only -and
  (Test-FlagFalse -Payload $run -Name "aws_contacted") -and
  (Test-FlagFalse -Payload $run -Name "github_api_contacted") -and
  (Test-FlagFalse -Payload $run -Name "civitai_contacted") -and
  (Test-FlagFalse -Payload $run -Name "comfyui_contacted") -and
  (Test-FlagFalse -Payload $run -Name "ec2_started") -and
  (Test-FlagFalse -Payload $run -Name "generation_executed")
) -Observed ([ordered]@{ result=$run.result; local_only=$run.local_only; lane_id=$run.lane_id }) -Expected "pass_local_only with all contact/execution flags false" -FailureCategory "run_package_contract_invalid"))

$packagedRows = @()
foreach ($row in @($run.packaged_files)) {
  $sourcePath = Resolve-ProjectPath -Path ([string]$row.source)
  $packagedPath = Resolve-ProjectPath -Path ([string]$row.packaged)
  $sourceExists = Test-Path -LiteralPath $sourcePath -PathType Leaf
  $packagedExists = Test-Path -LiteralPath $packagedPath -PathType Leaf
  $sourceHash = if ($sourceExists) { Get-Sha256 -Path $sourcePath } else { "" }
  $packagedHash = if ($packagedExists) { Get-Sha256 -Path $packagedPath } else { "" }
  $profileModified = ($null -ne $row.PSObject.Properties["profile_modified"] -and [bool]$row.profile_modified)
  $recordedHash = ([string]$row.sha256).ToLowerInvariant()
  $packagedMatches = ($packagedExists -and $packagedHash -eq $recordedHash)
  $sourceMatches = ($sourceExists -and ($profileModified -or $sourceHash -eq $recordedHash))
  $declaredMatchConsistent = if ($profileModified) {
    -not [bool]$row.source_hash_match
  } else {
    [bool]$row.source_hash_match -eq ($sourceHash -eq $packagedHash)
  }
  $passed = ($packagedMatches -and $sourceMatches -and $declaredMatchConsistent)
  $packagedRows += [pscustomobject][ordered]@{
    source = [string]$row.source
    packaged = [string]$row.packaged
    profile_modified = $profileModified
    source_exists = $sourceExists
    packaged_exists = $packagedExists
    recorded_sha256 = $recordedHash
    source_sha256 = $sourceHash
    packaged_sha256 = $packagedHash
    result = $(if ($passed) { "pass" } else { "fail" })
  }
  [void]$checks.Add((New-Check -Name "packaged_source:$([string]$row.source)" -Passed $passed -Observed $packagedRows[-1] -Expected "current source and packaged file match recorded hash, except explicit profile modification" -FailureCategory "packaged_source_drift"))
}

$generatedRows = @()
foreach ($row in @($run.generated_files)) {
  $path = Resolve-ProjectPath -Path ([string]$row.path)
  $exists = Test-Path -LiteralPath $path -PathType Leaf
  $observedHash = if ($exists) { Get-Sha256 -Path $path } else { "" }
  $recordedHash = ([string]$row.sha256).ToLowerInvariant()
  $passed = ($exists -and $observedHash -eq $recordedHash)
  $generatedRows += [pscustomobject][ordered]@{
    path = [string]$row.path
    exists = $exists
    recorded_sha256 = $recordedHash
    observed_sha256 = $observedHash
    result = $(if ($passed) { "pass" } else { "fail" })
  }
  [void]$checks.Add((New-Check -Name "generated_file:$([string]$row.path)" -Passed $passed -Observed $generatedRows[-1] -Expected "generated file exists and hash matches" -FailureCategory "generated_hash_mismatch"))
}

[void]$checks.Add((New-Check -Name "deploy_bundle_local_contract" -Passed (
  [string]$deploy.result -eq "pass_local_only" -and [bool]$deploy.local_only -and
  [bool]$deploy.source_git_clean -and [int]$deploy.source_git_status_count -eq 0 -and
  (Test-FlagFalse -Payload $deploy -Name "aws_contacted") -and
  (Test-FlagFalse -Payload $deploy -Name "github_api_contacted") -and
  (Test-FlagFalse -Payload $deploy -Name "civitai_contacted") -and
  (Test-FlagFalse -Payload $deploy -Name "comfyui_contacted") -and
  (Test-FlagFalse -Payload $deploy -Name "ec2_started") -and
  (Test-FlagFalse -Payload $deploy -Name "generation_executed")
) -Observed ([ordered]@{ result=$deploy.result; source_git_head=$deploy.source_git_head; source_git_clean=$deploy.source_git_clean; source_git_status_count=$deploy.source_git_status_count }) -Expected "pass_local_only clean-source bundle with all contact/execution flags false" -FailureCategory "deploy_bundle_contract_invalid"))

$normalizedDeployRun = Resolve-ProjectPath -Path ([string]$deploy.run_package_manifest)
[void]$checks.Add((New-Check -Name "lane_and_run_package_linkage" -Passed (
  [string]$deploy.lane_id -eq [string]$run.lane_id -and
  [System.IO.Path]::GetFullPath($normalizedDeployRun).Equals([System.IO.Path]::GetFullPath($runManifestPath), [System.StringComparison]::OrdinalIgnoreCase)
) -Observed ([ordered]@{ run_lane=$run.lane_id; deploy_lane=$deploy.lane_id; supplied_run=ConvertTo-ProjectRelativePath -Path $runManifestPath; deploy_run=$deploy.run_package_manifest }) -Expected "same lane and exact run-package manifest" -FailureCategory "bundle_linkage_mismatch"))

$bundleFileRows = @()
foreach ($row in @($deploy.files)) {
  $contentPath = Join-Path $contentRoot ([string]$row.path).Replace("/", "\")
  $exists = Test-Path -LiteralPath $contentPath -PathType Leaf
  $observedHash = if ($exists) { Get-Sha256 -Path $contentPath } else { "" }
  $recordedHash = ([string]$row.sha256).ToLowerInvariant()
  $passed = ($exists -and $observedHash -eq $recordedHash)
  $bundleFileRows += [pscustomobject][ordered]@{
    path = [string]$row.path
    exists = $exists
    recorded_sha256 = $recordedHash
    observed_sha256 = $observedHash
    result = $(if ($passed) { "pass" } else { "fail" })
  }
  [void]$checks.Add((New-Check -Name "bundle_content:$([string]$row.path)" -Passed $passed -Observed $bundleFileRows[-1] -Expected "bundle content exists and hash matches manifest" -FailureCategory "bundle_content_hash_mismatch"))
}

$runManifestRepoPath = ConvertTo-ProjectRelativePath -Path $runManifestPath
$runIncluded = @($deploy.files | Where-Object { [string]$_.path -eq $runManifestRepoPath }).Count -eq 1
[void]$checks.Add((New-Check -Name "bundle_contains_selected_run_manifest" -Passed $runIncluded -Observed $runManifestRepoPath -Expected "exact selected run manifest appears once in bundle files" -FailureCategory "bundle_linkage_mismatch"))

$zipPath = Join-Path $deployDir ([string]$deploy.bundle_zip)
$zipExists = Test-Path -LiteralPath $zipPath -PathType Leaf
$zipHash = if ($zipExists) { Get-Sha256 -Path $zipPath } else { "" }
$zipSize = if ($zipExists) { (Get-Item -LiteralPath $zipPath).Length } else { 0 }
[void]$checks.Add((New-Check -Name "bundle_zip_hash_and_size" -Passed (
  $zipExists -and $zipHash -eq ([string]$deploy.bundle_zip_sha256).ToLowerInvariant() -and
  $zipSize -eq [int64]$deploy.bundle_zip_size_bytes -and (Split-Path -Leaf $zipPath) -eq [string]$deploy.bundle_zip
) -Observed ([ordered]@{ exists=$zipExists; path=$zipPath; observed_sha256=$zipHash; expected_sha256=$deploy.bundle_zip_sha256; observed_size=$zipSize; expected_size=$deploy.bundle_zip_size_bytes }) -Expected "ZIP exists and filename/hash/size match deploy manifest" -FailureCategory "zip_hash_mismatch"))

if ($publishEvidenceSupplied) {
  $publishInputFailureCategory = switch ($publishInputStatus) {
    "missing" { "publish_evidence_missing" }
    "invalid_payload" { "publish_evidence_payload_invalid" }
    default { "publish_evidence_json_invalid" }
  }
  [void]$checks.Add((New-Check -Name "publish_evidence_input" -Passed ($publishInputStatus -eq "parsed") -Observed ([ordered]@{
    status = $publishInputStatus
    path = ConvertTo-ProjectRelativePath -Path $publishPath
    read_error = $publishReadError
  }) -Expected "supplied publish evidence exists and parses as JSON" -FailureCategory $publishInputFailureCategory))
}

if ($null -ne $publish) {
  $bundleUriLeaf = [System.IO.Path]::GetFileName(([string]$publish.s3_bundle_uri).Replace("/", "\"))
  $manifestUriLeaf = [System.IO.Path]::GetFileName(([string]$publish.s3_manifest_uri).Replace("/", "\"))
  $publishDryRunValid = (
    [string]$publish.result -eq "dry_run_ready_to_upload" -and [bool]$publish.local_only -and
    (Test-FlagFalse -Payload $publish -Name "aws_contacted") -and
    (Test-FlagFalse -Payload $publish.upload -Name "attempted")
  )
  $publishLiveValid = (
    [string]$publish.result -eq "deploy_bundle_uploaded_to_s3" -and
    (Test-FlagFalse -Payload $publish -Name "local_only") -and
    [bool]$publish.aws_contacted -and [bool]$publish.upload.attempted -and
    [int]$publish.upload.bundle_rc -eq 0 -and [int]$publish.upload.manifest_rc -eq 0
  )
  [void]$checks.Add((New-Check -Name "publish_dry_run_linkage" -Passed (
    [string]$publish.operation -eq "publish_deploy_bundle_to_s3" -and
    ($publishDryRunValid -or $publishLiveValid) -and
    (Test-FlagFalse -Payload $publish -Name "ec2_started") -and
    (Test-FlagFalse -Payload $publish -Name "generation_executed") -and
    [string]$publish.bundle_id -eq [string]$deploy.bundle_id -and
    [string]$publish.lane_id -eq [string]$deploy.lane_id -and
    ([string]$publish.bundle_zip_sha256).ToLowerInvariant() -eq $zipHash -and
    $bundleUriLeaf -eq [string]$deploy.bundle_zip -and
    $manifestUriLeaf -eq (Split-Path -Leaf $deployManifestPath)
  ) -Observed ([ordered]@{ result=$publish.result; bundle_id=$publish.bundle_id; lane_id=$publish.lane_id; bundle_sha=$publish.bundle_zip_sha256; bundle_uri=$publish.s3_bundle_uri; manifest_uri=$publish.s3_manifest_uri; upload_attempted=$publish.upload.attempted; bundle_rc=$publish.upload.bundle_rc; manifest_rc=$publish.upload.manifest_rc }) -Expected "matching local-only dry-run or successful live S3 publish with no EC2/generation activity" -FailureCategory "publish_linkage_mismatch"))
} elseif (-not $publishEvidenceSupplied) {
  [void]$warnings.Add("publish_evidence_not_supplied")
}

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$failureCategories = @($failedChecks | ForEach-Object { [string]$_.failure_category } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
if ([bool]$deploy.source_git_clean -and @($packagedRows | Where-Object { [string]$_.result -ne "pass" }).Count -gt 0) {
  $failureCategories = @("stale_clean_git_metadata") + @($failureCategories)
}
$result = if ($failedChecks.Count -eq 0 -and (-not $Strict -or $warnings.Count -eq 0)) { "pass_local_only" } else { "fail" }
$failureCategory = if ($result -eq "pass_local_only") { $null } elseif ($failureCategories.Count -gt 0) { $failureCategories[0] } else { "strict_warning_failure" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "run_package_deploy_bundle_consistency_validation"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  failure_category = $failureCategory
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  strict = [bool]$Strict
  lane_id = [string]$run.lane_id
  run_id = [string]$run.run_id
  run_package_manifest = ConvertTo-ProjectRelativePath -Path $runManifestPath
  deploy_bundle_manifest = ConvertTo-ProjectRelativePath -Path $deployManifestPath
  publish_evidence = $(if ($null -ne $publishPath) { ConvertTo-ProjectRelativePath -Path $publishPath } else { $null })
  publish_evidence_supplied = $publishEvidenceSupplied
  publish_evidence_status = $publishInputStatus
  publish_evidence_read_error = $publishReadError
  bundle_id = [string]$deploy.bundle_id
  bundle_zip = ConvertTo-ProjectRelativePath -Path $zipPath
  bundle_zip_sha256 = $zipHash
  source_git_head = [string]$deploy.source_git_head
  source_git_clean = [bool]$deploy.source_git_clean
  packaged_file_count = @($packagedRows).Count
  packaged_files = @($packagedRows)
  generated_file_count = @($generatedRows).Count
  generated_files = @($generatedRows)
  bundle_content_file_count = @($bundleFileRows).Count
  bundle_content_files = @($bundleFileRows)
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  failure_categories = @($failureCategories)
  warnings = @($warnings)
  target_runtime_proof = $false
  certification_claimed = $false
  boundary = "Local package/deploy/publish consistency validation only. No external service was contacted and no target-runtime or certification claim is made."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_RUN_PACKAGE_DEPLOY_BUNDLE_CONSISTENCY_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $outPath)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outPath, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)
$record | ConvertTo-Json -Depth 30
if ($result -ne "pass_local_only") { exit 1 }
exit 0
