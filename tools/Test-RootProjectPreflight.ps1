<#
.SYNOPSIS
Runs a local-only preflight from C:\Comfy_UI_Main.

.DESCRIPTION
Checks the visible root scaffold, exported workflows, Git state, .env variable
names, model/runtime directories, active lane manifest, model registry coverage,
and static workflow validity without contacting AWS, GitHub APIs, Civitai,
ComfyUI, or EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Add-Check {
  param(
    [System.Collections.ArrayList]$Checks,
    [string]$Name,
    [bool]$Passed,
    [object]$Observed = $null,
    [string]$Message = ""
  )
  [void]$Checks.Add([ordered]@{
    name = $Name
    passed = $Passed
    observed = $Observed
    message = $Message
    result = $(if ($Passed) { "pass" } else { "fail" })
  })
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne ($Object.PSObject.Properties[$Name])
}

function Find-LatestFile {
  param(
    [Parameter(Mandatory=$true)][string]$Directory,
    [Parameter(Mandatory=$true)][string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $match = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $match) { return $null }
  return $match.FullName
}

function ConvertTo-RepoPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($ProjectRoot)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }
  $targetFull = [System.IO.Path]::GetFullPath($Path)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("\", "/")
}

function Test-EnvNamePresent {
  param(
    [Parameter(Mandatory=$true)][string]$EnvFile,
    [Parameter(Mandatory=$true)][string]$Name
  )
  if (!(Test-Path -LiteralPath $EnvFile)) { return $false }
  return Select-String -LiteralPath $EnvFile -Pattern ("^\s*" + [regex]::Escape($Name) + "\s*=") -Quiet
}

function Invoke-WorkflowStaticValidation {
  param(
    [Parameter(Mandatory=$true)][string]$LaneDir
  )
  $script = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"
  if (!(Test-Path -LiteralPath $script)) {
    throw "Static workflow validator missing: $script"
  }
  $jsonText = & powershell -NoProfile -ExecutionPolicy Bypass -File $script -ProjectRoot $ProjectRoot -LaneDir $LaneDir
  if ($LASTEXITCODE -ne 0) {
    throw "Static workflow validation command failed for $LaneDir"
  }
  return ($jsonText | Out-String | ConvertFrom-Json)
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 10
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

$checks = New-Object System.Collections.ArrayList
$workflowResults = New-Object System.Collections.ArrayList
$errors = New-Object System.Collections.ArrayList

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}

$rootManifestPath = Join-Path $ProjectRoot "PROJECT_ROOT_MANIFEST.json"
$activeLanesPath = Join-Path $ProjectRoot "Workflows\base_generation\ACTIVE_LANES.json"
$modelRegistryCoverageDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Model_Registry"
$envPath = Join-Path $ProjectRoot ".env"

Add-Check -Checks $checks -Name "project_root_exists" -Passed (Test-Path -LiteralPath $ProjectRoot) -Observed $ProjectRoot
Add-Check -Checks $checks -Name "git_directory_exists" -Passed (Test-Path -LiteralPath (Join-Path $ProjectRoot ".git")) -Observed (Join-Path $ProjectRoot ".git")

$gitRoot = $null
$gitHead = $null
$gitOrigin = $null
$gitStatus = $null
try {
  $gitRoot = (git -C $ProjectRoot rev-parse --show-toplevel 2>$null | Select-Object -First 1)
  $gitHead = (git -C $ProjectRoot rev-parse HEAD 2>$null | Select-Object -First 1)
  $gitOrigin = (git -C $ProjectRoot rev-parse origin/main 2>$null | Select-Object -First 1)
  $gitStatus = @(git -C $ProjectRoot status --porcelain)
} catch {
  [void]$errors.Add([ordered]@{ check = "git"; error = $_.Exception.Message })
}
Add-Check -Checks $checks -Name "git_root_is_project_root" -Passed ([System.IO.Path]::GetFullPath($gitRoot) -eq [System.IO.Path]::GetFullPath($ProjectRoot)) -Observed $gitRoot
Add-Check -Checks $checks -Name "git_head_matches_origin_main" -Passed (($gitHead -ne $null) -and ($gitHead -eq $gitOrigin)) -Observed ([ordered]@{ head = $gitHead; origin_main = $gitOrigin })
Add-Check -Checks $checks -Name "git_worktree_clean" -Passed (@($gitStatus).Count -eq 0) -Observed @($gitStatus)

