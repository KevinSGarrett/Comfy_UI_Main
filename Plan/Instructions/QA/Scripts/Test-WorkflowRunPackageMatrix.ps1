<#
.SYNOPSIS
Validates a policy-bounded multi-sample workflow run package matrix.

.DESCRIPTION
Builds the package matrix in a temporary package root, checks every sample
manifest for route policy, prompt profile application, unique seed/output
prefix, local-only boundaries, and writes a reusable evidence record. This
does not contact AWS, GitHub APIs, Civitai, ComfyUI, or EC2, and does not run
generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$MatrixFile = "PromptProfiles\base_generation\realvisxl_multisample_certification.matrix.json",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function ConvertTo-ProjectRelativePath {
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
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator).Replace("\", "/")
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
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

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Run_Package\W66_WORKFLOW_RUN_PACKAGE_MATRIX_$stamp.json"
}

$resolvedMatrixFile = $MatrixFile
if (![System.IO.Path]::IsPathRooted($resolvedMatrixFile)) {
  $resolvedMatrixFile = Join-Path $ProjectRoot $resolvedMatrixFile
}
Assert-ProjectInputFile -Path $resolvedMatrixFile
$matrix = Read-JsonFile -Path $resolvedMatrixFile
$matrixId = [string]$matrix.matrix_id
$laneId = [string]$matrix.lane_id
$requiresRouterGate = $true
if ($null -ne $matrix.PSObject.Properties["requires_router_gate"]) { $requiresRouterGate = [bool]$matrix.requires_router_gate }
$requiresUniqueSeeds = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_seeds"]) { $requiresUniqueSeeds = [bool]$matrix.requires_unique_seeds }
$requiresUniqueOutputPrefixes = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_output_prefixes"]) { $requiresUniqueOutputPrefixes = [bool]$matrix.requires_unique_output_prefixes }
$requiresUniquePromptHashes = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_prompt_hashes"]) { $requiresUniquePromptHashes = [bool]$matrix.requires_unique_prompt_hashes }
$requiresUniqueVariantSignatures = $true
if ($null -ne $matrix.PSObject.Properties["requires_unique_variant_signatures"]) { $requiresUniqueVariantSignatures = [bool]$matrix.requires_unique_variant_signatures }

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "comfy_package_matrix_$stamp"
$tempPackages = Join-Path $tempRoot "packages"
$tempMatrices = Join-Path $tempRoot "matrices"
New-Item -ItemType Directory -Force -Path $tempPackages | Out-Null
New-Item -ItemType Directory -Force -Path $tempMatrices | Out-Null

$matrixBuilder = Join-Path $ProjectRoot "tools\New-WorkflowRunPackageMatrix.ps1"
$runIdPrefix = "$matrixId`_$stamp"
$matrixOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $matrixBuilder `
  -ProjectRoot $ProjectRoot `
  -MatrixFile $resolvedMatrixFile `
  -PackageRoot $tempPackages `
  -MatrixRoot $tempMatrices `
  -RunIdPrefix $runIdPrefix `
  -ClientId "codex-matrix-validation" 2>&1
if ($LASTEXITCODE -ne 0) {
  throw "Package matrix builder failed: $($matrixOutput | Out-String)"
}

$safeRunIdPrefix = (($runIdPrefix.ToLowerInvariant() -replace '[^a-z0-9]+', '_').Trim('_'))
$matrixManifestPath = Join-Path $tempMatrices "$safeRunIdPrefix\RUN_PACKAGE_MATRIX_MANIFEST.json"
$matrixManifest = Read-JsonFile -Path $matrixManifestPath
$samples = @($matrixManifest.samples)
$minimumSampleCount = [int]$matrix.minimum_sample_count

