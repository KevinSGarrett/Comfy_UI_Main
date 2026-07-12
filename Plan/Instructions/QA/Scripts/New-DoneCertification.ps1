[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$TaskId,
  [Parameter(Mandatory = $true)][string]$Title,
  [string]$TrackerId = '',
  [string]$ArtifactId = '',
  [string[]]$ArtifactScope = @(),
  [string]$ImplementationSummary = '',
  [string[]]$TestsPerformed = @(),
  [string]$QASummary = '',
  [string[]]$EvidencePaths = @(),
  [string[]]$KnownIssues = @(),
  [ValidateSet('done', 'done_with_non_blocking_notes', 'pending_runtime_validation', 'failed', 'blocked')]
  [string]$FinalDecision = 'pending_runtime_validation',
  [string]$QARecordPath = '',
  [string]$TestRunRecordPath = '',
  [string]$EvidenceManifestPath = '',
  [switch]$ImplementationFinished,
  [switch]$RelevantTestRunPerformed,
  [switch]$QARecordCreated,
  [switch]$ArtifactInspectionCompleted,
  [switch]$TrackerUpdated,
  [switch]$ItemUpdated,
  [switch]$KnownIssuesReviewed,
  [switch]$EvidenceManifestCreated,
  [switch]$ExactArtifactTestQABindings,
  [string]$OutFile = './done_certification.json',
  [switch]$LegacyMarkdown
)

$ErrorActionPreference = 'Stop'
$isMarkdown = $LegacyMarkdown -or ([System.IO.Path]::GetExtension($OutFile) -ieq '.md')
$timestamp = [DateTimeOffset]::Now.ToString('o')

if ($isMarkdown) {
  $content = @"
# Done Certification Template

- Certification ID: CERT-$TaskId
- Task / Tracker ID: $TaskId / $TrackerId
- Title: $Title
- Artifact Scope: $ArtifactScope
- Implementation Summary: $ImplementationSummary
- Tests Performed: $($TestsPerformed -join '; ')
- QA Summary: $QASummary
- Evidence Paths: $($EvidencePaths -join '; ')
- Known Issues: $(if ($KnownIssues.Count -eq 0) { 'none' } else { $KnownIssues -join '; ' })
- Final Decision: $FinalDecision
- Certifier: Codex Desktop autonomous release manager
- Timestamp: $timestamp
"@
  Set-Content -LiteralPath $OutFile -Value $content -Encoding UTF8
  Write-Host "Initialized legacy Markdown done certification: $OutFile"
  exit 0
}

foreach ($required in @{
    TrackerId = $TrackerId
    ArtifactId = $ArtifactId
    ImplementationSummary = $ImplementationSummary
    QASummary = $QASummary
    QARecordPath = $QARecordPath
    TestRunRecordPath = $TestRunRecordPath
    EvidenceManifestPath = $EvidenceManifestPath
}.GetEnumerator()) {
  if ([string]::IsNullOrWhiteSpace([string]$required.Value)) {
    throw "$($required.Key) is required for strict JSON done certification."
  }
}
if ($ArtifactScope.Count -lt 1) { throw 'ArtifactScope is required for strict JSON done certification.' }
if (@($ArtifactScope | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -gt 0) { throw 'ArtifactScope entries must be non-empty.' }
if ($TestsPerformed.Count -lt 1) { throw 'TestsPerformed is required for strict JSON done certification.' }
if ($EvidencePaths.Count -lt 1) { throw 'EvidencePaths is required for strict JSON done certification.' }

$record = [ordered]@{
  certification_id = "CERT-$TaskId"
  task_id = $TaskId
  tracker_id = $TrackerId
  artifact_id = $ArtifactId
  title = $Title
  artifact_scope = @($ArtifactScope)
  implementation_summary = $ImplementationSummary
  tests_performed = @($TestsPerformed)
  qa_summary = $QASummary
  evidence_paths = @($EvidencePaths)
  known_issues = @($KnownIssues)
  final_decision = $FinalDecision
  certifier = 'Codex Desktop autonomous release manager'
  timestamp = $timestamp
  completion_gates = [ordered]@{
    implementation_finished = [bool]$ImplementationFinished
    relevant_test_run_performed = [bool]$RelevantTestRunPerformed
    qa_record_created = [bool]$QARecordCreated
    artifact_inspection_completed = [bool]$ArtifactInspectionCompleted
    tracker_updated = [bool]$TrackerUpdated
    item_updated = [bool]$ItemUpdated
    known_issues_reviewed = [bool]$KnownIssuesReviewed
    evidence_manifest_created = [bool]$EvidenceManifestCreated
    exact_artifact_test_qa_bindings = [bool]$ExactArtifactTestQABindings
  }
  bindings = [ordered]@{
    qa_record_path = $QARecordPath
    test_run_record_path = $TestRunRecordPath
    evidence_manifest_path = $EvidenceManifestPath
  }
}

$parent = Split-Path -Parent $OutFile
if (-not [string]::IsNullOrWhiteSpace($parent)) {
  $null = New-Item -ItemType Directory -Path $parent -Force
}
$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Initialized strict JSON done certification: $OutFile"