$envIgnored = $false
try {
  $ignoreOutput = git -C $ProjectRoot check-ignore -v .env 2>$null
  $envIgnored = ($LASTEXITCODE -eq 0 -and ![string]::IsNullOrWhiteSpace(($ignoreOutput | Out-String)))
} catch {
  $envIgnored = $false
}
Add-Check -Checks $checks -Name "env_file_exists" -Passed (Test-Path -LiteralPath $envPath) -Observed ".env"
Add-Check -Checks $checks -Name "env_file_ignored" -Passed $envIgnored -Observed ".gitignore"
Add-Check -Checks $checks -Name "github_token_name_present" -Passed (Test-EnvNamePresent -EnvFile $envPath -Name "GITHUB_TOKEN") -Observed "GITHUB_TOKEN"
Add-Check -Checks $checks -Name "civitai_api_key_name_present" -Passed (Test-EnvNamePresent -EnvFile $envPath -Name "CIVITAI_API_KEY") -Observed "CIVITAI_API_KEY"

foreach ($requiredDir in @(
  "Plan",
  "Workflows",
  "Workflows\base_generation",
  "models\checkpoints",
  "models\loras",
  "models\vae",
  "models\controlnet",
  "models\embeddings",
  "configs\local",
  "configs\ec2",
  "runtime_artifacts\pullbacks",
  "runtime_artifacts\reviews",
  "runtime_artifacts\run_manifests"
)) {
  $path = Join-Path $ProjectRoot $requiredDir
  Add-Check -Checks $checks -Name "directory_exists:$($requiredDir.Replace('\','/'))" -Passed (Test-Path -LiteralPath $path) -Observed $requiredDir
}

$rootManifest = $null
$activeLanes = $null
try {
  $rootManifest = Read-JsonFile -Path $rootManifestPath
  Add-Check -Checks $checks -Name "root_manifest_json_valid" -Passed $true -Observed "PROJECT_ROOT_MANIFEST.json"
} catch {
  Add-Check -Checks $checks -Name "root_manifest_json_valid" -Passed $false -Observed "PROJECT_ROOT_MANIFEST.json" -Message $_.Exception.Message
}
try {
  $activeLanes = Read-JsonFile -Path $activeLanesPath
  Add-Check -Checks $checks -Name "active_lanes_json_valid" -Passed $true -Observed "Workflows/base_generation/ACTIVE_LANES.json"
} catch {
  Add-Check -Checks $checks -Name "active_lanes_json_valid" -Passed $false -Observed "Workflows/base_generation/ACTIVE_LANES.json" -Message $_.Exception.Message
}

