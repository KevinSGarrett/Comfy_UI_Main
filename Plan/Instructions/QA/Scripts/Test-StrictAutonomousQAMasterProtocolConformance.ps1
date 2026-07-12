[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$RequestPath,
  [Parameter(Mandatory = $true)][string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$canonicalRoot = [System.IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath '..\..\..\..'))
$requiredReviewerRole = 'Codex Desktop autonomous QA'
$requiredBlockerPolicy = 'No unresolved blockers may be marked pass; unresolved blockers force blocked; quality/test failures force fail; suppressed failures forbidden.'
$supportedFailureClasses = @(
  'environment_infrastructure',
  'workflow_logic',
  'artifact_quality',
  'observability_evidence',
  'unknown_needs_diagnosis'
)

function New-OperationalError {
  param([string]$Message)
  $ex = [System.InvalidOperationException]::new($Message)
  $ex.Data['Operational'] = $true
  return $ex
}

function Get-PhysicalRoot {
  if (Test-Path -LiteralPath $canonicalRoot -PathType Container) {
    return [System.IO.Path]::GetFullPath($canonicalRoot)
  }
  throw (New-OperationalError "Canonical project root is unavailable at '$canonicalRoot'.")
}

function Add-Failure {
  param(
    [System.Collections.Generic.List[object]]$Failures,
    [string]$Code,
    [string]$Message
  )
  $Failures.Add([ordered]@{
      code = $Code
      message = $Message
    })
}

function Add-Blocker {
  param(
    [System.Collections.Generic.List[object]]$Blockers,
    [string]$Code,
    [string]$Message
  )
  $Blockers.Add([ordered]@{
      code = $Code
      message = $Message
    })
}

function Test-StartsWithPath {
  param(
    [string]$Path,
    [string]$Root
  )
  $normalizedPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
  $normalizedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
  if ($normalizedPath -eq $normalizedRoot) {
    return $true
  }
  return $normalizedPath.StartsWith("$normalizedRoot$([System.IO.Path]::DirectorySeparatorChar)", [System.StringComparison]::OrdinalIgnoreCase)
}

function Convert-ToRepoRelativePath {
  param(
    [string]$InputPath,
    [string]$PhysicalRoot
  )
  $trimmed = $InputPath.Trim()
  if ([string]::IsNullOrWhiteSpace($trimmed)) {
    throw (New-OperationalError 'Received an empty path.')
  }

  if ([System.IO.Path]::IsPathRooted($trimmed)) {
    $candidate = [System.IO.Path]::GetFullPath($trimmed)
    if (Test-StartsWithPath -Path $candidate -Root $PhysicalRoot) {
      return $candidate.Substring([System.IO.Path]::GetFullPath($PhysicalRoot).TrimEnd('\', '/').Length).TrimStart('\', '/')
    }

    if ($trimmed -match '^[A-Za-z]:\\') {
      $canonicalNormalized = $canonicalRoot.TrimEnd('\')
      if ($trimmed.StartsWith($canonicalNormalized, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $trimmed.Substring($canonicalNormalized.Length).TrimStart('\', '/')
      }
    }
    throw (New-OperationalError "Path escape rejected: '$InputPath'.")
  }

  return $trimmed.TrimStart('\', '/')
}

function Resolve-PathUnderCanonicalRoot {
  param(
    [string]$InputPath,
    [string]$PhysicalRoot,
    [switch]$AllowMissingLeaf
  )

  $repoRelative = Convert-ToRepoRelativePath -InputPath $InputPath -PhysicalRoot $PhysicalRoot
  $combined = [System.IO.Path]::GetFullPath((Join-Path -Path $PhysicalRoot -ChildPath $repoRelative))
  if (-not (Test-StartsWithPath -Path $combined -Root $PhysicalRoot)) {
    throw (New-OperationalError "Path escape rejected: '$InputPath'.")
  }

  $canonical = Join-Path -Path $canonicalRoot -ChildPath ($repoRelative -replace '/', '\')
  if ((-not $AllowMissingLeaf) -and -not (Test-Path -LiteralPath $combined)) {
    throw (New-OperationalError "Required path does not exist: '$canonical'.")
  }

  return [ordered]@{
    canonical = $canonical
    physical = $combined
    relative = ($repoRelative -replace '\\', '/')
  }
}

function ConvertTo-HashtableRecursive {
  param([AllowNull()]$InputObject)

  if ($null -eq $InputObject) {
    return $null
  }
  if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
    $result = @{}
    foreach ($property in $InputObject.PSObject.Properties) {
      $result[$property.Name] = ConvertTo-HashtableRecursive -InputObject $property.Value
    }
    return $result
  }
  if ($InputObject -is [System.Collections.IDictionary]) {
    $result = @{}
    foreach ($key in $InputObject.Keys) {
      $result[[string]$key] = ConvertTo-HashtableRecursive -InputObject $InputObject[$key]
    }
    return $result
  }
  if (($InputObject -is [System.Collections.IEnumerable]) -and ($InputObject -isnot [string])) {
    $items = @($InputObject | ForEach-Object { ConvertTo-HashtableRecursive -InputObject $_ })
    return ,$items
  }
  return $InputObject
}

function Read-JsonObject {
  param([string]$Path)
  try {
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    return (ConvertTo-HashtableRecursive -InputObject ($raw | ConvertFrom-Json))
  } catch {
    throw [System.InvalidDataException]::new("JSON parse failed for '$Path': $($_.Exception.Message)")
  }
}

function Validate-ExactKeys {
  param(
    [hashtable]$Object,
    [string[]]$RequiredKeys,
    [string[]]$OptionalKeys,
    [string]$Context,
    [System.Collections.Generic.List[object]]$Failures
  )
  foreach ($key in $RequiredKeys) {
    if (-not $Object.ContainsKey($key)) {
      Add-Failure -Failures $Failures -Code "$($Context).missing_key" -Message "Missing required key '$key' in $Context."
      $Object[$key] = $null
    }
  }
  $allowed = @($RequiredKeys + $OptionalKeys)
  foreach ($key in $Object.Keys) {
    if ($allowed -notcontains $key) {
      Add-Failure -Failures $Failures -Code "$($Context).unknown_key" -Message "Unknown key '$key' in $Context."
    }
  }
}

function Test-IsStringArray {
  param([object]$Value)
  if ($Value -isnot [System.Collections.IEnumerable] -or $Value -is [string]) {
    return $false
  }
  foreach ($entry in $Value) {
    if ($entry -isnot [string]) {
      return $false
    }
  }
  return $true
}

function Test-IsIntegerValue {
  param(
    [object]$Value,
    [long]$Minimum = [long]::MinValue,
    [long]$Maximum = [long]::MaxValue
  )
  if (($Value -isnot [byte]) -and ($Value -isnot [int16]) -and ($Value -isnot [int]) -and
    ($Value -isnot [int64]) -and ($Value -isnot [uint16]) -and ($Value -isnot [uint32]) -and
    ($Value -isnot [double]) -and ($Value -isnot [decimal])) {
    return $false
  }
  $number = [double]$Value
  if ([double]::IsNaN($number) -or [double]::IsInfinity($number) -or ([Math]::Floor($number) -ne $number)) {
    return $false
  }
  return ($number -ge $Minimum -and $number -le $Maximum)
}

function Test-IsNonEmptyString {
  param([object]$Value)
  return (($Value -is [string]) -and -not [string]::IsNullOrWhiteSpace($Value))
}

function ConvertTo-DirectionFingerprint {
  param([object]$Value)
  if ($Value -isnot [string]) { return '' }
  $normalized = $Value.Normalize([Text.NormalizationForm]::FormKC).ToLowerInvariant()
  $tokens = @([regex]::Matches($normalized, '[\p{L}\p{Nd}]+') | ForEach-Object { $_.Value } | Sort-Object -Unique)
  return ($tokens -join '|')
}

function Test-RecordIdentity {
  param(
    [hashtable]$Record,
    [hashtable]$Request,
    [string]$Context,
    [string]$ItemKey = 'item_id',
    [System.Collections.Generic.List[object]]$Failures
  )

  $valid = $true
  foreach ($pair in @(
      @{ record = 'tracker_id'; request = 'tracker_id' },
      @{ record = $ItemKey; request = 'item_id' },
      @{ record = 'artifact_id'; request = 'artifact_id' }
    )) {
    $actual = $Record[$pair.record]
    $expected = $Request[$pair.request]
    if (($actual -isnot [string]) -or ($expected -isnot [string]) -or ($actual -ne $expected)) {
      Add-Failure -Failures $Failures -Code "$($Context).identity_mismatch" -Message "$Context identity '$($pair.record)' must match the request."
      $valid = $false
    }
  }
  return $valid
}

function Test-VerifiedBindingArray {
  param(
    [object]$Bindings,
    [string]$Context,
    [string]$PhysicalRoot,
    [System.Collections.Generic.List[object]]$Failures
  )

  $valid = $true
  $verifiedPaths = @()
  if (($Bindings -isnot [System.Collections.IEnumerable]) -or ($Bindings -is [string]) -or @($Bindings).Count -lt 1) {
    Add-Failure -Failures $Failures -Code "$($Context).invalid" -Message "$Context must be a non-empty array of exact file bindings."
    return [ordered]@{ valid = $false; verified_paths = @() }
  }

  $index = 0
  foreach ($binding in @($Bindings)) {
    if ($binding -isnot [hashtable]) {
      Add-Failure -Failures $Failures -Code "$($Context).entry_type" -Message "$Context entry $index must be an object."
      $valid = $false
      $index++
      continue
    }
    $result = Get-FileBindingValidation -Name "$($Context)[$index]" -Binding $binding -PhysicalRoot $PhysicalRoot -Failures $Failures
    if (($null -eq $result) -or (-not $result.verified)) {
      $valid = $false
    } else {
      $verifiedPaths += $result.relative_path
    }
    $index++
  }
  return [ordered]@{ valid = $valid; verified_paths = @($verifiedPaths) }
}

function Get-FileBindingValidation {
  param(
    [string]$Name,
    [hashtable]$Binding,
    [string]$PhysicalRoot,
    [System.Collections.Generic.List[object]]$Failures
  )
  Validate-ExactKeys -Object $Binding -RequiredKeys @('path', 'sha256', 'bytes') -OptionalKeys @() -Context "bindings.$Name" -Failures $Failures
  if (($Binding.path -isnot [string]) -or [string]::IsNullOrWhiteSpace($Binding.path)) {
    Add-Failure -Failures $Failures -Code "bindings.$Name.path_type" -Message "Binding '$Name' path must be a non-empty string."
    return $null
  }
  if (($Binding.sha256 -isnot [string]) -or [string]::IsNullOrWhiteSpace($Binding.sha256)) {
    Add-Failure -Failures $Failures -Code "bindings.$Name.sha_type" -Message "Binding '$Name' sha256 must be a non-empty string."
    return $null
  }
  if (-not (Test-IsIntegerValue -Value $Binding.bytes -Minimum 0)) {
    Add-Failure -Failures $Failures -Code "bindings.$Name.bytes_type" -Message "Binding '$Name' bytes must be an integer."
    return $null
  }
  try {
    $resolved = Resolve-PathUnderCanonicalRoot -InputPath $Binding.path -PhysicalRoot $PhysicalRoot -AllowMissingLeaf
  } catch {
    Add-Failure -Failures $Failures -Code "bindings.$Name.path_escape" -Message $_.Exception.Message
    return $null
  }
  if (-not (Test-Path -LiteralPath $resolved.physical -PathType Leaf)) {
    Add-Failure -Failures $Failures -Code "bindings.$Name.missing" -Message "Binding '$Name' path does not exist as a file: '$($resolved.canonical)'."
    return $null
  }
  $fileInfo = Get-Item -LiteralPath $resolved.physical
  $actualBytes = [int64]$fileInfo.Length
  $actualSha = (Get-FileHash -LiteralPath $resolved.physical -Algorithm SHA256).Hash.ToLowerInvariant()
  $expectedSha = $Binding.sha256.Trim().ToLowerInvariant()
  $expectedBytes = [int64]$Binding.bytes
  if ($actualSha -ne $expectedSha) {
    Add-Failure -Failures $Failures -Code "bindings.$Name.sha_mismatch" -Message "Binding '$Name' sha256 mismatch."
  }
  if ($actualBytes -ne $expectedBytes) {
    Add-Failure -Failures $Failures -Code "bindings.$Name.bytes_mismatch" -Message "Binding '$Name' bytes mismatch."
  }
  return [ordered]@{
    name = $Name
    canonical_path = $resolved.canonical
    physical_path = $resolved.physical
    relative_path = $resolved.relative
    expected_sha256 = $expectedSha
    actual_sha256 = $actualSha
    expected_bytes = $expectedBytes
    actual_bytes = $actualBytes
    verified = (($actualSha -eq $expectedSha) -and ($actualBytes -eq $expectedBytes))
  }
}

function Read-RecordFromBinding {
  param(
    [hashtable]$BindingResult,
    [switch]$AllowMarkdown
  )
  if ($null -eq $BindingResult) {
    return $null
  }
  if ($AllowMarkdown) {
    $extension = [System.IO.Path]::GetExtension($BindingResult.physical_path).ToLowerInvariant()
    if ($extension -eq '.md') {
      return Get-Content -LiteralPath $BindingResult.physical_path -Raw -Encoding UTF8
    }
  }
  return Read-JsonObject -Path $BindingResult.physical_path
}

function Parse-DoneCertificationMarkdown {
  param([string]$Content)
  $map = @{}
  foreach ($line in ($Content -split "`r?`n")) {
    if ($line -match '^\s*-\s*([^:]+):\s*(.*)\s*$') {
      $key = $matches[1].Trim().ToLowerInvariant() -replace '[^a-z0-9]+', '_'
      $map[$key] = $matches[2].Trim()
    }
  }
  return $map
}

$exitCode = 2
$physicalRoot = $null
try {
  $physicalRoot = Get-PhysicalRoot
  $requestResolved = Resolve-PathUnderCanonicalRoot -InputPath $RequestPath -PhysicalRoot $physicalRoot
  $outputResolved = Resolve-PathUnderCanonicalRoot -InputPath $OutputPath -PhysicalRoot $physicalRoot -AllowMissingLeaf
  if (Test-Path -LiteralPath $outputResolved.physical) {
    throw (New-OperationalError "Output collision rejected: '$($outputResolved.canonical)'.")
  }
} catch {
  $isOperational = $_.Exception.Data.Contains('Operational') -and [bool]$_.Exception.Data['Operational']
  if ($isOperational) {
    Write-Error $_.Exception.Message
    exit 1
  }
  throw
}

$failures = [System.Collections.Generic.List[object]]::new()
$blockers = [System.Collections.Generic.List[object]]::new()
$gates = [ordered]@{
  strict_protocol_read = $false
  qa_record_required = $false
  evidence_path_required = $false
  blocker_policy_required = $false
  test_run_required = $false
  failure_retest_discipline = $false
  tracker_item_linkage = $false
  done_certification_gate = $false
}

try {
  $request = Read-JsonObject -Path $requestResolved.physical
} catch {
  Add-Failure -Failures $failures -Code 'request.parse_failed' -Message $_.Exception.Message
  $request = @{}
}
if ($request -isnot [hashtable]) {
  Add-Failure -Failures $failures -Code 'request.root_type' -Message 'Request JSON root must be an object.'
  $request = @{}
}

Validate-ExactKeys -Object $request `
  -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'intended_lifecycle_status', 'protocol_acknowledgement', 'bindings') `
  -OptionalKeys @() `
  -Context 'request' `
  -Failures $failures

foreach ($scalarKey in @('tracker_id', 'item_id', 'artifact_id', 'intended_lifecycle_status')) {
  if (($request[$scalarKey] -isnot [string]) -or [string]::IsNullOrWhiteSpace([string]$request[$scalarKey])) {
    Add-Failure -Failures $failures -Code "request.$scalarKey.type" -Message "Request key '$scalarKey' must be a non-empty string."
  }
}
$allowedLifecycleStatuses = @('complete', 'in_progress', 'pending_validation', 'failed', 'blocked', 'needs_retest')
if (($request.intended_lifecycle_status -is [string]) -and ($allowedLifecycleStatuses -notcontains $request.intended_lifecycle_status)) {
  Add-Failure -Failures $failures -Code 'request.intended_lifecycle_status.invalid' -Message 'Request intended_lifecycle_status is unsupported.'
}

if ($request.protocol_acknowledgement -isnot [hashtable]) {
  Add-Failure -Failures $failures -Code 'request.protocol_acknowledgement.type' -Message 'protocol_acknowledgement must be an object.'
  $request.protocol_acknowledgement = @{}
}
Validate-ExactKeys -Object $request.protocol_acknowledgement `
  -RequiredKeys @('protocol_path', 'protocol_sha256', 'reviewer_role') `
  -OptionalKeys @() `
  -Context 'request.protocol_acknowledgement' `
  -Failures $failures

if ($request.bindings -isnot [hashtable]) {
  Add-Failure -Failures $failures -Code 'request.bindings.type' -Message 'bindings must be an object.'
  $request.bindings = @{}
}
  Validate-ExactKeys -Object $request.bindings `
    -RequiredKeys @('qa_record', 'test_run_record', 'evidence_manifest', 'blocker_record', 'tracker_record', 'item_record') `
    -OptionalKeys @('failure_record', 'retest_record', 'attempt_history_record', 'done_certification_record') `
  -Context 'request.bindings' `
  -Failures $failures

$bindingResults = @{}
foreach ($bindingName in $request.bindings.Keys) {
  $binding = $request.bindings[$bindingName]
  if ($binding -isnot [hashtable]) {
    Add-Failure -Failures $failures -Code "request.bindings.$bindingName.type" -Message "Binding '$bindingName' must be an object."
    continue
  }
  $bindingResults[$bindingName] = Get-FileBindingValidation -Name $bindingName -Binding $binding -PhysicalRoot $physicalRoot -Failures $failures
}

$protocolPath = 'Plan/Instructions/QA/STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md'
$protocolBindingPath = Resolve-PathUnderCanonicalRoot -InputPath $protocolPath -PhysicalRoot $physicalRoot
$protocolHash = (Get-FileHash -LiteralPath $protocolBindingPath.physical -Algorithm SHA256).Hash.ToLowerInvariant()
if (($request.protocol_acknowledgement.protocol_path -is [string]) -and
  ($request.protocol_acknowledgement.protocol_sha256 -is [string]) -and
  ($request.protocol_acknowledgement.reviewer_role -is [string])) {
  $pathOk = ($request.protocol_acknowledgement.protocol_path -eq $protocolPath)
  $hashOk = ($request.protocol_acknowledgement.protocol_sha256.Trim().ToLowerInvariant() -eq $protocolHash)
  $roleOk = ($request.protocol_acknowledgement.reviewer_role -eq $requiredReviewerRole)
  $gates.strict_protocol_read = ($pathOk -and $hashOk -and $roleOk)
  if (-not $pathOk) {
    Add-Failure -Failures $failures -Code 'protocol_ack.path_mismatch' -Message 'protocol_path does not match the strict protocol path.'
  }
  if (-not $hashOk) {
    Add-Failure -Failures $failures -Code 'protocol_ack.hash_mismatch' -Message 'protocol_sha256 does not match the current strict protocol hash.'
  }
  if (-not $roleOk) {
    Add-Failure -Failures $failures -Code 'protocol_ack.role_mismatch' -Message 'reviewer_role must be Codex Desktop autonomous QA.'
  }
}

$qaRecord = $null
$testRecord = $null
$manifestRecord = $null
$blockerRecord = $null
$trackerRecord = $null
$itemRecord = $null
$failureRecord = $null
$retestRecord = $null
$attemptHistoryRecord = $null
$doneRecord = $null

try { $qaRecord = Read-RecordFromBinding -BindingResult $bindingResults.qa_record } catch { Add-Failure -Failures $failures -Code 'qa_record.parse_failed' -Message $_.Exception.Message }
try { $testRecord = Read-RecordFromBinding -BindingResult $bindingResults.test_run_record } catch { Add-Failure -Failures $failures -Code 'test_run_record.parse_failed' -Message $_.Exception.Message }
try { $manifestRecord = Read-RecordFromBinding -BindingResult $bindingResults.evidence_manifest } catch { Add-Failure -Failures $failures -Code 'evidence_manifest.parse_failed' -Message $_.Exception.Message }
try { $blockerRecord = Read-RecordFromBinding -BindingResult $bindingResults.blocker_record } catch { Add-Failure -Failures $failures -Code 'blocker_record.parse_failed' -Message $_.Exception.Message }
try { $trackerRecord = Read-RecordFromBinding -BindingResult $bindingResults.tracker_record } catch { Add-Failure -Failures $failures -Code 'tracker_record.parse_failed' -Message $_.Exception.Message }
try { $itemRecord = Read-RecordFromBinding -BindingResult $bindingResults.item_record } catch { Add-Failure -Failures $failures -Code 'item_record.parse_failed' -Message $_.Exception.Message }
if ($bindingResults.ContainsKey('failure_record') -and $null -ne $bindingResults.failure_record) {
  try { $failureRecord = Read-RecordFromBinding -BindingResult $bindingResults.failure_record } catch { Add-Failure -Failures $failures -Code 'failure_record.parse_failed' -Message $_.Exception.Message }
}
if ($bindingResults.ContainsKey('retest_record') -and $null -ne $bindingResults.retest_record) {
  try { $retestRecord = Read-RecordFromBinding -BindingResult $bindingResults.retest_record } catch { Add-Failure -Failures $failures -Code 'retest_record.parse_failed' -Message $_.Exception.Message }
}
if ($bindingResults.ContainsKey('attempt_history_record') -and $null -ne $bindingResults.attempt_history_record) {
  try { $attemptHistoryRecord = Read-RecordFromBinding -BindingResult $bindingResults.attempt_history_record } catch { Add-Failure -Failures $failures -Code 'attempt_history_record.parse_failed' -Message $_.Exception.Message }
}
if ($bindingResults.ContainsKey('done_certification_record') -and $null -ne $bindingResults.done_certification_record) {
  try {
    $doneRecordRaw = Read-RecordFromBinding -BindingResult $bindingResults.done_certification_record -AllowMarkdown
    if ($doneRecordRaw -is [string]) {
      $doneRecord = Parse-DoneCertificationMarkdown -Content $doneRecordRaw
    } else {
      $doneRecord = $doneRecordRaw
    }
  } catch {
    Add-Failure -Failures $failures -Code 'done_certification_record.parse_failed' -Message $_.Exception.Message
  }
}

if ($qaRecord -is [hashtable]) {
  Validate-ExactKeys -Object $qaRecord `
    -RequiredKeys @('artifact_id', 'artifact_type', 'task_id', 'tracker_id', 'reviewer', 'test_method', 'qa_status', 'evidence_paths', 'known_issues', 'next_action', 'timestamp', 'review_modalities', 'severity_findings', 'inspection_status') `
    -OptionalKeys @('scores', 'defects', 'evidence_id', 'workflow_reference', 'prompt_reference', 'model_context', 'image', 'visual_runtime_ready', 'final_decision_allowed') `
    -Context 'qa_record' `
    -Failures $failures
  if (($qaRecord.reviewer -isnot [string]) -or ($qaRecord.reviewer -ne $requiredReviewerRole)) {
    Add-Failure -Failures $failures -Code 'qa_record.reviewer_invalid' -Message 'qa_record.reviewer must be Codex Desktop autonomous QA.'
  }
  if (($qaRecord.artifact_id -isnot [string]) -or ($qaRecord.tracker_id -isnot [string]) -or ($qaRecord.task_id -isnot [string])) {
    Add-Failure -Failures $failures -Code 'qa_record.identity_type' -Message 'qa_record identity keys must be strings.'
  }
  if (($qaRecord.artifact_type -isnot [string]) -or [string]::IsNullOrWhiteSpace($qaRecord.artifact_type)) {
    Add-Failure -Failures $failures -Code 'qa_record.artifact_type_invalid' -Message 'qa_record.artifact_type must be a non-empty string.'
  }
  if (-not (Test-IsNonEmptyString -Value $qaRecord.test_method)) {
    Add-Failure -Failures $failures -Code 'qa_record.test_method_invalid' -Message 'qa_record.test_method must be a non-empty string.'
  }
  if (($qaRecord.qa_status -isnot [string]) -or (@('pass', 'pass_with_non_blocking_issues', 'fail', 'blocked', 'needs_clarification', 'needs_retest', 'pending_artifact', 'pending_visual_review', 'pending_validation') -notcontains $qaRecord.qa_status)) {
    Add-Failure -Failures $failures -Code 'qa_record.qa_status_invalid' -Message 'qa_record.qa_status is unsupported.'
  }
  $null = Test-RecordIdentity -Record $qaRecord -Request $request -Context 'qa_record' -ItemKey 'task_id' -Failures $failures
  if (-not (Test-IsStringArray -Value $qaRecord.evidence_paths) -or @($qaRecord.evidence_paths).Count -lt 1) {
    Add-Failure -Failures $failures -Code 'qa_record.evidence_paths_invalid' -Message 'qa_record.evidence_paths must be a non-empty string array.'
  }
  if (-not (Test-IsStringArray -Value $qaRecord.review_modalities) -or @($qaRecord.review_modalities).Count -lt 1) {
    Add-Failure -Failures $failures -Code 'qa_record.review_modalities_invalid' -Message 'qa_record.review_modalities must be a non-empty string array.'
  }
  if (($qaRecord.severity_findings -isnot [hashtable]) -or
    @(@('s0', 's1', 's2', 's3', 's4').Where({ -not $qaRecord.severity_findings.ContainsKey($_) })).Count -gt 0 -or
    @($qaRecord.severity_findings.Keys).Count -ne 5 -or
    @($qaRecord.severity_findings.Values.Where({ -not (Test-IsIntegerValue -Value $_ -Minimum 0) })).Count -gt 0) {
    Add-Failure -Failures $failures -Code 'qa_record.severity_findings_invalid' -Message 'qa_record.severity_findings must contain s0-s4.'
  }
  if (($qaRecord.inspection_status -isnot [string]) -or (@('completed', 'partial', 'not_started') -notcontains $qaRecord.inspection_status)) {
    Add-Failure -Failures $failures -Code 'qa_record.inspection_status_invalid' -Message 'qa_record.inspection_status must be completed, partial, or not_started.'
  }
  if (($qaRecord.known_issues -isnot [System.Collections.IEnumerable]) -or ($qaRecord.known_issues -is [string])) {
    Add-Failure -Failures $failures -Code 'qa_record.known_issues_invalid' -Message 'qa_record.known_issues must be an array.'
  }
  if (-not (Test-IsNonEmptyString -Value $qaRecord.next_action)) {
    Add-Failure -Failures $failures -Code 'qa_record.next_action_invalid' -Message 'qa_record.next_action must be a non-empty string.'
  }
  $qaTimestamp = [DateTimeOffset]::MinValue
  if (($qaRecord.timestamp -isnot [string]) -or -not [DateTimeOffset]::TryParse($qaRecord.timestamp, [ref]$qaTimestamp)) {
    Add-Failure -Failures $failures -Code 'qa_record.timestamp_invalid' -Message 'qa_record.timestamp must be a parseable timestamp.'
  }
  $gates.qa_record_required = (@($failures.Where({ $_.code -like 'qa_record*' })).Count -eq 0)
} else {
  Add-Failure -Failures $failures -Code 'qa_record.missing' -Message 'qa_record is missing or invalid.'
}

$testVerifiedEvidencePaths = @()
$testLogPaths = @()
if ($testRecord -is [hashtable]) {
  Validate-ExactKeys -Object $testRecord `
    -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'command', 'exit_code', 'result', 'expected_summary', 'actual_summary', 'logs', 'evidence_bindings') `
    -OptionalKeys @() `
    -Context 'test_run_record' `
    -Failures $failures
  if (($testRecord.command -isnot [string]) -or [string]::IsNullOrWhiteSpace($testRecord.command)) {
    Add-Failure -Failures $failures -Code 'test_run_record.command_invalid' -Message 'test_run_record.command must be a non-empty string.'
  }
  if (-not (Test-IsIntegerValue -Value $testRecord.exit_code)) {
    Add-Failure -Failures $failures -Code 'test_run_record.exit_code_invalid' -Message 'test_run_record.exit_code must be an integer.'
  }
  if (($testRecord.result -isnot [string]) -or (@('pass', 'fail', 'blocked', 'needs_retest') -notcontains $testRecord.result)) {
    Add-Failure -Failures $failures -Code 'test_run_record.result_invalid' -Message 'test_run_record.result is invalid.'
  }
  if (($testRecord.result -eq 'pass') -and ($testRecord.exit_code -ne 0)) {
    Add-Failure -Failures $failures -Code 'test_run_record.pass_exit_mismatch' -Message 'A passing test_run_record must have exit_code 0.'
  }
  foreach ($summaryKey in @('expected_summary', 'actual_summary')) {
    if (-not (Test-IsNonEmptyString -Value $testRecord[$summaryKey])) {
      Add-Failure -Failures $failures -Code "test_run_record.$($summaryKey)_invalid" -Message "test_run_record.$summaryKey must be a non-empty string."
    }
  }
  $null = Test-RecordIdentity -Record $testRecord -Request $request -Context 'test_run_record' -Failures $failures
  if (-not (Test-IsStringArray -Value $testRecord.logs) -or @($testRecord.logs).Count -lt 1) {
    Add-Failure -Failures $failures -Code 'test_run_record.logs_invalid' -Message 'test_run_record.logs must be a non-empty string array.'
  } else {
    $testLogPaths = @($testRecord.logs)
  }
  $testEvidenceValidation = Test-VerifiedBindingArray -Bindings $testRecord.evidence_bindings -Context 'test_run_record.evidence_bindings' -PhysicalRoot $physicalRoot -Failures $failures
  if (-not $testEvidenceValidation.valid) {
    Add-Failure -Failures $failures -Code 'test_run_record.evidence_bindings_invalid' -Message 'test_run_record evidence bindings must all verify by path, sha256, and bytes.'
  } else {
    $testVerifiedEvidencePaths = @($testEvidenceValidation.verified_paths)
  }
  foreach ($logPath in $testLogPaths) {
    try {
      $resolvedLog = Resolve-PathUnderCanonicalRoot -InputPath $logPath -PhysicalRoot $physicalRoot
      if ($testVerifiedEvidencePaths -notcontains $resolvedLog.relative) {
        Add-Failure -Failures $failures -Code 'test_run_record.log_not_bound' -Message "Log '$logPath' is not present in verified evidence_bindings."
      }
    } catch {
      Add-Failure -Failures $failures -Code 'test_run_record.log_invalid' -Message $_.Exception.Message
    }
  }
  $gates.test_run_required = (@($failures.Where({ $_.code -like 'test_run_record*' })).Count -eq 0)
} else {
  Add-Failure -Failures $failures -Code 'test_run_record.missing' -Message 'test_run_record is missing or invalid.'
}

$manifestVerifiedPaths = @()
if ($manifestRecord -is [hashtable]) {
  Validate-ExactKeys -Object $manifestRecord `
    -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'evidence') `
    -OptionalKeys @() `
    -Context 'evidence_manifest' `
    -Failures $failures
  $null = Test-RecordIdentity -Record $manifestRecord -Request $request -Context 'evidence_manifest' -Failures $failures
  if ($manifestRecord.evidence -isnot [System.Collections.IEnumerable] -or ($manifestRecord.evidence -is [string]) -or @($manifestRecord.evidence).Count -lt 1) {
    Add-Failure -Failures $failures -Code 'evidence_manifest.empty' -Message 'evidence_manifest.evidence must be a non-empty array.'
  } else {
    $allManifestBindingsGood = $true
    foreach ($entry in @($manifestRecord.evidence)) {
      if ($entry -isnot [hashtable]) {
        Add-Failure -Failures $failures -Code 'evidence_manifest.entry_type' -Message 'Each evidence manifest entry must be an object.'
        $allManifestBindingsGood = $false
        continue
      }
      Validate-ExactKeys -Object $entry -RequiredKeys @('path', 'sha256', 'bytes') -OptionalKeys @() -Context 'evidence_manifest.entry' -Failures $failures
      try {
        $manifestBinding = Get-FileBindingValidation -Name 'manifest_entry' -Binding $entry -PhysicalRoot $physicalRoot -Failures $failures
        if ($null -eq $manifestBinding -or -not $manifestBinding.verified) {
          $allManifestBindingsGood = $false
        } else {
          $manifestVerifiedPaths += $manifestBinding.relative_path
        }
      } catch {
        Add-Failure -Failures $failures -Code 'evidence_manifest.entry_invalid' -Message $_.Exception.Message
        $allManifestBindingsGood = $false
      }
    }
    $gates.evidence_path_required = $allManifestBindingsGood
  }
} else {
  Add-Failure -Failures $failures -Code 'evidence_manifest.missing' -Message 'evidence_manifest is missing or invalid.'
}

foreach ($path in $testVerifiedEvidencePaths) {
  if ($manifestVerifiedPaths -notcontains $path) {
    Add-Failure -Failures $failures -Code 'test_run_record.evidence_not_manifested' -Message "Verified test evidence '$path' is absent from the evidence manifest."
  }
}
if ($qaRecord -is [hashtable] -and (Test-IsStringArray -Value $qaRecord.evidence_paths)) {
  foreach ($path in @($qaRecord.evidence_paths)) {
    if ($manifestVerifiedPaths -notcontains $path) {
      Add-Failure -Failures $failures -Code 'qa_record.evidence_not_manifested' -Message "QA evidence '$path' is absent from the verified evidence manifest."
    }
  }
}

$qualityOrTestFailurePresent = $false
if ($blockerRecord -is [hashtable]) {
  Validate-ExactKeys -Object $blockerRecord `
    -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'blocker_policy', 'unresolved_blockers', 'classification', 'status', 'suppressed_failures', 'quality_failures', 'test_failures') `
    -OptionalKeys @() `
    -Context 'blocker_record' `
    -Failures $failures
  $null = Test-RecordIdentity -Record $blockerRecord -Request $request -Context 'blocker_record' -Failures $failures
  if (($blockerRecord.blocker_policy -isnot [string]) -or ($blockerRecord.blocker_policy -ne $requiredBlockerPolicy)) {
    Add-Failure -Failures $failures -Code 'blocker_record.policy_mismatch' -Message 'blocker_record.blocker_policy is invalid.'
  }
  if (($blockerRecord.classification -isnot [string]) -or (@('clear', 'blocked') -notcontains $blockerRecord.classification) -or
    ($blockerRecord.status -isnot [string]) -or (@('clear', 'blocked') -notcontains $blockerRecord.status)) {
    Add-Failure -Failures $failures -Code 'blocker_record.state_invalid' -Message 'blocker_record classification and status must be clear or blocked.'
  } elseif ($blockerRecord.classification -ne $blockerRecord.status) {
    Add-Failure -Failures $failures -Code 'blocker_record.state_mismatch' -Message 'blocker_record classification and status must agree.'
  } elseif ($blockerRecord.status -eq 'blocked') {
    Add-Blocker -Blockers $blockers -Code 'blocker_record.blocked_state' -Message 'blocker_record explicitly declares a blocked state.'
  }
  if ($blockerRecord.unresolved_blockers -isnot [System.Collections.IEnumerable] -or ($blockerRecord.unresolved_blockers -is [string])) {
    Add-Failure -Failures $failures -Code 'blocker_record.unresolved_blockers_invalid' -Message 'blocker_record.unresolved_blockers must be an array.'
  } elseif (@($blockerRecord.unresolved_blockers).Count -gt 0) {
    foreach ($entry in @($blockerRecord.unresolved_blockers)) {
      if ($entry -isnot [hashtable]) {
        Add-Blocker -Blockers $blockers -Code 'blocker_record.unresolved_entry_type' -Message 'Unresolved blocker entry must be an object.'
      } else {
        Validate-ExactKeys -Object $entry -RequiredKeys @('code', 'reason', 'status') -OptionalKeys @() -Context 'blocker_record.unresolved_entry' -Failures $failures
        $reason = if ($entry.ContainsKey('reason') -and ($entry.reason -is [string]) -and -not [string]::IsNullOrWhiteSpace($entry.reason)) { $entry.reason } else { 'unspecified' }
        Add-Blocker -Blockers $blockers -Code 'unresolved_blocker' -Message ("Unresolved blocker: {0}" -f $reason)
      }
    }
  }
  if ($blockerRecord.suppressed_failures -isnot [System.Collections.IEnumerable] -or ($blockerRecord.suppressed_failures -is [string])) {
    Add-Failure -Failures $failures -Code 'blocker_record.suppressed_failures_invalid' -Message 'blocker_record.suppressed_failures must be an array.'
  } elseif (@($blockerRecord.suppressed_failures).Count -gt 0) {
    Add-Failure -Failures $failures -Code 'blocker_record.suppressed_failures_present' -Message 'Suppressed failures are forbidden.'
  }
  foreach ($failureArrayName in @('quality_failures', 'test_failures')) {
    $value = $blockerRecord[$failureArrayName]
    if (($value -isnot [System.Collections.IEnumerable]) -or ($value -is [string])) {
      Add-Failure -Failures $failures -Code "blocker_record.$($failureArrayName)_invalid" -Message "blocker_record.$failureArrayName must be an array."
    }
  }
  $qualityCount = @($blockerRecord.quality_failures).Count
  $testCount = @($blockerRecord.test_failures).Count
  if ($qualityCount -gt 0 -or $testCount -gt 0) {
    $qualityOrTestFailurePresent = $true
    if ($qualityCount -gt 0) { Add-Failure -Failures $failures -Code 'blocker_record.quality_failures_present' -Message 'Quality failures present in blocker record.' }
    if ($testCount -gt 0) { Add-Failure -Failures $failures -Code 'blocker_record.test_failures_present' -Message 'Test failures present in blocker record.' }
  }
  $gates.blocker_policy_required = (@($failures.Where({ $_.code -like 'blocker_record*' })).Count -eq 0)
} else {
  Add-Failure -Failures $failures -Code 'blocker_record.missing' -Message 'blocker_record is missing or invalid.'
}

if (($trackerRecord -is [hashtable]) -and ($itemRecord -is [hashtable])) {
  Validate-ExactKeys -Object $trackerRecord -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'status', 'final_decision', 'evidence_paths') -OptionalKeys @() -Context 'tracker_record' -Failures $failures
  Validate-ExactKeys -Object $itemRecord -RequiredKeys @('item_id', 'tracker_id', 'artifact_id', 'status', 'final_decision', 'evidence_paths') -OptionalKeys @() -Context 'item_record' -Failures $failures

  $identityOk = $true
  foreach ($pair in @(
      @{ request = 'tracker_id'; tracker = 'tracker_id'; item = 'tracker_id' },
      @{ request = 'item_id'; tracker = 'item_id'; item = 'item_id' },
      @{ request = 'artifact_id'; tracker = 'artifact_id'; item = 'artifact_id' }
    )) {
    $requestValue = [string]$request[$pair.request]
    if (($trackerRecord[$pair.tracker] -ne $requestValue) -or ($itemRecord[$pair.item] -ne $requestValue)) {
      $identityOk = $false
      Add-Failure -Failures $failures -Code 'tracker_item.identity_mismatch' -Message "Identity mismatch for '$($pair.request)'."
    }
  }
  if (-not (Test-IsStringArray -Value $trackerRecord.evidence_paths) -or -not (Test-IsStringArray -Value $itemRecord.evidence_paths)) {
    Add-Failure -Failures $failures -Code 'tracker_item.evidence_paths_invalid' -Message 'tracker/item evidence_paths must be string arrays.'
    $identityOk = $false
  } else {
    $trackerPaths = @($trackerRecord.evidence_paths)
    $itemPaths = @($itemRecord.evidence_paths)
    if (@(Compare-Object -ReferenceObject $trackerPaths -DifferenceObject $itemPaths).Count -gt 0) {
      Add-Failure -Failures $failures -Code 'tracker_item.evidence_paths_mismatch' -Message 'tracker and item evidence paths do not match.'
      $identityOk = $false
    }
    foreach ($path in @($trackerPaths + $itemPaths | Select-Object -Unique)) {
      if ($manifestVerifiedPaths -notcontains $path) {
        Add-Failure -Failures $failures -Code 'tracker_item.evidence_not_manifested' -Message "Tracker/item evidence '$path' is absent from the verified evidence manifest."
        $identityOk = $false
      }
    }
  }
  if ($trackerRecord.final_decision -ne $itemRecord.final_decision) {
    Add-Failure -Failures $failures -Code 'tracker_item.final_decision_mismatch' -Message 'tracker and item final_decision must match.'
    $identityOk = $false
  }
  if ($trackerRecord.status -ne $itemRecord.status) {
    Add-Failure -Failures $failures -Code 'tracker_item.status_mismatch' -Message 'tracker and item status must match.'
    $identityOk = $false
  }
  if ((@('complete', 'blocked', 'failed', 'in_progress', 'pending_validation', 'needs_retest') -notcontains $trackerRecord.status) -or
    (@('pass', 'blocked', 'fail', 'pending') -notcontains $trackerRecord.final_decision)) {
    Add-Failure -Failures $failures -Code 'tracker_item.state_invalid' -Message 'tracker/item status or final_decision is unsupported.'
    $identityOk = $false
  }
  $gates.tracker_item_linkage = $identityOk
} else {
  Add-Failure -Failures $failures -Code 'tracker_item.missing' -Message 'tracker and item records must both exist.'
}

$needsFailureRetest = $false
$requestedStatus = [string]$request.intended_lifecycle_status
$qaStatus = if ($qaRecord -is [hashtable]) { [string]$qaRecord.qa_status } else { '' }
$testResult = if ($testRecord -is [hashtable]) { [string]$testRecord.result } else { '' }
if (@('fail', 'needs_retest') -contains $requestedStatus -or @('fail', 'needs_retest') -contains $qaStatus -or @('fail', 'needs_retest') -contains $testResult) {
  $needsFailureRetest = $true
}

$failureRetestValid = $true
if ($needsFailureRetest) {
  if ($null -eq $failureRecord) {
    Add-Failure -Failures $failures -Code 'failure_record.required' -Message 'failure_record is required for failed/needs_retest histories.'
    $failureRetestValid = $false
  }
  if ($null -eq $retestRecord) {
    Add-Failure -Failures $failures -Code 'retest_record.required' -Message 'retest_record is required for failed/needs_retest histories.'
    $failureRetestValid = $false
  }
  if ($null -eq $attemptHistoryRecord) {
    Add-Failure -Failures $failures -Code 'attempt_history_record.required' -Message 'A hash-bound attempt_history_record is required for failed/needs_retest histories.'
    $failureRetestValid = $false
  }
  if ($failureRecord -is [hashtable]) {
    Validate-ExactKeys -Object $failureRecord `
      -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'failure_class', 'severity', 'suspected_cause', 'attempt_number', 'similar_to_previous', 'material_change', 'new_direction_evidence', 'deeper_diagnosis_performed') `
      -OptionalKeys @() `
      -Context 'failure_record' `
      -Failures $failures
    if (-not (Test-RecordIdentity -Record $failureRecord -Request $request -Context 'failure_record' -Failures $failures)) {
      $failureRetestValid = $false
    }
    if ($supportedFailureClasses -notcontains [string]$failureRecord.failure_class) {
      Add-Failure -Failures $failures -Code 'failure_record.failure_class_invalid' -Message 'failure_record.failure_class is unsupported.'
      $failureRetestValid = $false
    }
    if (($failureRecord.severity -isnot [string]) -or ($failureRecord.severity -notmatch '^S[0-4]$')) {
      Add-Failure -Failures $failures -Code 'failure_record.severity_invalid' -Message 'failure_record.severity must be S0-S4.'
      $failureRetestValid = $false
    }
    if (-not (Test-IsNonEmptyString -Value $failureRecord.suspected_cause)) {
      Add-Failure -Failures $failures -Code 'failure_record.suspected_cause_invalid' -Message 'failure_record.suspected_cause must be a non-empty string.'
      $failureRetestValid = $false
    }
    foreach ($booleanKey in @('similar_to_previous', 'material_change', 'deeper_diagnosis_performed')) {
      if ($failureRecord[$booleanKey] -isnot [bool]) {
        Add-Failure -Failures $failures -Code "failure_record.$($booleanKey)_invalid" -Message "failure_record.$booleanKey must be boolean."
        $failureRetestValid = $false
      }
    }
    if ($failureRecord.new_direction_evidence -isnot [string]) {
      Add-Failure -Failures $failures -Code 'failure_record.new_direction_evidence_invalid' -Message 'failure_record.new_direction_evidence must be a string.'
      $failureRetestValid = $false
    }
    if (-not (Test-IsIntegerValue -Value $failureRecord.attempt_number -Minimum 1 -Maximum ([int]::MaxValue))) {
      Add-Failure -Failures $failures -Code 'failure_record.attempt_number_invalid' -Message 'failure_record.attempt_number must be a positive integer.'
      $failureRetestValid = $false
    } else {
      $attempt = [int]$failureRecord.attempt_number
      if (($attempt -ge 3) -and (-not [bool]$failureRecord.deeper_diagnosis_performed)) {
        Add-Failure -Failures $failures -Code 'failure_record.deeper_diagnosis_required' -Message 'Third similar failed attempt requires deeper diagnosis.'
        $failureRetestValid = $false
      }
      if (($attempt -ge 4) -and [string]::IsNullOrWhiteSpace([string]$failureRecord.new_direction_evidence)) {
        Add-Blocker -Blockers $blockers -Code 'failure_record.redesign_block' -Message 'Fourth failed attempt is blocked pending redesign.'
      }
      if (($attempt -gt 1) -and (-not [bool]$failureRecord.material_change) -and [string]::IsNullOrWhiteSpace([string]$failureRecord.new_direction_evidence)) {
        Add-Failure -Failures $failures -Code 'failure_record.material_change_required' -Message 'Retest attempts require material change or new direction evidence.'
        $failureRetestValid = $false
      }
    }
  }
  if ($retestRecord -is [hashtable]) {
    Validate-ExactKeys -Object $retestRecord `
      -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'attempt_number', 'intended_fix', 'expected_result', 'material_change', 'new_direction_evidence', 'result') `
      -OptionalKeys @() `
      -Context 'retest_record' `
      -Failures $failures
    if (-not (Test-RecordIdentity -Record $retestRecord -Request $request -Context 'retest_record' -Failures $failures)) {
      $failureRetestValid = $false
    }
    if (-not (Test-IsIntegerValue -Value $retestRecord.attempt_number -Minimum 1 -Maximum ([int]::MaxValue))) {
      Add-Failure -Failures $failures -Code 'retest_record.attempt_number_invalid' -Message 'retest_record.attempt_number must be a positive integer.'
      $failureRetestValid = $false
    }
    foreach ($stringKey in @('intended_fix', 'expected_result')) {
      if (-not (Test-IsNonEmptyString -Value $retestRecord[$stringKey])) {
        Add-Failure -Failures $failures -Code "retest_record.$($stringKey)_invalid" -Message "retest_record.$stringKey must be a non-empty string."
        $failureRetestValid = $false
      }
    }
    if (($retestRecord.material_change -isnot [bool]) -or ($retestRecord.new_direction_evidence -isnot [string])) {
      Add-Failure -Failures $failures -Code 'retest_record.change_evidence_invalid' -Message 'retest_record material_change must be boolean and new_direction_evidence must be a string.'
      $failureRetestValid = $false
    }
    if (($retestRecord.result -isnot [string]) -or (@('pass', 'fail', 'blocked', 'needs_retest') -notcontains $retestRecord.result)) {
      Add-Failure -Failures $failures -Code 'retest_record.result_invalid' -Message 'retest_record.result is unsupported.'
      $failureRetestValid = $false
    }
    if (($failureRecord -is [hashtable]) -and ($retestRecord.attempt_number -ne $failureRecord.attempt_number)) {
      Add-Failure -Failures $failures -Code 'retest_record.attempt_mismatch' -Message 'retest_record.attempt_number must match failure_record.attempt_number.'
      $failureRetestValid = $false
    }
    if (($failureRecord -is [hashtable]) -and
      (($retestRecord.material_change -ne $failureRecord.material_change) -or
        ($retestRecord.new_direction_evidence -ne $failureRecord.new_direction_evidence))) {
      Add-Failure -Failures $failures -Code 'retest_record.change_evidence_mismatch' -Message 'retest_record change evidence must match failure_record.'
      $failureRetestValid = $false
    }
  }
  if ($attemptHistoryRecord -is [hashtable]) {
    Validate-ExactKeys -Object $attemptHistoryRecord `
      -RequiredKeys @('tracker_id', 'item_id', 'artifact_id', 'attempts') `
      -OptionalKeys @() `
      -Context 'attempt_history_record' `
      -Failures $failures
    if (-not (Test-RecordIdentity -Record $attemptHistoryRecord -Request $request -Context 'attempt_history_record' -Failures $failures)) {
      $failureRetestValid = $false
    }
    if (($attemptHistoryRecord.attempts -isnot [System.Collections.IEnumerable]) -or
      ($attemptHistoryRecord.attempts -is [string]) -or
      @($attemptHistoryRecord.attempts).Count -lt 1) {
      Add-Failure -Failures $failures -Code 'attempt_history_record.attempts_invalid' -Message 'attempt_history_record.attempts must be a non-empty array.'
      $failureRetestValid = $false
    } elseif (($failureRecord -is [hashtable]) -and (Test-IsIntegerValue -Value $failureRecord.attempt_number -Minimum 1 -Maximum ([int]::MaxValue))) {
      $currentAttempt = [int]$failureRecord.attempt_number
      $historyByAttempt = @{}
      foreach ($entry in @($attemptHistoryRecord.attempts)) {
        if ($entry -isnot [hashtable]) {
          Add-Failure -Failures $failures -Code 'attempt_history_record.entry_type' -Message 'Each attempt history entry must be an object.'
          $failureRetestValid = $false
          continue
        }
        Validate-ExactKeys -Object $entry `
          -RequiredKeys @('attempt_number', 'failure_class', 'result', 'material_change', 'new_direction_evidence', 'deeper_diagnosis_performed') `
          -OptionalKeys @() `
          -Context 'attempt_history_record.entry' `
          -Failures $failures
        if (-not (Test-IsIntegerValue -Value $entry.attempt_number -Minimum 1 -Maximum ([int]::MaxValue))) {
          Add-Failure -Failures $failures -Code 'attempt_history_record.attempt_number_invalid' -Message 'Attempt history numbers must be positive integers.'
          $failureRetestValid = $false
          continue
        }
        if (($supportedFailureClasses -notcontains [string]$entry.failure_class) -or
          (@('pass', 'fail', 'blocked', 'needs_retest') -notcontains [string]$entry.result) -or
          ($entry.material_change -isnot [bool]) -or
          ($entry.new_direction_evidence -isnot [string]) -or
          ($entry.deeper_diagnosis_performed -isnot [bool])) {
          Add-Failure -Failures $failures -Code 'attempt_history_record.entry_value_invalid' -Message 'Attempt history entry values are invalid.'
          $failureRetestValid = $false
        }
        $number = [int]$entry.attempt_number
        if ($historyByAttempt.ContainsKey($number)) {
          Add-Failure -Failures $failures -Code 'attempt_history_record.duplicate_attempt' -Message "Attempt history contains duplicate attempt $number."
          $failureRetestValid = $false
        } else {
          $historyByAttempt[$number] = $entry
        }
      }
      foreach ($number in 1..$currentAttempt) {
        if (-not $historyByAttempt.ContainsKey($number)) {
          Add-Failure -Failures $failures -Code 'attempt_history_record.sequence_gap' -Message "Attempt history is missing attempt $number."
          $failureRetestValid = $false
        }
      }
      if ($historyByAttempt.ContainsKey($currentAttempt)) {
        $currentHistory = $historyByAttempt[$currentAttempt]
        if (($currentHistory.failure_class -ne $failureRecord.failure_class) -or
          ($currentHistory.material_change -ne $failureRecord.material_change) -or
          ($currentHistory.new_direction_evidence -ne $failureRecord.new_direction_evidence) -or
          ($currentHistory.deeper_diagnosis_performed -ne $failureRecord.deeper_diagnosis_performed) -or
          (($retestRecord -is [hashtable]) -and ($currentHistory.result -ne $retestRecord.result))) {
          Add-Failure -Failures $failures -Code 'attempt_history_record.current_attempt_mismatch' -Message 'Current attempt history does not match the bound failure/retest records.'
          $failureRetestValid = $false
        }
        if ($currentAttempt -ge 4 -and -not [string]::IsNullOrWhiteSpace([string]$currentHistory.new_direction_evidence)) {
          $currentDirectionFingerprint = ConvertTo-DirectionFingerprint -Value $currentHistory.new_direction_evidence
          $priorDirectionFingerprints = @(1..($currentAttempt - 1) | ForEach-Object {
              if ($historyByAttempt.ContainsKey($_)) {
                ConvertTo-DirectionFingerprint -Value $historyByAttempt[$_].new_direction_evidence
              }
            } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
          if ($priorDirectionFingerprints -contains $currentDirectionFingerprint) {
            Add-Blocker -Blockers $blockers -Code 'failure_record.repeated_direction_block' -Message 'Fourth-or-later attempt reused prior new-direction evidence and remains blocked pending redesign.'
          }
          $directionEvidenceVerified = $false
          try {
            $directionEvidencePath = Resolve-PathUnderCanonicalRoot -InputPath ([string]$currentHistory.new_direction_evidence) -PhysicalRoot $physicalRoot -AllowMissingLeaf
            $directionEvidenceVerified = ($manifestVerifiedPaths -contains $directionEvidencePath.relative)
          } catch {
            $directionEvidenceVerified = $false
          }
          if (-not $directionEvidenceVerified) {
            Add-Blocker -Blockers $blockers -Code 'failure_record.new_direction_evidence_unverified' -Message 'Fourth-or-later new_direction_evidence must identify a hash-verified evidence-manifest artifact.'
          }
        }
      }
    }
  }
}
$gates.failure_retest_discipline = ($failureRetestValid -and (@($failures.Where({ $_.code -like 'failure_record*' -or $_.code -like 'retest_record*' -or $_.code -like 'attempt_history_record*' })).Count -eq 0))

$doneGatePassed = $false
$donePresent = $null -ne $doneRecord

$completionRequirements = [ordered]@{
  implementation_finished = $false
  relevant_test_run_performed = $false
  qa_record_created = $false
  artifact_inspection_completed = $false
  tracker_updated = $false
  item_updated = $false
  known_issues_reviewed = $false
  evidence_manifest_created = $false
  exact_artifact_test_qa_bindings = $false
}
$implementationScopeVerified = $false

if ($donePresent) {
  if ($doneRecord -is [hashtable]) {
    Validate-ExactKeys -Object $doneRecord `
      -RequiredKeys @('certification_id', 'task_id', 'tracker_id', 'artifact_id', 'title', 'artifact_scope', 'implementation_summary', 'tests_performed', 'qa_summary', 'evidence_paths', 'known_issues', 'final_decision', 'certifier', 'timestamp', 'completion_gates', 'bindings') `
      -OptionalKeys @() `
      -Context 'done_certification' `
      -Failures $failures
    $null = Test-RecordIdentity -Record $doneRecord -Request $request -Context 'done_certification' -ItemKey 'task_id' -Failures $failures
    foreach ($stringKey in @('certification_id', 'title', 'implementation_summary', 'qa_summary')) {
      if (-not (Test-IsNonEmptyString -Value $doneRecord[$stringKey])) {
        Add-Failure -Failures $failures -Code "done_certification.$($stringKey)_invalid" -Message "Done certification $stringKey must be a non-empty string."
      }
    }
    if (-not (Test-IsStringArray -Value $doneRecord.artifact_scope) -or @($doneRecord.artifact_scope).Count -lt 1) {
      Add-Failure -Failures $failures -Code 'done_certification.artifact_scope_invalid' -Message 'Done certification artifact_scope must be a non-empty string array.'
    } else {
      $implementationScopeVerified = $true
      foreach ($path in @($doneRecord.artifact_scope)) {
        if ($manifestVerifiedPaths -notcontains $path) {
          Add-Failure -Failures $failures -Code 'done_certification.artifact_scope_not_manifested' -Message "Implementation artifact '$path' is absent from the verified evidence manifest."
          $implementationScopeVerified = $false
        }
        if ($testVerifiedEvidencePaths -notcontains $path) {
          Add-Failure -Failures $failures -Code 'done_certification.artifact_scope_not_test_bound' -Message "Implementation artifact '$path' is absent from the verified test evidence bindings."
          $implementationScopeVerified = $false
        }
      }
    }
    if (-not (Test-IsStringArray -Value $doneRecord.tests_performed) -or @($doneRecord.tests_performed).Count -lt 1) {
      Add-Failure -Failures $failures -Code 'done_certification.tests_performed_invalid' -Message 'Done certification tests_performed must be a non-empty string array.'
    }
    if (($doneRecord.known_issues -isnot [System.Collections.IEnumerable]) -or ($doneRecord.known_issues -is [string])) {
      Add-Failure -Failures $failures -Code 'done_certification.known_issues_invalid' -Message 'Done certification known_issues must be an array.'
    }
    $doneTimestamp = [DateTimeOffset]::MinValue
    if (($doneRecord.timestamp -isnot [string]) -or -not [DateTimeOffset]::TryParse($doneRecord.timestamp, [ref]$doneTimestamp)) {
      Add-Failure -Failures $failures -Code 'done_certification.timestamp_invalid' -Message 'Done certification timestamp must be parseable.'
    }
    if (($doneRecord.certifier -isnot [string]) -or ($doneRecord.certifier -ne 'Codex Desktop autonomous release manager')) {
      Add-Failure -Failures $failures -Code 'done_certification.certifier_invalid' -Message 'Done certification certifier is invalid.'
    }
    if (($doneRecord.final_decision -isnot [string]) -or (@('done', 'done_with_non_blocking_notes') -notcontains $doneRecord.final_decision)) {
      Add-Failure -Failures $failures -Code 'done_certification.final_decision_invalid' -Message 'A pass-authorizing done certification must use done or done_with_non_blocking_notes.'
    }
    if (-not (Test-IsStringArray -Value $doneRecord.evidence_paths) -or @($doneRecord.evidence_paths).Count -lt 1) {
      Add-Failure -Failures $failures -Code 'done_certification.evidence_paths_invalid' -Message 'Done certification evidence_paths must be a non-empty string array.'
    } else {
      foreach ($path in @($doneRecord.evidence_paths)) {
        if ($manifestVerifiedPaths -notcontains $path) {
          Add-Failure -Failures $failures -Code 'done_certification.evidence_not_manifested' -Message "Done certification evidence '$path' is absent from the verified evidence manifest."
        }
      }
    }
    if ($doneRecord.completion_gates -is [hashtable]) {
      Validate-ExactKeys -Object $doneRecord.completion_gates -RequiredKeys @($completionRequirements.Keys) -OptionalKeys @() -Context 'done_certification.completion_gates' -Failures $failures
    } else {
      Add-Failure -Failures $failures -Code 'done_certification.completion_gates_invalid' -Message 'Done certification completion_gates must be an object.'
    }
    if ($doneRecord.bindings -is [hashtable]) {
      Validate-ExactKeys -Object $doneRecord.bindings -RequiredKeys @('qa_record_path', 'test_run_record_path', 'evidence_manifest_path') -OptionalKeys @() -Context 'done_certification.bindings' -Failures $failures
    } else {
      Add-Failure -Failures $failures -Code 'done_certification.bindings_invalid' -Message 'Done certification bindings must be an object.'
    }
    if ($doneRecord.ContainsKey('completion_gates') -and ($doneRecord.completion_gates -is [hashtable])) {
      foreach ($key in @($completionRequirements.Keys)) {
        if ((@('implementation_finished', 'exact_artifact_test_qa_bindings') -notcontains $key) -and
          $doneRecord.completion_gates.ContainsKey($key) -and
          ($doneRecord.completion_gates[$key] -is [bool]) -and
          [bool]$doneRecord.completion_gates[$key]) {
          $completionRequirements[$key] = $true
        }
      }
    }
    $completionRequirements.exact_artifact_test_qa_bindings = $false
    if ($doneRecord.ContainsKey('artifact_id') -and
      ($doneRecord.artifact_id -eq $request.artifact_id) -and
      $doneRecord.ContainsKey('bindings') -and
      ($doneRecord.bindings -is [hashtable]) -and
      $bindingResults.ContainsKey('qa_record') -and
      $bindingResults.ContainsKey('test_run_record') -and
      $bindingResults.ContainsKey('evidence_manifest') -and
      $null -ne $bindingResults.qa_record -and
      $null -ne $bindingResults.test_run_record -and
      $null -ne $bindingResults.evidence_manifest) {
      if (($bindingResults.qa_record.relative_path -eq [string]$doneRecord.bindings.qa_record_path) -and
        ($bindingResults.test_run_record.relative_path -eq [string]$doneRecord.bindings.test_run_record_path) -and
        ($bindingResults.evidence_manifest.relative_path -eq [string]$doneRecord.bindings.evidence_manifest_path)) {
        $completionRequirements.exact_artifact_test_qa_bindings = $true
      }
    }
  }
}

$gates.qa_record_required = (($qaRecord -is [hashtable]) -and (@($failures.Where({ $_.code -like 'qa_record*' })).Count -eq 0))
$gates.test_run_required = (($testRecord -is [hashtable]) -and (@($failures.Where({ $_.code -like 'test_run_record*' })).Count -eq 0))
$gates.evidence_path_required = (($manifestRecord -is [hashtable]) -and (@($failures.Where({ $_.code -like 'evidence_manifest*' })).Count -eq 0) -and $manifestVerifiedPaths.Count -gt 0)
$gates.blocker_policy_required = (($blockerRecord -is [hashtable]) -and (@($failures.Where({ $_.code -like 'blocker_record*' })).Count -eq 0))
$gates.tracker_item_linkage = (($trackerRecord -is [hashtable]) -and ($itemRecord -is [hashtable]) -and (@($failures.Where({ $_.code -like 'tracker_item*' })).Count -eq 0))

$completionRequirements.relevant_test_run_performed = $gates.test_run_required
$completionRequirements.qa_record_created = $gates.qa_record_required
$completionRequirements.artifact_inspection_completed = ($qaRecord -is [hashtable] -and $qaRecord.inspection_status -eq 'completed')
$completionRequirements.tracker_updated = ($trackerRecord -is [hashtable] -and $trackerRecord.status -eq 'complete' -and $trackerRecord.final_decision -eq 'pass')
$completionRequirements.item_updated = ($itemRecord -is [hashtable] -and $itemRecord.status -eq 'complete' -and $itemRecord.final_decision -eq 'pass')
$completionRequirements.known_issues_reviewed = ($qaRecord -is [hashtable] -and ($qaRecord.known_issues -is [System.Collections.IEnumerable]) -and ($qaRecord.known_issues -isnot [string]))
$completionRequirements.evidence_manifest_created = $gates.evidence_path_required
$completionRequirements.implementation_finished = ($implementationScopeVerified -and $gates.test_run_required -and $gates.qa_record_required)

$passQAStatuses = @('pass', 'pass_with_non_blocking_issues')
if ($requestedStatus -eq 'failed') {
  Add-Failure -Failures $failures -Code 'lifecycle.requested_failed' -Message 'A failed lifecycle cannot authorize pass.'
} elseif ($requestedStatus -ne 'complete') {
  Add-Blocker -Blockers $blockers -Code 'lifecycle.not_pass_ready' -Message "Lifecycle status '$requestedStatus' is not pass-ready."
}
if ($qaStatus -eq 'fail') {
  Add-Failure -Failures $failures -Code 'qa_record.reported_failure' -Message 'QA record reports failure.'
} elseif ($passQAStatuses -notcontains $qaStatus) {
  Add-Blocker -Blockers $blockers -Code 'qa_record.not_pass_ready' -Message "QA status '$qaStatus' is not pass-ready."
}
if ($testResult -eq 'fail') {
  Add-Failure -Failures $failures -Code 'test_run_record.reported_failure' -Message 'Test run record reports failure.'
} elseif ($testResult -ne 'pass') {
  Add-Blocker -Blockers $blockers -Code 'test_run_record.not_pass_ready' -Message "Test result '$testResult' is not pass-ready."
}

$candidatePass = ($failures.Count -eq 0 -and $blockers.Count -eq 0 -and -not $qualityOrTestFailurePresent)
if ($candidatePass) {
  if (-not $donePresent) {
    Add-Failure -Failures $failures -Code 'done_certification.required_for_pass' -Message 'Done certification is required for pass/complete outcomes.'
  } else {
    $doneGatePassed = (@($completionRequirements.Values.Where({ -not $_ })).Count -eq 0)
    if (-not $doneGatePassed) {
      Add-Failure -Failures $failures -Code 'done_certification.incomplete' -Message 'Done certification does not satisfy required completion gates.'
    }
  }
} else {
  if ($donePresent) {
    Add-Failure -Failures $failures -Code 'done_certification.forbidden_non_pass' -Message 'Done certification is forbidden as authoritative for blocked/fail outcomes.'
  }
}
$gates.done_certification_gate = $doneGatePassed

$hasUnresolvedBlockers = ($blockers.Count -gt 0)
$hasFailures = ($failures.Count -gt 0)
$hasQualityOrTestFailure = $qualityOrTestFailurePresent -or ($testRecord -is [hashtable] -and ($testRecord.result -eq 'fail')) -or ($qaRecord -is [hashtable] -and ($qaRecord.qa_status -eq 'fail'))

$finalDecision = 'pass'
if ($hasQualityOrTestFailure -or $hasFailures) {
  $finalDecision = 'fail'
} elseif ($hasUnresolvedBlockers -or ($requestedStatus -eq 'blocked') -or ($qaStatus -eq 'blocked') -or ($testResult -eq 'blocked')) {
  $finalDecision = 'blocked'
}
if ($finalDecision -eq 'pass' -and -not $gates.done_certification_gate) {
  $finalDecision = 'fail'
}

$productionEligibility = ($finalDecision -eq 'pass')
$certificationEligibility = ($finalDecision -eq 'pass' -and $gates.done_certification_gate)

$result = [ordered]@{
  source = [ordered]@{
    request_path = $requestResolved.relative
    output_path = $outputResolved.relative
    canonical_root = $canonicalRoot
    physical_root = $physicalRoot
  }
  identity = [ordered]@{
    tracker_id = $request.tracker_id
    item_id = $request.item_id
    artifact_id = $request.artifact_id
    intended_lifecycle_status = $request.intended_lifecycle_status
    protocol_acknowledgement = [ordered]@{
      protocol_path = $request.protocol_acknowledgement.protocol_path
      protocol_sha256 = $request.protocol_acknowledgement.protocol_sha256
      reviewer_role = $request.protocol_acknowledgement.reviewer_role
      expected_protocol_path = $protocolPath
      expected_protocol_sha256 = $protocolHash
      expected_reviewer_role = $requiredReviewerRole
    }
  }
  binding_validation = [ordered]@{
    required_bindings = @('qa_record', 'test_run_record', 'evidence_manifest', 'blocker_record', 'tracker_record', 'item_record')
    optional_bindings = @('failure_record', 'retest_record', 'attempt_history_record', 'done_certification_record')
    verified = @($bindingResults.Values | ForEach-Object { $_ })
  }
  gate_results = $gates
  protocol_failure_retest_derivation = [ordered]@{
    requested_status = $requestedStatus
    qa_status = $qaStatus
    test_result = $testResult
    failure_retest_required = $needsFailureRetest
    supported_failure_classes = $supportedFailureClasses
  }
  blocker_array = @($blockers)
  failure_array = @($failures)
  completion_requirements = $completionRequirements
  production_eligibility = $productionEligibility
  certification_eligibility = $certificationEligibility
  final_decision = $finalDecision
  exit_coupling = [ordered]@{
    pass_exit_code = 0
    blocked_or_fail_exit_code = 2
    operational_exit_code = 1
    selected_exit_code = $(if ($finalDecision -eq 'pass') { 0 } else { 2 })
  }
}

$outputDirectory = Split-Path -Parent $outputResolved.physical
if (-not [string]::IsNullOrWhiteSpace($outputDirectory)) {
  $null = New-Item -ItemType Directory -Path $outputDirectory -Force
}
$tempOutput = '{0}.{1}.tmp' -f $outputResolved.physical, ([System.Guid]::NewGuid().ToString('N'))
$json = $result | ConvertTo-Json -Depth 100
Set-Content -LiteralPath $tempOutput -Value $json -Encoding UTF8
Move-Item -LiteralPath $tempOutput -Destination $outputResolved.physical -Force

if ($finalDecision -eq 'pass') {
  exit 0
}
exit 2
