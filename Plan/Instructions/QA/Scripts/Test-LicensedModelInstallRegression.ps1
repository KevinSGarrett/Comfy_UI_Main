<#
.SYNOPSIS
Runs disposable local-only regression checks for licensed model HTTP installer.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param([object]$Value, [string]$Path, [int]$Depth = 24)
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) { [IO.Directory]::CreateDirectory($parent) | Out-Null }
  [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine, (New-Object Text.UTF8Encoding($false)))
}

function Add-Check {
  param([Collections.ArrayList]$Checks, [string]$Name, [bool]$Passed, [object]$Observed = $null)
  [void]$Checks.Add([ordered]@{
    name = $Name
    passed = $Passed
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
  })
}

function Get-FreeTcpPort {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  try {
    $listener.Start()
    return ([int]($listener.LocalEndpoint.Port))
  } finally {
    $listener.Stop()
  }
}

function Invoke-InstallerCase {
  param(
    [string]$Name,
    [string]$PsExe,
    [string]$InstallerPath,
    [string]$FixtureRoot,
    [string]$RuntimeFile,
    [string]$DestinationRoot,
    [string]$CaseOutDir,
    [string]$LicenseAcceptanceFile,
    [string]$SourceUrl,
    [switch]$Execute,
    [switch]$LicenseAccepted
  )

  $outPath = Join-Path $CaseOutDir "$Name.json"
  $args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $InstallerPath,
    "-ProjectRoot", $FixtureRoot,
    "-RuntimeRequirementsFile", $RuntimeFile,
    "-DestinationModelRoot", $DestinationRoot,
    "-ModelRole", "checkpoint",
    "-OutFile", $outPath,
    "-SourceUrl", $SourceUrl
  )
  if (-not [string]::IsNullOrWhiteSpace($LicenseAcceptanceFile)) {
    $args += @("-LicenseAcceptanceFile", $LicenseAcceptanceFile)
  }
  if ($Execute) { $args += "-Execute" }
  if ($LicenseAccepted) { $args += "-LicenseAccepted" }

  & $PsExe @args | Out-Null
  $exitCode = $LASTEXITCODE
  $payload = Get-Content -LiteralPath $outPath -Raw | ConvertFrom-Json
  return [ordered]@{
    case = $Name
    out_file = $outPath
    exit_code = $exitCode
    payload = $payload
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "Project root not found: $ProjectRoot" }
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$installerPath = Join-Path $ProjectRoot "Plan/Instructions/Operations/Scripts/Install-LicensedModelFromHttp.ps1"
if (-not (Test-Path -LiteralPath $installerPath -PathType Leaf)) { throw "Installer script not found: $installerPath" }

