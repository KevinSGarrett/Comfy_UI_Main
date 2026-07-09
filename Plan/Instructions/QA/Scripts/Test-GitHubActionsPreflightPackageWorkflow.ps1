<#
.SYNOPSIS
Validates the GitHub Actions preflight package workflow against the active runtime queue.

.DESCRIPTION
Checks that .github/workflows/preflight-package.yml contains the local-only
prerequisite gates and that its matrix matches the active base-generation runtime
queue. With -RunLocalPackageBuild, it also syncs workflow exports, runs the same
local prerequisite gates, builds each matrix run package, and builds a deploy
bundle for every matrix row under a short validation root. It does not contact
GitHub APIs, AWS, Civitai, ComfyUI, or EC2, and it does not execute generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WorkflowFile = ".github\workflows\preflight-package.yml",
  [string]$QueueFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$OutFile = "",
  [switch]$RunLocalPackageBuild
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
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
  if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$TargetPath
  )
  return (Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath).Replace("\", "/")
}

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function New-Check {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][bool]$Passed,
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

function Get-WorkflowMatrixEntries {
  param([Parameter(Mandatory=$true)][string]$WorkflowText)

  $entries = New-Object System.Collections.ArrayList
  $current = $null
  foreach ($line in ($WorkflowText -split "`r?`n")) {
    if ($line -match '^\s*-\s+lane_id:\s*(\S+)\s*$') {
      if ($null -ne $current) { [void]$entries.Add([pscustomobject]$current) }
      $current = [ordered]@{
        lane_id = $Matches[1]
        run_id = ""
        prompt_profile = ""
        allow_non_first_lane = ""
      }
      continue
    }
    if ($null -eq $current) { continue }
    if ($line -match '^\s*run_id:\s*(\S+)\s*$') {
      $current.run_id = $Matches[1]
    } elseif ($line -match '^\s*prompt_profile:\s*"?([^"]*)"?\s*$') {
      $current.prompt_profile = $Matches[1]
    } elseif ($line -match '^\s*allow_non_first_lane:\s*"?([^"]*)"?\s*$') {
      $current.allow_non_first_lane = $Matches[1]
    }
  }
  if ($null -ne $current) { [void]$entries.Add([pscustomobject]$current) }
  return @($entries)
}

if (!(Test-Path -LiteralPath $ProjectRoot)) { throw "ProjectRoot not found: $ProjectRoot" }
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$workflowPath = Resolve-ProjectPath -Path $WorkflowFile
$queuePath = Resolve-ProjectPath -Path $QueueFile
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_GITHUB_ACTIONS_PREFLIGHT_PACKAGE_WORKFLOW_$stamp.json"
}

$workflowText = Get-Content -Raw -LiteralPath $workflowPath
$queue = Read-JsonFile -Path $queuePath
$queueLanes = @($queue.lanes | Sort-Object order | ForEach-Object { [string]$_.lane_id })
$matrix = Get-WorkflowMatrixEntries -WorkflowText $workflowText
$matrixLanes = @($matrix | ForEach-Object { [string]$_.lane_id })
$missingInWorkflow = @($queueLanes | Where-Object { $matrixLanes -notcontains $_ })
$extraInWorkflow = @($matrixLanes | Where-Object { $queueLanes -notcontains $_ })
$duplicates = @($matrixLanes | Group-Object | Where-Object Count -gt 1 | ForEach-Object { $_.Name })

