[CmdletBinding(SupportsShouldProcess=$true)]
param(
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [ValidateRange(1,168)][int]$PendingReviewTtlHours=24,
  [switch]$Apply
)

$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
$worktreeRoot=Join-Path $root 'worktrees'
$cutoff=[DateTimeOffset]::Now.AddHours(-$PendingReviewTtlHours)
$actions=@()
$lock=Join-Path $root 'locks\lifecycle.lock'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $lock)|Out-Null
if(-not(Enter-AIWorkerFileLock -Path $lock -StaleMinutes 30)){[ordered]@{status='IDLE';classification='AI_WORKER_LIFECYCLE_ALREADY_RUNNING';actions=@()}|ConvertTo-Json;return}
try {
  foreach($recordPath in @(Get-ChildItem (Join-Path $root 'completed') -Filter dispatch_record.json -File -Recurse -ErrorAction SilentlyContinue)){
    try {
      $record=Read-AIWorkerSignedJson -Path $recordPath.FullName -DispatcherRoot $root
      if(-not$record.worktree_retained_for_codex_review){continue}
      $final=[DateTimeOffset]$record.finalized_at
      $reviewed=$record.adoption_status-in@('ADOPTED','PARTIALLY_ADOPTED','REJECTED')
      if(-not$reviewed-and$final-ge$cutoff){continue}
      $path=[IO.Path]::GetFullPath([string]$record.isolated_worktree_path)
      if(-not$path.StartsWith($worktreeRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe retained worktree: $path"}
      $exists=Test-Path -LiteralPath $path;$removed=$false
      if($Apply-and$exists-and$PSCmdlet.ShouldProcess($path,'Remove reviewed or expired worker worktree')){
        &git.exe -C ([string]$record.project_root) worktree remove --force $path|Out-Null;$removed=$LASTEXITCODE-eq0
      }
      if($Apply-and$removed){$record.worktree_retained_for_codex_review=$false;$record.worktree_removed_at=(Get-Date).ToString('o');Write-AIWorkerSignedJson -Path $recordPath.FullName -Value $record -DispatcherRoot $root|Out-Null}
      $actions+=[ordered]@{request_id=$record.request_id;worktree=$path;reason=$(if($reviewed){'review_finalized'}else{'review_ttl_expired'});exists=$exists;removed=$removed}
    } catch {$actions+=[ordered]@{record=$recordPath.FullName;issue=$_.Exception.Message;removed=$false}}
  }
} finally {Remove-Item $lock -Force -ErrorAction SilentlyContinue}
[ordered]@{status=$(if(@($actions|Where-Object{$_.issue}).Count){'FAIL'}else{'PASS'});classification=$(if($Apply){'AI_WORKER_WORKTREE_LIFECYCLE_APPLIED'}else{'AI_WORKER_WORKTREE_LIFECYCLE_DRY_RUN'});cutoff=$cutoff.ToString('o');actions=$actions}|ConvertTo-Json -Depth 8
