<#
.SYNOPSIS
Exercises root-project preflight behavior with disposable local Git fixtures.

.DESCRIPTION
Builds a minimal two-lane project fixture under the system temp directory, then
verifies clean success and fail-closed behavior for non-Git, dirty, divergent,
missing, malformed, empty-lane, and missing-coverage states. The authoritative
repository is read only and no external service or runtime is contacted.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
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

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine, $encoding)
}

function Write-TextNoBom {
  param(
    [Parameter(Mandatory=$true)][string]$Value,
    [Parameter(Mandatory=$true)][string]$Path
  )
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Value, $encoding)
}

function Invoke-GitCommand {
  param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][string[]]$Arguments
  )
  $output = & git -C $Root @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "Fixture git command failed: git -C $Root $($Arguments -join ' ') :: $($output | Out-String)"
  }
  return @($output)
}

function Commit-FixtureChange {
  param(
    [Parameter(Mandatory=$true)][string]$Root,
    [Parameter(Mandatory=$true)][string]$Message,
    [bool]$UpdateOrigin = $true
  )
  [void](Invoke-GitCommand -Root $Root -Arguments @("add", "-A"))
  [void](Invoke-GitCommand -Root $Root -Arguments @("commit", "-m", $Message))
  if ($UpdateOrigin) {
    $head = [string]((Invoke-GitCommand -Root $Root -Arguments @("rev-parse", "HEAD")) | Select-Object -First 1)
    [void](Invoke-GitCommand -Root $Root -Arguments @("update-ref", "refs/remotes/origin/main", $head))
  }
}

