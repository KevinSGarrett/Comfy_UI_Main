<#
.SYNOPSIS
Builds a local matrix of workflow run packages from prompt profiles.

.DESCRIPTION
Reads a matrix JSON file, then invokes New-WorkflowRunPackage.ps1 once per
sample profile. This is local-only preparation for later bounded runtime work.
It does not contact AWS, GitHub APIs, Civitai, ComfyUI, or EC2, and it does not
execute generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$MatrixFile = "PromptProfiles\base_generation\realvisxl_multisample_certification.matrix.json",
  [string]$PackageRoot = "",
  [string]$MatrixRoot = "",
  [string]$RunIdPrefix = "",
  [string]$ClientId = "codex-package-matrix"
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
    return $Path
  }
  return Join-Path $ProjectRoot $Path
}

function ConvertTo-SafeId {
  param([Parameter(Mandatory=$true)][string]$Value)
  return (($Value.ToLowerInvariant() -replace '[^a-z0-9]+', '_').Trim('_'))
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

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}

$resolvedMatrixFile = Resolve-ProjectPath -Path $MatrixFile
$matrix = Read-JsonFile -Path $resolvedMatrixFile
$matrixId = [string]$matrix.matrix_id
if ([string]::IsNullOrWhiteSpace($matrixId)) {
  throw "Matrix file must define matrix_id."
}

$laneId = [string]$matrix.lane_id
if ([string]::IsNullOrWhiteSpace($laneId)) {
  throw "Matrix file must define lane_id."
}

$routeRequestFile = [string]$matrix.route_request_file
if ([string]::IsNullOrWhiteSpace($routeRequestFile)) {
  throw "Matrix file must define route_request_file."
}

if ([string]::IsNullOrWhiteSpace($PackageRoot)) {
  $PackageRoot = Join-Path $ProjectRoot "runtime_artifacts\run_packages"
}
if ([string]::IsNullOrWhiteSpace($MatrixRoot)) {
  $MatrixRoot = Join-Path $ProjectRoot "runtime_artifacts\run_package_matrices"
}
if ([string]::IsNullOrWhiteSpace($RunIdPrefix)) {
  $RunIdPrefix = "$matrixId`_$((Get-Date).ToString('yyyyMMddTHHmmsszzz').Replace(':',''))"
}

$packageScript = Join-Path $ProjectRoot "tools\New-WorkflowRunPackage.ps1"
if (!(Test-Path -LiteralPath $packageScript)) {
  throw "Package builder missing: $packageScript"
}

$samples = @($matrix.samples)
if ($samples.Count -eq 0) {
  throw "Matrix file contains no samples."
}

$matrixDir = Join-Path $MatrixRoot (ConvertTo-SafeId -Value $RunIdPrefix)
New-Item -ItemType Directory -Force -Path $matrixDir | Out-Null

