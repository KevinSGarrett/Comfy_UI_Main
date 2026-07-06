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

Only then does it start the approved EC2 instance, run the ComfyUI prompt
remotely through SSM, create a remote artifact manifest, optionally sync
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
  [string]$OutFile = "",
  [string]$OutRequestFile = "",
  [string]$RunPackageManifestFile = "",
  [string]$RunRecordFile = "",
  [string]$RemoteProjectRoot = "/home/ubuntu/Comfy_UI_Main",
  [string]$RemoteComfyRoot = "/home/ubuntu/ComfyUI",
  [string]$RemoteArtifactRoot = "/home/ubuntu/comfyui_artifacts",
  [string]$S3Bucket = "",
  [string]$S3Prefix = "",
  [int]$ComfyPort = 8192,
  [int]$TimeoutSeconds = 900,
  [int]$PollSeconds = 3,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

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

function Get-ReadinessStatus {
  param([string]$Path)

  $result = [ordered]@{
    file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    found = (![string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path))
    local_pre_ec2_ready = $false
    ready_for_ec2_static_proof = $false
    ready_for_generation = $false
    lane_id = $null
    lane_match = $false
    result = "missing_readiness_record"
    failure_category = "missing_readiness_record"
    status = "missing_readiness_record"
  }
  if (!$result.found) { return $result }
  $readiness = Read-JsonFile -Path $Path
  $result.failure_category = $null
  $result.local_pre_ec2_ready = [bool]$readiness.local_pre_ec2_ready
  $result.ready_for_ec2_static_proof = [bool]$readiness.ready_for_ec2_static_proof
  $result.ready_for_generation = [bool]$readiness.ready_for_generation
  if (Has-Property -Object $readiness -Name "lane_id") {
    $result.lane_id = [string]$readiness.lane_id
  }
  $result.lane_match = ([string]$result.lane_id -eq [string]$LaneId)
  if (Has-Property -Object $readiness -Name "result") {
    $result.result = [string]$readiness.result
  } else {
    $result.result = $(if ($result.ready_for_generation) { "ready_for_generation" } elseif ($result.local_pre_ec2_ready) { "local_pre_ec2_ready_runtime_blocked" } else { "not_ready" })
  }
  if (Has-Property -Object $readiness -Name "failure_category") {
    $result.failure_category = $readiness.failure_category
  }
  $result.status = $(if ($result.ready_for_generation) { "generation_ready" } elseif ($result.local_pre_ec2_ready) { "local_ready_runtime_blocked" } else { "not_ready" })
  return $result
}

function Get-LocalGitCheckpointGate {
  $result = [ordered]@{
    git_root = $null
    head = $null
    origin_main = $null
    expected_remote_head = $null
    local_matches_origin = $false
    clean = $false
    porcelain_count = $null
    remote = $null
    result = "fail"
    error = $null
  }

  try {
    Push-Location $ProjectRoot
    try {
      $result.git_root = (git rev-parse --show-toplevel 2>$null)
      if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.git_root)) {
        throw "Project root is not a Git checkout."
      }
      $result.head = (git rev-parse HEAD 2>$null)
      if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.head)) {
        throw "Unable to resolve local HEAD."
      }
      $result.origin_main = (git rev-parse origin/main 2>$null)
      if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.origin_main)) {
        throw "Unable to resolve origin/main."
      }
      $result.expected_remote_head = $result.origin_main
      $result.local_matches_origin = ([string]$result.head -eq [string]$result.origin_main)
      $porcelain = @(git status --porcelain 2>$null)
      $result.porcelain_count = $porcelain.Count
      $result.clean = ($porcelain.Count -eq 0)
      $remoteLines = @(git remote -v 2>$null)
      $result.remote = (($remoteLines | Where-Object { $_ -match "^origin\s+" }) | Select-Object -First 1)
      $result.result = $(if ($result.local_matches_origin -and $result.clean) { "pass" } else { "fail" })
    } finally {
      Pop-Location
    }
  } catch {
    $result.error = $_.Exception.Message
    $result.result = "fail"
  }

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

