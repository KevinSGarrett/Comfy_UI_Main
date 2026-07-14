<#
.SYNOPSIS
Builds a local-only EC2 deploy bundle from a validated workflow run package.

.DESCRIPTION
Creates a minimal ready-to-upload bundle that can be prepared while EC2 is
stopped. The bundle contains the active lane files, the selected run package,
model registry metadata, and safe runtime context. It does not contact AWS,
GitHub APIs, Civitai, ComfyUI, or start EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [ValidatePattern('^[a-z0-9_]+$')][string]$WorkflowGroup = "base_generation",
  [string]$LaneId = "",
  [string]$RunPackageManifestFile = "",
  [string]$OutDir = "",
  [string]$BundleName = "",
  [string[]]$SourceGitStatusExcludePath = @()
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
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

function ConvertTo-GitRelativePath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return "" }
  $value = ([string]$Path).Trim().Replace("\", "/")
  while ($value.StartsWith("./")) {
    $value = $value.Substring(2)
  }
  return $value.Trim("/")
}

function Test-GitPathUnderRoot {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Root
  )

  $normalizedPath = ConvertTo-GitRelativePath -Path $Path
  $normalizedRoot = ConvertTo-GitRelativePath -Path $Root
  if ([string]::IsNullOrWhiteSpace($normalizedPath) -or [string]::IsNullOrWhiteSpace($normalizedRoot)) { return $false }
  return ($normalizedPath -eq $normalizedRoot -or $normalizedPath.StartsWith("$normalizedRoot/"))
}

