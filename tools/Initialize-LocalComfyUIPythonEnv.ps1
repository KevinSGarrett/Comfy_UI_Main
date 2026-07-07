<#
.SYNOPSIS
Creates a local ignored ComfyUI Python environment for development checks.

.DESCRIPTION
Dry-run by default. With -Execute, creates a venv under the ignored local
ComfyUI checkout, installs CUDA Torch wheels from the configured PyTorch wheel
index, installs the non-Torch ComfyUI requirements, and records import/CUDA
evidence. This never starts EC2, never downloads models, and never commits the
venv.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LocalComfyRoot = "",
  [string]$VenvPath = "",
  [string]$Python = "python",
  [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu128",
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

function Invoke-CapturedCommand {
  param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter(Mandatory=$true)][string[]]$Arguments,
    [string]$WorkingDirectory = ""
  )
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
      $output = @(& $FilePath @Arguments 2>&1)
    } else {
      Push-Location -LiteralPath $WorkingDirectory
      try {
        $output = @(& $FilePath @Arguments 2>&1)
      } finally {
        Pop-Location
      }
    }
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  return [ordered]@{
    command = "$FilePath $($Arguments -join ' ')"
    exit_code = $exitCode
    output_tail = (($output | Select-Object -Last 40) -join "`n")
  }
}

function Test-PythonTorch {
  param([string]$PythonExe)
  $probe = "import json, sys; r={'executable':sys.executable,'torch_imported':False,'torch_version':None,'cuda_available':False,'cuda_version':None,'device_count':0,'device_name':None,'error':None};`ntry:`n import torch; r['torch_imported']=True; r['torch_version']=getattr(torch,'__version__',None); r['cuda_available']=bool(torch.cuda.is_available()); r['cuda_version']=getattr(torch.version,'cuda',None); r['device_count']=torch.cuda.device_count(); r['device_name']=torch.cuda.get_device_name(0) if r['device_count'] else None`nexcept Exception as e:`n r['error']=str(e)`nprint(json.dumps(r))"
  $result = Invoke-CapturedCommand -FilePath $PythonExe -Arguments @("-c", $probe)
  $record = [ordered]@{
    command = $result.command
    exit_code = $result.exit_code
    output_tail = $result.output_tail
    parsed = $null
  }
  if ($result.exit_code -eq 0 -and ![string]::IsNullOrWhiteSpace($result.output_tail)) {
    try {
      $record.parsed = ($result.output_tail | Select-Object -Last 1 | ConvertFrom-Json)
    } catch {}
  }
  return $record
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($LocalComfyRoot)) {
  $LocalComfyRoot = Join-Path $ProjectRoot "ComfyUI"
}
$LocalComfyRoot = [System.IO.Path]::GetFullPath($LocalComfyRoot)
if ([string]::IsNullOrWhiteSpace($VenvPath)) {
  $VenvPath = Join-Path $LocalComfyRoot ".venv"
}
$VenvPath = [System.IO.Path]::GetFullPath($VenvPath)

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_LOCAL_COMFYUI_PYTHON_ENV_$stamp.json"
}

$requirements = Join-Path $LocalComfyRoot "requirements.txt"
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
$venvExists = Test-Path -LiteralPath $venvPython
$mainPyExists = Test-Path -LiteralPath (Join-Path $LocalComfyRoot "main.py")
$requirementsExists = Test-Path -LiteralPath $requirements
$commands = New-Object System.Collections.ArrayList
$errors = New-Object System.Collections.ArrayList

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "initialize_local_comfyui_python_env"
  project_root = $ProjectRoot
  local_comfy_root = $LocalComfyRoot
  venv_path = $VenvPath
  venv_python = $venvPython
  torch_index_url = $TorchIndexUrl
  execute = [bool]$Execute
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  model_binaries_downloaded = $false
  main_py_exists = $mainPyExists
  requirements_exists = $requirementsExists
  venv_preexisting = $venvExists
  commands = @()
  torch_probe = $null
  result = "dry_run_local_python_env_plan"
  failure_category = $null
  errors = @()
  next_action = "Run with -Execute to create the ignored venv and install CUDA Torch plus ComfyUI requirements."
}

if (!$mainPyExists) {
  $record.result = "blocked_local_comfyui_not_found"
  $record.failure_category = "local_comfyui_not_found"
  [void]$errors.Add("Local ComfyUI main.py not found: $LocalComfyRoot")
} elseif (!$requirementsExists) {
  $record.result = "blocked_requirements_not_found"
  $record.failure_category = "requirements_not_found"
  [void]$errors.Add("requirements.txt not found: $requirements")
} elseif ($Execute) {
  if (!(Test-Path -LiteralPath $venvPython)) {
    [void]$commands.Add((Invoke-CapturedCommand -FilePath $Python -Arguments @("-m", "venv", $VenvPath)))
  }
  if (Test-Path -LiteralPath $venvPython) {
    [void]$commands.Add((Invoke-CapturedCommand -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")))
    [void]$commands.Add((Invoke-CapturedCommand -FilePath $venvPython -Arguments @("-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", $TorchIndexUrl)))
    $filteredRequirements = Join-Path ([System.IO.Path]::GetTempPath()) ("comfyui_non_torch_requirements_{0}.txt" -f $stamp)
    Get-Content -LiteralPath $requirements |
      Where-Object { $_ -notmatch '^\s*torch(|vision|audio)\s*($|[<>=#])' } |
      Set-Content -LiteralPath $filteredRequirements -Encoding UTF8
    [void]$commands.Add((Invoke-CapturedCommand -FilePath $venvPython -Arguments @("-m", "pip", "install", "-r", $filteredRequirements)))
    $record.torch_probe = Test-PythonTorch -PythonExe $venvPython
    $torchParsed = $record.torch_probe.parsed
    if ($commands | Where-Object { $_.exit_code -ne 0 }) {
      $record.result = "local_python_env_install_failed"
      $record.failure_category = "pip_install_failed"
      [void]$errors.Add("One or more Python environment commands failed.")
    } elseif ($null -eq $torchParsed -or ![bool]$torchParsed.torch_imported) {
      $record.result = "local_python_env_torch_import_failed"
      $record.failure_category = "torch_import_failed"
      [void]$errors.Add("Torch did not import from the local venv.")
    } elseif (![bool]$torchParsed.cuda_available) {
      $record.result = "local_python_env_ready_cpu_only"
      $record.failure_category = "torch_cuda_unavailable"
      [void]$errors.Add("Torch imports from the local venv but CUDA is not available.")
    } else {
      $record.result = "local_python_env_cuda_ready"
      $record.next_action = "Rerun tools/Test-LocalComfyUIDevPreflight.ps1; local model placement is still required before local generation."
    }
  } else {
    $record.result = "local_python_env_venv_create_failed"
    $record.failure_category = "venv_create_failed"
    [void]$errors.Add("Venv python was not found after creation attempt.")
  }
}

$record.commands = @($commands)
$record.errors = @($errors)
if ($errors.Count -gt 0 -and [string]::IsNullOrWhiteSpace($record.failure_category)) {
  $record.failure_category = "local_python_env_error"
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
$record | ConvertTo-Json -Depth 30
if ($record.result -like "blocked_*" -or $record.result -like "*failed") { exit 2 }
