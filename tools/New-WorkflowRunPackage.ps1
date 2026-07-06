<#
.SYNOPSIS
Builds a local run package for an exported ComfyUI workflow lane.

.DESCRIPTION
Creates a runtime_artifacts/run_packages/<run_id> folder containing the exported
workflow files, a patched ComfyUI /prompt request body, static validation output,
dry-run smoke output, and a package manifest. This is local-only preparation for
later EC2 execution; it does not contact ComfyUI, AWS, GitHub APIs, Civitai, or
start EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "",
  [string]$PromptProfileFile = "",
  [string]$PackageRoot = "",
  [string]$RunId = "",
  [string]$ClientId = "codex-root-run-package",
  [switch]$AllowNonFirstLane
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
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

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Test-MapKey {
  param(
    [object]$Map,
    [string]$Key
  )
  if ($null -eq $Map) { return $false }
  if ($Map -is [System.Collections.IDictionary]) {
    return $Map.Contains($Key)
  }
  return @($Map.PSObject.Properties.Name) -contains $Key
}

function ConvertTo-HashtableDeep {
  param([object]$InputObject)

  if ($null -eq $InputObject) { return $null }

  if ($InputObject -is [System.Collections.IDictionary]) {
    $hash = [ordered]@{}
    foreach ($key in $InputObject.Keys) {
      $hash[$key] = ConvertTo-HashtableDeep -InputObject $InputObject[$key]
    }
    return $hash
  }

  if ($InputObject -is [pscustomobject]) {
    $hash = [ordered]@{}
    foreach ($property in $InputObject.PSObject.Properties) {
      $hash[$property.Name] = ConvertTo-HashtableDeep -InputObject $property.Value
    }
    return $hash
  }

  if ($InputObject -is [System.Collections.IEnumerable] -and $InputObject -isnot [string]) {
    $array = @()
    foreach ($item in $InputObject) {
      $array += ,(ConvertTo-HashtableDeep -InputObject $item)
    }
    return $array
  }

  return $InputObject
}

function Merge-HashtableDeep {
  param(
    [Parameter(Mandatory=$true)][System.Collections.IDictionary]$Target,
    [Parameter(Mandatory=$true)][System.Collections.IDictionary]$Overlay
  )

  foreach ($key in $Overlay.Keys) {
    if ((Test-MapKey -Map $Target -Key $key) -and
        $Target[$key] -is [System.Collections.IDictionary] -and
        $Overlay[$key] -is [System.Collections.IDictionary]) {
      Merge-HashtableDeep -Target $Target[$key] -Overlay $Overlay[$key]
    } else {
      $Target[$key] = $Overlay[$key]
    }
  }
}

function Copy-PackageFile {
  param(
    [Parameter(Mandatory=$true)][string]$SourcePath,
    [Parameter(Mandatory=$true)][string]$DestinationPath,
    [System.Collections.ArrayList]$FileRecords
  )

  if (!(Test-Path -LiteralPath $SourcePath)) {
    throw "Package source file missing: $SourcePath"
  }
  Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
  $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $SourcePath).Hash.ToLowerInvariant()
  $destinationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $DestinationPath).Hash.ToLowerInvariant()
  [void]$FileRecords.Add([ordered]@{
    source = Convert-ToRepoPath -Path $SourcePath
    packaged = Convert-ToRepoPath -Path $DestinationPath
    size_bytes = (Get-Item -LiteralPath $DestinationPath).Length
    sha256 = $destinationHash
    source_hash_match = ($sourceHash -eq $destinationHash)
  })
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}

if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
  $PackageRoot = Join-Path $ProjectRoot "runtime_artifacts\run_packages"
}

$activeLanesPath = Join-Path $ProjectRoot "Workflows\base_generation\ACTIVE_LANES.json"
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

if (-not $AllowNonFirstLane -and [int]$selectedLane.order -ne 1) {
  throw "Refusing to package non-first lane '$LaneId' without -AllowNonFirstLane. First queued lane must prove runtime path first."
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
  $RunId = "$LaneId`_$((Get-Date).ToString('yyyyMMddTHHmmsszzz').Replace(':',''))"
}

$packageDir = Join-Path $PackageRoot $RunId
$laneFilesDir = Join-Path $packageDir "lane_files"
New-Item -ItemType Directory -Force -Path $laneFilesDir | Out-Null

