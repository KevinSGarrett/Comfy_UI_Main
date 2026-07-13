function ConvertTo-EC2SafetyGitRelativePath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return "" }
  $value = ([string]$Path).Trim().Replace("\", "/")
  while ($value.StartsWith("./")) { $value = $value.Substring(2) }
  return $value.Trim("/")
}

function Test-EC2SafetyGitPathUnderRoot {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$Root
  )
  $normalizedPath = ConvertTo-EC2SafetyGitRelativePath $Path
  $normalizedRoot = ConvertTo-EC2SafetyGitRelativePath $Root
  if ([string]::IsNullOrWhiteSpace($normalizedPath) -or [string]::IsNullOrWhiteSpace($normalizedRoot)) { return $false }
  return ($normalizedPath -eq $normalizedRoot -or $normalizedPath.StartsWith("$normalizedRoot/"))
}

function Get-EC2SafetyPorcelainPath {
  param([string]$Line)
  if ([string]::IsNullOrWhiteSpace($Line)) { return "" }
  if ($Line.Length -gt 3) { return ConvertTo-EC2SafetyGitRelativePath $Line.Substring(3).Trim() }
  return ConvertTo-EC2SafetyGitRelativePath $Line.Trim()
}

function Resolve-GitCheckpointCleanliness {
  param(
    [string[]]$PorcelainLines = @(),
    [string[]]$PreservedExcludePath = @()
  )

  $normalizedExcludes = @($PreservedExcludePath | ForEach-Object { ConvertTo-EC2SafetyGitRelativePath $_ } | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
  $stagedPaths = New-Object System.Collections.ArrayList
  $excludedDirtyPaths = New-Object System.Collections.ArrayList
  $unexpectedDirtyPaths = New-Object System.Collections.ArrayList

  foreach ($line in @($PorcelainLines | Where-Object { ![string]::IsNullOrWhiteSpace($_) })) {
    $path = Get-EC2SafetyPorcelainPath $line
    if ([string]::IsNullOrWhiteSpace($path)) {
      [void]$unexpectedDirtyPaths.Add([string]$line)
      continue
    }
    $indexStatus = $(if ($line.Length -ge 1) { $line.Substring(0, 1) } else { "?" })
    $isStaged = ($indexStatus -ne " " -and $indexStatus -ne "?")
    if ($isStaged) {
      [void]$stagedPaths.Add($path)
      continue
    }
    $excluded = $false
    foreach ($excludePath in $normalizedExcludes) {
      if (Test-EC2SafetyGitPathUnderRoot -Path $path -Root $excludePath) {
        $excluded = $true
        break
      }
    }
    if ($excluded) { [void]$excludedDirtyPaths.Add($path) } else { [void]$unexpectedDirtyPaths.Add($path) }
  }

  $actualClean = (@($PorcelainLines | Where-Object { ![string]::IsNullOrWhiteSpace($_) }).Count -eq 0)
  $effectiveClean = ($stagedPaths.Count -eq 0 -and $unexpectedDirtyPaths.Count -eq 0)
  return [pscustomobject][ordered]@{
    actual_clean = $actualClean
    effective_clean = $effectiveClean
    normalized_exclude_paths = @($normalizedExcludes)
    staged_paths = @($stagedPaths)
    excluded_dirty_paths = @($excludedDirtyPaths)
    unexpected_dirty_paths = @($unexpectedDirtyPaths)
    porcelain_count = @($PorcelainLines | Where-Object { ![string]::IsNullOrWhiteSpace($_) }).Count
    staged_count = $stagedPaths.Count
    excluded_dirty_count = $excludedDirtyPaths.Count
    unexpected_dirty_count = $unexpectedDirtyPaths.Count
  }
}

function Get-LocalGitCheckpointGate {
  param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [string[]]$PreservedExcludePath = @()
  )

  $result = [ordered]@{
    git_root = $null
    head = $null
    origin_main = $null
    expected_remote_head = $null
    local_matches_origin = $false
    actual_clean = $false
    effective_clean = $false
    clean = $false
    porcelain_count = $null
    staged_count = $null
    excluded_dirty_count = $null
    unexpected_dirty_count = $null
    normalized_exclude_paths = @()
    staged_paths = @()
    excluded_dirty_paths = @()
    unexpected_dirty_paths = @()
    remote = $null
    result = "fail"
    error = $null
  }
  try {
    $result.git_root = (git -C $ProjectRoot rev-parse --show-toplevel 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.git_root)) { throw "Project root is not a Git checkout." }
    $result.head = (git -C $ProjectRoot rev-parse HEAD 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.head)) { throw "Unable to resolve local HEAD." }
    $result.origin_main = (git -C $ProjectRoot rev-parse origin/main 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$result.origin_main)) { throw "Unable to resolve origin/main." }
    $result.expected_remote_head = $result.origin_main
    $result.local_matches_origin = ([string]$result.head -eq [string]$result.origin_main)
    $porcelain = @(git -C $ProjectRoot status --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0) { throw "Unable to read Git porcelain status." }
    $cleanliness = Resolve-GitCheckpointCleanliness -PorcelainLines $porcelain -PreservedExcludePath $PreservedExcludePath
    foreach ($name in @("actual_clean", "effective_clean", "porcelain_count", "staged_count", "excluded_dirty_count", "unexpected_dirty_count", "normalized_exclude_paths", "staged_paths", "excluded_dirty_paths", "unexpected_dirty_paths")) {
      $result[$name] = $cleanliness.$name
    }
    $result.clean = $cleanliness.effective_clean
    $remoteLines = @(git -C $ProjectRoot remote -v 2>$null)
    $result.remote = (($remoteLines | Where-Object { $_ -match "^origin\s+" }) | Select-Object -First 1)
    $result.result = $(if ($result.local_matches_origin -and $result.effective_clean) { "pass" } else { "fail" })
  } catch {
    $result.error = $_.Exception.Message
    $result.result = "fail"
  }
  return [pscustomobject]$result
}