$psExe = (Get-Process -Id $PID).Path
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
if ($null -eq $pythonCmd) { throw "python or python3 is required for local http.server regression." }

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LICENSED_MODEL_INSTALL_REGRESSION_$stamp.json"
} elseif (-not [IO.Path]::IsPathRooted($OutFile)) {
  $OutFile = Join-Path $ProjectRoot $OutFile
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("licensed_model_install_regression_" + [Guid]::NewGuid().ToString("N"))
$fixtureRoot = Join-Path $tempRoot "fixture"
$sourceRoot = Join-Path $tempRoot "source"
$caseOutDir = Join-Path $tempRoot "cases"
$runtimeFile = Join-Path $fixtureRoot "runtime_requirements.json"
$acceptanceValid = Join-Path $fixtureRoot "license_acceptance_valid.json"
$acceptanceInvalid = Join-Path $fixtureRoot "license_acceptance_invalid.json"
$acceptanceInvalidTimestamp = Join-Path $fixtureRoot "license_acceptance_invalid_timestamp.json"
$runtimeTraversal = Join-Path $fixtureRoot "runtime_requirements_traversal.json"
$destRoot = Join-Path $fixtureRoot "ComfyUI/models"
$serverOut = Join-Path $tempRoot "http_stdout.log"
$serverErr = Join-Path $tempRoot "http_stderr.log"
$checks = New-Object Collections.ArrayList
$caseOutputs = @{}
$serverProcess = $null

$revision = "fixture-revision-001"
$repository = "fixtures/local-license-model"
$licenseId = "fixture-noncommercial-license"
$modelFile = "fixture-model.safetensors"
$modelSubdir = "checkpoints"

try {
  [IO.Directory]::CreateDirectory($fixtureRoot) | Out-Null
  [IO.Directory]::CreateDirectory($sourceRoot) | Out-Null
  [IO.Directory]::CreateDirectory($caseOutDir) | Out-Null

  $fixtureBytes = [Text.Encoding]::ASCII.GetBytes("fixture licensed model bytes for local regression")
  $fixtureModelPath = Join-Path $sourceRoot $modelFile
  [IO.File]::WriteAllBytes($fixtureModelPath, $fixtureBytes)
  $expectedSize = [int64](Get-Item -LiteralPath $fixtureModelPath).Length
  $expectedSha = (Get-FileHash -LiteralPath $fixtureModelPath -Algorithm SHA256).Hash.ToLowerInvariant()

  $runtimeDoc = [ordered]@{
    lane_id = "fixture_lane"
    required_models = @(
      [ordered]@{
        role = "checkpoint"
        comfyui_model_subdir = $modelSubdir
        filename = $modelFile
        sha256 = $expectedSha
        bytes = $expectedSize
      }
    )
    licensed_source = [ordered]@{
      provider = "fixture"
      repository = $repository
      revision = $revision
      immutable_file_url = "https://example.invalid/$repository/blob/$revision/$modelFile"
      api_url = "https://example.invalid/api/models/$repository/revision/${revision}?blobs=true"
      license_id = $licenseId
    }
  }
  [IO.File]::WriteAllText($runtimeFile, ($runtimeDoc | ConvertTo-Json -Depth 20), (New-Object Text.UTF8Encoding($false)))

  $validAcceptance = [ordered]@{
    accepted = $true
    license_id = $licenseId
    repository = $repository
    revision = $revision
    filename = $modelFile
    use_scope = "noncommercial"
    accepted_by = "local-regression"
    accepted_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  }
  [IO.File]::WriteAllText($acceptanceValid, ($validAcceptance | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding($false)))

  $invalidAcceptance = [ordered]@{
    accepted = $true
    license_id = "wrong-license"
    repository = $repository
    revision = $revision
    filename = $modelFile
    use_scope = "commercial"
    accepted_by = ""
    accepted_at = ""
  }
  [IO.File]::WriteAllText($acceptanceInvalid, ($invalidAcceptance | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding($false)))

  $invalidTimestampAcceptance = [ordered]@{}
  foreach ($property in $validAcceptance.GetEnumerator()) { $invalidTimestampAcceptance[$property.Key] = $property.Value }
  $invalidTimestampAcceptance.accepted_at = "not-a-timestamp"
  [IO.File]::WriteAllText($acceptanceInvalidTimestamp, ($invalidTimestampAcceptance | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding($false)))

  $traversalDoc = [ordered]@{
    lane_id = "fixture_lane_traversal"
    required_models = @(
      [ordered]@{
        role = "checkpoint"
        comfyui_model_subdir = "../escape"
        filename = $modelFile
        sha256 = $expectedSha
        bytes = $expectedSize
      }
    )
    licensed_source = $runtimeDoc.licensed_source
  }
  [IO.File]::WriteAllText($runtimeTraversal, ($traversalDoc | ConvertTo-Json -Depth 20), (New-Object Text.UTF8Encoding($false)))

  $port = Get-FreeTcpPort
  $sourceUrl = "http://127.0.0.1:$port/${modelFile}?revision=$revision"
  $serverProcess = Start-Process -FilePath $pythonCmd.Source -ArgumentList @("-m", "http.server", "$port", "--bind", "127.0.0.1", "--directory", $sourceRoot) -WindowStyle Hidden -PassThru -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr
  Start-Sleep -Milliseconds 800

  $readServerLog = {
    if (Test-Path -LiteralPath $serverErr -PathType Leaf) {
      return (Get-Content -LiteralPath $serverErr -Raw)
    }
    return ""
  }
  $logBefore = & $readServerLog

  $caseOutputs.dry_run = Invoke-InstallerCase -Name "dry_run" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -LicenseAcceptanceFile $acceptanceValid -SourceUrl $sourceUrl
  $logAfterDryRun = & $readServerLog
  Add-Check $checks "dry_run_exit_zero" ($caseOutputs.dry_run.exit_code -eq 0) $caseOutputs.dry_run.exit_code
  Add-Check $checks "dry_run_no_network_contact" (-not [bool]$caseOutputs.dry_run.payload.network_contacted) $caseOutputs.dry_run.payload.network_contacted
  Add-Check $checks "dry_run_reports_acceptance_required" ([string]$caseOutputs.dry_run.payload.next_action -like "*LicenseAccepted*") $caseOutputs.dry_run.payload.next_action
  Add-Check $checks "dry_run_did_not_hit_http_server" ($logAfterDryRun -eq $logBefore) ([ordered]@{ before = $logBefore.Length; after = $logAfterDryRun.Length })

  $caseOutputs.execute_no_switch = Invoke-InstallerCase -Name "execute_no_switch" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -SourceUrl $sourceUrl -Execute
  Add-Check $checks "execute_without_license_switch_fails_pre_network" ($caseOutputs.execute_no_switch.exit_code -eq 2 -and -not [bool]$caseOutputs.execute_no_switch.payload.network_contacted) ([ordered]@{ exit = $caseOutputs.execute_no_switch.exit_code; result = $caseOutputs.execute_no_switch.payload.result })

  $caseOutputs.execute_invalid_acceptance = Invoke-InstallerCase -Name "execute_invalid_acceptance" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -LicenseAcceptanceFile $acceptanceInvalid -SourceUrl $sourceUrl -Execute -LicenseAccepted
  Add-Check $checks "invalid_acceptance_binding_fails_pre_network" ($caseOutputs.execute_invalid_acceptance.exit_code -eq 2 -and -not [bool]$caseOutputs.execute_invalid_acceptance.payload.network_contacted) ([ordered]@{ exit = $caseOutputs.execute_invalid_acceptance.exit_code; result = $caseOutputs.execute_invalid_acceptance.payload.result })

  $caseOutputs.execute_invalid_timestamp = Invoke-InstallerCase -Name "execute_invalid_timestamp" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -LicenseAcceptanceFile $acceptanceInvalidTimestamp -SourceUrl $sourceUrl -Execute -LicenseAccepted
  Add-Check $checks "invalid_acceptance_timestamp_fails_pre_network" ($caseOutputs.execute_invalid_timestamp.exit_code -eq 2 -and -not [bool]$caseOutputs.execute_invalid_timestamp.payload.network_contacted -and -not [bool]$caseOutputs.execute_invalid_timestamp.payload.license_acceptance.record.binding.accepted_at_valid) ([ordered]@{ exit = $caseOutputs.execute_invalid_timestamp.exit_code; result = $caseOutputs.execute_invalid_timestamp.payload.result })

  $caseOutputs.traversal = Invoke-InstallerCase -Name "traversal" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeTraversal -DestinationRoot $destRoot -CaseOutDir $caseOutDir -SourceUrl $sourceUrl
  Add-Check $checks "model_subdir_traversal_fails_pre_network" ($caseOutputs.traversal.exit_code -eq 2 -and -not [bool]$caseOutputs.traversal.payload.network_contacted) ([ordered]@{ exit = $caseOutputs.traversal.exit_code; errors = @($caseOutputs.traversal.payload.errors) })

  $insecureSourceUrl = "http://example.com/$repository/$revision/$modelFile"
  $caseOutputs.insecure_source = Invoke-InstallerCase -Name "insecure_source" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -SourceUrl $insecureSourceUrl
  Add-Check $checks "non_loopback_http_source_fails_pre_network" ($caseOutputs.insecure_source.exit_code -eq 2 -and -not [bool]$caseOutputs.insecure_source.payload.network_contacted) ([ordered]@{ exit = $caseOutputs.insecure_source.exit_code; errors = @($caseOutputs.insecure_source.payload.errors) })

  $destPath = Join-Path (Join-Path $destRoot $modelSubdir) $modelFile
  [IO.Directory]::CreateDirectory((Split-Path -Parent $destPath)) | Out-Null
  $partialPath = "$destPath.partial"

  $caseOutputs.execute_valid = Invoke-InstallerCase -Name "execute_valid" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -LicenseAcceptanceFile $acceptanceValid -SourceUrl $sourceUrl -Execute -LicenseAccepted
  $installedSha = if (Test-Path -LiteralPath $destPath -PathType Leaf) { (Get-FileHash -LiteralPath $destPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
  $installedSize = if (Test-Path -LiteralPath $destPath -PathType Leaf) { [int64](Get-Item -LiteralPath $destPath).Length } else { -1 }
  Add-Check $checks "valid_acceptance_downloads_and_verifies" ($caseOutputs.execute_valid.exit_code -eq 0 -and [string]$caseOutputs.execute_valid.payload.result -eq "installed_verified" -and $installedSha -eq $expectedSha -and $installedSize -eq $expectedSize) ([ordered]@{ exit = $caseOutputs.execute_valid.exit_code; result = $caseOutputs.execute_valid.payload.result; size = $installedSize; sha256 = $installedSha })
  Add-Check $checks "partial_install_path_verified" ([bool]$caseOutputs.execute_valid.payload.download_attempted -and [bool]$caseOutputs.execute_valid.payload.network_contacted -and -not (Test-Path -LiteralPath $partialPath -PathType Leaf)) $caseOutputs.execute_valid.payload.curl_contract

  $caseOutputs.execute_second = Invoke-InstallerCase -Name "execute_second" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $destRoot -CaseOutDir $caseOutDir -LicenseAcceptanceFile $acceptanceValid -SourceUrl $sourceUrl -Execute -LicenseAccepted
  Add-Check $checks "second_execute_already_installed_verified" ($caseOutputs.execute_second.exit_code -eq 0 -and [string]$caseOutputs.execute_second.payload.result -eq "already_installed_verified") ([ordered]@{ exit = $caseOutputs.execute_second.exit_code; result = $caseOutputs.execute_second.payload.result })

  $mismatchDestRoot = Join-Path $fixtureRoot "mismatch_root/models"
  $mismatchDestPath = Join-Path (Join-Path $mismatchDestRoot $modelSubdir) $modelFile
  [IO.Directory]::CreateDirectory((Split-Path -Parent $mismatchDestPath)) | Out-Null
  [IO.File]::WriteAllBytes($mismatchDestPath, [Text.Encoding]::ASCII.GetBytes("mismatch"))
  $mismatchOriginalSha = (Get-FileHash -LiteralPath $mismatchDestPath -Algorithm SHA256).Hash.ToLowerInvariant()
  $caseOutputs.execute_mismatch = Invoke-InstallerCase -Name "execute_mismatch" -PsExe $psExe -InstallerPath $installerPath -FixtureRoot $fixtureRoot -RuntimeFile $runtimeFile -DestinationRoot $mismatchDestRoot -CaseOutDir $caseOutDir -LicenseAcceptanceFile $acceptanceValid -SourceUrl $sourceUrl -Execute -LicenseAccepted
  $mismatchPostSha = (Get-FileHash -LiteralPath $mismatchDestPath -Algorithm SHA256).Hash.ToLowerInvariant()
  Add-Check $checks "preexisting_mismatch_fails_without_overwrite" ($caseOutputs.execute_mismatch.exit_code -eq 2 -and [string]$caseOutputs.execute_mismatch.payload.result -eq "destination_mismatch_blocked" -and $mismatchOriginalSha -eq $mismatchPostSha -and -not [bool]$caseOutputs.execute_mismatch.payload.network_contacted) ([ordered]@{ exit = $caseOutputs.execute_mismatch.exit_code; result = $caseOutputs.execute_mismatch.payload.result; hash_unchanged = ($mismatchOriginalSha -eq $mismatchPostSha) })

  $curlContract = @($caseOutputs.execute_valid.payload.curl_contract)
  $continueIndex = [Array]::IndexOf($curlContract, "--continue-at")
  Add-Check $checks "curl_continue_at_contract_present" ($continueIndex -ge 0 -and $continueIndex + 1 -lt $curlContract.Count -and $curlContract[$continueIndex + 1] -eq "-") $curlContract

  $failed = @($checks | Where-Object { -not $_.passed })
  $summary = [ordered]@{
    schema_version = "1.0"
    timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    operation = "test_licensed_model_install_regression"
    installer_script = "Plan/Instructions/Operations/Scripts/Install-LicensedModelFromHttp.ps1"
    installer_script_sha256 = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    regression_script = "Plan/Instructions/QA/Scripts/Test-LicensedModelInstallRegression.ps1"
    regression_script_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    local_only = $true
    external_network_contacted = $false
    aws_contacted = $false
    ec2_contacted = $false
    s3_contacted = $false
    github_contacted = $false
    comfyui_contacted = $false
    check_count = $checks.Count
    failed_check_count = $failed.Count
    failed_check_names = @($failed | ForEach-Object { $_.name })
    checks = @($checks)
    case_outputs = $caseOutputs
    result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  }

  Write-JsonNoBom -Value $summary -Path $OutFile -Depth 30
  $summary | ConvertTo-Json -Depth 30
  if ($failed.Count -gt 0) { exit 2 }
  exit 0
} finally {
  if ($null -ne $serverProcess) {
    try {
      if (-not $serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -Force }
    } catch {}
  }
  if (Test-Path -LiteralPath $tempRoot -PathType Container) {
    try { Remove-Item -LiteralPath $tempRoot -Recurse -Force } catch {}
  }
}
