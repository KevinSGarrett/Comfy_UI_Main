[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot='C:\Users\kevin\.codex\ai_worker_dispatcher',
  [ValidateRange(1,720)][int]$LookbackHours=168,
  [string]$OutputPath=''
)

$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'AIWorkerDispatcher.Common.psm1') -Force -DisableNameChecking
$root=[IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
$cutoff=[DateTimeOffset]::Now.AddHours(-$LookbackHours)

function Read-Record {
  param([string]$Path)
  try { if(Test-Path -LiteralPath ($Path+'.sig')){return Read-AIWorkerSignedJson -Path $Path -DispatcherRoot $root};return Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json } catch { return $null }
}
function Get-Percent {param([double]$Numerator,[double]$Denominator);if($Denominator-le0){return 0.0};return [math]::Round(100.0*$Numerator/$Denominator,2)}
function Get-Percentile {param([double[]]$Values,[double]$Percentile);$ordered=@($Values|Sort-Object);if(-not$ordered.Count){return 0};$index=[math]::Ceiling(($Percentile/100.0)*$ordered.Count)-1;return [math]::Round([double]$ordered[[math]::Max(0,$index)],2)}

$records=@()
foreach($state in @('completed','dead_letter','failed')){
  foreach($path in @(Get-ChildItem -LiteralPath (Join-Path $root $state) -Filter dispatch_record.json -File -Recurse -ErrorAction SilentlyContinue)){
    $record=Read-Record $path.FullName
    if($record-and$record.artifact_type-eq'ai_worker_dispatch_record'-and[DateTimeOffset]$record.finalized_at-ge$cutoff){$record|Add-Member _record_path $path.FullName -Force;$records+=$record}
  }
}
$substantive=@($records|Where-Object{[string]$_.worker_classification-notmatch'HEALTH_PROBE|PROBE'})
$completed=@($substantive|Where-Object{$_.status-eq'PASS'})
$useful=@($completed|Where-Object{@($_.issues).Count-eq0})
$reviewed=@($completed|Where-Object{$_.adoption_status-in@('ADOPTED','PARTIALLY_ADOPTED','REJECTED')})
$adoptionPoints=0.0
foreach($record in $completed){
  if($record.PSObject.Properties.Name-contains'adoption_percent'){$adoptionPoints+=[double]$record.adoption_percent/100.0}
  elseif($record.adoption_status-eq'ADOPTED'){$adoptionPoints+=1.0}
  elseif($record.adoption_status-eq'PARTIALLY_ADOPTED'){$adoptionPoints+=0.5}
}
$scopeCompliant=@($completed|Where-Object{@($_.outside_allowed_paths).Count-eq0-and@($_.issues).Count-eq0})
$firstPass=@($completed|Where-Object{[int]$_.attempt-le1})
$criticalDefects=@($reviewed|Where-Object{$_.risk_class-eq'critical'-and@($_.residual_defects).Count-gt0})

$admission=@()
foreach($path in @(Get-ChildItem -LiteralPath (Join-Path $root 'admission\events') -Filter *.json -File -ErrorAction SilentlyContinue)){
  $event=Read-Record $path.FullName
  if($event-and$event.artifact_type-eq'ai_worker_admission_decision'-and[DateTimeOffset]$event.finalized_at-ge$cutoff){$admission+=$event}
}
$eligible=@($admission|Where-Object{$_.eligible_for_worker-eq$true})
$routed=@($eligible|Where-Object{@($_.request_ids).Count-gt0})
$unrecordedCodexEstimate=[int](@($admission|Where-Object{$_.route-eq'CODEX_ONLY_AUTHORITY'-and[string]::IsNullOrWhiteSpace([string]$_.authority_reason)}).Count)

$queueLatency=@();$cycleDuration=@()
foreach($record in $substantive){
  $requestPath=Join-Path (Split-Path -Parent $record._record_path) 'request.json';$request=Read-Record $requestPath
  if($request){$queueLatency+=([DateTimeOffset]$record.started_at-[DateTimeOffset]$request.created_at).TotalSeconds}
  if($record.duration_ms-ne$null){$cycleDuration+=[double]$record.duration_ms/1000.0}
}
$measurements=@()
foreach($path in @(Get-ChildItem -LiteralPath (Join-Path $root 'measurements') -Filter *.json -File -ErrorAction SilentlyContinue)){
  $m=Read-Record $path.FullName;if($m-and$m.artifact_type-eq'codex_usage_window_measurement'-and[DateTimeOffset]$m.ended_at-ge$cutoff){$measurements+=$m}
}
$fiveHourPasses=@($measurements|Where-Object{$_.window_type-eq'five_hour'-and$_.target_met-eq$true}).Count
$longWindowPasses=@($measurements|Where-Object{$_.window_type-eq'twenty_four_hour_weekly_rate'-and$_.target_met-eq$true}).Count

$usefulRate=Get-Percent $useful.Count $substantive.Count
$adoptionRate=Get-Percent $adoptionPoints $completed.Count
$scopeRate=Get-Percent $scopeCompliant.Count $completed.Count
$routingRate=Get-Percent $routed.Count $eligible.Count
$firstPassRate=Get-Percent $firstPass.Count $completed.Count
$deadLetterRate=Get-Percent (@($substantive|Where-Object{$_.status-ne'PASS'}).Count) $substantive.Count
$checks=[ordered]@{
  substantive_handoffs=[ordered]@{actual=$substantive.Count;required=25;pass=($substantive.Count-ge25)}
  useful_completion_percent=[ordered]@{actual=$usefulRate;required=85;pass=($usefulRate-ge85)}
  weighted_adopted_output_percent=[ordered]@{actual=$adoptionRate;required=80;pass=($adoptionRate-ge80)}
  scope_compliance_percent=[ordered]@{actual=$scopeRate;required=95;pass=($scopeRate-ge95)}
  eligible_worker_routing_percent=[ordered]@{actual=$routingRate;required=90;pass=($routingRate-ge90-and$eligible.Count-ge1)}
  first_pass_success_percent=[ordered]@{actual=$firstPassRate;required=75;pass=($firstPassRate-ge75)}
  dead_letter_percent=[ordered]@{actual=$deadLetterRate;maximum=10;pass=($deadLetterRate-le10-and$substantive.Count-ge1)}
  unresolved_critical_defects=[ordered]@{actual=$criticalDefects.Count;maximum=0;pass=($criticalDefects.Count-eq0)}
  unreasoned_codex_only_events=[ordered]@{actual=$unrecordedCodexEstimate;maximum=0;pass=($unrecordedCodexEstimate-eq0)}
  five_hour_reduction_periods=[ordered]@{actual=$fiveHourPasses;required=2;pass=($fiveHourPasses-ge2)}
  daily_or_weekly_rate_periods=[ordered]@{actual=$longWindowPasses;required=2;pass=($longWindowPasses-ge2)}
}
$allPass=@($checks.Values|Where-Object{-not$_.pass}).Count-eq0
$result=[ordered]@{
  schema_version=2;artifact_type='ai_worker_qualification_measurement';status=$(if($allPass){'QUALIFIED'}else{'NOT_YET_QUALIFIED'});confidence=$(if($allPass){'HIGH'}else{'LOW_TO_MEDIUM_UNTIL_MEASURED'});finalized_at=(Get-Date).ToString('o');lookback_hours=$LookbackHours
  population=[ordered]@{admission_events=$admission.Count;eligible_work=$eligible.Count;routed_eligible_work=$routed.Count;substantive_handoffs=$substantive.Count;completed=$completed.Count;reviewed=$reviewed.Count;dead_lettered=@($substantive|Where-Object{$_.status-ne'PASS'}).Count}
  performance=[ordered]@{queue_latency_seconds_p50=Get-Percentile $queueLatency 50;queue_latency_seconds_p95=Get-Percentile $queueLatency 95;cycle_duration_seconds_p50=Get-Percentile $cycleDuration 50;cycle_duration_seconds_p95=Get-Percentile $cycleDuration 95;first_pass_success_percent=$firstPassRate;dead_letter_percent=$deadLetterRate}
  quality=[ordered]@{weighted_adoption_percent=$adoptionRate;scope_compliance_percent=$scopeRate;unresolved_critical_defects=$criticalDefects.Count}
  checks=$checks;direct_measurement_required=$true;note='Speed, adoption, correctness, scope, and direct Codex usage reduction must all pass. Subscription utilization alone is not qualification.'
}
if($OutputPath){Write-AIWorkerSignedJson -Path $OutputPath -Value $result -DispatcherRoot $root|Out-Null}
$result|ConvertTo-Json -Depth 12
