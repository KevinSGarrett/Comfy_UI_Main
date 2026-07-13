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
