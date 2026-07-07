<#
.SYNOPSIS
Runs a bounded local ComfyUI smoke from a verified run package.

.DESCRIPTION
Dry-run by default. In dry-run mode this helper validates a run package manifest,
resolves its prompt_request.json, checks hash/lane consistency, finds the local
ComfyUI checkout and Python, and writes a local-only evidence plan.

With -Execute, it starts the ignored local ComfyUI checkout, waits for
/object_info, posts the packaged prompt request to /prompt, polls /history,
copies generated images into Plan/Instructions/Operations/Pulled_Back_Artifacts,
writes a local artifact manifest, and stops the local process it started.

This helper is for low-cost local iteration only. It never replaces EC2
target-runtime proof.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RunPackageManifestFile = "",
  [string]$LaneId = "",
  [string]$LocalComfyRoot = "",
  [string]$ExtraModelPathsConfig = "C:\Comfy_UI_Main\config\comfyui_extra_model_paths.yaml",
  [int]$Port = 8188,
  [string]$HostAddress = "127.0.0.1",
  [string]$OutFile = "",
  [string]$PullbackRoot = "",
  [int]$StartTimeoutSeconds = 240,
  [int]$TimeoutSeconds = 900,
  [int]$PollSeconds = 3,
  [switch]$LowVram,
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 40
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Has-Property {
  param([object]$Object, [string]$Name)
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "JSON file not found: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Get-RelativePathCompat {
  param([string]$BasePath, [string]$TargetPath)
  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("\", "/")
}

function Resolve-ProjectPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function ConvertTo-ProjectRelativePath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  return Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path
}

