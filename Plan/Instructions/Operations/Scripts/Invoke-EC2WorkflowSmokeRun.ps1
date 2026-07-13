<#
.SYNOPSIS
Coordinates a bounded EC2 ComfyUI workflow smoke run for a selected lane.

.DESCRIPTION
Dry-run by default. The dry run validates the local lane contract, finds the
latest auth gate and EC2 static proof records, builds the smoke request through
Invoke-ComfyWorkflowSmoke.ps1, and writes a gate/evidence record without
starting EC2 or posting a prompt.

With -Execute, this script requires:
- an auth gate proving account 029530099913 and safe_to_start_ec2=true
- a selected-lane readiness record allowing generation
- a static proof with passing object_info and model path/hash proof
- a verified same-window emergency-stop schedule before EC2 start

Only then does it start the approved EC2 instance, verify the same-window
instance watchdog after SSM is online, run the ComfyUI prompt remotely through
SSM, create a remote artifact manifest, optionally sync
artifacts through S3, create a local pullback record when artifacts arrive, and
stop the instance in a finally block.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$InstanceId = "i-0560bf8d143f93bb1",
  [string]$Region = "us-east-1",
  [string]$AuthGateFile = "",
  [string]$StaticProofFile = "",
  [string]$ReadinessFile = "",
  [string]$RuntimeWindowId = "",
  [string]$EmergencyStopEvidencePath = "",
  [string]$WatchdogEvidenceOutFile = "",
  [string[]]$PreservedGitExcludePath = @(),
  [string]$OutFile = "",
  [string]$OutRequestFile = "",
  [string]$RunPackageManifestFile = "",
  [string]$RunRecordFile = "",
  [string]$RemoteProjectRoot = "/home/ubuntu/Comfy_UI_Main",
  [string]$RemoteComfyRoot = "/home/ubuntu/ComfyUI",
  [string]$RemoteArtifactRoot = "/home/ubuntu/comfyui_artifacts",
  [string]$S3Bucket = "",
  [string]$S3Prefix = "",
  [string]$DeployBundleS3Uri = "",
  [string]$DeployBundleSha256 = "",
  [int]$ComfyPort = 8192,
  [int]$TimeoutSeconds = 900,
  [int]$PollSeconds = 3,
  [int]$MaxEc2RuntimeMinutes = 45,
  [switch]$AllowWatchdogOsShutdownFallback,
  [switch]$SkipGitLfsPull,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"
$startFailureClassifier = Join-Path $PSScriptRoot "EC2StartFailureClassification.ps1"
. $startFailureClassifier
$stopFailureClassifier = Join-Path $PSScriptRoot "EC2StopFailureClassification.ps1"
. $stopFailureClassifier
$runtimeSafetyGate = Join-Path $PSScriptRoot "EC2RuntimeWindowSafetyGate.ps1"
. $runtimeSafetyGate

