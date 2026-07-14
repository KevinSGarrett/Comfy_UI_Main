<#
.SYNOPSIS
Exercises run-package source binding support in the EC2 deploy-bundle builder.

.DESCRIPTION
Creates a minimal synthetic project and verifies that a hash-bound packaged
source is accepted while hash drift and package-directory escape fail closed.
No external service or runtime is contacted.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$builder = Join-Path $ProjectRoot "tools\New-EC2DeployBundle.ps1"
if (!(Test-Path -LiteralPath $builder -PathType Leaf)) { throw "Deploy bundle builder missing: $builder" }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-JsonFile {
  param([string]$Path, [object]$Value)
  [System.IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 30), $utf8NoBom)
}

function Invoke-BuildCase {
  param(
    [string]$Name,
    [int]$ExpectedExitCode,
    [string]$ExpectedMessage = ""
  )

  $outDir = Join-Path $fixture "runtime_artifacts\bundles\$Name"
  $arguments = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $builder,
    "-ProjectRoot", $fixture,
    "-WorkflowGroup", "video_generation",
    "-LaneId", "source_binding_test_lane",
    "-RunPackageManifestFile", $manifestPath,
    "-OutDir", $outDir,
    "-BundleName", $Name
  )
  $priorErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = (& powershell @arguments 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $priorErrorActionPreference
  }
  $messagePass = ([string]::IsNullOrWhiteSpace($ExpectedMessage) -or $output -match [regex]::Escape($ExpectedMessage))
  $manifest = $null
  $deployManifestPath = Join-Path $outDir "DEPLOY_BUNDLE_MANIFEST.json"
  if (Test-Path -LiteralPath $deployManifestPath -PathType Leaf) {
    $manifest = Get-Content -LiteralPath $deployManifestPath -Raw | ConvertFrom-Json
  }
  $sourceAsset = if ($null -ne $manifest) { @($manifest.required_input_assets | Where-Object { $_.filename -eq "bound-source.jpg" } | Select-Object -First 1) } else { @() }
  $assetPass = if ($ExpectedExitCode -eq 0) {
    @($sourceAsset).Count -eq 1 -and
    ([string]$sourceAsset[0].source_kind) -eq "run_package_source_binding" -and
    ([string]$sourceAsset[0].sha256) -eq $script:sourceHash -and
    ([int64]$sourceAsset[0].size_bytes) -eq $script:sourceBytes
  } else {
    $true
  }
  $passed = ($exitCode -eq $ExpectedExitCode -and $messagePass -and $assetPass)
  return [ordered]@{
    name = $Name
    result = $(if ($passed) { "pass" } else { "fail" })
    exit_code = $exitCode
    expected_exit_code = $ExpectedExitCode
    expected_message = $ExpectedMessage
    message_matched = $messagePass
    source_asset_valid = $assetPass
    source_asset_count = @($sourceAsset).Count
    source_asset_kind = $(if (@($sourceAsset).Count -eq 1) { [string]$sourceAsset[0].source_kind } else { $null })
    source_asset_sha256 = $(if (@($sourceAsset).Count -eq 1) { [string]$sourceAsset[0].sha256 } else { $null })
    source_asset_size_bytes = $(if (@($sourceAsset).Count -eq 1) { [int64]$sourceAsset[0].size_bytes } else { $null })
    output = $output
  }
}

