<#
.SYNOPSIS
Installs one licensed ComfyUI model from immutable HTTP source metadata.

.DESCRIPTION
Dry-run by default. Reads runtime requirements, validates immutable source and
license metadata, and reports install readiness without contacting the network.
With -Execute, requires explicit license acceptance switch and a valid
acceptance JSON binding before any network activity.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeRequirementsFile = "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/flux1_dev_primary_base/runtime_requirements.json",
  [string]$ModelRole = "checkpoint",
  [string]$DestinationModelRoot = "ComfyUI/models",
  [string]$LicenseAcceptanceFile = "",
  [string]$OutFile = "",
  [switch]$Execute,
  [switch]$LicenseAccepted,
  [string]$SourceUrl = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory = $true)][object]$Value,
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$Depth = 30
  )
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) {
    [IO.Directory]::CreateDirectory($parent) | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine, $encoding)
}

function Resolve-PathFromRoot {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$PathValue
  )
  if ([string]::IsNullOrWhiteSpace($PathValue)) { return $PathValue }
  if ([IO.Path]::IsPathRooted($PathValue)) { return [IO.Path]::GetFullPath($PathValue) }
  return [IO.Path]::GetFullPath((Join-Path $Root $PathValue))
}

function Add-Error {
  param([Collections.ArrayList]$Errors, [string]$Message)
  if (-not [string]::IsNullOrWhiteSpace($Message)) { [void]$Errors.Add($Message) }
}

function Get-FreeBytesForPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  $full = [IO.Path]::GetFullPath($Path)
  $drives = @(Get-PSDrive -PSProvider FileSystem | Sort-Object { $_.Root.Length } -Descending)
  foreach ($drive in $drives) {
    $root = [string]$drive.Root
    if ([string]::IsNullOrWhiteSpace($root)) { continue }
    if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
      return [int64]$drive.Free
    }
  }
  return $null
}

function Test-LicenseAcceptanceRecord {
  param(
    [string]$Path,
    [string]$ExpectedLicenseId,
    [string]$ExpectedRepository,
    [string]$ExpectedRevision,
    [string]$ExpectedFileName
  )
  $result = [ordered]@{
    path = $Path
    present = $false
    parse_ok = $false
    valid = $false
    accepted = $false
    binding = [ordered]@{
      license_id_match = $false
      repository_match = $false
      revision_match = $false
      filename_match = $false
      use_scope_noncommercial = $false
      accepted_by_present = $false
      accepted_at_present = $false
      accepted_at_valid = $false
    }
    errors = @()
  }

  if ([string]::IsNullOrWhiteSpace($Path)) {
    $result.errors += "LicenseAcceptanceFile is required for Execute."
    return $result
  }
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    $result.errors += "License acceptance file not found: $Path"
    return $result
  }
  $result.present = $true

  try {
    $doc = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $result.parse_ok = $true
    $result.accepted = [bool]$doc.accepted
    $result.binding.license_id_match = ([string]$doc.license_id -eq [string]$ExpectedLicenseId)
    $result.binding.repository_match = ([string]$doc.repository -eq [string]$ExpectedRepository)
    $result.binding.revision_match = ([string]$doc.revision -eq [string]$ExpectedRevision)
    $result.binding.filename_match = ([string]$doc.filename -eq [string]$ExpectedFileName)
    $result.binding.use_scope_noncommercial = ([string]$doc.use_scope).ToLowerInvariant() -eq "noncommercial"
    $result.binding.accepted_by_present = -not [string]::IsNullOrWhiteSpace([string]$doc.accepted_by)
    $result.binding.accepted_at_present = -not [string]::IsNullOrWhiteSpace([string]$doc.accepted_at)
    $acceptedAt = [DateTimeOffset]::MinValue
    $result.binding.accepted_at_valid = $result.binding.accepted_at_present -and [DateTimeOffset]::TryParse(
      [string]$doc.accepted_at,
      [Globalization.CultureInfo]::InvariantCulture,
      [Globalization.DateTimeStyles]::RoundtripKind,
      [ref]$acceptedAt
    )

    $allBinding = $result.accepted -and
      $result.binding.license_id_match -and
      $result.binding.repository_match -and
      $result.binding.revision_match -and
      $result.binding.filename_match -and
      $result.binding.use_scope_noncommercial -and
      $result.binding.accepted_by_present -and
      $result.binding.accepted_at_valid

    $result.valid = [bool]$allBinding
    if (-not $result.valid) {
      $result.errors += "License acceptance record exists but required fields do not fully bind."
    }
  } catch {
    $result.errors += "Failed to parse license acceptance JSON: $($_.Exception.Message)"
  }

  return $result
}