$sampleRecords = @()
$checks = @()
$seeds = @{}
$prefixes = @{}
$index = 0
foreach ($sample in $samples) {
  $index += 1
  $profileFile = Resolve-ProjectPath -Path ([string]$sample.profile_file)
  $profile = Read-JsonFile -Path $profileFile
  $profileId = [string]$profile.profile_id
  if ([string]::IsNullOrWhiteSpace($profileId)) {
    throw "Profile missing profile_id: $profileFile"
  }
  if ([string]$profile.target_lane_id -ne $laneId) {
    throw "Profile $profileId target_lane_id '$($profile.target_lane_id)' does not match matrix lane '$laneId'."
  }

  $safeProfile = ConvertTo-SafeId -Value $profileId
  $runId = "$(ConvertTo-SafeId -Value $RunIdPrefix)_$safeProfile"
  $client = "$ClientId-$index"

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $packageScript `
    -ProjectRoot $ProjectRoot `
    -LaneId $laneId `
    -AllowNonFirstLane `
    -RouteRequestFile $routeRequestFile `
    -PromptProfileFile $profileFile `
    -PackageRoot $PackageRoot `
    -RunId $runId `
    -ClientId $client 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Package builder failed for profile $profileId`: $($output | Out-String)"
  }

  $manifestPath = Join-Path $PackageRoot "$runId\RUN_PACKAGE_MANIFEST.json"
  $manifest = Read-JsonFile -Path $manifestPath
  $seed = [string]$profile.request_patch_values.seed
  $outputPrefix = [string]$profile.request_patch_values.save_prefix
  if (![string]::IsNullOrWhiteSpace($seed)) { $seeds[$seed] = $true }
  if (![string]::IsNullOrWhiteSpace($outputPrefix)) { $prefixes[$outputPrefix] = $true }

  $sampleRecords += [ordered]@{
    profile_id = $profileId
    profile_file = Convert-ToRepoPath -Path $profileFile
    certification_focus = [string]$sample.certification_focus
    run_id = $runId
    manifest_path = Convert-ToRepoPath -Path $manifestPath
    result = [string]$manifest.result
    route_result = [string]$manifest.route_gate.result
    route_selected_lane_id = [string]$manifest.route_gate.selected_lane_id
    prompt_profile_applied = [bool]$manifest.prompt_profile.applied
    seed = $seed
    output_prefix = $outputPrefix
    local_only = [bool]$manifest.local_only
    ec2_started = [bool]$manifest.ec2_started
    generation_executed = [bool]$manifest.generation_executed
  }
}

$minimumSampleCount = [int]$matrix.minimum_sample_count
if ($minimumSampleCount -lt 1) { $minimumSampleCount = $samples.Count }

$checks += New-Check -Name "sample_count_meets_minimum" -Passed ($sampleRecords.Count -ge $minimumSampleCount) -Observed $sampleRecords.Count -Expected $minimumSampleCount
$checks += New-Check -Name "all_packages_pass" -Passed (@($sampleRecords | Where-Object { $_["result"] -ne "pass_local_only" }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["result"] }) -Expected "all pass_local_only"
$checks += New-Check -Name "all_route_gates_pass" -Passed (@($sampleRecords | Where-Object { $_["route_result"] -ne "pass_local_only" }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["route_result"] }) -Expected "all pass_local_only"
$checks += New-Check -Name "all_routes_match_lane" -Passed (@($sampleRecords | Where-Object { $_["route_selected_lane_id"] -ne $laneId }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["route_selected_lane_id"] }) -Expected $laneId
$checks += New-Check -Name "all_prompt_profiles_applied" -Passed (@($sampleRecords | Where-Object { $_["prompt_profile_applied"] -ne $true }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["prompt_profile_applied"] }) -Expected "all true"
$checks += New-Check -Name "unique_seeds" -Passed ($seeds.Keys.Count -eq $sampleRecords.Count) -Observed $seeds.Keys.Count -Expected $sampleRecords.Count
$checks += New-Check -Name "unique_output_prefixes" -Passed ($prefixes.Keys.Count -eq $sampleRecords.Count) -Observed $prefixes.Keys.Count -Expected $sampleRecords.Count
$checks += New-Check -Name "matrix_local_only" -Passed (@($sampleRecords | Where-Object { $_["local_only"] -ne $true -or $_["ec2_started"] -ne $false -or $_["generation_executed"] -ne $false }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { [ordered]@{ profile_id = $_["profile_id"]; local_only = $_["local_only"]; ec2_started = $_["ec2_started"]; generation_executed = $_["generation_executed"] } }) -Expected "all local_only=true; ec2_started=false; generation_executed=false"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$manifestRecord = [ordered]@{
  schema_version = "1.0"
  matrix_id = $matrixId
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  matrix_file = Convert-ToRepoPath -Path $resolvedMatrixFile
  lane_id = $laneId
  route_request_file = Convert-ToRepoPath -Path (Resolve-ProjectPath -Path $routeRequestFile)
  run_id_prefix = $RunIdPrefix
  matrix_dir = Convert-ToRepoPath -Path $matrixDir
  package_root = Convert-ToRepoPath -Path $PackageRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  sample_count = $sampleRecords.Count
  samples = $sampleRecords
  certification_scope = @($matrix.certification_scope)
  qa_protocols = @($matrix.qa_protocols)
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = "After auth, Git, static proof, and runtime cost-control gates pass, execute these package manifests as a bounded multi-sample RealVisXL quality run and perform whole-image QA for every sample."
}

$manifestPath = Join-Path $matrixDir "RUN_PACKAGE_MATRIX_MANIFEST.json"
Write-JsonNoBom -Value $manifestRecord -Path $manifestPath -Depth 40
$manifestRecord | ConvertTo-Json -Depth 40
if ($manifestRecord.result -ne "pass_local_only") {
  exit 1
}
