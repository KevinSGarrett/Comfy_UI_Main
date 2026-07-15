[CmdletBinding()]
param()
$ErrorActionPreference='Stop';$temp=Join-Path $env:TEMP('ai-worker-qualification-'+[guid]::NewGuid().ToString('N'));$root=Join-Path $temp 'dispatcher'
try{
  &(Join-Path $PSScriptRoot 'Initialize-AIWorkerDispatcherSecurity.ps1') -DispatcherRoot $root -Apply|Out-Null
  Import-Module(Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1')-Force -DisableNameChecking
  $now=[DateTimeOffset]::Now
  for($i=1;$i-le25;$i++){
    $intent="intent_$i";$event=[ordered]@{schema_version=1;artifact_type='ai_worker_admission_decision';status='FINALIZED';finalized_at=$now.AddMinutes(-$i).ToString('o');intent_id=$intent;task_name="task_$i";route=$(if($i%3-eq0){'CLAUDE_SONNET_PRIMARY_REQUIRED'}else{'CURSOR_FIRST_REQUIRED'});authority_reason='';eligible_for_worker=$true;estimated_codex_minutes=6;request_ids=@("request_$i");quality_profile='balanced_default';risk_class='medium'};Write-AIWorkerSignedJson -Path(Join-Path $root "admission\events\$intent.json") -Value $event -DispatcherRoot $root|Out-Null
    $dir=Join-Path $root "completed\request_$i";$record=[ordered]@{schema_version=2;artifact_type='ai_worker_dispatch_record';request_id="request_$i";started_at=$now.AddMinutes(-$i).ToString('o');finalized_at=$now.AddMinutes(-$i).AddSeconds(10).ToString('o');duration_ms=10000;status='PASS';classification='AI_WORKER_DISPATCH_COMPLETED_AWAITING_CODEX';worker_classification=$(if($i%3-eq0){'CLAUDE_SONNET_HANDOFF_COMPLETED'}else{'CURSOR_HANDOFF_COMPLETED'});worker_lane=$(if($i%3-eq0){'Claude'}else{'Cursor'});operation='read_only';risk_class='medium';quality_profile='balanced_default';attempt=1;issues=@();outside_allowed_paths=@();adoption_status='ADOPTED';adoption_percent=100;residual_defects=@()};Write-AIWorkerSignedJson -Path(Join-Path $dir 'dispatch_record.json') -Value $record -DispatcherRoot $root|Out-Null
    $request=[ordered]@{artifact_type='ai_worker_dispatch_request';created_at=$now.AddMinutes(-$i).AddSeconds(-2).ToString('o')};Write-AIWorkerSignedJson -Path(Join-Path $dir 'request.json') -Value $request -DispatcherRoot $root|Out-Null
  }
  New-Item -ItemType Directory -Force -Path(Join-Path $root 'measurements')|Out-Null
  foreach($type in @('five_hour','five_hour','twenty_four_hour_weekly_rate','twenty_four_hour_weekly_rate')){$id=[guid]::NewGuid().ToString('N');$m=[ordered]@{artifact_type='codex_usage_window_measurement';window_type=$type;ended_at=$now.ToString('o');target_met=$true};Write-AIWorkerSignedJson -Path(Join-Path $root "measurements\$id.json") -Value $m -DispatcherRoot $root|Out-Null}
  $result=&(Join-Path $PSScriptRoot 'Measure-AIWorkerQualification.ps1') -DispatcherRoot $root|ConvertFrom-Json
  $checks=[ordered]@{qualified=($result.status-eq'QUALIFIED');automatic_denominator=($result.population.eligible_work-eq25-and$result.checks.eligible_worker_routing_percent.actual-eq100);quality_gate=($result.quality.unresolved_critical_defects-eq0);performance_measured=($result.performance.first_pass_success_percent-eq100)}
  $failed=@($checks.GetEnumerator()|Where-Object{-not$_.Value}|ForEach-Object{$_.Key});[ordered]@{status=$(if($failed.Count){'FAIL'}else{'PASS'});classification='AI_WORKER_QUALIFICATION_REGRESSION';checks=$checks;failed=$failed;qualification=$(if($failed.Count){$result}else{$null})}|ConvertTo-Json -Depth 12;if($failed.Count){exit 1}
}finally{Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue}