function Test-EC2RuntimeSafetyProperty {
  param(
    [object]$Object,
    [Parameter(Mandatory=$true)][string]$Name
  )
  return ($null -ne $Object -and @($Object.PSObject.Properties.Name) -contains $Name)
}

function Read-EC2RuntimeSafetyEvidence {
  param([string]$Path)

  $result = [ordered]@{
    path = $Path
    found = $false
    json_valid = $false
    payload = $null
    read_error = $null
  }
  if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path -PathType Leaf)) {
    return [pscustomobject]$result
  }
  $result.found = $true
  try {
    $result.payload = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $result.json_valid = ($null -ne $result.payload)
  } catch {
    $result.read_error = $_.Exception.Message
  }
  return [pscustomobject]$result
}

function Get-EmergencyStopScheduleStatus {
  param(
    [string]$Path,
    [Parameter(Mandatory=$true)][string]$ExpectedWindowId,
    [Parameter(Mandatory=$true)][string]$ExpectedInstanceId,
    [Parameter(Mandatory=$true)][string]$ExpectedRegion
  )

  $evidence = Read-EC2RuntimeSafetyEvidence -Path $Path
  $payload = $evidence.payload
  $checks = [ordered]@{
    evidence_found = $evidence.found
    json_valid = $evidence.json_valid
    result_verified = ($null -ne $payload -and [string]$payload.result -ceq "emergency_stop_schedule_created_and_verified")
    runtime_window_match = ($null -ne $payload -and [string]$payload.runtime_window_id -ceq $ExpectedWindowId)
    instance_match = ($null -ne $payload -and [string]$payload.instance_id -ceq $ExpectedInstanceId)
    region_match = ($null -ne $payload -and [string]$payload.region -ceq $ExpectedRegion)
    execute_true = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "execute") -and [bool]$payload.execute)
    aws_contacted_true = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "aws_contacted") -and [bool]$payload.aws_contacted)
    schedule_verified_true = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "schedule_verified") -and [bool]$payload.schedule_verified)
    ec2_not_started_by_schedule = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "ec2_started") -and -not [bool]$payload.ec2_started)
    generation_not_executed = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "generation_executed") -and -not [bool]$payload.generation_executed)
  }
  $verified = (@($checks.GetEnumerator() | Where-Object { -not [bool]$_.Value }).Count -eq 0)
  return [pscustomobject][ordered]@{
    path = $Path
    found = $evidence.found
    json_valid = $evidence.json_valid
    result = $(if ($null -ne $payload) { [string]$payload.result } else { $null })
    runtime_window_id = $(if ($null -ne $payload) { [string]$payload.runtime_window_id } else { $null })
    instance_id = $(if ($null -ne $payload) { [string]$payload.instance_id } else { $null })
    region = $(if ($null -ne $payload) { [string]$payload.region } else { $null })
    verified = $verified
    status = $(if ($verified) { "pass" } else { "blocked" })
    failure_category = $(if ($verified) { $null } else { "live_emergency_stop_schedule_not_verified" })
    checks = $checks
    read_error = $evidence.read_error
  }
}

