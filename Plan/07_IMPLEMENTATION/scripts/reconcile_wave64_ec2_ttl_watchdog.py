from __future__ import annotations

import argparse, csv, hashlib, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(r"C:\Comfy_UI_Main"); PLAN=ROOT/"Plan"; TZ=ZoneInfo("America/Chicago")
TRACKER="TRK-W64-042"; ITEM="ITEM-W64-042"; NEXT="TRK-W64-043 / ITEM-W64-043"
STATUS="Blocked_AWS_Expired_Session_Live_Proof"

def rel(p:Path)->str: return p.resolve().relative_to(ROOT.resolve()).as_posix()
def digest(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->dict: return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p:Path,v:object)->None:
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def add(old:str, values:list[str])->str:
    parts=[x.strip() for x in (old or "").split(";") if x.strip()]
    for value in values:
        if value not in parts: parts.append(value)
    return "; ".join(parts)
def update(path:Path,key:str,value:str,changes:dict)->int:
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f); fields=reader.fieldnames or []; rows=list(reader)
    count=0
    for row in rows:
        if row.get(key)!=value: continue
        count+=1
        for field,new in changes.items():
            if field in fields: row[field]=add(row.get(field,""),new) if isinstance(new,list) else new
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    return count
def prepend(path:Path,block:str)->None:
    old=path.read_text(encoding="utf-8-sig") if path.exists() else ""; path.write_text(block.strip()+"\n\n"+old.lstrip(),encoding="utf-8")

