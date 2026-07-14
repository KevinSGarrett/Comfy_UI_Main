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
  $temporary = "$Path.$([guid]::NewGuid().ToString('N')).tmp"
  try {
    [System.IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
  } finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
  }
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

function Assert-ProjectInputFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if (!$resolved.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Input file must remain inside ProjectRoot: $Path"
  }
  if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) {
    throw "Required input file missing: $resolved"
  }
}

function ConvertTo-SafeId {
  param([Parameter(Mandatory=$true)][string]$Value)
  return (($Value.ToLowerInvariant() -replace '[^a-z0-9]+', '_').Trim('_'))
}

function Get-StringSha256Lower {
  param([Parameter(Mandatory=$true)][string]$Value)
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
  $sha256 = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([System.BitConverter]::ToString($sha256.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
  } finally {
    $sha256.Dispose()
  }
}

function Get-FileSha256Lower {
  param([Parameter(Mandatory=$true)][string]$Path)
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
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
Assert-ProjectInputFile -Path $resolvedMatrixFile
$matrix = Read-JsonFile -Path $resolvedMatrixFile
$matrixId = [string]$matrix.matrix_id
if ([string]::IsNullOrWhiteSpace($matrixId)) {
  throw "Matrix file must define matrix_id."
}

$laneId = [string]$matrix.lane_id
if ([string]::IsNullOrWhiteSpace($laneId)) {
  throw "Matrix file must define lane_id."
}
$workflowGroup = [string]$matrix.workflow_group
if ([string]::IsNullOrWhiteSpace($workflowGroup)) {
  $workflowGroup = "base_generation"
}

$requiresRouterGate = $true
if ($null -ne $matrix.PSObject.Properties["requires_router_gate"]) {
  $requiresRouterGate = [bool]$matrix.requires_router_gate
}
$routeRequestFile = [string]$matrix.route_request_file
if ($requiresRouterGate -and [string]::IsNullOrWhiteSpace($routeRequestFile)) {
  throw "Matrix file must define route_request_file when requires_router_gate=true."
}
if (![string]::IsNullOrWhiteSpace($routeRequestFile)) {
  Assert-ProjectInputFile -Path (Resolve-ProjectPath -Path $routeRequestFile)
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
$requiresSourceBindings = $false
if ($null -ne $matrix.PSObject.Properties["requires_source_bindings"]) {
  $requiresSourceBindings = [bool]$matrix.requires_source_bindings
}
$excludedSourceScopePath = [string]$matrix.excluded_source_scope.path
$excludedSourceScopeFull = $null
if (![string]::IsNullOrWhiteSpace($excludedSourceScopePath)) {
  $excludedSourceScopeFull = [System.IO.Path]::GetFullPath((Resolve-ProjectPath -Path $excludedSourceScopePath)).TrimEnd("\", "/")
  $projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  if (!$excludedSourceScopeFull.StartsWith($projectRootFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Matrix excluded_source_scope must remain inside ProjectRoot: $excludedSourceScopePath"
  }
}

$matrixDir = Join-Path $MatrixRoot (ConvertTo-SafeId -Value $RunIdPrefix)
New-Item -ItemType Directory -Force -Path $matrixDir | Out-Null

$sampleRecords = @()
$checks = @()
$seeds = @{}
$prefixes = @{}
$promptHashes = @{}
$variantSignatures = @{}
$index = 0
foreach ($sample in $samples) {
  $index += 1
  $profileFile = Resolve-ProjectPath -Path ([string]$sample.profile_file)
  Assert-ProjectInputFile -Path $profileFile
  $profile = Read-JsonFile -Path $profileFile
  $profileId = [string]$profile.profile_id
  if ([string]::IsNullOrWhiteSpace($profileId)) {
    throw "Profile missing profile_id: $profileFile"
  }
  if ([string]$profile.target_lane_id -ne $laneId) {
    throw "Profile $profileId target_lane_id '$($profile.target_lane_id)' does not match matrix lane '$laneId'."
  }

  $sourceBindingSupplied = ($null -ne $profile.PSObject.Properties["source_binding"])
  if ($requiresSourceBindings -and !$sourceBindingSupplied) {
    throw "Profile $profileId must define source_binding because the matrix requires exact source bindings."
  }
  $sourceBindingValid = !$requiresSourceBindings
  $sourceProjectPath = $null
  $sourceStagedFilename = $null
  $sourceSizeBytes = $null
  $sourceSha256 = $null
  if ($sourceBindingSupplied) {
    $binding = $profile.source_binding
    $bindingProjectPath = [string]$binding.project_path
    $sourceStagedFilename = [string]$binding.staged_filename
    $expectedSourceSha256 = ([string]$binding.sha256).ToLowerInvariant()
    $expectedSourceSizeBytes = [int64]$binding.size_bytes
    if ([string]::IsNullOrWhiteSpace($bindingProjectPath) -or
        [string]::IsNullOrWhiteSpace($sourceStagedFilename) -or
        $expectedSourceSha256 -notmatch '^[a-f0-9]{64}$' -or
        $expectedSourceSizeBytes -lt 1) {
      throw "Profile $profileId source_binding must define project_path, staged_filename, 64-character sha256, and positive size_bytes."
    }
    $resolvedSourcePath = Resolve-ProjectPath -Path $bindingProjectPath
    Assert-ProjectInputFile -Path $resolvedSourcePath
    $resolvedSourceFull = [System.IO.Path]::GetFullPath($resolvedSourcePath)
    if ($null -ne $excludedSourceScopeFull -and
        ($resolvedSourceFull.Equals($excludedSourceScopeFull, [System.StringComparison]::OrdinalIgnoreCase) -or
         $resolvedSourceFull.StartsWith($excludedSourceScopeFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase))) {
      throw "Profile $profileId source_binding is inside excluded_source_scope '$excludedSourceScopePath': $bindingProjectPath"
    }
    $sourceProjectPath = Convert-ToRepoPath -Path $resolvedSourcePath
    $sourceSizeBytes = [int64](Get-Item -LiteralPath $resolvedSourcePath).Length
    $sourceSha256 = Get-FileSha256Lower -Path $resolvedSourcePath
    $requestSourceImage = [string]$profile.request_patch_values.source_image
    if ($sourceSizeBytes -ne $expectedSourceSizeBytes) {
      throw "Profile $profileId source_binding size mismatch: expected $expectedSourceSizeBytes, observed $sourceSizeBytes."
    }
    if ($sourceSha256 -ne $expectedSourceSha256) {
      throw "Profile $profileId source_binding SHA-256 mismatch: expected $expectedSourceSha256, observed $sourceSha256."
    }
    if ($requestSourceImage -ne $sourceStagedFilename) {
      throw "Profile $profileId request source_image '$requestSourceImage' does not match source_binding staged_filename '$sourceStagedFilename'."
    }
    $sourceBindingValid = $true
  }

  $safeProfile = ConvertTo-SafeId -Value $profileId
  $runId = "$(ConvertTo-SafeId -Value $RunIdPrefix)_$safeProfile"
  $client = "$ClientId-$index"

  $packageArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $packageScript,
    "-ProjectRoot", $ProjectRoot,
    "-WorkflowGroup", $workflowGroup,
    "-LaneId", $laneId,
    "-AllowNonFirstLane"
  )
  if (![string]::IsNullOrWhiteSpace($routeRequestFile)) {
    $packageArgs += @("-RouteRequestFile", $routeRequestFile)
  }
  $packageArgs += @(
    "-PromptProfileFile", $profileFile,
    "-PackageRoot", $PackageRoot,
    "-RunId", $runId,
    "-ClientId", $client
  )
  $output = & powershell @packageArgs 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Package builder failed for profile $profileId`: $($output | Out-String)"
  }

  $manifestPath = Join-Path $PackageRoot "$runId\RUN_PACKAGE_MANIFEST.json"
  $manifest = Read-JsonFile -Path $manifestPath
  $packageSourceBindingValid = [bool]$manifest.prompt_profile.source_binding.valid
  $packageSourcePath = [string]$manifest.prompt_profile.source_binding.packaged
  if ($sourceBindingSupplied -and (!$packageSourceBindingValid -or [string]::IsNullOrWhiteSpace($packageSourcePath))) {
    throw "Package $runId did not preserve the validated source binding."
  }
  $seed = [string]$profile.request_patch_values.seed
  $outputPrefix = [string]$profile.request_patch_values.save_prefix
  if ([string]::IsNullOrWhiteSpace($outputPrefix)) {
    $outputPrefix = [string]$profile.request_patch_values.output_video.filename_prefix
  }
  if ([string]::IsNullOrWhiteSpace($outputPrefix)) {
    $outputPrefix = [string]$profile.expected_outputs.output_prefix
  }
  $sourceImage = [string]$profile.request_patch_values.source_image
  $videoLength = [string]$profile.request_patch_values.video_latent.length
  $artifactType = [string]$profile.expected_outputs.artifact_type
  $expectedWidth = [string]$profile.request_patch_values.video_latent.width
  $expectedHeight = [string]$profile.request_patch_values.video_latent.height
  $expectedFrameCount = [string]$profile.expected_outputs.frame_count
  if ([string]::IsNullOrWhiteSpace($expectedFrameCount)) { $expectedFrameCount = $videoLength }
  $expectedFps = [string]$profile.expected_outputs.fps
  $promptHash = [string]$manifest.prompt_request.sha256
  $variantMaterial = [ordered]@{
    positive_prompt = [string]$profile.request_patch_values.positive_prompt
    negative_prompt = [string]$profile.request_patch_values.negative_prompt
    seed = $seed
    sampler_settings = $profile.request_patch_values.sampler_settings
    video_latent = $profile.request_patch_values.video_latent
    source_image = $sourceImage
    source_binding_supplied = $sourceBindingSupplied
    source_binding_valid = $sourceBindingValid
    source_project_path = $sourceProjectPath
    source_staged_filename = $sourceStagedFilename
    source_size_bytes = $sourceSizeBytes
    source_sha256 = $sourceSha256
    source_packaged_path = $packageSourcePath
    source_package_binding_valid = $packageSourceBindingValid
    excluded_source_scope_path = $excludedSourceScopePath
    outside_excluded_source_scope = $true
    diffusion_model = [string]$profile.request_patch_values.diffusion_model
    text_encoder = [string]$profile.request_patch_values.text_encoder
    vae_model = [string]$profile.request_patch_values.vae_model
  }
  $variantSignature = Get-StringSha256Lower -Value ($variantMaterial | ConvertTo-Json -Depth 20 -Compress)
  if (![string]::IsNullOrWhiteSpace($seed)) { $seeds[$seed] = $true }
  if (![string]::IsNullOrWhiteSpace($outputPrefix)) { $prefixes[$outputPrefix] = $true }
  if (![string]::IsNullOrWhiteSpace($promptHash)) { $promptHashes[$promptHash] = $true }
  if (![string]::IsNullOrWhiteSpace($variantSignature)) { $variantSignatures[$variantSignature] = $true }

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
    source_image = $sourceImage
    source_binding_supplied = $sourceBindingSupplied
    source_binding_valid = $sourceBindingValid
    source_project_path = $sourceProjectPath
    source_staged_filename = $sourceStagedFilename
    source_size_bytes = $sourceSizeBytes
    source_sha256 = $sourceSha256
    source_packaged_path = $packageSourcePath
    source_package_binding_valid = $packageSourceBindingValid
    excluded_source_scope_path = $excludedSourceScopePath
    outside_excluded_source_scope = $true
    video_length = $videoLength
    artifact_type = $artifactType
    expected_width = $expectedWidth
    expected_height = $expectedHeight
    expected_frame_count = $expectedFrameCount
    expected_fps = $expectedFps
    prompt_request_sha256 = $promptHash
    variant_signature_sha256 = $variantSignature
    local_only = [bool]$manifest.local_only
    ec2_started = [bool]$manifest.ec2_started
    generation_executed = [bool]$manifest.generation_executed
  }
}

$minimumSampleCount = [int]$matrix.minimum_sample_count
if ($minimumSampleCount -lt 1) { $minimumSampleCount = $samples.Count }
$requiresUniqueSeeds = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_seeds"]) { $requiresUniqueSeeds = [bool]$matrix.requires_unique_seeds }
$requiresUniqueOutputPrefixes = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_output_prefixes"]) { $requiresUniqueOutputPrefixes = [bool]$matrix.requires_unique_output_prefixes }
$requiresUniquePromptHashes = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_prompt_hashes"]) { $requiresUniquePromptHashes = [bool]$matrix.requires_unique_prompt_hashes }
$requiresUniqueVariantSignatures = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_variant_signatures"]) { $requiresUniqueVariantSignatures = [bool]$matrix.requires_unique_variant_signatures }

$checks += New-Check -Name "sample_count_meets_minimum" -Passed ($sampleRecords.Count -ge $minimumSampleCount) -Observed $sampleRecords.Count -Expected $minimumSampleCount
$checks += New-Check -Name "all_packages_pass" -Passed (@($sampleRecords | Where-Object { $_["result"] -ne "pass_local_only" }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["result"] }) -Expected "all pass_local_only"
if ($requiresRouterGate) {
  $checks += New-Check -Name "all_route_gates_pass" -Passed (@($sampleRecords | Where-Object { $_["route_result"] -ne "pass_local_only" }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["route_result"] }) -Expected "all pass_local_only"
  $checks += New-Check -Name "all_routes_match_lane" -Passed (@($sampleRecords | Where-Object { $_["route_selected_lane_id"] -ne $laneId }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["route_selected_lane_id"] }) -Expected $laneId
} else {
  $checks += New-Check -Name "all_route_gates_not_supplied_by_policy" -Passed (@($sampleRecords | Where-Object { $_["route_result"] -ne "not_supplied" }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["route_result"] }) -Expected "all not_supplied"
}
$checks += New-Check -Name "all_prompt_profiles_applied" -Passed (@($sampleRecords | Where-Object { $_["prompt_profile_applied"] -ne $true }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { $_["prompt_profile_applied"] }) -Expected "all true"
$checks += New-Check -Name "required_source_bindings_valid" -Passed (!$requiresSourceBindings -or @($sampleRecords | Where-Object { $_["source_binding_supplied"] -ne $true -or $_["source_binding_valid"] -ne $true -or $_["source_package_binding_valid"] -ne $true -or [string]::IsNullOrWhiteSpace([string]$_["source_packaged_path"]) }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { [ordered]@{ profile_id = $_["profile_id"]; supplied = $_["source_binding_supplied"]; valid = $_["source_binding_valid"]; package_valid = $_["source_package_binding_valid"]; packaged_path = $_["source_packaged_path"]; source_sha256 = $_["source_sha256"] } }) -Expected $(if ($requiresSourceBindings) { "all supplied, valid, and packaged" } else { "not required" })
$checks += New-Check -Name "sources_outside_excluded_scope" -Passed (@($sampleRecords | Where-Object { $_["outside_excluded_source_scope"] -ne $true }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { [ordered]@{ profile_id = $_["profile_id"]; source = $_["source_project_path"]; excluded_scope = $_["excluded_source_scope_path"]; outside = $_["outside_excluded_source_scope"] } }) -Expected "all true"
$checks += New-Check -Name "unique_seeds" -Passed (!$requiresUniqueSeeds -or $seeds.Keys.Count -eq $sampleRecords.Count) -Observed $seeds.Keys.Count -Expected $(if ($requiresUniqueSeeds) { $sampleRecords.Count } else { "not required" })
$checks += New-Check -Name "unique_output_prefixes" -Passed (!$requiresUniqueOutputPrefixes -or $prefixes.Keys.Count -eq $sampleRecords.Count) -Observed $prefixes.Keys.Count -Expected $(if ($requiresUniqueOutputPrefixes) { $sampleRecords.Count } else { "not required" })
$checks += New-Check -Name "unique_prompt_request_hashes" -Passed (!$requiresUniquePromptHashes -or $promptHashes.Keys.Count -eq $sampleRecords.Count) -Observed $promptHashes.Keys.Count -Expected $(if ($requiresUniquePromptHashes) { $sampleRecords.Count } else { "not required" })
$checks += New-Check -Name "unique_substantive_variant_signatures" -Passed (!$requiresUniqueVariantSignatures -or $variantSignatures.Keys.Count -eq $sampleRecords.Count) -Observed $variantSignatures.Keys.Count -Expected $(if ($requiresUniqueVariantSignatures) { $sampleRecords.Count } else { "not required" })
$checks += New-Check -Name "matrix_local_only" -Passed (@($sampleRecords | Where-Object { $_["local_only"] -ne $true -or $_["ec2_started"] -ne $false -or $_["generation_executed"] -ne $false }).Count -eq 0) -Observed @($sampleRecords | ForEach-Object { [ordered]@{ profile_id = $_["profile_id"]; local_only = $_["local_only"]; ec2_started = $_["ec2_started"]; generation_executed = $_["generation_executed"] } }) -Expected "all local_only=true; ec2_started=false; generation_executed=false"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$manifestRecord = [ordered]@{
  schema_version = "1.0"
  matrix_id = $matrixId
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  matrix_file = Convert-ToRepoPath -Path $resolvedMatrixFile
  lane_id = $laneId
  workflow_group = $workflowGroup
  route_request_file = $(if ([string]::IsNullOrWhiteSpace($routeRequestFile)) { $null } else { Convert-ToRepoPath -Path (Resolve-ProjectPath -Path $routeRequestFile) })
  requires_router_gate = $requiresRouterGate
  requires_source_bindings = $requiresSourceBindings
  excluded_source_scope_path = $excludedSourceScopePath
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
  next_action = $(if (![string]::IsNullOrWhiteSpace([string]$matrix.next_action)) { [string]$matrix.next_action } else { "After auth, Git, static proof, and runtime cost-control gates pass, execute these package manifests as a bounded multi-sample quality run and perform whole-artifact QA for every sample." })
}

$manifestPath = Join-Path $matrixDir "RUN_PACKAGE_MATRIX_MANIFEST.json"
Write-JsonNoBom -Value $manifestRecord -Path $manifestPath -Depth 40
$manifestRecord | ConvertTo-Json -Depth 40
if ($manifestRecord.result -ne "pass_local_only") {
  exit 1
}