function Get-RelativePathCompat {
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
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$ExcludePattern = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  $file = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

function Test-JsonMatchesLane {
  param(
    [object]$Payload,
    [string]$ExpectedLaneId
  )

  if ($null -eq $Payload -or [string]::IsNullOrWhiteSpace($ExpectedLaneId)) { return $false }
  if ((Has-Property -Object $Payload -Name "lane_id") -and [string]$Payload.lane_id -eq $ExpectedLaneId) {
    return $true
  }
  if (Has-Property -Object $Payload -Name "lane_dir") {
    $laneDirText = ([string]$Payload.lane_dir).Replace("\", "/").TrimEnd("/")
    return $laneDirText.EndsWith("/$ExpectedLaneId", [System.StringComparison]::OrdinalIgnoreCase)
  }
  return $false
}

function Find-LatestJsonByLaneId {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$ExpectedLaneId,
    [string]$ExcludePattern = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  foreach ($file in @($files | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

function Test-JsonContract {
  param([string[]]$Paths)

  $results = @()
  foreach ($path in $Paths) {
    $entry = [ordered]@{
      path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $path
      exists = (Test-Path -LiteralPath $path)
      json_valid = $false
      error = $null
    }
    if ($entry.exists) {
      try {
        $null = Read-JsonFile -Path $path
        $entry.json_valid = $true
      } catch {
        $entry.error = $_.Exception.Message
      }
    }
    $results += $entry
  }
  return $results
}

function Get-FileSha256Lower {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path)) { return $null }
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Resolve-ProjectPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Get-RunPackageStatus {
  param([string]$Path)

  $result = [ordered]@{
    supplied = $false
    file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    found = $false
    valid = $false
    errors = @()
    run_id = $null
    result = $null
    lane_id = $null
    lane_match = $false
    prompt_profile = [ordered]@{
      supplied = $false
      applied = $false
      profile_id = $null
      path = $null
    }
    prompt_request = [ordered]@{
      path = $null
      expected_sha256 = $null
      actual_sha256 = $null
      hash_match = $false
      json_valid = $false
      node_count = 0
      client_id = $null
    }
  }

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $result
  }

  $result.supplied = $true
  $manifestPath = Resolve-ProjectPath -Path $Path
  $result.file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $manifestPath
  if (!(Test-Path -LiteralPath $manifestPath)) {
    $result.errors += "Run package manifest not found: $Path"
    return $result
  }
  $result.found = $true

  try {
    $manifest = Read-JsonFile -Path $manifestPath
  } catch {
    $result.errors += "Run package manifest JSON parse failed: $($_.Exception.Message)"
    return $result
  }

  if (Has-Property -Object $manifest -Name "run_id") { $result.run_id = [string]$manifest.run_id }
  if (Has-Property -Object $manifest -Name "result") { $result.result = [string]$manifest.result }
  if (Has-Property -Object $manifest -Name "lane_id") { $result.lane_id = [string]$manifest.lane_id }
  $result.lane_match = ([string]$result.lane_id -eq [string]$LaneId)
  if (!$result.lane_match) {
    $result.errors += "Run package lane_id '$($result.lane_id)' does not match selected lane '$LaneId'."
  }
  if ([string]$result.result -ne "pass_local_only") {
    $result.errors += "Run package result is '$($result.result)', not pass_local_only."
  }
  if ((Has-Property -Object $manifest -Name "ec2_started") -and [bool]$manifest.ec2_started) {
    $result.errors += "Run package records ec2_started=true; expected a local-only package."
  }
  if ((Has-Property -Object $manifest -Name "generation_executed") -and [bool]$manifest.generation_executed) {
    $result.errors += "Run package records generation_executed=true; expected a pre-execution package."
  }
  if ((Has-Property -Object $manifest -Name "prompt_profile") -and $null -ne $manifest.prompt_profile) {
    $result.prompt_profile.supplied = [bool]$manifest.prompt_profile.supplied
    $result.prompt_profile.applied = [bool]$manifest.prompt_profile.applied
    if (Has-Property -Object $manifest.prompt_profile -Name "profile_id") {
      $result.prompt_profile.profile_id = [string]$manifest.prompt_profile.profile_id
    }
    if (Has-Property -Object $manifest.prompt_profile -Name "path") {
      $result.prompt_profile.path = [string]$manifest.prompt_profile.path
    }
  }

  $promptRequestPath = $null
  $expectedHash = $null
  if (Has-Property -Object $manifest -Name "generated_files") {
    $promptGenerated = @($manifest.generated_files | Where-Object { [string]$_.path -match '(^|/)prompt_request\.json$' } | Select-Object -First 1)
    if ($promptGenerated.Count -gt 0) {
      $promptRequestPath = [string]$promptGenerated[0].path
      if (Has-Property -Object $promptGenerated[0] -Name "sha256") {
        $expectedHash = ([string]$promptGenerated[0].sha256).ToLowerInvariant()
      }
    }
  }
  if ([string]::IsNullOrWhiteSpace($promptRequestPath) -and
      (Has-Property -Object $manifest -Name "package_dir") -and
      ![string]::IsNullOrWhiteSpace([string]$manifest.package_dir)) {
    $promptRequestPath = ([string]$manifest.package_dir).TrimEnd("/", "\") + "/prompt_request.json"
  }
  if ([string]::IsNullOrWhiteSpace($expectedHash) -and
      (Has-Property -Object $manifest -Name "prompt_request") -and
      $null -ne $manifest.prompt_request -and
      (Has-Property -Object $manifest.prompt_request -Name "sha256")) {
    $expectedHash = ([string]$manifest.prompt_request.sha256).ToLowerInvariant()
  }
  if ([string]::IsNullOrWhiteSpace($promptRequestPath)) {
    $result.errors += "Run package manifest does not identify prompt_request.json."
    return $result
  }

  $promptFullPath = Resolve-ProjectPath -Path $promptRequestPath
  $result.prompt_request.path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $promptFullPath
  $result.prompt_request.expected_sha256 = $expectedHash
  if (!(Test-Path -LiteralPath $promptFullPath)) {
    $result.errors += "Run package prompt_request.json not found: $promptRequestPath"
    return $result
  }

  $actualHash = Get-FileSha256Lower -Path $promptFullPath
  $result.prompt_request.actual_sha256 = $actualHash
  $result.prompt_request.hash_match = (![string]::IsNullOrWhiteSpace($expectedHash) -and $actualHash -eq $expectedHash)
  if (![string]::IsNullOrWhiteSpace($expectedHash) -and !$result.prompt_request.hash_match) {
    $result.errors += "Run package prompt_request.json sha256 does not match manifest."
  }

  try {
    $request = Read-JsonFile -Path $promptFullPath
    $result.prompt_request.json_valid = $true
    if (Has-Property -Object $request -Name "client_id") {
      $result.prompt_request.client_id = [string]$request.client_id
    }
    if ((Has-Property -Object $request -Name "prompt") -and $null -ne $request.prompt) {
      $result.prompt_request.node_count = @($request.prompt.PSObject.Properties).Count
    } else {
      $result.errors += "Run package prompt_request.json has no prompt object."
    }
  } catch {
    $result.errors += "Run package prompt_request.json parse failed: $($_.Exception.Message)"
  }

  $result.valid = ($result.errors.Count -eq 0)
  return $result
}

function Test-StaticProof {
  param([string]$Path)

  $result = [ordered]@{
    file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    supplied = $false
    found = $false
    valid = $false
    errors = @()
    object_info_status = $null
    model_proof_count = 0
    dry_run_record = $false
    lane_id = $null
    lane_match = $false
  }

  if ([string]::IsNullOrWhiteSpace($Path)) {
    $result.errors += "No EC2 static proof file supplied or found."
    return $result
  }
  $result.supplied = $true
  if (!(Test-Path -LiteralPath $Path)) {
    $result.errors += "EC2 static proof file not found: $Path"
    return $result
  }
  $result.found = $true

  $proof = Read-JsonFile -Path $Path
  $proofPayload = $proof
  if (Has-Property -Object $proof -Name "lane_id") {
    $result.lane_id = [string]$proof.lane_id
  }
  if ((Has-Property -Object $proof -Name "mode") -and [string]$proof.mode -eq "dry_run") {
    $result.dry_run_record = $true
    $result.lane_match = ([string]$result.lane_id -eq [string]$LaneId)
    if (!$result.lane_match) {
      $result.errors += "EC2 static proof lane_id '$($result.lane_id)' does not match selected lane '$LaneId'."
    }
    $result.errors += "EC2 static proof is a dry-run plan, not object-info/path/hash proof."
    return $result
  }

  if (Has-Property -Object $proof -Name "stdout") {
    if ([string]::IsNullOrWhiteSpace([string]$proof.stdout)) {
      $result.errors += "EC2 static proof stdout is empty."
      return $result
    }
    try {
      $proofPayload = ([string]$proof.stdout | ConvertFrom-Json)
      if (Has-Property -Object $proofPayload -Name "lane_id") {
        $result.lane_id = [string]$proofPayload.lane_id
      }
    } catch {
      $result.errors += "EC2 static proof stdout is not valid JSON: $($_.Exception.Message)"
      return $result
    }
    if ((Has-Property -Object $proof -Name "command_status") -and [string]$proof.command_status -ne "Success") {
      $result.errors += "EC2 static proof command_status is $($proof.command_status), not Success."
    }
    if ((Has-Property -Object $proof -Name "final_state") -and [string]$proof.final_state -ne "stopped") {
      $result.errors += "EC2 static proof final_state is $($proof.final_state), not stopped."
    }
  }

  if (!(Has-Property -Object $proofPayload -Name "object_info")) {
    $result.errors += "EC2 static proof payload has no object_info."
  } else {
    $result.object_info_status = [string]$proofPayload.object_info.status
    if ([string]$proofPayload.object_info.status -ne "pass") {
      $result.errors += "EC2 static proof object_info status is $($proofPayload.object_info.status), not pass."
    }
  }

  if (!(Has-Property -Object $proofPayload -Name "model_proofs")) {
    $result.errors += "EC2 static proof payload has no model_proofs."
  } else {
    $models = @($proofPayload.model_proofs)
    $result.model_proof_count = $models.Count
    if ($models.Count -eq 0) {
      $result.errors += "EC2 static proof has zero model_proofs."
    }
    foreach ($model in $models) {
      if (-not [bool]$model.exists) {
        $result.errors += "Required model missing in EC2 static proof: $($model.relative_path)"
      }
      if ([string]::IsNullOrWhiteSpace([string]$model.sha256)) {
        $result.errors += "Required model missing sha256 in EC2 static proof: $($model.relative_path)"
      }
    }
  }

  $result.lane_match = ([string]$result.lane_id -eq [string]$LaneId)
  if (!$result.lane_match) {
    $result.errors += "EC2 static proof lane_id '$($result.lane_id)' does not match selected lane '$LaneId'."
  }

  $result.valid = ($result.errors.Count -eq 0)
  return $result
}

function Get-AuthGateStatus {
  param([string]$Path)

  $result = [ordered]@{
    file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    found = (![string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path))
    expected_account = "029530099913"
    account_match = $false
    ec2_work_allowed = $false
    safe_to_start_ec2 = $false
    generation_allowed = $false
    result = "missing_auth_gate"
    status = "missing_auth_gate"
    failure_category = "missing_auth_gate"
    remote_login_status = "missing_auth_gate"
  }

  if (!$result.found) { return $result }
  $auth = Read-JsonFile -Path $Path
  $result.failure_category = $null
  $result.remote_login_status = $null
  $result.expected_account = [string]$auth.expected_account
  $result.ec2_work_allowed = [bool]$auth.ec2_work_allowed
  $result.safe_to_start_ec2 = [bool]$auth.safe_to_start_ec2
  $result.generation_allowed = [bool]$auth.generation_allowed
  if (Has-Property -Object $auth -Name "result") {
    $result.result = [string]$auth.result
  } else {
    $result.result = $(if ($result.safe_to_start_ec2) { "pass" } else { "blocked" })
  }
  if (Has-Property -Object $auth -Name "failure_category") {
    $result.failure_category = $auth.failure_category
  }
  if (Has-Property -Object $auth -Name "account_match") {
    $result.account_match = [bool]$auth.account_match
  }
  if (Has-Property -Object $auth -Name "remote_login_status") {
    $result.remote_login_status = [string]$auth.remote_login_status
  }
  if ((Has-Property -Object $auth -Name "sts_after") -and $null -ne $auth.sts_after) {
    $result.account_match = [bool]$auth.sts_after.account_match
    if ([string]::IsNullOrWhiteSpace([string]$result.failure_category)) {
      $result.failure_category = [string]$auth.sts_after.failure_category
    }
  } elseif ((Has-Property -Object $auth -Name "sts_before") -and $null -ne $auth.sts_before) {
    $result.account_match = [bool]$auth.sts_before.account_match
    if ([string]::IsNullOrWhiteSpace([string]$result.failure_category)) {
      $result.failure_category = [string]$auth.sts_before.failure_category
    }
  }
  if ((Has-Property -Object $auth -Name "remote_login") -and $null -ne $auth.remote_login) {
    $result.remote_login_status = [string]$auth.remote_login.status
  }
  $result.status = $(if ($result.safe_to_start_ec2) { "pass" } else { "blocked" })
  return $result
}

function Invoke-SmokeRequestDryRun {
  param(
    [string]$SmokeScript,
    [string]$LaneDirectory,
    [string]$ProofFile,
    [string]$RequestOutFile
  )

  $arguments = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $SmokeScript,
    "-ProjectRoot",
    $ProjectRoot,
    "-LaneDir",
    $LaneDirectory
  )
  if (![string]::IsNullOrWhiteSpace($ProofFile)) {
    $arguments += @("-StaticProofFile", $ProofFile)
  }
  if (![string]::IsNullOrWhiteSpace($RequestOutFile)) {
    $arguments += @("-OutRequestFile", $RequestOutFile)
  }

  $output = & powershell @arguments 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  $summary = [ordered]@{
    attempted = $true
    exit_code = $LASTEXITCODE
    request_file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RequestOutFile
    request_file_exists = (![string]::IsNullOrWhiteSpace($RequestOutFile) -and (Test-Path -LiteralPath $RequestOutFile))
    json_parsed = $false
    execution_allowed = $false
    generation_executed = $false
    errors = @()
  }
  try {
    $jsonStart = $text.IndexOf("{")
    if ($jsonStart -ge 0) {
      $payload = $text.Substring($jsonStart) | ConvertFrom-Json
      $summary.json_parsed = $true
      $summary.execution_allowed = [bool]$payload.execution_allowed
      $summary.generation_executed = [bool]$payload.generation_executed
      if (Has-Property -Object $payload -Name "errors") {
        $summary.errors = @($payload.errors)
      }
    } else {
      $summary.errors += "Smoke helper did not emit JSON."
    }
  } catch {
    $summary.errors += "Smoke helper JSON parse failed: $($_.Exception.Message)"
  }
  if ($summary.exit_code -ne 0) {
    $summary.errors += "Smoke helper dry-run exited $($summary.exit_code)."
  }
  return $summary
}

function Copy-RunPackageRequest {
  param(
    [System.Collections.IDictionary]$RunPackage,
    [string]$RequestOutFile
  )

  $summary = [ordered]@{
    attempted = $true
    source = "run_package"
    exit_code = 1
    request_file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RequestOutFile
    request_file_exists = $false
    json_parsed = $false
    execution_allowed = $false
    generation_executed = $false
    run_package_id = $RunPackage.run_id
    prompt_profile_id = $RunPackage.prompt_profile.profile_id
    prompt_request_sha256 = $RunPackage.prompt_request.actual_sha256
    errors = @()
  }

  if (!$RunPackage.valid) {
    $summary.errors = @($RunPackage.errors)
    return $summary
  }

  $sourcePath = Resolve-ProjectPath -Path ([string]$RunPackage.prompt_request.path)
  try {
    $requestDir = Split-Path -Parent $RequestOutFile
    if (![string]::IsNullOrWhiteSpace($requestDir)) {
      $null = New-Item -ItemType Directory -Force -Path $requestDir
    }
    Copy-Item -LiteralPath $sourcePath -Destination $RequestOutFile -Force
    $summary.request_file_exists = (Test-Path -LiteralPath $RequestOutFile)
    $request = Read-JsonFile -Path $RequestOutFile
    $summary.json_parsed = $true
    if (!(Has-Property -Object $request -Name "prompt")) {
      $summary.errors += "Copied run package request has no prompt object."
    }
    $summary.exit_code = $(if ($summary.errors.Count -eq 0) { 0 } else { 1 })
  } catch {
    $summary.errors += "Run package request copy/parse failed: $($_.Exception.Message)"
  }

  return $summary
}

function Invoke-AwsCliJson {
  param([string[]]$Arguments)

  $output = & aws @Arguments 2>&1
  $text = (($output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
  return [ordered]@{
    exit_code = $LASTEXITCODE
    output = $text
  }
}

function Get-TailText {
  param(
    [string]$Text,
    [int]$MaxChars = 4000
  )

  if ([string]::IsNullOrEmpty($Text)) { return "" }
  if ($Text.Length -le $MaxChars) { return $Text }
  return $Text.Substring($Text.Length - $MaxChars)
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$runId = "aws_gpu_workflow_smoke_$stamp"
$startTime = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

$envLoader = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1"
if (Test-Path -LiteralPath $envLoader) {
  . $envLoader -ProjectRoot $ProjectRoot -Quiet
}
if ([string]::IsNullOrWhiteSpace($S3Bucket) -and ![string]::IsNullOrWhiteSpace($env:S3_MODEL_BUCKET)) {
  $S3Bucket = $env:S3_MODEL_BUCKET
}
if ([string]::IsNullOrWhiteSpace($S3Prefix) -and ![string]::IsNullOrWhiteSpace($env:S3_RENDER_OUTPUT_PREFIX)) {
  $S3Prefix = $env:S3_RENDER_OUTPUT_PREFIX
}
if ([string]::IsNullOrWhiteSpace($S3Prefix)) {
  $S3Prefix = "comfy-ui-main/pullback"
}
$S3Prefix = $S3Prefix.Trim("/")

$laneDir = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\$LaneId"
$workflowPath = Join-Path $laneDir "workflow.api.json"
$patchPath = Join-Path $laneDir "patch_points.json"
$runtimePath = Join-Path $laneDir "runtime_requirements.json"
$smokePath = Join-Path $laneDir "smoke_test_request.json"
$smokeScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-ComfyWorkflowSmoke.ps1"
$pullbackScript = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1"
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
$workflowRuntimeDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime"
$pullbackRoot = Join-Path $ProjectRoot "Plan\Instructions\Operations\Pulled_Back_Artifacts"
if ([string]::IsNullOrWhiteSpace($WatchdogEvidenceOutFile)) {
  $WatchdogEvidenceOutFile = Join-Path $runtimeReadinessDir "W64_EC2_INSTANCE_WATCHDOG_EXECUTION_$stamp.json"
}

if ([string]::IsNullOrWhiteSpace($AuthGateFile)) {
  $AuthGateFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "*AWS_AUTH_GATE*.json"
}
if ([string]::IsNullOrWhiteSpace($StaticProofFile)) {
  $StaticProofFile = Find-LatestJsonByLaneId -Directory $workflowStaticDir -Filter "*EC2_LANE_STATIC_PROOF_*.json" -ExpectedLaneId $LaneId -ExcludePattern "DRY_RUN|BLOCKED_EXECUTE"
}
if ([string]::IsNullOrWhiteSpace($ReadinessFile)) {
  $ReadinessFile = Find-LatestJsonByLaneId -Directory $runtimeReadinessDir -Filter "*LANE_RUNTIME_READINESS_*.json" -ExpectedLaneId $LaneId
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $workflowRuntimeDir ("W61_EC2_WORKFLOW_SMOKE_RUN_{0}_{1}.json" -f $(if ($Execute) { "EXECUTION" } else { "DRY_RUN" }), $stamp)
}
if ([string]::IsNullOrWhiteSpace($RunRecordFile)) {
  $RunRecordFile = Join-Path $ProjectRoot "Plan\Instructions\Operations\Run_Records\$runId.json"
}

$laneContracts = Test-JsonContract -Paths @($workflowPath, $patchPath, $runtimePath, $smokePath)
$laneContractValid = (@($laneContracts | Where-Object { -not $_.exists -or -not $_.json_valid }).Count -eq 0)
$authGate = Get-AuthGateStatus -Path $AuthGateFile
$readinessGate = Get-EC2LaneReadinessStatus -Path $ReadinessFile -ExpectedLaneId $LaneId
$staticProof = Test-StaticProof -Path $StaticProofFile
$localGitGate = Get-LocalGitCheckpointGate -ProjectRoot $ProjectRoot -PreservedExcludePath $PreservedGitExcludePath
$runPackage = Get-RunPackageStatus -Path $RunPackageManifestFile
$runtimeWindowIdValid = ($RuntimeWindowId -cmatch "^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$")
$emergencyStopGate = Get-EmergencyStopScheduleStatus -Path $EmergencyStopEvidencePath -ExpectedWindowId $RuntimeWindowId -ExpectedInstanceId $InstanceId -ExpectedRegion $Region

if ([string]::IsNullOrWhiteSpace($OutRequestFile)) {
  $null = New-Item -ItemType Directory -Force -Path $workflowRuntimeDir
  $requestFile = Join-Path $workflowRuntimeDir ("W61_EC2_WORKFLOW_SMOKE_RUN_REQUEST_$stamp.json")
} else {
  $requestFile = $OutRequestFile
  $requestDir = Split-Path -Parent $requestFile
  if (![string]::IsNullOrWhiteSpace($requestDir)) {
    $null = New-Item -ItemType Directory -Force -Path $requestDir
  }
}
$requestSource = $(if ($runPackage.supplied) { "run_package" } else { "lane_smoke_request" })
if ($runPackage.supplied) {
  $smokeRequest = Copy-RunPackageRequest -RunPackage $runPackage -RequestOutFile $requestFile
} else {
  $smokeRequest = Invoke-SmokeRequestDryRun -SmokeScript $smokeScript -LaneDirectory $laneDir -ProofFile $StaticProofFile -RequestOutFile $requestFile
  $smokeRequest["source"] = "lane_smoke_request"
}
$smokeRequestReady = ($smokeRequest.exit_code -eq 0 -and $smokeRequest.json_parsed -and $smokeRequest.request_file_exists)

$blockedReasons = @()
if ($InstanceId -ne "i-0560bf8d143f93bb1") { $blockedReasons += "InstanceId is not the approved EC2 instance." }
if (!$runtimeWindowIdValid) { $blockedReasons += "RuntimeWindowId is missing or invalid." }
if (!$emergencyStopGate.verified) { $blockedReasons += "Same-window live emergency-stop schedule is not verified." }
if (!$laneContractValid) { $blockedReasons += "Selected lane JSON contract is missing or invalid." }
if ($runPackage.supplied -and !$runPackage.valid) { $blockedReasons += "Run package manifest/request is invalid." }
if ($localGitGate.result -ne "pass") { $blockedReasons += "Local Git checkpoint gate is not clean and synced to origin/main." }
if (!$authGate.safe_to_start_ec2) { $blockedReasons += "Auth gate does not allow EC2 start." }
if ($readinessGate.found -and !$readinessGate.lane_match) { $blockedReasons += "Lane readiness file does not match selected lane $LaneId." }
if (!$readinessGate.ready_for_generation) { $blockedReasons += "Lane readiness gate does not allow generation." }
if ($staticProof.found -and !$staticProof.lane_match) { $blockedReasons += "EC2 static proof file does not match selected lane $LaneId." }
if (!$staticProof.valid) { $blockedReasons += "EC2 object-info/path/hash static proof is missing or invalid." }
if (!$smokeRequestReady) { $blockedReasons += "Smoke request dry-run did not produce a valid request body." }

$executeGatesPass = ($blockedReasons.Count -eq 0)
$gateFailureCategory = $null
if ($InstanceId -ne "i-0560bf8d143f93bb1") {
  $gateFailureCategory = "unapproved_instance"
} elseif (!$runtimeWindowIdValid) {
  $gateFailureCategory = "missing_or_invalid_runtime_window_id"
} elseif (!$emergencyStopGate.verified) {
  $gateFailureCategory = [string]$emergencyStopGate.failure_category
} elseif (!$laneContractValid) {
  $gateFailureCategory = "lane_contract_invalid"
} elseif ($runPackage.supplied -and !$runPackage.valid) {
  $gateFailureCategory = "run_package_invalid"
} elseif ($localGitGate.result -ne "pass") {
  $gateFailureCategory = $(if ([int]$localGitGate.staged_count -gt 0) { "local_git_staged_changes_present" } elseif ([int]$localGitGate.unexpected_dirty_count -gt 0) { "local_git_unexpected_dirty_paths" } elseif ($localGitGate.local_matches_origin -ne $true) { "local_git_not_synced_to_origin" } else { "local_git_checkpoint_invalid" })
} elseif (!$authGate.safe_to_start_ec2) {
  $gateFailureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$authGate.failure_category)) { [string]$authGate.failure_category } else { "aws_auth_blocked" })
} elseif ($readinessGate.found -and !$readinessGate.lane_match) {
  $gateFailureCategory = "lane_readiness_mismatch"
} elseif (!$readinessGate.ready_for_generation) {
  $gateFailureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$readinessGate.failure_category)) { [string]$readinessGate.failure_category } else { "lane_readiness_blocked" })
} elseif ($staticProof.found -and !$staticProof.lane_match) {
  $gateFailureCategory = "ec2_static_proof_lane_mismatch"
} elseif (!$staticProof.valid) {
  $gateFailureCategory = "missing_ec2_static_proof"
} elseif (!$smokeRequestReady) {
  $gateFailureCategory = "smoke_request_invalid"
}

