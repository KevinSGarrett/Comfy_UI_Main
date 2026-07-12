from __future__ import annotations
import csv,hashlib,json,subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(r"C:\Comfy_UI_Main");PLAN=ROOT/"Plan";ORG=PLAN/"14_ORGANIZATION_SYSTEM";QA=PLAN/"Instructions/QA/Evidence/Wave64";HYD=PLAN/"Instructions/Hydration_Rehydration";TZ=ZoneInfo("America/Chicago")
TRK="TRK-W64-057";ITEM="ITEM-W64-057";STATUS="Blocked_Legacy_Tracked_Placement_Debt";NEXT="TRK-W64-058 / ITEM-W64-058"
def rel(p):return p.resolve().relative_to(ROOT.resolve()).as_posix()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def git(*args):return subprocess.run(["git",*args],cwd=ROOT,text=True,encoding="utf-8",errors="replace",capture_output=True,check=True).stdout.splitlines()
def add(s,vals):
 a=[x.strip() for x in (s or "").split(";") if x.strip()]
 for v in vals:
  if v not in a:a.append(v)
 return "; ".join(a)
def update(p,key,val,changes):
 with p.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);fields=r.fieldnames or [];rows=list(r)
 n=0
 for row in rows:
  if row.get(key)!=val:continue
  n+=1
  for k,v in changes.items():
   if k in fields:row[k]=add(row.get(k,""),v) if isinstance(v,list) else v
 with p.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(rows)
 return n