$fixture = Join-Path ([System.IO.Path]::GetTempPath()) ("ec2_source_binding_{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 10)))
[System.IO.Directory]::CreateDirectory($fixture) | Out-Null
try {
  [System.IO.File]::WriteAllText((Join-Path $fixture "README.md"), "fixture", $utf8NoBom)
  Write-JsonFile -Path (Join-Path $fixture "PROJECT_ROOT_MANIFEST.json") -Value ([ordered]@{ schema_version = "1.0" })
  Write-JsonFile -Path (Join-Path $fixture "Workflows\video_generation\ACTIVE_LANES.json") -Value ([ordered]@{
    lanes = @([ordered]@{ lane_id = "source_binding_test_lane"; order = 1 })
  })
  Write-JsonFile -Path (Join-Path $fixture "Plan\07_IMPLEMENTATION\workflow_templates\video_generation\runtime_lane_queue.json") -Value ([ordered]@{ schema_version = "1.0" })
  Write-JsonFile -Path (Join-Path $fixture "Plan\07_IMPLEMENTATION\workflow_templates\video_generation\source_binding_test_lane\workflow.api.json") -Value ([ordered]@{ fixture = $true })

  $prompt = [ordered]@{
    "1" = [ordered]@{ class_type = "LoadImage"; inputs = [ordered]@{ image = "bound-source.jpg" } }
  }
  Write-JsonFile -Path (Join-Path $fixture "Workflows\video_generation\source_binding_test_lane\workflow.api.json") -Value $prompt
  Write-JsonFile -Path (Join-Path $fixture "Workflows\video_generation\source_binding_test_lane\runtime_requirements.json") -Value ([ordered]@{
    required_input_assets = @()
  })

  $packageDir = Join-Path $fixture "runtime_artifacts\run_packages\source_binding_package"
  $sourcePath = Join-Path $packageDir "inputs\bound-source.jpg"
  [System.IO.Directory]::CreateDirectory((Split-Path -Parent $sourcePath)) | Out-Null
  [System.IO.File]::WriteAllBytes($sourcePath, [byte[]](1..64))
  $script:sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
  $script:sourceBytes = (Get-Item -LiteralPath $sourcePath).Length

  $promptRequestPath = Join-Path $packageDir "prompt_request.json"
  Write-JsonFile -Path $promptRequestPath -Value ([ordered]@{ prompt = $prompt })
  $promptHash = (Get-FileHash -LiteralPath $promptRequestPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $manifestPath = Join-Path $packageDir "RUN_PACKAGE_MANIFEST.json"
  $manifest = [ordered]@{
    result = "pass_local_only"
    lane_id = "source_binding_test_lane"
    prompt_request = [ordered]@{ sha256 = $promptHash }
    prompt_profile = [ordered]@{
      applied = $true
      path = $null
      source_binding = [ordered]@{
        supplied = $true
        valid = $true
        packaged = "runtime_artifacts/run_packages/source_binding_package/inputs/bound-source.jpg"
        staged_filename = "bound-source.jpg"
        size_bytes = $script:sourceBytes
        sha256 = $script:sourceHash
      }
    }
  }
  Write-JsonFile -Path $manifestPath -Value $manifest

  $tests = @()
  $tests += Invoke-BuildCase -Name "valid_source_binding" -ExpectedExitCode 0

  [System.IO.File]::AppendAllText($sourcePath, "drift", $utf8NoBom)
  $tests += Invoke-BuildCase -Name "hash_drift_rejected" -ExpectedExitCode 1 -ExpectedMessage "Run-package source binding size mismatch"
  [System.IO.File]::WriteAllBytes($sourcePath, [byte[]](1..64))

  $outsidePath = Join-Path $fixture "runtime_artifacts\outside-source.jpg"
  [System.IO.Directory]::CreateDirectory((Split-Path -Parent $outsidePath)) | Out-Null
  [System.IO.File]::WriteAllBytes($outsidePath, [byte[]](1..64))
  $manifest.prompt_profile.source_binding.packaged = "runtime_artifacts/outside-source.jpg"
  Write-JsonFile -Path $manifestPath -Value $manifest
  $tests += Invoke-BuildCase -Name "package_escape_rejected" -ExpectedExitCode 1 -ExpectedMessage "must remain inside its run package"

  $failed = @($tests | Where-Object { $_.result -ne "pass" })
  $record = [ordered]@{
    schema_version = "1.0"
    artifact_type = "ec2_deploy_bundle_source_binding_regression"
    created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
    test_count = $tests.Count
    passing_test_count = @($tests | Where-Object { $_.result -eq "pass" }).Count
    failed_test_count = $failed.Count
    tests = $tests
    local_only = $true
    aws_contacted = $false
    comfyui_contacted = $false
    ec2_started = $false
    generation_executed = $false
  }

  if (![string]::IsNullOrWhiteSpace($OutFile)) {
    $resolvedOut = if ([System.IO.Path]::IsPathRooted($OutFile)) { $OutFile } else { Join-Path $ProjectRoot $OutFile }
    Write-JsonFile -Path $resolvedOut -Value $record
  }
  $record | ConvertTo-Json -Depth 20
  if ($failed.Count -gt 0) { exit 1 }
  exit 0
} finally {
  $tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd("\") + "\"
  $fixtureFull = [System.IO.Path]::GetFullPath($fixture)
  if ($fixtureFull.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
    Remove-Item -LiteralPath $fixtureFull -Recurse -Force -ErrorAction SilentlyContinue
  }
}
