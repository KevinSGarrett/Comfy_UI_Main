[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath '..\..\..\..'))
$runtimeRoot = Join-Path -Path $projectRoot -ChildPath 'runtime_artifacts/strict_qa_master_protocol_harness'
$canonicalRoot = $projectRoot
$evaluatorPath = Join-Path -Path $projectRoot -ChildPath 'Plan/Instructions/QA/Scripts/Test-StrictAutonomousQAMasterProtocolConformance.ps1'
$doneHelperPath = Join-Path -Path $projectRoot -ChildPath 'Plan/Instructions/QA/Scripts/New-DoneCertification.ps1'
$imageQAHelperPath = Join-Path -Path $projectRoot -ChildPath 'Plan/Instructions/QA/Scripts/New-ImageArtifactQARecord.ps1'
$protocolPathRel = 'Plan/Instructions/QA/STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md'
$protocolPathPhysical = Join-Path -Path $projectRoot -ChildPath $protocolPathRel
$protocolSha = (Get-FileHash -LiteralPath $protocolPathPhysical -Algorithm SHA256).Hash.ToLowerInvariant()
$requiredBlockerPolicy = 'No unresolved blockers may be marked pass; unresolved blockers force blocked; quality/test failures force fail; suppressed failures forbidden.'
$childPowerShell = (Get-Process -Id $PID).Path