function Get-FileSha256Lower {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Find-ComfyRoot {
  param([string]$ExplicitRoot)
  $candidates = New-Object System.Collections.ArrayList
  if (![string]::IsNullOrWhiteSpace($ExplicitRoot)) { [void]$candidates.Add($ExplicitRoot) }
  foreach ($candidate in @(
    "C:\Comfy_UI_Main\ComfyUI",
    "C:\Comfy_UI_Main\ComfyUI_windows_portable\ComfyUI",
    "C:\Comfy_UI\ComfyUI",
    "C:\Comfy_UI\ComfyUI_windows_portable\ComfyUI",
    "C:\Comfy_UI\portable\ComfyUI",
    "C:\Comfy_UI\Runtime\ComfyUI",
    "C:\Comfy_UI"
  )) {
    [void]$candidates.Add($candidate)
  }

  foreach ($candidate in @($candidates | Select-Object -Unique)) {
    if (Test-Path -LiteralPath (Join-Path $candidate "main.py") -PathType Leaf) {
      return [System.IO.Path]::GetFullPath($candidate)
    }
  }
  return $null
}

function Find-Python {
  param([string]$ComfyRoot)
  $parentRoot = Split-Path -Parent $ComfyRoot
  foreach ($candidate in @(
    (Join-Path $ComfyRoot ".venv\Scripts\python.exe"),
    (Join-Path $ComfyRoot "venv\Scripts\python.exe"),
    (Join-Path $parentRoot "python_embeded\python.exe"),
    (Join-Path $parentRoot "python_embedded\python.exe"),
    "python"
  )) {
    if ($candidate -eq "python") { return $candidate }
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
  }
  return "python"
}

function Get-RunPackageStatus {
  param([string]$Path)

  $status = [ordered]@{
    supplied = ![string]::IsNullOrWhiteSpace($Path)
    file = $Path
    found = $false
    valid = $false
    errors = @()
    run_id = $null
    lane_id = $null
    lane_match = $false
    result = $null
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
    $status.errors += "RunPackageManifestFile is required."
    return $status
  }

  $manifestPath = Resolve-ProjectPath -Path $Path
  $status.file = ConvertTo-ProjectRelativePath -Path $manifestPath
  if (!(Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    $status.errors += "Run package manifest not found: $Path"
    return $status
  }
  $status.found = $true

  try {
    $manifest = Read-JsonFile -Path $manifestPath
  } catch {
    $status.errors += "Run package manifest JSON parse failed: $($_.Exception.Message)"
    return $status
  }

  if (Has-Property -Object $manifest -Name "run_id") { $status.run_id = [string]$manifest.run_id }
  if (Has-Property -Object $manifest -Name "lane_id") { $status.lane_id = [string]$manifest.lane_id }
  if (Has-Property -Object $manifest -Name "result") { $status.result = [string]$manifest.result }
  if ([string]::IsNullOrWhiteSpace($LaneId) -and ![string]::IsNullOrWhiteSpace([string]$status.lane_id)) {
    $script:LaneId = [string]$status.lane_id
  }
  $status.lane_match = (![string]::IsNullOrWhiteSpace($LaneId) -and [string]$status.lane_id -eq [string]$LaneId)
  if (!$status.lane_match) {
    $status.errors += "Run package lane_id '$($status.lane_id)' does not match selected lane '$LaneId'."
  }
  if ([string]$status.result -ne "pass_local_only") {
    $status.errors += "Run package result is '$($status.result)', not pass_local_only."
  }
  if ((Has-Property -Object $manifest -Name "ec2_started") -and [bool]$manifest.ec2_started) {
    $status.errors += "Run package records ec2_started=true; expected local-only package."
  }
  if ((Has-Property -Object $manifest -Name "generation_executed") -and [bool]$manifest.generation_executed) {
    $status.errors += "Run package records generation_executed=true; expected pre-execution package."
  }

  $promptPath = $null
  $expectedHash = $null
  if (Has-Property -Object $manifest -Name "generated_files") {
    $promptGenerated = @($manifest.generated_files | Where-Object { [string]$_.path -match '(^|/)prompt_request\.json$' } | Select-Object -First 1)
    if ($promptGenerated.Count -gt 0) {
      $promptPath = [string]$promptGenerated[0].path
      if (Has-Property -Object $promptGenerated[0] -Name "sha256") {
        $expectedHash = ([string]$promptGenerated[0].sha256).ToLowerInvariant()
      }
    }
  }
  if ([string]::IsNullOrWhiteSpace($promptPath) -and
      (Has-Property -Object $manifest -Name "package_dir") -and
      ![string]::IsNullOrWhiteSpace([string]$manifest.package_dir)) {
    $promptPath = ([string]$manifest.package_dir).TrimEnd("/", "\") + "/prompt_request.json"
  }
  if ([string]::IsNullOrWhiteSpace($expectedHash) -and
      (Has-Property -Object $manifest -Name "prompt_request") -and
      $null -ne $manifest.prompt_request -and
      (Has-Property -Object $manifest.prompt_request -Name "sha256")) {
    $expectedHash = ([string]$manifest.prompt_request.sha256).ToLowerInvariant()
  }
  if ([string]::IsNullOrWhiteSpace($promptPath)) {
    $status.errors += "Run package manifest does not identify prompt_request.json."
    return $status
  }

  $promptFullPath = Resolve-ProjectPath -Path $promptPath
  $status.prompt_request.path = ConvertTo-ProjectRelativePath -Path $promptFullPath
  $status.prompt_request.expected_sha256 = $expectedHash
  if (!(Test-Path -LiteralPath $promptFullPath -PathType Leaf)) {
    $status.errors += "Run package prompt_request.json not found: $promptPath"
    return $status
  }

  $actualHash = Get-FileSha256Lower -Path $promptFullPath
  $status.prompt_request.actual_sha256 = $actualHash
  $status.prompt_request.hash_match = (![string]::IsNullOrWhiteSpace($expectedHash) -and $actualHash -eq $expectedHash)
  if (![string]::IsNullOrWhiteSpace($expectedHash) -and !$status.prompt_request.hash_match) {
    $status.errors += "Run package prompt_request.json sha256 does not match manifest."
  }

  try {
    $request = Read-JsonFile -Path $promptFullPath
    $status.prompt_request.json_valid = $true
    if (Has-Property -Object $request -Name "client_id") {
      $status.prompt_request.client_id = [string]$request.client_id
    }
    if ((Has-Property -Object $request -Name "prompt") -and $null -ne $request.prompt) {
      $status.prompt_request.node_count = @($request.prompt.PSObject.Properties).Count
    } else {
      $status.errors += "Run package prompt_request.json has no prompt object."
    }
  } catch {
    $status.errors += "Run package prompt_request.json parse failed: $($_.Exception.Message)"
  }

  $status.valid = ($status.errors.Count -eq 0)
  return $status
}

function Wait-ObjectInfo {
  param([string]$BaseUrl, [int]$DeadlineSeconds)

  $deadline = (Get-Date).AddSeconds($DeadlineSeconds)
  $lastError = $null
  while ((Get-Date) -lt $deadline) {
    try {
      return Invoke-RestMethod -Method Get -Uri "$BaseUrl/object_info" -TimeoutSec 5
    } catch {
      $lastError = $_.Exception.Message
      Start-Sleep -Seconds 2
    }
  }
  throw "ComfyUI /object_info not ready before timeout. Last error: $lastError"
}

if (!(Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_LOCAL_COMFYUI_RUN_PACKAGE_SMOKE_$stamp.json"
}

$comfyRoot = Find-ComfyRoot -ExplicitRoot $LocalComfyRoot
$python = $(if (![string]::IsNullOrWhiteSpace($comfyRoot)) { Find-Python -ComfyRoot $comfyRoot } else { $null })
$runPackage = Get-RunPackageStatus -Path $RunPackageManifestFile
$apiBaseUrl = "http://$HostAddress`:$Port"
$resultName = $(if ($Execute) { "local_comfyui_run_package_smoke_started" } else { "dry_run_local_comfyui_run_package_smoke_plan" })
$record = [ordered]@{
  schema_version = "1.0"
  evidence_id = "W66-LOCAL-COMFYUI-RUN-PACKAGE-SMOKE-$stamp"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  mode = $(if ($Execute) { "execute" } else { "dry_run" })
  project_root = $ProjectRoot
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  lane_id = $LaneId
  api_base_url = $apiBaseUrl
  run_package = $runPackage
  local_comfy = [ordered]@{
    root = $comfyRoot
    python = $python
    extra_model_paths_config = $(if (![string]::IsNullOrWhiteSpace($ExtraModelPathsConfig)) { ConvertTo-ProjectRelativePath -Path $ExtraModelPathsConfig } else { $null })
    process_id = $null
    started_by_helper = $false
    stopped_by_helper = $false
    port_closed_after_stop = $false
  }
  object_info = [ordered]@{
    status = "not_started"
    node_count = $null
    required_nodes_present = @()
    missing_required_nodes = @()
  }
  prompt_id = $null
  history_status = "not_started"
  output_images = @()
  pulled_artifacts = @()
  pullback_dir = $null
  result = $resultName
  failure_category = $null
  errors = @()
  next_action = "Use local results for iteration only; EC2 target-runtime proof remains separate."
}

if ([string]::IsNullOrWhiteSpace($comfyRoot)) {
  $record.result = "blocked_local_comfyui_not_found"
  $record.failure_category = "local_comfyui_not_found"
  $record.errors += "Could not find a local ComfyUI checkout containing main.py."
}
if (!$runPackage.valid) {
  $record.result = $(if ($Execute) { "blocked_invalid_run_package" } else { "dry_run_local_comfyui_run_package_smoke_plan_invalid" })
  $record.failure_category = "invalid_run_package"
  $record.errors += @($runPackage.errors)
}
if (![string]::IsNullOrWhiteSpace($ExtraModelPathsConfig) -and !(Test-Path -LiteralPath $ExtraModelPathsConfig -PathType Leaf)) {
  $record.result = $(if ($Execute) { "blocked_extra_model_paths_config_missing" } else { "dry_run_local_comfyui_run_package_smoke_plan_invalid" })
  $record.failure_category = "extra_model_paths_config_missing"
  $record.errors += "Extra model paths config not found: $ExtraModelPathsConfig"
}

if ($Execute -and $record.errors.Count -eq 0) {
  $startedProcess = $null
  try {
    $argsList = @("main.py", "--listen", $HostAddress, "--port", [string]$Port)
    if ($LowVram) { $argsList += "--lowvram" }
    if (![string]::IsNullOrWhiteSpace($ExtraModelPathsConfig)) {
      $argsList += @("--extra-model-paths-config", $ExtraModelPathsConfig)
    }
    $startedProcess = Start-Process -FilePath $python -ArgumentList $argsList -WorkingDirectory $comfyRoot -PassThru -WindowStyle Hidden
    $record.local_comfy.process_id = $startedProcess.Id
    $record.local_comfy.started_by_helper = $true

    $objectInfo = Wait-ObjectInfo -BaseUrl $apiBaseUrl -DeadlineSeconds $StartTimeoutSeconds
    $required = @("CheckpointLoaderSimple", "EmptyLatentImage", "CLIPTextEncode", "KSampler", "VAEDecode", "SaveImage")
    $nodeNames = @($objectInfo.PSObject.Properties.Name)
    $present = @($required | Where-Object { $nodeNames -contains $_ })
    $missing = @($required | Where-Object { $nodeNames -notcontains $_ })
    $record.object_info.status = $(if ($missing.Count -eq 0) { "pass" } else { "fail" })
    $record.object_info.node_count = $nodeNames.Count
    $record.object_info.required_nodes_present = $present
    $record.object_info.missing_required_nodes = $missing
    if ($missing.Count -gt 0) {
      throw "ComfyUI missing required nodes: $($missing -join ', ')"
    }

    $promptFullPath = Resolve-ProjectPath -Path $runPackage.prompt_request.path
    $requestJson = Get-Content -Raw -LiteralPath $promptFullPath
    $promptResponse = Invoke-RestMethod -Method Post -Uri "$apiBaseUrl/prompt" -ContentType "application/json" -Body $requestJson -TimeoutSec 30
    $record.prompt_id = [string]$promptResponse.prompt_id
    if ([string]::IsNullOrWhiteSpace($record.prompt_id)) {
      throw "ComfyUI /prompt response did not include prompt_id."
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $outputs = @()
    $record.history_status = "polling"
    while ((Get-Date) -lt $deadline) {
      $history = Invoke-RestMethod -Method Get -Uri "$apiBaseUrl/history/$($record.prompt_id)" -TimeoutSec 20
      if (Has-Property -Object $history -Name $record.prompt_id) {
        $item = $history.PSObject.Properties[$record.prompt_id].Value
        if ($item.status -and $item.status.status_str) { $record.history_status = [string]$item.status.status_str }
        if ($item.outputs) {
          foreach ($node in $item.outputs.PSObject.Properties) {
            if (Has-Property -Object $node.Value -Name "images") {
              foreach ($image in @($node.Value.images)) {
                $outputs += [ordered]@{
                  node_id = $node.Name
                  filename = [string]$image.filename
                  subfolder = [string]$image.subfolder
                  type = [string]$image.type
                }
              }
            }
          }
          if ($outputs.Count -gt 0) { break }
        }
      }
      Start-Sleep -Seconds $PollSeconds
    }
    if ($outputs.Count -eq 0) {
      throw "No output images were found before timeout."
    }
    $record.output_images = $outputs

    if ([string]::IsNullOrWhiteSpace($PullbackRoot)) {
      $safeRunId = $(if (![string]::IsNullOrWhiteSpace($runPackage.run_id)) { $runPackage.run_id } else { "local_run_package_smoke" })
      $PullbackRoot = Join-Path $ProjectRoot "Plan\Instructions\Operations\Pulled_Back_Artifacts\$($safeRunId)_$stamp"
    }
    $imageDir = Join-Path $PullbackRoot "images"
    $null = New-Item -ItemType Directory -Force -Path $imageDir
    $record.pullback_dir = ConvertTo-ProjectRelativePath -Path $PullbackRoot

    foreach ($image in $outputs) {
      $sourceDir = Join-Path $comfyRoot "output"
      if (![string]::IsNullOrWhiteSpace($image.subfolder)) { $sourceDir = Join-Path $sourceDir $image.subfolder }
      $sourcePath = Join-Path $sourceDir $image.filename
      if (!(Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Generated output missing on disk: $sourcePath"
      }
      $destPath = Join-Path $imageDir $image.filename
      Copy-Item -LiteralPath $sourcePath -Destination $destPath -Force
      $file = Get-Item -LiteralPath $destPath
      $record.pulled_artifacts += [ordered]@{
        source = ConvertTo-ProjectRelativePath -Path $sourcePath
        local_path = ConvertTo-ProjectRelativePath -Path $destPath
        bytes = $file.Length
        sha256 = Get-FileSha256Lower -Path $destPath
        node_id = $image.node_id
        type = $image.type
      }
    }
    $record.generation_executed = $true
    $record.history_status = "outputs_found"
    $record.result = "pass_local_run_package_generation_smoke"

    $artifactManifestPath = Join-Path $PullbackRoot "LOCAL_ARTIFACT_MANIFEST.json"
    Write-JsonNoBom -Value $record -Path $artifactManifestPath -Depth 50
  } catch {
    $record.errors += $_.Exception.Message
    $record.result = "fail_local_run_package_generation_smoke"
    $record.failure_category = "local_run_package_generation_failed"
  } finally {
    if ($null -ne $startedProcess) {
      try {
        if (Get-Process -Id $startedProcess.Id -ErrorAction SilentlyContinue) {
          Stop-Process -Id $startedProcess.Id -Force
          Start-Sleep -Seconds 3
        }
        $record.local_comfy.stopped_by_helper = $true
      } catch {
        $record.errors += "Stop local ComfyUI failed: $($_.Exception.Message)"
      }
    }
    try {
      Invoke-WebRequest -Uri "$apiBaseUrl/object_info" -TimeoutSec 2 | Out-Null
      $record.local_comfy.port_closed_after_stop = $false
    } catch {
      $record.local_comfy.port_closed_after_stop = $true
    }
  }
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 50
$record | ConvertTo-Json -Depth 50
if ($record.errors.Count -gt 0 -or ($Execute -and $record.result -ne "pass_local_run_package_generation_smoke")) { exit 2 }