$exitCode = 2
$errors = New-Object Collections.ArrayList
$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = $timestamp
  operation = "install_licensed_model_from_http"
  installer_script_path = $PSCommandPath
  installer_script_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
  execute = [bool]$Execute
  project_root = $ProjectRoot
  runtime_requirements_file = $RuntimeRequirementsFile
  runtime_requirements_sha256 = $null
  model_role = $ModelRole
  destination_model_root = $DestinationModelRoot
  license_acceptance_file = $LicenseAcceptanceFile
  source_url_override = $SourceUrl
  network_contacted = $false
  download_attempted = $false
  partial_preserved = $false
  aws_contacted = $false
  ec2_contacted = $false
  s3_contacted = $false
  github_contacted = $false
  comfyui_contacted = $false
  expected = [ordered]@{
    filename = $null
    model_subdir = $null
    sha256 = $null
    bytes = $null
    license_id = $null
    repository = $null
    revision = $null
    source_url = $null
  }
  observed = [ordered]@{
    destination_path = $null
    destination_exists = $false
    destination_size_bytes = $null
    destination_sha256 = $null
    partial_path = $null
    partial_exists = $false
    partial_size_bytes = $null
    free_disk_bytes = $null
    enough_free_disk = $null
    curl_exit_code = $null
  }
  license_acceptance = [ordered]@{
    switch_present = [bool]$LicenseAccepted
    file_sha256 = $null
    record = $null
  }
  result = "blocked_preconditions_not_met"
  classification = "BLOCKED_PRECONDITIONS_NOT_MET"
  next_action = "Fix blocker(s) and rerun."
  errors = @()
}

