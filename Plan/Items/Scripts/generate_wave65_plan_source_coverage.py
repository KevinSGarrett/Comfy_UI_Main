#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(r"C:\Comfy_UI_Main")
PLAN = ROOT / "Plan"
ITEMS = PLAN / "Items"
TRACKER = PLAN / "Tracker"
INSTRUCTIONS = PLAN / "Instructions"

WAVE = "65"
WAVE_NAME = "plan_source_coverage_closure"
BINARY_OR_MEDIA_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ico",
    ".zip", ".7z", ".tar", ".gz", ".pdf", ".safetensors", ".ckpt",
}

ITEM_COLUMNS = [
    "Item_ID", "Item_Wave", "Item_Type", "Item_Title", "Item_Category", "Item_Domain",
    "Owner_Domain", "Autonomous_Required", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Action", "Implementation_Target", "Deliverable_Type", "Acceptance_Criteria",
    "QA_Gates_Required", "Visual_Review_Required", "Visual_Review_Method", "Test_Required",
    "Evidence_Required", "Runtime_Proof_Required", "EC2_Allowed", "Blocker_Policy",
    "Source_Plan_Root", "Citation_File", "Citation_Full_Path", "Citation_Section",
    "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt", "Source_Package",
    "Source_Type", "Source_File_Size", "Priority", "Risk_Level", "Status", "Created_From",
    "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level", "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]

TRACKER_COLUMNS = [
    "Tracker_ID", "Wave", "Phase", "Workstream", "Priority", "Risk_Level", "Owner_Role",
    "Environment", "Status", "Task_Name", "Detailed_Action", "Completion_Criteria",
    "Acceptance_Evidence", "Dependency_Prerequisite", "Validation_Method", "Output_Artifact",
    "Source_Path", "Related_Source_Paths", "Package_Top_Level_Directory",
    "Autonomous_Execution_Mode", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Desktop_Action", "QA_Strictness", "Visual_Review_Required", "Visual_Review_Method",
    "Test_Required", "Runtime_Proof_Required", "EC2_Allowed", "Preview_Required",
    "Final_Render_Gate", "Evidence_Path", "Citation_File", "Citation_Full_Path",
    "Citation_Section", "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt",
    "Source_Package", "Source_Type", "Source_Item_ID", "Blocker_Policy", "Rerun_Policy",
    "Status_Decision", "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level",
    "Coverage_Audit_Status", "Ultra_Source_Coverage_Record",
]

OUTPUT_PATHS = [
    ITEMS / "wave65_plan_source_coverage_closure_itemized_list.csv",
    ITEMS / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_ITEM_ROWS.csv",
    ITEMS / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_REQUIREMENTS.json",
    ITEMS / "Waves" / "Wave65" / "README.md",
    ITEMS / "Reports" / "wave65_plan_source_coverage_report.json",
    TRACKER / "wave65_plan_source_coverage_closure_tracker.csv",
    TRACKER / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_TRACKER_ROWS.csv",
    TRACKER / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_REQUIREMENTS.json",
    TRACKER / "Waves" / "Wave65" / "README.md",
    TRACKER / "Reports" / "wave65_plan_source_coverage_report.json",
    INSTRUCTIONS / "Waves" / "Wave65" / "WAVE65_SCOPE.md",
    INSTRUCTIONS / "Waves" / "Wave65" / "WAVE65_ITEMIZED_LIST_SUPPLEMENT.csv",
    INSTRUCTIONS / "Waves" / "Wave65" / "WAVE65_TRACKER_SUPPLEMENT.csv",
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("/", "\\")


def norm(value: str | None) -> str:
    if not value:
        return ""
    raw = str(value).strip().strip('"').replace("/", "\\")
    lowered = raw.lower()
    marker = "\\plan\\"
    if marker in lowered:
        idx = lowered.rfind(marker)
        raw = raw[idx + 1 :]
    elif lowered.startswith("c:\\comfy_ui_main\\"):
        raw = raw[len("C:\\Comfy_UI_Main\\") :]
    return raw.lower()


def read_lines(path: Path) -> list[str]:
    if path.suffix.lower() in BINARY_OR_MEDIA_EXTENSIONS:
        return []
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def clean_citation_text(value: str) -> str:
    without_ansi = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", " ", value)
    without_control = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", without_ansi)
    return re.sub(r"\s+", " ", without_control).strip()


def citation_for(path: Path) -> dict[str, str]:
    if path.suffix.lower() in BINARY_OR_MEDIA_EXTENSIONS:
        source_type = path.suffix.lstrip(".").lower() or "file"
        file_size = path.stat().st_size if path.exists() else 0
        return {
            "Citation_File": rel(path),
            "Citation_Full_Path": str(path),
            "Citation_Section": f"{source_type.upper()} binary/media artifact",
            "Citation_Line_Start": "1",
            "Citation_Line_End": "1",
            "Citation_Excerpt": f"Binary or media Plan artifact {rel(path)} exists with size {file_size} bytes; use hash, pullback, and whole-artifact QA evidence instead of embedding raw bytes in source coverage CSV.",
            "Source_Package": str(PLAN),
            "Source_Type": source_type,
            "Source_File_Size": str(file_size),
            "Source_File_Relative": rel(path),
        }

    lines = read_lines(path)
    section = path.stem
    start = 1
    for index, line in enumerate(lines, start=1):
        stripped = clean_citation_text(line)
        if stripped.startswith("#"):
            section = re.sub(r"^#+\s*", "", stripped)[:180] or section
            start = index
            break
        if path.suffix.lower() == ".csv" and index == 1 and stripped:
            section = f"CSV header: {stripped[:140]}"
            start = 1
            break
        if path.suffix.lower() == ".json" and stripped and stripped not in ("{", "["):
            section = f"JSON root near line {index}"
            start = index
            break
        if stripped and index <= 5:
            section = stripped[:180]
            start = index
            break
    end = min(max(start + 12, start), len(lines) if lines else start)
    excerpt = clean_citation_text(" ".join(line.strip() for line in lines[start - 1 : end] if line.strip()))[:700]
    if not excerpt:
        excerpt = f"Plan source file {rel(path)} exists and requires Items/Tracker coverage."
    return {
        "Citation_File": rel(path),
        "Citation_Full_Path": str(path),
        "Citation_Section": section,
        "Citation_Line_Start": str(start),
        "Citation_Line_End": str(end),
        "Citation_Excerpt": excerpt,
        "Source_Package": str(PLAN),
        "Source_Type": path.suffix.lstrip(".").lower() or "file",
        "Source_File_Size": str(path.stat().st_size if path.exists() else 0),
        "Source_File_Relative": rel(path),
    }


def plan_files() -> list[Path]:
    candidates = {path for path in PLAN.rglob("*") if path.is_file() and is_plan_source_file(path)}
    ignored = git_ignored_paths(candidates)
    found = {path for path in candidates if norm(rel(path)) not in ignored}
    found.update(OUTPUT_PATHS)
    found.add(ITEMS / "Scripts" / "generate_wave65_plan_source_coverage.py")
    return sorted(found, key=lambda p: rel(p).lower())


def git_ignored_paths(paths: set[Path]) -> set[str]:
    if not paths:
        return set()
    repo_paths = sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in paths)
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "--stdin"],
            input="\n".join(repo_paths) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return set()
    if result.returncode not in (0, 1):
        return set()
    return {norm(line) for line in result.stdout.splitlines() if line.strip()}