function Get-PorcelainPath {
  param([string]$Line)
  if ([string]::IsNullOrWhiteSpace($Line)) { return "" }
  if ($Line.Length -gt 3) { return (ConvertTo-GitRelativePath -Path $Line.Substring(3).Trim()) }
  return (ConvertTo-GitRelativePath -Path $Line.Trim())
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
    [string]$BundleRelativePath = "",
    [switch]$Required
  )

  if (!(Test-Path -LiteralPath $SourcePath)) {
    if ($Required) { throw "Bundle source file missing: $SourcePath" }
    return
  }
  Assert-UnderProject -Path $SourcePath
  $repoPath = $(if ([string]::IsNullOrWhiteSpace($BundleRelativePath)) { Convert-ToRepoPath -Path $SourcePath } else { $BundleRelativePath.Replace("\", "/").TrimStart("/") })
  if ([string]::IsNullOrWhiteSpace($repoPath) -or [System.IO.Path]::IsPathRooted($repoPath) -or @($repoPath.Split("/") | Where-Object { $_ -eq ".." }).Count -gt 0) {
    throw "Unsafe deploy-bundle relative path: $BundleRelativePath"
  }
  $destination = Join-Path $ContentRoot $repoPath.Replace("/", "\")
  $destinationDir = Split-Path -Parent $destination
  if (![string]::IsNullOrWhiteSpace($destinationDir)) {
    $null = New-Item -ItemType Directory -Force -Path $destinationDir
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

function Find-RunPackageManifest {
  param([string]$ExpectedLaneId)

  $packageRoot = Join-Path $ProjectRoot "runtime_artifacts\run_packages"
  if (!(Test-Path -LiteralPath $packageRoot)) { return $null }
  foreach ($candidate in @(Get-ChildItem -LiteralPath $packageRoot -Recurse -Filter "RUN_PACKAGE_MANIFEST.json" -File | Sort-Object LastWriteTimeUtc -Descending)) {
    try {
      $manifest = Read-JsonFile -Path $candidate.FullName
      if (([string]$manifest.result -eq "pass_local_only") -and
          ([string]::IsNullOrWhiteSpace($ExpectedLaneId) -or [string]$manifest.lane_id -eq $ExpectedLaneId)) {
        return $candidate.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

$activeLanesPath = Join-Path $ProjectRoot "Workflows\$WorkflowGroup\ACTIVE_LANES.json"
$activeLanes = Read-JsonFile -Path $activeLanesPath
$orderedLanes = @($activeLanes.lanes | Sort-Object order)
if ($orderedLanes.Count -eq 0) {
  throw "ACTIVE_LANES.json contains no lanes."
}

if ([string]::IsNullOrWhiteSpace($LaneId)) {
  $LaneId = [string]$orderedLanes[0].lane_id
}

$selectedLane = @($orderedLanes | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)
if ($selectedLane.Count -eq 0) {
  throw "Lane is not listed in ACTIVE_LANES.json: $LaneId"
}
$selectedLane = $selectedLane[0]

if ([string]::IsNullOrWhiteSpace($RunPackageManifestFile)) {
  $RunPackageManifestFile = Find-RunPackageManifest -ExpectedLaneId $LaneId
}
if ([string]::IsNullOrWhiteSpace($RunPackageManifestFile)) {
  throw "No passing run package manifest found for lane: $LaneId"
}
$RunPackageManifestFile = Resolve-ProjectPath -Path $RunPackageManifestFile
Assert-UnderProject -Path $RunPackageManifestFile
$runPackage = Read-JsonFile -Path $RunPackageManifestFile
if ([string]$runPackage.result -ne "pass_local_only") {
  throw "Run package manifest result must be pass_local_only: $RunPackageManifestFile"
}
if ([string]$runPackage.lane_id -ne $LaneId) {
  throw "Run package lane '$($runPackage.lane_id)' does not match requested lane '$LaneId'."
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($BundleName)) {
  $BundleName = "deploy_bundle_$($LaneId)_$stamp"
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $ProjectRoot "runtime_artifacts\deploy_bundles\$BundleName"
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
$contentRoot = Join-Path $OutDir "content"
$null = New-Item -ItemType Directory -Force -Path $contentRoot

$records = New-Object System.Collections.ArrayList

foreach ($requiredFile in @(
  "README.md",
  "PROJECT_ROOT_MANIFEST.json",
  "Workflows/$WorkflowGroup/ACTIVE_LANES.json",
  "Plan/07_IMPLEMENTATION/workflow_templates/$WorkflowGroup/runtime_lane_queue.json"
)) {
  Copy-BundleFile -SourcePath (Resolve-ProjectPath -Path $requiredFile) -ContentRoot $contentRoot -Records $records -Required
}

Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Workflows/$WorkflowGroup/$LaneId") -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/$WorkflowGroup/$LaneId") -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Plan/Registries/Models") -ContentRoot $contentRoot -Records $records
Copy-BundleDirectory -SourceDir (Split-Path -Parent $RunPackageManifestFile) -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "configs/ec2") -ContentRoot $contentRoot -Records $records

if ($runPackage.prompt_profile -and $runPackage.prompt_profile.path) {
  Copy-BundleFile -SourcePath (Resolve-ProjectPath -Path ([string]$runPackage.prompt_profile.path)) -ContentRoot $contentRoot -Records $records
}

$laneRuntimeRequirementsPath = Resolve-ProjectPath -Path "Workflows/$WorkflowGroup/$LaneId/runtime_requirements.json"
$laneRuntimeRequirements = Read-JsonFile -Path $laneRuntimeRequirementsPath
$laneWorkflowPath = Resolve-ProjectPath -Path "Workflows/$WorkflowGroup/$LaneId/workflow.api.json"
$laneWorkflow = Read-JsonFile -Path $laneWorkflowPath
$workflowInputGraph = $laneWorkflow
$workflowInputSource = "lane_workflow"
$runPromptRequestPath = Join-Path (Split-Path -Parent $RunPackageManifestFile) "prompt_request.json"
if (Test-Path -LiteralPath $runPromptRequestPath -PathType Leaf) {
  $runPromptRequest = Read-JsonFile -Path $runPromptRequestPath
  if ($null -eq $runPromptRequest.PSObject.Properties["prompt"] -or $null -eq $runPromptRequest.prompt) {
    throw "Run package prompt_request.json does not contain a prompt graph: $runPromptRequestPath"
  }
  $recordedPromptRequestHash = ([string]$runPackage.prompt_request.sha256).Trim().ToLowerInvariant()
  $actualPromptRequestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $runPromptRequestPath).Hash.ToLowerInvariant()
  if ($recordedPromptRequestHash -notmatch '^[0-9a-f]{64}$' -or $actualPromptRequestHash -cne $recordedPromptRequestHash) {
    throw "Run package prompt_request.json hash mismatch: expected $recordedPromptRequestHash observed $actualPromptRequestHash"
  }
  $workflowInputGraph = $runPromptRequest.prompt
  $workflowInputSource = "run_package_prompt_request"
}

function Get-ZipEntrySha256 {
  param([Parameter(Mandatory=$true)][System.IO.Compression.ZipArchiveEntry]$Entry)

  $stream = $Entry.Open()
  $sha256 = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([System.BitConverter]::ToString($sha256.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
  } finally {
    $sha256.Dispose()
    $stream.Dispose()
  }
}

function Assert-SafeZipEntryName {
  param([Parameter(Mandatory=$true)][string]$EntryName)

  if ([string]::IsNullOrWhiteSpace($EntryName) -or
      $EntryName.Contains("\") -or
      $EntryName.StartsWith("/") -or
      $EntryName -match '^[A-Za-z]:' -or
      @($EntryName.Split("/") | Where-Object { $_ -in @("", ".", "..") }).Count -gt 0) {
    throw "Unsafe or non-portable ZIP entry name: $EntryName"
  }
}

function New-PortableZipArchive {
  param(
    [Parameter(Mandatory=$true)][string]$SourceRoot,
    [Parameter(Mandatory=$true)][string]$DestinationPath
  )

  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem

  $sourceRootFull = [System.IO.Path]::GetFullPath($SourceRoot).TrimEnd("\", "/")
  $entryNames = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
  $files = @(Get-ChildItem -LiteralPath $sourceRootFull -Recurse -File | Sort-Object FullName)
  if ($files.Count -eq 0) {
    throw "Refusing to create an empty deploy bundle ZIP: $SourceRoot"
  }

  $destinationDirectory = Split-Path -Parent $DestinationPath
  if (![string]::IsNullOrWhiteSpace($destinationDirectory)) {
    $null = New-Item -ItemType Directory -Force -Path $destinationDirectory
  }
  if (Test-Path -LiteralPath $DestinationPath) {
    Remove-Item -LiteralPath $DestinationPath -Force
  }

  $fileStream = [System.IO.File]::Open($DestinationPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
  $archive = New-Object System.IO.Compression.ZipArchive($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
  try {
    foreach ($file in $files) {
      $entryName = (Get-RelativePathCompat -BasePath $sourceRootFull -TargetPath $file.FullName).Replace("\", "/")
      Assert-SafeZipEntryName -EntryName $entryName
      if (!$entryNames.Add($entryName)) {
        throw "Duplicate normalized ZIP entry name: $entryName"
      }

      $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
      $entry.LastWriteTime = New-Object System.DateTimeOffset(1980, 1, 1, 0, 0, 0, [System.TimeSpan]::Zero)
      $inputStream = [System.IO.File]::OpenRead($file.FullName)
      $entryStream = $entry.Open()
      try {
        $inputStream.CopyTo($entryStream)
      } finally {
        $entryStream.Dispose()
        $inputStream.Dispose()
      }
    }
  } finally {
    $archive.Dispose()
    $fileStream.Dispose()
  }
}

function Assert-PortableDeployBundleZip {
  param(
    [Parameter(Mandatory=$true)][string]$ZipPath,
    [Parameter(Mandatory=$true)][object]$Manifest
  )

  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem

  $expected = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($record in @($Manifest.files)) {
    $path = ([string]$record.path).Replace("\", "/")
    Assert-SafeZipEntryName -EntryName $path
    if ($expected.ContainsKey($path)) {
      throw "Deploy manifest contains duplicate normalized path: $path"
    }
    $hash = ([string]$record.sha256).Trim().ToLowerInvariant()
    if ($hash -notmatch '^[0-9a-f]{64}$') {
      throw "Deploy manifest contains an invalid SHA-256 for: $path"
    }
    $expected.Add($path, $hash)
  }
  if ($expected.Count -ne [int]$Manifest.file_count) {
    throw "Deploy manifest file_count does not match its unique file records."
  }

  $fileStream = [System.IO.File]::OpenRead($ZipPath)
  $archive = New-Object System.IO.Compression.ZipArchive($fileStream, [System.IO.Compression.ZipArchiveMode]::Read, $false)
  $observed = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
  try {
    foreach ($entry in @($archive.Entries)) {
      $entryName = [string]$entry.FullName
      Assert-SafeZipEntryName -EntryName $entryName
      if (!$observed.Add($entryName)) {
        throw "ZIP contains duplicate normalized entry name: $entryName"
      }
      if ($entryName -eq "DEPLOY_BUNDLE_MANIFEST.json") {
        continue
      }
      if (!$expected.ContainsKey($entryName)) {
        throw "ZIP entry is not declared by the deploy manifest: $entryName"
      }
      $actualHash = Get-ZipEntrySha256 -Entry $entry
      if ($actualHash -cne $expected[$entryName]) {
        throw "ZIP entry hash does not match the deploy manifest for: $entryName"
      }
    }
  } finally {
    $archive.Dispose()
    $fileStream.Dispose()
  }

  if (!$observed.Contains("DEPLOY_BUNDLE_MANIFEST.json")) {
    throw "ZIP is missing DEPLOY_BUNDLE_MANIFEST.json."
  }
  foreach ($path in $expected.Keys) {
    if (!$observed.Contains($path)) {
      throw "Deploy manifest path is missing from ZIP: $path"
    }
  }
}
$workflowInputFilenames = @(
  $workflowInputGraph.psobject.Properties.Value |
    Where-Object { [string]$_.class_type -in @("LoadImage", "LoadImageMask") } |
    ForEach-Object { [string]$_.inputs.image } |
    Where-Object { ![string]::IsNullOrWhiteSpace($_) } |
    Sort-Object -Unique
)
$declaredInputAssets = @(
  @($laneRuntimeRequirements.required_input_assets | Where-Object { $null -ne $_ })
  @($laneRuntimeRequirements.required_inputs | Where-Object { $null -ne $_ })
)
$runPackageDir = [System.IO.Path]::GetFullPath((Split-Path -Parent $RunPackageManifestFile)).TrimEnd("\", "/")
$sourceBinding = $runPackage.prompt_profile.source_binding
$sourceBindingAvailable = ($null -ne $sourceBinding -and [bool]$sourceBinding.supplied -and [bool]$sourceBinding.valid)
$requiredInputAssets = New-Object System.Collections.ArrayList
foreach ($workflowInputFilename in $workflowInputFilenames) {
  $sourceKind = "lane_runtime_requirement"
  if ($sourceBindingAvailable -and [string]$sourceBinding.staged_filename -eq $workflowInputFilename) {
    $sourceArtifact = [string]$sourceBinding.packaged
    $filename = [string]$sourceBinding.staged_filename
    $expectedSha256 = ([string]$sourceBinding.sha256).Trim().ToLowerInvariant()
    $expectedSizeBytes = [int64]$sourceBinding.size_bytes
    if ([string]::IsNullOrWhiteSpace($sourceArtifact) -or
        [string]::IsNullOrWhiteSpace($filename) -or
        [System.IO.Path]::GetFileName($filename) -ne $filename -or
        $expectedSha256 -notmatch '^[0-9a-f]{64}$' -or
        $expectedSizeBytes -lt 1) {
      throw "Run-package source binding is incomplete or invalid for workflow input: $workflowInputFilename"
    }
    $sourcePath = Resolve-ProjectPath -Path $sourceArtifact
    $sourcePathFull = [System.IO.Path]::GetFullPath($sourcePath)
    if (!$sourcePathFull.StartsWith($runPackageDir + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Run-package source binding must remain inside its run package: $sourceArtifact"
    }
    if (!(Test-Path -LiteralPath $sourcePathFull -PathType Leaf)) {
      throw "Run-package source binding file is missing: $sourceArtifact"
    }
    $actualSizeBytes = [int64](Get-Item -LiteralPath $sourcePathFull).Length
    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePathFull).Hash.ToLowerInvariant()
    if ($actualSizeBytes -ne $expectedSizeBytes) {
      throw "Run-package source binding size mismatch for $sourceArtifact`: expected $expectedSizeBytes observed $actualSizeBytes"
    }
    if ($actualSha256 -cne $expectedSha256) {
      throw "Run-package source binding hash mismatch for $sourceArtifact`: expected $expectedSha256 observed $actualSha256"
    }
    $sourcePath = $sourcePathFull
    $sourceKind = "run_package_source_binding"
  } else {
  $matchingAssets = @($declaredInputAssets | Where-Object { [string]$_.filename -eq $workflowInputFilename })
  if ($matchingAssets.Count -ne 1) {
    throw "Workflow input must have exactly one required_input_assets entry: $workflowInputFilename (found $($matchingAssets.Count))"
  }
  $asset = $matchingAssets[0]
  $sourceArtifact = [string]$asset.source_artifact
  $filename = [string]$asset.filename
  $expectedSha256 = ([string]$asset.sha256).Trim().ToLowerInvariant()
  if ([string]::IsNullOrWhiteSpace($expectedSha256)) {
    $expectedSha256 = ([string]$asset.source_sha256).Trim().ToLowerInvariant()
  }
  if ([string]::IsNullOrWhiteSpace($sourceArtifact) -or [string]::IsNullOrWhiteSpace($filename) -or $expectedSha256 -notmatch '^[0-9a-f]{64}$') {
    throw "Lane required_input_assets entry is incomplete or has an invalid sha256: $($asset | ConvertTo-Json -Compress)"
  }
  $sourcePath = Resolve-ProjectPath -Path $sourceArtifact
  if (!(Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
    throw "Required lane input asset is missing: $sourceArtifact"
  }
  $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
  if ($actualSha256 -cne $expectedSha256) {
    throw "Required lane input asset hash mismatch for $sourceArtifact`: expected $expectedSha256 observed $actualSha256"
  }
  }
  $bundlePath = "runtime_inputs/$LaneId/$filename"
  Copy-BundleFile -SourcePath $sourcePath -ContentRoot $contentRoot -Records $records -BundleRelativePath $bundlePath -Required
  [void]$requiredInputAssets.Add([ordered]@{
    filename = $filename
    source_artifact = Convert-ToRepoPath -Path $sourcePath
    bundle_path = $bundlePath
    comfyui_input_subdir = [string]$asset.comfyui_input_subdir
    sha256 = $actualSha256
    size_bytes = (Get-Item -LiteralPath $sourcePath).Length
    source_kind = $sourceKind
  })
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
$sourceGitStatusExcludePaths = @($SourceGitStatusExcludePath | ForEach-Object { ConvertTo-GitRelativePath -Path $_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$effectiveGitStatus = @($gitStatus | Where-Object {
  $statusPath = Get-PorcelainPath -Line $_
  if ([string]::IsNullOrWhiteSpace($statusPath)) { return $true }
  foreach ($excludePath in @($sourceGitStatusExcludePaths)) {
    if (Test-GitPathUnderRoot -Path $statusPath -Root $excludePath) { return $false }
  }
  return $true
})

$manifest = [ordered]@{
  schema_version = "1.0"
  bundle_id = $BundleName
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  workflow_group = $WorkflowGroup
  lane_id = $LaneId
  run_package_manifest = Convert-ToRepoPath -Path $RunPackageManifestFile
  source_git_head = $gitHead
  source_git_clean = (@($effectiveGitStatus).Count -eq 0)
  source_git_status_count = @($effectiveGitStatus).Count
  source_git_status_all_count = @($gitStatus).Count
  source_git_status_exclude_paths = @($sourceGitStatusExcludePaths)
  source_git_status_excluded_count = (@($gitStatus).Count - @($effectiveGitStatus).Count)
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
    direct_ec2_runtime_proof_reason = "Local/CI bundles reduce sync time but do not replace target EC2 A10G object-info, model path/hash, generation, pullback, and QA proof."
  }
  files = @($records | Sort-Object path)
  file_count = @($records).Count
  workflow_input_filenames = $workflowInputFilenames
  workflow_input_source = $workflowInputSource
  declared_required_input_asset_count = $declaredInputAssets.Count
  required_input_assets = @($requiredInputAssets)
  required_input_asset_count = @($requiredInputAssets).Count
  result = "pass_local_only"
  next_action = "Upload this bundle artifact to GitHub Actions/S3 before EC2 starts, then prefer bundle download on EC2 and skip Git LFS unless the selected lane explicitly requires it."
}

$contentManifestPath = Join-Path $contentRoot "DEPLOY_BUNDLE_MANIFEST.json"
Write-JsonNoBom -Value $manifest -Path $contentManifestPath -Depth 30

$zipPath = Join-Path $OutDir "$BundleName.zip"
New-PortableZipArchive -SourceRoot $contentRoot -DestinationPath $zipPath
Assert-PortableDeployBundleZip -ZipPath $zipPath -Manifest $manifest

$zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
$manifest.bundle_zip = Split-Path -Leaf $zipPath
$manifest.bundle_zip_sha256 = $zipHash
$manifest.bundle_zip_size_bytes = (Get-Item -LiteralPath $zipPath).Length
$manifest.zip_portability_gate = [ordered]@{
  result = "pass"
  entry_separator = "/"
  unsafe_entry_count = 0
  duplicate_normalized_entry_count = 0
  manifest_entry_mismatch_count = 0
}

$sidecarManifestPath = Join-Path $OutDir "DEPLOY_BUNDLE_MANIFEST.json"
Write-JsonNoBom -Value $manifest -Path $sidecarManifestPath -Depth 30

$manifest | ConvertTo-Json -Depth 30
