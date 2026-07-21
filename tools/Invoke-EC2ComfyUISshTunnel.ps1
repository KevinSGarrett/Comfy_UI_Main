<#
.SYNOPSIS
Starts, stops, or reports status for the EC2 ComfyUI SSH local port forward.

.DESCRIPTION
Forwards local TCP 8188 to remote ComfyUI at 127.0.0.1:8188 on the EC2 host.
Use this for temporary EC2 UI/API access through http://127.0.0.1:8188 — stop the
tunnel when finished; do not leave it running indefinitely.

.EXAMPLE
# Start tunnel (background ssh process)
.\tools\Invoke-EC2ComfyUISshTunnel.ps1 -Action Start

.EXAMPLE
# Check whether local 8188 is forwarded
.\tools\Invoke-EC2ComfyUISshTunnel.ps1 -Action Status

.EXAMPLE
# Stop tunnel started by this helper
.\tools\Invoke-EC2ComfyUISshTunnel.ps1 -Action Stop
#>
param(
  [ValidateSet("Start", "Stop", "Status")]
  [string]$Action = "Status",
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RemoteHost = "195.26.233.100",
  [string]$RemoteUser = "root",
  [int]$RemotePort = 52077,
  [int]$LocalPort = 8188,
  [string]$RemoteBindHost = "127.0.0.1",
  [int]$RemoteBindPort = 8188,
  [string]$IdentityFile = "",
  [string]$StateFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-IdentityPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) {
    $Path = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
  }
  if ($Path -like "~/*") {
    $Path = Join-Path $env:USERPROFILE ($Path.Substring(2))
  } elseif ($Path -like "~\*") {
    $Path = Join-Path $env:USERPROFILE ($Path.Substring(2))
  }
  return [System.IO.Path]::GetFullPath($Path)
}

function Get-SshExecutable {
  $candidate = Join-Path $env:WINDIR "System32\OpenSSH\ssh.exe"
  if (Test-Path -LiteralPath $candidate) { return $candidate }
  $fromPath = Get-Command ssh -ErrorAction SilentlyContinue
  if ($fromPath) { return $fromPath.Source }
  throw "OpenSSH client (ssh.exe) not found on PATH or in System32\\OpenSSH."
}

function Write-TunnelState {
  param(
    [hashtable]$Record,
    [string]$Path
  )
  $dir = Split-Path -Parent $Path
  if (!(Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Record | ConvertTo-Json -Depth 6), $encoding)
}

function Read-TunnelState {
  param([string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { return $null }
  try {
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
  } catch {
    return $null
  }
}

function Get-LocalPortOwner {
  param([int]$Port)
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $conn) { return $null }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    return [ordered]@{
      port = $Port
      process_id = $conn.OwningProcess
      process_name = if ($proc) { $proc.ProcessName } else { $null }
    }
  } catch {
    return $null
  }
}

function Test-ProcessAlive {
  param([int]$ProcessId)
  if ($ProcessId -le 0) { return $false }
  return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($StateFile)) {
  $StateFile = Join-Path $ProjectRoot "runtime_artifacts\run_manifests\EC2_COMFYUI_SSH_TUNNEL.state.json"
}
$StateFile = [System.IO.Path]::GetFullPath($StateFile)
$keyPath = Resolve-IdentityPath -Path $IdentityFile
$forwardSpec = "{0}:{1}:{2}" -f $LocalPort, $RemoteBindHost, $RemoteBindPort
$sshExe = Get-SshExecutable

$result = [ordered]@{
  action = $Action
  status = "unknown"
  local_url = "http://127.0.0.1:$LocalPort"
  forward = $forwardSpec
  remote_target = "{0}@{1}:{2}" -f $RemoteUser, $RemoteHost, $RemotePort
  identity_file = $keyPath
  state_file = $StateFile
  process_id = $null
  message = $null
}