function New-BaseFixture {
  param([Parameter(Mandatory=$true)][string]$Name)

  $root = Join-Path $tempRoot $Name
  [System.IO.Directory]::CreateDirectory($root) | Out-Null
  foreach ($requiredDir in @(
    "Plan",
    "Plan\Instructions\QA\Scripts",
    "Plan\Instructions\QA\Evidence\Model_Registry",
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
    [System.IO.Directory]::CreateDirectory((Join-Path $root $requiredDir)) | Out-Null
  }

  Copy-Item -LiteralPath (Join-Path $ProjectRoot "PROJECT_ROOT_MANIFEST.json") -Destination (Join-Path $root "PROJECT_ROOT_MANIFEST.json")
  Copy-Item -LiteralPath (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1") -Destination (Join-Path $root "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1")

  $activeSource = Get-Content -LiteralPath (Join-Path $ProjectRoot "Workflows\base_generation\ACTIVE_LANES.json") -Raw | ConvertFrom-Json
  $selectedLanes = @($activeSource.lanes | Sort-Object order | Select-Object -First 2)
  foreach ($lane in $selectedLanes) {
    $laneId = [string]$lane.lane_id
    $sourceLane = Join-Path $ProjectRoot "Workflows\base_generation\$laneId"
    $targetLane = Join-Path $root "Workflows\base_generation\$laneId"
    Copy-Item -LiteralPath $sourceLane -Destination $targetLane -Recurse
  }
  $activeFixture = [ordered]@{
    schema_version = "1.0"
    updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    source_queue = "fixture"
    lanes = @($selectedLanes)
    runtime_boundaries = [ordered]@{
      ec2_start_allowed_by_this_manifest = $false
      generation_allowed_by_this_manifest = $false
      reason = "Disposable local regression fixture."
    }
  }
  Write-JsonNoBom -Value $activeFixture -Path (Join-Path $root "Workflows\base_generation\ACTIVE_LANES.json")

  $laneIds = @($selectedLanes | ForEach-Object { [string]$_.lane_id })
  $coverage = [ordered]@{
    schema_version = "1.0"
    result = "pass_local_only"
    failed_check_count = 0
    registry_record_count = $laneIds.Count
    runtime_validation_queue_row_count = $laneIds.Count
    active_lane_ids = @($laneIds)
    lane_results = @($laneIds | ForEach-Object { [ordered]@{ lane_id = $_; result = "pass" } })
    local_only = $true
    aws_contacted = $false
    github_api_contacted = $false
    civitai_contacted = $false
    comfyui_contacted = $false
    ec2_started = $false
    generation_executed = $false
  }
  Write-JsonNoBom -Value $coverage -Path (Join-Path $root "Plan\Instructions\QA\Evidence\Model_Registry\FIXTURE_MODEL_REGISTRY_COVERAGE.json")
  Write-TextNoBom -Value ".env`n" -Path (Join-Path $root ".gitignore")
  Write-TextNoBom -Value "GITHUB_TOKEN=<placeholder>`nCIVITAI_API_KEY=<placeholder>`n" -Path (Join-Path $root ".env")
  Write-TextNoBom -Value "fixture`n" -Path (Join-Path $root "fixture_marker.txt")

  [void](Invoke-GitCommand -Root $root -Arguments @("init", "-b", "main"))
  [void](Invoke-GitCommand -Root $root -Arguments @("config", "user.email", "fixture@example.invalid"))
  [void](Invoke-GitCommand -Root $root -Arguments @("config", "user.name", "Preflight Fixture"))
  [void](Invoke-GitCommand -Root $root -Arguments @("config", "core.autocrlf", "false"))
  Commit-FixtureChange -Root $root -Message "fixture baseline" -UpdateOrigin $true
  return $root
}

function Get-Check {
  param(
    [AllowNull()][object]$Payload,
    [Parameter(Mandatory=$true)][string]$Name
  )
  if ($null -eq $Payload) { return $null }
  return @($Payload.checks | Where-Object { [string]$_.name -eq $Name } | Select-Object -First 1)
}

function Invoke-RegressionCase {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$Mutation,
    [Parameter(Mandatory=$true)][string]$ExpectedResult,
    [Parameter(Mandatory=$true)][int]$ExpectedExitCode,
    [AllowNull()][string]$ExpectedFailedCheck
  )

  if ($Mutation -eq "non_git_root") {
    $fixtureRoot = Join-Path $tempRoot $Name
    [System.IO.Directory]::CreateDirectory($fixtureRoot) | Out-Null
  } else {
    $fixtureRoot = New-BaseFixture -Name $Name
    switch ($Mutation) {
      "none" { }
      "dirty_worktree" {
        Add-Content -LiteralPath (Join-Path $fixtureRoot "fixture_marker.txt") -Value "dirty"
      }
      "head_diverged" {
        Add-Content -LiteralPath (Join-Path $fixtureRoot "fixture_marker.txt") -Value "new head"
        Commit-FixtureChange -Root $fixtureRoot -Message "divergent head" -UpdateOrigin $false
      }
      "missing_root_manifest" {
        Remove-Item -LiteralPath (Join-Path $fixtureRoot "PROJECT_ROOT_MANIFEST.json") -Force
        Commit-FixtureChange -Root $fixtureRoot -Message "remove root manifest" -UpdateOrigin $true
      }
      "invalid_active_lanes" {
        Write-TextNoBom -Value "{ invalid json" -Path (Join-Path $fixtureRoot "Workflows\base_generation\ACTIVE_LANES.json")
        Commit-FixtureChange -Root $fixtureRoot -Message "invalidate active lanes" -UpdateOrigin $true
      }
      "empty_active_lanes" {
        Write-JsonNoBom -Value ([ordered]@{ schema_version = "1.0"; lanes = @() }) -Path (Join-Path $fixtureRoot "Workflows\base_generation\ACTIVE_LANES.json")
        Commit-FixtureChange -Root $fixtureRoot -Message "empty active lanes" -UpdateOrigin $true
      }
      "missing_model_coverage" {
        Remove-Item -LiteralPath (Join-Path $fixtureRoot "Plan\Instructions\QA\Evidence\Model_Registry\FIXTURE_MODEL_REGISTRY_COVERAGE.json") -Force
        Commit-FixtureChange -Root $fixtureRoot -Message "remove model coverage" -UpdateOrigin $true
      }
      default { throw "Unsupported fixture mutation: $Mutation" }
    }
  }

  $childOut = Join-Path $resultsRoot "$Name.json"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $preflightScript -ProjectRoot $fixtureRoot -OutFile $childOut *> $null
  $exitCode = $LASTEXITCODE
  $payload = $null
  if (Test-Path -LiteralPath $childOut -PathType Leaf) {
    try { $payload = Get-Content -LiteralPath $childOut -Raw | ConvertFrom-Json } catch { $payload = $null }
  }
  $targetCheck = if ([string]::IsNullOrWhiteSpace($ExpectedFailedCheck)) { $null } else { Get-Check -Payload $payload -Name $ExpectedFailedCheck }
  $targetCheckPass = if ([string]::IsNullOrWhiteSpace($ExpectedFailedCheck)) {
    $null -ne $payload -and [int]$payload.failed_check_count -eq 0
  } else {
    $null -ne $targetCheck -and @($targetCheck).Count -gt 0 -and -not [bool]$targetCheck[0].passed
  }
  $safetyPass = (
    $null -ne $payload -and [bool]$payload.local_only -and
    -not [bool]$payload.aws_contacted -and -not [bool]$payload.github_api_contacted -and
    -not [bool]$payload.civitai_contacted -and -not [bool]$payload.comfyui_contacted -and
    -not [bool]$payload.ec2_started -and -not [bool]$payload.generation_executed
  )
  $passed = (
    $exitCode -eq $ExpectedExitCode -and $null -ne $payload -and
    [string]$payload.result -eq $ExpectedResult -and $targetCheckPass -and $safetyPass
  )
  return [pscustomobject][ordered]@{
    name = $Name
    mutation = $Mutation
    result = $(if ($passed) { "pass" } else { "fail" })
    exit_code = $exitCode
    expected_exit_code = $ExpectedExitCode
    child_result = $(if ($null -ne $payload) { [string]$payload.result } else { $null })
    expected_result = $ExpectedResult
    output_exists = Test-Path -LiteralPath $childOut -PathType Leaf
    failed_check_count = $(if ($null -ne $payload) { [int]$payload.failed_check_count } else { $null })
    failed_check_names = $(if ($null -ne $payload) { @($payload.failed_check_names) } else { @() })
    child_git = $(if ($null -ne $payload) { $payload.git } else { $null })
    expected_failed_check = $ExpectedFailedCheck
    expected_check_failed = $targetCheckPass
    safety_pass = $safetyPass
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Authoritative project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$preflightScript = Join-Path $ProjectRoot "tools\Test-RootProjectPreflight.ps1"
if (-not (Test-Path -LiteralPath $preflightScript -PathType Leaf)) {
  throw "Root preflight script missing: $preflightScript"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("root_project_preflight_regression_{0}" -f ([guid]::NewGuid().ToString("N")))
$resultsRoot = Join-Path $tempRoot "results"
[System.IO.Directory]::CreateDirectory($resultsRoot) | Out-Null

$tests = @()
$tests += Invoke-RegressionCase -Name "clean_fixture_passes" -Mutation "none" -ExpectedResult "pass_local_only" -ExpectedExitCode 0 -ExpectedFailedCheck $null
$tests += Invoke-RegressionCase -Name "non_git_root_writes_failure" -Mutation "non_git_root" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "git_root_is_project_root"
$tests += Invoke-RegressionCase -Name "dirty_worktree_fails" -Mutation "dirty_worktree" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "git_worktree_clean"
$tests += Invoke-RegressionCase -Name "head_divergence_fails" -Mutation "head_diverged" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "git_head_matches_origin_main"
$tests += Invoke-RegressionCase -Name "missing_root_manifest_fails" -Mutation "missing_root_manifest" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "root_manifest_json_valid"
$tests += Invoke-RegressionCase -Name "invalid_active_lanes_fails" -Mutation "invalid_active_lanes" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "active_lanes_json_valid"
$tests += Invoke-RegressionCase -Name "empty_active_lanes_fails" -Mutation "empty_active_lanes" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "active_lane_count_at_least_two"
$tests += Invoke-RegressionCase -Name "missing_model_coverage_fails" -Mutation "missing_model_coverage" -ExpectedResult "fail" -ExpectedExitCode 1 -ExpectedFailedCheck "model_registry_coverage_evidence_found"

$failed = @($tests | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "root_project_preflight_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  failure_category = $(if ($failed.Count -eq 0) { $null } else { "root_project_preflight_regression_failed" })
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  work_order_id = "WO-W66-GLOBAL-GIT-CHECKPOINT-CLEAN"
  preflight_script = ConvertTo-ProjectRelativePath -Path $preflightScript
  test_count = $tests.Count
  passing_test_count = @($tests | Where-Object { [string]$_.result -eq "pass" }).Count
  failed_test_count = $failed.Count
  tests = @($tests)
  work_order_closed = $false
  target_runtime_proof = $false
  certification_claimed = $false
  boundary = "Disposable local fixture regression only. The authoritative repository Git state was not mutated and the global work order was not closed."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_ROOT_PROJECT_PREFLIGHT_REGRESSION_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
Write-JsonNoBom -Value $record -Path $outPath -Depth 20

$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd("\") + "\"
$tempResolved = [System.IO.Path]::GetFullPath($tempRoot)
if ($tempResolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $tempResolved -Recurse -Force
}

$record | ConvertTo-Json -Depth 20
if ($failed.Count -gt 0) { exit 1 }
exit 0
