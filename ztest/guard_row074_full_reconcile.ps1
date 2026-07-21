# Exclusive Row074 library-PCM guardian: poll, safe-resume on death, stamp HOLD on coverage_complete.
# Does not start 076/077. CSV deferred. Max 2 commits on finalize (stamp + helper if needed).

$ErrorActionPreference = 'Continue'
$Root = 'C:\Comfy_UI_Main'
$Runtime = Join-Path $Root 'runtime_artifacts\multi_event_segmentation\row074_index_retained_20260720'
$ProgressPath = Join-Path $Runtime 'progress.json'
$ReceiptPath = Join-Path $Runtime 'retained_index_segment_receipt.json'
$OwnerPath = Join-Path $Runtime 'FULL_RECONCILE_OWNER.txt'
$GuardianState = Join-Path $Runtime 'guardian_poll_state.json'
$StampScript = Join-Path $Root 'ztest\stamp_row074_coverage_complete.py'
$Python = 'C:\Users\kevin\AppData\Local\Programs\Python\Python311\python.exe'
$ResumeArgs = @(
  'Plan/07_IMPLEMENTATION/scripts/segment_wave64_multi_event_audio.py',
  '--mode', 'index-retained',
  '--resume',
  '--retained-runtime-dir', 'runtime_artifacts/multi_event_segmentation/row074_index_retained_20260720'
)
$PollSeconds = 120
$MaxIdleStalls = 8  # ~16 min with no progress while process alive -> still wait; death triggers resume
$KnownPid = 40256

function Write-GuardianState([hashtable]$State) {
  $State['updated_at'] = (Get-Date).ToUniversalTime().ToString('o')
  $json = ($State | ConvertTo-Json -Depth 6)
  $utf8NoBom = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($GuardianState, $json + "`n", $utf8NoBom)
}

function Get-Progress {
  if (-not (Test-Path $ProgressPath)) { return $null }
  return (Get-Content $ProgressPath -Raw | ConvertFrom-Json)
}

function Find-Row074Process {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'segment_wave64_multi_event_audio\.py' -and $_.CommandLine -match 'row074_index_retained_20260720' }
}

function Assert-No076077 {
  $bad = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'row076|row077' }
  if ($bad) {
    Write-Host "REFUSING: competing 076/077 process(es) present"
    $bad | ForEach-Object { Write-Host "  $($_.ProcessId)" }
    return $false
  }
  return $true
}