switch ($Action) {
  "Start" {
    if (!(Test-Path -LiteralPath $keyPath)) {
      $result.status = "blocked"
      $result.message = "Identity file not found at resolved path."
      $result | ConvertTo-Json -Depth 6
      exit 2
    }

    $existing = Read-TunnelState -Path $StateFile
    if ($existing -and (Test-ProcessAlive -ProcessId ([int]$existing.process_id))) {
      $owner = Get-LocalPortOwner -Port $LocalPort
      $result.status = "already_running"
      $result.process_id = [int]$existing.process_id
      $result.message = "Tunnel process already recorded; use -Action Stop before starting again."
      if ($owner) { $result.port_owner = $owner }
      $result | ConvertTo-Json -Depth 6
      exit 0
    }

    $portOwner = Get-LocalPortOwner -Port $LocalPort
    if ($portOwner -and $portOwner.process_name -ne "ssh") {
      $result.status = "blocked"
      $result.message = "Local port $LocalPort is already in use by another process."
      $result.port_owner = $portOwner
      $result | ConvertTo-Json -Depth 6
      exit 3
    }

    $sshArgs = @(
      "-N",
      "-L", $forwardSpec,
      "-p", "$RemotePort",
      "-i", $keyPath,
      "-o", "ExitOnForwardFailure=yes",
      "-o", "ServerAliveInterval=60",
      "-o", "BatchMode=yes",
      "{0}@{1}" -f $RemoteUser, $RemoteHost
    )

    try {
      $proc = Start-Process -FilePath $sshExe -ArgumentList $sshArgs -PassThru -WindowStyle Hidden
    } catch {
      $result.status = "failed"
      $result.message = $_.Exception.Message
      $result | ConvertTo-Json -Depth 6
      exit 4
    }

    Start-Sleep -Seconds 2
    if (!(Test-ProcessAlive -ProcessId $proc.Id)) {
      $result.status = "failed"
      $result.process_id = $proc.Id
      $result.message = "ssh exited immediately; check host reachability, key authorization, and remote ComfyUI."
      $result | ConvertTo-Json -Depth 6
      exit 5
    }

    $record = [ordered]@{
      process_id = $proc.Id
      started_at = (Get-Date).ToString("o")
      forward = $forwardSpec
      remote_target = $result.remote_target
      identity_file = $keyPath
      local_url = $result.local_url
    }
    Write-TunnelState -Record $record -Path $StateFile

    $result.status = "started"
    $result.process_id = $proc.Id
    $result.message = "Tunnel running. Open $($result.local_url) while needed, then run -Action Stop."
    $result | ConvertTo-Json -Depth 6
    exit 0
  }

  "Stop" {
    $stopped = $false
    $state = Read-TunnelState -Path $StateFile
    if ($state -and (Test-ProcessAlive -ProcessId ([int]$state.process_id))) {
      Stop-Process -Id ([int]$state.process_id) -Force -ErrorAction SilentlyContinue
      $stopped = $true
      $result.process_id = [int]$state.process_id
    }

    $owner = Get-LocalPortOwner -Port $LocalPort
    if ($owner -and $owner.process_name -eq "ssh") {
      Stop-Process -Id $owner.process_id -Force -ErrorAction SilentlyContinue
      $stopped = $true
      $result.process_id = $owner.process_id
    }

    if (Test-Path -LiteralPath $StateFile) {
      Remove-Item -LiteralPath $StateFile -Force -ErrorAction SilentlyContinue
    }

    if ($stopped) {
      $result.status = "stopped"
      $result.message = "Tunnel stopped."
    } else {
      $result.status = "not_running"
      $result.message = "No recorded or listening ssh tunnel on local port $LocalPort."
    }
    $result | ConvertTo-Json -Depth 6
    exit 0
  }

  "Status" {
    $state = Read-TunnelState -Path $StateFile
    $owner = Get-LocalPortOwner -Port $LocalPort
    $alive = $false
    if ($state) {
      $alive = Test-ProcessAlive -ProcessId ([int]$state.process_id)
      $result.process_id = [int]$state.process_id
    }
    if ($alive -or ($owner -and $owner.process_name -eq "ssh")) {
      $result.status = "running"
      $result.message = "Tunnel appears active on local port $LocalPort. Run -Action Stop when finished."
      if ($owner) { $result.port_owner = $owner }
    } else {
      $result.status = "not_running"
      $result.message = "No active tunnel. Start with -Action Start; stop with -Action Stop."
    }
    $result | ConvertTo-Json -Depth 6
    exit 0
  }
}