$packagedFiles = New-Object System.Collections.ArrayList
$laneDir = Join-Path $ProjectRoot "Workflows\base_generation\$LaneId"
$workflowPath = Join-Path $ProjectRoot ([string]$selectedLane.workflow).Replace("/", "\")
$smokePath = Join-Path $ProjectRoot ([string]$selectedLane.smoke_request).Replace("/", "\")
$runtimePath = Join-Path $ProjectRoot ([string]$selectedLane.runtime_requirements).Replace("/", "\")
$patchPath = Join-Path $ProjectRoot ([string]$selectedLane.patch_points).Replace("/", "\")

Copy-PackageFile -SourcePath $workflowPath -DestinationPath (Join-Path $laneFilesDir "workflow.api.json") -FileRecords $packagedFiles
Copy-PackageFile -SourcePath $smokePath -DestinationPath (Join-Path $laneFilesDir "smoke_test_request.json") -FileRecords $packagedFiles
Copy-PackageFile -SourcePath $runtimePath -DestinationPath (Join-Path $laneFilesDir "runtime_requirements.json") -FileRecords $packagedFiles
Copy-PackageFile -SourcePath $patchPath -DestinationPath (Join-Path $laneFilesDir "patch_points.json") -FileRecords $packagedFiles
Copy-PackageFile -SourcePath $activeLanesPath -DestinationPath (Join-Path $packageDir "ACTIVE_LANES.snapshot.json") -FileRecords $packagedFiles

$packagedSmokePath = Join-Path $laneFilesDir "smoke_test_request.json"
$promptProfile = $null
$promptProfileRecord = [ordered]@{
  supplied = $false
  applied = $false
  path = $null
  profile_id = $null
  errors = @()
}

if (![string]::IsNullOrWhiteSpace($PromptProfileFile)) {
  $resolvedProfilePath = $PromptProfileFile
  if (![System.IO.Path]::IsPathRooted($resolvedProfilePath)) {
    $resolvedProfilePath = Join-Path $ProjectRoot $resolvedProfilePath
  }
  $promptProfileRecord.supplied = $true
  $promptProfileRecord.path = Convert-ToRepoPath -Path $resolvedProfilePath
  $promptProfile = Read-JsonFile -Path $resolvedProfilePath
  $promptProfileHash = ConvertTo-HashtableDeep -InputObject $promptProfile
  $promptProfileRecord.profile_id = [string]$promptProfileHash["profile_id"]

  if ((Test-MapKey -Map $promptProfileHash -Key "target_lane_id") -and
      ![string]::IsNullOrWhiteSpace([string]$promptProfileHash["target_lane_id"]) -and
      [string]$promptProfileHash["target_lane_id"] -ne $LaneId) {
    throw "Prompt profile target_lane_id '$($promptProfileHash["target_lane_id"])' does not match lane '$LaneId'."
  }

  $smokeHash = ConvertTo-HashtableDeep -InputObject (Read-JsonFile -Path $packagedSmokePath)
  if (!(Test-MapKey -Map $smokeHash -Key "request_patch_values")) {
    $smokeHash["request_patch_values"] = [ordered]@{}
  }
  if (Test-MapKey -Map $promptProfileHash -Key "request_patch_values") {
    Merge-HashtableDeep -Target $smokeHash["request_patch_values"] -Overlay $promptProfileHash["request_patch_values"]
  }
  if (Test-MapKey -Map $promptProfileHash -Key "expected_outputs") {
    if (!(Test-MapKey -Map $smokeHash -Key "expected_outputs")) {
      $smokeHash["expected_outputs"] = [ordered]@{}
    }
    Merge-HashtableDeep -Target $smokeHash["expected_outputs"] -Overlay $promptProfileHash["expected_outputs"]
  }
  $smokeHash["prompt_profile"] = [ordered]@{
    profile_id = [string]$promptProfileHash["profile_id"]
    source = $promptProfileRecord.path
  }
  Write-JsonNoBom -Value $smokeHash -Path $packagedSmokePath -Depth 20
  $modifiedSmokeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $packagedSmokePath).Hash.ToLowerInvariant()
  $packagedSmokeRepoPath = Convert-ToRepoPath -Path $packagedSmokePath
  foreach ($fileRecord in @($packagedFiles)) {
    if ([string]$fileRecord["packaged"] -eq $packagedSmokeRepoPath) {
      $fileRecord["sha256"] = $modifiedSmokeHash
      $fileRecord["source_hash_match"] = $false
      $fileRecord["profile_modified"] = $true
    }
  }
  $promptProfileRecord.applied = $true
}

$staticValidationPath = Join-Path $packageDir "static_validation.json"
$promptRequestPath = Join-Path $packageDir "prompt_request.json"
$smokeDryRunPath = Join-Path $packageDir "smoke_dry_run.json"

$staticScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"
$smokeScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-ComfyWorkflowSmoke.ps1"

& powershell -NoProfile -ExecutionPolicy Bypass -File $staticScript -ProjectRoot $ProjectRoot -LaneDir $laneFilesDir -OutFile $staticValidationPath | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Static workflow validation failed for $LaneId"
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $smokeScript -ProjectRoot $ProjectRoot -LaneDir $laneFilesDir -ClientId $ClientId -OutFile $smokeDryRunPath -OutRequestFile $promptRequestPath | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Comfy workflow smoke dry-run failed for $LaneId"
}

$staticValidation = Read-JsonFile -Path $staticValidationPath
$smokeDryRun = Read-JsonFile -Path $smokeDryRunPath
$promptRequest = Read-JsonFile -Path $promptRequestPath

$requestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $promptRequestPath).Hash.ToLowerInvariant()
$staticHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $staticValidationPath).Hash.ToLowerInvariant()
$smokeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $smokeDryRunPath).Hash.ToLowerInvariant()

