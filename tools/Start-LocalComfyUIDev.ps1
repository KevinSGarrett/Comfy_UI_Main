<#
.SYNOPSIS
Starts or plans a local ComfyUI development server for low-cost workflow checks.

.DESCRIPTION
Dry-run by default. With -Execute, starts an existing local ComfyUI checkout in
a hidden process using low-VRAM-friendly defaults. This lane is for development
iteration only and never replaces final EC2 A10G proof.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LocalComfyRoot = "",
  [int]$Port = 8188,
  [string]$HostAddress = "127.0.0.1",
  [switch]$LowVram,
  [string]$ExtraArgs = "",
  [string]$OutFile = "",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Find-ComfyRoot {
  param([string]$ExplicitRoot)
  $candidates = New-Object System.Collections.ArrayList
  if (![string]::IsNullOrWhiteSpace($ExplicitRoot)) { [void]$candidates.Add($ExplicitRoot) }
  foreach ($candidate in @(
    "C:\Comfy_UI_Main\ComfyUI",
    "C:\Comfy_UI_Main\ComfyUI_windows_portable\ComfyUI"
  )) {
    [void]$candidates.Add($candidate)
  }
  foreach ($candidate in @($candidates | Select-Object -Unique)) {
    $mainPath = Join-Path $candidate "main.py"
    if (Test-Path -LiteralPath $mainPath) {
      return [System.IO.Path]::GetFullPath($candidate)
    }
  }
  return $null
}

function Find-Python {
  param([string]$ComfyRoot)
  $parentRoot = Split-Path -Parent $ComfyRoot
  foreach ($candidate in @(
    (Join-Path $ComfyRoot "venv\Scripts\python.exe"),
    (Join-Path $ComfyRoot ".venv\Scripts\python.exe"),
    (Join-Path $parentRoot "python_embeded\python.exe"),
    (Join-Path $parentRoot "python_embedded\python.exe"),
    "python"
  )) {
    if ($candidate -eq "python") { return $candidate }
    if (Test-Path -LiteralPath $candidate) { return $candidate }
  }
  return "python"
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "runtime_artifacts\run_manifests\LOCAL_COMFY_DEV_START_$stamp.json"
}

$selectedRoot = Find-ComfyRoot -ExplicitRoot $LocalComfyRoot
$gpu = [ordered]@{ nvidia_smi_found = $false; name = $null; memory_total_mib = $null }
try {
  $gpuRaw = (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null | Select-Object -First 1)
  if (![string]::IsNullOrWhiteSpace($gpuRaw)) {
    $parts = @($gpuRaw -split ",")
    $gpu.nvidia_smi_found = $true
    $gpu.name = $parts[0].Trim()
    $gpu.memory_total_mib = [int](($parts[1] -replace "[^0-9]", "").Trim())
  }
} catch {}

$argsList = @("main.py", "--listen", $HostAddress, "--port", [string]$Port)
if ($LowVram -or (($gpu.memory_total_mib -as [int]) -le 8192)) {
  $argsList += "--lowvram"
}
if (![string]::IsNullOrWhiteSpace($ExtraArgs)) {
  $argsList += @($ExtraArgs -split "\s+" | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
}

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "start_local_comfyui_dev"
  project_root = $ProjectRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  local_comfy_root = $selectedRoot
  local_gpu = $gpu
  host = $HostAddress
  port = $Port
  low_vram_args_enabled = ($argsList -contains "--lowvram")
  execute = [bool]$Execute
  process_id = $null
  result = "dry_run_local_comfyui_start_plan"
  failure_category = $null
  errors = @()
  next_action = "Use local ComfyUI for prompt/workflow iteration only; EC2 final proof is still required."
}

if ([string]::IsNullOrWhiteSpace($selectedRoot)) {
  $record.result = "blocked_local_comfyui_not_found"
  $record.failure_category = "local_comfyui_not_found"
  $record.next_action = "Install or point -LocalComfyRoot at a real ComfyUI checkout containing main.py."
} else {
  $python = Find-Python -ComfyRoot $selectedRoot
  $record.python = $python
  $record.command = "$python $($argsList -join ' ')"
  if ($Execute) {
    try {
      $process = Start-Process -FilePath $python -ArgumentList $argsList -WorkingDirectory $selectedRoot -PassThru -WindowStyle Hidden
      $record.process_id = $process.Id
      $record.result = "local_comfyui_dev_started"
      $record.next_action = "Open http://$HostAddress`:$Port for low-cost local workflow iteration, then keep EC2 for target-runtime proof only."
    } catch {
      $record.result = "local_comfyui_dev_start_failed"
      $record.failure_category = "local_comfyui_start_failed"
      $record.errors += $_.Exception.Message
    }
  }
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
$record | ConvertTo-Json -Depth 20
if ($record.errors.Count -gt 0 -or ($Execute -and $record.result -ne "local_comfyui_dev_started")) { exit 2 }