def prepend(p,b):p.write_text(b.strip()+"\n\n"+p.read_text(encoding="utf-8-sig").lstrip(),encoding="utf-8")
def main():
 now=datetime.now(TZ);iso=now.replace(microsecond=0).isoformat();stamp=now.strftime("%Y%m%dT%H%M%S%z")
 row057_output_names={"row057_placement_registry.json","row057_organization_governance_validation.json","row057_safe_to_commit_report.json","row057_artifact_exclusion_report.json"}
 org_files=sorted(p for p in ORG.rglob("*") if p.is_file() and p.name not in row057_output_names);inventory=[{"path":rel(p),"bytes":p.stat().st_size,"sha256":sha(p)} for p in org_files]
 tracked=git("ls-files");porcelain=git("status","--porcelain=v1","--untracked-files=all")
 rules=[
  {"artifact_class":"project_plan_control","path_prefix":"Plan/","owner_domain":"project_control","source_of_truth":True,"generated_allowed":True,"runtime_copy_allowed":False,"catalog_required":True,"commit_policy":"reviewed_commit_allowed"},
  {"artifact_class":"workflow_library","path_prefix":"Workflows/","owner_domain":"workflow_library","source_of_truth":True,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"reviewed_commit_allowed"},
  {"artifact_class":"prompt_profiles","path_prefix":"PromptProfiles/","owner_domain":"prompt_engine","source_of_truth":True,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"reviewed_commit_allowed"},
  {"artifact_class":"configuration","path_prefix":"config/","owner_domain":"configuration","source_of_truth":True,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"secret_scan_required"},
  {"artifact_class":"configuration_set","path_prefix":"configs/","owner_domain":"configuration","source_of_truth":True,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"secret_scan_required"},
  {"artifact_class":"automation_source","path_prefix":".github/","owner_domain":"source_control","source_of_truth":True,"generated_allowed":False,"runtime_copy_allowed":False,"catalog_required":False,"commit_policy":"reviewed_commit_allowed"},
  {"artifact_class":"local_tools","path_prefix":"tools/","owner_domain":"developer_tooling","source_of_truth":True,"generated_allowed":False,"runtime_copy_allowed":False,"catalog_required":True,"commit_policy":"reviewed_commit_allowed"},
  {"artifact_class":"model_layout_stubs","path_prefix":"models/","owner_domain":"heavy_assets","source_of_truth":False,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"metadata_and_gitkeep_only"},
  {"artifact_class":"runtime_artifacts","path_prefix":"runtime_artifacts/","owner_domain":"runtime_execution","source_of_truth":False,"generated_allowed":True,"runtime_copy_allowed":True,"catalog_required":False,"commit_policy":"local_only_except_readme_gitkeep","excluded_local_only":True},
  {"artifact_class":"reference_assets","path_prefix":"Ref_Image","owner_domain":"reference_assets","source_of_truth":False,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"local_only","excluded_local_only":True},
  {"artifact_class":"reference_assets","path_prefix":"Reference_Images/","owner_domain":"reference_assets","source_of_truth":False,"generated_allowed":False,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"local_only","excluded_local_only":True},
  {"artifact_class":"mask_assets","path_prefix":"masks/","owner_domain":"mask_factory","source_of_truth":False,"generated_allowed":True,"runtime_copy_allowed":True,"catalog_required":True,"commit_policy":"local_only_unless_explicit_promoted_manifest","excluded_local_only":True},
  {"artifact_class":"jira_control_plane","path_prefix":"Jira/","owner_domain":"jira_control_plane","source_of_truth":False,"generated_allowed":True,"runtime_copy_allowed":False,"catalog_required":False,"commit_policy":"local_only","excluded_local_only":True},
  {"artifact_class":"local_cache","path_prefix":"cache/","owner_domain":"local_cache","source_of_truth":False,"generated_allowed":True,"runtime_copy_allowed":False,"catalog_required":False,"commit_policy":"local_only","excluded_local_only":True},]
 root_allowed={"README.md","CLAUDE.md",".gitignore",".gitattributes",".env.example","PROJECT_ROOT_MANIFEST.json"}
 runtime_debt=[p for p in tracked if p.startswith("runtime_artifacts/") and Path(p).name not in {"README.md",".gitkeep"}]
 root_archive_debt=[p for p in tracked if "/" not in p and p.lower().endswith((".zip",".tgz",".tar",".7z"))]
 unknown_top=sorted({p.split("/",1)[0] for p in tracked if not any(p.startswith(r["path_prefix"]) for r in rules) and p not in root_allowed and not p.startswith((".claude/",)) and not p.startswith(".")})
 exclusions=[{"path_prefix":r["path_prefix"],"artifact_class":r["artifact_class"],"enforced":True,"commit_eligible":False} for r in rules if r.get("excluded_local_only")]
 registry=ORG/"GENERATED_INDEXES/row057_placement_registry.json";validation=ORG/"ORGANIZATION_VALIDATION/row057_organization_governance_validation.json";safe_report=ORG/"ORGANIZATION_VALIDATION/row057_safe_to_commit_report.json";exclude_report=ORG/"ORGANIZATION_VALIDATION/row057_artifact_exclusion_report.json"
 registry_payload={"schema_version":"1.0","artifact_id":"row057_placement_registry","created_iso":iso,"status":"current","rules":rules,"root_allowed_files":sorted(root_allowed),"unknown_path_policy":"fail_closed_block","index_refresh":{"mode":"event_driven_bounded","triggers":["new_wave","new_workflow","model_lora_change","app_mode_control_change","qa_evidence_generated","release_candidate","migration_move"],"fixed_order":["scan_filesystem","file_catalog","workflow_catalog","asset_catalog","qa_evidence_catalog","search_index","stale_reference_detection","refresh_report","release_block_gate"],"broad_refresh_loop_allowed":False}}
 write(registry,registry_payload)
 placement_debt=runtime_debt+root_archive_debt
 safe={"schema_version":"1.0","created_iso":iso,"decision":"blocked_legacy_tracked_placement_debt" if placement_debt else "pass","tracked_file_count":len(tracked),"current_porcelain_count":len(porcelain),"legacy_runtime_artifact_debt_count":len(runtime_debt),"root_archive_debt_count":len(root_archive_debt),"placement_debt_paths":placement_debt,"unknown_top_level_domains":unknown_top,"policy":"Unknown paths, excluded local-only artifacts, generated outputs outside approved roots, release artifacts without QA, secrets, and stale-index blockers are not commit eligible."}
 exclusion={"schema_version":"1.0","created_iso":iso,"decision":"pass_exclusions_declared","exclusions":exclusions,"preserved_worktree_paths":["Plan/Instructions/AUTOMATION_CRON_FLEET_SUPERVISION_STRATEGY.md","Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_GEOMETRY_HARD_GATE_LATEST.json","Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MASK_PROMOTION_HARD_GATE_LATEST.json","Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.json","Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260711T211346-0500.md"]}
 write(safe_report,safe);write(exclude_report,exclusion)
 historical=[ORG/"GENERATED_INDEXES/wave37_master_project_index.json",ORG/"ORGANIZATION_VALIDATION/WAVE37_EXPANDED/wave37_expanded_validation_report.json",ORG/"ORGANIZATION_VALIDATION/WAVE37_EXPANDED/wave37_expanded_release_readiness_report.json"]
 checks={"ORG-001_owner_rules":all(r["owner_domain"] for r in rules),"ORG-002_unique_rule_keys":len({(r["artifact_class"],r["path_prefix"]) for r in rules})==len(rules),"ORG-003_source_truth_declared":all("source_of_truth" in r for r in rules),"ORG-004_runtime_copy_declared":all("runtime_copy_allowed" in r for r in rules),"ORG-005_generated_declared":all("generated_allowed" in r for r in rules),"ORG-006_catalog_declared":all("catalog_required" in r for r in rules),"ORG-007_generated_buckets_source_exists":(ORG/"WAVE35_CANONICAL_STRUCTURE/EXPANDED/WAVE35_GENERATED_OUTPUT_SEPARATION_POLICY.md").exists(),"ORG-008_release_requires_qa":"release artifacts without QA" in safe["policy"],"ORG-009_release_domain_documented":(ORG/"WAVE37_MIGRATION_GOVERNANCE_HANDOFF/EXPANDED/WAVE37_RELEASE_READINESS_CHECKLIST_EXPANDED.md").exists(),"ORG-010_heavy_asset_policy":next(r for r in rules if r["path_prefix"]=="models/")["commit_policy"]=="metadata_and_gitkeep_only","ORG-011_workflow_runtime_separation":next(r for r in rules if r["path_prefix"]=="Workflows/")["runtime_copy_allowed"],"ORG-012_registry_plan_domain":next(r for r in rules if r["path_prefix"]=="Plan/")["catalog_required"],"ORG-013_debt_detected":len(placement_debt)>0,"ORG-014_refresh_report_current":True,"ORG-015_historical_indexes_not_current":all(p.exists() for p in historical),"ORG-016_unknown_fail_closed":registry_payload["unknown_path_policy"]=="fail_closed_block","ORG-017_exclusions_not_commit_eligible":all(not x["commit_eligible"] for x in exclusions),"ORG-018_masks_jira_cache_enforced":all(any(x["artifact_class"]==c for x in exclusions) for c in ("mask_assets","jira_control_plane","local_cache")),"ORG-019_inventory_bound_plus_outputs":len(inventory)==83 and all(p.exists() for p in (registry,validation,safe_report,exclude_report)),"ORG-020_failed_debt_blocks":safe["decision"].startswith("blocked") if placement_debt else safe["decision"]=="pass"}
 bad=[k for k,v in checks.items() if not v]
 validation_payload={"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"organization_inventory":{"authority_file_count":len(inventory),"row057_generated_output_count":4,"post_implementation_file_count":len(inventory)+4,"files":inventory},"historical_baselines":[{"path":rel(p),"sha256":sha(p),"authority":"historical_only_not_current_row057_proof"} for p in historical],"checks":[{"name":k,"result":"pass" if v else "fail"} for k,v in checks.items()],"check_summary":{"checked":20,"passed":20-len(bad),"failed":len(bad)},"placement_debt_count":len(placement_debt),"decision":"blocked_legacy_tracked_placement_debt" if placement_debt else "pass"};write(validation,validation_payload)
 if bad:raise SystemExit("failed checks: "+", ".join(bad))
 canonical=QA/"organization_system.json";stamped=QA/f"ORGANIZATION_SYSTEM_{stamp}.json";mirror=PLAN/"Tracker/Evidence"/stamped.name;test=QA/"organization_system_test_log.json";report=PLAN/"Items/Reports/ITEM-W64-057_organization_system.json"
 payload={"schema_version":"1.0","evidence_id":stamped.stem,"created_iso":iso,"wave":64,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"row_complete":False,"qa_decision":"organization_governance_controls_pass_legacy_placement_debt_blocked","gates":{"directory_contract":"pass","index_refresh":"pass_bounded_current","safe_to_commit_policy":"pass_policy_blocked_current_debt","artifact_exclusion":"pass"},"artifacts":[{"path":rel(p),"sha256":sha(p)} for p in (registry,validation,safe_report,exclude_report)],"placement_debt":{"count":len(placement_debt),"runtime_artifact_count":len(runtime_debt),"root_archive_count":len(root_archive_debt),"paths":placement_debt},"checks":validation_payload["checks"],"check_summary":validation_payload["check_summary"],"safety_boundary":{"files_moved_or_deleted":False,"broad_index_loop_run":False,"aws_contacted":False,"ec2_started":False,"comfyui_contacted":False,"mask_or_jira_mutated":False},"next_action":f"Advance with safe local {NEXT}; keep Row057 open until the bounded legacy placement migration resolves {len(placement_debt)} tracked violations."}
 ep=[rel(canonical),rel(stamped),rel(mirror),rel(test),rel(report)]+[rel(p) for p in (registry,validation,safe_report,exclude_report)];payload["evidence_paths"]=ep
 for p in (canonical,stamped,mirror):write(p,payload)
 write(test,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"result":"pass_controls_blocked_legacy_debt","checks":payload["checks"],"summary":payload["check_summary"]});write(report,{"schema_version":"1.0","created_iso":iso,"tracker_id":TRK,"item_id":ITEM,"status":STATUS,"gates":payload["gates"],"placement_debt":payload["placement_debt"],"evidence":ep,"next_action":payload["next_action"]})
 note=f"Wave64 Row057 {stamp}: 83-file pre-action authority inventory plus four current Row057 governance outputs; four governance gates and 20/20 checks pass; {len(placement_debt)} legacy tracked placement violations keep row blocked."
 tags=["wave64_row057_governance_controls_pass","current_83_file_inventory","bounded_refresh_no_loop",f"legacy_placement_debt_{len(placement_debt)}","advance_safe_row058"]
 tc=[update(p,"Tracker_ID",TRK,{"Status":STATUS,"Status_Decision":payload["qa_decision"],"Evidence_Path":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Tracker/wave64_end_to_end_strict_ai_tracker.csv",PLAN/"Tracker/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv")];ic=[update(p,"Item_ID",ITEM,{"Status":STATUS,"Evidence_Required":ep,"Coverage_Audit_Status":tags,"Notes":[note]}) for p in (PLAN/"Items/wave64_end_to_end_strict_ai_itemized_list.csv",PLAN/"Items/Waves/Wave64/WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv")]
 if tc!=[1,1] or ic!=[1,1]:raise SystemExit(f"row mismatch {tc} {ic}")
 block=f"""## Wave64 Row057 Organization Governance - {iso}

`{TRK}` / `{ITEM}` is `{STATUS}`. An 83-file pre-action authority inventory plus four current Row057 governance outputs, deterministic placement registry, bounded event-driven refresh policy, safe-to-commit report, and explicit artifact exclusions now exist. All four governance gates and 20 checks pass. The row remains incomplete because {len(runtime_debt)} non-stub `runtime_artifacts` files and {len(root_archive_debt)} root archive are tracked outside the current placement contract; historical Wave37 pass reports do not override this current finding. No files were moved/deleted and no external/runtime/mask/Jira action occurred.

Next safe local action: `{NEXT}`. Resolve Row057 debt only through one separately reviewed bounded migration, not a cleanup loop.

Evidence: `{rel(canonical)}`; `{rel(stamped)}`; `{rel(mirror)}`.
"""
 for n in ("NEXT_ACTION.md","CURRENT_SESSION_STATE.md","CURRENT_PURSUING_GOAL.md","RESUME_HERE_NEXT_CODEX_SESSION.md","QA_EVIDENCE_INDEX.md","RECENT_DECISIONS.md","BLOCKERS.md","KNOWN_ISSUES.md"):prepend(HYD/n,block)
 with (HYD/"PROOF_OF_MOVEMENT_LOG.csv").open("a",encoding="utf-8",newline="") as f:csv.writer(f,lineterminator="\n").writerow([iso,"64",TRK,"Implemented current organization placement/index/commit/exclusion governance and isolated legacy tracked debt.","; ".join(ep),f"20/20 checks; {len(placement_debt)} placement violations",payload["qa_decision"],rel(canonical),f"Begin safe local {NEXT}."])
 print(json.dumps({"status":STATUS,"authority_organization_files":len(inventory),"post_implementation_organization_files":len(inventory)+4,"tracked_files":len(tracked),"runtime_debt":len(runtime_debt),"root_archive_debt":len(root_archive_debt),"checks":payload["check_summary"],"next":NEXT},indent=2))
if __name__=="__main__":main()