function Get-InstanceStopWatchdogStatus {
  param(
    [string]$Path,
    [Parameter(Mandatory=$true)][string]$ExpectedWindowId,
    [Parameter(Mandatory=$true)][string]$ExpectedInstanceId,
    [Parameter(Mandatory=$true)][string]$ExpectedRegion
  )

  $evidence = Read-EC2RuntimeSafetyEvidence -Path $Path
  $payload = $evidence.payload
  $checks = [ordered]@{
    evidence_found = $evidence.found
    json_valid = $evidence.json_valid
    result_verified = ($null -ne $payload -and [string]$payload.result -ceq "instance_stop_watchdog_started_and_capability_verified")
    runtime_window_match = ($null -ne $payload -and [string]$payload.runtime_window_id -ceq $ExpectedWindowId)
    instance_match = ($null -ne $payload -and [string]$payload.instance_id -ceq $ExpectedInstanceId)
    region_match = ($null -ne $payload -and [string]$payload.region -ceq $ExpectedRegion)
    execute_true = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "execute") -and [bool]$payload.execute)
    aws_contacted_true = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "aws_contacted") -and [bool]$payload.aws_contacted)
    command_success = ($null -ne $payload -and [string]$payload.command_status -ceq "Success")
    capability_verified = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "stop_capability_verified") -and [bool]$payload.stop_capability_verified)
    watchdog_pid_present = ($null -ne $payload -and [string]$payload.watchdog_pid -match "^[0-9]+$")
    generation_not_executed = ($null -ne $payload -and (Test-EC2RuntimeSafetyProperty $payload "generation_executed") -and -not [bool]$payload.generation_executed)
  }
  $verified = (@($checks.GetEnumerator() | Where-Object { -not [bool]$_.Value }).Count -eq 0)
  return [pscustomobject][ordered]@{
    path = $Path
    found = $evidence.found
    json_valid = $evidence.json_valid
    result = $(if ($null -ne $payload) { [string]$payload.result } else { $null })
    runtime_window_id = $(if ($null -ne $payload) { [string]$payload.runtime_window_id } else { $null })
    command_id = $(if ($null -ne $payload) { [string]$payload.command_id } else { $null })
    watchdog_pid = $(if ($null -ne $payload) { [string]$payload.watchdog_pid } else { $null })
    verified = $verified
    status = $(if ($verified) { "pass" } else { "blocked" })
    failure_category = $(if ($verified) { $null } else { "instance_stop_watchdog_not_verified" })
    checks = $checks
    read_error = $evidence.read_error
  }
}

function Invoke-VerifiedInstanceWatchdog {
  param(
    [Parameter(Mandatory=$true)][string]$WatchdogScriptPath,
    [Parameter(Mandatory=$true)][string]$InstanceId,
    [Parameter(Mandatory=$true)][string]$Region,
    [Parameter(Mandatory=$true)][string]$RuntimeWindowId,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [int]$StopAfterMinutes = 60,
    [string]$TrackerId = "",
    [string]$ItemId = ""
  )

  $arguments = @(
    "-NoProfile", "-File", $WatchdogScriptPath,
    "-InstanceId", $InstanceId,
    "-Region", $Region,
    "-RuntimeWindowId", $RuntimeWindowId,
    "-StopAfterMinutes", [string]$StopAfterMinutes,
    "-OutFile", $OutFile,
    "-Execute"
  )
  if (![string]::IsNullOrWhiteSpace($TrackerId)) { $arguments += @("-TrackerId", $TrackerId) }
  if (![string]::IsNullOrWhiteSpace($ItemId)) { $arguments += @("-ItemId", $ItemId) }

  $global:LASTEXITCODE = 0
  $output = @(& powershell @arguments 2>&1)
  $exitCode = $LASTEXITCODE
  $status = Get-InstanceStopWatchdogStatus -Path $OutFile -ExpectedWindowId $RuntimeWindowId -ExpectedInstanceId $InstanceId -ExpectedRegion $Region
  $outputText = (($output | ForEach-Object { [string]$_ }) -join [Environment]::NewLine).Trim()
  $outputTail = $(if ($outputText.Length -gt 2000) { $outputText.Substring($outputText.Length - 2000) } else { $outputText })
  $status | Add-Member -NotePropertyName exit_code -NotePropertyValue $exitCode
  $status | Add-Member -NotePropertyName output_tail -NotePropertyValue $outputTail
  if ($exitCode -ne 0 -or !$status.verified) {
    throw "Instance stop watchdog verification failed for runtime window $RuntimeWindowId (exit=$exitCode, result=$($status.result))."
  }
  return $status
}