if ([string]::IsNullOrWhiteSpace($AuthGateFile)) {
  $AuthGateFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE_*.json"
}
if ([string]::IsNullOrWhiteSpace($StaticProofFile)) {
  $StaticProofFile = Find-LatestJsonByLaneId -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_*.json" -ExpectedLaneId $LaneId -ExcludePattern "DRY_RUN|BLOCKED_EXECUTE"
}
if ([string]::IsNullOrWhiteSpace($ReadinessFile)) {
  $ReadinessFile = Find-LatestJsonByLaneId -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS_*.json" -ExpectedLaneId $LaneId
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
$readinessGate = Get-ReadinessStatus -Path $ReadinessFile
$staticProof = Test-StaticProof -Path $StaticProofFile
$localGitGate = Get-LocalGitCheckpointGate
$runPackage = Get-RunPackageStatus -Path $RunPackageManifestFile

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
} elseif (!$laneContractValid) {
  $gateFailureCategory = "lane_contract_invalid"
} elseif ($runPackage.supplied -and !$runPackage.valid) {
  $gateFailureCategory = "run_package_invalid"
} elseif ($localGitGate.result -ne "pass") {
  $gateFailureCategory = $(if ($localGitGate.clean -ne $true) { "local_git_worktree_dirty" } elseif ($localGitGate.local_matches_origin -ne $true) { "local_git_not_synced_to_origin" } else { "local_git_checkpoint_invalid" })
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
  instance_id = $InstanceId
  region = $Region
  remote_project_root = $RemoteProjectRoot
  remote_comfy_root = $RemoteComfyRoot
  remote_artifact_root = "$RemoteArtifactRoot/$runId"
  comfy_port = $ComfyPort
  timeout_seconds = $TimeoutSeconds
  result = $(if ($executeGatesPass) { "ready_for_workflow_smoke_execute" } elseif ($Execute) { "blocked_before_ec2_start" } else { "dry_run_blocked_before_ec2_start" })
  failure_category = $gateFailureCategory
  lane_contracts = $laneContracts
  local_git_checkpoint_gate = $localGitGate
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
    "Require selected-lane readiness gate before generation.",
    "Require EC2 object-info/path/hash static proof before generation.",
    $(if ($runPackage.supplied) { "Load the validated run package prompt_request.json as the bounded ComfyUI /prompt body." } else { "Build the patched ComfyUI /prompt request body locally." }),
    "With -Execute only, start i-0560bf8d143f93bb1, run remote ComfyUI smoke, create artifact manifest, pull back artifacts when S3 is available, then stop EC2."
  )
  generation_executed = $false
  ec2_started = $false
  command_id = $null
  command_status = "not_started"
  start_state = $null
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
$remoteScript = @"
python3 - <<'PY'
import base64, datetime, glob, hashlib, json, os, shutil, signal, subprocess, time, traceback, urllib.request

RUN_ID = "$runId"
PROJECT = "$RemoteProjectRoot"
COMFY = "$RemoteComfyRoot"
ARTIFACT_ROOT = "$RemoteArtifactRoot/$runId"
REQUEST_B64 = "$requestBase64"
EXPECTED_GIT_HEAD = "$expectedRemoteGitHead"
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