function Assert-ContainedPath {
  param(
    [string]$Path,
    [string]$Root
  )
  $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
  $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
  if ($fullPath -ne $fullRoot -and -not $fullPath.StartsWith("$fullRoot$([System.IO.Path]::DirectorySeparatorChar)", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path '$Path' is not contained under '$Root'."
  }
}

function Remove-DirectorySafe {
  param([string]$Path)
  if (Test-Path -LiteralPath $Path) {
    Assert-ContainedPath -Path $Path -Root $runtimeRoot
    Remove-Item -LiteralPath $Path -Recurse -Force
  }
}

function To-RepoRelative {
  param([string]$Path)
  $fullPath = [System.IO.Path]::GetFullPath($Path)
  $fullRoot = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\', '/')
  if (-not $fullPath.StartsWith($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path '$Path' is outside project root."
  }
  return $fullPath.Substring($fullRoot.Length).TrimStart('\', '/') -replace '\\', '/'
}

function New-Binding {
  param([string]$Path)
  $item = Get-Item -LiteralPath $Path
  return [ordered]@{
    path = (To-RepoRelative -Path $item.FullName)
    sha256 = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    bytes = [int64]$item.Length
  }
}

function Write-JsonFile {
  param(
    [string]$Path,
    [System.Collections.IDictionary]$Data
  )
  $dir = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($dir)) {
    $null = New-Item -ItemType Directory -Path $dir -Force
  }
  $Data | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $Path -Encoding UTF8
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

function Read-JsonHashtable {
  param([string]$Path)
  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  return (ConvertTo-HashtableRecursive -InputObject ($raw | ConvertFrom-Json))
}

function New-BaseCase {
  param([string]$CaseDir)
  $filesDir = Join-Path -Path $CaseDir -ChildPath 'files'
  $recordsDir = Join-Path -Path $CaseDir -ChildPath 'records'
  $null = New-Item -ItemType Directory -Path $filesDir -Force
  $null = New-Item -ItemType Directory -Path $recordsDir -Force

  $artifactFile = Join-Path -Path $filesDir -ChildPath 'artifact.bin'
  $logFile = Join-Path -Path $filesDir -ChildPath 'run.log'
  Set-Content -LiteralPath $artifactFile -Value 'artifact bytes' -Encoding ASCII
  Set-Content -LiteralPath $logFile -Value 'log lines' -Encoding ASCII

  $artifactBinding = New-Binding -Path $artifactFile
  $logBinding = New-Binding -Path $logFile
  $evidencePaths = @($artifactBinding.path, $logBinding.path)

  $qaRecordPath = Join-Path -Path $recordsDir -ChildPath 'qa_record.json'
  $testRecordPath = Join-Path -Path $recordsDir -ChildPath 'test_run_record.json'
  $manifestPath = Join-Path -Path $recordsDir -ChildPath 'evidence_manifest.json'
  $blockerPath = Join-Path -Path $recordsDir -ChildPath 'blocker_record.json'
  $trackerPath = Join-Path -Path $recordsDir -ChildPath 'tracker_record.json'
  $itemPath = Join-Path -Path $recordsDir -ChildPath 'item_record.json'
  $failurePath = Join-Path -Path $recordsDir -ChildPath 'failure_record.json'
  $retestPath = Join-Path -Path $recordsDir -ChildPath 'retest_record.json'
  $attemptHistoryPath = Join-Path -Path $recordsDir -ChildPath 'attempt_history_record.json'
  $donePath = Join-Path -Path $recordsDir -ChildPath 'done_certification.json'

  $qaRecord = [ordered]@{
    artifact_id = 'ART-W64-035'
    artifact_type = 'script'
    task_id = 'ITEM-W64-035'
    tracker_id = 'TRK-W64-035'
    reviewer = 'Codex Desktop autonomous QA'
    test_method = 'deterministic_child_process_validation'
    qa_status = 'pass'
    evidence_paths = $evidencePaths
    known_issues = @()
    next_action = 'none'
    timestamp = '2026-07-12T03:15:48-05:00'
    review_modalities = @('static_analysis', 'execution_trace')
    severity_findings = [ordered]@{
      s0 = 0
      s1 = 0
      s2 = 0
      s3 = 0
      s4 = 0
    }
    inspection_status = 'completed'
    scores = [ordered]@{}
    defects = @()
  }
  Write-JsonFile -Path $qaRecordPath -Data $qaRecord

  $testRecord = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    command = 'powershell.exe -NoProfile -File Plan/Instructions/QA/Scripts/test_strict_autonomous_qa_master_protocol_conformance.ps1'
    exit_code = 0
    result = 'pass'
    expected_summary = 'all assertions pass'
    actual_summary = 'all assertions pass'
    logs = @($logBinding.path)
    evidence_bindings = @($artifactBinding, $logBinding)
  }
  Write-JsonFile -Path $testRecordPath -Data $testRecord

  $manifest = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    evidence = @($artifactBinding, $logBinding)
  }
  Write-JsonFile -Path $manifestPath -Data $manifest

  $blockerRecord = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    blocker_policy = $requiredBlockerPolicy
    unresolved_blockers = @()
    classification = 'clear'
    status = 'clear'
    suppressed_failures = @()
    quality_failures = @()
    test_failures = @()
  }
  Write-JsonFile -Path $blockerPath -Data $blockerRecord

  $trackerRecord = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    status = 'complete'
    final_decision = 'pass'
    evidence_paths = $evidencePaths
  }
  Write-JsonFile -Path $trackerPath -Data $trackerRecord

  $itemRecord = [ordered]@{
    item_id = 'ITEM-W64-035'
    tracker_id = 'TRK-W64-035'
    artifact_id = 'ART-W64-035'
    status = 'complete'
    final_decision = 'pass'
    evidence_paths = $evidencePaths
  }
  Write-JsonFile -Path $itemPath -Data $itemRecord

  $failureRecord = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    failure_class = 'artifact_quality'
    severity = 'S2'
    suspected_cause = 'baseline'
    attempt_number = 1
    similar_to_previous = $false
    material_change = $true
    new_direction_evidence = 'initial'
    deeper_diagnosis_performed = $true
  }
  Write-JsonFile -Path $failurePath -Data $failureRecord

  $retestRecord = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    attempt_number = 1
    intended_fix = 'baseline'
    expected_result = 'pass'
    material_change = $true
    new_direction_evidence = 'initial'
    result = 'pass'
  }
  Write-JsonFile -Path $retestPath -Data $retestRecord

  $attemptHistoryRecord = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    attempts = @([ordered]@{
        attempt_number = 1
        failure_class = 'artifact_quality'
        result = 'pass'
        material_change = $true
        new_direction_evidence = 'initial'
        deeper_diagnosis_performed = $true
      })
  }
  Write-JsonFile -Path $attemptHistoryPath -Data $attemptHistoryRecord

  & $doneHelperPath `
    -TaskId 'ITEM-W64-035' `
    -TrackerId 'TRK-W64-035' `
    -ArtifactId 'ART-W64-035' `
    -Title 'Strict autonomous QA master protocol fixture' `
    -ArtifactScope $artifactBinding.path `
    -ImplementationSummary 'Deterministic conformance fixture complete.' `
    -TestsPerformed @('strict conformance harness') `
    -QASummary 'Fixture QA passed.' `
    -EvidencePaths $evidencePaths `
    -FinalDecision 'done' `
    -QARecordPath (To-RepoRelative -Path $qaRecordPath) `
    -TestRunRecordPath (To-RepoRelative -Path $testRecordPath) `
    -EvidenceManifestPath (To-RepoRelative -Path $manifestPath) `
    -ImplementationFinished `
    -RelevantTestRunPerformed `
    -QARecordCreated `
    -ArtifactInspectionCompleted `
    -TrackerUpdated `
    -ItemUpdated `
    -KnownIssuesReviewed `
    -EvidenceManifestCreated `
    -ExactArtifactTestQABindings `
    -OutFile $donePath *> $null

  $request = [ordered]@{
    tracker_id = 'TRK-W64-035'
    item_id = 'ITEM-W64-035'
    artifact_id = 'ART-W64-035'
    intended_lifecycle_status = 'complete'
    protocol_acknowledgement = [ordered]@{
      protocol_path = $protocolPathRel
      protocol_sha256 = $protocolSha
      reviewer_role = 'Codex Desktop autonomous QA'
    }
    bindings = [ordered]@{
      qa_record = New-Binding -Path $qaRecordPath
      test_run_record = New-Binding -Path $testRecordPath
      evidence_manifest = New-Binding -Path $manifestPath
      blocker_record = New-Binding -Path $blockerPath
      tracker_record = New-Binding -Path $trackerPath
      item_record = New-Binding -Path $itemPath
      done_certification_record = New-Binding -Path $donePath
    }
  }

  return [ordered]@{
    request = $request
    files = [ordered]@{
      qa_record = $qaRecordPath
      test_run_record = $testRecordPath
      evidence_manifest = $manifestPath
      blocker_record = $blockerPath
      tracker_record = $trackerPath
      item_record = $itemPath
      failure_record = $failurePath
      retest_record = $retestPath
      attempt_history_record = $attemptHistoryPath
      done_certification_record = $donePath
      artifact = $artifactFile
      log = $logFile
    }
  }
}

function Update-RequestBindings {
  param(
    [System.Collections.IDictionary]$BaseCase,
    [System.Collections.IDictionary]$Request
  )
  foreach ($name in @('qa_record', 'test_run_record', 'evidence_manifest', 'blocker_record', 'tracker_record', 'item_record')) {
    $Request.bindings[$name] = New-Binding -Path $BaseCase.files[$name]
  }
  foreach ($optional in @('failure_record', 'retest_record', 'attempt_history_record', 'done_certification_record')) {
    if ($Request.bindings.Contains($optional)) {
      $Request.bindings[$optional] = New-Binding -Path $BaseCase.files[$optional]
    }
  }
}

function Add-FailureRetestBindings {
  param(
    [System.Collections.IDictionary]$BaseCase,
    [System.Collections.IDictionary]$Request
  )
  $Request.bindings.failure_record = New-Binding -Path $BaseCase.files.failure_record
  $Request.bindings.retest_record = New-Binding -Path $BaseCase.files.retest_record
  $Request.bindings.attempt_history_record = New-Binding -Path $BaseCase.files.attempt_history_record
}

function Run-Case {
  param(
    [string]$Name,
    [scriptblock]$Mutate,
    [scriptblock]$PostBindMutate = {},
    [int]$ExpectedExitCode,
    [string]$ExpectedDecision,
    [string[]]$ExpectedFailureCodes = @(),
    [string[]]$ExpectedBlockerCodes = @(),
    [string[]]$ForbiddenBlockerCodes = @()
  )
  $caseDir = Join-Path -Path $runtimeRoot -ChildPath $Name
  Remove-DirectorySafe -Path $caseDir
  $null = New-Item -ItemType Directory -Path $caseDir -Force

  $base = New-BaseCase -CaseDir $caseDir
  $request = $base.request
  & $Mutate $base $request
  Update-RequestBindings -BaseCase $base -Request $request
  & $PostBindMutate $base $request

  $requestPath = Join-Path -Path $caseDir -ChildPath 'request.json'
  $outputPath = Join-Path -Path $caseDir -ChildPath 'output.json'
  Write-JsonFile -Path $requestPath -Data $request

  & $childPowerShell -NoProfile -File $evaluatorPath -RequestPath (To-RepoRelative -Path $requestPath) -OutputPath (To-RepoRelative -Path $outputPath)
  $actualExit = $LASTEXITCODE

  $pass = $true
  $notes = @()
  if ($actualExit -ne $ExpectedExitCode) {
    $pass = $false
    $notes += "expected exit $ExpectedExitCode got $actualExit"
  }
  if ($ExpectedExitCode -ne 1 -and (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
    try {
      $result = Read-JsonHashtable -Path $outputPath
      if ($ExpectedDecision -and ($result.final_decision -ne $ExpectedDecision)) {
        $pass = $false
        $notes += "expected decision $ExpectedDecision got $($result.final_decision)"
      }
      if ($result.exit_coupling.selected_exit_code -ne $actualExit) {
        $pass = $false
        $notes += "report selected exit $($result.exit_coupling.selected_exit_code) differs from process exit $actualExit"
      }
      $actualFailureCodes = @($result.failure_array | ForEach-Object { $_.code })
      $actualBlockerCodes = @($result.blocker_array | ForEach-Object { $_.code })
      foreach ($code in $ExpectedFailureCodes) {
        if ($actualFailureCodes -notcontains $code) {
          $pass = $false
          $notes += "missing expected failure code $code"
        }
      }
      foreach ($code in $ExpectedBlockerCodes) {
        if ($actualBlockerCodes -notcontains $code) {
          $pass = $false
          $notes += "missing expected blocker code $code"
        }
      }
      foreach ($code in $ForbiddenBlockerCodes) {
        if ($actualBlockerCodes -contains $code) {
          $pass = $false
          $notes += "unexpected forbidden blocker code $code"
        }
      }
    } catch {
      $pass = $false
      $notes += 'unable to parse output JSON'
    }
  } elseif ($ExpectedExitCode -ne 1) {
    $pass = $false
    $notes += 'expected output JSON was not written'
  }

  return [ordered]@{
    name = $Name
    pass = $pass
    notes = $notes -join '; '
    expected_exit = $ExpectedExitCode
    actual_exit = $actualExit
  }
}

Remove-DirectorySafe -Path $runtimeRoot
$null = New-Item -ItemType Directory -Path $runtimeRoot -Force

$results = New-Object System.Collections.Generic.List[object]

$results.Add((Run-Case -Name '01_pass_complete' -ExpectedExitCode 0 -ExpectedDecision 'pass' -Mutate {
      param($base, $request)
    }))

$results.Add((Run-Case -Name '02_blocked_unresolved' -ExpectedExitCode 2 -ExpectedDecision 'blocked' -ExpectedBlockerCodes @('unresolved_blocker') -Mutate {
      param($base, $request)
      $blocker = Read-JsonHashtable -Path $base.files.blocker_record
      $blocker.unresolved_blockers = @([ordered]@{ code = 'BLK-1'; reason = 'dependency missing'; status = 'open' })
      $blocker.classification = 'blocked'
      $blocker.status = 'blocked'
      Write-JsonFile -Path $base.files.blocker_record -Data $blocker
      $request.intended_lifecycle_status = 'blocked'
      $request.bindings.Remove('done_certification_record')
    }))

$results.Add((Run-Case -Name '03_protocol_hash_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('protocol_ack.hash_mismatch') -Mutate {
      param($base, $request)
      $request.protocol_acknowledgement.protocol_sha256 = ('0' * 64)
    }))

$results.Add((Run-Case -Name '04_protocol_path_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('protocol_ack.path_mismatch') -Mutate {
      param($base, $request)
      $request.protocol_acknowledgement.protocol_path = 'Plan/Instructions/QA/WRONG.md'
    }))

$results.Add((Run-Case -Name '05_protocol_role_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('protocol_ack.role_mismatch') -Mutate {
      param($base, $request)
      $request.protocol_acknowledgement.reviewer_role = 'Another role'
    }))

$results.Add((Run-Case -Name '06_binding_missing_file' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('bindings.qa_record.missing') -Mutate {
      param($base, $request)
    } -PostBindMutate {
      param($base, $request)
      Remove-Item -LiteralPath $base.files.qa_record -Force
    }))

$results.Add((Run-Case -Name '07_binding_sha_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('bindings.qa_record.sha_mismatch') -Mutate {
      param($base, $request)
    } -PostBindMutate {
      param($base, $request)
      $request.bindings.qa_record.sha256 = ('a' * 64)
    }))

$results.Add((Run-Case -Name '08_binding_bytes_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('bindings.qa_record.bytes_mismatch') -Mutate {
      param($base, $request)
    } -PostBindMutate {
      param($base, $request)
      $request.bindings.qa_record.bytes = 99999
    }))

$results.Add((Run-Case -Name '09_binding_escape_path' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('bindings.qa_record.path_escape') -Mutate {
      param($base, $request)
    } -PostBindMutate {
      param($base, $request)
      $request.bindings.qa_record.path = '../outside.json'
    }))

$results.Add((Run-Case -Name '10_unknown_request_key' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('request.unknown_key') -Mutate {
      param($base, $request)
      $request['unknown_key'] = 'x'
    }))

$results.Add((Run-Case -Name '11_missing_request_key' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('request.missing_key') -Mutate {
      param($base, $request)
      $request.Remove('artifact_id')
    }))

$results.Add((Run-Case -Name '12_wrong_typed_request_value' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('request.item_id.type') -Mutate {
      param($base, $request)
      $request.item_id = @('bad')
    }))

$results.Add((Run-Case -Name '13_qa_identity_defect' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('qa_record.identity_mismatch') -Mutate {
      param($base, $request)
      $qa = Read-JsonHashtable -Path $base.files.qa_record
      $qa.artifact_id = 'WRONG'
      Write-JsonFile -Path $base.files.qa_record -Data $qa
    }))

$results.Add((Run-Case -Name '14_qa_reviewer_defect' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('qa_record.reviewer_invalid') -Mutate {
      param($base, $request)
      $qa = Read-JsonHashtable -Path $base.files.qa_record
      $qa.reviewer = 'Bad reviewer'
      Write-JsonFile -Path $base.files.qa_record -Data $qa
    }))

$results.Add((Run-Case -Name '15_qa_inspection_defect' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('qa_record.inspection_status_invalid') -Mutate {
      param($base, $request)
      $qa = Read-JsonHashtable -Path $base.files.qa_record
      $qa.inspection_status = 'nope'
      Write-JsonFile -Path $base.files.qa_record -Data $qa
    }))

$results.Add((Run-Case -Name '16_test_command_missing' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('test_run_record.command_invalid') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.command = ''
      Write-JsonFile -Path $base.files.test_run_record -Data $record
    }))

$results.Add((Run-Case -Name '17_test_exit_type_wrong' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('test_run_record.exit_code_invalid') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.exit_code = 'zero'
      Write-JsonFile -Path $base.files.test_run_record -Data $record
    }))

$results.Add((Run-Case -Name '18_test_result_fail' -ExpectedExitCode 2 -ExpectedDecision 'fail' -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.result = 'fail'
      Write-JsonFile -Path $base.files.test_run_record -Data $record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $retest.result = 'fail'
      Write-JsonFile -Path $base.files.retest_record -Data $retest
      $history = Read-JsonHashtable -Path $base.files.attempt_history_record
      $history.attempts[0].result = 'fail'
      Write-JsonFile -Path $base.files.attempt_history_record -Data $history
      $request.intended_lifecycle_status = 'fail'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
    }))

$results.Add((Run-Case -Name '19_manifest_empty_evidence' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('evidence_manifest.empty') -Mutate {
      param($base, $request)
      $manifest = Read-JsonHashtable -Path $base.files.evidence_manifest
      $manifest.evidence = @()
      Write-JsonFile -Path $base.files.evidence_manifest -Data $manifest
    }))

$results.Add((Run-Case -Name '20_blocker_suppressed_failure' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('blocker_record.suppressed_failures_present') -Mutate {
      param($base, $request)
      $blocker = Read-JsonHashtable -Path $base.files.blocker_record
      $blocker.suppressed_failures = @('hidden')
      Write-JsonFile -Path $base.files.blocker_record -Data $blocker
    }))

$results.Add((Run-Case -Name '21_blocker_quality_failure' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('blocker_record.quality_failures_present') -Mutate {
      param($base, $request)
      $blocker = Read-JsonHashtable -Path $base.files.blocker_record
      $blocker.quality_failures = @('blur')
      Write-JsonFile -Path $base.files.blocker_record -Data $blocker
    }))

$results.Add((Run-Case -Name '22_tracker_item_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('tracker_item.identity_mismatch') -Mutate {
      param($base, $request)
      $tracker = Read-JsonHashtable -Path $base.files.tracker_record
      $tracker.item_id = 'ITEM-W64-999'
      Write-JsonFile -Path $base.files.tracker_record -Data $tracker
    }))

$results.Add((Run-Case -Name '23_done_missing_on_pass' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('done_certification.required_for_pass') -Mutate {
      param($base, $request)
      $request.bindings.Remove('done_certification_record')
    }))

$results.Add((Run-Case -Name '24_done_present_on_blocked' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('done_certification.forbidden_non_pass') -ExpectedBlockerCodes @('unresolved_blocker') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'blocked'
      $blocker = Read-JsonHashtable -Path $base.files.blocker_record
      $blocker.unresolved_blockers = @([ordered]@{ code = 'BLK-2'; reason = 'blocked path'; status = 'open' })
      $blocker.classification = 'blocked'
      $blocker.status = 'blocked'
      Write-JsonFile -Path $base.files.blocker_record -Data $blocker
    }))

$results.Add((Run-Case -Name '25_done_unmanifested_implementation_scope' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('done_certification.artifact_scope_not_manifested') -Mutate {
      param($base, $request)
      $done = Read-JsonHashtable -Path $base.files.done_certification_record
      $done.artifact_scope = @('runtime_artifacts/not-manifested.bin')
      Write-JsonFile -Path $base.files.done_certification_record -Data $done
    }))

$results.Add((Run-Case -Name '26_done_wrong_binding' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('done_certification.incomplete') -Mutate {
      param($base, $request)
      $done = Read-JsonHashtable -Path $base.files.done_certification_record
      $done.bindings.qa_record_path = 'runtime_artifacts/wrong.json'
      Write-JsonFile -Path $base.files.done_certification_record -Data $done
    }))

$results.Add((Run-Case -Name '27_failure_class_invalid' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('failure_record.failure_class_invalid') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $failure.failure_class = 'unsupported_class'
      Write-JsonFile -Path $base.files.failure_record -Data $failure
    }))

$results.Add((Run-Case -Name '28_retest_attempt_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('retest_record.attempt_mismatch') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = 2
      $retest.attempt_number = 1
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
    }))

$results.Add((Run-Case -Name '29_third_attempt_without_diagnosis' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('failure_record.deeper_diagnosis_required') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = 3
      $failure.deeper_diagnosis_performed = $false
      $failure.material_change = $true
      $retest.attempt_number = 3
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
    }))

$results.Add((Run-Case -Name '30_fourth_attempt_blocked' -ExpectedExitCode 2 -ExpectedDecision 'blocked' -ExpectedBlockerCodes @('failure_record.redesign_block') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = 4
      $failure.deeper_diagnosis_performed = $true
      $failure.material_change = $true
      $failure.new_direction_evidence = ''
      $retest.attempt_number = 4
      $retest.result = 'needs_retest'
      $retest.new_direction_evidence = ''
      $history = Read-JsonHashtable -Path $base.files.attempt_history_record
      $history.attempts = @(
        [ordered]@{ attempt_number = 1; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-1'; deeper_diagnosis_performed = $false },
        [ordered]@{ attempt_number = 2; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-2'; deeper_diagnosis_performed = $false },
        [ordered]@{ attempt_number = 3; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-3'; deeper_diagnosis_performed = $true },
        [ordered]@{ attempt_number = 4; failure_class = 'artifact_quality'; result = 'needs_retest'; material_change = $true; new_direction_evidence = ''; deeper_diagnosis_performed = $true }
      )
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
      Write-JsonFile -Path $base.files.attempt_history_record -Data $history
    }))

$results.Add((Run-Case -Name '31_test_identity_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('test_run_record.identity_mismatch') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.tracker_id = 'TRK-W64-999'
      Write-JsonFile -Path $base.files.test_run_record -Data $record
    }))

$results.Add((Run-Case -Name '32_manifest_identity_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('evidence_manifest.identity_mismatch') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.evidence_manifest
      $record.artifact_id = 'ART-W64-999'
      Write-JsonFile -Path $base.files.evidence_manifest -Data $record
    }))

$results.Add((Run-Case -Name '33_blocker_identity_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('blocker_record.identity_mismatch') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.blocker_record
      $record.item_id = 'ITEM-W64-999'
      Write-JsonFile -Path $base.files.blocker_record -Data $record
    }))

$results.Add((Run-Case -Name '34_test_evidence_hash_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('test_run_record.evidence_bindings_invalid') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.evidence_bindings[0].sha256 = ('b' * 64)
      Write-JsonFile -Path $base.files.test_run_record -Data $record
    }))

$results.Add((Run-Case -Name '35_test_log_not_bound' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('test_run_record.log_not_bound') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.logs = @((To-RepoRelative -Path $base.files.qa_record))
      Write-JsonFile -Path $base.files.test_run_record -Data $record
    }))

$results.Add((Run-Case -Name '36_attempt_history_required' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('attempt_history_record.required') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      $request.bindings.failure_record = New-Binding -Path $base.files.failure_record
      $request.bindings.retest_record = New-Binding -Path $base.files.retest_record
      $request.bindings.Remove('done_certification_record')
    }))

$results.Add((Run-Case -Name '37_attempt_history_sequence_gap' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('attempt_history_record.sequence_gap') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = 2
      $retest.attempt_number = 2
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
    }))

& {
  $caseName = '38_image_qa_helper_schema'
  $caseDir = Join-Path -Path $runtimeRoot -ChildPath $caseName
  Remove-DirectorySafe -Path $caseDir
  $null = New-Item -ItemType Directory -Path $caseDir -Force
  $recordPath = Join-Path -Path $caseDir -ChildPath 'image_qa_record.json'
  $checklistPath = Join-Path -Path $caseDir -ChildPath 'image_qa_checklist.md'
  & $imageQAHelperPath -TaskId 'ITEM-W64-035' -TrackerId 'TRK-W64-035' -ArtifactId 'ART-W64-035-IMAGE' -OutFile $recordPath -ChecklistOutFile $checklistPath -DryRun *> $null
  $record = Read-JsonHashtable -Path $recordPath
  $required = @('artifact_id', 'artifact_type', 'task_id', 'tracker_id', 'reviewer', 'test_method', 'qa_status', 'evidence_paths', 'known_issues', 'next_action', 'timestamp', 'review_modalities', 'severity_findings', 'inspection_status')
  $optional = @('scores', 'defects', 'evidence_id', 'workflow_reference', 'prompt_reference', 'model_context', 'image', 'visual_runtime_ready', 'final_decision_allowed')
  $missing = @($required | Where-Object { -not $record.ContainsKey($_) })
  $unknown = @($record.Keys | Where-Object { @($required + $optional) -notcontains $_ })
  $schemaPass = ($missing.Count -eq 0 -and $unknown.Count -eq 0 -and $record.inspection_status -eq 'not_started')
  $results.Add([ordered]@{
      name = $caseName
      pass = $schemaPass
      notes = $(if ($schemaPass) { '' } else { "missing=$($missing -join ',') unknown=$($unknown -join ',') inspection=$($record.inspection_status)" })
      expected_exit = 0
      actual_exit = $(if ($schemaPass) { 0 } else { 1 })
  })
}

$results.Add((Run-Case -Name '39_qa_status_unknown' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('qa_record.qa_status_invalid') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.qa_record
      $record.qa_status = 'invented_status'
      Write-JsonFile -Path $base.files.qa_record -Data $record
    }))

$results.Add((Run-Case -Name '40_qa_pending_blocks' -ExpectedExitCode 2 -ExpectedDecision 'blocked' -ExpectedBlockerCodes @('qa_record.not_pass_ready') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.qa_record
      $record.qa_status = 'pending_validation'
      $record.inspection_status = 'partial'
      Write-JsonFile -Path $base.files.qa_record -Data $record
      $request.bindings.Remove('done_certification_record')
    }))

$results.Add((Run-Case -Name '41_test_pass_nonzero' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('test_run_record.pass_exit_mismatch') -Mutate {
      param($base, $request)
      $record = Read-JsonHashtable -Path $base.files.test_run_record
      $record.exit_code = 1
      Write-JsonFile -Path $base.files.test_run_record -Data $record
    }))

$results.Add((Run-Case -Name '42_tracker_incomplete' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('done_certification.incomplete') -Mutate {
      param($base, $request)
      $tracker = Read-JsonHashtable -Path $base.files.tracker_record
      $item = Read-JsonHashtable -Path $base.files.item_record
      $tracker.status = 'in_progress'
      $tracker.final_decision = 'pending'
      $item.status = 'in_progress'
      $item.final_decision = 'pending'
      Write-JsonFile -Path $base.files.tracker_record -Data $tracker
      Write-JsonFile -Path $base.files.item_record -Data $item
    }))

$results.Add((Run-Case -Name '43_lifecycle_in_progress' -ExpectedExitCode 2 -ExpectedDecision 'blocked' -ExpectedBlockerCodes @('lifecycle.not_pass_ready') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'in_progress'
      $request.bindings.Remove('done_certification_record')
    }))

$results.Add((Run-Case -Name '44_attempt_history_current_mismatch' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('attempt_history_record.current_attempt_mismatch') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $history = Read-JsonHashtable -Path $base.files.attempt_history_record
      $history.attempts[0].new_direction_evidence = 'does-not-match'
      Write-JsonFile -Path $base.files.attempt_history_record -Data $history
    }))

& {
  $caseName = '45_request_root_array'
  $caseDir = Join-Path -Path $runtimeRoot -ChildPath $caseName
  Remove-DirectorySafe -Path $caseDir
  $null = New-Item -ItemType Directory -Path $caseDir -Force
  $requestPath = Join-Path -Path $caseDir -ChildPath 'request.json'
  $outputPath = Join-Path -Path $caseDir -ChildPath 'output.json'
  Set-Content -LiteralPath $requestPath -Value '[1,2]' -Encoding UTF8
  & $childPowerShell -NoProfile -File $evaluatorPath -RequestPath (To-RepoRelative -Path $requestPath) -OutputPath (To-RepoRelative -Path $outputPath)
  $actual = $LASTEXITCODE
  $record = if (Test-Path -LiteralPath $outputPath) { Read-JsonHashtable -Path $outputPath } else { $null }
  $codes = if ($null -ne $record) { @($record.failure_array | ForEach-Object { $_.code }) } else { @() }
  $casePass = ($actual -eq 2 -and $codes -contains 'request.root_type')
  $results.Add([ordered]@{
      name = $caseName
      pass = $casePass
      notes = $(if ($casePass) { '' } else { "expected exit 2 and request.root_type; exit=$actual codes=$($codes -join ',')" })
      expected_exit = 2
      actual_exit = $actual
  })
}

$results.Add((Run-Case -Name '46_attempt_number_overflow' -ExpectedExitCode 2 -ExpectedDecision 'fail' -ExpectedFailureCodes @('failure_record.attempt_number_invalid') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = [double]1e20
      $retest.attempt_number = [double]1e20
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
    }))

$results.Add((Run-Case -Name '47_repeated_new_direction_blocked' -ExpectedExitCode 2 -ExpectedDecision 'blocked' -ExpectedBlockerCodes @('failure_record.repeated_direction_block', 'failure_record.new_direction_evidence_unverified') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = 4
      $failure.deeper_diagnosis_performed = $true
      $failure.new_direction_evidence = ' Direction-2!!! '
      $retest.attempt_number = 4
      $retest.result = 'needs_retest'
      $retest.new_direction_evidence = ' Direction-2!!! '
      $history = Read-JsonHashtable -Path $base.files.attempt_history_record
      $history.attempts = @(
        [ordered]@{ attempt_number = 1; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-1'; deeper_diagnosis_performed = $false },
        [ordered]@{ attempt_number = 2; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-2'; deeper_diagnosis_performed = $false },
        [ordered]@{ attempt_number = 3; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-3'; deeper_diagnosis_performed = $true },
        [ordered]@{ attempt_number = 4; failure_class = 'artifact_quality'; result = 'needs_retest'; material_change = $true; new_direction_evidence = ' Direction-2!!! '; deeper_diagnosis_performed = $true }
      )
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
      Write-JsonFile -Path $base.files.attempt_history_record -Data $history
    }))

$results.Add((Run-Case -Name '48_verified_new_direction_allowed' -ExpectedExitCode 2 -ExpectedDecision 'blocked' -ExpectedBlockerCodes @('lifecycle.not_pass_ready') -ForbiddenBlockerCodes @('failure_record.redesign_block', 'failure_record.repeated_direction_block', 'failure_record.new_direction_evidence_unverified') -Mutate {
      param($base, $request)
      $request.intended_lifecycle_status = 'needs_retest'
      Add-FailureRetestBindings -BaseCase $base -Request $request
      $request.bindings.Remove('done_certification_record')
      $directionEvidence = To-RepoRelative -Path $base.files.artifact
      $failure = Read-JsonHashtable -Path $base.files.failure_record
      $retest = Read-JsonHashtable -Path $base.files.retest_record
      $failure.attempt_number = 4
      $failure.deeper_diagnosis_performed = $true
      $failure.new_direction_evidence = $directionEvidence
      $retest.attempt_number = 4
      $retest.result = 'needs_retest'
      $retest.new_direction_evidence = $directionEvidence
      $history = Read-JsonHashtable -Path $base.files.attempt_history_record
      $history.attempts = @(
        [ordered]@{ attempt_number = 1; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-1'; deeper_diagnosis_performed = $false },
        [ordered]@{ attempt_number = 2; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-2'; deeper_diagnosis_performed = $false },
        [ordered]@{ attempt_number = 3; failure_class = 'artifact_quality'; result = 'fail'; material_change = $true; new_direction_evidence = 'direction-3'; deeper_diagnosis_performed = $true },
        [ordered]@{ attempt_number = 4; failure_class = 'artifact_quality'; result = 'needs_retest'; material_change = $true; new_direction_evidence = $directionEvidence; deeper_diagnosis_performed = $true }
      )
      Write-JsonFile -Path $base.files.failure_record -Data $failure
      Write-JsonFile -Path $base.files.retest_record -Data $retest
      Write-JsonFile -Path $base.files.attempt_history_record -Data $history
    }))

& {
  $caseName = '49_path_escape_request'
  $caseDir = Join-Path -Path $runtimeRoot -ChildPath $caseName
  Remove-DirectorySafe -Path $caseDir
  $null = New-Item -ItemType Directory -Path $caseDir -Force
  $outputPath = Join-Path -Path $caseDir -ChildPath 'output.json'
  & $childPowerShell -NoProfile -File $evaluatorPath -RequestPath '../../escape/request.json' -OutputPath (To-RepoRelative -Path $outputPath)
  $actual = $LASTEXITCODE
  $results.Add([ordered]@{
      name = $caseName
      pass = ($actual -eq 1)
      notes = $(if ($actual -eq 1) { '' } else { "expected exit 1 got $actual" })
      expected_exit = 1
      actual_exit = $actual
    })
}

& {
  $caseName = '50_output_collision'
  $caseDir = Join-Path -Path $runtimeRoot -ChildPath $caseName
  Remove-DirectorySafe -Path $caseDir
  $null = New-Item -ItemType Directory -Path $caseDir -Force
  $base = New-BaseCase -CaseDir $caseDir
  $request = $base.request
  Update-RequestBindings -BaseCase $base -Request $request
  $requestPath = Join-Path -Path $caseDir -ChildPath 'request.json'
  $outputPath = Join-Path -Path $caseDir -ChildPath 'output.json'
  Write-JsonFile -Path $requestPath -Data $request
  Set-Content -LiteralPath $outputPath -Value '{}' -Encoding UTF8
  & $childPowerShell -NoProfile -File $evaluatorPath -RequestPath (To-RepoRelative -Path $requestPath) -OutputPath (To-RepoRelative -Path $outputPath)
  $actual = $LASTEXITCODE
  $results.Add([ordered]@{
      name = $caseName
      pass = ($actual -eq 1)
      notes = $(if ($actual -eq 1) { '' } else { "expected exit 1 got $actual" })
      expected_exit = 1
      actual_exit = $actual
    })
}

$total = $results.Count
$failed = @($results | Where-Object { -not $_.pass })
$passed = $total - $failed.Count
Write-Host ("Conformance Harness: {0} passed / {1} total / {2} failed" -f $passed, $total, $failed.Count)
if ($failed.Count -gt 0) {
  foreach ($failure in $failed) {
    Write-Host ("FAIL {0}: {1}" -f $failure.name, $failure.notes)
  }
  exit 1
}
exit 0