$record = [ordered]@{
  evidence_id = "EC2-WORKFLOW-SMOKE-RUN-" + $stamp
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  mode = $(if ($Execute) { "execute" } else { "dry_run" })
  run_id = $runId
  lane_id = $LaneId
  runtime_window_id = $RuntimeWindowId
  instance_id = $InstanceId
  region = $Region
  remote_project_root = $RemoteProjectRoot
  remote_comfy_root = $RemoteComfyRoot
  remote_artifact_root = "$RemoteArtifactRoot/$runId"
  comfy_port = $ComfyPort
  timeout_seconds = $TimeoutSeconds
  max_ec2_runtime_minutes = $MaxEc2RuntimeMinutes
  git_lfs_pull_skipped = [bool]$SkipGitLfsPull.IsPresent
  deploy_bundle_s3_uri = $DeployBundleS3Uri
  deploy_bundle_sha256 = $DeployBundleSha256
  result = $(if ($executeGatesPass) { "ready_for_workflow_smoke_execute" } elseif ($Execute) { "blocked_before_ec2_start" } else { "dry_run_blocked_before_ec2_start" })
  failure_category = $gateFailureCategory
  lane_contracts = $laneContracts
  local_git_checkpoint_gate = $localGitGate
  emergency_stop_gate = $emergencyStopGate
  instance_watchdog = $null
  watchdog_evidence_out_file = $WatchdogEvidenceOutFile
  auth_gate = $authGate
  readiness_gate = $readinessGate
  ec2_static_proof = $staticProof
  run_package = $runPackage
  request_source = $requestSource
  smoke_request = $smokeRequest
  execute_gates_pass = $executeGatesPass
  blocked_reasons = $blockedReasons
  dry_run_actions = @(
    "Load .env without printing values.",
    "Require auth gate for AWS account 029530099913 before EC2 start.",
    "Require a same-window live emergency-stop schedule before EC2 start.",
    "Require selected-lane readiness gate before generation.",
    "Require EC2 object-info/path/hash static proof before generation.",
    "After SSM is online, start and verify the same-window instance watchdog before posting /prompt.",
    $(if ($runPackage.supplied) { "Load the validated run package prompt_request.json as the bounded ComfyUI /prompt body." } else { "Build the patched ComfyUI /prompt request body locally." }),
    "With -Execute only, start i-0560bf8d143f93bb1, run Git LFS only when needed, run remote ComfyUI smoke, create artifact manifest, pull back artifacts when S3 is available, then stop EC2."
  )
  generation_executed = $false
  ec2_started = $false
  command_id = $null
  command_status = "not_started"
  start_state = $null
  start_exit_code = $null
  start_output_tail = $null
  stop_exit_code = $null
  stop_output_tail = $null
  stop_failure_category = $null
  final_state = $null
  remote_result = $null
  local_pullback = [ordered]@{
    attempted = $false
    status = "not_attempted"
  }
  run_record_file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RunRecordFile
  errors = @()
  next_action = $(if ($executeGatesPass) { "Run with -Execute to perform the bounded EC2 smoke run, pull back artifacts, then perform image QA." } else { "Resolve blocked_reasons before any EC2 workflow smoke execution." })
}

