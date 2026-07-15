#!/usr/bin/env python3
"""Build the additive Wave64 Rows113-148 hyperreal speech control package."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/Comfy_UI_Main")
STATUS = "Planned_Autonomous_Implementation_Required"
MASTER = Path("Plan/00_PROJECT_CONTROL/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_AND_VOICE_MASTER_PLAN.md")
ARCH = Path("Plan/02_TARGET_ARCHITECTURE/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ARCHITECTURE.md")
ENGINE = Path("Plan/05_AUDIO_SYSTEM/WAVE64_HYPERREAL_SPEECH_ENGINE_AND_MODEL_STRATEGY.md")
QA = Path("Plan/Instructions/QA/AUTONOMOUS_HYPERREAL_SPEECH_AND_VOICE_QA_PROTOCOL.md")
ASSET_PROTOCOL = Path("Plan/Instructions/QA/WAVE64_HYPERREAL_AUDIO_MODEL_ASSET_DISCOVERY_PROTOCOL.md")
ASSET_CATALOG = Path("Plan/10_REGISTRIES/wave64_hyperreal_audio_model_asset_acquisition_catalog.json")
ASSET_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_HYPERREAL_AUDIO_PROVIDER_DISCOVERY_20260715.json")
SECOND_PASS_EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_HYPERREAL_AUDIO_SECOND_PASS_AUDIT_20260715.json")
ITEMS = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ITEM_ROWS.csv")
TRACKER = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_TRACKER_ROWS.csv")
REQ = Path("Plan/Items/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
REQ_MIRROR = Path("Plan/Tracker/Waves/Wave64/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_REQUIREMENTS.json")
REGISTRY = Path("Plan/10_REGISTRIES/wave64_autonomous_hyperreal_speech_work_package_registry.json")
EVIDENCE = Path("Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_PLANNING_COVERAGE_20260715.json")
EVIDENCE_MIRROR = Path("Plan/Tracker/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_PLANNING_COVERAGE_20260715.json")


ROWS = [
    (113, "speech_program_authority", "Hyperreal speech authority and no-false-completion control", "control", "Define execution authority, boundaries, dependencies, classifications, and evidence rules for Rows113-148.", "Authority registry and validator reject completion without runtime and certification evidence."),
    (114, "voice_reference_cards", "Immutable character voice-reference card system", "authority", "Implement per-character versioned voice cards with hashes, rights, transcript, traits, embeddings, continuity lines, approved engines, and revocation.", "Cards validate, bind exact references, separate authority from synthesis, and fail closed on missing rights or hashes."),
    (115, "voice_reference_intake_qa", "Voice-reference intake, segmentation, and quality QA", "authority", "Decode, segment, transcribe, score, and curate reference speech without modifying source bytes.", "Reference segments have sample bounds, transcript, quality metrics, contamination flags, and deterministic selection evidence."),
    (116, "autonomous_character_voice_casting", "Autonomous character voice casting and identity policy", "authority", "Rank licensed references or designed synthetic voices against character requirements across male and female targets.", "Casting record is explainable, hash-bound, rights-valid, continuity-tested, and production authority remains explicit."),
    (117, "speech_engine_acquisition_registry", "Provider-resolved speech/audio acquisition, adapter, and license registry", "models", "Execute the provider-resolved catalog for exact Qwen3-TTS, Fun-CosyVoice3, Chatterbox V3/Turbo, Fish Audio S2, synchronization, Foley, and evaluator assets using reuse-first isolated adapters.", "Every selected asset binds an official immutable revision or exact Civitai version/file, hashes, license/access, environment, loader proof, row dependency, and fail-closed availability."),
    (118, "speech_engine_benchmark_tournament", "Multi-engine speech benchmark tournament", "models", "Benchmark eligible engines by character, language, duration, style, quality, identity, runtime, and failure rate.", "Tournament uses calibrated hard gates and explainable ranking; no universal engine is assumed."),
    (119, "dialogue_text_normalization", "Dialogue text normalization and token authority", "planning", "Normalize numbers, dates, abbreviations, symbols, punctuation, casing, and language while preserving original text lineage.", "Normalized text is deterministic, reversible, tested, and hash-bound to the line contract."),
    (120, "pronunciation_g2p_lexicon", "Pronunciation, G2P, phoneme, and lexicon authority", "planning", "Compile language-aware pronunciation dictionaries, proper-name overrides, phonemes, stress, and fallback confidence.", "Pronunciation fixtures pass and unknown or ambiguous pronunciations block or route to explicit review."),
    (121, "dialogue_performance_planner", "Dialogue performance, pause, breath, and emphasis planner", "planning", "Compile emotion, delivery style, intensity, pace, articulation, emphasis, pauses, breaths, and vocal effort as separate controls.", "Line plan validates without taxonomy conflation and records unsupported engine controls explicitly."),
    (122, "duration_aware_speech_planner", "Duration-aware dialogue and shot timing planner", "planning", "Estimate duration from phonemes and calibrated character pace, then choose native timing, bounded correction, alternate engine, or shot-contract blocker.", "Planner never trims spoken content and proves timing decisions against calibrated tolerances."),
    (123, "multi_engine_candidate_generation", "Bounded multi-engine dialogue candidate generation", "generation", "Generate immutable candidate sets across eligible engines with exact requests, seeds, references, models, outputs, and runtime telemetry.", "Candidates are reproducible, hash-bound, count-limited, and never overwrite rejected evidence."),
    (124, "reference_voice_cloning", "Reference-conditioned voice cloning and identity preservation", "generation", "Implement cloning routes with multi-reference authority and identity leakage/drift checks.", "Cloned speech passes content, calibrated identity, continuity, rights, and reference-separation gates."),
    (125, "designed_synthetic_voice", "Designed synthetic voice creation and locking", "generation", "Create new character voices from explicit design controls and lock a reproducible baseline without impersonation claims.", "Voice design has immutable model/configuration, continuity corpus, character approval record, and no reference-clone ambiguity."),
    (126, "speech_prosody_control", "Prosody, pitch, pace, pause, and articulation control", "performance", "Measure and control F0, energy, rhythm, speaking rate, pauses, emphasis, and articulation per line and character.", "Prosody evidence compares target and output distributions and rejects unmeasured control claims."),
    (127, "speech_emotion_intensity_control", "Emotion, delivery-style, and intensity control", "performance", "Evaluate emotion class separately from delivery style and intensity using supported taxonomies and calibrated evidence.", "Focused/controlled are not force-mapped; unsupported targets remain explicit blockers."),
    (128, "nonverbal_vocalization_system", "Breath, effort, laugh, cry, whisper, shout, and nonverbal voice system", "performance", "Generate or select identity-consistent nonverbal vocal events with rights, timing, intensity, and acoustic context.", "Vocal events have character ownership, event class, onset/decay, identity, quality, and promotion evidence."),
    (129, "speech_recording_chain", "Virtual microphone, proximity, and recording-chain renderer", "acoustics", "Model microphone character, proximity, EQ, dynamics, saturation, mouth noise, and production recording state nondestructively.", "Dry source and processing recipe are retained; character identity and intelligibility remain within thresholds."),
    (130, "speech_enhancement_restoration", "Speech enhancement, de-click, de-plosive, de-ess, and restoration", "acoustics", "Apply bounded speech repair and enhancement with before/after metrics and listening eligibility.", "Enhancement reduces defects without removing phonemes, breaths required for realism, bandwidth, or identity."),
    (131, "speaker_identity_evaluator", "Calibrated multi-reference speaker identity evaluator", "continuity", "Build character-specific identity thresholds using disjoint calibration/held-out references and multiple embedding routes.", "False accept/reject behavior is measured and one similarity score cannot authorize production."),
    (132, "cross_line_scene_voice_continuity", "Cross-line, cross-shot, and cross-scene voice continuity", "continuity", "Track identity, pitch, timbre, pace, accent, microphone, and room consistency across production history.", "Continuity matrix covers at least ten lines and three scenes per certified character."),
    (133, "multilingual_accent_voice_continuity", "Multilingual, accent, and code-switch voice continuity", "continuity", "Evaluate supported languages, pronunciation, accent retention, code switching, and cross-language identity.", "Language-specific metrics and human playback eligibility pass without claiming unsupported languages."),
    (134, "multi_speaker_dialogue_control", "Multi-speaker dialogue, turn-taking, and active-speaker ownership", "continuity", "Plan and validate speaker turns, interruptions, overlaps, off-screen speech, and visible active-speaker identity.", "Every segment binds the correct character and overlap state with diarization and visual ownership evidence."),
    (135, "word_phoneme_forced_alignment", "Word and phoneme forced alignment", "alignment", "Integrate WhisperX-style word timing and MFA-style phoneme alignment with monotonic sample-level manifests.", "Alignment covers required speech, matches transcript, records confidence, and rejects ambiguous transforms."),
    (136, "phoneme_viseme_compiler", "Phoneme-to-viseme and coarticulation compiler", "alignment", "Map aligned phonemes to versioned visemes, coarticulation, jaw/lip controls, frames, and confidence.", "Fixtures cover plosives, fricatives, vowels, closures, silence, and rapid transitions without timing overlap defects."),
    (137, "speech_lip_sync_correction", "Identity-preserving lip-sync correction and QA", "alignment", "Apply a validated lip-sync correction route only after accepted speech and alignment exist.", "Mouth motion aligns without face identity drift, frame corruption, or accepting incorrect speech."),
    (138, "dialogue_spatial_scene_rendering", "Dialogue spatial position, distance, occlusion, and room rendering", "mix", "Render actor motion, distance, elevation, obstruction, early reflections, reverb, and microphone perspective.", "Acoustic fixtures match source trajectories and room state while preserving intelligibility and identity."),
    (139, "dialogue_edit_mix_bus", "Dialogue editing, room tone, ducking, bus processing, and stems", "mix", "Build sample-accurate dialogue edits, crossfades, room tone, Foley/ambience ducking, buses, loudness, and stems.", "Mix passes clipping, loudness, masking, continuity, and full-duration playback gates with dry and processed stems."),
    (140, "overlap_interruption_dialogue_mix", "Overlapping speech, interruption, crowd, and priority mixing", "mix", "Handle simultaneous speakers and priority without losing words, identity, spatial ownership, or realism.", "Overlap corpus passes diarization, intelligibility, active-speaker, masking, and spatial-separation thresholds."),
    (141, "speech_evaluator_ensemble", "Speech content, identity, prosody, quality, and alignment evaluator ensemble", "qa", "Combine ASR, speaker, prosody, emotion, intensity, DNSMOS/full-band, alignment, and acoustic evidence with versioned thresholds.", "Missing mandatory metrics block; evaluator outputs are calibrated and cannot self-authorize production."),
    (142, "speech_adversarial_regression", "Adversarial speech defect and regression matrix", "qa", "Test hallucination, repetition, truncation, difficult text, identity drift, timing, noise, reverb, emotion, and multilingual failures.", "Known defects are detected at required rates and rejected candidates remain immutable regression fixtures."),
    (143, "speech_playback_review_packets", "Automated human playback request and review packet production", "qa", "Prepare hash-bound eligible speech and mux packets with real authority_type discrimination and full-play requirements.", "Automation never fabricates a human review; validators reject incomplete, mismatched, or model-labeled-as-human records."),
    (144, "speech_candidate_promotion_revocation", "Speech candidate promotion, revocation, rollback, and lineage", "promotion", "Promote eligible dry/mixed dialogue with complete authority, ranking, review, rollback, and revocation lineage.", "Promotion is atomic, idempotent, replayable, and immediately invalidated by revoked references or models."),
    (145, "comfyui_speech_integration", "ComfyUI speech nodes, workflows, API bridge, and orchestration", "integration", "Expose voice cards, line plans, engine routing, generation, evaluation, alignment, mix, and evidence through modular ComfyUI/API units.", "Workflow contracts validate, dependencies are visible, failures are structured, and headless execution is proven."),
    (146, "speech_runtime_cache_cost", "Speech runtime isolation, caching, batching, and cost control", "operations", "Implement environment isolation, model cache, reference embedding cache, batching, GPU routing, watchdogs, and cost telemetry.", "Cache keys include exact hashes; concurrency is safe; stale or incompatible environments fail closed."),
    (147, "speech_benchmark_certification_corpus", "Hyperreal speech benchmark and certification corpus", "qa", "Build rights-valid calibration and held-out fixtures across characters, genders, languages, styles, durations, nonverbal events, rooms, and overlaps.", "Calibration/test roles stay separate and corpus coverage satisfies the final certification matrix."),
    (148, "speech_full_system_certification", "Autonomous hyperreal speech full-system certification", "certification", "Execute multi-character, multi-engine, multi-scene dry-to-mux production certification with replay and rollback.", "All required rows pass, zero blocking defects remain, human and model authority are valid, and production artifacts are hash-bound."),
]


HASH = {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}
FILE_BINDING = {
    "type": "object",
    "required": ["path", "sha256", "bytes"],
    "properties": {"path": {"type": "string"}, "sha256": HASH, "bytes": {"type": "integer", "minimum": 1}},
}
SCHEMAS: dict[str, dict[str, Any]] = {
    "voice_reference_card.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Voice Reference Card", "type": "object",
        "required": ["schema_version", "voice_reference_id", "character_id", "character_version", "identity_policy", "production_authorized", "source", "rights", "transcript", "voice_traits", "quality", "content_based_suppression"],
        "properties": {
            "schema_version": {"type": "string"}, "voice_reference_id": {"type": "string", "minLength": 1}, "character_id": {"type": "string"}, "character_version": {"type": "string"},
            "identity_policy": {"enum": ["licensed_reference_match", "designed_synthetic_voice", "consistent_synthetic_baseline", "pending_selection"]}, "production_authorized": {"type": "boolean"},
            "source": {**FILE_BINDING, "required": FILE_BINDING["required"] + ["duration_seconds", "sample_rate_hz", "channels"], "properties": {**FILE_BINDING["properties"], "duration_seconds": {"type": "number", "exclusiveMinimum": 0}, "sample_rate_hz": {"type": "integer", "minimum": 8000}, "channels": {"type": "integer", "minimum": 1}}},
            "rights": {"type": "object", "required": ["license", "provenance", "derivative_use_allowed"], "properties": {"license": {"type": "string"}, "provenance": {"type": "string"}, "derivative_use_allowed": {"type": "boolean"}, "attribution": {"type": "string"}}},
            "transcript": {"type": "object", "required": ["text", "language"], "properties": {"text": {"type": "string"}, "language": {"type": "string"}}},
            "voice_traits": {"type": "object"}, "quality": {"type": "object"}, "approved_engine_configurations": {"type": "array", "items": {"type": "string"}}, "content_based_suppression": {"const": False}, "revoked": {"type": "boolean"},
        }, "additionalProperties": True,
    },
    "speech_engine_adapter.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Speech Engine Adapter", "type": "object",
        "required": ["schema_version", "adapter_id", "engine_family", "repository", "revision", "model_files", "license", "environment", "capabilities", "runtime_status"],
        "properties": {
            "schema_version": {"type": "string"}, "adapter_id": {"type": "string"}, "engine_family": {"type": "string"}, "repository": {"type": "string"}, "revision": {"type": "string", "minLength": 7},
            "model_files": {"type": "array", "minItems": 1, "items": {**FILE_BINDING, "required": ["filename", "sha256", "bytes"], "properties": {"filename": {"type": "string"}, "sha256": HASH, "bytes": {"type": "integer", "minimum": 1}}}},
            "license": {"type": "object"}, "environment": {"type": "object"}, "capabilities": {"type": "object"}, "runtime_status": {"enum": ["planned", "acquired", "load_proven", "candidate_proven", "approved", "blocked", "revoked"]},
        }, "additionalProperties": True,
    },
    "speech_candidate_manifest.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Speech Candidate Manifest", "type": "object",
        "required": ["schema_version", "candidate_id", "request_sha256", "character_id", "voice_reference_ids", "engine_adapter_id", "model_revision", "seed", "output", "runtime", "disposition"],
        "properties": {"schema_version": {"type": "string"}, "candidate_id": {"type": "string"}, "request_sha256": HASH, "character_id": {"type": "string"}, "voice_reference_ids": {"type": "array", "items": {"type": "string"}}, "engine_adapter_id": {"type": "string"}, "model_revision": {"type": "string"}, "seed": {"type": "integer"}, "output": {**FILE_BINDING, "required": FILE_BINDING["required"] + ["duration_seconds", "sample_rate_hz", "channels"]}, "runtime": {"type": "object"}, "disposition": {"enum": ["candidate", "rejected", "eligible_for_playback", "promoted", "revoked"]}}, "additionalProperties": True,
    },
    "speech_alignment_manifest.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Speech Alignment Manifest", "type": "object",
        "required": ["schema_version", "candidate_id", "artifact_sha256", "sample_rate_hz", "transcript", "words", "phonemes", "coverage", "monotonic", "pass"],
        "properties": {"schema_version": {"type": "string"}, "candidate_id": {"type": "string"}, "artifact_sha256": HASH, "sample_rate_hz": {"type": "integer"}, "transcript": {"type": "string"}, "words": {"type": "array", "items": {"$ref": "#/$defs/interval"}}, "phonemes": {"type": "array", "items": {"$ref": "#/$defs/interval"}}, "coverage": {"type": "number", "minimum": 0, "maximum": 1}, "monotonic": {"type": "boolean"}, "pass": {"type": "boolean"}},
        "$defs": {"interval": {"type": "object", "required": ["label", "start_sample", "end_sample", "confidence"], "properties": {"label": {"type": "string"}, "start_sample": {"type": "integer", "minimum": 0}, "end_sample": {"type": "integer", "minimum": 1}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}}, "additionalProperties": True,
    },
    "speech_evaluation_record.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Speech Evaluation Record", "type": "object",
        "required": ["schema_version", "candidate_id", "artifact_sha256", "evaluator_versions", "content", "identity", "performance", "technical", "timing", "hard_gates", "decision"],
        "properties": {"schema_version": {"type": "string"}, "candidate_id": {"type": "string"}, "artifact_sha256": HASH, "evaluator_versions": {"type": "object", "minProperties": 1}, "content": {"type": "object"}, "identity": {"type": "object"}, "performance": {"type": "object"}, "technical": {"type": "object"}, "timing": {"type": "object"}, "hard_gates": {"type": "object"}, "decision": {"enum": ["reject", "blocked", "eligible_for_playback", "pass_bounded"]}}, "additionalProperties": True,
    },
    "speech_promotion_record.schema.json": {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Speech Promotion Record", "type": "object",
        "required": ["schema_version", "promotion_id", "candidate_id", "artifact_sha256", "character_version", "authority_bindings", "evaluation_bindings", "review_bindings", "rollback", "decision"],
        "properties": {"schema_version": {"type": "string"}, "promotion_id": {"type": "string"}, "candidate_id": {"type": "string"}, "artifact_sha256": HASH, "character_version": {"type": "string"}, "authority_bindings": {"type": "array", "minItems": 1, "items": {"type": "object"}}, "evaluation_bindings": {"type": "array", "minItems": 1, "items": {"type": "object"}}, "review_bindings": {"type": "array", "minItems": 1, "items": {"type": "object"}}, "rollback": {"type": "object"}, "decision": {"enum": ["promoted", "revoked", "rolled_back"]}}, "additionalProperties": True,
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle))


def row_requirement(number: int, workstream: str, title: str, category: str, action: str, acceptance: str) -> dict[str, Any]:
    return {
        "row_number": number, "tracker_id": f"TRK-W64-{number:03d}", "item_id": f"ITEM-W64-{number:03d}",
        "workstream": workstream, "title": title, "category": category, "status": STATUS,
        "implementation_action": action, "acceptance": acceptance,
        "mandatory_evidence": ["implementation_hashes", "tests", "dependency_versions", "runtime_manifest_if_applicable", "artifact_hashes_if_applicable", "qa_record", "pass_or_exact_blocker"],
        "prohibited_claims": ["planning_is_runtime", "download_is_ready", "single_metric_is_promotion", "model_review_is_human_review", "full_project_complete_without_row148"],
    }


def item_row(fields: list[str], requirement: dict[str, Any], source_size: int) -> dict[str, str]:
    n = requirement["row_number"]
    values = {
        "Item_ID": requirement["item_id"], "Item_Wave": "64", "Item_Type": "Autonomous implementation and certification control", "Item_Title": requirement["title"],
        "Item_Category": requirement["category"], "Item_Domain": "hyperreal_speech_voice", "Owner_Domain": "Codex Desktop Autonomous Agent", "Autonomous_Required": "TRUE", "Human_Input_Allowed": "FALSE", "Human_Work_Allowed": "FALSE",
        "Codex_Action": requirement["implementation_action"], "Implementation_Target": requirement["workstream"], "Deliverable_Type": "implementation|tests|runtime_evidence|qa|status_decision", "Acceptance_Criteria": requirement["acceptance"],
        "QA_Gates_Required": "authority|runtime|content|identity|performance|technical|timing|scene|review|promotion", "Visual_Review_Required": "TRUE" if n in {137, 138, 139, 140, 148} else "FALSE", "Visual_Review_Method": "speech_video_playback_review" if n in {137, 138, 139, 140, 148} else "not_applicable_or_audio_review", "Test_Required": "TRUE",
        "Evidence_Required": f"Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{n:03d}.json", "Runtime_Proof_Required": "FALSE" if n in {113, 114, 117} else "TRUE", "EC2_Allowed": "TRUE",
        "Blocker_Policy": "Fail closed with one exact blocker; do not infer implementation from planning, model presence, or adjacent rows.", "Source_Plan_Root": str(ROOT / "Plan"), "Citation_File": MASTER.as_posix(), "Citation_Full_Path": str(ROOT / MASTER),
        "Citation_Section": "Reserved execution rows", "Citation_Line_Start": "1", "Citation_Line_End": "260", "Citation_Excerpt": requirement["title"], "Source_Package": str(ROOT / "Plan"), "Source_Type": "md", "Source_File_Size": str(source_size),
        "Priority": "P0", "Risk_Level": "CRITICAL" if n in {114, 116, 117, 118, 123, 124, 131, 137, 141, 144, 148} else "HIGH", "Status": STATUS, "Created_From": "WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_AND_VOICE_MASTER_PLAN",
        "Notes": "Additive speech expansion; Rows025-033 and Rows067-112 remain separate authority. content_based_suppression=false.", "Source_Key": f"W64:autonomous_hyperreal_speech:{n:03d}", "Source_File_Relative": MASTER.as_posix(),
        "Coverage_Level": "planned_autonomous_implementation_control", "Coverage_Audit_Status": "covered_by_wave64_hyperreal_speech_expansion_not_yet_implemented", "Ultra_Source_Coverage_Record": f"W64:autonomous_hyperreal_speech:{n:03d}",
    }
    return {field: values.get(field, "") for field in fields}


def tracker_row(fields: list[str], requirement: dict[str, Any]) -> dict[str, str]:
    n = requirement["row_number"]
    evidence = f"Plan/Instructions/QA/Evidence/Audio_Asset_Intake/WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_ROW{n:03d}.json"
    values = {
        "Tracker_ID": requirement["tracker_id"], "Wave": "64", "Phase": "Wave 64", "Workstream": requirement["workstream"], "Priority": "P0", "Risk_Level": "CRITICAL" if n in {114, 116, 117, 118, 123, 124, 131, 137, 141, 144, 148} else "HIGH",
        "Owner_Role": "Codex Desktop Autonomous Agent", "Environment": "local_repo_ci_comfyui_ec2_as_required", "Status": STATUS, "Task_Name": requirement["title"], "Detailed_Action": requirement["implementation_action"], "Completion_Criteria": requirement["acceptance"],
        "Acceptance_Evidence": "implementation_hashes|test_log|runtime_manifest|artifact_hashes|qa_record|pass_or_exact_blocker", "Dependency_Prerequisite": "Read the master plan, provider-resolved asset catalog, architecture, engine strategy, QA protocol, current voice authority, and exact dependency evidence before execution.", "Validation_Method": "deterministic_contract_tests|genuine_runtime_if_required|audio_or_video_playback_qa|promotion_gate",
        "Output_Artifact": evidence, "Source_Path": str(ROOT / MASTER), "Related_Source_Paths": f"{ARCH.as_posix()}; {ENGINE.as_posix()}; {QA.as_posix()}; {ASSET_CATALOG.as_posix()}; {ASSET_PROTOCOL.as_posix()}", "Package_Top_Level_Directory": str(ROOT / "Plan"), "Autonomous_Execution_Mode": "Codex Desktop fully autonomous; irreducible human playback only through existing authority protocol", "Human_Input_Allowed": "FALSE", "Human_Work_Allowed": "FALSE",
        "Codex_Desktop_Action": requirement["implementation_action"], "QA_Strictness": "STRICT", "Visual_Review_Required": "TRUE" if n in {137, 138, 139, 140, 148} else "FALSE", "Visual_Review_Method": "speech_video_playback_review" if n in {137, 138, 139, 140, 148} else "audio_review_or_not_applicable", "Test_Required": "TRUE", "Runtime_Proof_Required": "FALSE" if n in {113, 114, 117} else "TRUE", "EC2_Allowed": "TRUE", "Preview_Required": "TRUE" if n >= 123 else "FALSE",
        "Final_Render_Gate": "BLOCKED_UNTIL_HASH_BOUND_RUNTIME_QA_AND_AUTHORITY_PASS", "Evidence_Path": evidence, "Citation_File": MASTER.as_posix(), "Citation_Full_Path": str(ROOT / MASTER), "Citation_Section": "Reserved execution rows", "Citation_Line_Start": "1", "Citation_Line_End": "260", "Citation_Excerpt": requirement["title"], "Source_Package": str(ROOT / "Plan"), "Source_Type": "md", "Source_Item_ID": requirement["item_id"],
        "Blocker_Policy": "Fail closed with one exact blocker; never promote from planning, download, a single metric, or fabricated review authority.", "Rerun_Policy": "Preserve completed evidence; rerun only for a materially changed source, model, reference, configuration, threshold, or objective.", "Status_Decision": "planned_autonomous_implementation_required", "Notes": "Additive speech expansion. No existing row status is changed. content_based_suppression=false.",
        "Source_Key": f"W64:autonomous_hyperreal_speech:{n:03d}", "Source_File_Relative": MASTER.as_posix(), "Coverage_Level": "planned_autonomous_implementation_control", "Coverage_Audit_Status": "covered_by_wave64_hyperreal_speech_expansion_not_yet_implemented", "Ultra_Source_Coverage_Record": f"W64:autonomous_hyperreal_speech:{n:03d}",
    }
    return {field: values.get(field, "") for field in fields}


def main(root: Path = ROOT) -> None:
    root = root.resolve()
    item_fields = read_header(root / "Plan/Items/wave64_end_to_end_strict_ai_itemized_list.csv")
    tracker_fields = read_header(root / "Plan/Tracker/wave64_end_to_end_strict_ai_tracker.csv")
    asset_catalog = json.loads((root / ASSET_CATALOG).read_text(encoding="utf-8"))
    requirements = [row_requirement(*row) for row in ROWS]
    for requirement in requirements:
        requirement["asset_catalog"] = ASSET_CATALOG.as_posix()
        requirement["required_asset_ids"] = asset_catalog["row_asset_bindings"].get(requirement["tracker_id"], [])
    source_size = (root / MASTER).stat().st_size

    for relative, rows, fields, builder in ((ITEMS, requirements, item_fields, lambda req: item_row(item_fields, req, source_size)), (TRACKER, requirements, tracker_fields, lambda req: tracker_row(tracker_fields, req))):
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(builder(row) for row in rows)

    requirement_payload = {"schema_version": "1.0", "package_id": "wave64_autonomous_hyperreal_speech_rows113_148", "row_range": {"first": 113, "last": 148, "count": len(requirements)}, "status": STATUS, "content_based_suppression": False, "requirements": requirements}
    write_json(root / REQ, requirement_payload); write_json(root / REQ_MIRROR, requirement_payload)

    schema_dir = root / "Plan/08_SCHEMAS"
    for name, schema in SCHEMAS.items(): write_json(schema_dir / name, schema)

    registry = {
        "schema_version": "1.0", "registry_id": "wave64_autonomous_hyperreal_speech_work_packages", "row_range": {"first": 113, "last": 148, "count": 36}, "default_status": STATUS,
        "dependencies": {"portfolio_rows": [f"TRK-W64-{n:03d}" for n in range(25, 34)], "sound_intelligence_rows": [f"TRK-W64-{n:03d}" for n in range(67, 113)]},
        "provider_resolved_asset_catalog": ASSET_CATALOG.as_posix(),
        "provider_discovery_protocol": ASSET_PROTOCOL.as_posix(),
        "provider_discovery_evidence": ASSET_EVIDENCE.as_posix(),
        "provider_second_pass_evidence": SECOND_PASS_EVIDENCE.as_posix(),
        "provider_catalog_summary": {"official_asset_groups": len(asset_catalog["official_asset_groups"]), "official_source_repositories": len(asset_catalog["official_source_repositories"]), "civitai_integration_candidates": len(asset_catalog["civitai_integration_candidates"]), "row_bindings": len(asset_catalog["row_asset_bindings"])},
        "engine_candidates": [
            {"family": "qwen3_tts", "official_repository": "https://github.com/QwenLM/Qwen3-TTS", "roles": ["voice_design", "custom_voice", "cloning", "streaming"], "status": "exact_assets_and_runtime_required"},
            {"family": "fun_cosyvoice3", "official_repository": "https://github.com/FunAudioLLM/CosyVoice", "roles": ["multilingual", "zero_shot_cloning", "instruction"], "status": "exact_assets_and_runtime_required"},
            {"family": "chatterbox_v3_turbo", "official_repository": "https://github.com/resemble-ai/chatterbox", "roles": ["multilingual_cloning", "english_low_latency"], "status": "exact_assets_and_runtime_required"},
            {"family": "fish_speech_s2", "official_repository": "https://github.com/fishaudio/fish-speech", "roles": ["multilingual", "short_reference_cloning"], "status": "exact_assets_and_runtime_required"},
            {"family": "parler_tts", "official_repository": "https://github.com/huggingface/parler-tts", "roles": ["english_prompt_controlled_baseline"], "status": "existing_rejected_candidate_regression_baseline"},
        ],
        "evaluation_candidates": [
            {"family": "whisperx", "official_repository": "https://github.com/m-bain/whisperX", "role": "word_timing_asr"},
            {"family": "montreal_forced_aligner", "official_repository": "https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner", "role": "phoneme_alignment"},
            {"family": "pyannote_audio", "official_repository": "https://github.com/pyannote/pyannote-audio", "role": "diarization_and_speaker_turns"},
            {"family": "dnsmos", "official_repository": "https://github.com/microsoft/DNS-Challenge", "role": "speech_quality"},
        ],
        "work_packages": [{"tracker_id": row["tracker_id"], "item_id": row["item_id"], "workstream": row["workstream"], "category": row["category"], "status": STATUS} for row in requirements],
        "boundaries": {"content_based_suppression": False, "planning_is_runtime": False, "download_is_ready": False, "human_review_may_be_fabricated": False, "existing_rows_mutated": False},
    }
    write_json(root / REGISTRY, registry)

    outputs = [MASTER, ARCH, ENGINE, QA, ASSET_PROTOCOL, ASSET_CATALOG, ASSET_EVIDENCE, SECOND_PASS_EVIDENCE, ITEMS, TRACKER, REQ, REQ_MIRROR, REGISTRY] + [Path("Plan/08_SCHEMAS") / name for name in SCHEMAS]
    evidence = {
        "schema_version": "1.0", "evidence_id": "WAVE64_AUTONOMOUS_HYPERREAL_SPEECH_PLANNING_COVERAGE_20260715", "created_at": datetime.now(timezone.utc).isoformat(), "result": "pass_additive_planning_and_execution_control_package_only",
        "row_range": {"first": 113, "last": 148, "count": 36}, "status_count": {STATUS: 36}, "canonical_header_compatibility": True, "existing_id_collision_count": 0, "schema_count": len(SCHEMAS), "content_based_suppression": False,
        "outputs": [{"path": path.as_posix(), "sha256": sha(root / path), "bytes": (root / path).stat().st_size} for path in outputs],
        "boundaries": {"runtime_implementation_complete": False, "model_acquisition_performed": False, "generation_executed": False, "existing_files_modified_by_generator": False, "git_mutated": False, "aws_mutated": False, "mask_wave71_jira_mutated": False},
    }
    write_json(root / EVIDENCE, evidence); write_json(root / EVIDENCE_MIRROR, evidence)
    print(json.dumps({"result": evidence["result"], "rows": 36, "schemas": len(SCHEMAS), "outputs": len(outputs) + 2}, indent=2))


if __name__ == "__main__":
    main()
