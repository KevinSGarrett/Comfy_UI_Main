<#
.SYNOPSIS
Builds a local-only pre-EC2 handoff bundle for one ControlNet lane.

.DESCRIPTION
Validates current package/deploy consistency evidence, deploy-bundle S3 publish
dry-run evidence, asset-transfer dry-run evidence, and a clean Git gate. The
script is read-only except for its report and never authorizes live execution.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$LaneId,
  [Parameter(Mandatory=$true)][string]$RunPackageManifestFile,
  [Parameter(Mandatory=$true)][string]$DeployBundleManifestFile,
  [Parameter(Mandatory=$true)][string]$PackageDeployEvidenceFile,
  [Parameter(Mandatory=$true)][string]$DeployPublishEvidenceFile,
  [Parameter(Mandatory=$true)][string]$AssetTransferEvidenceFile,
  [Parameter(Mandatory=$true)][string]$GitGateEvidenceFile,
  [string]$OutFile = "",
  [string]$MarkdownOutFile = "",
  [switch]$Execute
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

function Test-SafeLocalEvidence {
  param([object]$Payload)
  return (
    $null -ne $Payload -and [bool]$Payload.local_only -and
    (Test-FlagFalse -Payload $Payload -Name "aws_contacted") -and
    (Test-FlagFalse -Payload $Payload -Name "ec2_started") -and
    (Test-FlagFalse -Payload $Payload -Name "generation_executed")
  )
}