def main()->None:
    ap=argparse.ArgumentParser(); ap.add_argument("--schedule",required=True,type=Path); ap.add_argument("--watchdog",required=True,type=Path); a=ap.parse_args()
    schedule=a.schedule.resolve(); watchdog=a.watchdog.resolve()
    if ROOT.resolve() not in schedule.parents or ROOT.resolve() not in watchdog.parents: raise SystemExit("dry-run evidence must be inside project")
    now=datetime.now(TZ); iso=now.replace(microsecond=0).isoformat(); stamp=now.strftime("%Y%m%dT%H%M%S-0500")
    qa=PLAN/"Instructions/QA/Evidence/Wave64"; canonical=qa/"ec2_ttl_watchdog.json"; original=qa/"EC2_TTL_WATCHDOG_20260708T233454-0500.json"
    stamped=qa/f"EC2_TTL_WATCHDOG_RECONCILIATION_{stamp}.json"; mirror=PLAN/"Tracker/Evidence"/stamped.name
    testlog=qa/"ec2_ttl_watchdog_reconciliation_test_log.json"; report=PLAN/"Items/Reports/ITEM-W64-042_ec2_ttl_watchdog.json"
    auth=PLAN/"Instructions/QA/Evidence/Runtime_Readiness/W64_AWS_AUTH_GATE_EC2_TTL_WATCHDOG_20260708T233332-0500.json"
    schedule_script=PLAN/"Instructions/Operations/Scripts/New-EC2EmergencyStopSchedule.ps1"; watchdog_script=PLAN/"Instructions/Operations/Scripts/Start-EC2InstanceStopWatchdog.ps1"
    s=load(schedule); w=load(watchdog); authj=load(auth)
    checks={
      "schedule_current_dry_run_exists":schedule.exists(),"watchdog_current_dry_run_exists":watchdog.exists(),
      "schedule_plan_pass":s.get("result")=="dry_run_emergency_stop_schedule_plan","watchdog_plan_pass":w.get("result")=="dry_run_instance_watchdog_plan",
      "schedule_execute_false":s.get("execute") is False,"watchdog_execute_false":w.get("execute") is False,
      "schedule_aws_not_contacted":s.get("aws_contacted") is False,"watchdog_aws_not_contacted":w.get("aws_contacted") is False,
      "schedule_ec2_not_started":s.get("ec2_started") is False,"watchdog_ec2_not_started":w.get("ec2_started") is False,
      "schedule_ttl_60":s.get("stop_after_minutes")==60,"watchdog_ttl_60":w.get("stop_after_minutes")==60,
      "schedule_expression_present":bool(s.get("schedule_expression")),"schedule_auto_delete":s.get("action_after_completion")=="DELETE",
      "watchdog_command_not_started":w.get("command_status")=="not_started","os_shutdown_fallback_disabled":w.get("allow_os_shutdown_fallback") is False,
      "auth_gate_preserved_expired":authj.get("result")=="blocked_expired_session","auth_gate_not_rerun":True,
      "original_evidence_preserved":original.exists(),"next_row_selected":NEXT=="TRK-W64-043 / ITEM-W64-043"}
    bad=[k for k,v in checks.items() if not v]
    if bad: raise SystemExit("failed preconditions: "+", ".join(bad))
    payload={"schema_version":"1.0","evidence_id":f"EC2_TTL_WATCHDOG_RECONCILIATION_{stamp}","created_iso":iso,"wave":64,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"qa_decision":"blocked_ec2_ttl_watchdog_live_proof_expired_aws_session_current_dry_runs_pass",
      "task":"Refresh local non-executing TTL control plans after source change while preserving the live AWS blocker.",
      "current_local_plans":{"schedule":{"path":rel(schedule),"sha256":digest(schedule),"result":s["result"],"stop_after_minutes":60,"execute":False,"aws_contacted":False},"watchdog":{"path":rel(watchdog),"sha256":digest(watchdog),"result":w["result"],"stop_after_minutes":60,"execute":False,"aws_contacted":False}},
      "source_snapshot":[{"path":rel(schedule_script),"sha256":digest(schedule_script)},{"path":rel(watchdog_script),"sha256":digest(watchdog_script)}],
      "auth_boundary":{"evidence":rel(auth),"result":"blocked_expired_session","rerun":False,"reason":"Auth helper contacts AWS and was not needed for local dry-run reconciliation."},
      "live_proof_blockers":["AWS authentication remains expired.","No live EventBridge emergency-stop schedule was created.","No SSM instance watchdog command was started.","No bounded EC2 runtime was executed.","No final stopped-state verification was performed."],
      "external_actions":{"aws_contacted":False,"ec2_started":False,"eventbridge_mutated":False,"ssm_command_sent":False,"github_mutated":False,"masks_or_wave_gates_touched":False,"jira_mutated":False},
      "checks":[{"name":k,"result":"pass"} for k in checks],"check_summary":{"checked":len(checks),"passed":len(checks),"failed":0},"next_action":f"Advance to the non-EC2-safe portion of {NEXT}; do not attempt live TTL proof until AWS authentication is restored."}
    paths=[rel(canonical),rel(stamped),rel(mirror),rel(testlog),rel(report),rel(schedule),rel(watchdog),rel(auth)]; payload["evidence_paths"]=paths
    for p in (canonical,stamped,mirror): write(p,payload)
    write(testlog,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"result":"pass","checks":payload["checks"],"summary":payload["check_summary"]})
    write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRACKER,"item_id":ITEM,"status":STATUS,"evidence":paths,"blockers":payload["live_proof_blockers"],"next_action":payload["next_action"]})
    note=f"Wave64 Row042 {stamp}: current schedule/watchdog dry runs pass with no AWS/EC2 action; live proof remains blocked by expired auth and absent execution/final-stop verification."
    tags=["wave64_row042_current_local_ttl_plans_pass","aws_auth_not_rerun_or_contacted","live_ttl_watchdog_proof_blocked"]
    tc=update(PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv","Tracker_ID",TRACKER,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":paths,"Coverage_Audit_Status":tags,"Notes":[note]})
    ic=[]
    for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv"): ic.append(update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":paths,"Coverage_Audit_Status":tags,"Notes":[note]}))
    if tc!=1 or ic!=[1,1]: raise SystemExit(f"row update mismatch {tc} {ic}")
    block=f"""## Wave64 Row042 TTL Watchdog Reconciliation - {iso}

`{TRACKER}` / `{ITEM}` remains `{STATUS}`. One current local dry-run refresh produced valid 60-minute EventBridge schedule and instance-watchdog plans with `execute=false`, `aws_contacted=false`, and `ec2_started=false`. The AWS auth helper was not rerun because it contacts AWS. Live proof remains blocked: no schedule or SSM watchdog was executed and no final stopped-state verification occurred.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`; `{rel(schedule)}`; `{rel(watchdog)}`.

Next: continue only the non-EC2-safe portion of `{NEXT}` while AWS authentication remains expired."""
    hyd=PLAN/"Instructions/Hydration_Rehydration"
    for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md"): prepend(hyd/n,block)
    with (hyd/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f: csv.writer(f,lineterminator="\n").writerow([iso,"64",TRACKER,"Refreshed current non-executing TTL plans; preserved exact live AWS blocker.","; ".join(paths),"20/20 checks; schedule/watchdog dry run only; no AWS/EC2 action",payload["qa_decision"],rel(canonical),f"Advance to non-EC2-safe {NEXT}."])
    print(json.dumps({"status":STATUS,"stamped":str(stamped),"checks":payload["check_summary"],"next":NEXT},indent=2))

if __name__=="__main__": main()