if ($rootManifest -ne $null) {
  $ec2StartRequires = @()
  if ((Has-Property -Object $rootManifest -Name "active_runtime_queue") -and
      (Has-Property -Object $rootManifest.active_runtime_queue -Name "ec2_start_requires")) {
    $ec2StartRequires = @($rootManifest.active_runtime_queue.ec2_start_requires | ForEach-Object { [string]$_ })
  }
  $manifestRequiresModelCoverage = (@($ec2StartRequires | Where-Object { $_ -match "model registry coverage" }).Count -gt 0)
  Add-Check -Checks $checks -Name "root_manifest_requires_model_registry_coverage_gate" `
    -Passed $manifestRequiresModelCoverage `
    -Observed $ec2StartRequires `
    -Message "PROJECT_ROOT_MANIFEST.json active_runtime_queue.ec2_start_requires must include the model registry coverage gate."
}

if ($activeLanes -ne $null) {
  $laneCount = @($activeLanes.lanes).Count
  Add-Check -Checks $checks -Name "active_lane_count_at_least_two" -Passed ($laneCount -ge 2) -Observed $laneCount
  $firstLane = @($activeLanes.lanes | Sort-Object order | Select-Object -First 1)[0]
  Add-Check -Checks $checks -Name "first_lane_is_low_risk" -Passed ([string]$firstLane.lane_id -eq "sdxl_low_risk_fallback_lane") -Observed ([string]$firstLane.lane_id)

  foreach ($lane in @($activeLanes.lanes)) {
    $laneId = [string]$lane.lane_id
    $laneDir = Join-Path $ProjectRoot "Workflows\base_generation\$laneId"
    foreach ($property in @("workflow","smoke_request","runtime_requirements","patch_points")) {
      $rel = [string]$lane.$property
      $filePath = Join-Path $ProjectRoot $rel.Replace("/", "\")
      Add-Check -Checks $checks -Name "active_lane_file_exists:${laneId}:$property" -Passed (Test-Path -LiteralPath $filePath) -Observed $rel
    }

    try {
      $workflowResult = Invoke-WorkflowStaticValidation -LaneDir $laneDir
      [void]$workflowResults.Add([ordered]@{
        lane_id = $laneId
        lane_dir = "Workflows/base_generation/$laneId"
        qa_status = [string]$workflowResult.qa_status
        node_count = [int]$workflowResult.node_count
        link_count = [int]$workflowResult.link_count
        defect_count = @($workflowResult.defects).Count
        checkpoint = @($workflowResult.checkpoint_nodes | ForEach-Object { $_.ckpt_name })
      })
      Add-Check -Checks $checks -Name "workflow_static_validation:${laneId}" -Passed ([string]$workflowResult.qa_status -eq "pass") -Observed ([string]$workflowResult.qa_status)
    } catch {
      [void]$errors.Add([ordered]@{ check = "workflow_static_validation"; lane_id = $laneId; error = $_.Exception.Message })
      Add-Check -Checks $checks -Name "workflow_static_validation:${laneId}" -Passed $false -Observed "error" -Message $_.Exception.Message
    }
  }
}

$activeLaneIds = @()
if ($activeLanes -ne $null) {
  $activeLaneIds = @($activeLanes.lanes | ForEach-Object { [string]$_.lane_id } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

$modelRegistryCoverage = [ordered]@{
  evidence = $null
  found = $false
  json_valid = $false
  result = "missing_model_registry_coverage"
  failed_check_count = $null
  registry_record_count = $null
  runtime_validation_queue_row_count = $null
  active_lane_ids = @()
  lane_results = @()
  local_only = $false
  aws_contacted = $true
  github_api_contacted = $true
  civitai_contacted = $true
  comfyui_contacted = $true
  ec2_started = $true
  generation_executed = $true
  coverage_allows_root_ec2_static_proof = $false
}

$modelRegistryCoverageFile = Find-LatestFile -Directory $modelRegistryCoverageDir -Filter "W61_MODEL_REGISTRY_COVERAGE*.json"
$modelRegistryCoverage.evidence = ConvertTo-RepoPath -Path $modelRegistryCoverageFile
$modelRegistryCoverage.found = (![string]::IsNullOrWhiteSpace($modelRegistryCoverageFile) -and (Test-Path -LiteralPath $modelRegistryCoverageFile))
Add-Check -Checks $checks -Name "model_registry_coverage_evidence_found" `
  -Passed $modelRegistryCoverage.found `
  -Observed $(if ($modelRegistryCoverage.found) { $modelRegistryCoverage.evidence } else { "missing" }) `
  -Message "Latest model registry coverage evidence is required before EC2 static proof."

if ($modelRegistryCoverage.found) {
  try {
    $coverageJson = Read-JsonFile -Path $modelRegistryCoverageFile
    $modelRegistryCoverage.json_valid = $true
    Add-Check -Checks $checks -Name "model_registry_coverage_json_valid" -Passed $true -Observed $modelRegistryCoverage.evidence

    if (Has-Property -Object $coverageJson -Name "result") { $modelRegistryCoverage.result = [string]$coverageJson.result }
    foreach ($name in @("failed_check_count", "registry_record_count", "runtime_validation_queue_row_count")) {
      if (Has-Property -Object $coverageJson -Name $name) { $modelRegistryCoverage[$name] = [int]$coverageJson.$name }
    }
    foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")) {
      if (Has-Property -Object $coverageJson -Name $name) { $modelRegistryCoverage[$name] = [bool]$coverageJson.$name }
    }
    if (Has-Property -Object $coverageJson -Name "active_lane_ids") {
      $modelRegistryCoverage.active_lane_ids = @($coverageJson.active_lane_ids | ForEach-Object { [string]$_ })
    }

    Add-Check -Checks $checks -Name "model_registry_coverage_result_passes" `
      -Passed ($modelRegistryCoverage.result -eq "pass_local_only") `
      -Observed $modelRegistryCoverage.result
    Add-Check -Checks $checks -Name "model_registry_coverage_failed_check_count_zero" `
      -Passed ($modelRegistryCoverage.failed_check_count -eq 0) `
      -Observed $modelRegistryCoverage.failed_check_count
    Add-Check -Checks $checks -Name "model_registry_coverage_local_only" `
      -Passed ($modelRegistryCoverage.local_only -eq $true) `
      -Observed $modelRegistryCoverage.local_only
    Add-Check -Checks $checks -Name "model_registry_coverage_no_external_contact" `
      -Passed ($modelRegistryCoverage.aws_contacted -eq $false -and $modelRegistryCoverage.github_api_contacted -eq $false -and $modelRegistryCoverage.civitai_contacted -eq $false -and $modelRegistryCoverage.comfyui_contacted -eq $false) `
      -Observed ([ordered]@{
        aws_contacted = $modelRegistryCoverage.aws_contacted
        github_api_contacted = $modelRegistryCoverage.github_api_contacted
        civitai_contacted = $modelRegistryCoverage.civitai_contacted
        comfyui_contacted = $modelRegistryCoverage.comfyui_contacted
      })
    Add-Check -Checks $checks -Name "model_registry_coverage_no_ec2_or_generation" `
      -Passed ($modelRegistryCoverage.ec2_started -eq $false -and $modelRegistryCoverage.generation_executed -eq $false) `
      -Observed ([ordered]@{
        ec2_started = $modelRegistryCoverage.ec2_started
        generation_executed = $modelRegistryCoverage.generation_executed
      })

    $laneCoverageRows = @()
    foreach ($laneId in $activeLaneIds) {
      $selectedLane = $null
      if (Has-Property -Object $coverageJson -Name "lane_results") {
        $selectedLane = @($coverageJson.lane_results | Where-Object { [string]$_.lane_id -eq $laneId } | Select-Object -First 1)
      }
      $laneCovered = ($null -ne $selectedLane -and @($selectedLane).Count -gt 0)
      $laneResult = $(if ($laneCovered -and (Has-Property -Object $selectedLane[0] -Name "result")) { [string]$selectedLane[0].result } else { "missing" })
      $lanePass = ($laneCovered -and $laneResult -eq "pass")
      $laneCoverageRows += [ordered]@{
        lane_id = $laneId
        covered = $laneCovered
        result = $laneResult
        pass = $lanePass
      }
      Add-Check -Checks $checks -Name "model_registry_coverage_active_lane:${laneId}" `
        -Passed $lanePass `
        -Observed ([ordered]@{ covered = $laneCovered; result = $laneResult })
    }
    $modelRegistryCoverage.lane_results = @($laneCoverageRows)
    $modelRegistryCoverage.coverage_allows_root_ec2_static_proof = (
      $modelRegistryCoverage.result -eq "pass_local_only" -and
      $modelRegistryCoverage.failed_check_count -eq 0 -and
      $modelRegistryCoverage.local_only -eq $true -and
      $modelRegistryCoverage.aws_contacted -eq $false -and
      $modelRegistryCoverage.github_api_contacted -eq $false -and
      $modelRegistryCoverage.civitai_contacted -eq $false -and
      $modelRegistryCoverage.comfyui_contacted -eq $false -and
      $modelRegistryCoverage.ec2_started -eq $false -and
      $modelRegistryCoverage.generation_executed -eq $false -and
      @($laneCoverageRows | Where-Object { -not $_.pass }).Count -eq 0 -and
      @($laneCoverageRows).Count -gt 0
    )
    Add-Check -Checks $checks -Name "model_registry_coverage_allows_root_ec2_static_proof" `
      -Passed $modelRegistryCoverage.coverage_allows_root_ec2_static_proof `
      -Observed $modelRegistryCoverage.coverage_allows_root_ec2_static_proof
  } catch {
    Add-Check -Checks $checks -Name "model_registry_coverage_json_valid" -Passed $false -Observed $modelRegistryCoverage.evidence -Message $_.Exception.Message
  }
}

$failedChecks = @($checks | Where-Object { -not $_.passed })
$result = $(if (@($failedChecks).Count -eq 0 -and @($errors).Count -eq 0) { "pass_local_only" } else { "fail" })

$record = [ordered]@{
  evidence_id = "ROOT-LOCAL-PREFLIGHT-$((Get-Date).ToString('yyyyMMddTHHmmsszzz').Replace(':',''))"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  git = [ordered]@{
    root = $gitRoot
    head = $gitHead
    origin_main = $gitOrigin
    worktree_clean = (@($gitStatus).Count -eq 0)
  }
  checks = @($checks)
  failed_check_count = @($failedChecks).Count
  workflow_static_results = @($workflowResults)
  model_registry_coverage = $modelRegistryCoverage
  errors = @($errors)
  result = $result
  next_action = "Refresh AWS browser/SSO auth before EC2 static proof; local root scaffold and exported workflows are ready only if this preflight passes."
}

if ($OutFile) {
  $outDir = Split-Path -Parent $OutFile
  if ($outDir) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 10
}

$record | ConvertTo-Json -Depth 10
if ($result -ne "pass_local_only") {
  exit 1
}