proc = None
log_handle = None
try:
    if not os.path.isdir(PROJECT):
        raise RuntimeError("remote project missing: " + PROJECT)
    if not os.path.exists(os.path.join(COMFY, "main.py")):
        raise RuntimeError("ComfyUI main.py missing under " + COMFY)

    os.makedirs(os.path.join(ARTIFACT_ROOT, "logs"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACT_ROOT, "reports"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACT_ROOT, "workflows"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACT_ROOT, "images"), exist_ok=True)

    result["git_head_before"] = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
    result["git_pull"] = run(["git", "pull", "--ff-only", "origin", "main"], cwd=PROJECT, timeout=300, check=True)["stdout"][-500:]
    result["git_lfs_pull_rc"] = run(["git", "lfs", "pull"], cwd=PROJECT, timeout=300, check=True)["rc"]
    result["git_head_after"] = run(["git", "rev-parse", "HEAD"], cwd=PROJECT, check=True)["stdout"]
    result["git_expected_head"] = EXPECTED_GIT_HEAD
    result["git_head_matches_expected"] = (not EXPECTED_GIT_HEAD) or result["git_head_after"] == EXPECTED_GIT_HEAD
    if EXPECTED_GIT_HEAD and result["git_head_after"] != EXPECTED_GIT_HEAD:
        raise RuntimeError("remote project HEAD %s did not match expected origin/main %s" % (result["git_head_after"], EXPECTED_GIT_HEAD))

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
    for _ in range(90):
        if proc.poll() is not None:
            ready_error = "ComfyUI exited early rc=%s" % proc.returncode
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:%s/object_info" % PORT, timeout=2) as resp:
                result["object_info_node_count"] = len(json.loads(resp.read().decode("utf-8")))
                ready_error = ""
                break
        except Exception as exc:
            ready_error = str(exc)
            time.sleep(2)
    if ready_error:
        raise RuntimeError("ComfyUI API did not become ready: " + ready_error)

    prompt_body = request_json.encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:%s/prompt" % PORT,
        data=prompt_body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        prompt_response = json.loads(resp.read().decode("utf-8"))
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
    aws ec2 start-instances --region $Region --instance-ids $InstanceId --output json | Out-Null
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

  $payloadPath = Join-Path $env:TEMP ("codex_ec2_workflow_smoke_{0}.json" -f $stamp)
  $payload = @{
    DocumentName = "AWS-RunShellScript"
    InstanceIds = @($InstanceId)
    Parameters = @{ commands = @($remoteScript); executionTimeout = @([string]($TimeoutSeconds + 900)) }
    CloudWatchOutputConfig = @{ CloudWatchOutputEnabled = $false }
  } | ConvertTo-Json -Depth 8
  [System.IO.File]::WriteAllText($payloadPath, $payload, [System.Text.UTF8Encoding]::new($false))

  $record.command_id = (aws ssm send-command --region $Region --cli-input-json "file://$payloadPath" --query "Command.CommandId" --output text).Trim()
  Write-Host "SSM command sent: $($record.command_id)"
  for ($i = 0; $i -lt [Math]::Max(120, [int](($TimeoutSeconds + 900) / 5)); $i++) {
    Start-Sleep -Seconds 5
    $record.command_status = (aws ssm get-command-invocation --region $Region --instance-id $InstanceId --command-id $record.command_id --query "Status" --output text 2>$null).Trim()
    Write-Host "SSM command wait $($i + 1) status=$($record.command_status)"
    if ($record.command_status -in @("Success", "Cancelled", "TimedOut", "Failed", "Cancelling")) { break }
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
    Write-Host "Stopping EC2 instance $InstanceId after workflow smoke attempt"
    aws ec2 stop-instances --region $Region --instance-ids $InstanceId --output json | Out-Null
    $null = Wait-InstanceState -DesiredState "stopped" -MaxAttempts 120 -SleepSeconds 5
    $record.final_state = (aws ec2 describe-instances --region $Region --instance-ids $InstanceId --query "Reservations[0].Instances[0].State.Name" --output text).Trim()
  } catch {
    $record.errors += "Stop/final-state verification failed: $($_.Exception.Message)"
  }
}

$record.next_action = $(if ($record.generation_executed -and $record.local_pullback.status -eq "pullback_record_created") { "Run image QA on the pulled-back generated image artifacts." } else { "Inspect run record, complete artifact pullback if needed, and do not claim image QA until artifacts are local and reviewed." })
if ($record.generation_executed -and $record.final_state -eq "stopped" -and $record.errors.Count -eq 0) {
  $record.result = "workflow_smoke_generation_complete"
  $record.failure_category = $null
} elseif ($record.ec2_started -or $record.command_status -ne "not_started") {
  $record.result = "workflow_smoke_generation_incomplete"
  if ([string]::IsNullOrWhiteSpace([string]$record.failure_category)) {
    $record.failure_category = "workflow_smoke_generation_incomplete"
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