if (!$Execute) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote EC2 workflow smoke run dry-run record: $OutFile"
  $record | ConvertTo-Json -Depth 40
  exit 0
}

if (!$executeGatesPass) {
  $record.errors += "Execution blocked by gate failures. EC2 was not started."
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote blocked EC2 workflow smoke run record: $OutFile"
  $record | ConvertTo-Json -Depth 40
  exit 2
}

$requestJson = Get-Content -LiteralPath $requestFile -Raw
$requestBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($requestJson))
$expectedRemoteGitHead = [string]$localGitGate.expected_remote_head
$s3BucketForRemote = $S3Bucket
$s3PrefixForRemote = "$S3Prefix/$runId".Trim("/")
$ssmExecutionTimeoutSeconds = [Math]::Min([Math]::Max(600, $TimeoutSeconds + 900), [Math]::Max(600, $MaxEc2RuntimeMinutes * 60))
$remoteScript = @"
python3 - <<'PY'
import base64, datetime, glob, hashlib, json, os, shutil, signal, subprocess, tempfile, time, traceback, urllib.error, urllib.request, zipfile

RUN_ID = "$runId"
LANE_ID = "$LaneId"
PROJECT = "$RemoteProjectRoot"
COMFY = "$RemoteComfyRoot"
ARTIFACT_ROOT = "$RemoteArtifactRoot/$runId"
REQUEST_B64 = "$requestBase64"
EXPECTED_GIT_HEAD = "$expectedRemoteGitHead"
SKIP_GIT_LFS_PULL = "$($SkipGitLfsPull.IsPresent)".lower() == "true"
DEPLOY_BUNDLE_S3_URI = "$DeployBundleS3Uri"
DEPLOY_BUNDLE_SHA256 = "$DeployBundleSha256".strip().lower()
PORT = $ComfyPort
TIMEOUT_SECONDS = $TimeoutSeconds
POLL_SECONDS = $PollSeconds
S3_BUCKET = "$s3BucketForRemote"
S3_PREFIX = "$s3PrefixForRemote"