function Start-SafeResume([int]$PriorPid) {
  if (-not (Assert-No076077)) { return $null }
  $existing = Find-Row074Process
  if ($existing) {
    Write-Host "RESUME_SKIP already_alive pid=$($existing.ProcessId)"
    return [int]$existing.ProcessId
  }
  $p = Get-Progress
  if ($p -and $p.complete -eq $true -and $p.counts.records_processed -ge 39771) {
    Write-Host 'RESUME_SKIP already_coverage_complete'
    return $null
  }
  "owner=segment_wave64_multi_event_audio.py`nprior_dead_pid=$PriorPid`nresumed=$(Get-Date -Format o)`nguardian=guard_row074_full_reconcile.ps1" |
    Set-Content -Path $OwnerPath -Encoding UTF8
  $stdout = Join-Path $Runtime 'full_reconcile_stdout.log'
  $stderr = Join-Path $Runtime 'full_reconcile_stderr.log'
  $proc = Start-Process -FilePath $Python -ArgumentList $ResumeArgs -WorkingDirectory $Root `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
  Start-Sleep -Seconds 3
  $alive = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
  if (-not $alive) {
    Write-Host "RESUME_FAILED pid=$($proc.Id)"
    return $null
  }
  Add-Content -Path $OwnerPath -Value "pid=$($proc.Id)" -Encoding UTF8
  Write-Host "RESUMED pid=$($proc.Id) from prior=$PriorPid"
  return [int]$proc.Id
}

function Invoke-HoldStampAndCommit([int]$FinalizePid) {
  Write-Host "STAMPING HOLD coverage_complete finalize_pid=$FinalizePid"
  & $Python $StampScript
  if ($LASTEXITCODE -ne 0) {
    Write-Host "STAMP_FAILED exit=$LASTEXITCODE"
    return $false
  }
  Set-Location $Root
  $stampFiles = Get-ChildItem (Join-Path $Root 'Plan\Instructions\QA\Evidence\Wave64') -Filter 'TRK-W64-074_MULTI_EVENT_SEGMENTATION_RECONCILE_PROGRESS_*.json' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $paths = @(
    'Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_MULTI_EVENT_SEGMENTATION_CURRENT_DELTA_20260719.json',
    'Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_ACCEPTED_INDEX_RETAINED_SEGMENT_SUMMARY_20260720.json',
    'Plan/Instructions/QA/Evidence/Wave64/TRK-W64-074_multi_event_segmentation.json',
    'ztest/stamp_row074_coverage_complete.py',
    'ztest/guard_row074_full_reconcile.ps1'
  )
  if ($stampFiles) { $paths += ('Plan/Instructions/QA/Evidence/Wave64/' + $stampFiles.Name) }
  git add -- @paths
  $staged = git diff --cached --name-only
  if (-not $staged) {
    Write-Host 'STAMP_COMMIT_SKIP nothing_staged'
    return $true
  }
  $msg = @"
Stamp Row074 index-retained multi-event coverage_complete (39771/39771).

Runtime PID $FinalizePid clean-exited; HOLD on thresholds/event-count calibration — no product COMPLETE; CSV deferred; do not start 076/077.
"@
  git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m $msg
  Write-Host "STAMP_COMMIT=$(git rev-parse HEAD)"
  # Optional second commit only if helper paths remain dirty and not in first commit.
  $helperDirty = git status --short -- ztest/stamp_row074_coverage_complete.py ztest/guard_row074_full_reconcile.ps1
  if ($helperDirty) {
    git add -- ztest/stamp_row074_coverage_complete.py ztest/guard_row074_full_reconcile.ps1
    git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m @"
Add Row074 coverage stamp and exclusive guardian helpers.

Supports HOLD finalize/resume without claiming product COMPLETE or starting 076/077.
"@
    Write-Host "HELPER_COMMIT=$(git rev-parse HEAD)"
  }
  return $true
}

Write-Host "=== Row074 guardian start known_pid=$KnownPid ==="
$state = @{
  mode = 'poll'
  known_pid = $KnownPid
  last_processed = 0
  stalls = 0
  resumes = 0
  coverage_complete = $false
}
$p0 = Get-Progress
if ($p0) { $state.last_processed = [int]$p0.counts.records_processed }
Write-GuardianState $state

while ($true) {
  if (-not (Assert-No076077)) {
    Write-GuardianState $state
    Start-Sleep -Seconds $PollSeconds
    continue
  }

  $progress = Get-Progress
  $proc = Find-Row074Process
  $alivePid = if ($proc) { [int]$proc.ProcessId } else { $null }
  $processed = if ($progress) { [int]$progress.counts.records_processed } else { -1 }
  $total = if ($progress) { [int]$progress.counts.records_total } else { 39771 }
  $complete = if ($progress) { [bool]$progress.complete } else { $false }
  $receiptComplete = $false
  if (Test-Path $ReceiptPath) {
    $receipt = Get-Content $ReceiptPath -Raw | ConvertFrom-Json
    $receiptComplete = [bool]$receipt.coverage_complete
  }

  Write-Host ("POLL pid={0} processed={1}/{2} complete={3} receipt_cc={4}" -f $(if ($alivePid) { $alivePid } else { 'DEAD' }), $processed, $total, $complete, $receiptComplete)

  if ($complete -and $receiptComplete -and $processed -ge $total -and -not $alivePid) {
    $state.coverage_complete = $true
    $state.mode = 'finalize'
    Write-GuardianState $state
    $ok = Invoke-HoldStampAndCommit -FinalizePid $KnownPid
    $state.mode = if ($ok) { 'done_hold_stamped' } else { 'stamp_failed' }
    Write-GuardianState $state
    Write-Host "GUARDIAN_DONE mode=$($state.mode)"
    break
  }

  if (-not $alivePid) {
    if ($complete -and $processed -ge $total) {
      # wait for receipt write
      Start-Sleep -Seconds 5
      continue
    }
    Write-Host "DEATH detected prior=$KnownPid; safe resume"
    $newPid = Start-SafeResume -PriorPid $KnownPid
    if ($newPid) {
      $KnownPid = $newPid
      $state.known_pid = $KnownPid
      $state.resumes = [int]$state.resumes + 1
      $state.stalls = 0
    }
    Write-GuardianState $state
    Start-Sleep -Seconds $PollSeconds
    continue
  }

  $KnownPid = $alivePid
  $state.known_pid = $KnownPid
  if ($processed -gt [int]$state.last_processed) {
    $state.last_processed = $processed
    $state.stalls = 0
    $state.mode = 'advancing'
  } else {
    $state.stalls = [int]$state.stalls + 1
    $state.mode = 'alive_stall_or_slow'
    if ([int]$state.stalls -ge $MaxIdleStalls) {
      Write-Host "STALL_WARN stalls=$($state.stalls) processed=$processed (process still alive; not killing)"
    }
  }
  Write-GuardianState $state
  Start-Sleep -Seconds $PollSeconds
}