def is_plan_source_file(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if "__pycache__" in lowered_parts:
        return False
    if path.suffix.lower() in {".pyc", ".pyo"}:
        return False
    return True


def coverage_csv_paths(base: Path) -> list[Path]:
    paths = []
    for path in base.rglob("*.csv"):
        lowered = str(path).lower()
        if "wave65_plan_source_coverage" in lowered or "\\wave65\\" in lowered:
            continue
        paths.append(path)
    return paths


def covered_paths_from_csv(paths: list[Path]) -> set[str]:
    covered: set[str] = set()
    source_fields = [
        "Citation_File",
        "Citation_Full_Path",
        "Source_File_Relative",
        "Source_Path",
        "Related_Source_Paths",
        "Ultra_Source_Coverage_Record",
    ]
    for path in paths:
        try:
            with path.open(newline="", encoding="utf-8-sig", errors="ignore") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    for field in source_fields:
                        value = row.get(field, "")
                        if not value:
                            continue
                        for part in str(value).replace("|", ";").split(";"):
                            cleaned = part.split("#L", 1)[0]
                            normalized = norm(cleaned)
                            if normalized.startswith("plan\\"):
                                covered.add(normalized)
        except Exception:
            continue
    return covered


def domain_for(path: Path) -> tuple[str, str, str, str, str, str, str, str]:
    relative = rel(path)
    lower = relative.lower()
    parts = path.relative_to(PLAN).parts
    top = parts[0] if parts else "Plan"
    domain = re.sub(r"[^a-z0-9]+", "_", top.lower()).strip("_") or "plan"
    category = "Plan source coverage"
    priority = "P1"
    risk = "MEDIUM"
    visual_required = "FALSE"
    visual_method = "not_applicable_source_coverage"
    review_clause = "source-driven implementation, test, QA, and evidence review"

    if "03_image_system" in lower or "image" in lower:
        category = "Image source coverage"
        priority = "P0"
        risk = "CRITICAL"
        visual_required = "TRUE"
        visual_method = "whole_image_visual_review_when_this_source_affects_generated_media"
        review_clause = "whole-image visual QA, including target and non-target regions"
    elif "04_video_gif_system" in lower or "video" in lower or "gif" in lower:
        category = "Video source coverage"
        priority = "P0"
        risk = "CRITICAL"
        visual_required = "TRUE"
        visual_method = "full_duration_video_frame_and_playback_review_when_this_source_affects_generated_media"
        review_clause = "full-duration temporal visual QA across the entire generated artifact"
    elif "05_audio_system" in lower or "audio" in lower:
        category = "Audio source coverage"
        priority = "P0"
        risk = "CRITICAL"
        visual_required = "FALSE"
        visual_method = "full_duration_audio_playback_spectrogram_and_av_sync_review_when_this_source_affects_audio"
        review_clause = "full-duration audio QA across the entire generated artifact"
    elif "06_qa_testing" in lower or "\\qa\\" in lower or "qa_" in lower:
        category = "QA source coverage"
        priority = "P0"
        risk = "CRITICAL"
        review_clause = "strict QA gate and evidence review"
    elif "instructions" in lower or "hydration_rehydration" in lower:
        category = "Instruction source coverage"
        priority = "P0"
        risk = "HIGH"
        review_clause = "autonomous instruction, no-loop, and hydration compliance review"
    elif "07_implementation" in lower or "workflow" in lower:
        category = "Implementation source coverage"
        priority = "P0"
        risk = "CRITICAL"
        review_clause = "workflow/static/runtime compatibility and evidence review"
    elif "registr" in lower or "model" in lower:
        category = "Registry source coverage"
        priority = "P0"
        risk = "HIGH"
        review_clause = "registry consistency, model hash, and cross-reference review"

    return domain, category, priority, risk, visual_required, visual_method, review_clause, top


def item_row(index: int, source_path: Path) -> dict[str, str]:
    citation = citation_for(source_path)
    source_rel = citation["Source_File_Relative"]
    domain, category, priority, risk, visual_required, visual_method, review_clause, top = domain_for(source_path)
    safe_id = f"ITEM-W65-{index:04d}"
    source_key = f"W65:{domain}:{source_rel}#L{citation['Citation_Line_Start']}-L{citation['Citation_Line_End']}"
    title = f"AI source coverage closure for {source_rel}"
    acceptance = (
        "The autonomous session has a direct Items/Tracker row for this Plan source file, reads the cited section before acting on it, "
        f"translates any requirements into executable work, and blocks completion until {review_clause}, tests, and evidence pass. "
        "Localized image, video, GIF, mask, prompt, frame, or audio work cannot pass if any unrelated whole-artifact visual or audio defect remains."
    )
    qa = (
        "source_file_read|citation_file_section_line_excerpt_present|requirements_extracted|implementation_or_blocker_recorded|"
        "test_or_review_gate_recorded|whole_artifact_visual_audio_regression_if_media|evidence_path_recorded"
    )
    row = {
        "Item_ID": safe_id,
        "Item_Wave": WAVE,
        "Item_Type": "plan_source_coverage_closure",
        "Item_Title": title,
        "Item_Category": category,
        "Item_Domain": domain,
        "Owner_Domain": top,
        "Autonomous_Required": "TRUE",
        "Human_Input_Allowed": "FALSE",
        "Human_Work_Allowed": "FALSE",
        "Codex_Action": f"Autonomously read, interpret, implement or block, test, review, and evidence every actionable requirement from {source_rel}.",
        "Implementation_Target": source_rel,
        "Deliverable_Type": "source_traceability_item_tracker_row_test_review_evidence_or_blocker",
        "Acceptance_Criteria": acceptance,
        "QA_Gates_Required": qa,
        "Visual_Review_Required": visual_required,
        "Visual_Review_Method": visual_method,
        "Test_Required": "TRUE",
        "Evidence_Required": "source_citation|required_action_extraction|test_or_static_validation|qa_review_record|pass_fail_or_blocker_decision",
        "Runtime_Proof_Required": "TRUE" if risk == "CRITICAL" and ("workflow" in source_rel.lower() or "runtime" in source_rel.lower()) else "FALSE",
        "EC2_Allowed": "TRUE" if risk == "CRITICAL" and ("workflow" in source_rel.lower() or "runtime" in source_rel.lower()) else "FALSE",
        "Blocker_Policy": "No human work. If this source cannot be read, mapped, tested, reviewed, or evidenced, create a source-cited blocker and continue only with safe autonomous work.",
        "Source_Plan_Root": str(PLAN),
        "Priority": priority,
        "Risk_Level": risk,
        "Status": "Required_Tracked_Not_Complete_Until_Evidence_Passes",
        "Created_From": "Wave65 exhaustive Plan source coverage closure generator",
        "Notes": "AI-only source closure row. This is not a human checklist; it is an autonomous execution and QA control record.",
        "Source_Key": source_key,
        "Coverage_Level": "exhaustive_current_plan_file_source_closure",
        "Coverage_Audit_Status": "covered_by_wave65_plan_source_closure",
        "Ultra_Source_Coverage_Record": source_key,
    }
    row.update(citation)
    return row


def tracker_row(index: int, item: dict[str, str]) -> dict[str, str]:
    return {
        "Tracker_ID": f"TRK-W65-{index:04d}",
        "Wave": WAVE,
        "Phase": "source_coverage_closure",
        "Workstream": item["Item_Domain"],
        "Priority": item["Priority"],
        "Risk_Level": item["Risk_Level"],
        "Owner_Role": "Codex Desktop Autonomous AI Session",
        "Environment": "local_first_then_ci_then_ec2_only_when_runtime_proof_required",
        "Status": "required_not_complete_until_evidence_passes",
        "Task_Name": item["Item_Title"],
        "Detailed_Action": item["Codex_Action"],
        "Completion_Criteria": item["Acceptance_Criteria"],
        "Acceptance_Evidence": item["Evidence_Required"],
        "Dependency_Prerequisite": "Read active goal, current session state, next action, blockers, known issues, QA evidence index, and cited source file before acting.",
        "Validation_Method": item["QA_Gates_Required"],
        "Output_Artifact": f"Plan/Instructions/QA/Evidence/Wave65/{item['Item_ID']}.json",
        "Source_Path": item["Citation_Full_Path"],
        "Related_Source_Paths": item["Citation_File"],
        "Package_Top_Level_Directory": str(PLAN),
        "Autonomous_Execution_Mode": "Codex Desktop fully autonomous, no human input, no human manual work",
        "Human_Input_Allowed": "FALSE",
        "Human_Work_Allowed": "FALSE",
        "Codex_Desktop_Action": item["Codex_Action"],
        "QA_Strictness": "STRICT",
        "Visual_Review_Required": item["Visual_Review_Required"],
        "Visual_Review_Method": item["Visual_Review_Method"],
        "Test_Required": item["Test_Required"],
        "Runtime_Proof_Required": item["Runtime_Proof_Required"],
        "EC2_Allowed": item["EC2_Allowed"],
        "Preview_Required": "TRUE" if item["Visual_Review_Required"] == "TRUE" else "FALSE",
        "Final_Render_Gate": "BLOCKED_UNTIL_SOURCE_REQUIREMENTS_TESTS_QA_AND_WHOLE_ARTIFACT_MEDIA_REVIEW_PASS",
        "Evidence_Path": f"Plan/Instructions/QA/Evidence/Wave65/{item['Item_ID']}.json",
        "Citation_File": item["Citation_File"],
        "Citation_Full_Path": item["Citation_Full_Path"],
        "Citation_Section": item["Citation_Section"],
        "Citation_Line_Start": item["Citation_Line_Start"],
        "Citation_Line_End": item["Citation_Line_End"],
        "Citation_Excerpt": item["Citation_Excerpt"],
        "Source_Package": item["Source_Package"],
        "Source_Type": item["Source_Type"],
        "Source_Item_ID": item["Item_ID"],
        "Blocker_Policy": item["Blocker_Policy"],
        "Rerun_Policy": "Targeted rerun only after source, model, prompt, workflow, artifact, or QA threshold changes; preserve passed evidence.",
        "Status_Decision": "blocked_or_passed_by_structured_evidence_only",
        "Notes": item["Notes"],
        "Source_Key": item["Source_Key"],
        "Source_File_Relative": item["Source_File_Relative"],
        "Coverage_Level": item["Coverage_Level"],
        "Coverage_Audit_Status": item["Coverage_Audit_Status"],
        "Ultra_Source_Coverage_Record": item["Ultra_Source_Coverage_Record"],
    }


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            cleaned = {}
            for column in columns:
                value = str(row.get(column, ""))
                cleaned[column] = value.replace("\r", " ").replace("\n", " ").rstrip()
            writer.writerow(cleaned)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate(rows: list[dict[str, str]], tracker_rows: list[dict[str, str]], all_plan_files: list[Path]) -> dict[str, object]:
    baseline_covered = covered_paths_from_csv(coverage_csv_paths(ITEMS) + coverage_csv_paths(TRACKER))
    wave65_covered = {norm(row["Citation_File"]) for row in rows}
    plan_norms = {norm(rel(path)) for path in all_plan_files}
    post_covered = baseline_covered | wave65_covered
    missing_after = sorted(plan_norms - post_covered)
    required_fields = [
        "Citation_File",
        "Citation_Full_Path",
        "Citation_Section",
        "Citation_Line_Start",
        "Citation_Line_End",
        "Citation_Excerpt",
        "Source_Key",
        "Source_File_Relative",
    ]
    errors = []
    for label, data_rows, id_col in (("item", rows, "Item_ID"), ("tracker", tracker_rows, "Tracker_ID")):
        for row in data_rows:
            missing = [field for field in required_fields if not row.get(field)]
            if missing:
                errors.append(f"{label} {row.get(id_col)} missing {missing}")
            if row.get("Human_Input_Allowed") != "FALSE" or row.get("Human_Work_Allowed") != "FALSE":
                errors.append(f"{label} {row.get(id_col)} allows human input/work")
            if label == "tracker" and row.get("QA_Strictness") != "STRICT":
                errors.append(f"{label} {row.get(id_col)} is not STRICT")
            try:
                start = int(row.get("Citation_Line_Start", "0"))
                end = int(row.get("Citation_Line_End", "0"))
                if start < 1 or end < start:
                    errors.append(f"{label} {row.get(id_col)} has invalid line span")
            except ValueError:
                errors.append(f"{label} {row.get(id_col)} has non-integer citation line")
    if missing_after:
        errors.append(f"{len(missing_after)} Plan files remain without Items/Tracker source coverage")
    return {
        "schema_version": "1.0",
        "operation": "wave65_plan_source_coverage_closure",
        "result": "pass" if not errors else "fail",
        "plan_file_count": len(plan_norms),
        "baseline_covered_plan_files": len(plan_norms & baseline_covered),
        "wave65_rows_created": len(rows),
        "post_wave65_covered_plan_files": len(plan_norms & post_covered),
        "missing_after_wave65_count": len(missing_after),
        "missing_after_wave65_sample": missing_after[:50],
        "item_row_count": len(rows),
        "tracker_row_count": len(tracker_rows),
        "required_fields": required_fields,
        "human_input_allowed": False,
        "human_work_allowed": False,
        "whole_artifact_rule": "Any localized image, video, GIF, mask, prompt, frame, or audio work fails if the entire generated artifact has unrelated visual or audio defects.",
        "confidence_statement": "Wave65 closes direct Items/Tracker source coverage for every current Plan file. Completion still requires each source row's implementation, tests, QA, media review, and evidence to pass.",
        "errors": errors,
    }


def main() -> int:
    all_files = plan_files()
    baseline_covered = covered_paths_from_csv(coverage_csv_paths(ITEMS) + coverage_csv_paths(TRACKER))
    missing = [path for path in all_files if norm(rel(path)) not in baseline_covered]
    item_rows = [item_row(index, path) for index, path in enumerate(missing, start=1)]
    tracker_rows = [tracker_row(index, row) for index, row in enumerate(item_rows, start=1)]

    write_csv(ITEMS / "wave65_plan_source_coverage_closure_itemized_list.csv", ITEM_COLUMNS, item_rows)
    write_csv(ITEMS / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_ITEM_ROWS.csv", ITEM_COLUMNS, item_rows)
    write_csv(TRACKER / "wave65_plan_source_coverage_closure_tracker.csv", TRACKER_COLUMNS, tracker_rows)
    write_csv(TRACKER / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_TRACKER_ROWS.csv", TRACKER_COLUMNS, tracker_rows)

    requirements = {
        "schema_version": "1.0",
        "wave": 65,
        "purpose": "Close direct Items/Tracker coverage for every current file under C:\\Comfy_UI_Main\\Plan.",
        "coverage_rule": "Every current Plan file must appear in baseline Items/Tracker coverage or Wave65 closure rows with Citation_File, Citation_Full_Path, Citation_Section, Citation_Line_Start, Citation_Line_End, Citation_Excerpt, Source_Key, and Source_File_Relative.",
        "autonomy_rule": "Rows are AI-only. Human_Input_Allowed and Human_Work_Allowed must remain FALSE.",
        "whole_artifact_rule": "Localized media work cannot pass unless full-frame, full-duration, and full-artifact visual/audio QA also pass.",
        "regeneration_rule": "Rerun Plan/Items/Scripts/generate_wave65_plan_source_coverage.py after any new Plan file is added or renamed.",
    }
    for path in (
        ITEMS / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_REQUIREMENTS.json",
        TRACKER / "Waves" / "Wave65" / "WAVE65_PLAN_SOURCE_COVERAGE_REQUIREMENTS.json",
    ):
        write_text(path, json.dumps(requirements, indent=2) + "\n")

    readme = (
        "# Wave65 Plan Source Coverage Closure\n\n"
        "Wave65 is an AI-only source coverage closure. It exists so the autonomous session can prove that every current file under "
        "`C:\\Comfy_UI_Main\\Plan` has direct Items/Tracker coverage with file, section, line span, excerpt, and Source_Key.\n\n"
        "Completion is not granted by the row existing. The AI session must still read the cited source, extract requirements, implement or block, "
        "run required tests, perform whole-artifact visual/audio review when media is affected, and record structured evidence.\n"
    )
    write_text(ITEMS / "Waves" / "Wave65" / "README.md", readme)
    write_text(TRACKER / "Waves" / "Wave65" / "README.md", readme)

    scope = (
        "# Wave65 Scope - Exhaustive AI Source Coverage Closure\n\n"
        "Wave65 is active when the session needs confidence that Plan/Items and Plan/Tracker directly cover every current Plan file.\n\n"
        "Hard rules:\n"
        "- Every current Plan file must be represented by existing baseline Items/Tracker coverage or a Wave65 closure row.\n"
        "- Every closure row must include Citation_File, Citation_Full_Path, Citation_Section, Citation_Line_Start, Citation_Line_End, Citation_Excerpt, Source_Key, and Source_File_Relative.\n"
        "- Human_Input_Allowed and Human_Work_Allowed must be FALSE.\n"
        "- The autonomous session must rerun the Wave65 generator after adding or renaming any Plan file.\n"
        "- Localized image, video, GIF, mask, prompt, frame, or audio work cannot pass if the whole generated artifact has unrelated defects.\n"
    )
    write_text(INSTRUCTIONS / "Waves" / "Wave65" / "WAVE65_SCOPE.md", scope)

    supplement_columns = ["Wave", "Supplement_ID", "Purpose", "Required_Action", "Evidence"]
    item_supplement = [
        {
            "Wave": WAVE,
            "Supplement_ID": "W65-ITEM-SOURCE-CLOSURE",
            "Purpose": "Ensure Plan/Items has current direct source coverage for every Plan file.",
            "Required_Action": "Rerun generate_wave65_plan_source_coverage.py after Plan file additions or renames.",
            "Evidence": "Plan/Items/Reports/wave65_plan_source_coverage_report.json",
        }
    ]
    tracker_supplement = [
        {
            "Wave": WAVE,
            "Supplement_ID": "W65-TRACKER-SOURCE-CLOSURE",
            "Purpose": "Ensure Plan/Tracker has current direct source coverage for every Plan file.",
            "Required_Action": "Rerun generate_wave65_plan_source_coverage.py after Plan file additions or renames.",
            "Evidence": "Plan/Tracker/Reports/wave65_plan_source_coverage_report.json",
        }
    ]
    write_csv(INSTRUCTIONS / "Waves" / "Wave65" / "WAVE65_ITEMIZED_LIST_SUPPLEMENT.csv", supplement_columns, item_supplement)
    write_csv(INSTRUCTIONS / "Waves" / "Wave65" / "WAVE65_TRACKER_SUPPLEMENT.csv", supplement_columns, tracker_supplement)

    report = validate(item_rows, tracker_rows, all_files)
    for path in (
        ITEMS / "Reports" / "wave65_plan_source_coverage_report.json",
        TRACKER / "Reports" / "wave65_plan_source_coverage_report.json",
    ):
        write_text(path, json.dumps(report, indent=2) + "\n")

    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