result = {
    "run_id": RUN_ID,
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "remote_project": PROJECT,
    "remote_comfy_root": COMFY,
    "artifact_root": ARTIFACT_ROOT,
    "prompt_id": None,
    "output_images": [],
    "manifest_path": None,
    "s3_sync": {"attempted": False, "succeeded": False, "s3_uri": None},
    "errors": []
}

def run(cmd, cwd=None, timeout=300, check=False):
    p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError("command failed rc=%s: %s\nSTDOUT=%s\nSTDERR=%s" % (p.returncode, " ".join(cmd), p.stdout[-1000:], p.stderr[-1000:]))
    return {"rc": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def normalized_bundle_member_name(name):
    normalized = str(name).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("content/"):
        normalized = normalized[len("content/"):]
    return normalized

def apply_deploy_bundle_if_configured():
    if not DEPLOY_BUNDLE_S3_URI:
        return None
    os.makedirs(PROJECT, exist_ok=True)
    bundle_path = os.path.join(tempfile.gettempdir(), "codex_deploy_bundle_%s.zip" % int(time.time()))
    download = run(["aws", "s3", "cp", DEPLOY_BUNDLE_S3_URI, bundle_path, "--only-show-errors"], timeout=900, check=True)
    actual_sha = sha256_file(bundle_path).lower()
    if DEPLOY_BUNDLE_SHA256 and actual_sha != DEPLOY_BUNDLE_SHA256:
        raise RuntimeError("deploy bundle sha256 mismatch: expected %s observed %s" % (DEPLOY_BUNDLE_SHA256, actual_sha))
    extract_root = tempfile.mkdtemp(prefix="codex_deploy_bundle_")
    try:
        with zipfile.ZipFile(bundle_path, "r") as zf:
            for member in zf.infolist():
                normalized_name = normalized_bundle_member_name(member.filename)
                normalized = os.path.normpath(normalized_name)
                if normalized.startswith("..") or os.path.isabs(normalized_name) or (len(normalized_name) >= 2 and normalized_name[1] == ":"):
                    raise RuntimeError("unsafe deploy bundle path: " + member.filename)
            zf.extractall(extract_root)
        manifest = {}
        manifest_name = None
        for candidate in ["DEPLOY_BUNDLE_MANIFEST.json", "DEPLOY_BUNDLE_MATRIX_MANIFEST.json"]:
            manifest_path = os.path.join(extract_root, candidate)
            if os.path.exists(manifest_path):
                manifest_name = candidate
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                break
        source_head = str(manifest.get("source_git_head") or "")
        if EXPECTED_GIT_HEAD and source_head and source_head != EXPECTED_GIT_HEAD:
            raise RuntimeError("deploy bundle source head %s did not match expected origin/main %s" % (source_head, EXPECTED_GIT_HEAD))
        for name in os.listdir(extract_root):
            src = os.path.join(extract_root, name)
            dst = os.path.join(PROJECT, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        required_assets = manifest.get("required_input_assets")
        if required_assets is None:
            raise RuntimeError("deploy bundle manifest missing required_input_assets")
        declared_required_count = manifest.get("required_input_asset_count")
        if not isinstance(declared_required_count, int) or declared_required_count != len(required_assets):
            raise RuntimeError("deploy bundle required input asset count mismatch")
        project_root_real = os.path.realpath(PROJECT)
        copied_required_assets = []
        with zipfile.ZipFile(bundle_path, "r") as asset_zip:
            archive_files = [info for info in asset_zip.infolist() if not info.is_dir()]
            for asset in required_assets:
                rel = str(asset.get("bundle_path") or "").replace("\\", "/")
                expected_asset_sha = str(asset.get("sha256") or "").lower()
                normalized_rel = os.path.normpath(rel)
                if not rel or os.path.isabs(rel) or normalized_rel.startswith("..") or (len(rel) >= 2 and rel[1] == ":"):
                    raise RuntimeError("unsafe required input asset bundle path: " + rel)
                deployed_asset = os.path.realpath(os.path.join(project_root_real, normalized_rel))
                if os.path.commonpath([project_root_real, deployed_asset]) != project_root_real:
                    raise RuntimeError("required input asset escapes remote project: " + rel)
                matching_members = [info for info in archive_files if normalized_bundle_member_name(info.filename) == normalized_rel]
                if len(matching_members) != 1:
                    raise RuntimeError("required input asset must appear exactly once in deploy archive: %s (found %s)" % (rel, len(matching_members)))
                if not expected_asset_sha:
                    raise RuntimeError("required input asset sha256 missing for %s" % rel)
                os.makedirs(os.path.dirname(deployed_asset), exist_ok=True)
                with asset_zip.open(matching_members[0], "r") as source_stream, open(deployed_asset, "wb") as destination_stream:
                    shutil.copyfileobj(source_stream, destination_stream)
                deployed_sha = sha256_file(deployed_asset).lower()
                if deployed_sha != expected_asset_sha:
                    raise RuntimeError("required input asset deployed sha256 mismatch for %s" % rel)
                copied_required_assets.append({"bundle_path": rel, "sha256": deployed_sha})
        return {
            "deployment_method": "s3_deploy_bundle",
            "s3_uri": DEPLOY_BUNDLE_S3_URI,
            "download_rc": download["rc"],
            "sha256": actual_sha,
            "sha256_expected": DEPLOY_BUNDLE_SHA256,
            "sha256_verified": (not DEPLOY_BUNDLE_SHA256) or actual_sha == DEPLOY_BUNDLE_SHA256,
            "manifest_name": manifest_name,
            "manifest_bundle_type": manifest.get("bundle_type"),
            "manifest_source_git_head": source_head,
            "manifest_lane_id": manifest.get("lane_id"),
            "manifest_matrix_id": manifest.get("matrix_id"),
            "manifest_sample_count": manifest.get("sample_count"),
            "manifest_file_count": manifest.get("file_count"),
            "required_input_asset_count": len(copied_required_assets),
            "required_input_assets": copied_required_assets,
            "git_lfs_pull_skipped": True
        }
    finally:
        shutil.rmtree(extract_root, ignore_errors=True)

def artifact_type(rel):
    p = rel.replace("\\", "/").lower()
    ext = os.path.splitext(p)[1]
    if p.startswith("logs/"):
        return "log"
    if p.startswith("reports/"):
        return "report"
    if p.startswith("workflows/"):
        return "workflow"
    if p.startswith("images/") or ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        return "image"
    if p.startswith("videos/") or ext in [".mp4", ".mov", ".avi", ".webm", ".gif"]:
        return "video"
    if p.startswith("audio/") or ext in [".wav", ".flac", ".mp3", ".ogg", ".m4a"]:
        return "audio"
    if ext == ".json":
        return "json"
    return "other"

def qa_required(kind):
    return kind in ["image", "video", "audio", "log", "report", "workflow", "json"]

def stage_required_input_assets():
    requirements_path = os.path.join(PROJECT, "Workflows", "base_generation", LANE_ID, "runtime_requirements.json")
    if not os.path.isfile(requirements_path):
        raise RuntimeError("lane runtime requirements missing: " + requirements_path)
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = json.load(f)
    bundle_manifest_path = os.path.join(PROJECT, "DEPLOY_BUNDLE_MANIFEST.json")
    bundle_assets = None
    if os.path.isfile(bundle_manifest_path):
        with open(bundle_manifest_path, "r", encoding="utf-8") as f:
            bundle_manifest = json.load(f)
        bundle_assets = bundle_manifest.get("required_input_assets")
    assets = bundle_assets if bundle_assets is not None else requirements.get("required_input_assets", [])
    staged = []
    project_root = os.path.realpath(PROJECT)
    comfy_input_root = os.path.realpath(os.path.join(COMFY, "input"))
    for asset in assets:
        source_rel = str(asset.get("bundle_path") or asset.get("source_artifact") or "")
        filename = os.path.basename(str(asset.get("filename") or ""))
        input_subdir = str(asset.get("comfyui_input_subdir") or "").strip("/\\")
        expected_sha = str(asset.get("sha256") or "").lower()
        source = os.path.realpath(os.path.join(PROJECT, source_rel))
        destination = os.path.realpath(os.path.join(comfy_input_root, input_subdir, filename))
        if not source_rel or not filename or os.path.commonpath([project_root, source]) != project_root:
            raise RuntimeError("unsafe or incomplete required input asset: " + source_rel)
        if os.path.commonpath([comfy_input_root, destination]) != comfy_input_root:
            raise RuntimeError("unsafe ComfyUI input destination for: " + filename)
        if not os.path.isfile(source):
            raise RuntimeError("required input asset missing from deploy bundle: " + source_rel)
        actual_sha = sha256_file(source).lower()
        if not expected_sha or actual_sha != expected_sha:
            raise RuntimeError("required input asset sha256 mismatch for %s: expected %s observed %s" % (filename, expected_sha, actual_sha))
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)
        staged.append({
            "filename": filename,
            "bundle_path": source_rel,
            "source_artifact": str(asset.get("source_artifact") or ""),
            "destination": destination,
            "sha256": actual_sha,
            "size_bytes": os.path.getsize(destination)
        })
    return staged

def prompt_link(value):
    return (
        isinstance(value, list) and
        len(value) == 2 and
        isinstance(value[0], (str, int)) and
        isinstance(value[1], int) and
        not isinstance(value[1], bool)
    )

def input_type_and_options(input_spec):
    if not isinstance(input_spec, list) or not input_spec:
        return None, None, {}
    first = input_spec[0]
    metadata = input_spec[1] if len(input_spec) > 1 and isinstance(input_spec[1], dict) else {}
    if isinstance(first, list):
        return "COMBO", first, metadata
    if first == "COMBO":
        return "COMBO", metadata.get("options"), metadata
    return first if isinstance(first, str) else None, None, metadata

def validate_prompt_schema(request, object_info):
    graph = request.get("prompt") if isinstance(request, dict) else None
    errors = []
    node_reports = []
    if not isinstance(graph, dict) or not graph:
        return {"status": "fail", "errors": ["prompt graph is missing or empty"], "nodes": []}
    for node_id, node in graph.items():
        class_type = node.get("class_type") if isinstance(node, dict) else None
        inputs = node.get("inputs") if isinstance(node, dict) else None
        schema = object_info.get(class_type) if class_type else None
        node_errors = []
        if not isinstance(schema, dict):
            node_errors.append("class_type is absent from live object_info: %s" % class_type)
        if not isinstance(inputs, dict):
            node_errors.append("inputs must be an object")
            inputs = {}
        input_schema = schema.get("input", {}) if isinstance(schema, dict) else {}
        required = input_schema.get("required", {}) if isinstance(input_schema.get("required", {}), dict) else {}
        optional = input_schema.get("optional", {}) if isinstance(input_schema.get("optional", {}), dict) else {}
        hidden = input_schema.get("hidden", {}) if isinstance(input_schema.get("hidden", {}), dict) else {}
        allowed = dict(required)
        allowed.update(optional)
        allowed.update(hidden)
        for input_name in sorted(required):
            if input_name not in inputs:
                node_errors.append("missing required input: %s" % input_name)
        for input_name, value in inputs.items():
            if input_name not in allowed:
                node_errors.append("unknown API input: %s" % input_name)
                continue
            expected_type, options, metadata = input_type_and_options(allowed[input_name])
            if prompt_link(value):
                source_id = str(value[0])
                output_index = value[1]
                source_node = graph.get(source_id)
                if not isinstance(source_node, dict):
                    node_errors.append("input %s references missing node %s" % (input_name, source_id))
                    continue
                source_schema = object_info.get(source_node.get("class_type"), {})
                source_outputs = source_schema.get("output", []) if isinstance(source_schema, dict) else []
                if output_index < 0 or output_index >= len(source_outputs):
                    node_errors.append("input %s references invalid output %s.%s" % (input_name, source_id, output_index))
                    continue
                source_type = source_outputs[output_index]
                if expected_type and source_type and expected_type != source_type:
                    node_errors.append("input %s expects %s but link %s.%s outputs %s" % (input_name, expected_type, source_id, output_index, source_type))
                continue
            if isinstance(options, list) and value not in options:
                node_errors.append("input %s value is not in live options: %s" % (input_name, value))
            if expected_type == "INT" and (not isinstance(value, int) or isinstance(value, bool)):
                node_errors.append("input %s must be INT" % input_name)
            elif expected_type == "FLOAT" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                node_errors.append("input %s must be FLOAT" % input_name)
            elif expected_type == "BOOLEAN" and not isinstance(value, bool):
                node_errors.append("input %s must be BOOLEAN" % input_name)
            elif expected_type == "STRING" and not isinstance(value, str):
                node_errors.append("input %s must be STRING" % input_name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if "min" in metadata and value < metadata["min"]:
                    node_errors.append("input %s is below live minimum %s" % (input_name, metadata["min"]))
                if "max" in metadata and value > metadata["max"]:
                    node_errors.append("input %s exceeds live maximum %s" % (input_name, metadata["max"]))
        errors.extend("node %s (%s): %s" % (node_id, class_type, error) for error in node_errors)
        node_reports.append({
            "node_id": str(node_id),
            "class_type": class_type,
            "input_names": sorted(inputs),
            "required_input_names": sorted(required),
            "optional_input_names": sorted(optional),
            "hidden_input_names": sorted(hidden),
            "errors": node_errors
        })
    return {
        "status": "pass" if not errors else "fail",
        "node_count": len(graph),
        "checked_input_count": sum(len(node.get("input_names", [])) for node in node_reports),
        "error_count": len(errors),
        "errors": errors,
        "nodes": node_reports
    }

proc = None
log_handle = None
try:
    deployment = apply_deploy_bundle_if_configured()
    if deployment:
        result["remote_project_deployment"] = deployment
    if not os.path.isdir(PROJECT):
        raise RuntimeError("remote project missing: " + PROJECT)
    if not os.path.exists(os.path.join(COMFY, "main.py")):
        raise RuntimeError("ComfyUI main.py missing under " + COMFY)

    os.makedirs(os.path.join(ARTIFACT_ROOT, "logs"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACT_ROOT, "reports"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACT_ROOT, "workflows"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACT_ROOT, "images"), exist_ok=True)
    if not deployment:
        result["remote_project_deployment"] = {"deployment_method": "git_pull"}
        result["git_head_before"] = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
        result["git_pull"] = run(["git", "pull", "--ff-only", "origin", "main"], cwd=PROJECT, timeout=300, check=True)["stdout"][-500:]
        if SKIP_GIT_LFS_PULL:
            result["git_lfs_pull_rc"] = 0
            result["git_lfs_pull_skipped"] = True
        else:
            result["git_lfs_pull_rc"] = run(["git", "lfs", "pull"], cwd=PROJECT, timeout=300, check=True)["rc"]
            result["git_lfs_pull_skipped"] = False
        result["git_head_after"] = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
        result["git_expected_head"] = EXPECTED_GIT_HEAD
        result["git_head_matches_expected"] = (not EXPECTED_GIT_HEAD) or result["git_head_after"] == EXPECTED_GIT_HEAD
        if EXPECTED_GIT_HEAD and result["git_head_after"] != EXPECTED_GIT_HEAD:
            raise RuntimeError("remote project HEAD %s did not match expected origin/main %s" % (result["git_head_after"], EXPECTED_GIT_HEAD))

    result["staged_input_assets"] = stage_required_input_assets()

    request_json = base64.b64decode(REQUEST_B64.encode("ascii")).decode("utf-8")
    request_path = os.path.join(ARTIFACT_ROOT, "workflows", "prompt_request.json")
    with open(request_path, "w", encoding="utf-8") as f:
        f.write(request_json)

    py_candidates = [
        os.path.join(COMFY, "venv", "bin", "python"),
        os.path.join(COMFY, ".venv", "bin", "python"),
        "/usr/bin/python3",
        "python3"
    ]
    py_exec = next((p for p in py_candidates if (os.path.isabs(p) and os.path.exists(p)) or not os.path.isabs(p)), "python3")
    log_path = os.path.join(ARTIFACT_ROOT, "logs", "comfyui.log")
    log_handle = open(log_path, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [py_exec, "main.py", "--listen", "127.0.0.1", "--port", str(PORT)],
        cwd=COMFY,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True
    )

    ready_error = ""
    object_info = None
    for _ in range(90):
        if proc.poll() is not None:
            ready_error = "ComfyUI exited early rc=%s" % proc.returncode
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:%s/object_info" % PORT, timeout=2) as resp:
                object_info = json.loads(resp.read().decode("utf-8"))
                result["object_info_node_count"] = len(object_info)
                ready_error = ""
                break
        except Exception as exc:
            ready_error = str(exc)
            time.sleep(2)
    if ready_error:
        raise RuntimeError("ComfyUI API did not become ready: " + ready_error)

    request_payload = json.loads(request_json)
    schema_validation = validate_prompt_schema(request_payload, object_info or {})
    result["prompt_schema_validation"] = schema_validation
    schema_report_path = os.path.join(ARTIFACT_ROOT, "reports", "prompt_schema_validation.json")
    with open(schema_report_path, "w", encoding="utf-8") as f:
        json.dump(schema_validation, f, sort_keys=True, indent=2)
    if schema_validation["status"] != "pass":
        raise RuntimeError("prompt failed live object_info validation: " + "; ".join(schema_validation["errors"][:20]))

    prompt_body = request_json.encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:%s/prompt" % PORT,
        data=prompt_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            prompt_response = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        result["prompt_http_error"] = {
            "status": exc.code,
            "reason": str(exc.reason),
            "headers": dict(exc.headers.items()),
            "body": response_body[-12000:]
        }
        raise RuntimeError("ComfyUI /prompt rejected request with HTTP %s: %s" % (exc.code, response_body[-4000:])) from exc
    result["prompt_response"] = prompt_response
    result["prompt_id"] = prompt_response.get("prompt_id")
    if not result["prompt_id"]:
        raise RuntimeError("ComfyUI /prompt response did not include prompt_id.")

    deadline = time.time() + TIMEOUT_SECONDS
    history = None
    while time.time() < deadline:
        with urllib.request.urlopen("http://127.0.0.1:%s/history/%s" % (PORT, result["prompt_id"]), timeout=15) as resp:
            history_all = json.loads(resp.read().decode("utf-8"))
        if result["prompt_id"] in history_all and history_all[result["prompt_id"]].get("outputs"):
            history = history_all[result["prompt_id"]]
            break
        time.sleep(POLL_SECONDS)
    if history is None:
        raise RuntimeError("No ComfyUI history outputs found before timeout.")

    history_path = os.path.join(ARTIFACT_ROOT, "reports", "history.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, sort_keys=True, indent=2)

    output_root = os.path.join(COMFY, "output")
    for node_id, node_output in history.get("outputs", {}).items():
        for image in node_output.get("images", []):
            filename = image.get("filename", "")
            subfolder = image.get("subfolder", "")
            source = os.path.join(output_root, subfolder, filename)
            image_record = {"node_id": node_id, "filename": filename, "subfolder": subfolder, "type": image.get("type"), "source": source, "copied": False}
            if os.path.exists(source):
                safe_name = ("%s_%s" % (node_id, filename)).replace("/", "_")
                dest = os.path.join(ARTIFACT_ROOT, "images", safe_name)
                shutil.copy2(source, dest)
                image_record["copied"] = True
                image_record["artifact_relative_path"] = os.path.relpath(dest, ARTIFACT_ROOT).replace(os.sep, "/")
            result["output_images"].append(image_record)

    if not any(img.get("copied") for img in result["output_images"]):
        raise RuntimeError("ComfyUI history contained no copied image artifacts.")

    files = []
    for root, _, names in os.walk(ARTIFACT_ROOT):
        for name in names:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, ARTIFACT_ROOT).replace(os.sep, "/")
            if rel == "REMOTE_ARTIFACT_MANIFEST.json":
                continue
            kind = artifact_type(rel)
            files.append({
                "relative_path": rel,
                "size_bytes": os.path.getsize(path),
                "sha256": sha256_file(path),
                "artifact_type": kind,
                "qa_required": qa_required(kind)
            })
    manifest = {
        "run_id": RUN_ID,
        "instance_id": "$InstanceId",
        "artifact_root": ARTIFACT_ROOT,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": sorted(files, key=lambda item: item["relative_path"])
    }
    manifest_path = os.path.join(ARTIFACT_ROOT, "REMOTE_ARTIFACT_MANIFEST.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, indent=2)
    result["manifest_path"] = manifest_path
    result["manifest_file_count"] = len(files)

    if S3_BUCKET:
        s3_uri = "s3://%s/%s/" % (S3_BUCKET, S3_PREFIX.strip("/"))
        result["s3_sync"] = {"attempted": True, "s3_uri": s3_uri, "succeeded": False}
        sync = run(["aws", "s3", "sync", ARTIFACT_ROOT, s3_uri, "--only-show-errors"], timeout=900, check=False)
        result["s3_sync"]["rc"] = sync["rc"]
        result["s3_sync"]["stdout_tail"] = sync["stdout"][-1000:]
        result["s3_sync"]["stderr_tail"] = sync["stderr"][-1000:]
        result["s3_sync"]["succeeded"] = (sync["rc"] == 0)
except Exception as exc:
    result["errors"].append(str(exc))
    result["traceback_tail"] = traceback.format_exc()[-4000:]
finally:
    if proc is not None and proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=20)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
    if log_handle is not None:
        try:
            log_handle.close()
        except Exception:
            pass

print(json.dumps(result, sort_keys=True))
PY
"@

function Wait-InstanceState {
  param(
    [Parameter(Mandatory=$true)][string]$DesiredState,
    [int]$MaxAttempts = 80,
    [int]$SleepSeconds = 5
  )

  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    Write-Host "EC2 state wait $i/$MaxAttempts desired=$DesiredState observed=$state"
    if ($state -eq $DesiredState) { return $state }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Timed out waiting for EC2 state '$DesiredState' on $InstanceId"
}

function Wait-InstanceStatusOk {
  param(
    [int]$MaxAttempts = 80,
    [int]$SleepSeconds = 5
  )

  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $status = aws ec2 describe-instance-status --region $Region --instance-ids $InstanceId --include-all-instances --query "InstanceStatuses[0].{system:SystemStatus.Status,instance:InstanceStatus.Status,state:InstanceState.Name}" --output json | ConvertFrom-Json
    Write-Host "EC2 status wait $i/$MaxAttempts state=$($status.state) system=$($status.system) instance=$($status.instance)"
    if ($status.state -eq "running" -and $status.system -eq "ok" -and $status.instance -eq "ok") { return $true }
    Start-Sleep -Seconds $SleepSeconds
  }
  throw "Timed out waiting for EC2 instance status checks on $InstanceId"
}

try {
  $record.start_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  if ($record.start_state -ne "running") {
    Write-Host "Starting EC2 instance $InstanceId from state $($record.start_state)"
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
      $startOutput = @(aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
      $record.start_exit_code = $LASTEXITCODE
    } finally {
      $ErrorActionPreference = $previousErrorActionPreference
    }
    $startText = (($startOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
    $record.start_output_tail = Get-TailText -Text $startText -MaxChars 2000
    if ($record.start_exit_code -ne 0) {
      $record.failure_category = Get-EC2StartFailureCategory -ExitCode $record.start_exit_code -OutputText $startText
      $record.result = "workflow_smoke_start_failed"
      throw "EC2 start-instances failed with exit code $($record.start_exit_code). $startText"
    }
    $record.ec2_started = $true
  }
  $null = Wait-InstanceState -DesiredState "running"
  $null = Wait-InstanceStatusOk

  $ssmOnline = $false
  for ($i = 0; $i -lt 30; $i++) {
    $ping = (aws ssm describe-instance-information --region $Region --filters "Key=InstanceIds,Values=$InstanceId" --query "InstanceInformationList[0].PingStatus" --output text 2>$null).Trim()
    Write-Host "SSM wait $($i + 1)/30 ping=$ping"
    if ($ping -eq "Online") { $ssmOnline = $true; break }
    Start-Sleep -Seconds 10
  }
  if (!$ssmOnline) { throw "SSM did not become Online for $InstanceId." }

  try {
    $record.instance_watchdog = Invoke-VerifiedInstanceWatchdog `
      -WatchdogScriptPath (Join-Path $PSScriptRoot "Start-EC2InstanceStopWatchdog.ps1") `
      -InstanceId $InstanceId `
      -Region $Region `
      -RuntimeWindowId $RuntimeWindowId `
      -OutFile $WatchdogEvidenceOutFile `
      -StopAfterMinutes $MaxEc2RuntimeMinutes `
      -TrackerId "TRK-W64-042" `
      -ItemId "ITEM-W64-042" `
      -AllowOsShutdownFallback:$AllowWatchdogOsShutdownFallback
  } catch {
    $record.failure_category = "instance_stop_watchdog_not_verified"
    throw
  }

  $payloadPath = Join-Path $env:TEMP ("codex_ec2_workflow_smoke_{0}.json" -f $stamp)
  $payload = @{
    DocumentName = "AWS-RunShellScript"
    InstanceIds = @($InstanceId)
    TimeoutSeconds = $ssmExecutionTimeoutSeconds
    Parameters = @{ commands = @($remoteScript); executionTimeout = @([string]$ssmExecutionTimeoutSeconds) }
    CloudWatchOutputConfig = @{ CloudWatchOutputEnabled = $false }
  } | ConvertTo-Json -Depth 8
  [System.IO.File]::WriteAllText($payloadPath, $payload, [System.Text.UTF8Encoding]::new($false))

  $record.command_id = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
  Write-Host "SSM command sent: $($record.command_id)"
  $record.ssm_execution_timeout_seconds = $ssmExecutionTimeoutSeconds
  $maxCommandPolls = [Math]::Max(1, [int][Math]::Ceiling($ssmExecutionTimeoutSeconds / 5))
  for ($i = 0; $i -lt $maxCommandPolls; $i++) {
    Start-Sleep -Seconds 5
    $record.command_status = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "Status" --output text 2>$null).Trim()
    Write-Host "SSM command wait $($i + 1)/$maxCommandPolls status=$($record.command_status)"
    if ($record.command_status -in @("Success", "Cancelled", "TimedOut", "Failed", "Cancelling")) { break }
  }
  if ($record.command_status -notin @("Success", "Cancelled", "TimedOut", "Failed", "Cancelling")) {
    $record.command_status = "LocalTimeout"
    try {
      aws ssm cancel-command --region $Region --command-id $record.command_id --instance-ids $InstanceId --output json | Out-Null
    } catch {
      $record.errors += "SSM cancel-command after local timeout failed: $($_.Exception.Message)"
    }
  }

  $stdout = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardOutputContent" --output text
  $stderr = aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "StandardErrorContent" --output text
  $record.remote_stdout_tail = Get-TailText -Text ([string]$stdout) -MaxChars 6000
  $record.remote_stderr_tail = Get-TailText -Text ([string]$stderr) -MaxChars 4000

  try {
    $jsonStart = ([string]$stdout).IndexOf("{")
    if ($jsonStart -ge 0) {
      $record.remote_result = ([string]$stdout).Substring($jsonStart) | ConvertFrom-Json
      $record.generation_executed = (@($record.remote_result.output_images | Where-Object { [bool]$_.copied }).Count -gt 0)
    } else {
      $record.errors += "Remote stdout did not contain a JSON result."
    }
  } catch {
    $record.errors += "Remote result JSON parse failed: $($_.Exception.Message)"
  }

  if ($record.remote_result -and $record.remote_result.s3_sync -and [bool]$record.remote_result.s3_sync.succeeded) {
    $localDestination = Join-Path $pullbackRoot $runId
    $null = New-Item -ItemType Directory -Force -Path $localDestination
    $syncUri = [string]$record.remote_result.s3_sync.s3_uri
    $record.local_pullback.attempted = $true
    $syncResult = Invoke-AwsCliJson -Arguments @("s3", "sync", $syncUri, $localDestination, "--only-show-errors")
    $record.local_pullback.s3_uri = $syncUri
    $record.local_pullback.local_destination = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $localDestination
    $record.local_pullback.sync_exit_code = $syncResult.exit_code
    $record.local_pullback.sync_output_tail = Get-TailText -Text ([string]$syncResult.output) -MaxChars 2000
    if ($syncResult.exit_code -eq 0) {
      $manifestLocal = Join-Path $localDestination "REMOTE_ARTIFACT_MANIFEST.json"
      $pullbackOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $pullbackScript -ProjectRoot $ProjectRoot -RunId $runId -LocalDestination $localDestination -RemoteManifestFile $manifestLocal -SourceInstance $InstanceId -SourceArtifactRoot ([string]$record.remote_result.artifact_root) -S3Prefix $syncUri 2>&1
      $record.local_pullback.status = $(if ($LASTEXITCODE -eq 0) { "pullback_record_created" } else { "pullback_record_failed" })
      $record.local_pullback.pullback_record_output_tail = Get-TailText -Text (($pullbackOutput | ForEach-Object { $_.ToString() }) -join "`n") -MaxChars 2000
    } else {
      $record.local_pullback.status = "s3_sync_failed"
    }
  } elseif (![string]::IsNullOrWhiteSpace($S3Bucket)) {
    $record.local_pullback.status = "remote_s3_sync_not_successful"
  } else {
    $record.local_pullback.status = "s3_bucket_not_configured"
  }
}
catch {
  $record.errors += $_.Exception.Message
}
finally {
  try {
    $shouldStopInstance = ($record.ec2_started -or $record.start_state -eq "running" -or $record.command_status -ne "not_started")
    if ($shouldStopInstance) {
      Write-Host "Stopping EC2 instance $InstanceId after workflow smoke attempt"
      $previousErrorActionPreference = $ErrorActionPreference
      $ErrorActionPreference = "Continue"
      try {
        $stopOutput = @(aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json 2>&1)
        $record.stop_exit_code = $LASTEXITCODE
      } finally {
        $ErrorActionPreference = $previousErrorActionPreference
      }
      $stopText = (($stopOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
      $record.stop_output_tail = Get-TailText -Text $stopText -MaxChars 2000
      if ($record.stop_exit_code -ne 0) {
        $record.stop_failure_category = Get-EC2StopFailureCategory -ExitCode $record.stop_exit_code -OutputText $stopText
        throw "EC2 stop-instances failed with exit code $($record.stop_exit_code). $stopText"
      }
      $null = Wait-InstanceState -DesiredState "stopped" -MaxAttempts 120 -SleepSeconds 5
      $record.final_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
    } else {
      $record.final_state = $record.start_state
    }
  } catch {
    if ([string]::IsNullOrWhiteSpace([string]$record.stop_failure_category)) {
      $record.stop_failure_category = "ec2_stop_or_final_state_verification_failed"
    }
    $record.errors += "Stop/final-state verification failed: $($_.Exception.Message)"
  }
}

$record.next_action = $(if ($record.generation_executed -and $record.local_pullback.status -eq "pullback_record_created") { "Run image QA on the pulled-back generated image artifacts." } else { "Inspect run record, complete artifact pullback if needed, and do not claim image QA until artifacts are local and reviewed." })
if ($record.result -eq "workflow_smoke_start_failed") {
  $record.next_action = $(if ($record.failure_category -eq "ec2_insufficient_instance_capacity") { "Do not retry in the same capacity window; preserve staged assets and wait for a fresh capacity state." } else { "Resolve the recorded EC2 start failure before another intentionally gated workflow smoke." })
} elseif ($record.generation_executed -and $record.final_state -eq "stopped" -and $record.errors.Count -eq 0) {
  $record.result = "workflow_smoke_generation_complete"
  $record.failure_category = $null
} elseif ($record.ec2_started -or $record.command_status -ne "not_started") {
  $record.result = "workflow_smoke_generation_incomplete"
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) {
    $record.failure_category = "workflow_smoke_generation_incomplete"
  }
} elseif ($record.errors.Count -gt 0) {
  $record.result = "workflow_smoke_generation_incomplete"
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) {
    $record.failure_category = "workflow_smoke_preflight_or_start_failed"
  }
}

$runDir = Split-Path -Parent $RunRecordFile
if (![string]::IsNullOrWhiteSpace($runDir)) {
  $null = New-Item -ItemType Directory -Force -Path $runDir
}
$record | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $RunRecordFile -Encoding UTF8

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote EC2 workflow smoke run record: $OutFile"
$record | ConvertTo-Json -Depth 50

if ($record.errors.Count -gt 0 -or !$record.generation_executed -or $record.final_state -ne "stopped") { exit 2 }