$checks = @()
$checks += New-Check -Name "workflow_file_exists" -Passed (Test-Path -LiteralPath $workflowPath) -Observed (ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $workflowPath) -Expected "workflow exists"
$checks += New-Check -Name "queue_file_exists" -Passed (Test-Path -LiteralPath $queuePath) -Observed (ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $queuePath) -Expected "runtime queue exists"
$checks += New-Check -Name "workflow_matrix_count_matches_queue" -Passed ($matrixLanes.Count -eq $queueLanes.Count) -Observed $matrixLanes.Count -Expected $queueLanes.Count
$checks += New-Check -Name "workflow_matrix_lanes_match_queue" -Passed ($missingInWorkflow.Count -eq 0 -and $extraInWorkflow.Count -eq 0 -and $duplicates.Count -eq 0) -Observed ([ordered]@{ missing = $missingInWorkflow; extra = $extraInWorkflow; duplicates = $duplicates }) -Expected "same lane set, no duplicates"
$checks += New-Check -Name "first_lane_is_low_risk_without_non_first_override" -Passed ($matrix.Count -gt 0 -and [string]$matrix[0].lane_id -eq "sdxl_low_risk_fallback_lane" -and [string]$matrix[0].allow_non_first_lane -eq "false") -Observed ($(if ($matrix.Count -gt 0) { $matrix[0] } else { $null })) -Expected "first matrix row is low-risk lane with allow_non_first_lane=false"
$checks += New-Check -Name "non_first_rows_allow_non_first" -Passed (@($matrix | Select-Object -Skip 1 | Where-Object { [string]$_.allow_non_first_lane -ne "true" }).Count -eq 0) -Observed @($matrix | Select-Object -Skip 1 | ForEach-Object { "$($_.lane_id)=$($_.allow_non_first_lane)" }) -Expected "all non-first rows allow_non_first_lane=true"
$checks += New-Check -Name "model_registry_gate_wired" -Passed ($workflowText -like "*Test-WorkflowModelRegistryCoverage.ps1*") -Observed "Test-WorkflowModelRegistryCoverage.ps1" -Expected "model registry gate is wired"
$checks += New-Check -Name "authored_lane_gate_wired" -Passed ($workflowText -like "*Test-AuthoredLaneEvidenceCoverage.ps1*") -Observed "Test-AuthoredLaneEvidenceCoverage.ps1" -Expected "authored-lane coverage gate is wired"
$checks += New-Check -Name "runtime_queue_gate_wired" -Passed ($workflowText -like "*Test-RuntimeLaneQueue.ps1*") -Observed "Test-RuntimeLaneQueue.ps1" -Expected "runtime queue gate is wired"
$checks += New-Check -Name "runtime_queue_consumes_authored_gate_output" -Passed ($workflowText -like "*-CoverageFile*authored_lane_evidence_coverage.json*") -Observed "-CoverageFile authored_lane_evidence_coverage.json" -Expected "runtime queue gate uses same workflow-authored coverage JSON"
$checks += New-Check -Name "prerequisite_json_uploaded" -Passed ($workflowText -like "*ci_artifacts/workflow_prerequisite_matching/*.json*") -Observed "ci_artifacts/workflow_prerequisite_matching/*.json" -Expected "workflow prerequisite JSON uploaded"