$packageManifest = [ordered]@{
  schema_version = "1.0"
  run_id = $RunId
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  lane_id = $LaneId
  lane_order = [int]$selectedLane.order
  package_dir = Convert-ToRepoPath -Path $packageDir
  active_lanes_manifest = Convert-ToRepoPath -Path $activeLanesPath
  prompt_profile = $promptProfileRecord
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  packaged_files = @($packagedFiles)
  generated_files = @(
    [ordered]@{
      path = Convert-ToRepoPath -Path $staticValidationPath
      sha256 = $staticHash
      purpose = "Static workflow validation for the exported lane."
    },
    [ordered]@{
      path = Convert-ToRepoPath -Path $smokeDryRunPath
      sha256 = $smokeHash
      purpose = "Dry-run ComfyUI smoke request build record."
    },
    [ordered]@{
      path = Convert-ToRepoPath -Path $promptRequestPath
      sha256 = $requestHash
      purpose = "Patched ComfyUI /prompt request body for later runtime execution."
    }
  )
  workflow_static = [ordered]@{
    qa_status = [string]$staticValidation.qa_status
    node_count = [int]$staticValidation.node_count
    link_count = [int]$staticValidation.link_count
    defect_count = @($staticValidation.defects).Count
  }
  smoke_dry_run = [ordered]@{
    mode = [string]$smokeDryRun.mode
    request_body_written = [bool]$smokeDryRun.request_body_written
    patched_input_count = @($smokeDryRun.patched_inputs).Count
    execution_allowed = [bool]$smokeDryRun.execution_allowed
    generation_executed = [bool]$smokeDryRun.generation_executed
    error_count = @($smokeDryRun.errors).Count
  }
  prompt_request = [ordered]@{
    client_id = [string]$promptRequest.client_id
    node_count = @($promptRequest.prompt.PSObject.Properties).Count
    sha256 = $requestHash
  }
  runtime_boundaries = [ordered]@{
    ec2_start_allowed_by_package = $false
    generation_allowed_by_package = $false
    reason = "This package proves local request construction only. EC2 static proof and AWS auth remain mandatory before execution."
  }
  result = $(if ([string]$staticValidation.qa_status -eq "pass" -and [bool]$smokeDryRun.request_body_written -and @($smokeDryRun.errors).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "After AWS auth is refreshed and EC2 static proof passes, use prompt_request.json as the bounded /prompt body for this lane."
}

$manifestPath = Join-Path $packageDir "RUN_PACKAGE_MANIFEST.json"
Write-JsonNoBom -Value $packageManifest -Path $manifestPath -Depth 20

$packageManifest | ConvertTo-Json -Depth 20
if ($packageManifest.result -ne "pass_local_only") {
  exit 1
}