try {
  if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    Add-Error $errors "Project root not found: $ProjectRoot"
    throw "Project root missing."
  }
  $projectRootFull = [IO.Path]::GetFullPath($ProjectRoot)

  $runtimePath = Resolve-PathFromRoot -Root $projectRootFull -PathValue $RuntimeRequirementsFile
  $destinationRootFull = Resolve-PathFromRoot -Root $projectRootFull -PathValue $DestinationModelRoot
  $licensePath = if ([string]::IsNullOrWhiteSpace($LicenseAcceptanceFile)) { "" } else { Resolve-PathFromRoot -Root $projectRootFull -PathValue $LicenseAcceptanceFile }
  $record.project_root = $projectRootFull
  $record.runtime_requirements_file = $runtimePath
  $record.runtime_requirements_sha256 = (Get-FileHash -LiteralPath $runtimePath -Algorithm SHA256).Hash.ToLowerInvariant()
  $record.destination_model_root = $destinationRootFull
  $record.license_acceptance_file = $licensePath

  if (-not (Test-Path -LiteralPath $runtimePath -PathType Leaf)) {
    Add-Error $errors "Runtime requirements file not found: $runtimePath"
    throw "Runtime requirements missing."
  }
  $runtime = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
  $licensed = $runtime.licensed_source
  $requiredModels = @($runtime.required_models)
  if ($null -eq $licensed) {
    Add-Error $errors "runtime_requirements.licensed_source is required."
  }
  if ($requiredModels.Count -eq 0) {
    Add-Error $errors "runtime_requirements.required_models must contain at least one row."
  }
  if ($errors.Count -gt 0) { throw "Runtime metadata missing." }

  $matching = @($requiredModels | Where-Object { [string]$_.role -eq [string]$ModelRole })
  if ($matching.Count -ne 1) {
    Add-Error $errors "Expected exactly one required_models entry with role '$ModelRole'; found $($matching.Count)."
    throw "Model role selection invalid."
  }
  $model = $matching[0]

  $fileName = [string]$model.filename
  $subdir = [string]$model.comfyui_model_subdir
  $sha = ([string]$model.sha256).ToLowerInvariant()
  $bytes = [int64]$model.bytes
  $licenseId = [string]$licensed.license_id
  $repository = [string]$licensed.repository
  $revision = [string]$licensed.revision
  $immutableFileUrl = [string]$licensed.immutable_file_url
  $downloadUrl = [string]$licensed.download_url
  $apiUrl = [string]$licensed.api_url

  $record.expected.filename = $fileName
  $record.expected.model_subdir = $subdir
  $record.expected.sha256 = $sha
  $record.expected.bytes = $bytes
  $record.expected.license_id = $licenseId
  $record.expected.repository = $repository
  $record.expected.revision = $revision

  if ([string]::IsNullOrWhiteSpace($fileName)) { Add-Error $errors "required_models filename must be nonempty." }
  if ([string]::IsNullOrWhiteSpace($subdir)) { Add-Error $errors "required_models comfyui_model_subdir must be nonempty." }
  if (-not [string]::IsNullOrWhiteSpace($fileName) -and [IO.Path]::GetFileName($fileName) -ne $fileName) {
    Add-Error $errors "required_models filename must be a leaf filename without path segments."
  }
  if (-not [string]::IsNullOrWhiteSpace($subdir) -and ([IO.Path]::IsPathRooted($subdir) -or $subdir -match '(^|[\\/])\.\.([\\/]|$)')) {
    Add-Error $errors "required_models comfyui_model_subdir must be a contained relative path without traversal."
  }
  if ($sha -notmatch "^[0-9a-f]{64}$") { Add-Error $errors "required_models sha256 must be a 64-character lowercase/uppercase hex digest." }
  if ($bytes -le 0) { Add-Error $errors "required_models bytes must be a positive integer." }
  if ([string]::IsNullOrWhiteSpace($licenseId)) { Add-Error $errors "licensed_source license_id is required." }
  if ([string]::IsNullOrWhiteSpace($repository)) { Add-Error $errors "licensed_source repository is required." }
  if ([string]::IsNullOrWhiteSpace($revision)) { Add-Error $errors "licensed_source revision is required for immutable source binding." }
  if ([string]::IsNullOrWhiteSpace($immutableFileUrl) -and [string]::IsNullOrWhiteSpace($apiUrl)) {
    Add-Error $errors "licensed_source immutable_file_url or api_url is required."
  }
  if (-not [string]::IsNullOrWhiteSpace($immutableFileUrl) -and $immutableFileUrl -notlike "*$revision*") {
    Add-Error $errors "licensed_source immutable_file_url must bind the same revision."
  }
  if (-not [string]::IsNullOrWhiteSpace($immutableFileUrl) -and ($immutableFileUrl -notlike "*$repository*" -or $immutableFileUrl -notlike "*$fileName*")) {
    Add-Error $errors "licensed_source immutable_file_url must bind the same repository and filename."
  }
  if (-not [string]::IsNullOrWhiteSpace($apiUrl) -and $apiUrl -notlike "*$revision*") {
    Add-Error $errors "licensed_source api_url must bind the same revision."
  }
  if (-not [string]::IsNullOrWhiteSpace($downloadUrl) -and ($downloadUrl -notlike "*$repository*" -or $downloadUrl -notlike "*$revision*" -or $downloadUrl -notlike "*$fileName*")) {
    Add-Error $errors "licensed_source download_url must bind the same repository, revision, and filename."
  }

  $resolvedUrl = ""
  if (-not [string]::IsNullOrWhiteSpace($SourceUrl)) {
    if ($SourceUrl -notlike "*$revision*") {
      Add-Error $errors "SourceUrl override must contain the immutable revision token."
    }
    $resolvedUrl = $SourceUrl
  } else {
    if (-not [string]::IsNullOrWhiteSpace($downloadUrl)) {
      $resolvedUrl = $downloadUrl
    } elseif (-not [string]::IsNullOrWhiteSpace($repository) -and -not [string]::IsNullOrWhiteSpace($revision) -and -not [string]::IsNullOrWhiteSpace($fileName)) {
      $resolvedUrl = "https://huggingface.co/$repository/resolve/$revision/${fileName}?download=true"
    }
  }
  if ([string]::IsNullOrWhiteSpace($resolvedUrl)) {
    Add-Error $errors "Failed to resolve immutable download URL."
  } else {
    $resolvedUri = $null
    if (-not [Uri]::TryCreate($resolvedUrl, [UriKind]::Absolute, [ref]$resolvedUri)) {
      Add-Error $errors "Resolved source URL must be an absolute URI."
    } elseif ($resolvedUri.Scheme -ne "https" -and -not ($resolvedUri.Scheme -eq "http" -and $resolvedUri.IsLoopback)) {
      Add-Error $errors "Resolved source URL must use HTTPS; HTTP is allowed only for loopback regression fixtures."
    } elseif (-not $resolvedUri.IsLoopback -and -not [string]::IsNullOrWhiteSpace($resolvedUri.Query) -and $resolvedUri.Query -ne "?download=true") {
      Add-Error $errors "External source URL query parameters are restricted to ?download=true to prevent credential-bearing URLs in evidence."
    }
  }
  $record.expected.source_url = $resolvedUrl

  if ($errors.Count -gt 0) { throw "Validation failed." }

  $destDir = Join-Path $destinationRootFull $subdir
  $destPath = Join-Path $destDir $fileName
  $destinationPrefix = [IO.Path]::GetFullPath($destinationRootFull).TrimEnd("\", "/") + [IO.Path]::DirectorySeparatorChar
  if (-not [IO.Path]::GetFullPath($destPath).StartsWith($destinationPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    Add-Error $errors "Resolved destination escapes DestinationModelRoot."
    throw "Destination containment failed."
  }
  $partialPath = "$destPath.partial"
  $record.observed.destination_path = $destPath
  $record.observed.partial_path = $partialPath

  if (Test-Path -LiteralPath $destPath -PathType Leaf) {
    $record.observed.destination_exists = $true
    $item = Get-Item -LiteralPath $destPath
    $record.observed.destination_size_bytes = [int64]$item.Length
    $record.observed.destination_sha256 = (Get-FileHash -LiteralPath $destPath -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  if (Test-Path -LiteralPath $partialPath -PathType Leaf) {
    $record.observed.partial_exists = $true
    $record.observed.partial_size_bytes = [int64](Get-Item -LiteralPath $partialPath).Length
  }
  $freeBytes = Get-FreeBytesForPath -Path $destDir
  $record.observed.free_disk_bytes = $freeBytes
  if ($null -ne $freeBytes) {
    $record.observed.enough_free_disk = ([int64]$freeBytes -ge [int64]$bytes)
  }

  $licenseRecord = Test-LicenseAcceptanceRecord -Path $licensePath -ExpectedLicenseId $licenseId -ExpectedRepository $repository -ExpectedRevision $revision -ExpectedFileName $fileName
  if (-not [string]::IsNullOrWhiteSpace($licensePath) -and (Test-Path -LiteralPath $licensePath -PathType Leaf)) {
    $record.license_acceptance.file_sha256 = (Get-FileHash -LiteralPath $licensePath -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  $record.license_acceptance.record = $licenseRecord
  $curlContract = @(
    "--continue-at", "-",
    "--location",
    "--fail",
    "--retry", "3",
    "--output", $partialPath,
    $resolvedUrl
  )
  $record.curl_contract = @($curlContract)

  $destinationVerified = $record.observed.destination_exists -and
    ([int64]$record.observed.destination_size_bytes -eq [int64]$bytes) -and
    ([string]$record.observed.destination_sha256 -eq [string]$sha)
  $destinationMismatch = $record.observed.destination_exists -and -not $destinationVerified

  if ($destinationMismatch) {
    Add-Error $errors "Destination file exists but size/hash mismatch. Refusing overwrite."
    $record.result = "destination_mismatch_blocked"
    $record.classification = "DESTINATION_MISMATCH_BLOCKED"
    $record.next_action = "Manually remediate destination mismatch, then rerun."
    throw "Destination mismatch."
  }

  if (-not $Execute) {
    if ($destinationVerified) {
      $record.result = "already_installed_verified"
      $record.classification = "ALREADY_INSTALLED_VERIFIED"
      $record.next_action = "No action required."
      $exitCode = 0
    } else {
      $record.result = "ready_dry_run"
      $record.classification = "DRY_RUN_READY_NO_NETWORK"
      if (-not $LicenseAccepted -or -not $licenseRecord.valid) {
        $record.next_action = "Provide -LicenseAccepted and a valid LicenseAcceptanceFile, then rerun with -Execute."
      } else {
        $record.next_action = "Run again with -Execute to download, verify, and install."
      }
      if ($record.observed.enough_free_disk -eq $false) {
        Add-Error $errors "Free disk appears lower than expected bytes."
        $record.result = "dry_run_blocked_insufficient_disk"
        $record.classification = "DRY_RUN_BLOCKED_INSUFFICIENT_DISK"
        $record.next_action = "Free disk space or choose another DestinationModelRoot."
        throw "Insufficient free disk."
      }
      $exitCode = 0
    }
  } else {
    if (-not $LicenseAccepted) {
      Add-Error $errors "Execute requires -LicenseAccepted switch."
      $record.result = "blocked_license_switch_required"
      $record.classification = "LICENSE_ACCEPTANCE_REQUIRED_PRE_NETWORK"
      $record.next_action = "Rerun with -LicenseAccepted and a valid acceptance JSON."
      throw "License switch missing."
    }
    if (-not $licenseRecord.valid) {
      foreach ($msg in @($licenseRecord.errors)) { Add-Error $errors $msg }
      $record.result = "blocked_invalid_license_acceptance_record"
      $record.classification = "LICENSE_ACCEPTANCE_REQUIRED_PRE_NETWORK"
      $record.next_action = "Fix LicenseAcceptanceFile binding fields and rerun."
      throw "Invalid license acceptance record."
    }
    if ($destinationVerified) {
      $record.result = "already_installed_verified"
      $record.classification = "ALREADY_INSTALLED_VERIFIED"
      $record.next_action = "No action required."
      $exitCode = 0
    } else {
      if ($record.observed.enough_free_disk -eq $false) {
        Add-Error $errors "Free disk appears lower than expected bytes."
        $record.result = "blocked_insufficient_disk_pre_network"
        $record.classification = "INSUFFICIENT_DISK_PRE_NETWORK"
        $record.next_action = "Free disk space or choose another DestinationModelRoot."
        throw "Insufficient free disk."
      }
      [IO.Directory]::CreateDirectory($destDir) | Out-Null

      $curlCommand = Get-Command curl.exe -ErrorAction SilentlyContinue
      if ($null -eq $curlCommand) {
        Add-Error $errors "curl.exe not found on PATH."
        $record.result = "blocked_missing_curl_exe"
        $record.classification = "TOOLING_BLOCKER"
        $record.next_action = "Install or expose curl.exe, then rerun."
        throw "curl.exe missing."
      }

      $record.download_attempted = $true
      $record.network_contacted = $true
      & curl.exe @curlContract
      $record.observed.curl_exit_code = [int]$LASTEXITCODE
      if ($LASTEXITCODE -ne 0) {
        $record.partial_preserved = Test-Path -LiteralPath $partialPath -PathType Leaf
        Add-Error $errors "curl.exe download failed with exit code $LASTEXITCODE."
        $record.result = "download_failed_partial_preserved"
        $record.classification = "DOWNLOAD_FAILED"
        $record.next_action = "Inspect connectivity/source URL and rerun Execute; partial remains for resume."
        throw "Download failed."
      }

      if (-not (Test-Path -LiteralPath $partialPath -PathType Leaf)) {
        Add-Error $errors "curl.exe completed without producing partial file."
        $record.result = "download_missing_partial_output"
        $record.classification = "DOWNLOAD_FAILED"
        $record.next_action = "Rerun Execute after investigating curl output path permissions."
        throw "Partial missing."
      }

      $partialItem = Get-Item -LiteralPath $partialPath
      $partialSize = [int64]$partialItem.Length
      $partialSha = (Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash.ToLowerInvariant()
      $record.observed.partial_exists = $true
      $record.observed.partial_size_bytes = $partialSize
      $record.partial_preserved = $true
      $record.observed.destination_sha256 = $partialSha
      $record.observed.destination_size_bytes = $partialSize

      if ($partialSize -ne [int64]$bytes) {
        Add-Error $errors "Downloaded byte count mismatch. Expected $bytes observed $partialSize."
        $record.result = "download_size_mismatch_partial_preserved"
        $record.classification = "DOWNLOAD_VERIFY_FAILED"
        $record.next_action = "Rerun Execute; partial remains for resume."
        throw "Size mismatch."
      }
      if ($partialSha -ne $sha) {
        Add-Error $errors "Downloaded SHA256 mismatch. Expected $sha observed $partialSha."
        $record.result = "download_hash_mismatch_partial_preserved"
        $record.classification = "DOWNLOAD_VERIFY_FAILED"
        $record.next_action = "Rerun Execute after verifying source integrity; partial remains."
        throw "SHA mismatch."
      }

      Move-Item -LiteralPath $partialPath -Destination $destPath
      $record.partial_preserved = $false
      $record.observed.destination_exists = $true
      $record.observed.destination_size_bytes = [int64](Get-Item -LiteralPath $destPath).Length
      $record.observed.destination_sha256 = (Get-FileHash -LiteralPath $destPath -Algorithm SHA256).Hash.ToLowerInvariant()

      $record.result = "installed_verified"
      $record.classification = "INSTALL_SUCCESS_VERIFIED"
      $record.next_action = "No action required."
      $exitCode = 0
    }
  }
} catch {
  if ($record.result -in @("installed_verified", "already_installed_verified", "ready_dry_run")) {
    Add-Error $errors $_.Exception.Message
    $record.result = "blocked_unexpected_exception"
    $record.classification = "UNEXPECTED_EXCEPTION"
    $record.next_action = "Inspect errors and rerun."
    $exitCode = 2
  }
} finally {
  $record.errors = @($errors)
  if (-not [string]::IsNullOrWhiteSpace($OutFile)) {
    $outPath = Resolve-PathFromRoot -Root $record.project_root -PathValue $OutFile
    Write-JsonNoBom -Value $record -Path $outPath -Depth 30
  }
  $record | ConvertTo-Json -Depth 30
}

if ($exitCode -eq 0) {
  exit 0
}
exit 2
