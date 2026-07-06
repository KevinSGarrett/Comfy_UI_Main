<#
.SYNOPSIS
Builds a local-only EC2 deploy bundle for a run package matrix.

.DESCRIPTION
Creates one deploy bundle containing shared lane/runtime context, model
registry metadata, the matrix manifest, and every run package referenced by
the matrix. The bundle is prepared while EC2 is stopped. It does not contact
AWS, GitHub APIs, Civitai, ComfyUI, or EC2, and it does not execute generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RunPackageMatrixManifestFile = "runtime_artifacts\run_package_matrices\realvisxl_multisample_certification_v1\RUN_PACKAGE_MATRIX_MANIFEST.json",
  [string]$OutDir = "",
  [string]$BundleName = ""
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "Required JSON file missing: $Path" }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 30
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Get-RelativePathCompat {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$TargetPath
  )

  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator)
}

function Convert-ToRepoPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path).Replace("\", "/")
}

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Assert-UnderProject {
  param([Parameter(Mandatory=$true)][string]$Path)

  $projectFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($Path)
  if (!$targetFull.StartsWith($projectFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to package a path outside ProjectRoot: $Path"
  }
}

function Copy-BundleFile {
  param(
    [Parameter(Mandatory=$true)][string]$SourcePath,
    [Parameter(Mandatory=$true)][string]$ContentRoot,
    [System.Collections.ArrayList]$Records,
    [switch]$Required
  )

  if (!(Test-Path -LiteralPath $SourcePath)) {
    if ($Required) { throw "Bundle source file missing: $SourcePath" }
    return
  }
  Assert-UnderProject -Path $SourcePath
  $repoPath = Convert-ToRepoPath -Path $SourcePath
  $destination = Join-Path $ContentRoot $repoPath.Replace("/", "\")
  $destinationDir = Split-Path -Parent $destination
  if (![string]::IsNullOrWhiteSpace($destinationDir)) {
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
  }
  Copy-Item -LiteralPath $SourcePath -Destination $destination -Force
  [void]$Records.Add([ordered]@{
    path = $repoPath
    size_bytes = (Get-Item -LiteralPath $destination).Length
    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
  })
}

function Copy-BundleDirectory {
  param(
    [Parameter(Mandatory=$true)][string]$SourceDir,
    [Parameter(Mandatory=$true)][string]$ContentRoot,
    [System.Collections.ArrayList]$Records,
    [switch]$Required
  )

  if (!(Test-Path -LiteralPath $SourceDir)) {
    if ($Required) { throw "Bundle source directory missing: $SourceDir" }
    return
  }
  Assert-UnderProject -Path $SourceDir
  foreach ($file in @(Get-ChildItem -LiteralPath $SourceDir -Recurse -File)) {
    Copy-BundleFile -SourcePath $file.FullName -ContentRoot $ContentRoot -Records $Records -Required
  }
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$RunPackageMatrixManifestFile = Resolve-ProjectPath -Path $RunPackageMatrixManifestFile
Assert-UnderProject -Path $RunPackageMatrixManifestFile
$matrix = Read-JsonFile -Path $RunPackageMatrixManifestFile
if ([string]$matrix.result -ne "pass_local_only") {
  throw "Run package matrix result must be pass_local_only: $RunPackageMatrixManifestFile"
}

$laneId = [string]$matrix.lane_id
if ([string]::IsNullOrWhiteSpace($laneId)) {
  throw "Matrix manifest does not define lane_id."
}

$samples = @($matrix.samples)
if ($samples.Count -eq 0) {
  throw "Matrix manifest contains no samples."
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($BundleName)) {
  $BundleName = "deploy_bundle_matrix_$($matrix.matrix_id)_$stamp"
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $ProjectRoot "runtime_artifacts\deploy_bundles\$BundleName"
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
$contentRoot = Join-Path $OutDir "content"
New-Item -ItemType Directory -Force -Path $contentRoot | Out-Null

$records = New-Object System.Collections.ArrayList
foreach ($requiredFile in @(
  "README.md",
  "PROJECT_ROOT_MANIFEST.json",
  "Workflows/base_generation/ACTIVE_LANES.json",
  "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
)) {
  Copy-BundleFile -SourcePath (Resolve-ProjectPath -Path $requiredFile) -ContentRoot $contentRoot -Records $records -Required
}

Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Workflows/base_generation/$laneId") -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/$laneId") -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Plan/Registries/Models") -ContentRoot $contentRoot -Records $records
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "configs/ec2") -ContentRoot $contentRoot -Records $records
Copy-BundleFile -SourcePath $RunPackageMatrixManifestFile -ContentRoot $contentRoot -Records $records -Required
$matrixSourceFile = Resolve-ProjectPath -Path ([string]$matrix.matrix_file)
Copy-BundleFile -SourcePath $matrixSourceFile -ContentRoot $contentRoot -Records $records -Required

$packageSummaries = @()
foreach ($sample in $samples) {
  $manifestPath = Resolve-ProjectPath -Path ([string]$sample.manifest_path)
  Assert-UnderProject -Path $manifestPath
  $package = Read-JsonFile -Path $manifestPath
  if ([string]$package.result -ne "pass_local_only") {
    throw "Sample run package is not pass_local_only: $manifestPath"
  }
  if ([string]$package.lane_id -ne $laneId) {
    throw "Sample run package lane '$($package.lane_id)' does not match matrix lane '$laneId'."
  }
  Copy-BundleDirectory -SourceDir (Split-Path -Parent $manifestPath) -ContentRoot $contentRoot -Records $records -Required
  if ($package.prompt_profile -and $package.prompt_profile.path) {
    Copy-BundleFile -SourcePath (Resolve-ProjectPath -Path ([string]$package.prompt_profile.path)) -ContentRoot $contentRoot -Records $records -Required
  }
  $packageSummaries += [ordered]@{
    profile_id = [string]$sample.profile_id
    run_id = [string]$sample.run_id
    manifest_path = Convert-ToRepoPath -Path $manifestPath
    prompt_profile_id = [string]$package.prompt_profile.profile_id
    prompt_request_sha256 = [string]$package.prompt_request.sha256
    route_result = [string]$package.route_gate.result
    route_selected_lane_id = [string]$package.route_gate.selected_lane_id
  }
}

$gitHead = $null
$gitStatus = @()
try {
  $gitHead = (git -C $ProjectRoot rev-parse HEAD 2>$null | Select-Object -First 1)
  $gitStatus = @(git -C $ProjectRoot status --porcelain 2>$null)
} catch {
  $gitHead = $null
  $gitStatus = @("git_status_unavailable")
}

$manifest = [ordered]@{
  schema_version = "1.0"
  bundle_id = $BundleName
  bundle_type = "run_package_matrix_deploy_bundle"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  lane_id = $laneId
  matrix_id = [string]$matrix.matrix_id
  run_package_matrix_manifest = Convert-ToRepoPath -Path $RunPackageMatrixManifestFile
  sample_count = $samples.Count
  sample_packages = $packageSummaries
  source_git_head = $gitHead
  source_git_clean = (@($gitStatus).Count -eq 0)
  source_git_status_count = @($gitStatus).Count
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  cost_controls = [ordered]@{
    prepared_while_ec2_stopped = $true
    git_lfs_required_by_bundle = $false
    direct_ec2_runtime_proof_required = $true
    direct_ec2_runtime_proof_reason = "Matrix deploy bundles reduce EC2 sync time but do not replace target EC2 A10G object-info, model path/hash, generation, pullback, and whole-image QA proof."
  }
  files = @($records | Sort-Object path)
  file_count = @($records).Count
  result = "pass_local_only"
  next_action = "Upload this matrix bundle to S3 before EC2 starts; execute each sample run package in a bounded sequence, then pull back and whole-image QA every output."
}

$contentManifestPath = Join-Path $contentRoot "DEPLOY_BUNDLE_MATRIX_MANIFEST.json"
Write-JsonNoBom -Value $manifest -Path $contentManifestPath -Depth 40

$zipPath = Join-Path $OutDir "$BundleName.zip"
if (Test-Path -LiteralPath $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $contentRoot "*") -DestinationPath $zipPath -Force

$zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
$manifest.bundle_zip = Split-Path -Leaf $zipPath
$manifest.bundle_zip_sha256 = $zipHash
$manifest.bundle_zip_size_bytes = (Get-Item -LiteralPath $zipPath).Length

$sidecarManifestPath = Join-Path $OutDir "DEPLOY_BUNDLE_MATRIX_MANIFEST.json"
Write-JsonNoBom -Value $manifest -Path $sidecarManifestPath -Depth 40

$manifest | ConvertTo-Json -Depth 40