function Get-UriLeaf {
  param([string]$Uri)
  if ([string]::IsNullOrWhiteSpace($Uri)) { return "" }
  return [System.IO.Path]::GetFileName($Uri.Replace("/", "\"))
}

if ($Execute) {
  throw "Live execution is forbidden. This handoff bundle is local-only."
}
if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$allowedLanes = @(
  "sdxl_realvisxl_controlnet_depth_lane",
  "sdxl_realvisxl_controlnet_lineart_lane",
  "sdxl_realvisxl_controlnet_openpose_lane",
  "sdxl_realvisxl_controlnet_normal_lane"
)
$supportedLane = $LaneId -in $allowedLanes

$paths = [ordered]@{
  run_manifest = Resolve-ProjectPath -Path $RunPackageManifestFile
  deploy_manifest = Resolve-ProjectPath -Path $DeployBundleManifestFile
  package_deploy_evidence = Resolve-ProjectPath -Path $PackageDeployEvidenceFile
  deploy_publish_evidence = Resolve-ProjectPath -Path $DeployPublishEvidenceFile
  asset_transfer_evidence = Resolve-ProjectPath -Path $AssetTransferEvidenceFile
  git_gate_evidence = Resolve-ProjectPath -Path $GitGateEvidenceFile
}
$missingPaths = @($paths.Values | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($missingPaths.Count -gt 0) {
  throw "Required handoff input missing: $($missingPaths -join ', ')"
}

$run = Get-Content -LiteralPath $paths.run_manifest -Raw | ConvertFrom-Json
$deploy = Get-Content -LiteralPath $paths.deploy_manifest -Raw | ConvertFrom-Json
$packageEvidence = Get-Content -LiteralPath $paths.package_deploy_evidence -Raw | ConvertFrom-Json
$publishEvidence = Get-Content -LiteralPath $paths.deploy_publish_evidence -Raw | ConvertFrom-Json
$assetEvidence = Get-Content -LiteralPath $paths.asset_transfer_evidence -Raw | ConvertFrom-Json
$gitGate = Get-Content -LiteralPath $paths.git_gate_evidence -Raw | ConvertFrom-Json

$currentHead = (& git -C $ProjectRoot rev-parse HEAD 2>$null).Trim()
$originMain = (& git -C $ProjectRoot rev-parse origin/main 2>$null).Trim()
$porcelain = @(& git -C $ProjectRoot status --porcelain=v1 --untracked-files=all)
$porcelainCount = @($porcelain | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count
$deployDir = Split-Path -Parent $paths.deploy_manifest
$bundleZipPath = Join-Path $deployDir ([string]$deploy.bundle_zip)
$bundleZipExists = Test-Path -LiteralPath $bundleZipPath -PathType Leaf
$bundleZipHash = if ($bundleZipExists) { (Get-FileHash -Algorithm SHA256 -LiteralPath $bundleZipPath).Hash.ToLowerInvariant() } else { "" }

$checks = [System.Collections.Generic.List[object]]::new()
[void]$checks.Add((New-Check -Name "supported_controlnet_lane" -Passed $supportedLane -Observed $LaneId -Expected $allowedLanes -FailureCategory "unsupported_controlnet_lane"))

$laneIds = [ordered]@{
  requested = $LaneId
  run_manifest = [string]$run.lane_id
  deploy_manifest = [string]$deploy.lane_id
  package_deploy_evidence = [string]$packageEvidence.lane_id
  deploy_publish_evidence = [string]$publishEvidence.lane_id
  asset_transfer_evidence = [string]$assetEvidence.lane_id
}
$laneMatch = ($supportedLane -and @($laneIds.Values | Where-Object { [string]$_ -ne $LaneId }).Count -eq 0)
[void]$checks.Add((New-Check -Name "lane_identity_alignment" -Passed $laneMatch -Observed $laneIds -Expected "all lane_id values equal requested lane" -FailureCategory "lane_identity_mismatch"))

$resolvedPackageRun = Resolve-ProjectPath -Path ([string]$packageEvidence.run_package_manifest)
$resolvedPackageDeploy = Resolve-ProjectPath -Path ([string]$packageEvidence.deploy_bundle_manifest)
$packageContractPass = (
  [string]$packageEvidence.result -eq "pass_local_only" -and [int]$packageEvidence.failed_check_count -eq 0 -and
  (Test-SafeLocalEvidence -Payload $packageEvidence) -and
  (Test-FlagFalse -Payload $packageEvidence -Name "target_runtime_proof") -and
  (Test-FlagFalse -Payload $packageEvidence -Name "certification_claimed") -and
  [System.IO.Path]::GetFullPath($resolvedPackageRun).Equals([System.IO.Path]::GetFullPath($paths.run_manifest), [System.StringComparison]::OrdinalIgnoreCase) -and
  [System.IO.Path]::GetFullPath($resolvedPackageDeploy).Equals([System.IO.Path]::GetFullPath($paths.deploy_manifest), [System.StringComparison]::OrdinalIgnoreCase)
)
[void]$checks.Add((New-Check -Name "package_deploy_contract" -Passed $packageContractPass -Observed ([ordered]@{
  result=$packageEvidence.result
  failed_check_count=$packageEvidence.failed_check_count
  run_package_manifest=$packageEvidence.run_package_manifest
  deploy_bundle_manifest=$packageEvidence.deploy_bundle_manifest
}) -Expected "matching pass_local_only package/deploy evidence with zero failures" -FailureCategory "package_deploy_contract_invalid"))

$deployContractPass = (
  [string]$deploy.result -eq "pass_local_only" -and [bool]$deploy.local_only -and
  [bool]$deploy.source_git_clean -and [int]$deploy.source_git_status_count -eq 0 -and
  [string]$deploy.lane_id -eq $LaneId -and $bundleZipExists -and
  $bundleZipHash -eq ([string]$deploy.bundle_zip_sha256).ToLowerInvariant() -and
  (Test-FlagFalse -Payload $deploy -Name "aws_contacted") -and
  (Test-FlagFalse -Payload $deploy -Name "ec2_started") -and
  (Test-FlagFalse -Payload $deploy -Name "generation_executed")
)
[void]$checks.Add((New-Check -Name "deploy_bundle_contract" -Passed $deployContractPass -Observed ([ordered]@{
  result=$deploy.result
  bundle_id=$deploy.bundle_id
  source_git_head=$deploy.source_git_head
  source_git_clean=$deploy.source_git_clean
  source_git_status_count=$deploy.source_git_status_count
  bundle_zip_sha256=$bundleZipHash
}) -Expected "clean local deploy bundle with current ZIP hash" -FailureCategory "deploy_bundle_contract_invalid"))

$publishContractPass = (
  [string]$publishEvidence.operation -eq "publish_deploy_bundle_to_s3" -and
  [string]$publishEvidence.result -eq "dry_run_ready_to_upload" -and
  (Test-SafeLocalEvidence -Payload $publishEvidence) -and
  -not [bool]$publishEvidence.upload.attempted -and
  [string]$publishEvidence.bundle_id -eq [string]$deploy.bundle_id -and
  ([string]$publishEvidence.bundle_zip_sha256).ToLowerInvariant() -eq $bundleZipHash -and
  (Get-UriLeaf -Uri ([string]$publishEvidence.s3_bundle_uri)) -eq [string]$deploy.bundle_zip -and
  (Get-UriLeaf -Uri ([string]$publishEvidence.s3_manifest_uri)) -eq (Split-Path -Leaf $paths.deploy_manifest)
)
[void]$checks.Add((New-Check -Name "deploy_publish_dry_run_contract" -Passed $publishContractPass -Observed ([ordered]@{
  result=$publishEvidence.result
  bundle_id=$publishEvidence.bundle_id
  bundle_zip_sha256=$publishEvidence.bundle_zip_sha256
  upload_attempted=$publishEvidence.upload.attempted
  s3_bundle_uri=$publishEvidence.s3_bundle_uri
}) -Expected "matching no-upload deploy-bundle publish dry run" -FailureCategory "deploy_publish_contract_invalid"))

$assetContractPass = (
  [string]$assetEvidence.result -eq "pass_local_only_controlnet_asset_transfer_dry_run_bundle_validated" -and
  [int]$assetEvidence.child_artifact_count -eq 6 -and [int]$assetEvidence.failed_check_count -eq 0 -and
  (Test-SafeLocalEvidence -Payload $assetEvidence) -and
  (Test-FlagFalse -Payload $assetEvidence -Name "target_runtime_proof") -and
  (Test-FlagFalse -Payload $assetEvidence -Name "certification_claimed") -and
  (Test-FlagFalse -Payload $assetEvidence -Name "promotion_allowed") -and
  (Test-FlagFalse -Payload $assetEvidence -Name "execute_allowed_now")
)
[void]$checks.Add((New-Check -Name "asset_transfer_dry_run_contract" -Passed $assetContractPass -Observed ([ordered]@{
  result=$assetEvidence.result
  child_artifact_count=$assetEvidence.child_artifact_count
  failed_check_count=$assetEvidence.failed_check_count
  checkpoint_s3_uri=$assetEvidence.checkpoint_s3_uri
  controlnet_s3_uri=$assetEvidence.controlnet_s3_uri
  input_s3_uri=$assetEvidence.input_s3_uri
}) -Expected "matching six-child local-only asset-transfer dry-run bundle" -FailureCategory "asset_transfer_contract_invalid"))

$gitGatePass = (
  [string]$gitGate.result -eq "pass_git_checkpoint_ready" -and
  [bool]$gitGate.clean_worktree -and [bool]$gitGate.local_matches_origin -and
  [int]$gitGate.porcelain_count -eq 0 -and [int]$gitGate.blocked_changed_path_count -eq 0 -and
  [int]$gitGate.staged_secret_match_count -eq 0 -and
  [string]$gitGate.head -eq [string]$gitGate.origin_main -and
  [string]$gitGate.head -eq $currentHead -and $currentHead -eq $originMain -and $porcelainCount -eq 0
)
[void]$checks.Add((New-Check -Name "current_clean_git_gate" -Passed $gitGatePass -Observed ([ordered]@{
  gate_result=$gitGate.result
  gate_head=$gitGate.head
  gate_origin_main=$gitGate.origin_main
  current_head=$currentHead
  current_origin_main=$originMain
  gate_clean_worktree=$gitGate.clean_worktree
  current_porcelain_count=$porcelainCount
  blocked_changed_path_count=$gitGate.blocked_changed_path_count
  staged_secret_match_count=$gitGate.staged_secret_match_count
}) -Expected "supplied clean gate and current repository both clean at identical HEAD/origin" -FailureCategory "git_gate_not_current_clean"))

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$failureCategories = @($failedChecks | ForEach-Object { [string]$_.failure_category } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$result = if ($failedChecks.Count -eq 0) { "pass_local_only_controlnet_pre_ec2_handoff_ready_live_blocked" } else { "fail_controlnet_pre_ec2_handoff" }
$failureCategory = if ($failedChecks.Count -eq 0) { $null } else { $failureCategories[0] }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "controlnet_lane_pre_ec2_handoff_bundle"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  tracker_id = "WO-W66-$($LaneId.ToUpperInvariant().Replace('_','-'))-TARGET-RUNTIME-PROOF"
  lane_id = $LaneId
  result = $result
  failure_category = $failureCategory
  local_only = $true
  aws_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  jira_mutated = $false
  target_runtime_proof = $false
  certification_claimed = $false
  promotion_allowed = $false
  execute_allowed_now = $false
  target_runtime_launch_allowed = $false
  current_git_head = $currentHead
  current_origin_main = $originMain
  current_porcelain_count = $porcelainCount
  run_package_manifest = ConvertTo-ProjectRelativePath -Path $paths.run_manifest
  deploy_bundle_manifest = ConvertTo-ProjectRelativePath -Path $paths.deploy_manifest
  package_deploy_evidence = ConvertTo-ProjectRelativePath -Path $paths.package_deploy_evidence
  deploy_publish_evidence = ConvertTo-ProjectRelativePath -Path $paths.deploy_publish_evidence
  asset_transfer_evidence = ConvertTo-ProjectRelativePath -Path $paths.asset_transfer_evidence
  git_gate_evidence = ConvertTo-ProjectRelativePath -Path $paths.git_gate_evidence
  bundle_id = [string]$deploy.bundle_id
  bundle_zip_sha256 = $bundleZipHash
  deploy_bundle_s3_uri = [string]$publishEvidence.s3_bundle_uri
  checkpoint_s3_uri = [string]$assetEvidence.checkpoint_s3_uri
  controlnet_s3_uri = [string]$assetEvidence.controlnet_s3_uri
  input_s3_uri = [string]$assetEvidence.input_s3_uri
  check_count = $checks.Count
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  failure_categories = @($failureCategories)
  exact_blockers = @(
    "explicit_live_execution_intent_required",
    "deploy_and_asset_s3_publish_execute_proofs_missing",
    "ec2_asset_install_hash_proofs_missing",
    "target_runtime_object_info_and_static_proof_missing",
    "bounded_target_runtime_generation_missing",
    "artifact_pullback_and_strict_visual_qa_missing",
    "final_lane_certification_review_missing"
  )
  boundary = "Local ControlNet pre-EC2 handoff validation only. This does not upload, start EC2, install remotely, write active markers, execute generation, prove target runtime, promote the lane, complete Items/Tracker rows, or claim certification."
  next_action = "Keep EC2 stopped. Use this handoff only after explicit live-window selection and fresh live gates; otherwise continue local orchestration for another lane."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_CONTROLNET_PRE_EC2_HANDOFF_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($outPath, ".md")
}
$markdownPath = Resolve-ProjectPath -Path $MarkdownOutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $outPath)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $markdownPath)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outPath, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$checkLines = @($checks | ForEach-Object { "- $($_.name): $($_.result)" }) -join [Environment]::NewLine
$markdown = @"
# ControlNet Pre-EC2 Handoff Bundle

- created_at: $($record.created_at)
- lane_id: $($record.lane_id)
- result: $($record.result)
- failed_check_count: $($record.failed_check_count)
- execute_allowed_now: false
- target_runtime_launch_allowed: false
- target_runtime_proof: false
- certification_claimed: false

## Checks

$checkLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownPath, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($result -like "fail_*") { exit 2 }
exit 0