$buildRoot = $null
$buildResults = @()
if ($RunLocalPackageBuild) {
  $shortBuildStamp = (Get-Date -Format "HHmmss")
  $buildRoot = Join-Path $ProjectRoot "runtime_artifacts\pf_$shortBuildStamp"
  foreach ($dir in @("m", "w", "r", "d")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $buildRoot $dir) | Out-Null
  }

  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "tools\Sync-WorkflowExports.ps1") -ProjectRoot $ProjectRoot | Out-Null
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1") -ProjectRoot $ProjectRoot -OutFile (Join-Path $buildRoot "m\model_registry_coverage.json") | Out-Null
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-AuthoredLaneEvidenceCoverage.ps1") -ProjectRoot $ProjectRoot -OutFile (Join-Path $buildRoot "w\authored_lane_evidence_coverage.json") | Out-Null
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1") -ProjectRoot $ProjectRoot -CoverageFile (Join-Path $buildRoot "w\authored_lane_evidence_coverage.json") -OutFile (Join-Path $buildRoot "w\runtime_lane_queue.json") | Out-Null

  foreach ($entry in $matrix) {
    $packageArgs = @(
      "-NoProfile",
      "-ExecutionPolicy", "Bypass",
      "-File", (Join-Path $ProjectRoot "tools\New-WorkflowRunPackage.ps1"),
      "-ProjectRoot", $ProjectRoot,
      "-LaneId", [string]$entry.lane_id,
      "-RunId", [string]$entry.run_id,
      "-PackageRoot", (Join-Path $buildRoot "r")
    )
    if (![string]::IsNullOrWhiteSpace([string]$entry.prompt_profile)) {
      $packageArgs += @("-PromptProfileFile", [string]$entry.prompt_profile)
    }
    if ([string]$entry.allow_non_first_lane -eq "true") {
      $packageArgs += "-AllowNonFirstLane"
    }
    & powershell @packageArgs | Out-Null
    $manifestPath = Join-Path $buildRoot "r\$($entry.run_id)\RUN_PACKAGE_MANIFEST.json"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "tools\New-EC2DeployBundle.ps1") -ProjectRoot $ProjectRoot -LaneId ([string]$entry.lane_id) -RunPackageManifestFile $manifestPath -OutDir (Join-Path $buildRoot "d\$($entry.run_id)") -BundleName ([string]$entry.run_id) | Out-Null
    $bundleManifestPath = Join-Path $buildRoot "d\$($entry.run_id)\DEPLOY_BUNDLE_MANIFEST.json"
    $packageManifest = Read-JsonFile -Path $manifestPath
    $bundleManifest = Read-JsonFile -Path $bundleManifestPath
    $bundleZipPath = Join-Path (Split-Path -Parent $bundleManifestPath) ([string]$bundleManifest.bundle_zip)
    $buildResults += [ordered]@{
      lane_id = [string]$entry.lane_id
      run_id = [string]$entry.run_id
      package_result = [string]$packageManifest.result
      package_manifest = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $manifestPath
      bundle_manifest = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $bundleManifestPath
      bundle_zip = [string]$bundleManifest.bundle_zip
      bundle_zip_exists = Test-Path -LiteralPath $bundleZipPath
      bundle_zip_sha256 = [string]$bundleManifest.bundle_zip_sha256
    }
  }

  $packageFailures = @($buildResults | Where-Object { [string]$_.package_result -ne "pass_local_only" })
  $missingZips = @($buildResults | Where-Object { -not [bool]$_.bundle_zip_exists })
  $checks += New-Check -Name "local_build_result_count_matches_matrix" -Passed ($buildResults.Count -eq $matrix.Count) -Observed $buildResults.Count -Expected $matrix.Count
  $checks += New-Check -Name "local_build_all_packages_pass" -Passed ($packageFailures.Count -eq 0) -Observed $packageFailures.Count -Expected 0
  $checks += New-Check -Name "local_build_all_bundle_zips_exist" -Passed ($missingZips.Count -eq 0) -Observed $missingZips.Count -Expected 0
}

$failures = @($checks | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "W66-GITHUB-ACTIONS-PREFLIGHT-PACKAGE-WORKFLOW-$stamp"
  created_at = $createdAt
  artifact_type = "github_actions_preflight_package_workflow_validation"
  tracker_ids = @("TRK-W66-RUNTIME-ORCHESTRATION")
  item_ids = @("ITEM-W66-RUNTIME-ORCHESTRATION")
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  masks_promoted = $false
  wave71_activated = $false
  jira_updated = $false
  workflow_file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $workflowPath
  queue_file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $queuePath
  workflow_matrix = $matrix
  queue_lanes = $queueLanes
  run_local_package_build = [bool]$RunLocalPackageBuild
  validation_root = $(if ($buildRoot) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $buildRoot } else { $null })
  local_build_results = $buildResults
  checks = $checks
  failed_check_count = $failures.Count
  failures = $failures
  result = $(if ($failures.Count -eq 0) { "pass_local_only" } else { "fail" })
  known_limits = @(
    "Does not run GitHub Actions remotely.",
    "Does not contact AWS or upload to S3.",
    "Does not start EC2, contact ComfyUI, or execute generation.",
    "Does not promote masks, certify gold masks, or activate Wave71+."
  )
  next_action = "Keep this validator as the reusable proof for preflight workflow lane/package drift before live upload or EC2 execution."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
Write-JsonNoBom -Value $record -Path $OutFile -Depth 80
$record | ConvertTo-Json -Depth 80
if ($record.result -ne "pass_local_only") { exit 1 }