$checks = @()
$checks += New-Check -Name "matrix_result_passes" -Passed ([string]$matrixManifest.result -eq "pass_local_only") -Observed $matrixManifest.result -Expected "pass_local_only"
$checks += New-Check -Name "matrix_lane_matches" -Passed ([string]$matrixManifest.lane_id -eq $laneId) -Observed $matrixManifest.lane_id -Expected $laneId
$checks += New-Check -Name "sample_count_meets_minimum" -Passed ($samples.Count -ge $minimumSampleCount) -Observed $samples.Count -Expected $minimumSampleCount
$checks += New-Check -Name "all_sample_packages_pass" -Passed (@($samples | Where-Object { $_.result -ne "pass_local_only" }).Count -eq 0) -Observed @($samples | Select-Object -ExpandProperty result) -Expected "all pass_local_only"
if ($requiresRouterGate) {
  $checks += New-Check -Name "all_sample_routes_pass" -Passed (@($samples | Where-Object { $_.route_result -ne "pass_local_only" }).Count -eq 0) -Observed @($samples | Select-Object -ExpandProperty route_result) -Expected "all pass_local_only"
  $checks += New-Check -Name "all_sample_routes_match_lane" -Passed (@($samples | Where-Object { $_.route_selected_lane_id -ne $laneId }).Count -eq 0) -Observed @($samples | Select-Object -ExpandProperty route_selected_lane_id) -Expected $laneId
} else {
  $checks += New-Check -Name "all_sample_routes_not_supplied_by_policy" -Passed (@($samples | Where-Object { $_.route_result -ne "not_supplied" }).Count -eq 0) -Observed @($samples | Select-Object -ExpandProperty route_result) -Expected "all not_supplied"
}
$checks += New-Check -Name "all_prompt_profiles_applied" -Passed (@($samples | Where-Object { $_.prompt_profile_applied -ne $true }).Count -eq 0) -Observed @($samples | Select-Object -ExpandProperty prompt_profile_applied) -Expected "all true"
$checks += New-Check -Name "unique_seed_count" -Passed (!$requiresUniqueSeeds -or @($samples | Select-Object -ExpandProperty seed -Unique).Count -eq $samples.Count) -Observed @($samples | Select-Object -ExpandProperty seed -Unique).Count -Expected $(if ($requiresUniqueSeeds) { $samples.Count } else { "not required" })
$checks += New-Check -Name "unique_output_prefix_count" -Passed (!$requiresUniqueOutputPrefixes -or @($samples | Select-Object -ExpandProperty output_prefix -Unique).Count -eq $samples.Count) -Observed @($samples | Select-Object -ExpandProperty output_prefix -Unique).Count -Expected $(if ($requiresUniqueOutputPrefixes) { $samples.Count } else { "not required" })
$checks += New-Check -Name "unique_prompt_request_hash_count" -Passed (!$requiresUniquePromptHashes -or @($samples | Select-Object -ExpandProperty prompt_request_sha256 -Unique).Count -eq $samples.Count) -Observed @($samples | Select-Object -ExpandProperty prompt_request_sha256 -Unique).Count -Expected $(if ($requiresUniquePromptHashes) { $samples.Count } else { "not required" })
$checks += New-Check -Name "unique_substantive_variant_signature_count" -Passed (!$requiresUniqueVariantSignatures -or @($samples | Select-Object -ExpandProperty variant_signature_sha256 -Unique).Count -eq $samples.Count) -Observed @($samples | Select-Object -ExpandProperty variant_signature_sha256 -Unique).Count -Expected $(if ($requiresUniqueVariantSignatures) { $samples.Count } else { "not required" })
$checks += New-Check -Name "matrix_no_external_contact_or_generation" -Passed ([bool]$matrixManifest.local_only -eq $true -and [bool]$matrixManifest.aws_contacted -eq $false -and [bool]$matrixManifest.github_api_contacted -eq $false -and [bool]$matrixManifest.civitai_contacted -eq $false -and [bool]$matrixManifest.comfyui_contacted -eq $false -and [bool]$matrixManifest.ec2_started -eq $false -and [bool]$matrixManifest.generation_executed -eq $false) -Observed ([ordered]@{ local_only = $matrixManifest.local_only; aws = $matrixManifest.aws_contacted; github_api = $matrixManifest.github_api_contacted; civitai = $matrixManifest.civitai_contacted; comfyui = $matrixManifest.comfyui_contacted; ec2_started = $matrixManifest.ec2_started; generation_executed = $matrixManifest.generation_executed }) -Expected "local_only=true; all contacts false; ec2_started=false; generation_executed=false"

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W66-WORKFLOW-RUN-PACKAGE-MATRIX-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W64-009"
  artifact_type = "workflow_run_package_matrix_validation"
  matrix_id = $matrixId
  lane_id = $laneId
  local_only = $true
  ec2_started = $false
  generation_executed = $false
  scripts = [ordered]@{
    matrix_builder = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $matrixBuilder
    validator = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $PSCommandPath
  }
  matrix_file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $resolvedMatrixFile
  validation_temp_root = "[VALIDATION_TEMP_ROOT]"
  sample_count = $samples.Count
  samples = @($samples | ForEach-Object {
    [ordered]@{
      profile_id = [string]$_.profile_id
      certification_focus = [string]$_.certification_focus
      result = [string]$_.result
      route_result = [string]$_.route_result
      route_selected_lane_id = [string]$_.route_selected_lane_id
      prompt_profile_applied = [bool]$_.prompt_profile_applied
      seed = [string]$_.seed
      output_prefix = [string]$_.output_prefix
      source_image = [string]$_.source_image
      video_length = [string]$_.video_length
      artifact_type = [string]$_.artifact_type
      expected_width = [string]$_.expected_width
      expected_height = [string]$_.expected_height
      expected_frame_count = [string]$_.expected_frame_count
      expected_fps = [string]$_.expected_fps
      prompt_request_sha256 = [string]$_.prompt_request_sha256
      variant_signature_sha256 = [string]$_.variant_signature_sha256
      manifest_path = "[VALIDATION_TEMP_ROOT]/packages/$($_.run_id)/RUN_PACKAGE_MANIFEST.json"
    }
  })
  checks = $checks
  failure_count = @($failures).Count
  failures = $failures
  result = $(if (@($failures).Count -eq 0) { "pass_local_only" } else { "fail" })
  next_action = $(if (![string]::IsNullOrWhiteSpace([string]$matrix.next_action)) { [string]$matrix.next_action } else { "Use the matrix builder to create a persistent multi-sample package set before the next bounded target-runtime quality run." })
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}
$record | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $OutFile -Encoding UTF8
$record | ConvertTo-Json -Depth 80
if ($record.result -ne "pass_local_only") {
  exit 1
}
