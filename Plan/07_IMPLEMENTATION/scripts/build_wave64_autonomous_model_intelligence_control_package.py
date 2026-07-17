#!/usr/bin/env python3
"""Build or check the additive Wave64 Rows221-260 model-intelligence package.

The default mode is read-only. Pass --write to materialize deterministic planning
artifacts. This package never imports model binaries, changes the Wave30 archives,
or claims runtime qualification.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFERRED_STATUS = (
    "Deferred_Pending_Complete_Model_Library_Download_Inventory_Verification_"
    "And_Main_Task_Acknowledgement"
)
PRE_ACTIVATION_STATIC_STATUS = "Planned_Static_Control_Allowed_Pre_Activation"
PACKAGE_ID = "wave64_autonomous_model_intelligence_rows221_260"
SCHEMA_VERSION = "1.0.0"
UPDATED_AT = "2026-07-16T19:30:00-05:00"
MAIN_TASK_ID = "019f422f-88b1-7382-872b-21de2089e983"
ACTIVATION_GATE_ID = "wave64_model_library_download_readiness_gate_v1"
ACTIVATION_PHASES = (
    "none",
    "staging",
    "qualification",
    "shadow_selection",
    "production_selection",
)
ACTIVE_GATE_STATE_TO_PHASE = {
    "active_staging_only": "staging",
    "active_qualification": "qualification",
    "active_shadow_selection": "shadow_selection",
    "active_production_selection": "production_selection",
}
PHASE_PERMISSION_KEYS = (
    "source_staging_import",
    "operational_registry_mutation",
    "execution_bundle_compilation",
    "qualification_execution",
    "benchmark_execution",
    "profile_and_certificate_issuance",
    "shadow_selection",
    "production_selection",
    "app_mode_runtime",
    "autonomous_role_shadow_eligibility",
    "autonomous_role_production_eligibility",
)
PRE_ACTIVATION_STATIC_ROWS = frozenset({221, 222})
AUTHORITY_REL = Path(
    "Plan/00_PROJECT_CONTROL/"
    "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_AND_SELECTION_MASTER_PLAN.md"
)
CANONICAL_AUTHORITY_FULL_PATH = str(
    PureWindowsPath("C:/Comfy_UI_Main") / PureWindowsPath(AUTHORITY_REL.as_posix())
)

ITEM_HEADER = [
    "Item_ID", "Item_Wave", "Item_Type", "Item_Title", "Item_Category",
    "Item_Domain", "Owner_Domain", "Autonomous_Required",
    "Human_Input_Allowed", "Human_Work_Allowed", "Codex_Action",
    "Implementation_Target", "Deliverable_Type", "Acceptance_Criteria",
    "QA_Gates_Required", "Visual_Review_Required", "Visual_Review_Method",
    "Test_Required", "Evidence_Required", "Runtime_Proof_Required",
    "EC2_Allowed", "Blocker_Policy", "Source_Plan_Root", "Citation_File",
    "Citation_Full_Path", "Citation_Section", "Citation_Line_Start",
    "Citation_Line_End", "Citation_Excerpt", "Source_Package", "Source_Type",
    "Source_File_Size", "Priority", "Risk_Level", "Status", "Created_From",
    "Notes", "Source_Key", "Source_File_Relative", "Coverage_Level",
    "Coverage_Audit_Status", "Ultra_Source_Coverage_Record",
]

TRACKER_HEADER = [
    "Tracker_ID", "Wave", "Phase", "Workstream", "Priority", "Risk_Level",
    "Owner_Role", "Environment", "Status", "Task_Name", "Detailed_Action",
    "Completion_Criteria", "Acceptance_Evidence", "Dependency_Prerequisite",
    "Validation_Method", "Output_Artifact", "Source_Path",
    "Related_Source_Paths", "Package_Top_Level_Directory",
    "Autonomous_Execution_Mode", "Human_Input_Allowed", "Human_Work_Allowed",
    "Codex_Desktop_Action", "QA_Strictness", "Visual_Review_Required",
    "Visual_Review_Method", "Test_Required", "Runtime_Proof_Required",
    "EC2_Allowed", "Preview_Required", "Final_Render_Gate", "Evidence_Path",
    "Citation_File", "Citation_Full_Path", "Citation_Section",
    "Citation_Line_Start", "Citation_Line_End", "Citation_Excerpt",
    "Source_Package", "Source_Type", "Source_Item_ID", "Blocker_Policy",
    "Rerun_Policy", "Status_Decision", "Notes", "Source_Key",
    "Source_File_Relative", "Coverage_Level", "Coverage_Audit_Status",
    "Ultra_Source_Coverage_Record",
]


@dataclass(frozen=True)
class PlanRow:
    number: int
    workstream: str
    phase: str
    domain: str
    category: str
    title: str
    action: str
    acceptance: str
    dependencies: tuple[int, ...]
    runtime_proof: bool = True
    review: str = "structured evidence review"
    priority: str = "P0"
    risk: str = "CRITICAL"


ROWS: list[PlanRow] = [
    PlanRow(221, "W64-MI-GOV", "MI-00", "source_governance", "archive_intake",
            "Wave30 Source Snapshot and Integrity Admission",
            "Register every multipart archive part, logical ZIP hash, patch relationship, inventory count, CRC result, source defect, and authority ceiling without importing model authority.",
            "The five-part stream and patch are hash-bound; unsafe paths, missing parts, duplicate names, manifest inconsistencies, and the metadata-only authority ceiling are explicit.",
            (149, 152, 165, 201), False, "archive manifest and inventory review"),
    PlanRow(222, "W64-MI-GOV", "MI-00", "source_governance", "authority",
            "Discovery, Operational, and Empirical Authority Tiers",
            "Separate source claims, normalized discovery metadata, installed operational assets, runtime observations, scoped certificates, and production selection authority.",
            "No Wave30 score, tag, copy-ready label, Civitai sample, or LLM statement can satisfy a runtime capability or promotion gate.",
            (150, 152, 165, 166, 209, 221), False, "authority-matrix review"),
    PlanRow(223, "W64-MI-GOV", "MI-00", "source_governance", "identity_lineage",
            "Model Asset Identity, Deduplication, and Version Lineage",
            "Resolve family, model, version, file, SHA-256, duplicate group, supersession, preferred revision, and storage identity as separate immutable entities.",
            "Aliases converge on one content identity while distinct revisions remain independently testable and historically addressable.",
            (43, 51, 152, 153, 221, 222), True, "dedupe and lineage fixture review"),
    PlanRow(224, "W64-MI-GOV", "MI-00", "source_governance", "lifecycle",
            "Model Lifecycle, Decision Authority, and Revocation State Machine",
            "Define discovery, admitted, installed, load-proven, benchmark-candidate, provisionally-certified, production-certified, suspended, revoked, rejected, and superseded transitions.",
            "Every transition has one authority, evidence prerequisites, expiry, rollback, and immutable event history; an LLM cannot certify or promote.",
            (150, 152, 197, 198, 201, 221, 222, 223), True, "state-transition and forbidden-authority tests"),

    PlanRow(225, "W64-MI-CAT", "MI-01", "catalog_intelligence", "asset_cards",
            "Strict Model Asset Intelligence Card",
            "Normalize Wave30, Civitai, local, S3, EC2, ComfyUI, hash, loader, taxonomy, prompt, trigger, compatibility, rights, availability, and evidence fields into a strict versioned card.",
            "Each card distinguishes claimed, inferred, observed, measured, and certified facts and carries source-level citations and freshness.",
            (44, 54, 165, 221, 222, 223), True, "schema, source crosswalk, and sample-card review"),
    PlanRow(226, "W64-MI-CAT", "MI-01", "catalog_intelligence", "ontology",
            "Capability, Role, Region, Modality, and Defect Ontology",
            "Map checkpoints, LoRAs, adapters, controls, video, audio, speech, Foley, upscalers, and analyzers to normalized pass intents, targets, defects, controls, and risks.",
            "The selector can query exact functional meaning across character, scene, image, video, audio, and AV work without relying on filenames.",
            (51, 54, 153, 155, 165, 173, 209, 225), True, "ontology coverage and ambiguity review"),
    PlanRow(227, "W64-MI-CAT", "MI-01", "catalog_intelligence", "hierarchy",
            "Family, Artifact, Revision, Bundle, and Certificate Separation",
            "Model discovery operates at family level while execution, evidence, and certification bind exact artifact revisions and execution bundles.",
            "No family summary is used as artifact proof and no artifact certificate silently transfers to another hash, workflow, adapter bundle, or runtime.",
            (152, 156, 165, 223, 224, 225), True, "cross-level leakage tests"),
    PlanRow(228, "W64-MI-CAT", "MI-01", "catalog_intelligence", "retrieval_index",
            "Hybrid Retrieval Index and Immutable Citation Projection",
            "Build structured filters, full-text search, embeddings, taxonomy joins, evidence joins, and materialized summaries over immutable source and empirical records.",
            "Every retrieved fact resolves to a versioned record and evidence reference; stale, conflicting, missing, and superseded records remain visible.",
            (51, 54, 198, 202, 221, 225, 226, 227), True, "retrieval precision, freshness, conflict, and citation tests"),

    PlanRow(229, "W64-MI-COMPAT", "MI-02", "compatibility_and_bundles", "hard_compatibility",
            "Engine, Base-Family, Loader, and Adapter Hard Compatibility Graph",
            "Represent exact compatible and incompatible edges for engines, checkpoints, LoRAs, VAEs, encoders, controls, schedulers, nodes, workflows, quantizations, and media adapters.",
            "Wrong-family assets and unproven cross-family assumptions fail before ranking with typed reasons.",
            (36, 44, 54, 65, 165, 166, 225, 226, 227), True, "positive and negative compatibility fixtures"),
    PlanRow(230, "W64-MI-COMPAT", "MI-02", "compatibility_and_bundles", "execution_bundle",
            "Exact Model Execution Bundle Compiler",
            "Compile one selectable unit from base model, LoRA stack, VAE, encoders, controls, workflow hash, node/runtime lock, sampler, precision, hardware, and prompt adapter.",
            "Selection and evidence bind the complete reproducible bundle rather than a model brand or standalone LoRA.",
            (156, 165, 166, 170, 171, 227, 229), True, "bundle reproducibility and substitution tests"),
    PlanRow(231, "W64-MI-COMPAT", "MI-02", "compatibility_and_bundles", "interaction_graph",
            "LoRA and Component Interaction, Conflict, and Attribution Graph",
            "Record pairwise and higher-order compatibility, dominance, cancellation, overcook, trigger collision, regional overlap, identity drift, and checkpoint dependence.",
            "Unknown combinations are not assumed safe; tested interactions are scoped and combinatorial testing is prioritized by use and risk.",
            (13, 14, 15, 165, 173, 174, 225, 229, 230), True, "designed-experiment and stack-ablation review"),
    PlanRow(232, "W64-MI-COMPAT", "MI-02", "compatibility_and_bundles", "runtime_envelope",
            "Availability, Residency, Resource, and Runtime Envelope",
            "Bind local/S3/EC2 availability, bytes, load time, VRAM/RAM, precision, offload, warm-cache affinity, concurrency, and failure telemetry to each bundle.",
            "No route assumes an absent asset or starts outside a measured resource envelope; quality is not silently downgraded under pressure.",
            (42, 44, 61, 62, 63, 166, 205, 206, 208, 230), True, "load, OOM, eviction, concurrency, and recovery tests"),

    PlanRow(233, "W64-MI-QUAL", "MI-03", "qualification", "funnel",
            "Progressive Model Qualification Funnel",
            "Implement source admission, static scan, install/hash proof, loader smoke, baseline A/B, parameter sweep, capability benchmark, stack-interaction, shadow, and certification stages.",
            "Expensive rendering is reserved for eligible high-value or high-uncertainty candidates while every skipped stage and authority ceiling is explicit.",
            (37, 38, 44, 54, 63, 165, 209, 210, 221, 224, 229, 230, 232), True, "stage-entry, stop, resume, and failure tests"),
    PlanRow(234, "W64-MI-QUAL", "MI-03", "qualification", "benchmark_corpus",
            "Canonical Multimodal Model Benchmark Corpus",
            "Create fixed and held-out cases for character identity, anatomy, skin, hair, clothing, pose, interaction, environment, motion, speech, Foley, audio, and AV behavior.",
            "Cases bind approved inputs, baselines, seeds, prompts, masks, controls, expected effects, protected invariants, metrics, and adjudicated outcomes.",
            (109, 147, 172, 183, 188, 192, 196, 209, 210, 225, 226, 233), True, "corpus coverage, leakage, and repeatability review"),
    PlanRow(235, "W64-MI-QUAL", "MI-03", "qualification", "sweeps",
            "Parameter, Trigger, Prompt, Weight, Denoise, and Seed Sweep Engine",
            "Generate reproducible baseline-controlled sweeps with early stopping, adaptive refinement, matched seeds, fixed workflows, and parameter-response curves.",
            "Best envelope, overcook threshold, instability, prompt sensitivity, and failure regions are measured without treating a single attractive output as proof.",
            (64, 167, 173, 174, 233, 234), True, "paired sweep, early-stop, and reproducibility tests"),
    PlanRow(236, "W64-MI-QUAL", "MI-03", "qualification", "certification",
            "Capability-Bucket Certificate, Expiry, and Requalification",
            "Certify exact bundles only for measured pass intent, target, checkpoint, stack, character count, mask tier, resolution, workflow, runtime, and hardware buckets.",
            "Certificates include sample floors, confidence, hard-gate results, validity window, exclusions, fallback, and revocation links; there is no universal best-model certificate.",
            (59, 63, 165, 172, 209, 211, 224, 230, 233, 234, 235), True, "certificate boundary, expiry, and misuse tests"),

    PlanRow(237, "W64-MI-SELECT", "MI-04", "contextual_selection", "context",
            "Canonical Model Selection Context Envelope",
            "Compile character revisions, scene/shot/take, pass objective, defect, target/protected scope, modality, references, controls, masks, quality, runtime, cost, risk, and downstream needs.",
            "Equivalent requests canonicalize identically while materially different targets, owners, engines, stacks, or constraints remain separate evidence buckets.",
            (153, 154, 155, 161, 162, 165, 168, 173, 189, 193, 225, 226), True, "context canonicalization and collision tests"),
    PlanRow(238, "W64-MI-SELECT", "MI-04", "contextual_selection", "candidate_generation",
            "Hard Eligibility Solver and Scalable Candidate Retrieval",
            "Apply lifecycle, availability, engine, bundle, certificate, mask, control, character, resource, evidence-freshness, and prohibited-combination filters before ranking.",
            "The solver can search thousands of assets without scoring ineligible entries and returns complete typed exclusion evidence.",
            (165, 166, 168, 228, 229, 230, 231, 232, 236, 237), True, "large-registry latency and zero-incompatible-selection tests"),
    PlanRow(239, "W64-MI-SELECT", "MI-04", "contextual_selection", "ranking",
            "Conservative Contextual Evidence Ranker and Pareto Frontier",
            "Rank eligible bundles with quality lower-confidence bounds, risk upper-confidence bounds, preservation, failures, resource cost, bridge cost, cache affinity, evidence freshness, and policy weights.",
            "Scores are replayable, calibrated, versioned, uncertainty-aware, and scoped; metadata priors cannot outrank measured production evidence.",
            (63, 167, 168, 208, 209, 211, 225, 228, 236, 237, 238), True, "offline replay, calibration, ranking-regret, and explanation tests"),
    PlanRow(240, "W64-MI-SELECT", "MI-04", "contextual_selection", "exploration",
            "Exploration, Candidate Branch, Abstention, and Fallback Policy",
            "Use bounded offline or shadow exploration for uncertain candidates, allow certified production champions for required passes, and emit abstention or explicit fallback when evidence is insufficient.",
            "Exploration never mutates an accepted parent or silently promotes a cold-start model; every candidate branch has budget, stop, QA, and learning eligibility.",
            (49, 63, 168, 175, 199, 203, 224, 233, 236, 238, 239), True, "cold-start, uncertainty, budget, fallback, and abstention tests"),

    PlanRow(241, "W64-MI-OBS", "MI-05", "observation_and_learning", "use_observation",
            "Per-Use Model and Bundle Observation Record",
            "Record why a bundle was selected, exact context, parents, prompts, controls, outputs, telemetry, deterministic metrics, critic observations, defects, repair outcome, and final decision.",
            "Every execution produces an attributable report even when rejected, blocked, cancelled, or excluded from learning.",
            (43, 51, 54, 156, 167, 184, 188, 192, 196, 198, 209, 230, 237, 239), True, "run-to-observation lineage tests"),
    PlanRow(242, "W64-MI-OBS", "MI-05", "observation_and_learning", "performance_profile",
            "Contextual Model Performance Profile and Living Report Card",
            "Aggregate eligible observations by exact capability bucket with sample counts, confidence intervals, response envelopes, success/failure modes, drift risks, recommended uses, and exclusions.",
            "Reports distinguish metadata priors, qualification trials, production observations, reviewer opinions, and certified facts and preserve all source evidence.",
            (54, 63, 209, 211, 225, 227, 233, 236, 241), True, "aggregation, confidence, provenance, and sparse-bucket tests"),
    PlanRow(243, "W64-MI-OBS", "MI-05", "observation_and_learning", "evidence_update",
            "Append-Only Evidence Recalculation and Continual Learning Job",
            "Recalculate profiles and ranking features from eligible immutable observations through versioned batch jobs rather than mutable online self-training.",
            "A production run cannot directly rewrite its own score; updates are reproducible, leakage-checked, reversible, and separated from holdout evaluation.",
            (43, 48, 51, 62, 198, 202, 207, 211, 224, 239, 241, 242), True, "rebuild, idempotency, holdout leakage, and rollback tests"),
    PlanRow(244, "W64-MI-OBS", "MI-05", "observation_and_learning", "drift_revocation",
            "Behavior Drift, Regression, Suspension, Revocation, and Rollback",
            "Detect model, workflow, runtime, dependency, prompt-template, data, reviewer, and workload drift and bind affected certificates, routes, cached results, and fallbacks.",
            "Critical drift suspends new selection immediately; requalification or rollback restores authority without rewriting prior decisions.",
            (47, 48, 49, 54, 59, 63, 152, 200, 207, 208, 212, 224, 236, 242, 243), True, "drift injection, blast-radius, revocation, and rollback tests"),

    PlanRow(245, "W64-MI-LLM", "MI-06", "autonomous_intelligence", "roles",
            "Autonomous Planner, Prompt, Router-Advisor, Reviewer, and Summarizer Role Contracts",
            "Define bounded planner, prompt composer, retrieval analyst, router advisor, defect classifier, VLM critic, audio critic, report writer, and summarizer inputs and outputs.",
            "Every role has exact authority, tools, context budget, schemas, escalation, and prohibited actions; no role promotes its own proposal or observation.",
            (150, 197, 201, 203, 224, 228, 237, 241), True, "role-routing and forbidden-authority tests"),
    PlanRow(246, "W64-MI-LLM", "MI-06", "autonomous_intelligence", "rag_memory",
            "Registry-Grounded RAG, Evidence Bundle, and Context Memory Contract",
            "Retrieve only versioned packages, model cards, certificates, benchmark results, failures, current run state, and policy records with citations, freshness, conflict, and compaction metadata.",
            "The LLM sees a bounded evidence packet rather than the whole library; missing or conflicting evidence causes uncertainty, alternatives, or abstention rather than invention.",
            (51, 54, 198, 202, 203, 207, 225, 228, 242, 245), True, "retrieval, injection, stale evidence, conflict, and context-limit tests"),
    PlanRow(247, "W64-MI-LLM", "MI-06", "autonomous_intelligence", "structured_tools",
            "Schema-Constrained Proposal, Prompt Package, Tool Gateway, and Policy Decision",
            "Require typed planner proposals, prompt packages, reviewer observations, tool actions, policy decisions, uncertainty, evidence IDs, alternatives, and denied-action records.",
            "Invalid IDs, unsupported claims, arbitrary paths, unallowlisted workflows, credential access, registry mutation, and promotion attempts fail deterministically.",
            (35, 48, 49, 51, 62, 197, 201, 202, 203, 224, 245, 246), True, "malformed output, hallucinated ID, path, injection, and authorization tests"),
    PlanRow(248, "W64-MI-LLM", "MI-06", "autonomous_intelligence", "serving_qualification",
            "Exact Self-Hosted Role Stack, Benchmark, Shadow, and Activation Control",
            "Register model, revision, runtime, quantization, chat template, parser, context, batching, hardware, fallback, and role-specific benchmark certificates.",
            "Only a role-qualified exact stack activates; planner and reviewer changes run in shadow, preserve prior decisions, and cannot silently change route or promotion behavior.",
            (44, 54, 63, 201, 202, 203, 204, 205, 208, 210, 211, 245, 246, 247), True, "held-out role, load, failover, shadow, drift, and rollback proof"),

    PlanRow(249, "W64-MI-QA", "MI-07", "model_qa", "multimodal_qa",
            "Deterministic, Perceptual, VLM, Audio-Critic, and Playback QA Ensemble",
            "Evaluate technical validity, effect accuracy, target fidelity, identity, anatomy, preservation, mask leakage, temporal behavior, audio quality, sync, resource stability, and lineage.",
            "Hard facts remain deterministic, critics emit scoped observations with uncertainty, and no single scalar or reviewer overrides a hard failure.",
            (16, 17, 18, 21, 30, 32, 33, 34, 60, 103, 106, 131, 141, 209, 211, 233, 234, 241, 245), True, "adjudicated image, video, audio, and AV panels"),
    PlanRow(250, "W64-MI-QA", "MI-07", "model_qa", "attribution",
            "Baseline, Counterfactual, Ablation, and Stack Attribution Protocol",
            "Compare no-adapter baselines, matched seeds, component ablations, alternative bundles, strength curves, and protected outputs to isolate actual model contribution.",
            "A model receives credit or blame only where the experiment can attribute the change; checkpoint, prompt, seed, mask, and stack confounding are recorded.",
            (63, 167, 172, 176, 209, 211, 231, 233, 234, 235, 241, 249), True, "paired comparison, ablation, and confound tests"),
    PlanRow(251, "W64-MI-QA", "MI-07", "model_qa", "calibration",
            "Critic Calibration, Disagreement, Bias, and Adjudication Control",
            "Measure false accept/reject rates, region and modality coverage, reviewer-version effects, uncertainty calibration, disagreement, and escalation against held-out adjudicated cases.",
            "Reviewer observations remain candidate evidence until calibration and policy authorize their exact use; disagreement is retained rather than averaged away.",
            (60, 63, 203, 204, 209, 210, 211, 245, 248, 249), True, "blinded held-out calibration and disagreement tests"),
    PlanRow(252, "W64-MI-QA", "MI-07", "model_qa", "decision_audit",
            "Selection Decision Audit, Model Report, and Promotion Gate",
            "Package candidate exclusions, rank features, uncertainty, selected bundle, execution, QA, comparison, observation, performance delta, certificate, and policy outcome.",
            "Every future run can explain why a model was selected, how it behaved, what changed in its report, and whether the evidence may affect future selection.",
            (35, 43, 51, 54, 59, 63, 150, 156, 167, 168, 198, 209, 211, 236, 239, 241, 242, 249, 250, 251), True, "complete decision-packet replay and audit"),

    PlanRow(253, "W64-MI-OPS", "MI-08", "operations", "stores",
            "Event Store, Evidence Store, Feature Store, and Projection Boundaries",
            "Persist source records, lifecycle events, bundles, trials, observations, certificates, reports, ranking features, decisions, and audit projections with immutable IDs and snapshots.",
            "State reconstructs from append-only events, feature values resolve to evidence, and no mutable cache becomes authority.",
            (43, 51, 62, 198, 200, 202, 207, 221, 224, 228, 241, 242, 243, 252), True, "empty-projection rebuild, hash, idempotency, and corruption tests"),
    PlanRow(254, "W64-MI-OPS", "MI-08", "operations", "qualification_scheduler",
            "Resource-Aware Batch Qualification and Active-Learning Scheduler",
            "Prioritize installed, high-value, high-usage, high-risk, coverage-gap, and uncertain candidates; schedule sweeps, comparisons, and requalification under GPU, storage, time, and cost budgets.",
            "The scheduler avoids all-pairs explosion, respects leases and thermal/resource envelopes, resumes safely, and records why work was prioritized or deferred.",
            (42, 61, 62, 63, 199, 200, 205, 206, 207, 208, 233, 234, 235, 240, 243), True, "priority, fairness, budget, crash, cancellation, and resume tests"),
    PlanRow(255, "W64-MI-OPS", "MI-08", "operations", "operator_ux",
            "Model Explorer, Qualification Queue, Comparison, Report, and Route-Explanation UX",
            "Expose library health, source authority, availability, compatibility, test coverage, certificates, reports, failures, drift, decisions, and side-by-side media without raw node or credential exposure.",
            "Operators can trace every claim and approve policy changes or exceptions without manually editing graphs or registry bytes.",
            (47, 51, 107, 145, 202, 213, 214, 215, 216, 228, 242, 252, 253, 254), True, "scripted operator journeys and accessibility review"),
    PlanRow(256, "W64-MI-OPS", "MI-08", "operations", "observability_security",
            "Telemetry, Capacity, Security, Backup, Recovery, and Degraded-Mode Control",
            "Monitor ingestion, index freshness, queue depth, load failures, QA latency, ranking drift, certificate health, storage, costs, untrusted metadata, model scans, tools, and recovery points.",
            "Outage or saturation changes routes only through declared policies; source text and model files cannot obtain tool, credential, registry, or promotion authority.",
            (40, 41, 42, 47, 48, 49, 61, 62, 63, 200, 205, 206, 207, 208, 212, 244, 247, 253, 254), True, "outage, restore, saturation, injection, and least-authority tests"),

    PlanRow(257, "W64-MI-REL", "MI-09", "release_and_adoption", "dry_run",
            "Wave30 Dry-Run Import, Reconciliation, and Exception Report",
            "Map all 7,282 artifacts and 3,770 families into discovery records, reconcile 675-member archive defects and selector/status disagreements, and emit no operational promotion.",
            "Counts, hashes, duplicates, missing fields, blocked rows, stale reports, absent visual-test assets, and migration mappings reconcile or produce typed exceptions.",
            (50, 51, 57, 58, 212, 217, 221, 222, 223, 225, 226, 227, 228), True, "full dry-run counts, schema, and exception reconciliation"),
    PlanRow(258, "W64-MI-REL", "MI-09", "release_and_adoption", "pilot",
            "Copy-Ready and High-Value Pilot Qualification Tranche",
            "Hash-verify and qualify the 187 Wave30 copy-ready candidates plus a stratified set of installed/high-value models across priority capability buckets.",
            "The pilot produces real bundles, A/B evidence, reports, scoped certificates, failures, cost measurements, and rollback without treating copy-ready as production-ready.",
            (37, 38, 44, 54, 63, 218, 229, 230, 232, 233, 234, 235, 236, 249, 250, 251, 252, 254, 257), True, "real pilot render/playback and evidence review"),
    PlanRow(259, "W64-MI-REL", "MI-09", "release_and_adoption", "progressive_expansion",
            "Value, Coverage, Risk, and Uncertainty-Driven Library Expansion",
            "Expand qualification by production demand, capability gaps, model diversity, uncertainty, expected value of information, and resource budget rather than archive order.",
            "Coverage grows measurably while unqualified long-tail assets remain discoverable, on-demand-testable, and excluded from certified production routes.",
            (219, 233, 234, 236, 239, 240, 242, 243, 244, 249, 251, 252, 254, 258), True, "coverage, regret, cost, drift, and long-tail on-demand tests"),
    PlanRow(260, "W64-MI-REL", "MI-09", "release_and_adoption", "release",
            "Autonomous Model Intelligence Release Certification and Main-Task Adoption",
            "Certify schemas, stores, ingestion, bundles, qualification, selection, LLM roles, QA, reports, App UX, recovery, security, rollback, and preservation handoff.",
            "Rows221-259 are traceable; runtime claims are evidence-backed; no critical gate is open; the main task formally adopts or rejects every additive artifact.",
            (59, 60, 66, 112, 148, 204, 208, 212, 216, 220, 224, 236, 244, 248, 252, 255, 256, 257, 258, 259), True, "independent end-to-end selection, generation, QA, report, recovery, and rollback review"),
]


def row_requires_activation(row: PlanRow) -> bool:
    """Return whether a row is blocked by the model-library readiness gate."""
    return row.number not in PRE_ACTIVATION_STATIC_ROWS


def row_status(row: PlanRow) -> str:
    if row_requires_activation(row):
        return DEFERRED_STATUS
    return PRE_ACTIVATION_STATIC_STATUS


def row_runtime_truth(row: PlanRow) -> str:
    if row_requires_activation(row):
        return "deferred_prerequisites_not_satisfied"
    return "not_started_static_control_allowed"


SOURCE_SNAPSHOT: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "record_type": "model_library_source_snapshot",
    "source_snapshot_id": "source_wave30_final_production_cumulative_20260716",
    "revision": "1",
    "status": "discovery_metadata_only",
    "created_at": UPDATED_AT,
    "source_name": "Ultimate LoRA Model OS Wave30 Final Production Cumulative",
    "content_based_suppression": False,
    "parts": [
        {"part": 1, "name": "Ultimate_LoRA_Model_OS_Wave30_Final_Production_Cumulative.zip.part001", "bytes": 78643200, "sha256": "c0d0c9d29b37930bc601294ec8ba63731d27182579f713a328f90d0bb17a7c2c"},
        {"part": 2, "name": "Ultimate_LoRA_Model_OS_Wave30_Final_Production_Cumulative.zip.part002", "bytes": 78643200, "sha256": "c9b8f6e36232af53d89a1d652c6b556e55b2d49c1fc25b0755d161e04a3bdda8"},
        {"part": 3, "name": "Ultimate_LoRA_Model_OS_Wave30_Final_Production_Cumulative.zip.part003", "bytes": 78643200, "sha256": "57e06d723b368496db3e32553817e17b88bcb0e2cbe32eb63b8298eba5294d3d"},
        {"part": 4, "name": "Ultimate_LoRA_Model_OS_Wave30_Final_Production_Cumulative.zip.part004", "bytes": 78643200, "sha256": "4e440af6fc438921333d587ff55b467a8d9aa74db65c145747fa1e8dd2ef34d0"},
        {"part": 5, "name": "Ultimate_LoRA_Model_OS_Wave30_Final_Production_Cumulative.zip.part005", "bytes": 53320477, "sha256": "90915c966f6d06cf473d940a059c86ae7ee0c94ea835cb802a31385ed587b8b5"},
    ],
    "logical_archive": {
        "bytes": 367893277,
        "sha256": "ab87f86c120085834d86b004e886e733a383ac9246f5f0f34087b6627d373351",
        "zip_entries": 675,
        "zip64": False,
        "crc_and_decompression_test": "pass",
        "uncompressed_bytes": 2577809722,
        "unsafe_paths": 0,
        "duplicate_names": 0,
    },
    "patch_archive": {
        "name": "Ultimate_LoRA_Model_OS_Wave30_Final_Production_PATCH_ONLY.zip",
        "bytes": 13243618,
        "sha256": "19add2d6e5bd298ad9cb985876e8c4b684a4d2e048624dcb19d75b4dfe958d26",
        "entries": 39,
        "crc_and_decompression_test": "pass",
        "relationship": "exact_member_subset_not_binary_delta",
    },
    "inventory": {
        "artifact_rows": 7282,
        "model_family_rows": 3770,
        "selector_rows": 7282,
        "selector_profiles": 13,
        "precomputed_recommendations": 650,
        "manual_review_rows": 29593,
        "quarantine_rows": 376,
        "production_copy_ready_rows": 187,
        "caution_first_pass_rows": 5056,
        "manual_review_required_rows": 2039,
        "all_artifact_qa_status": "open",
        "model_binary_count": 0,
    },
    "engine_counts": {
        "flux": 3278, "pony": 890, "wan_video": 875, "sdxl": 836,
        "sd15": 353, "zimage": 336, "illustrious": 255,
        "hunyuan_video": 132, "anima": 125, "ltxv": 90,
    },
    "known_source_issues": [
        "cumulative root MANIFEST identifies the patch and claims 39 rather than 675 files",
        "cumulative root README retains a Wave 08 title",
        "classification accuracy is heuristic internal consistency rather than measured generative behavior",
        "all 7282 artifact QA states are open and all rows require caution",
        "Wave12L planned 71800 renders and 4978 jobs but generated no images",
        "Wave12L referenced job-plan, weight-sweep, score-template, prompt-template, and rubric assets are absent",
        "selector eligibility and production-status summaries contain a 45-row disagreement requiring reconciliation",
        "manual review and quarantine registries contain no accumulated reviewer notes",
    ],
    "authority": {
        "maximum": "discovery_metadata",
        "runtime_selection_allowed": False,
        "promotion_allowed": False,
        "requires_independent_hash_scan_install_load_benchmark_certificate": True,
        "activation_gate_id": ACTIVATION_GATE_ID,
        "complete_model_download_declared": False,
        "complete_binary_inventory_verified": False,
        "main_task_activation_acknowledged": False,
        "bulk_ingestion_or_qualification_allowed": False,
    },
    "provenance": {
        "producer": "codex_archive_read_only_audit",
        "source_refs": [
            "C:/Users/kevin/Downloads/Ultimate_LoRA_Model_OS_Wave30_Final_Production_Cumulative.zip.part001..005",
            "C:/Users/kevin/Downloads/Ultimate_LoRA_Model_OS_Wave30_Final_Production_PATCH_ONLY.zip",
        ],
        "evidence_refs": [
            "Wave30 final production statistics",
            "Wave12L visual-test planning",
            "Wave26 selector scoring configuration",
            "Wave29 classification accuracy methodology",
        ],
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")


def text_bytes(value: str) -> bytes:
    return value.strip().replace("\r\n", "\n").encode("utf-8") + b"\n"


def csv_bytes(header: list[str], rows: list[dict[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=header, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


COMMON_SCHEMA_ID = "https://comfy-ui-main.local/schemas/model-intelligence-common/1.0.0"


def base_properties(record_type: str, id_field: str) -> dict[str, Any]:
    return {
        "schema_version": {"const": SCHEMA_VERSION},
        "record_type": {"const": record_type},
        id_field: {"type": "string", "minLength": 1},
        "revision": {"type": "string", "minLength": 1},
        "status": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "format": "date-time"},
        "provenance": {"$ref": COMMON_SCHEMA_ID + "#/$defs/Provenance"},
    }


def record_schema(
    title: str,
    slug: str,
    record_type: str,
    id_field: str,
    extra_properties: dict[str, Any],
    required_extra: list[str],
) -> dict[str, Any]:
    props = base_properties(record_type, id_field)
    props.update(extra_properties)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://comfy-ui-main.local/schemas/" + slug + "/1.0.0",
        "title": title,
        "type": "object",
        "required": [
            "schema_version", "record_type", id_field, "revision", "status",
            "created_at", *required_extra, "provenance",
        ],
        "properties": props,
        "additionalProperties": False,
    }


def build_schemas() -> dict[str, dict[str, Any]]:
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    record_ref = {"$ref": COMMON_SCHEMA_ID + "#/$defs/RecordRef"}
    evidence_ref = {"$ref": COMMON_SCHEMA_ID + "#/$defs/EvidenceRef"}
    metric = {"$ref": COMMON_SCHEMA_ID + "#/$defs/MetricObservation"}
    scope = {"$ref": COMMON_SCHEMA_ID + "#/$defs/CapabilityScope"}
    control_and_mask_requirements = {
        "$ref": COMMON_SCHEMA_ID + "#/$defs/ControlAndMaskRequirements"
    }

    def typed_record_ref(record_type: str) -> dict[str, Any]:
        return {
            "allOf": [
                record_ref,
                {
                    "type": "object",
                    "properties": {"record_type": {"const": record_type}},
                    "required": ["record_type"],
                },
            ]
        }

    def hash_bound_record_ref(record_type: str) -> dict[str, Any]:
        return {
            "allOf": [
                {"$ref": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef"},
                {
                    "type": "object",
                    "properties": {"record_type": {"const": record_type}},
                    "required": ["record_type"],
                },
            ]
        }
    common = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": COMMON_SCHEMA_ID,
        "title": "Wave64 Model Intelligence Common Definitions",
        "$defs": {
            "Sha256": sha,
            "RecordRef": {
                "type": "object",
                "required": ["record_type", "record_id", "revision"],
                "properties": {
                    "record_type": {"type": "string", "minLength": 1},
                    "record_id": {"type": "string", "minLength": 1},
                    "revision": {"type": "string", "minLength": 1},
                    "sha256": {"oneOf": [sha, {"type": "null"}]},
                    "path_or_uri": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "ImmutableRecordRef": {
                "type": "object",
                "required": [
                    "schema_id", "record_type", "record_id", "revision",
                    "sha256", "bytes", "path_or_uri",
                ],
                "properties": {
                    "schema_id": {"type": "string", "minLength": 1},
                    "record_type": {"type": "string", "minLength": 1},
                    "record_id": {"type": "string", "minLength": 1},
                    "revision": {"type": "string", "minLength": 1},
                    "sha256": sha,
                    "bytes": {"type": "integer", "minimum": 1},
                    "path_or_uri": {"type": "string", "minLength": 1},
                },
                "additionalProperties": False,
            },
            "EvidenceRef": {
                "type": "object",
                "required": ["evidence_id", "authority_tier"],
                "properties": {
                    "evidence_id": {"type": "string", "minLength": 1},
                    "authority_tier": {
                        "enum": [
                            "source_claim", "discovery_metadata", "static_measurement",
                            "runtime_observation", "qualification_measurement",
                            "adjudicated_review", "scoped_certificate",
                        ]
                    },
                    "sha256": {"oneOf": [sha, {"type": "null"}]},
                    "observed_at": {"type": ["string", "null"], "format": "date-time"},
                    "fresh_until": {"type": ["string", "null"], "format": "date-time"},
                },
                "additionalProperties": False,
            },
            "CapabilityScope": {
                "type": "object",
                "required": [
                    "modality", "pass_intent", "target_types", "engine_family",
                    "character_count_min", "character_count_max",
                ],
                "properties": {
                    "modality": {"enum": ["image", "video", "audio", "av", "analysis"]},
                    "pass_intent": {"type": "string", "minLength": 1},
                    "target_types": {
                        "type": "array", "items": {"type": "string"},
                        "minItems": 1, "uniqueItems": True,
                    },
                    "engine_family": {"type": "string", "minLength": 1},
                    "base_model_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "character_count_min": {"type": "integer", "minimum": 0},
                    "character_count_max": {"type": "integer", "minimum": 0},
                    "mask_authority_tiers": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "resolution_or_duration_bucket": {"type": "string"},
                    "hardware_envelope_id": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "MetricObservation": {
                "type": "object",
                "required": ["metric_id", "value", "direction", "authority"],
                "properties": {
                    "metric_id": {"type": "string", "minLength": 1},
                    "value": {"type": "number"},
                    "unit": {"type": ["string", "null"]},
                    "direction": {"enum": ["higher_is_better", "lower_is_better", "target_range"]},
                    "authority": {
                        "enum": [
                            "deterministic", "calibrated_metric", "vlm_observation",
                            "audio_critic_observation", "human_adjudication",
                        ]
                    },
                    "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                    "evidence_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                },
                "additionalProperties": False,
            },
            "ControlAndMaskRequirements": {
                "type": "object",
                "required": [
                    "mask_applicability", "mask_binding_ids",
                    "required_access_modes", "required_truth_tiers",
                    "required_control_types", "ownership_required",
                    "person_index_required", "ontology_version",
                    "source_coordinate_space", "target_coordinate_space",
                    "transform_validation_required", "certificate_required",
                    "source_image_hash_match_required",
                    "mode_b_outputs_are_draft_only",
                    "authority_upgrade_allowed", "writes_gold",
                    "promotion_gate_policy",
                ],
                "properties": {
                    "mask_applicability": {
                        "enum": ["required", "optional", "not_applicable"]
                    },
                    "mask_binding_ids": {
                        "type": "array", "items": {"type": "string", "minLength": 1},
                        "uniqueItems": True,
                    },
                    "required_access_modes": {
                        "type": "array", "uniqueItems": True,
                        "items": {
                            "enum": [
                                "mode_a_package_read", "mode_b_live_predict",
                                "mode_b_live_refine",
                            ]
                        },
                    },
                    "required_truth_tiers": {
                        "type": "array", "uniqueItems": True,
                        "items": {
                            "enum": [
                                "gold", "approved_package", "certified_machine",
                                "machine_draft", "manual_draft", "rejected",
                            ]
                        },
                    },
                    "required_control_types": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "ownership_required": {"type": "boolean"},
                    "person_index_required": {"type": "boolean"},
                    "ontology_version": {"type": ["string", "null"]},
                    "source_coordinate_space": {"type": ["string", "null"]},
                    "target_coordinate_space": {"type": ["string", "null"]},
                    "transform_validation_required": {"type": "boolean"},
                    "certificate_required": {"type": "boolean"},
                    "source_image_hash_match_required": {"type": "boolean"},
                    "mode_b_outputs_are_draft_only": {"const": True},
                    "authority_upgrade_allowed": {"const": False},
                    "writes_gold": {"const": False},
                    "promotion_gate_policy": {
                        "enum": [
                            "prohibited",
                            "requires_separately_validated_mode_a_binding",
                        ]
                    },
                },
                "allOf": [
                    {
                        "if": {
                            "properties": {"mask_applicability": {"const": "required"}},
                            "required": ["mask_applicability"],
                        },
                        "then": {
                            "properties": {
                                "mask_binding_ids": {"minItems": 1},
                                "required_access_modes": {"minItems": 1},
                                "required_truth_tiers": {"minItems": 1},
                                "ownership_required": {"const": True},
                                "person_index_required": {"const": True},
                                "transform_validation_required": {"const": True},
                                "certificate_required": {"const": True},
                                "source_image_hash_match_required": {"const": True},
                            }
                        },
                    },
                    {
                        "if": {
                            "properties": {"mask_applicability": {"const": "not_applicable"}},
                            "required": ["mask_applicability"],
                        },
                        "then": {
                            "properties": {
                                "mask_binding_ids": {"maxItems": 0},
                                "required_access_modes": {"maxItems": 0},
                                "required_truth_tiers": {"maxItems": 0},
                                "certificate_required": {"const": False},
                                "promotion_gate_policy": {"const": "prohibited"},
                            }
                        },
                    },
                ],
                "additionalProperties": False,
            },
            "Provenance": {
                "type": "object",
                "required": ["producer", "source_refs"],
                "properties": {
                    "producer": {"type": "string", "minLength": 1},
                    "source_refs": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "evidence_refs": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "registry_snapshot_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                },
                "additionalProperties": False,
            },
        },
    }
    schemas: dict[str, dict[str, Any]] = {
        "model_intelligence_common.schema.json": common,
    }

    schemas["model_library_source_snapshot.schema.json"] = record_schema(
        "Wave64 Model Library Source Snapshot",
        "model-library-source-snapshot",
        "model_library_source_snapshot",
        "source_snapshot_id",
        {
            "source_name": {"type": "string", "minLength": 1},
            "content_based_suppression": {"const": False},
            "parts": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["part", "name", "bytes", "sha256"],
                    "properties": {
                        "part": {"type": "integer", "minimum": 1},
                        "name": {"type": "string"},
                        "bytes": {"type": "integer", "minimum": 1},
                        "sha256": sha,
                    },
                    "additionalProperties": False,
                },
            },
            "logical_archive": {"type": "object"},
            "patch_archive": {"type": "object"},
            "inventory": {"type": "object"},
            "engine_counts": {
                "type": "object",
                "additionalProperties": {"type": "integer", "minimum": 0},
            },
            "known_source_issues": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "authority": {
                "type": "object",
                "required": [
                    "maximum", "runtime_selection_allowed", "promotion_allowed",
                    "requires_independent_hash_scan_install_load_benchmark_certificate",
                    "activation_gate_id", "complete_model_download_declared",
                    "complete_binary_inventory_verified",
                    "main_task_activation_acknowledged",
                    "bulk_ingestion_or_qualification_allowed",
                ],
                "properties": {
                    "maximum": {"const": "discovery_metadata"},
                    "runtime_selection_allowed": {"const": False},
                    "promotion_allowed": {"const": False},
                    "requires_independent_hash_scan_install_load_benchmark_certificate": {"const": True},
                    "activation_gate_id": {"const": ACTIVATION_GATE_ID},
                    "complete_model_download_declared": {"const": False},
                    "complete_binary_inventory_verified": {"const": False},
                    "main_task_activation_acknowledged": {"const": False},
                    "bulk_ingestion_or_qualification_allowed": {"const": False},
                },
                "additionalProperties": False,
            },
        },
        [
            "source_name", "content_based_suppression", "parts", "logical_archive",
            "patch_archive", "inventory", "known_source_issues", "authority",
        ],
    )

    schemas["model_asset_intelligence_card.schema.json"] = record_schema(
        "Wave64 Model Asset Intelligence Card",
        "model-asset-intelligence-card",
        "model_asset_intelligence_card",
        "model_asset_card_id",
        {
            "asset_identity": {
                "type": "object",
                "required": ["asset_id", "family_id", "asset_type", "revision_id", "sha256"],
                "properties": {
                    "asset_id": {"type": "string"},
                    "family_id": {"type": "string"},
                    "asset_type": {"type": "string"},
                    "revision_id": {"type": "string"},
                    "sha256": {"oneOf": [sha, {"type": "null"}]},
                    "aliases": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                    "duplicate_group_id": {"type": ["string", "null"]},
                    "supersedes_asset_id": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "source_claims": {"type": "array", "items": evidence_ref},
            "engine_family_claims": {"type": "array", "items": {"type": "string"}},
            "capability_hypotheses": {"type": "array", "items": {"type": "object"}},
            "trigger_and_parameter_priors": {"type": "object"},
            "availability": {"type": "object"},
            "lifecycle_axes": {"type": "object"},
            "evidence_authority_ceiling": {
                "enum": [
                    "discovery_metadata", "static_verified", "runtime_observed",
                    "qualification_candidate", "scoped_certified",
                ]
            },
            "known_conflicts": {"type": "array", "items": {"type": "string"}},
        },
        [
            "asset_identity", "source_claims", "engine_family_claims",
            "capability_hypotheses", "availability", "lifecycle_axes",
            "evidence_authority_ceiling",
        ],
    )

    schemas["model_compatibility_edge.schema.json"] = record_schema(
        "Wave64 Model Compatibility Edge",
        "model-compatibility-edge",
        "model_compatibility_edge",
        "compatibility_edge_id",
        {
            "source_component": record_ref,
            "target_component": record_ref,
            "relation": {
                "enum": ["compatible", "incompatible", "conditional", "unknown"]
            },
            "conditions": {"type": "array", "items": {"type": "string"}},
            "scope": scope,
            "evidence": {"type": "array", "items": evidence_ref},
            "authority": {
                "enum": ["metadata_hypothesis", "static_proven", "runtime_proven", "certified"]
            },
        },
        ["source_component", "target_component", "relation", "scope", "evidence", "authority"],
    )

    schemas["model_execution_bundle.schema.json"] = record_schema(
        "Wave64 Exact Model Execution Bundle",
        "model-execution-bundle",
        "model_execution_bundle",
        "execution_bundle_id",
        {
            "engine_family": {"type": "string", "minLength": 1},
            "base_model": record_ref,
            "components": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["slot", "record_ref", "order", "parameters"],
                    "properties": {
                        "slot": {"type": "string"},
                        "record_ref": record_ref,
                        "order": {"type": "integer", "minimum": 0},
                        "parameters": {"type": "object"},
                        "target_instance_ids": {"type": "array", "items": {"type": "string"}},
                        "target_regions": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": False,
                },
            },
            "workflow_ref": record_ref,
            "runtime_ref": record_ref,
            "prompt_profile_ref": {"oneOf": [record_ref, {"type": "null"}]},
            "bundle_sha256": sha,
            "compatibility_edge_ids": {"type": "array", "items": {"type": "string"}},
            "certificate_ids": {"type": "array", "items": {"type": "string"}},
            "mask_and_control_capabilities": {
                "type": "object",
                "required": [
                    "supported_access_modes", "supported_truth_tiers",
                    "supported_control_types", "supports_per_instance_ownership",
                    "supports_protected_mask", "supports_transform_chain",
                    "mode_b_authority_ceiling", "writes_gold",
                ],
                "properties": {
                    "supported_access_modes": {
                        "type": "array", "uniqueItems": True,
                        "items": {
                            "enum": [
                                "mode_a_package_read", "mode_b_live_predict",
                                "mode_b_live_refine",
                            ]
                        },
                    },
                    "supported_truth_tiers": {
                        "type": "array", "uniqueItems": True,
                        "items": {
                            "enum": [
                                "gold", "approved_package", "certified_machine",
                                "machine_draft", "manual_draft",
                            ]
                        },
                    },
                    "supported_control_types": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "supports_per_instance_ownership": {"type": "boolean"},
                    "supports_protected_mask": {"type": "boolean"},
                    "supports_transform_chain": {"type": "boolean"},
                    "mode_b_authority_ceiling": {"const": "machine_draft"},
                    "writes_gold": {"const": False},
                },
                "additionalProperties": False,
            },
            "no_silent_substitution": {"const": True},
        },
        [
            "engine_family", "base_model", "components", "workflow_ref",
            "runtime_ref", "bundle_sha256", "compatibility_edge_ids",
            "certificate_ids", "mask_and_control_capabilities",
            "no_silent_substitution",
        ],
    )

    schemas["model_qualification_plan.schema.json"] = record_schema(
        "Wave64 Model Qualification Plan",
        "model-qualification-plan",
        "model_qualification_plan",
        "qualification_plan_id",
        {
            "target_bundle_ref": record_ref,
            "current_authority": {"type": "string"},
            "requested_authority": {"type": "string"},
            "stages": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["stage_id", "stage_type", "entry_gates", "exit_gates", "stop_conditions"],
                    "properties": {
                        "stage_id": {"type": "string"},
                        "stage_type": {
                            "enum": [
                                "catalog_qa", "binary_qa", "load_smoke",
                                "functional_ab", "bucket_benchmark",
                                "bundle_interaction", "cross_engine_bridge",
                                "shadow_routing",
                            ]
                        },
                        "entry_gates": {"type": "array", "items": {"type": "string"}},
                        "exit_gates": {"type": "array", "items": {"type": "string"}},
                        "stop_conditions": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": False,
                },
            },
            "benchmark_suite_ids": {"type": "array", "items": {"type": "string"}},
            "resource_budget": {"type": "object"},
            "priority_evidence": {"type": "object"},
        },
        [
            "target_bundle_ref", "current_authority", "requested_authority",
            "stages", "benchmark_suite_ids", "resource_budget",
        ],
    )

    schemas["model_benchmark_suite.schema.json"] = record_schema(
        "Wave64 Model Benchmark Suite",
        "model-benchmark-suite",
        "model_benchmark_suite",
        "benchmark_suite_id",
        {
            "capability_scope": scope,
            "cases": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "case_id", "input_artifact_ids", "baseline_bundle_id",
                        "expected_changes", "protected_invariants", "seed_set",
                    ],
                    "properties": {
                        "case_id": {"type": "string"},
                        "input_artifact_ids": {"type": "array", "items": {"type": "string"}},
                        "baseline_bundle_id": {"type": "string"},
                        "expected_changes": {"type": "array", "items": {"type": "string"}},
                        "protected_invariants": {"type": "array", "items": {"type": "string"}},
                        "seed_set": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
                        "mask_binding_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": False,
                },
            },
            "parameter_sweeps": {"type": "object"},
            "metric_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "gate_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "holdout_policy": {"type": "object"},
        },
        [
            "capability_scope", "cases", "parameter_sweeps", "metric_ids",
            "gate_ids", "holdout_policy",
        ],
    )

    schemas["model_benchmark_result.schema.json"] = record_schema(
        "Wave64 Model Benchmark Result",
        "model-benchmark-result",
        "model_benchmark_result",
        "benchmark_result_id",
        {
            "qualification_plan_ref": record_ref,
            "benchmark_suite_ref": record_ref,
            "execution_bundle_ref": hash_bound_record_ref("model_execution_bundle"),
            "case_results": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "aggregate_metrics": {"type": "array", "items": metric},
            "hard_gate_results": {"type": "array", "items": {"type": "object"}},
            "failure_taxonomy": {"type": "array", "items": {"type": "string"}},
            "resource_telemetry": {"type": "object"},
            "output_artifact_ids": {"type": "array", "items": {"type": "string"}},
            "learning_eligibility": {"enum": ["eligible", "ineligible", "pending_adjudication"]},
        },
        [
            "qualification_plan_ref", "benchmark_suite_ref", "execution_bundle_ref",
            "case_results", "aggregate_metrics", "hard_gate_results",
            "resource_telemetry", "learning_eligibility",
        ],
    )

    capability_certificate = record_schema(
        "Wave64 Model Capability Certificate",
        "model-capability-certificate",
        "model_capability_certificate",
        "capability_certificate_id",
        {
            "execution_bundle_ref": hash_bound_record_ref("model_execution_bundle"),
            "capability_scope": scope,
            "benchmark_result_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "sample_counts": {
                "type": "object",
                "required": ["paired_outputs", "distinct_cases", "distinct_seeds"],
                "properties": {
                    "paired_outputs": {"type": "integer", "minimum": 1},
                    "distinct_cases": {"type": "integer", "minimum": 1},
                    "distinct_seeds": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            "confidence_bounds": {
                "type": "object",
                "required": ["quality_lcb", "serious_failure_rate_ucb", "confidence_level"],
                "properties": {
                    "quality_lcb": {"type": "number"},
                    "serious_failure_rate_ucb": {"type": "number", "minimum": 0, "maximum": 1},
                    "confidence_level": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
                },
                "additionalProperties": False,
            },
            "parameter_envelope": {
                "type": "object",
                "required": ["parameter_schema_id", "minimums", "maximums", "tested_values_sha256"],
                "properties": {
                    "parameter_schema_id": {"type": "string", "minLength": 1},
                    "minimums": {"type": "object", "additionalProperties": {"type": "number"}},
                    "maximums": {"type": "object", "additionalProperties": {"type": "number"}},
                    "tested_values_sha256": sha,
                },
                "additionalProperties": False,
            },
            "hard_gate_status": {"enum": ["pass", "fail"]},
            "authority": {
                "enum": ["provisional_candidate", "shadow_challenger", "production_eligible"]
            },
            "valid_from": {"type": "string", "format": "date-time"},
            "valid_until": {"type": "string", "format": "date-time"},
            "exclusions": {"type": "array", "items": {"type": "string"}},
            "revocation_event_id": {"type": ["string", "null"]},
        },
        [
            "execution_bundle_ref", "capability_scope", "benchmark_result_refs",
            "sample_counts", "confidence_bounds", "parameter_envelope",
            "hard_gate_status", "authority", "valid_from", "valid_until",
            "exclusions",
        ],
    )
    capability_certificate["allOf"] = [
        {
            "if": {
                "properties": {"authority": {"const": "production_eligible"}},
                "required": ["authority"],
            },
            "then": {
                "properties": {
                    "hard_gate_status": {"const": "pass"},
                    "sample_counts": {
                        "properties": {
                            "paired_outputs": {"minimum": 50},
                            "distinct_cases": {"minimum": 10},
                        }
                    },
                }
            },
        }
    ]
    schemas["model_capability_certificate.schema.json"] = capability_certificate

    schemas["model_selection_context.schema.json"] = record_schema(
        "Wave64 Model Selection Context",
        "model-selection-context",
        "model_selection_context",
        "selection_context_id",
        {
            "job_id": {"type": "string"},
            "run_id": {"type": "string"},
            "pass_id": {"type": "string"},
            "scene_id": {"type": "string"},
            "shot_id": {"type": "string"},
            "take_id": {"type": "string"},
            "character_revision_ids": {"type": "array", "items": {"type": "string"}},
            "character_instance_ids": {"type": "array", "items": {"type": "string"}},
            "capability_scope": scope,
            "defect_ids": {"type": "array", "items": {"type": "string"}},
            "target_contract": {
                "type": "object",
                "required": [
                    "owner_instance_ids", "target_types", "target_regions",
                    "target_mask_binding_ids", "coordinate_space",
                    "allow_change_outside_target",
                ],
                "properties": {
                    "owner_instance_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "target_types": {
                        "type": "array", "items": {"type": "string"},
                        "minItems": 1, "uniqueItems": True,
                    },
                    "target_regions": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "target_mask_binding_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "coordinate_space": {"type": ["string", "null"]},
                    "allow_change_outside_target": {"const": False},
                },
                "additionalProperties": False,
            },
            "protected_contract": {
                "type": "object",
                "required": [
                    "protected_instance_ids", "protected_regions",
                    "protected_mask_binding_ids", "preserve_identity",
                    "preserve_morphology", "preserve_pose", "preserve_camera",
                    "preserve_background", "outside_target_metric_ids",
                ],
                "properties": {
                    "protected_instance_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "protected_regions": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "protected_mask_binding_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                    "preserve_identity": {"type": "boolean"},
                    "preserve_morphology": {"type": "boolean"},
                    "preserve_pose": {"type": "boolean"},
                    "preserve_camera": {"type": "boolean"},
                    "preserve_background": {"type": "boolean"},
                    "outside_target_metric_ids": {
                        "type": "array", "items": {"type": "string"},
                        "minItems": 1, "uniqueItems": True,
                    },
                },
                "additionalProperties": False,
            },
            "control_and_mask_requirements": control_and_mask_requirements,
            "quality_cost_runtime_policy_id": {"type": "string"},
            "context_sha256": sha,
        },
        [
            "job_id", "run_id", "pass_id", "scene_id", "shot_id", "take_id",
            "character_revision_ids", "character_instance_ids",
            "capability_scope", "target_contract", "protected_contract",
            "control_and_mask_requirements", "quality_cost_runtime_policy_id",
            "context_sha256",
        ],
    )

    schemas["contextual_model_selection_request.schema.json"] = record_schema(
        "Wave64 Contextual Model Selection Request",
        "contextual-model-selection-request",
        "contextual_model_selection_request",
        "selection_request_id",
        {
            "selection_context_ref": record_ref,
            "registry_snapshot_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "required_certificate_authority": {"type": "string"},
            "preferred_bundle_ids": {"type": "array", "items": {"type": "string"}},
            "prohibited_bundle_ids": {"type": "array", "items": {"type": "string"}},
            "exploration_policy": {
                "enum": ["production_exploit_only", "shadow_challenger_allowed", "qualification_exploration"]
            },
            "fallback_policy": {"type": "string"},
            "candidate_limit": {"type": "integer", "minimum": 1},
        },
        [
            "selection_context_ref", "registry_snapshot_ids",
            "required_certificate_authority", "exploration_policy",
            "fallback_policy", "candidate_limit",
        ],
    )

    selection_decision = record_schema(
        "Wave64 Contextual Model Selection Decision",
        "contextual-model-selection-decision",
        "contextual_model_selection_decision",
        "selection_decision_id",
        {
            "selection_request_ref": record_ref,
            "decision": {
                "enum": ["selected", "abstained", "blocked", "qualification_enqueued"]
            },
            "evaluated_candidates": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "execution_bundle_id", "eligible", "eligibility_reasons",
                        "certificate_ids", "metric_vector", "quality_lcb",
                        "risk_ucb", "utility", "uncertainty",
                    ],
                    "properties": {
                        "execution_bundle_id": {"type": "string", "minLength": 1},
                        "eligible": {"type": "boolean"},
                        "eligibility_reasons": {"type": "array", "items": {"type": "string"}},
                        "certificate_ids": {
                            "type": "array", "items": {"type": "string"},
                            "uniqueItems": True,
                        },
                        "metric_vector": {"type": "object", "additionalProperties": {"type": "number"}},
                        "quality_lcb": {"type": ["number", "null"]},
                        "risk_ucb": {"type": ["number", "null"]},
                        "utility": {"type": ["number", "null"]},
                        "uncertainty": {
                            "type": ["number", "null"], "minimum": 0, "maximum": 1,
                        },
                        "evidence_ids": {
                            "type": "array", "items": {"type": "string"},
                            "uniqueItems": True,
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "pareto_frontier_bundle_ids": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "selected_bundle_id": {"type": ["string", "null"]},
            "selected_execution_bundle_ref": {
                "oneOf": [
                    hash_bound_record_ref("model_execution_bundle"),
                    {"type": "null"},
                ]
            },
            "challenger_bundle_id": {"type": ["string", "null"]},
            "ranking_policy_id": {"type": "string"},
            "feature_snapshot_sha256": sha,
            "selection_reasons": {"type": "array", "items": {"type": "string"}},
            "uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
            "fallback_bundle_ids": {"type": "array", "items": {"type": "string"}},
            "assignment_probability": {
                "type": ["number", "null"], "exclusiveMinimum": 0, "maximum": 1,
            },
            "assignment_policy_id": {"type": "string", "minLength": 1},
            "holdout_partition_id": {"type": ["string", "null"]},
            "learning_use_allowed": {"type": "boolean"},
            "no_silent_substitution": {"const": True},
        },
        [
            "selection_request_ref", "decision", "evaluated_candidates",
            "pareto_frontier_bundle_ids", "selected_bundle_id",
            "selected_execution_bundle_ref",
            "ranking_policy_id", "feature_snapshot_sha256",
            "selection_reasons", "uncertainty", "fallback_bundle_ids",
            "assignment_probability", "assignment_policy_id",
            "holdout_partition_id", "learning_use_allowed",
            "no_silent_substitution",
        ],
    )
    selection_decision["allOf"] = [
        {
            "if": {
                "properties": {"decision": {"const": "selected"}},
                "required": ["decision"],
            },
            "then": {
                "properties": {
                    "selected_bundle_id": {"type": "string", "minLength": 1},
                    "selected_execution_bundle_ref": hash_bound_record_ref(
                        "model_execution_bundle"
                    ),
                    "pareto_frontier_bundle_ids": {"minItems": 1},
                    "selection_reasons": {"minItems": 1},
                }
            },
            "else": {
                "properties": {
                    "selected_bundle_id": {"const": None},
                    "selected_execution_bundle_ref": {"const": None},
                }
            },
        }
    ]
    schemas["contextual_model_selection_decision.schema.json"] = selection_decision

    schemas["model_comparison_experiment.schema.json"] = record_schema(
        "Wave64 Model Comparison Experiment",
        "model-comparison-experiment",
        "model_comparison_experiment",
        "comparison_experiment_id",
        {
            "comparison_type": {
                "enum": ["baseline_ab", "matched_candidate", "component_ablation", "strength_curve", "bridge_pair"]
            },
            "candidate_bundle_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "baseline_bundle_ref": record_ref,
            "controlled_variables": {"type": "array", "items": {"type": "string"}},
            "changed_variables": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "randomization_and_blinding": {"type": "object"},
            "confounders": {"type": "array", "items": {"type": "string"}},
            "result_refs": {"type": "array", "items": record_ref},
            "attribution_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        },
        [
            "comparison_type", "candidate_bundle_refs", "baseline_bundle_ref",
            "controlled_variables", "changed_variables",
            "randomization_and_blinding", "confounders", "result_refs",
        ],
    )

    schemas["model_use_observation.schema.json"] = record_schema(
        "Wave64 Per-Use Model Observation",
        "model-use-observation",
        "model_use_observation",
        "use_observation_id",
        {
            "job_id": {"type": "string"},
            "run_id": {"type": "string"},
            "pass_id": {"type": "string"},
            "attempt_id": {"type": "string"},
            "selection_decision_ref": record_ref,
            "selection_context_ref": record_ref,
            "execution_bundle_ref": record_ref,
            "input_artifact_ids": {"type": "array", "items": {"type": "string"}},
            "output_artifact_ids": {"type": "array", "items": {"type": "string"}},
            "metrics": {"type": "array", "items": metric},
            "review_observation_ids": {"type": "array", "items": {"type": "string"}},
            "failure_codes": {"type": "array", "items": {"type": "string"}},
            "resource_telemetry": {"type": "object"},
            "qa_disposition": {
                "enum": ["accepted", "repair", "reroute", "rejected", "blocked", "cancelled"]
            },
            "learning_eligibility": {
                "enum": ["eligible_stack_level", "eligible_component_attribution", "ineligible", "pending"]
            },
            "learning_exclusion_reasons": {"type": "array", "items": {"type": "string"}},
        },
        [
            "job_id", "run_id", "pass_id", "attempt_id",
            "selection_decision_ref", "selection_context_ref",
            "execution_bundle_ref", "input_artifact_ids", "output_artifact_ids",
            "metrics", "failure_codes", "resource_telemetry",
            "qa_disposition", "learning_eligibility",
            "learning_exclusion_reasons",
        ],
    )

    schemas["model_performance_profile.schema.json"] = record_schema(
        "Wave64 Contextual Model Performance Profile",
        "model-performance-profile",
        "model_performance_profile",
        "performance_profile_id",
        {
            "execution_bundle_ref": record_ref,
            "capability_scope": scope,
            "evidence_snapshot_id": {"type": "string"},
            "sample_counts": {"type": "object"},
            "metric_distributions": {"type": "object"},
            "confidence_bounds": {"type": "object"},
            "parameter_response_envelope": {"type": "object"},
            "recommended_uses": {"type": "array", "items": {"type": "string"}},
            "known_failures": {"type": "array", "items": {"type": "string"}},
            "excluded_contexts": {"type": "array", "items": {"type": "string"}},
            "certificate_ids": {"type": "array", "items": {"type": "string"}},
            "fresh_until": {"type": "string", "format": "date-time"},
        },
        [
            "execution_bundle_ref", "capability_scope", "evidence_snapshot_id",
            "sample_counts", "metric_distributions", "confidence_bounds",
            "parameter_response_envelope", "recommended_uses",
            "known_failures", "excluded_contexts", "certificate_ids",
            "fresh_until",
        ],
    )

    schemas["model_intelligence_report.schema.json"] = record_schema(
        "Wave64 Model Intelligence Report",
        "model-intelligence-report",
        "model_intelligence_report",
        "model_report_id",
        {
            "subject_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "report_scope": {"enum": ["asset", "bundle", "capability_bucket", "selection_decision"]},
            "authority_summary": {"type": "object"},
            "certified_uses": {"type": "array", "items": {"type": "string"}},
            "untested_uses": {"type": "array", "items": {"type": "string"}},
            "best_contexts": {"type": "array", "items": {"type": "string"}},
            "worst_contexts": {"type": "array", "items": {"type": "string"}},
            "failure_summary": {"type": "object"},
            "resource_summary": {"type": "object"},
            "report_notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["note_type", "text", "evidence_ids"],
                    "properties": {
                        "note_type": {"enum": ["generated_summary", "human_annotation", "policy_note"]},
                        "text": {"type": "string"},
                        "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "additionalProperties": False,
                },
            },
            "supersedes_report_id": {"type": ["string", "null"]},
        },
        [
            "subject_refs", "report_scope", "authority_summary",
            "certified_uses", "untested_uses", "best_contexts",
            "worst_contexts", "failure_summary", "resource_summary",
            "report_notes",
        ],
    )

    schemas["model_drift_event.schema.json"] = record_schema(
        "Wave64 Model Drift Event",
        "model-drift-event",
        "model_drift_event",
        "drift_event_id",
        {
            "drift_type": {
                "enum": [
                    "model_hash", "component", "workflow", "runtime",
                    "prompt_template", "reviewer", "data", "metric", "workload",
                ]
            },
            "changed_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "baseline_snapshot_id": {"type": "string"},
            "observed_snapshot_id": {"type": "string"},
            "affected_certificate_ids": {"type": "array", "items": {"type": "string"}},
            "affected_route_ids": {"type": "array", "items": {"type": "string"}},
            "severity": {"enum": ["info", "caution", "suspend", "revoke"]},
            "required_action": {"enum": ["monitor", "rebenchmark", "suspend", "revoke", "rollback"]},
            "evidence": {"type": "array", "items": evidence_ref},
        },
        [
            "drift_type", "changed_refs", "baseline_snapshot_id",
            "observed_snapshot_id", "affected_certificate_ids",
            "affected_route_ids", "severity", "required_action", "evidence",
        ],
    )

    schemas["model_lifecycle_decision.schema.json"] = record_schema(
        "Wave64 Model Lifecycle Decision",
        "model-lifecycle-decision",
        "model_lifecycle_decision",
        "lifecycle_decision_id",
        {
            "subject_ref": record_ref,
            "axis": {
                "enum": ["identity", "binary_integrity", "classification", "availability", "runtime", "capability_authority", "evidence"]
            },
            "from_state": {"type": "string"},
            "to_state": {"type": "string"},
            "decision_authority": {
                "enum": ["deterministic_policy", "authorized_operator", "release_authority"]
            },
            "reason_codes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "evidence": {"type": "array", "items": evidence_ref},
            "affected_certificate_ids": {"type": "array", "items": {"type": "string"}},
            "rollback_ref": {"oneOf": [record_ref, {"type": "null"}]},
        },
        [
            "subject_ref", "axis", "from_state", "to_state",
            "decision_authority", "reason_codes", "evidence",
            "affected_certificate_ids",
        ],
    )

    schemas["autonomous_model_role_card.schema.json"] = record_schema(
        "Wave64 Autonomous Model Role Card",
        "autonomous-model-role-card",
        "autonomous_model_role_card",
        "autonomous_role_id",
        {
            "role": {
                "enum": [
                    "planner", "prompt_composer", "retrieval_analyst",
                    "router_advisor", "defect_classifier", "vlm_critic",
                    "audio_critic", "report_writer", "summarizer",
                    "drift_triage",
                ]
            },
            "allowed_input_record_types": {"type": "array", "items": {"type": "string"}},
            "allowed_output_record_types": {"type": "array", "items": {"type": "string"}},
            "allowed_tool_actions": {"type": "array", "items": {"type": "string"}},
            "prohibited_authorities": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "context_budget": {"type": "object"},
            "model_requirements": {"type": "object"},
            "escalation_conditions": {"type": "array", "items": {"type": "string"}},
        },
        [
            "role", "allowed_input_record_types", "allowed_output_record_types",
            "allowed_tool_actions", "prohibited_authorities", "context_budget",
            "model_requirements", "escalation_conditions",
        ],
    )

    schemas["autonomous_model_execution_stack.schema.json"] = record_schema(
        "Wave64 Autonomous Model Execution Stack",
        "autonomous-model-execution-stack",
        "autonomous_model_execution_stack",
        "autonomous_stack_id",
        {
            "autonomous_role_id": {"type": "string"},
            "model_id": {"type": "string"},
            "model_revision": {"type": "string"},
            "model_sha256": {"oneOf": [sha, {"type": "null"}]},
            "runtime": {"type": "string"},
            "runtime_revision": {"type": "string"},
            "quantization": {"type": "string"},
            "chat_template_id": {"type": "string"},
            "structured_output_parser_id": {"type": "string"},
            "context_limit": {"type": "integer", "minimum": 1},
            "batching_policy": {"type": "object"},
            "hardware_envelope_id": {"type": "string"},
            "qualification_certificate_ids": {"type": "array", "items": {"type": "string"}},
            "fallback_stack_ids": {"type": "array", "items": {"type": "string"}},
            "selection_state": {
                "enum": [
                    "unselected", "candidate", "qualified_inactive",
                    "shadow_active", "production_active", "suspended", "revoked",
                ]
            },
            "activation_decision_ref": {
                "oneOf": [record_ref, {"type": "null"}]
            },
            "direct_execution_authority": {"const": False},
            "registry_mutation_authority": {"const": False},
            "certificate_or_promotion_authority": {"const": False},
        },
        [
            "autonomous_role_id", "model_id", "model_revision",
            "model_sha256", "runtime", "runtime_revision", "quantization",
            "chat_template_id", "structured_output_parser_id",
            "context_limit", "batching_policy", "hardware_envelope_id",
            "qualification_certificate_ids", "fallback_stack_ids",
            "selection_state", "activation_decision_ref",
            "direct_execution_authority", "registry_mutation_authority",
            "certificate_or_promotion_authority",
        ],
    )

    schemas["autonomous_retrieval_evidence_bundle.schema.json"] = record_schema(
        "Wave64 Autonomous Retrieval Evidence Bundle",
        "autonomous-retrieval-evidence-bundle",
        "autonomous_retrieval_evidence_bundle",
        "retrieval_bundle_id",
        {
            "query": {"type": "object"},
            "registry_snapshot_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "retrieved_records": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["record_ref", "citation", "authority", "freshness"],
                    "properties": {
                        "record_ref": record_ref,
                        "citation": {"type": "string"},
                        "authority": {"type": "string"},
                        "freshness": {"type": "string"},
                        "conflict_group_id": {"type": ["string", "null"]},
                    },
                    "additionalProperties": False,
                },
            },
            "negative_evidence_ids": {"type": "array", "items": {"type": "string"}},
            "conflicts": {"type": "array", "items": {"type": "object"}},
            "missing_evidence": {"type": "array", "items": {"type": "string"}},
            "token_budget": {"type": "integer", "minimum": 1},
            "bundle_sha256": sha,
        },
        [
            "query", "registry_snapshot_ids", "retrieved_records",
            "negative_evidence_ids", "conflicts", "missing_evidence",
            "token_budget", "bundle_sha256",
        ],
    )

    schemas["autonomous_planner_proposal.schema.json"] = record_schema(
        "Wave64 Autonomous Planner Proposal",
        "autonomous-planner-proposal",
        "autonomous_planner_proposal",
        "planner_proposal_id",
        {
            "autonomous_stack_ref": record_ref,
            "retrieval_bundle_ref": record_ref,
            "objective": {"type": "object"},
            "proposed_passes": {"type": "array", "items": {"type": "object"}},
            "proposed_selection_request_ids": {"type": "array", "items": {"type": "string"}},
            "proposed_prompt_package_ids": {"type": "array", "items": {"type": "string"}},
            "repair_hypotheses": {"type": "array", "items": {"type": "object"}},
            "alternatives": {"type": "array", "items": {"type": "object"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "abstain": {"type": "boolean"},
            "abstention_reasons": {"type": "array", "items": {"type": "string"}},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        [
            "autonomous_stack_ref", "retrieval_bundle_ref", "objective",
            "proposed_passes", "proposed_selection_request_ids",
            "proposed_prompt_package_ids", "repair_hypotheses",
            "alternatives", "confidence", "abstain", "abstention_reasons",
            "evidence_ids",
        ],
    )

    schemas["autonomous_prompt_package.schema.json"] = record_schema(
        "Wave64 Autonomous Prompt Package",
        "autonomous-prompt-package",
        "autonomous_prompt_package",
        "prompt_package_id",
        {
            "selection_context_ref": record_ref,
            "engine_family": {"type": "string"},
            "workflow_module_id": {"type": "string"},
            "intent_summary": {"type": "string"},
            "positive_conditioning": {"type": "array", "items": {"type": "string"}},
            "negative_conditioning": {"type": "array", "items": {"type": "string"}},
            "trigger_bindings": {"type": "array", "items": {"type": "object"}},
            "adapter_bindings": {"type": "array", "items": {"type": "object"}},
            "protected_constraints": {"type": "array", "items": {"type": "string"}},
            "translation_policy_id": {"type": "string"},
            "prompt_sha256": sha,
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        [
            "selection_context_ref", "engine_family", "workflow_module_id",
            "intent_summary", "positive_conditioning", "negative_conditioning",
            "trigger_bindings", "adapter_bindings", "protected_constraints",
            "translation_policy_id", "prompt_sha256", "evidence_ids",
        ],
    )

    schemas["autonomous_reviewer_observation.schema.json"] = record_schema(
        "Wave64 Autonomous Reviewer Observation",
        "autonomous-reviewer-observation",
        "autonomous_reviewer_observation",
        "reviewer_observation_id",
        {
            "autonomous_stack_ref": record_ref,
            "artifact_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "scope_bindings": {"type": "array", "items": {"type": "object"}},
            "observations": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "metric_observations": {"type": "array", "items": metric},
            "uncertainty": {"type": "number", "minimum": 0, "maximum": 1},
            "disagreement_group_id": {"type": ["string", "null"]},
            "promotion_authority": {"const": "none"},
            "evidence_ids": {"type": "array", "items": {"type": "string"}},
        },
        [
            "autonomous_stack_ref", "artifact_ids", "scope_bindings",
            "observations", "metric_observations", "uncertainty",
            "promotion_authority", "evidence_ids",
        ],
    )

    tool_action = record_schema(
        "Wave64 Autonomous Tool Gateway Action",
        "autonomous-tool-gateway-action",
        "autonomous_tool_gateway_action",
        "tool_action_id",
        {
            "actor_role_id": {"type": "string"},
            "requested_action": {"type": "string"},
            "allowlisted_target_id": {"type": ["string", "null"]},
            "arguments": {
                "type": "object",
                "required": ["argument_schema_id", "payload_sha256"],
                "properties": {
                    "argument_schema_id": {"type": "string", "minLength": 1},
                    "payload_sha256": sha,
                    "payload": {"type": "object"},
                },
                "additionalProperties": False,
            },
            "authorization_decision": {"enum": ["allowed", "denied"]},
            "authorization_policy_id": {"type": "string"},
            "denial_reasons": {"type": "array", "items": {"type": "string"}},
            "execution_result": {
                "type": "object",
                "required": ["result_state", "evidence_ids"],
                "properties": {
                    "result_state": {
                        "enum": ["not_executed", "succeeded", "failed", "cancelled"]
                    },
                    "evidence_ids": {
                        "type": "array", "items": {"type": "string"},
                        "uniqueItems": True,
                    },
                },
                "additionalProperties": False,
            },
            "credential_exposure": {"const": False},
            "registry_mutation": {"const": False},
        },
        [
            "actor_role_id", "requested_action", "allowlisted_target_id",
            "arguments", "authorization_decision", "authorization_policy_id",
            "denial_reasons", "execution_result", "credential_exposure",
            "registry_mutation",
        ],
    )
    tool_action["allOf"] = [
        {
            "if": {
                "properties": {"authorization_decision": {"const": "allowed"}},
                "required": ["authorization_decision"],
            },
            "then": {
                "properties": {
                    "allowlisted_target_id": {"type": "string", "minLength": 1},
                    "denial_reasons": {"maxItems": 0},
                }
            },
            "else": {
                "properties": {
                    "denial_reasons": {"minItems": 1},
                    "execution_result": {
                        "properties": {"result_state": {"const": "not_executed"}}
                    },
                }
            },
        }
    ]
    schemas["autonomous_tool_gateway_action.schema.json"] = tool_action

    policy_decision = record_schema(
        "Wave64 Autonomous Policy Decision",
        "autonomous-policy-decision",
        "autonomous_policy_decision",
        "policy_decision_id",
        {
            "subject_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "policy_id": {"type": "string"},
            "gate_results": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["gate_id", "result", "evidence_ids"],
                    "properties": {
                        "gate_id": {"type": "string", "minLength": 1},
                        "result": {"enum": ["pass", "fail", "blocked", "not_applicable"]},
                        "evidence_ids": {
                            "type": "array", "items": {"type": "string"},
                            "uniqueItems": True,
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "decision": {
                "enum": [
                    "validate", "reject_proposal", "allow_execution",
                    "deny_execution", "accept_observation", "exclude_from_learning",
                    "certify", "suspend", "revoke", "promote_artifact",
                    "reject_artifact",
                ]
            },
            "decision_authority": {
                "enum": ["deterministic_policy", "authorized_operator", "release_authority"]
            },
            "reason_codes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "evidence_ids": {
                "type": "array", "items": {"type": "string"},
                "minItems": 1, "uniqueItems": True,
            },
        },
        [
            "subject_refs", "policy_id", "gate_results", "decision",
            "decision_authority", "reason_codes", "evidence_ids",
        ],
    )
    policy_decision["allOf"] = [
        {
            "if": {
                "properties": {
                    "decision": {
                        "enum": ["allow_execution", "certify", "promote_artifact"]
                    }
                },
                "required": ["decision"],
            },
            "then": {
                "properties": {
                    "gate_results": {
                        "minItems": 1,
                        "not": {
                            "contains": {
                                "type": "object",
                                "properties": {
                                    "result": {"enum": ["fail", "blocked"]}
                                },
                                "required": ["result"],
                            }
                        },
                    }
                }
            },
        }
    ]
    schemas["autonomous_policy_decision.schema.json"] = policy_decision

    schemas["autonomous_context_memory_manifest.schema.json"] = record_schema(
        "Wave64 Autonomous Context Memory Manifest",
        "autonomous-context-memory-manifest",
        "autonomous_context_memory_manifest",
        "context_memory_manifest_id",
        {
            "role_id": {"type": "string"},
            "context_limit": {"type": "integer", "minimum": 1},
            "token_budget": {"type": "object"},
            "included_record_refs": {"type": "array", "items": record_ref},
            "excluded_record_refs": {"type": "array", "items": record_ref},
            "compaction_summaries": {"type": "array", "items": {"type": "object"}},
            "conflict_ids": {"type": "array", "items": {"type": "string"}},
            "missing_evidence": {"type": "array", "items": {"type": "string"}},
            "context_sha256": sha,
        },
        [
            "role_id", "context_limit", "token_budget",
            "included_record_refs", "excluded_record_refs",
            "compaction_summaries", "conflict_ids", "missing_evidence",
            "context_sha256",
        ],
    )

    schemas["autonomous_role_qualification_certificate.schema.json"] = record_schema(
        "Wave64 Autonomous Role Qualification Certificate",
        "autonomous-role-qualification-certificate",
        "autonomous_role_qualification_certificate",
        "role_qualification_certificate_id",
        {
            "autonomous_stack_ref": record_ref,
            "role_id": {"type": "string"},
            "benchmark_suite_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "structured_output_validity": {"type": "object"},
            "grounding_and_citation": {"type": "object"},
            "uncertainty_and_abstention": {"type": "object"},
            "tool_safety": {"type": "object"},
            "quality_metrics": {"type": "array", "items": metric},
            "authority": {"enum": ["shadow_only", "qualified_for_role"]},
            "valid_from": {"type": "string", "format": "date-time"},
            "valid_until": {"type": "string", "format": "date-time"},
            "revocation_event_id": {"type": ["string", "null"]},
        },
        [
            "autonomous_stack_ref", "role_id", "benchmark_suite_ids",
            "structured_output_validity", "grounding_and_citation",
            "uncertainty_and_abstention", "tool_safety",
            "quality_metrics", "authority", "valid_from", "valid_until",
        ],
    )

    role_activation = record_schema(
        "Wave64 Autonomous Role Activation Decision",
        "autonomous-role-activation-decision",
        "autonomous_role_activation_decision",
        "role_activation_decision_id",
        {
            "role_card_ref": record_ref,
            "autonomous_stack_ref": {"oneOf": [record_ref, {"type": "null"}]},
            "role_qualification_certificate_refs": {
                "type": "array", "items": record_ref,
            },
            "shadow_evidence_refs": {"type": "array", "items": record_ref},
            "activation_state": {
                "enum": [
                    "inactive_unselected", "inactive_unqualified",
                    "qualified_inactive", "shadow_active",
                    "production_active", "suspended", "revoked",
                ]
            },
            "allowed_operating_modes": {
                "type": "array", "uniqueItems": True,
                "items": {"enum": ["offline", "shadow", "production"]},
            },
            "tool_authorization_policy_id": {"type": "string", "minLength": 1},
            "model_library_phase_transition_ref": {
                "oneOf": [record_ref, {"type": "null"}]
            },
            "registry_snapshot_ids": {
                "type": "array", "items": {"type": "string"},
                "uniqueItems": True,
            },
            "decision_authority": {
                "enum": ["deterministic_role_activation_policy", "release_authority"]
            },
            "valid_until": {"type": ["string", "null"], "format": "date-time"},
            "direct_execution_authority": {"const": False},
            "registry_mutation_authority": {"const": False},
            "certificate_authority": {"const": False},
            "artifact_promotion_authority": {"const": False},
            "reason_codes": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
        },
        [
            "role_card_ref", "autonomous_stack_ref",
            "role_qualification_certificate_refs", "shadow_evidence_refs",
            "activation_state", "allowed_operating_modes",
            "tool_authorization_policy_id", "model_library_phase_transition_ref",
            "registry_snapshot_ids", "decision_authority", "valid_until",
            "direct_execution_authority", "registry_mutation_authority",
            "certificate_authority", "artifact_promotion_authority",
            "reason_codes",
        ],
    )
    role_activation["allOf"] = [
        {
            "if": {
                "properties": {
                    "activation_state": {
                        "enum": ["shadow_active", "production_active"]
                    }
                },
                "required": ["activation_state"],
            },
            "then": {
                "properties": {
                    "autonomous_stack_ref": record_ref,
                    "role_qualification_certificate_refs": {"minItems": 1},
                    "model_library_phase_transition_ref": record_ref,
                    "registry_snapshot_ids": {"minItems": 1},
                }
            },
        },
        {
            "if": {
                "properties": {"activation_state": {"const": "production_active"}},
                "required": ["activation_state"],
            },
            "then": {
                "properties": {
                    "allowed_operating_modes": {"contains": {"const": "production"}},
                    "shadow_evidence_refs": {"minItems": 1},
                }
            },
        },
    ]
    schemas["autonomous_role_activation_decision.schema.json"] = role_activation

    schemas["autonomy_shadow_run.schema.json"] = record_schema(
        "Wave64 Autonomy Shadow Run",
        "autonomy-shadow-run",
        "autonomy_shadow_run",
        "shadow_run_id",
        {
            "job_id": {"type": "string"},
            "production_decision_refs": {"type": "array", "items": record_ref},
            "shadow_proposal_refs": {"type": "array", "items": record_ref},
            "decision_differences": {"type": "array", "items": {"type": "object"}},
            "shadow_execution_allowed": {"type": "boolean"},
            "shadow_artifact_ids": {"type": "array", "items": {"type": "string"}},
            "qa_comparison": {"type": "object"},
            "regret_and_risk": {"type": "object"},
            "activation_effect": {"enum": ["none", "supports_activation", "blocks_activation", "requires_more_evidence"]},
            "production_state_mutated": {"const": False},
        },
        [
            "job_id", "production_decision_refs", "shadow_proposal_refs",
            "decision_differences", "shadow_execution_allowed",
            "shadow_artifact_ids", "qa_comparison", "regret_and_risk",
            "activation_effect", "production_state_mutated",
        ],
    )

    schemas["model_library_expected_download_scope.schema.json"] = record_schema(
        "Wave64 Model Library Expected Download Scope",
        "model-library-expected-download-scope",
        "model_library_expected_download_scope",
        "expected_download_scope_id",
        {
            "main_task_id": {"const": MAIN_TASK_ID},
            "source_snapshot_ref": typed_record_ref("model_library_source_snapshot"),
            "scope_asset_manifest_ref": record_ref,
            "expected_catalog_artifact_count": {"type": "integer", "minimum": 1},
            "expected_model_binary_count": {"type": "integer", "minimum": 1},
            "included_asset_identity_sha256": sha,
            "declared_exclusions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["asset_id", "reason_code", "authority"],
                    "properties": {
                        "asset_id": {"type": "string", "minLength": 1},
                        "reason_code": {"type": "string", "minLength": 1},
                        "authority": {
                            "enum": ["user_scope_declaration", "main_task_scope_authority"]
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "scope_sha256": sha,
            "scope_declared_complete": {"const": True},
            "runtime_authority_granted": {"const": False},
        },
        [
            "main_task_id", "source_snapshot_ref", "scope_asset_manifest_ref",
            "expected_catalog_artifact_count", "expected_model_binary_count",
            "included_asset_identity_sha256", "declared_exclusions",
            "scope_sha256", "scope_declared_complete",
            "runtime_authority_granted",
        ],
    )

    schemas["model_download_completion_manifest.schema.json"] = record_schema(
        "Wave64 Model Download Completion Manifest",
        "model-download-completion-manifest",
        "model_download_completion_manifest",
        "download_completion_manifest_id",
        {
            "main_task_id": {"const": MAIN_TASK_ID},
            "expected_download_scope_ref": typed_record_ref(
                "model_library_expected_download_scope"
            ),
            "scope_sha256": sha,
            "declared_downloaded_binary_count": {"type": "integer", "minimum": 1},
            "download_root_inventory_sha256": sha,
            "download_complete_declared": {"const": True},
            "declaration_actor": {
                "enum": ["user", "main_task_authorized_controller"]
            },
            "binary_inventory_verified": {"const": False},
            "qualification_authority_granted": {"const": False},
            "production_authority_granted": {"const": False},
        },
        [
            "main_task_id", "expected_download_scope_ref", "scope_sha256",
            "declared_downloaded_binary_count", "download_root_inventory_sha256",
            "download_complete_declared", "declaration_actor",
            "binary_inventory_verified", "qualification_authority_granted",
            "production_authority_granted",
        ],
    )

    schemas["model_binary_inventory_verification_report.schema.json"] = record_schema(
        "Wave64 Model Binary Inventory Verification Report",
        "model-binary-inventory-verification-report",
        "model_binary_inventory_verification_report",
        "binary_inventory_verification_report_id",
        {
            "expected_download_scope_ref": typed_record_ref(
                "model_library_expected_download_scope"
            ),
            "download_completion_manifest_ref": typed_record_ref(
                "model_download_completion_manifest"
            ),
            "scope_sha256": sha,
            "expected_binary_count": {"type": "integer", "minimum": 1},
            "accounted_binary_count": {"type": "integer", "minimum": 1},
            "hash_verified_binary_count": {"type": "integer", "minimum": 0},
            "quarantined_binary_count": {"type": "integer", "minimum": 0},
            "failed_binary_count": {"type": "integer", "minimum": 0},
            "missing_binary_count": {"const": 0},
            "hash_pending_binary_count": {"const": 0},
            "unresolved_binary_count": {"const": 0},
            "all_intended_assets_accounted_for": {"const": True},
            "quarantined_and_failed_excluded_from_runtime": {"const": True},
            "inventory_sha256": sha,
            "verification_tool_revision": {"type": "string", "minLength": 1},
            "verification_passed": {"const": True},
        },
        [
            "expected_download_scope_ref", "download_completion_manifest_ref",
            "scope_sha256", "expected_binary_count", "accounted_binary_count",
            "hash_verified_binary_count", "quarantined_binary_count",
            "failed_binary_count", "missing_binary_count",
            "hash_pending_binary_count", "unresolved_binary_count",
            "all_intended_assets_accounted_for",
            "quarantined_and_failed_excluded_from_runtime", "inventory_sha256",
            "verification_tool_revision", "verification_passed",
        ],
    )

    schemas["main_task_model_library_activation_acknowledgement.schema.json"] = record_schema(
        "Wave64 Main-Task Model Library Activation Acknowledgement",
        "main-task-model-library-activation-acknowledgement",
        "main_task_model_library_activation_acknowledgement",
        "main_task_activation_acknowledgement_id",
        {
            "main_task_id": {"const": MAIN_TASK_ID},
            "expected_download_scope_ref": typed_record_ref(
                "model_library_expected_download_scope"
            ),
            "download_completion_manifest_ref": typed_record_ref(
                "model_download_completion_manifest"
            ),
            "binary_inventory_verification_report_ref": typed_record_ref(
                "model_binary_inventory_verification_report"
            ),
            "preservation_manifest_ref": record_ref,
            "acknowledged_phase": {"const": "staging"},
            "scope_sha256": sha,
            "acknowledgement_authority": {"const": "main_task_release_authority"},
            "no_implicit_later_phase_authority": {"const": True},
            "other_runtime_lanes_affected": {"const": False},
        },
        [
            "main_task_id", "expected_download_scope_ref",
            "download_completion_manifest_ref",
            "binary_inventory_verification_report_ref",
            "preservation_manifest_ref", "acknowledged_phase", "scope_sha256",
            "acknowledgement_authority", "no_implicit_later_phase_authority",
            "other_runtime_lanes_affected",
        ],
    )

    schemas["model_library_phase_transition_decision.schema.json"] = record_schema(
        "Wave64 Model Library Phase Transition Decision",
        "model-library-phase-transition-decision",
        "model_library_phase_transition_decision",
        "phase_transition_decision_id",
        {
            "main_task_id": {"const": MAIN_TASK_ID},
            "activation_gate_id": {"const": ACTIVATION_GATE_ID},
            "event_sequence": {"type": "integer", "minimum": 1},
            "previous_transition_sha256": {"oneOf": [sha, {"type": "null"}]},
            "from_gate_state": {"type": "string", "minLength": 1},
            "to_gate_state": {"type": "string", "minLength": 1},
            "from_phase": {"enum": list(ACTIVATION_PHASES)},
            "to_phase": {"enum": list(ACTIVATION_PHASES)},
            "decision": {"enum": ["authorized", "denied", "suspended"]},
            "prerequisite_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "permissions_sha256": sha,
            "decision_authority": {
                "enum": ["deterministic_phase_policy", "main_task_release_authority"]
            },
            "reason_codes": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "implicit_phase_cascade": {"const": False},
            "other_runtime_lanes_affected": {"const": False},
        },
        [
            "main_task_id", "activation_gate_id", "event_sequence",
            "previous_transition_sha256", "from_gate_state", "to_gate_state",
            "from_phase", "to_phase", "decision", "prerequisite_refs",
            "permissions_sha256", "decision_authority", "reason_codes",
            "implicit_phase_cascade", "other_runtime_lanes_affected",
        ],
    )

    schemas["comfyui_runtime_lock.schema.json"] = record_schema(
        "Wave64 ComfyUI Runtime Lock",
        "comfyui-runtime-lock",
        "comfyui_runtime_lock",
        "runtime_lock_id",
        {
            "runtime_id": {"type": "string", "minLength": 1},
            "core_version": {"type": "string", "minLength": 1},
            "core_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "core_dirty": {"type": "boolean"},
            "core_diff_sha256": {"oneOf": [sha, {"type": "null"}]},
            "frontend_version": {"type": "string", "minLength": 1},
            "python_version": {"type": "string", "minLength": 1},
            "torch_version": {"type": "string", "minLength": 1},
            "cuda_version": {"type": ["string", "null"]},
            "startup_argv_sha256": sha,
            "environment_lock_sha256": sha,
            "custom_nodes": {
                "type": "array", "uniqueItems": True,
                "items": {
                    "type": "object",
                    "required": [
                        "node_pack_id", "origin", "commit", "dirty",
                        "diff_sha256", "requirements_sha256", "import_status",
                        "node_signature_sha256",
                    ],
                    "properties": {
                        "node_pack_id": {"type": "string", "minLength": 1},
                        "origin": {"type": "string", "minLength": 1},
                        "commit": {"type": "string", "minLength": 1},
                        "dirty": {"type": "boolean"},
                        "diff_sha256": {"oneOf": [sha, {"type": "null"}]},
                        "requirements_sha256": sha,
                        "import_status": {"enum": ["passed", "failed"]},
                        "node_signature_sha256": sha,
                    },
                    "additionalProperties": False,
                },
            },
            "object_info_sha256": sha,
            "feature_probes": {
                "type": "object",
                "required": [
                    "prompt", "websocket", "history", "queue", "interrupt",
                    "jobs", "targeted_cancel",
                ],
                "properties": {
                    "prompt": {"type": "boolean"},
                    "websocket": {"type": "boolean"},
                    "history": {"type": "boolean"},
                    "queue": {"type": "boolean"},
                    "interrupt": {"type": "boolean"},
                    "jobs": {"type": "boolean"},
                    "targeted_cancel": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "folder_root_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
            "compatible_workflow_release_ids": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "captured_at": {"type": "string", "format": "date-time"},
        },
        [
            "runtime_id", "core_version", "core_commit", "core_dirty",
            "core_diff_sha256", "frontend_version", "python_version",
            "torch_version", "cuda_version", "startup_argv_sha256",
            "environment_lock_sha256", "custom_nodes", "object_info_sha256",
            "feature_probes", "folder_root_ids",
            "compatible_workflow_release_ids", "captured_at",
        ],
    )

    schemas["workflow_release_manifest.schema.json"] = record_schema(
        "Wave64 Workflow Release Manifest",
        "workflow-release-manifest",
        "workflow_release_manifest",
        "workflow_release_id",
        {
            "workflow_module_id": {"type": "string", "minLength": 1},
            "original_ui_schema_version": {"enum": ["0.4", "1.0"]},
            "original_ui_sha256": sha,
            "canonical_v1_ui_sha256": sha,
            "migration_tool_revision": {"type": ["string", "null"]},
            "semantic_equivalence_evidence_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "api_graph_sha256": sha,
            "flattened_api_graph_sha256": sha,
            "top_level_meta_removed": {"const": True},
            "allowlisted_patch_map_sha256": sha,
            "required_node_signature_sha256s": {
                "type": "array", "items": sha, "minItems": 1, "uniqueItems": True,
            },
            "input_bindings": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "output_bindings": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "project_subgraph_source_sha256s": {
                "type": "array", "items": sha, "uniqueItems": True,
            },
            "app_mode_config_sha256": {"oneOf": [sha, {"type": "null"}]},
            "minimum_frontend_version": {"type": "string", "minLength": 1},
            "compatible_runtime_lock_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
        },
        [
            "workflow_module_id", "original_ui_schema_version", "original_ui_sha256",
            "canonical_v1_ui_sha256", "migration_tool_revision",
            "semantic_equivalence_evidence_ids", "api_graph_sha256",
            "flattened_api_graph_sha256", "top_level_meta_removed",
            "allowlisted_patch_map_sha256", "required_node_signature_sha256s",
            "input_bindings", "output_bindings",
            "project_subgraph_source_sha256s", "app_mode_config_sha256",
            "minimum_frontend_version", "compatible_runtime_lock_ids",
        ],
    )

    schemas["comfyui_submission_envelope.schema.json"] = record_schema(
        "Wave64 ComfyUI Submission Envelope",
        "comfyui-submission-envelope",
        "comfyui_submission_envelope",
        "submission_envelope_id",
        {
            "attempt_id": {"type": "string", "minLength": 1},
            "run_id": {"type": "string", "minLength": 1},
            "pass_id": {"type": "string", "minLength": 1},
            "runtime_lock_ref": hash_bound_record_ref("comfyui_runtime_lock"),
            "workflow_release_ref": hash_bound_record_ref("workflow_release_manifest"),
            "prompt_id": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            },
            "client_id": {"type": "string", "minLength": 1},
            "idempotency_key": {"type": "string", "minLength": 1},
            "api_graph_sha256": sha,
            "request_body_sha256": sha,
            "partial_target_node_ids": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "allowlisted_extra_data_keys": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "output_namespace": {"type": "string", "minLength": 1},
            "timeout_seconds": {"type": "integer", "minimum": 1},
            "deadline": {"type": "string", "format": "date-time"},
            "cancellation_token_id": {"type": "string", "minLength": 1},
            "outbox_sequence": {"type": "integer", "minimum": 1},
            "no_duplicate_submission_authority": {"const": True},
            "credentials_embedded": {"const": False},
        },
        [
            "attempt_id", "run_id", "pass_id", "runtime_lock_ref",
            "workflow_release_ref", "prompt_id", "client_id", "idempotency_key",
            "api_graph_sha256", "request_body_sha256", "partial_target_node_ids",
            "allowlisted_extra_data_keys", "output_namespace", "timeout_seconds",
            "deadline", "cancellation_token_id", "outbox_sequence",
            "no_duplicate_submission_authority", "credentials_embedded",
        ],
    )

    safe_relative = r"^(?![A-Za-z]:)(?!/)(?!.*(?:^|[\\/])\.\.(?:[\\/]|$)).+$"
    schemas["comfyui_artifact_locator.schema.json"] = record_schema(
        "Wave64 ComfyUI Artifact Locator",
        "comfyui-artifact-locator",
        "comfyui_artifact_locator",
        "artifact_locator_id",
        {
            "scheme": {"enum": ["comfyui_output", "cas", "s3"]},
            "runtime_id": {"type": "string", "minLength": 1},
            "folder_root_id": {"type": "string", "minLength": 1},
            "folder_type": {"enum": ["input", "output", "temp", "cas", "s3"]},
            "subfolder": {"type": "string", "pattern": safe_relative},
            "filename": {
                "type": "string", "minLength": 1,
                "pattern": r"^(?!.*[\\/])(?!\.\.?$).+$",
            },
            "node_id": {"type": "string", "minLength": 1},
            "output_slot": {"type": "integer", "minimum": 0},
            "view_parameters": {
                "type": "object",
                "required": ["filename", "subfolder", "type"],
                "properties": {
                    "filename": {"type": "string", "minLength": 1},
                    "subfolder": {"type": "string", "pattern": safe_relative},
                    "type": {"enum": ["input", "output", "temp"]},
                },
                "additionalProperties": False,
            },
            "bytes": {"type": "integer", "minimum": 1},
            "sha256": sha,
            "media_type": {"type": "string", "minLength": 1},
            "cas_artifact_id": {"type": ["string", "null"]},
            "s3_object_version_id": {"type": ["string", "null"]},
            "absolute_path_allowed": {"const": False},
            "path_traversal_allowed": {"const": False},
            "verified_at": {"type": "string", "format": "date-time"},
        },
        [
            "scheme", "runtime_id", "folder_root_id", "folder_type",
            "subfolder", "filename", "node_id", "output_slot",
            "view_parameters", "bytes", "sha256", "media_type",
            "cas_artifact_id", "s3_object_version_id", "absolute_path_allowed",
            "path_traversal_allowed", "verified_at",
        ],
    )

    schemas["comfyui_execution_receipt.schema.json"] = record_schema(
        "Wave64 ComfyUI Execution Receipt",
        "comfyui-execution-receipt",
        "comfyui_execution_receipt",
        "execution_receipt_id",
        {
            "submission_envelope_ref": hash_bound_record_ref("comfyui_submission_envelope"),
            "runtime_lock_ref": hash_bound_record_ref("comfyui_runtime_lock"),
            "prompt_id": {"type": "string", "minLength": 1},
            "http_status": {"type": "integer", "minimum": 100, "maximum": 599},
            "queue_number": {"type": ["integer", "null"], "minimum": 0},
            "node_errors_sha256": {"oneOf": [sha, {"type": "null"}]},
            "websocket_event_digest_sha256": {"oneOf": [sha, {"type": "null"}]},
            "websocket_terminal_type": {
                "enum": [
                    "execution_success", "execution_error", "execution_interrupted",
                    "not_observed",
                ]
            },
            "history_or_job_snapshot_sha256": {"oneOf": [sha, {"type": "null"}]},
            "output_locator_refs": {"type": "array", "items": record_ref},
            "terminal_classification": {
                "enum": [
                    "accepted", "failed", "interrupted", "cancelled", "timed_out",
                    "server_restart_unknown", "duplicate_ambiguous", "orphaned",
                ]
            },
            "reconciliation_state": {
                "enum": ["unreconciled", "reconciled", "ambiguous_fail_closed"]
            },
            "error_codes": {"type": "array", "items": {"type": "string"}},
            "secrets_captured": {"const": False},
            "no_silent_substitution": {"const": True},
        },
        [
            "submission_envelope_ref", "runtime_lock_ref", "prompt_id",
            "http_status", "queue_number", "node_errors_sha256",
            "websocket_event_digest_sha256", "websocket_terminal_type",
            "history_or_job_snapshot_sha256", "output_locator_refs",
            "terminal_classification", "reconciliation_state", "error_codes",
            "secrets_captured", "no_silent_substitution",
        ],
    )

    schemas["runtime_reconciliation_report.schema.json"] = record_schema(
        "Wave64 Runtime Reconciliation Report",
        "runtime-reconciliation-report",
        "runtime_reconciliation_report",
        "runtime_reconciliation_report_id",
        {
            "submission_envelope_ref": hash_bound_record_ref("comfyui_submission_envelope"),
            "execution_receipt_refs": {"type": "array", "items": record_ref},
            "outbox_state": {"type": "string", "minLength": 1},
            "event_store_state": {"type": "string", "minLength": 1},
            "runtime_observations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["source", "snapshot_sha256", "observed_state"],
                    "properties": {
                        "source": {"enum": ["jobs", "queue", "history", "files", "cas"]},
                        "snapshot_sha256": sha,
                        "observed_state": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            },
            "classification": {
                "enum": [
                    "not_submitted", "pending", "running", "terminal_consistent",
                    "orphaned", "duplicate", "ambiguous",
                ]
            },
            "selected_action": {
                "enum": [
                    "submit", "observe", "collect_outputs", "cancel_targeted",
                    "retry_same_runtime", "repair_new_attempt", "block_no_failover",
                    "quarantine_duplicate", "promote_once", "no_action",
                ]
            },
            "reason_codes": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "comfyui_queue_history_authority": {"const": "observation_only"},
            "durable_event_store_authority": {"const": True},
            "ambiguous_attempt_cross_host_failover_allowed": {"const": False},
            "promotion_exactly_once": {"const": True},
        },
        [
            "submission_envelope_ref", "execution_receipt_refs", "outbox_state",
            "event_store_state", "runtime_observations", "classification",
            "selected_action", "reason_codes", "comfyui_queue_history_authority",
            "durable_event_store_authority",
            "ambiguous_attempt_cross_host_failover_allowed",
            "promotion_exactly_once",
        ],
    )

    schemas["runtime_worker_lease.schema.json"] = record_schema(
        "Wave64 Runtime Worker Lease",
        "runtime-worker-lease",
        "runtime_worker_lease",
        "runtime_worker_lease_id",
        {
            "runtime_id": {"type": "string", "minLength": 1},
            "runtime_lock_ref": hash_bound_record_ref("comfyui_runtime_lock"),
            "workload_classes": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
            "capacity": {
                "type": "object",
                "required": ["max_concurrency", "max_queue_depth", "vram_mib"],
                "properties": {
                    "max_concurrency": {"type": "integer", "minimum": 1},
                    "max_queue_depth": {"type": "integer", "minimum": 0},
                    "vram_mib": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
            "lease_owner_id": {"type": "string", "minLength": 1},
            "fencing_token": {"type": "integer", "minimum": 1},
            "heartbeat_at": {"type": "string", "format": "date-time"},
            "expires_at": {"type": "string", "format": "date-time"},
            "cancel_capability": {
                "enum": ["targeted_jobs", "queue_delete", "global_interrupt", "none"]
            },
            "degraded_state": {
                "enum": ["healthy", "degraded", "draining", "unavailable"]
            },
        },
        [
            "runtime_id", "runtime_lock_ref", "workload_classes", "capacity",
            "lease_owner_id", "fencing_token", "heartbeat_at", "expires_at",
            "cancel_capability", "degraded_state",
        ],
    )

    schemas["orchestrator_event_payload_envelope.schema.json"] = record_schema(
        "Wave64 Orchestrator Event Payload Envelope",
        "orchestrator-event-payload-envelope",
        "orchestrator_event_payload_envelope",
        "event_payload_envelope_id",
        {
            "event_type": {"type": "string", "minLength": 1},
            "payload_schema_id": {"type": "string", "minLength": 1},
            "payload_schema_revision": {"type": "string", "minLength": 1},
            "payload": {"type": "object"},
            "payload_sha256": sha,
            "schema_validation_passed": {"const": True},
        },
        [
            "event_type", "payload_schema_id", "payload_schema_revision",
            "payload", "payload_sha256", "schema_validation_passed",
        ],
    )

    schemas["orchestrator_state_transition_definition.schema.json"] = record_schema(
        "Wave64 Orchestrator State Transition Definition",
        "orchestrator-state-transition-definition",
        "orchestrator_state_transition_definition",
        "state_transition_definition_id",
        {
            "aggregate_type": {"type": "string", "minLength": 1},
            "from_state": {"type": "string", "minLength": 1},
            "event_type": {"type": "string", "minLength": 1},
            "to_state": {"type": "string", "minLength": 1},
            "payload_schema_id": {"type": "string", "minLength": 1},
            "required_authority": {"type": "string", "minLength": 1},
            "idempotency_scope": {"type": "string", "minLength": 1},
            "terminal": {"type": "boolean"},
            "reversible_by_event_types": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
        },
        [
            "aggregate_type", "from_state", "event_type", "to_state",
            "payload_schema_id", "required_authority", "idempotency_scope",
            "terminal", "reversible_by_event_types",
        ],
    )

    schemas["multimodal_pass_specification.schema.json"] = record_schema(
        "Wave64 Canonical Multimodal Pass Specification",
        "multimodal-pass-specification",
        "multimodal_pass_specification",
        "pass_specification_id",
        {
            "job_ref": hash_bound_record_ref("autonomous_multimodal_job"),
            "dag_id": {"type": "string", "minLength": 1},
            "pass_intent": {"type": "string", "minLength": 1},
            "modality": {"enum": ["image", "video", "audio", "av", "analysis"]},
            "dependency_pass_ids": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "input_artifact_refs": {
                "type": "array", "items": {"$ref": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef"},
            },
            "selection_context_ref": hash_bound_record_ref("model_selection_context"),
            "selection_request_ref": hash_bound_record_ref(
                "contextual_model_selection_request"
            ),
            "target_contract_sha256": sha,
            "protected_contract_sha256": sha,
            "mask_binding_ids": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "qa_gate_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
            "resource_class_id": {"type": "string", "minLength": 1},
            "max_attempts": {"type": "integer", "minimum": 1},
            "accepted_parent_immutable": {"const": True},
            "contains_execution_attempt": {"const": False},
            "contains_promotion_decision": {"const": False},
        },
        [
            "job_ref", "dag_id", "pass_intent", "modality",
            "dependency_pass_ids", "input_artifact_refs", "selection_context_ref",
            "selection_request_ref", "target_contract_sha256",
            "protected_contract_sha256", "mask_binding_ids", "qa_gate_ids",
            "resource_class_id", "max_attempts", "accepted_parent_immutable",
            "contains_execution_attempt", "contains_promotion_decision",
        ],
    )

    schemas["multimodal_execution_attempt.schema.json"] = record_schema(
        "Wave64 Canonical Multimodal Execution Attempt",
        "multimodal-execution-attempt",
        "multimodal_execution_attempt",
        "execution_attempt_id",
        {
            "pass_specification_ref": hash_bound_record_ref(
                "multimodal_pass_specification"
            ),
            "selection_decision_ref": hash_bound_record_ref(
                "contextual_model_selection_decision"
            ),
            "execution_bundle_ref": hash_bound_record_ref("model_execution_bundle"),
            "attempt_number": {"type": "integer", "minimum": 1},
            "repair_hypothesis_ref": {
                "oneOf": [
                    hash_bound_record_ref("failure_diagnosis_and_repair_hypothesis"),
                    {"type": "null"},
                ]
            },
            "submission_envelope_ref": hash_bound_record_ref(
                "comfyui_submission_envelope"
            ),
            "runtime_worker_lease_ref": hash_bound_record_ref("runtime_worker_lease"),
            "fencing_token": {"type": "integer", "minimum": 1},
            "attempt_state": {
                "enum": [
                    "created", "outbox_pending", "submitted", "running",
                    "terminal", "ambiguous", "reconciled", "cancelled",
                ]
            },
            "execution_receipt_refs": {"type": "array", "items": record_ref},
            "output_artifact_refs": {
                "type": "array", "items": {"$ref": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef"},
            },
            "promotion_authority": {"const": "none"},
        },
        [
            "pass_specification_ref", "selection_decision_ref",
            "execution_bundle_ref", "attempt_number", "repair_hypothesis_ref",
            "submission_envelope_ref", "runtime_worker_lease_ref", "fencing_token",
            "attempt_state", "execution_receipt_refs", "output_artifact_refs",
            "promotion_authority",
        ],
    )

    schemas["failure_diagnosis_and_repair_hypothesis.schema.json"] = record_schema(
        "Wave64 Failure Diagnosis and Repair Hypothesis",
        "failure-diagnosis-and-repair-hypothesis",
        "failure_diagnosis_and_repair_hypothesis",
        "repair_hypothesis_id",
        {
            "failed_attempt_refs": {
                "type": "array", "items": record_ref, "minItems": 1,
            },
            "defect_codes": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
            "failed_gate_ids": {
                "type": "array", "items": {"type": "string"}, "uniqueItems": True,
            },
            "causal_class": {
                "enum": [
                    "prompt", "model_bundle", "mask", "ownership", "transform",
                    "workflow", "runtime", "resource", "upstream_plan", "unknown",
                ]
            },
            "localized_scope_sha256": sha,
            "changed_variables": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
            "expected_effect": {"type": "string", "minLength": 1},
            "new_selection_request_ref": {
                "oneOf": [record_ref, {"type": "null"}]
            },
            "remaining_attempt_budget": {"type": "integer", "minimum": 0},
            "hypothesis_authority": {
                "enum": ["planner_candidate", "deterministically_validated", "adjudicated"]
            },
            "accepted_parent_mutation_allowed": {"const": False},
            "promotion_authority": {"const": "none"},
        },
        [
            "failed_attempt_refs", "defect_codes", "failed_gate_ids",
            "causal_class", "localized_scope_sha256", "changed_variables",
            "expected_effect", "new_selection_request_ref",
            "remaining_attempt_budget", "hypothesis_authority",
            "accepted_parent_mutation_allowed", "promotion_authority",
        ],
    )

    schemas["multimodal_qa_evaluation.schema.json"] = record_schema(
        "Wave64 Canonical Multimodal QA Evaluation",
        "multimodal-qa-evaluation",
        "multimodal_qa_evaluation",
        "qa_evaluation_id",
        {
            "execution_attempt_ref": hash_bound_record_ref("multimodal_execution_attempt"),
            "artifact_refs": {
                "type": "array", "items": {"$ref": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef"},
                "minItems": 1,
            },
            "deterministic_gate_results": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["gate_id", "result", "evidence_ids"],
                    "properties": {
                        "gate_id": {"type": "string", "minLength": 1},
                        "result": {"enum": ["pass", "fail", "blocked"]},
                        "evidence_ids": {
                            "type": "array", "items": {"type": "string"},
                            "minItems": 1,
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "critic_observation_refs": {"type": "array", "items": record_ref},
            "target_scope_passed": {"type": "boolean"},
            "protected_scope_passed": {"type": "boolean"},
            "whole_artifact_passed": {"type": "boolean"},
            "decision": {"enum": ["pass", "repair", "reroute", "reject", "block"]},
            "decision_authority": {
                "enum": ["deterministic_qa_policy", "authorized_adjudication"]
            },
            "promotion_authority": {"const": "none"},
        },
        [
            "execution_attempt_ref", "artifact_refs", "deterministic_gate_results",
            "critic_observation_refs", "target_scope_passed",
            "protected_scope_passed", "whole_artifact_passed", "decision",
            "decision_authority", "promotion_authority",
        ],
    )

    schemas["artifact_promotion_transaction.schema.json"] = record_schema(
        "Wave64 Artifact Promotion Transaction",
        "artifact-promotion-transaction",
        "artifact_promotion_transaction",
        "promotion_transaction_id",
        {
            "artifact_ref": {"$ref": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef"},
            "qa_evaluation_refs": {
                "type": "array", "items": record_ref, "minItems": 1,
            },
            "policy_decision_ref": hash_bound_record_ref("autonomous_policy_decision"),
            "prior_accepted_parent_ref": {
                "oneOf": [
                    {"$ref": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef"},
                    {"type": "null"},
                ]
            },
            "idempotency_key": {"type": "string", "minLength": 1},
            "decision": {"enum": ["commit", "reject", "revoke"]},
            "committed_event_ref": {"oneOf": [record_ref, {"type": "null"}]},
            "decision_authority": {"const": "deterministic_promotion_policy"},
            "generator_or_reviewer_self_promotion": {"const": False},
            "exactly_once": {"const": True},
        },
        [
            "artifact_ref", "qa_evaluation_refs", "policy_decision_ref",
            "prior_accepted_parent_ref", "idempotency_key", "decision",
            "committed_event_ref", "decision_authority",
            "generator_or_reviewer_self_promotion", "exactly_once",
        ],
    )

    schemas["canonical_media_clock_span.schema.json"] = record_schema(
        "Wave64 Canonical Media Clock Span",
        "canonical-media-clock-span",
        "canonical_media_clock_span",
        "media_clock_span_id",
        {
            "clock_id": {"type": "string", "minLength": 1},
            "timebase_numerator": {"type": "integer", "minimum": 1},
            "timebase_denominator": {"type": "integer", "minimum": 1},
            "start_pts": {"type": "integer", "minimum": 0},
            "end_pts_exclusive": {"type": "integer", "minimum": 1},
            "frame_rate": {"type": ["number", "null"], "exclusiveMinimum": 0},
            "sample_rate_hz": {"type": ["integer", "null"], "minimum": 1},
            "rounding_policy": {
                "enum": ["floor_start_ceil_end", "nearest_ties_to_even", "exact_only"]
            },
            "source_clock_ref": {"oneOf": [record_ref, {"type": "null"}]},
            "span_sha256": sha,
        },
        [
            "clock_id", "timebase_numerator", "timebase_denominator",
            "start_pts", "end_pts_exclusive", "frame_rate", "sample_rate_hz",
            "rounding_policy", "source_clock_ref", "span_sha256",
        ],
    )

    schemas["cross_engine_bridge_qualification_certificate.schema.json"] = record_schema(
        "Wave64 Cross-Engine Bridge Qualification Certificate",
        "cross-engine-bridge-qualification-certificate",
        "cross_engine_bridge_qualification_certificate",
        "bridge_qualification_certificate_id",
        {
            "source_bundle_ref": hash_bound_record_ref("model_execution_bundle"),
            "target_bundle_ref": hash_bound_record_ref("model_execution_bundle"),
            "workflow_release_ref": hash_bound_record_ref("workflow_release_manifest"),
            "transfer_types": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
                "uniqueItems": True,
            },
            "color_space_policy_id": {"type": "string", "minLength": 1},
            "alpha_policy_id": {"type": "string", "minLength": 1},
            "orientation_policy_id": {"type": "string", "minLength": 1},
            "transform_roundtrip_evidence_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "reintegration_and_seam_evidence_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "protected_preservation_metrics": {"type": "array", "items": metric, "minItems": 1},
            "hard_gate_status": {"enum": ["pass", "fail"]},
            "authority": {"enum": ["qualification_only", "shadow_eligible", "production_eligible"]},
            "valid_until": {"type": "string", "format": "date-time"},
            "revocation_event_id": {"type": ["string", "null"]},
        },
        [
            "source_bundle_ref", "target_bundle_ref", "workflow_release_ref",
            "transfer_types", "color_space_policy_id", "alpha_policy_id",
            "orientation_policy_id", "transform_roundtrip_evidence_ids",
            "reintegration_and_seam_evidence_ids",
            "protected_preservation_metrics", "hard_gate_status", "authority",
            "valid_until", "revocation_event_id",
        ],
    )

    schemas["autonomous_tool_request.schema.json"] = record_schema(
        "Wave64 Autonomous Tool Request",
        "autonomous-tool-request",
        "autonomous_tool_request",
        "tool_request_id",
        {
            "actor_role_activation_ref": hash_bound_record_ref(
                "autonomous_role_activation_decision"
            ),
            "requested_action": {"type": "string", "minLength": 1},
            "requested_target_id": {"type": "string", "minLength": 1},
            "argument_schema_id": {"type": "string", "minLength": 1},
            "arguments_sha256": sha,
            "reason": {"type": "string", "minLength": 1},
            "evidence_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "credential_access_requested": {"const": False},
            "registry_mutation_requested": {"const": False},
            "promotion_requested": {"const": False},
        },
        [
            "actor_role_activation_ref", "requested_action", "requested_target_id",
            "argument_schema_id", "arguments_sha256", "reason", "evidence_ids",
            "credential_access_requested", "registry_mutation_requested",
            "promotion_requested",
        ],
    )

    tool_authorization = record_schema(
        "Wave64 Autonomous Tool Authorization",
        "autonomous-tool-authorization",
        "autonomous_tool_authorization",
        "tool_authorization_id",
        {
            "tool_request_ref": hash_bound_record_ref("autonomous_tool_request"),
            "decision": {"enum": ["allowed", "denied"]},
            "allowlisted_target_id": {"type": ["string", "null"]},
            "authorization_policy_id": {"type": "string", "minLength": 1},
            "policy_revision": {"type": "string", "minLength": 1},
            "reason_codes": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "expires_at": {"type": ["string", "null"], "format": "date-time"},
            "credential_exposure": {"const": False},
            "registry_mutation": {"const": False},
            "certificate_or_promotion_authority": {"const": False},
        },
        [
            "tool_request_ref", "decision", "allowlisted_target_id",
            "authorization_policy_id", "policy_revision", "reason_codes",
            "expires_at", "credential_exposure", "registry_mutation",
            "certificate_or_promotion_authority",
        ],
    )
    tool_authorization["allOf"] = [
        {
            "if": {
                "properties": {"decision": {"const": "allowed"}},
                "required": ["decision"],
            },
            "then": {
                "properties": {
                    "allowlisted_target_id": {"type": "string", "minLength": 1},
                    "expires_at": {"type": "string", "format": "date-time"},
                }
            },
        }
    ]
    schemas["autonomous_tool_authorization.schema.json"] = tool_authorization

    schemas["autonomous_tool_execution_receipt.schema.json"] = record_schema(
        "Wave64 Autonomous Tool Execution Receipt",
        "autonomous-tool-execution-receipt",
        "autonomous_tool_execution_receipt",
        "tool_execution_receipt_id",
        {
            "tool_authorization_ref": hash_bound_record_ref(
                "autonomous_tool_authorization"
            ),
            "executor_id": {"type": "string", "minLength": 1},
            "result_state": {"enum": ["succeeded", "failed", "cancelled"]},
            "result_schema_id": {"type": "string", "minLength": 1},
            "result_sha256": sha,
            "output_record_refs": {"type": "array", "items": record_ref},
            "evidence_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "error_codes": {"type": "array", "items": {"type": "string"}},
            "secrets_captured": {"const": False},
            "registry_mutated": {"const": False},
            "promotion_committed": {"const": False},
        },
        [
            "tool_authorization_ref", "executor_id", "result_state",
            "result_schema_id", "result_sha256", "output_record_refs",
            "evidence_ids", "error_codes", "secrets_captured",
            "registry_mutated", "promotion_committed",
        ],
    )

    schemas["autonomous_context_summary.schema.json"] = record_schema(
        "Wave64 Autonomous Context Summary",
        "autonomous-context-summary",
        "autonomous_context_summary",
        "context_summary_id",
        {
            "source_record_refs": {
                "type": "array", "items": record_ref, "minItems": 1,
            },
            "summary_schema_id": {"type": "string", "minLength": 1},
            "summary_sha256": sha,
            "citation_ids": {
                "type": "array", "items": {"type": "string"}, "minItems": 1,
            },
            "missing_evidence": {"type": "array", "items": {"type": "string"}},
            "conflict_ids": {"type": "array", "items": {"type": "string"}},
            "authority_ceiling": {"const": "navigation_and_context_compaction_only"},
            "creates_new_evidence": {"const": False},
            "may_satisfy_certificate_or_promotion_gate": {"const": False},
            "untrusted_content_sanitization_passed": {"type": "boolean"},
        },
        [
            "source_record_refs", "summary_schema_id", "summary_sha256",
            "citation_ids", "missing_evidence", "conflict_ids",
            "authority_ceiling", "creates_new_evidence",
            "may_satisfy_certificate_or_promotion_gate",
            "untrusted_content_sanitization_passed",
        ],
    )

    schemas["operator_intent_command.schema.json"] = record_schema(
        "Wave64 Operator Intent Command",
        "operator-intent-command",
        "operator_intent_command",
        "operator_command_id",
        {
            "actor_id": {"type": "string", "minLength": 1},
            "command": {
                "enum": [
                    "create_job", "approve_policy_revision", "cancel_attempt",
                    "request_repair", "suspend_bundle", "revoke_certificate",
                    "acknowledge_model_library_staging", "request_phase_transition",
                ]
            },
            "target_refs": {"type": "array", "items": record_ref, "minItems": 1},
            "parameter_schema_id": {"type": "string", "minLength": 1},
            "parameters_sha256": sha,
            "expected_aggregate_version": {"type": "integer", "minimum": 0},
            "idempotency_key": {"type": "string", "minLength": 1},
            "authorization_policy_id": {"type": "string", "minLength": 1},
            "raw_path_or_credentials_present": {"const": False},
            "direct_runtime_mutation": {"const": False},
        },
        [
            "actor_id", "command", "target_refs", "parameter_schema_id",
            "parameters_sha256", "expected_aggregate_version",
            "idempotency_key", "authorization_policy_id",
            "raw_path_or_credentials_present", "direct_runtime_mutation",
        ],
    )

    activation_gate = record_schema(
        "Wave64 Model Library Phase-Safe Activation Gate",
        "model-library-activation-gate",
        "model_library_activation_gate",
        "activation_gate_id",
        {
            "main_task_id": {"const": MAIN_TASK_ID},
            "gate_state": {
                "enum": [
                    "deferred_waiting_for_complete_model_download",
                    "download_reported_pending_inventory_verification",
                    "inventory_verification_failed",
                    "inventory_verified_pending_main_task_acknowledgement",
                    *ACTIVE_GATE_STATE_TO_PHASE.keys(),
                    "suspended",
                ]
            },
            "authorized_phase": {"enum": list(ACTIVATION_PHASES)},
            "activation_scope": {
                "type": "object",
                "required": [
                    "source_snapshot_id", "catalog_artifact_rows",
                    "scope_authority", "all_intended_model_binaries_required",
                    "scope_manifest_ref", "gate_applies_only_to_package_id",
                    "does_not_block_independently_governed_lanes",
                    "independently_governed_lane_ids",
                ],
                "properties": {
                    "source_snapshot_id": {"type": "string", "minLength": 1},
                    "catalog_artifact_rows": {"type": "integer", "minimum": 1},
                    "scope_authority": {
                        "enum": [
                            "pending_main_task_download_completion_declaration",
                            "main_task_declared_complete_scope",
                        ]
                    },
                    "all_intended_model_binaries_required": {"const": True},
                    "scope_manifest_ref": {
                        "oneOf": [
                            typed_record_ref("model_library_expected_download_scope"),
                            {"type": "null"},
                        ]
                    },
                    "gate_applies_only_to_package_id": {"const": PACKAGE_ID},
                    "does_not_block_independently_governed_lanes": {"const": True},
                    "independently_governed_lane_ids": {
                        "type": "array", "items": {"type": "string"},
                        "minItems": 2, "uniqueItems": True,
                    },
                },
                "additionalProperties": False,
            },
            "prerequisites": {
                "type": "object",
                "required": [
                    "download_completion_declared",
                    "download_completion_declaration_ref",
                    "download_manifest_ref", "inventory_verification_ref",
                    "expected_in_scope_assets", "verified_in_scope_assets",
                    "missing_in_scope_assets", "hash_pending_assets",
                    "quarantined_assets", "failed_assets", "unresolved_assets",
                    "all_intended_assets_accounted_for",
                    "main_task_acknowledgement_ref", "main_task_acknowledged",
                    "all_prerequisites_satisfied",
                ],
                "properties": {
                    "download_completion_declared": {"type": "boolean"},
                    "download_completion_declaration_ref": {
                        "oneOf": [
                            typed_record_ref("model_download_completion_manifest"),
                            {"type": "null"},
                        ]
                    },
                    "download_manifest_ref": {
                        "oneOf": [
                            typed_record_ref("model_download_completion_manifest"),
                            {"type": "null"},
                        ]
                    },
                    "inventory_verification_ref": {
                        "oneOf": [
                            typed_record_ref("model_binary_inventory_verification_report"),
                            {"type": "null"},
                        ]
                    },
                    "expected_in_scope_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "verified_in_scope_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "missing_in_scope_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "hash_pending_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "quarantined_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "failed_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "unresolved_assets": {
                        "type": ["integer", "null"], "minimum": 0
                    },
                    "all_intended_assets_accounted_for": {"type": "boolean"},
                    "main_task_acknowledgement_ref": {
                        "oneOf": [
                            typed_record_ref(
                                "main_task_model_library_activation_acknowledgement"
                            ),
                            {"type": "null"},
                        ]
                    },
                    "main_task_acknowledged": {"type": "boolean"},
                    "all_prerequisites_satisfied": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "pre_activation_allowed_actions": {
                "type": "array", "items": {"type": "string"},
                "minItems": 1, "uniqueItems": True,
            },
            "blocked_actions": {
                "type": "array", "items": {"type": "string"},
                "minItems": 1, "uniqueItems": True,
            },
            "phase_permissions": {
                "type": "object",
                "required": list(PHASE_PERMISSION_KEYS),
                "properties": {
                    key: {"type": "boolean"} for key in PHASE_PERMISSION_KEYS
                },
                "additionalProperties": False,
            },
            "fail_closed_reason_codes": {
                "type": "array", "items": {"type": "string"},
                "minItems": 1, "uniqueItems": True,
            },
            "activation_authority": {
                "const": (
                    "deterministic_inventory_verifier_plus_main_task_"
                    "acknowledgement_after_user_download_complete_signal"
                )
            },
            "activation_decision_ref": {
                "oneOf": [
                    typed_record_ref("model_library_phase_transition_decision"),
                    {"type": "null"},
                ]
            },
            "runtime_execution_allowed": {"type": "boolean"},
            "last_evaluated_at": {"type": "string", "format": "date-time"},
        },
        [
            "main_task_id", "gate_state", "authorized_phase", "activation_scope",
            "prerequisites", "pre_activation_allowed_actions", "blocked_actions",
            "phase_permissions", "fail_closed_reason_codes",
            "activation_authority", "activation_decision_ref",
            "runtime_execution_allowed", "last_evaluated_at",
        ],
    )
    activation_gate["allOf"] = [
        {
            "if": {
                "properties": {
                    "gate_state": {"enum": list(ACTIVE_GATE_STATE_TO_PHASE)}
                },
                "required": ["gate_state"],
            },
            "then": {
                "properties": {
                    "runtime_execution_allowed": {"const": True},
                    "activation_decision_ref": typed_record_ref(
                        "model_library_phase_transition_decision"
                    ),
                    "activation_scope": {
                        "properties": {
                            "scope_authority": {
                                "const": "main_task_declared_complete_scope"
                            },
                            "scope_manifest_ref": typed_record_ref(
                                "model_library_expected_download_scope"
                            ),
                        }
                    },
                    "prerequisites": {
                        "properties": {
                            "download_completion_declared": {"const": True},
                            "download_completion_declaration_ref": typed_record_ref(
                                "model_download_completion_manifest"
                            ),
                            "download_manifest_ref": typed_record_ref(
                                "model_download_completion_manifest"
                            ),
                            "inventory_verification_ref": typed_record_ref(
                                "model_binary_inventory_verification_report"
                            ),
                            "expected_in_scope_assets": {
                                "type": "integer", "minimum": 1
                            },
                            "verified_in_scope_assets": {
                                "type": "integer", "minimum": 1
                            },
                            "all_intended_assets_accounted_for": {"const": True},
                            "main_task_acknowledgement_ref": typed_record_ref(
                                "main_task_model_library_activation_acknowledgement"
                            ),
                            "main_task_acknowledged": {"const": True},
                            "all_prerequisites_satisfied": {"const": True},
                            "missing_in_scope_assets": {"const": 0},
                            "hash_pending_assets": {"const": 0},
                            "unresolved_assets": {"const": 0},
                        }
                    },
                }
            },
            "else": {
                "properties": {
                    "authorized_phase": {"const": "none"},
                    "runtime_execution_allowed": {"const": False},
                }
            },
        }
    ]
    schemas["model_library_activation_gate.schema.json"] = activation_gate

    return schemas


MASTER_PLAN = r"""
# Wave64 Autonomous Model Intelligence and Selection Master Plan

Updated: 2026-07-16 America/Chicago

## Decision

Wave64 Rows221-260 are an additive child program of Rows165-172, 197-204,
209-212, and 217-220. The program converts a large discovery library into an
evidence-backed Model Intelligence and Qualification System for character,
image, video, audio, and AV workflows.

The Wave30 Model OS archive is admitted as immutable discovery metadata. It is
not a runtime registry and does not grant selection authority. Its tags,
triggers, folders, selector scores, estimated accuracy, family cards, and
copy-ready labels are useful priors for retrieval and qualification priority.
They cannot prove that an asset exists locally, loads, is compatible with an
exact checkpoint, produces the intended effect, preserves a character, fits the
runtime, or is safe to promote.

Planning coverage is not implementation, installed model evidence, visual or
audio QA, certificate authority, runtime proof, or release completion.

## Current activation state: execution deferred

The complete intended model library has not yet been downloaded. The current
gate is `deferred_waiting_for_complete_model_download`, and no bulk Wave30
staging import, operational-registry mutation, acquisition, installation,
bundle-solver runtime use, qualification, benchmark, pilot, selector/RAG
activation, App Mode runtime integration, certificate generation, or
production routing is authorized.

Before any of that work begins, the main task must receive the user's explicit
download-complete signal and the control plane must bind:

1. an expected-download scope manifest defining every intended model binary;
2. a download-completion manifest with immutable paths or URIs, bytes, and
   hashes and no incomplete transfer files;
3. a deterministic binary-inventory verification report reconciling the
   intended scope with zero missing, hash-pending, corrupt, or unresolved
   assets; and
4. a main-task activation acknowledgement binding the exact package, source,
   download, inventory, and preservation evidence.

The 7,282 catalog rows are not automatically 7,282 distinct binary downloads;
aliases, revisions, duplicate hashes, and modalities must be reconciled in the
expected scope. Unless the user explicitly revises that intended scope, the
gate requires every intended model to be present and verified. Archive
metadata and the 187 copy-ready labels cannot satisfy this gate.

Until it passes, only planning preservation, static schema/registry/test
validation, the already-completed read-only archive audit, read-only download
progress observation when requested, and main-task status communication are
allowed. Missing or conflicting evidence fails closed and unrelated project
work may continue.

## Source facts that shape the design

- The cumulative package is a clean raw-split ZIP stream of five parts,
  367,893,277 bytes, with 675 text members and no model weights.
- It describes 7,282 artifacts, 3,770 model families, 13 selector profiles, and
  650 precomputed recommendations.
- It contains 3,278 FLUX-labeled, 890 Pony-labeled, 875 WAN-video-labeled, and
  836 SDXL-labeled artifacts, plus other families.
- 5,056 artifacts are caution-first-pass candidates, 2,039 require manual
  review, and only 187 are copy-ready for hash verification.
- Every artifact QA state is open. The classification accuracy score is an
  internal-consistency heuristic, not a measured generative-quality score.
- Wave12L planned 4,978 ComfyUI jobs and 71,800 renders but explicitly generated
  no images; several referenced job, sweep, score, prompt, and rubric assets are
  absent.
- The current Main model registry has tens of operational records, not a
  qualified mirror of the 7,282-artifact discovery library.

## Required outcome

The completed system must:

1. admit large source catalogs without converting claims into authority;
2. identify every exact asset by immutable hash, revision, aliases, and lineage;
3. fingerprint engine, architecture, loader, base-family, adapter, and runtime
   compatibility before GPU execution;
4. construct exact selectable execution bundles rather than selecting filenames
   or model brands;
5. qualify assets and bundles through progressive, baseline-controlled,
   capability-specific tests;
6. issue scoped certificates and bucket-specific champions, never a universal
   best-model label;
7. select first-pass, specialist, video, speech, Foley, audio, and AV bundles
   using hard filtering followed by conservative empirical ranking;
8. generate an immutable observation and report for every use;
9. update performance profiles through reproducible batch evidence jobs;
10. detect drift, suspend affected scope, revoke certificates, and roll back;
11. provide cited retrieval and bounded LLM/VLM roles without promotion or
    arbitrary tool authority;
12. expose selection reasons, comparisons, failures, reports, certificates, and
    qualification queues through the operator application.

## Three authority planes

### Discovery plane

Contains source claims, Civitai metadata, Wave30 taxonomy, tags, triggers,
folders, sample metadata, classification confidence, and selector priors. These
records answer what might be relevant and what should be tested next.

### Operational plane

Contains exact hashes, storage instances, binary inspection, architecture
fingerprints, installed paths, loader visibility, workflow bindings, runtime
envelopes, and exact execution bundles. These records answer what can actually
run and under which technical constraints.

### Empirical plane

Contains benchmark cases, outputs, metrics, critic observations, comparisons,
per-use observations, confidence intervals, failure distributions, performance
profiles, certificates, champions, drift, suspension, and revocation. These
records answer what has been proven to work for an exact context.

No fact automatically moves from one plane to the next.

## Selectable unit

The router selects:

    engine family
    + exact base checkpoint or generative model hash
    + VAE and encoder hashes
    + ordered LoRA, adapter, ControlNet, reference, or audio component bundle
    + weights, target instances, target regions, and prompt triggers
    + workflow/API graph hash
    + sampler, scheduler, denoise, and prompt-translation profile
    + custom-node and runtime lock
    + precision, offload, hardware, and resource envelope
    + capability certificate set

A LoRA is not independently selectable when its behavior depends on the
checkpoint, weight, prompt, target, mask, workflow, or neighboring adapters.

## Autonomous decision flow

    job and pass objective
      -> canonical selection context
      -> structured and semantic candidate retrieval
      -> lifecycle, availability, compatibility, certificate, mask, and
         resource hard filters
      -> exact legal execution bundles
      -> matching capability-bucket evidence
      -> Pareto frontier
      -> conservative contextual utility ranking
      -> certified champion, bounded shadow challenger, explicit fallback,
         qualification request, or abstention
      -> execution
      -> deterministic and calibrated critic QA
      -> per-use observation and report
      -> versioned batch profile update
      -> future ranking snapshot

The LLM translates intent, proposes alternatives, designs tests, summarizes
evidence, and explains trade-offs. Deterministic services resolve IDs, enforce
compatibility, calculate ranking features, authorize tools, apply hard gates,
issue certificates, and promote or revoke.

## Progressive qualification

### L0 catalog admission

Validate archive structure, source row counts, IDs, references, encodings,
taxonomy values, JSON embedded in CSV, duplicate groups, and source
contradictions. Authority gained: discovery only.

### L1 binary admission

For a prioritized asset, acquire or locate the exact file, verify the expected
hash, scan its format, inspect tensors and architecture, identify base-family
and loader expectations, and record an installation instance. Authority gained:
binary integrity and architecture evidence.

### L2 isolated load smoke

Load the exact bundle inside a bounded process with a read-only model mount,
ephemeral outputs, memory and time limits, clean teardown, and no arbitrary
network or registry writes. Authority gained: load-smoke evidence for one
runtime envelope.

### L3 functional baseline A/B

Run adapter-off and adapter-on cases with matched prompts, seeds, masks,
workflow, and parent artifacts. Sweep an initial parameter range and measure
target effect and protected invariants. Authority gained: functional candidate.

### L4 capability benchmark

Evaluate held-out characters, scenes, regions, poses, references, masks,
resolutions, and failure cases for one capability bucket. Authority gained:
certificate candidate.

### L5 bundle interaction

Test single components, high-risk pairs, ablations, and the complete recipe.
Authority gained: bundle-specific evidence. An asset certificate does not imply
all stacks are safe.

### L6 cross-engine bridge

Test decoded-artifact round trips, region transforms, color and grain
continuity, identity, seams, and whole-artifact regression for an exact
base/specialist engine pair. Authority gained: pair-specific bridge evidence.

### L7 shadow routing

Keep the current champion authoritative while challengers are proposed or run
without replacing accepted parents. Measure quality, risk, cost, and regret.

### L8 production eligibility

The deterministic policy engine issues a scope-bounded, expiring certificate
only after sample floors, hard gates, evidence completeness, rollback, and
reviewer calibration pass.

## Scalable strategy for 7,282 assets

Brute-force qualification of every model and every pair is neither intelligent
nor affordable. The scheduler first deduplicates identical hashes and clusters
related revisions, architectures, functions, and embeddings. It prioritizes:

    expected route demand
    x uncovered capability value
    x classification or behavior uncertainty
    x expected information gain
    x risk reduction
    / estimated qualification cost

Installed assets, job blockers, high-demand capabilities, current champions,
credible challengers, coverage gaps, high-risk ambiguity, and representative
cluster members run first. Long-tail assets remain searchable and can trigger
on-demand qualification. Family evidence may support discovery and shared
technical facts but never substitutes for artifact and bundle behavior proof.

## Contextual ranking policy

Hard eligibility precedes every score. For eligible candidate c, context x, and
capability bucket b:

    quality_lcb =
        weighted lower confidence bound of required benefit and preservation

    risk_ucb =
        weighted upper confidence bound of serious failures, drift, OOM,
        instability, and regression

    utility(c | x, b) =
        quality_lcb
        - risk_ucb
        - latency, memory, storage, transfer, and monetary cost
        - evidence staleness and scope-distance penalties
        - cross-engine bridge and cache-miss penalties
        + declared cache and batching affinity

Metadata classification priors affect discovery and qualification priority,
not production-quality utility. Required dimensions and weights are frozen by
a versioned job policy. Candidate selection begins with a Pareto frontier so a
single composite number does not erase quality, preservation, reliability, and
resource trade-offs.

New or sparse candidates use uncertainty-aware exploration only in
qualification or shadow modes. Production required passes exploit a current
certificate-covered champion. If no candidate covers the context, the correct
result is qualification enqueued, fallback selected through a new immutable
decision, or abstention.

## Per-use intelligence and reports

Every attempt creates a model-use observation containing the selection request,
decision, candidate exclusions, complete bundle, context, parent and output
hashes, prompts, controls, masks, resource telemetry, metrics, critic
observations, failures, repair, and disposition.

Normal production observations update the complete bundle. Individual component
conclusions require controlled A/B, ablation, or otherwise qualified causal
evidence. Mask, prompt, pose, source, workflow, and parent failures are retained
as confounders rather than attributed to the selected LoRA.

The living report card shows:

- exact asset and bundle identities;
- discovery claims versus measured facts;
- certified, provisional, shadow, untested, suspended, and revoked scopes;
- best and worst contexts;
- base checkpoints and bundle partners;
- prompt and weight response curves;
- target improvement and protected-region preservation;
- identity, anatomy, pose, mask, temporal, audio, and sync behavior;
- sample counts, confidence bounds, outliers, and serious failures;
- VRAM, RAM, latency, load, cache, and cost distributions;
- current certificates, expiry, drift, fallback, and rollback;
- cited generated summaries and separately identified operator annotations.

The execution that produced an observation cannot directly rewrite its score or
promote itself. A versioned recalculation job validates learning eligibility,
keeps holdouts isolated, aggregates immutable records, produces a new profile
revision, and optionally submits a lifecycle decision.

## Content treatment

Content-based suppression is false. Adult or NSFW concepts remain ordinary
descriptive taxonomy and benchmark context. They do not cause hiding,
deprioritization, or a separate model-selection blocker. Binary integrity,
compatibility, provenance, runtime, ownership, evidence, and quality gates
remain technically identical across content categories.

## LLM and VLM architecture

Separate roles are required for planning, prompt composition, retrieval
analysis, router advice, defect classification, image/video review, audio
review, reporting, summarization, and drift triage. Each role receives an
evidence bundle small enough for its context window. It never receives an
unbounded dump of 7,282 cards.

Every self-hosted role binds an exact model revision, runtime, quantization,
template, structured-output parser, context limit, batching policy, hardware
envelope, and role qualification certificate. Exact stacks must pass held-out
grounding, schema, uncertainty, hallucinated-ID, citation, prompt-injection,
tool-authorization, and task-quality benchmarks before activation.

The planner and router advisor may propose model needs, candidates, comparisons,
and repair hypotheses. The VLM and audio critic may emit artifact-, region-,
frame-, span-, or stem-bound observations. They cannot change registry truth,
execute arbitrary graphs, access credentials, satisfy deterministic hard gates,
issue certificates, or promote their own outputs.

## Model change and drift

Model hash, base checkpoint, component order, weight range, VAE, encoder,
workflow, node lock, sampler, prompt template, translator, runtime, precision,
offload, driver, hardware, mask provider, metric, benchmark corpus, or reviewer
changes can invalidate scope. The drift controller identifies affected
certificates, route decisions, cached computations, reports, and fallbacks.

Hash mismatch, corruption, incompatible load, repeated serious deterministic
failure, or a certified risk bound crossing policy suspends new selection for
the affected scope. Requalification, revocation, or rollback occurs through an
immutable policy decision.

## Storage and operations

SQLite in WAL mode may support the single-node prototype event and projection
stores. PostgreSQL is the multi-executor target. High-volume observations,
artifacts, and benchmark media belong in the event/object stores; Git contains
schemas, policies, frozen fixtures, signed snapshots, reports, certificates,
and release projections.

The qualification scheduler uses leases, idempotency, bounded retries,
heartbeats, cancellation, resource admission, clean-process isolation, and
content-addressed caching. The local 8 GiB development GPU retains the existing
7,127 MiB initial certification ceiling and one heavy GPU lease. Heavy
generation and heavy planner/VLM service do not share it without a measured
certificate.

## Implementation sequence

1. Preserve and hash the source archives and current Wave64 package.
2. Freeze schemas, authority tiers, lifecycle axes, IDs, and source crosswalk.
3. Keep all model-library execution deferred while the intended model binaries
   are still being downloaded.
4. After the user reports completion to the main task, freeze the exact
   expected-download scope and download-completion manifest.
5. Run deterministic inventory reconciliation over the completed download and
   require zero missing, hash-pending, corrupt, incomplete-transfer, or
   unresolved in-scope assets.
6. Require the main task to acknowledge the verified evidence and explicitly
   activate staged ingestion. This acknowledgement does not grant model
   capability or production authority.
7. Run the full Wave30 staging import and contradiction report.
8. Build hash, dedupe, static inspection, installation, and compatibility
   services.
9. Build the exact execution-bundle compiler and solver.
10. Build isolated smoke, A/B, sweep, comparison, and benchmark execution.
11. Build evidence aggregation, profiles, reports, certificates, drift, and
   rollback.
12. Build hard-filtered contextual ranking and bounded exploration.
13. Build cited RAG, structured proposals, tool gateway, and role qualification.
14. Qualify the 187 copy-ready pilot plus representative high-value installed
    candidates without treating copy-ready as runtime-ready.
15. Run held-out and shadow selection across image, video, audio, and AV.
16. Integrate Model Explorer and route explanation into the operator app.
17. Expand the long tail by demand, coverage, risk, and information value.
18. Complete release, recovery, security, rollback, and final main-task
    adoption. Final release adoption is separate from the earlier bounded
    activation acknowledgement.

## Definition of done

This program is done only when the archive import reconciles; every selectable
bundle resolves exact hashes and compatibility; every production route is
covered by a current certificate; selection replay produces the same candidate
set and decision from the same snapshot; every use produces an attributable
report; model and reviewer drift can suspend and roll back; shadow floors pass;
the operator can inspect the full reasoning and evidence; and the main task
records formal adoption. Static planning validation alone cannot satisfy done.
The complete-download, deterministic inventory, and main-task activation gate
must also remain traceable to the exact source and package revisions.
"""


READINESS_AUDIT = r"""
# Wave30 Model OS Autonomous Selection Readiness Audit

Audit date: 2026-07-16 America/Chicago

## Verdict

Wave30 is a high-value catalog, taxonomy, review-queue, and migration-planning
package. It is not an empirically qualified model library and its selector
cannot be used directly as production routing authority.

The intended model binaries have not yet been completely downloaded. The
7,282-row staging import, pilot, bundle-solver runtime, benchmark runner, and
downstream autonomous selector integration are therefore deferred until a
complete-download declaration, exact scope manifest, deterministic inventory
verification, and main-task activation acknowledgement are recorded. The
metadata archive's `model_binary_count` of zero cannot satisfy that gate.

## Archive integrity

The five cumulative parts are a raw split of one ordinary single-disk ZIP, not
five independent volumes. Parts one through four are 78,643,200 bytes and part
five is 53,320,477 bytes. The logical stream is 367,893,277 bytes with SHA-256
ab87f86c120085834d86b004e886e733a383ac9246f5f0f34087b6627d373351.
The ZIP contains 675 members, has no unsafe or traversal paths, and passed full
decompression and CRC inspection.

The patch archive is 13,243,618 bytes with SHA-256
19add2d6e5bd298ad9cb985876e8c4b684a4d2e048624dcb19d75b4dfe958d26.
Its 39 members are exact members of the cumulative archive. It is a convenient
subset, not an incremental binary delta.

## What the source contains

- 334 CSV, 220 Markdown, 61 JSON, 42 JSONL, and 18 YAML members.
- 2,577,809,722 uncompressed bytes of text and metadata.
- No checkpoint, LoRA, ControlNet, VAE, video model, audio model, or other
  model-weight binary.
- 7,282 artifact records and artifact-card indexes.
- 3,770 model-family card records.
- A detailed Wave26 metadata selector with engine, function, tags, confidence,
  status, and conflict weights.
- Wave12L visual-test assignments and planning statistics.
- Wave29 classification-consistency scoring and QA queues.

## What the source does not prove

- That the model file exists at a local, S3, or target-runtime location.
- That its recorded hash matches a downloaded file.
- That its architecture matches the normalized engine label.
- That it loads in the intended ComfyUI runtime.
- That a LoRA works with an exact checkpoint, VAE, encoder, workflow, prompt,
  weight, target region, or neighboring LoRA.
- That it improves the desired output rather than merely changing it.
- That it preserves identity, anatomy, pose, ownership, protected regions,
  temporal continuity, audio quality, or synchronization.
- That it fits a VRAM, RAM, latency, cache, or cost envelope.
- That an LLM or critic can evaluate it reliably.

## Measured readiness

The final production statistics describe 5,056 caution-first-pass candidates,
2,039 manual-review-required artifacts, and 187 copy-ready records. Wave30 moved
zero files. All 7,282 artifact QA states remain open and all artifacts are
caution-required.

The apparent strong and acceptable classification-accuracy bands are computed
from internal consistency signals such as known engine, known parent function,
tags, folder agreement, review state, operational confidence, and selector
score. Wave29 explicitly states that this is not measured human-labeled
accuracy. It is also not measured generative behavior.

The manual-review registry contains 29,593 rows with no accumulated reviewer
or QA notes. The quarantine registry remains open. Therefore, the archive does
not yet provide the longitudinal observations requested for future intelligent
selection.

## Visual-test gap

Wave12L contains the correct idea: fixed checkpoint, prompt, negative prompt,
seed set, resolution, sampler, baseline, weight sweep, and visual metrics.
Statistics claim 4,978 jobs and 71,800 render rows, but the documentation states
that it generated no images. The referenced full job plan, weight-sweep table,
score sheet, prompt-template assets, and rubric are absent from the archive.
Wave12L must be rebuilt as executable qualification work rather than accepted as
completed QA.

## Source inconsistencies to preserve and reconcile

- The cumulative root MANIFEST identifies the patch pack and reports 39 files
  although the cumulative archive has 675 members.
- The root README retains a Wave 08 title while describing later waves.
- The root manifest self-size differs from the actual member.
- Selector eligibility and production-status summaries contain a 45-row
  disagreement.
- The archive contains intentional duplicated aliases and cumulative/final
  copies that must not become duplicate model identities.

These are ingestion exceptions, not reasons to discard the source.

## Existing project fit

Wave06 through Wave09 already establish engine-family compatibility, Civitai
metadata use, character-aware model constraints, and environment selection.
Wave64 Rows165-172 establish exact per-pass stacks, hard filters, contextual
ranking, first-pass selection, decoded bridges, translation, and pairing
certification. Rows201-204 establish role separation, registry-grounded
retrieval, structured uncertainty, and exact LLM/VLM stack qualification.

The missing layer is the strict source-to-observation-to-certificate-to-report
system defined by Rows221-260.

## Admission decision

Admit Wave30 as discovery_metadata with runtime_selection_allowed=false and
promotion_allowed=false. Preserve every source row and citation. Normalize it
into strict cards and use it to:

- retrieve candidates;
- estimate test relevance;
- discover conflicts and taxonomy gaps;
- prioritize hash acquisition and qualification;
- seed trigger and weight hypotheses;
- compare source claims with measured behavior.

Do not merge Wave30 scores directly into production model utility. Independent
hash, inspection, install, load, A/B, benchmark, report, and scoped certificate
evidence is required first.
"""


ARCHITECTURE = r"""
# Wave64 Autonomous Model Intelligence Control Plane Architecture

## Component map

    Wave30 and external catalogs
        -> model-library download readiness activation gate
        -> source admission and immutable claim store
        -> normalization, identity, dedupe, and lifecycle service
        -> compatibility and architecture graph
        -> installation and runtime inventory
        -> execution-bundle compiler
        -> qualification scheduler and sandbox executor
        -> benchmark, comparison, and QA services
        -> evidence aggregation, profiles, reports, and certificates
        -> contextual selector and challenger policy
        -> multimodal pass router and ComfyUI execution plane
        -> per-use observation stream
        -> drift, revocation, rollback, and future selector snapshots

    RAG service -> bounded LLM/VLM roles -> structured proposals/observations
                                      |
                           deterministic validator, tool gateway,
                           policy engine, and event store

The activation gate currently stops the pipeline before authoritative source
admission. The metadata archive audit and static planning package may exist on
the left side of the gate, but the 7,282-row staging import and every
operational or empirical service remain inactive until complete-download,
inventory-verification, and main-task acknowledgement evidence passes.

## Service boundaries

### Model-library activation gate

Owns the expected-download scope, download-completion manifest, observed binary
inventory report, main-task acknowledgement, and phase authorization. Its
current state is `deferred_waiting_for_complete_model_download` and its runtime
permission is false. It fails closed on missing, incomplete, stale,
contradictory, mismatched, or superseded evidence. Passing this gate authorizes
only the explicitly named staged-ingestion or qualification phase; it does not
certify any model, bundle, LLM/VLM role, artifact, or production route.

### Source admission

Reads archives and registries in staging, records byte and row provenance,
validates paths and formats, and emits immutable source claims. It cannot create
runtime authority.

### Identity and lifecycle

Owns content identity, aliases, family/version/artifact separation, dedupe,
availability, state axes, transition rules, supersession, suspension, and
revocation. It accepts only authorized lifecycle decisions.

### Compatibility graph

Owns architecture fingerprints and compatible, incompatible, conditional, and
unknown edges among exact component hashes, loaders, workflows, engines, and
runtimes. Unknown is not compatible.

### Bundle compiler

Constructs legal checkpoint, component, workflow, prompt, sampler, and runtime
recipes. It uses constraint solving and bounded beam search. It cannot silently
substitute a similarly named component.

### Qualification scheduler

Prioritizes candidates by demand, capability value, uncertainty, risk,
information gain, and cost. It controls leases, stages, retries, early stopping,
clean process isolation, and budgets.

### Sandbox executor

Runs static inspection, load smoke, A/B, sweep, ablation, bridge, and held-out
jobs. It has no arbitrary network, Git, registry-write, credential, or
promotion authority. Model files are read-only and outputs are ephemeral until
the artifact service records them.

### Evidence and report service

Stores raw observations, experiment designs, metric outputs, reviewer
observations, failures, telemetry, and QA dispositions. Versioned aggregation
jobs produce profiles and reports without mutating raw evidence.

### Certificate service

Applies deterministic sample, confidence, hard-gate, freshness, runtime, and
rollback policies. It issues, expires, suspends, and revokes exact
capability-bucket certificates. It is separate from generation and review.

### Contextual selector

Retrieves candidates, performs hard filtering, resolves matching certificates,
constructs the Pareto frontier, calculates replayable utility, applies the job
policy, and returns a champion, shadow challenger, fallback, qualification
request, blocker, or abstention.

### Autonomous intelligence services

The planner compiles semantic needs and pass proposals. The retrieval analyst
resolves cited evidence. The prompt composer creates engine-native prompt
packages. Router advice explains candidates but does not calculate authority.
VLM and audio critics emit scoped observations. The report writer summarizes
only cited records. All outputs are schema-constrained.

### Policy and tool gateway

The validator resolves every ID and hash. The gateway authorizes allowlisted
actions and owns credentials. The policy engine owns execution admission,
learning eligibility, certificate, promotion, suspension, and revocation
decisions.

## Data stores

- Append-only event store: lifecycle, qualification, execution, QA, selection,
  learning, drift, and policy events.
- Source-claim store: original archive fields and immutable citations.
- Registry projections: current asset, lifecycle, availability, compatibility,
  bundle, certificate, champion, and role-stack views.
- Evidence store: benchmark and per-use structured records.
- Object store: models, input fixtures, generated media, logs, comparisons, and
  reports addressed by content hash.
- Feature store: versioned selection features derived from evidence snapshots.
- Retrieval index: structured, lexical, and vector views with authority,
  freshness, conflict, and negative-evidence metadata.

SQLite may host single-node events and projections. PostgreSQL becomes the
multi-executor target. Object storage remains content-addressed. A cache is
never authoritative.

## APIs

Representative versioned endpoints:

- GET /v1/model-library/activation-gate
- POST /v1/model-library/activation-gate/evaluate
- POST /v1/model-sources/admit
- POST /v1/model-sources/reconcile
- GET /v1/model-assets/{asset_id}
- POST /v1/model-assets/{asset_id}/inspect
- POST /v1/model-bundles/compile
- POST /v1/model-qualification/jobs
- GET /v1/model-qualification/jobs/{job_id}
- POST /v1/model-selection/requests
- GET /v1/model-selection/decisions/{decision_id}
- POST /v1/model-observations
- GET /v1/model-reports/{subject_id}
- POST /v1/model-certificates/decisions
- POST /v1/model-drift/events
- POST /v1/autonomy/retrieve
- POST /v1/autonomy/proposals
- POST /v1/autonomy/tool-actions

All mutation endpoints require idempotency, actor, correlation, causation,
schema version, registry snapshot, and authorization policy bindings.
Every model-source, asset, bundle, qualification, selector, certificate, RAG,
and App runtime mutation endpoint must reject requests while the model-library
activation gate is not active for that exact phase.

## Candidate retrieval at scale

The LLM does not scan the library. A deterministic query compiler maps the
selection context to:

1. lifecycle, installed-location, engine, asset type, pass-intent, target,
   control, mask, certificate, resource, and freshness filters;
2. compatibility graph joins and bundle construction;
3. lexical and embedding retrieval for source claims, failure notes, and
   contextual similarity;
4. top-K empirically eligible bundles plus negative evidence and exclusions.

Approximate nearest-neighbor search may improve discovery latency, but it cannot
override structured hard constraints. Registry snapshot hashes make retrieval
and decisions replayable.

## Evidence ranking

Metric distributions retain count, mean, quantiles, dispersion, confidence
intervals, serious-failure rate, missingness, reviewer version, and evidence
age. Benefits use lower confidence bounds and harms use upper confidence bounds.
Sparse evidence is therefore conservative.

The job policy chooses weights for applicable dimensions. Identity-sensitive
passes heavily weight identity and morphology preservation. Regional passes
weight target effect, protected drift, mask leakage, seams, and whole-image
regression. Video adds temporal identity and transition continuity. Audio adds
event accuracy, intelligibility, voice identity, artifacts, loudness, and sync.

The selector retains the full metric vector and Pareto set in its decision.
Weights and normalization are registry versions, not free-form LLM outputs.

## Exploration

Qualification mode can use expected information value, Bayesian uncertainty,
or contextual bandit methods to choose tests. Shadow mode can compare a
challenger against the champion without changing production. Production mode
does not select an uncertified model for a required pass.

Exploration budgets, eligible pools, blinding, early stopping, and learning
eligibility are separate policies. Results do not promote from one sample.

## Evidence feedback

Each run records bundle-level evidence. Component-level learning requires an
attribution experiment. A batch job:

1. validates terminal QA and lineage;
2. rejects corrupted, duplicated, confounded, stale, or leakage-prone records;
3. partitions qualification, production, shadow, and holdout evidence;
4. recalculates profiles and features;
5. detects drift and significant changes;
6. emits a new evidence snapshot and report;
7. requests, but does not self-approve, lifecycle or certificate changes.

## Failure handling

- Missing hash or asset: block or enqueue acquisition.
- Wrong engine or architecture: exclude before ranking.
- Unknown interaction: keep candidate-only and enqueue comparison.
- Load failure or corruption: record failure and suspend affected runtime scope.
- OOM: invalidate or narrow the hardware envelope, not necessarily the model.
- QA failure: preserve accepted parent and record the failed bundle/context.
- Reviewer disagreement: retain both observations and apply calibration policy.
- No certified candidate: fallback through a new decision, qualification, or
  abstention.
- Drift: suspend affected certificate and route to a current rollback champion.
- Store or queue interruption: reconstruct from events and reconcile artifacts
  before resuming.

## Security and trust

Archive paths, CSV cells, descriptions, tags, prompts, model-card text, source
URLs, and model binaries are untrusted inputs. Admission protects against path
traversal, decompression bombs, malformed rows, formula injection, unsafe model
formats, remote-code loaders, and prompt injection. External text is never
interpreted as tool instructions.

Inference services have no arbitrary filesystem, shell, Git, cloud, credential,
or promotion authority. The gateway uses named allowlists and records denied
actions. Registry writes, certificate decisions, and artifact promotion require
deterministic policy and authorized state transitions.

## Growth path

Revisit SQLite, local vector search, and single-heavy-GPU scheduling when
concurrent executors, millions of observations, or multiple runtime pools make
them the measured bottleneck. PostgreSQL, a dedicated vector index, and a
distributed queue are target evolutions, not initial prerequisites.
"""


IMPLEMENTATION_PROTOCOL = r"""
# Autonomous Model Library Ingestion, Qualification, Selection, and Learning Protocol

## Purpose

This protocol governs how source model catalogs become selectable execution
bundles and how every use becomes future evidence. It applies to checkpoints,
LoRAs, adapters, ControlNets, reference models, upscalers, image-edit models,
video models, motion adapters, speech models, voice adapters, Foley and audio
models, lip-sync models, and multimodal analyzers.

## 0. Model-library activation gate

The current state is `deferred_waiting_for_complete_model_download`.
Rows223-260 and the 7,282-row dry-run import are execution-deferred. Do not
start authoritative staging import, registry mutation, acquisition, copying,
installation, loader exposure, ComfyUI model execution, bundle-solver runtime
use, qualification, benchmark, pilot, evidence/profile/certificate generation,
selector or RAG activation, App runtime integration, or production routing.

Pre-activation work is limited to preserving and reviewing the planning
package, validating its static generated artifacts, retaining the completed
read-only archive audit, observing download progress read-only when explicitly
requested, preparing the expected-download scope without operational import,
and communicating the deferred state.

Activation requires all of the following, bound to immutable revisions:

1. user or main-task declaration that the complete intended model library has
   finished downloading;
2. expected-download scope manifest resolving catalog aliases, revisions,
   duplicates, and modalities into the intended binary set;
3. download-completion manifest with stable locations, bytes, hashes, and zero
   temporary or incomplete transfer files;
4. deterministic inventory verification with zero missing, hash-pending,
   corrupt, quarantined, failed, or unresolved in-scope assets; and
5. acknowledgement by main task 019f422f-88b1-7382-872b-21de2089e983 that
   binds the exact package, source, download, inventory, and preservation
   evidence and authorizes a named phase.

The acknowledgement must follow verification. It authorizes no more than its
named phase and cannot substitute for model capability, QA, certificate, role,
or production promotion gates. Any missing or conflicting prerequisite keeps
the gate closed while unrelated project work continues.

## 1. Source admission

1. Create a model-library source snapshot before reading semantic content.
2. Record part order, bytes, SHA-256, archive type, entry count, compression
   ratio, CRC result, path checks, duplicate names, and manifest relationship.
3. Preserve source rows and member paths exactly in staging.
4. Parse CSV, JSON, JSONL, YAML, and Markdown with explicit encoding.
5. Treat spreadsheet formulas, HTML, prompts, descriptions, tags, triggers, and
   instructions as untrusted data.
6. Validate row IDs, reference integrity, embedded JSON, taxonomy values,
   boolean and numeric normalization, and counts.
7. Record source contradictions without silently selecting one value.
8. Set the maximum authority of source-only records to discovery_metadata.
9. Never copy or download a model merely because a source calls it production,
   copy-ready, high-confidence, or top-ranked.
10. Emit a reconciliation report before operational ingestion.

## 2. Identity and deduplication

Use separate IDs for source claim, family, model, source version, file artifact,
content hash, installation instance, execution component, bundle, workflow,
runtime, qualification plan, benchmark result, certificate, report, and route.

The SHA-256 content identity is authoritative for bytes. A name, model ID,
version ID, or source URL is an alias until the file hash is verified. Identical
hashes share one content record but retain every source alias. Different hashes
remain different revisions even when names match.

Version and supersession do not delete history. Historical bundles and
artifacts keep their original references.

## 3. Independent lifecycle axes

Track these axes independently:

- identity: discovered, canonicalized, hash_verified, duplicate_alias;
- binary integrity: unscanned, passed, quarantined, failed;
- classification: unclassified, proposed, reviewed, frozen;
- availability: remote_only, cache_pending, installed_quarantine,
  installed_verified, missing;
- runtime: untested, static_passed, load_smoke_passed,
  functional_smoke_passed, failed, suspended;
- capability authority: research_candidate, benchmark_candidate,
  provisional, shadow_challenger, production_eligible, suspended, revoked,
  superseded;
- evidence: current, stale, contradicted, revoked.

A production route requires every applicable axis and a current scoped
certificate. One status string cannot replace this state vector.

## 4. Asset acquisition and static inspection

Acquisition is a separate authorized job and remains prohibited until the
model-library activation gate authorizes that phase. Once authorized, it must:

1. resolve the exact expected hash and source;
2. download or copy into a quarantine path;
3. verify bytes and size before loader visibility;
4. inspect format and tensor structure without executing remote code;
5. identify architecture, base family, target modules, ranks, alphas, dtypes,
   quantization, and loader assumptions where applicable;
6. compare observed architecture with source claims;
7. scan corruption, malformed tensors, unsafe formats, and duplicate content;
8. record a verified installation instance;
9. expose only allowlisted model roots to ComfyUI;
10. keep failed or mismatched assets unavailable to production.

Content labels do not affect binary-integrity rules.

## 5. Capability hypotheses

Discovery metadata creates hypotheses, not certificates. A hypothesis can
describe likely engine, function, target region, modality, trigger, weight,
mask, control, or conflict. Each field carries source, confidence, freshness,
and conflict information.

The qualification planner converts hypotheses into measurable expected changes
and protected invariants. Generic claims such as quality, realism, anatomy, or
motion must be decomposed into testable metrics and cases.

## 6. Exact bundle construction

The bundle compiler receives a selection context or qualification target and:

1. chooses an exact base model;
2. enumerates compatible component candidates by semantic slots;
3. applies architecture, family, loader, workflow, and runtime edges;
4. enforces one primary component per exclusive slot unless pair proof exists;
5. binds target character instances and target regions;
6. binds weights, order, triggers, prompt translation, controls, and masks;
7. binds workflow, sampler, scheduler, runtime, precision, offload, and hardware;
8. hashes the canonical recipe;
9. records unknown interactions;
10. outputs legal bundles or typed blockers.

The compiler may use bounded beam search to avoid combinatorial explosion.
Greedy filename matching and cross-family component mixing are forbidden.

## 7. Qualification planning

Priority is calculated from:

- active job blockers;
- route demand and expected reuse;
- uncovered capability value;
- confidence and behavior uncertainty;
- source contradiction or risk;
- representative coverage of a family or cluster;
- challenger quality potential;
- expected information gain;
- acquisition, GPU, storage, and review cost.

The planner selects the lowest stage that can answer the current uncertainty.
It does not schedule all 71,800 legacy planned renders automatically.

Qualification plans bind baselines, fixed inputs, expected effects, protected
invariants, seeds, weights, prompts, masks, controls, workflows, budgets,
metrics, gates, early stopping, retry, cleanup, evidence, and target authority.

## 8. Sandbox execution

Each asset or bundle runs in a clean bounded process with:

- read-only model and fixture mounts;
- ephemeral working and output directories;
- no arbitrary network;
- allowlisted loader and workflow modules;
- wall, queue, heartbeat, GPU, RAM, VRAM, disk, and output limits;
- exact environment and dependency hashes;
- resource telemetry and accessed-file logging;
- graceful cancel, forced termination, and cleanup;
- no registry, certificate, or promotion credentials.

An infrastructure failure may be replayed identically when no artifact was
created. A quality failure requires a materially different hypothesis.

## 9. Baseline and sweep protocol

For LoRAs and adapters, begin with a no-adapter baseline and matched adapter-on
cases. Keep parent, crop, masks, prompt intent, negative constraints, workflow,
sampler, seed, and output size fixed.

Run a coarse safe weight or strength grid, then adaptively refine promising
regions. Record best envelope, overcook threshold, instability, target effect,
protected drift, prompt sensitivity, and seed variance. Stop early on repeated
hard failures, no measurable effect, severe regressions, or exhausted budget.

Checkpoint comparisons use equivalent prompt and control contracts but retain
engine-native translations rather than copying raw settings blindly.

Video and audio tests preserve timebase, duration, event, dialogue, and
reference authority. Full playback or listening is part of evidence.

## 10. Benchmark and comparison protocol

Benchmark cases are immutable and split into development, calibration, and
held-out partitions. Candidate identity is hidden from critics where practical.

Use:

- baseline A/B for effect;
- matched-candidate comparisons for route choice;
- component ablations for attribution;
- strength curves for operating envelopes;
- pair and full-bundle tests for interaction;
- decoded-bridge comparisons for cross-engine transitions;
- repeated seeds and cases for stability;
- adversarial and known-failure cases for risk.

Qualification evidence and ordinary production feedback remain distinct.
Holdout results are not used to tune the same policy revision.

## 11. Certificate protocol

A certificate binds:

- exact bundle and component hashes;
- capability scope and pass intent;
- base checkpoint and component order;
- character, instance-count, target, mask, control, and reference constraints;
- weight and parameter envelope;
- workflow, runtime, precision, and hardware;
- benchmark and comparison result IDs;
- sample counts and confidence bounds;
- hard gates and exclusions;
- valid-from, valid-until, drift triggers, revocation, and rollback.

One attractive sample, a load smoke, metadata confidence, or a family result
cannot issue a production certificate.

## 12. Production selection

The request compiler creates a canonical context and immutable context hash.
The selector:

1. retrieves lifecycle-eligible assets and bundles;
2. filters missing, incompatible, uncertified, stale, wrong-scope, wrong-mask,
   wrong-character, prohibited, or resource-ineligible candidates;
3. records every exclusion;
4. retrieves matching performance profiles and certificates;
5. builds applicable metric vectors and confidence bounds;
6. constructs the Pareto frontier;
7. applies a versioned quality, risk, cost, and runtime policy;
8. chooses a certified champion, or returns qualification, fallback, blocker,
   or abstention;
9. optionally records one bounded shadow challenger;
10. emits a complete immutable decision.

Forced model use is diagnostic and non-promoting unless its normal certificate
already covers the request.

## 13. LLM proposal and RAG

The LLM receives:

- a structured job and pass objective;
- a bounded cited evidence bundle;
- top eligible or hypothesis candidates;
- negative evidence, conflicts, missing proof, and uncertainty;
- exact schemas and allowed actions.

It may propose needs, candidates, prompt packages, comparisons, and repair
hypotheses. It must cite immutable IDs. Unknown IDs, stale claims, unsupported
triggers, arbitrary paths, direct workflow graphs, and authority changes are
rejected.

The retrieval service uses structured constraints first, then lexical/vector
similarity. Context manifests record included and excluded records, token
budgets, compaction summaries, conflicts, and missing evidence.

## 14. QA and reviewer protocol

Deterministic services evaluate hashes, formats, dimensions, coordinates,
lineage, masks, ownership, timing, resource limits, and thresholds. Calibrated
metrics evaluate applicable perceptual and acoustic properties. VLM and audio
critics emit observations tied to regions, frames, spans, stems, and artifact
IDs with uncertainty.

Critics cannot promote, certify, execute, or rewrite evidence. Disagreement is
stored and resolved by policy or authorized adjudication.

## 15. Per-use observation

Every terminal attempt writes a model-use observation, including failure and
cancelled attempts. It binds:

- route request and decision;
- context and exact bundle;
- input, parent, target, protected, and output artifacts;
- prompt, trigger, control, mask, and parameter packages;
- runtime and resource telemetry;
- deterministic metrics and critic observations;
- failure, repair, fallback, and QA disposition;
- component-attribution confidence;
- learning eligibility and exclusion reasons.

The report writer produces a cited narrative view but never replaces raw
records.

## 16. Evidence recalculation

Only a versioned batch job updates performance profiles. It:

1. validates source records and terminal QA;
2. removes duplicates and corrupt observations;
3. keeps rejected and negative results;
4. separates qualification, production, shadow, and holdout evidence;
5. checks confounders and attribution;
6. calculates distributions, confidence, risk bounds, and freshness;
7. produces a new profile, report, and selection-feature snapshot;
8. compares the prior snapshot for drift;
9. requests lifecycle or certificate action when thresholds are crossed;
10. leaves prior snapshots immutable and replayable.

## 17. Drift and rollback

Drift monitoring covers model bytes, components, workflows, nodes, runtimes,
hardware, prompts, translations, masks, metrics, corpora, reviewers, and
workload. Affected scope is computed from dependency edges.

Immediate technical suspension includes hash mismatch, corruption,
incompatible load, repeated serious deterministic failure, and certified risk
bounds exceeding policy. The route selector uses the recorded rollback champion
or creates a new fallback decision. Requalification is required before
restoring authority.

## 18. Reporting and App Mode

The operator surface includes:

- source and archive health;
- family, asset, revision, duplicate, and installation views;
- capability and compatibility graph;
- bundle recipes and component conflicts;
- qualification queue and budget;
- baseline, sweep, comparison, and held-out media;
- performance profiles, certificates, failures, and drift;
- model-use history and living reports;
- selection candidates, exclusions, Pareto frontier, rank features, reasons,
  uncertainty, fallback, and challenger;
- LLM/VLM proposals and observations with citations;
- promotion, suspension, revocation, and rollback decisions.

Normal use hides node IDs, raw credential paths, and mutable registry internals.

## 19. Fail-closed conditions

Block or abstain on:

- unknown or mismatched content hash;
- missing or unverified binary;
- architecture or family contradiction;
- unsafe or corrupt format;
- missing workflow or runtime lock;
- unknown required interaction;
- missing target or protected ownership;
- insufficient mask authority;
- absent or stale capability certificate;
- context outside certificate scope;
- resource envelope violation;
- missing ranking feature authority;
- retrieval conflict that changes eligibility;
- hallucinated ID or unsupported LLM claim;
- unauthorized tool, registry, certificate, or promotion action.

Unrelated passes may continue when their dependencies remain satisfied.

## 20. Preservation and handoff

Rows001-220 and their accepted evidence remain unchanged. Rows221-260 are
planning-only until the main task reviews and adopts them. Do not clean,
delete, renumber, merge into a current FLUX lane, or infer completion from the
presence of schemas, examples, or static tests.

The current package is additionally execution-deferred until the complete
intended model download, deterministic inventory verification, and main-task
activation acknowledgement are all recorded. Preservation or planning adoption
does not activate ingestion or qualification.
"""


QA_PROTOCOL = r"""
# Autonomous Model Intelligence QA and Promotion Protocol

## Core rule

The model library has two separate QA questions:

1. Is the catalog and classification record internally correct?
2. Does the exact execution bundle measurably work for the requested context?

Wave30 substantially addresses the first question as planning metadata. This
package defines the second and prevents the first from being mistaken for it.

## Gate families

### MI-QA-00 Model-library download readiness and activation

Before L0 or the 7,282-row dry-run import, validate the expected-download scope,
download-completion manifest, stable binary locations, bytes and hashes,
absence of incomplete transfers, deterministic inventory reconciliation, zero
missing/hash-pending/corrupt/quarantined/failed/unresolved in-scope assets, and
main-task acknowledgement of the exact evidence. The current gate is deferred
and `runtime_execution_allowed` is false. Archive integrity, metadata, planning
tests, copy-ready labels, and unrelated installed models cannot pass this gate.

### MI-QA-01 Source and archive integrity

Verify part order, bytes, hashes, ZIP integrity, member counts, path safety,
compression limits, encoding, row counts, unique IDs, references, embedded
JSON, and source-manifest inconsistencies.

### MI-QA-02 Identity and binary integrity

Verify exact SHA-256, size, format, tensor structure, architecture fingerprint,
base family, target modules, loader expectation, corruption, duplicate group,
and installation instance.

### MI-QA-03 Compatibility

Verify engine, checkpoint, VAE, encoder, LoRA, control, scheduler, workflow,
node, runtime, prompt translator, precision, and hardware compatibility.
Unknown is not pass.

### MI-QA-04 Runtime load and resource

Verify clean-process load, bounded output, accessed files, peak VRAM/RAM, wall
time, timeout, teardown, repeatability, and the certified envelope. OOM narrows
or suspends the envelope.

### MI-QA-05 Target effect

Verify that the selected asset or bundle produces the declared effect in the
owned target with sufficient magnitude and correctness.

### MI-QA-06 Protected preservation

Verify identity, morphology, pose, count, ownership, target-external regions,
wardrobe, environment, color, grain, timing, voice, stems, and synchronization
as applicable.

### MI-QA-07 Regional and mask quality

Verify target ownership, mask authority, transforms, leakage, boundary,
seam, crop, padding, feather, denoise, reinsertion, and whole-artifact
regression.

### MI-QA-08 Temporal and audio quality

Verify frame continuity, motion, contact, identity, flicker, transition, event
timing, intelligibility, voice identity, Foley accuracy, artifacts, loudness,
spatial behavior, and AV synchronization.

### MI-QA-09 Attribution

Verify baseline, matched variables, seeds, prompts, masks, workflows,
ablation, confounders, and attribution confidence before updating an individual
component profile.

### MI-QA-10 Evidence and statistics

Verify sample floors, missingness, outliers, negative evidence, confidence
bounds, serious-failure rates, calibration, freshness, holdout separation, and
reproducible aggregation.

### MI-QA-11 Selection replay

Verify registry, feature, policy, certificate, and context snapshots; candidate
exclusions; Pareto frontier; score components; uncertainty; selected bundle;
fallback; challenger; and identical replay from identical inputs.

### MI-QA-12 Autonomous role quality

Verify structured-output validity, ID resolution, citations, evidence
grounding, uncertainty, abstention, prompt-injection resistance, tool
authorization, role task quality, and no unauthorized state change.

### MI-QA-13 Lifecycle and certificate

Verify scope, evidence, authority, expiry, suspension, revocation, rollback,
and requalification. No generator or reviewer approves itself.

### MI-QA-14 Recovery, security, and operations

Verify leases, idempotency, cancellation, restart, event replay, artifact
reconciliation, backups, storage, cache invalidation, least authority, path and
archive attacks, unsafe loaders, and denied tool actions.

## Metric model

There is no universal model score. Applicable metrics are selected by
capability bucket. Each metric records direction, unit, authority, sample count,
distribution, confidence, evidence, and calibration.

Image dimensions include target-effect accuracy, identity similarity,
morphology preservation, pose error, count and ownership, anatomy stability,
skin/hair/material fidelity, protected-region drift, mask leakage, seam,
prompt/control adherence, photoreal coherence, and artifacts.

Video dimensions add temporal identity, flicker, motion, camera, contact,
transition, span-repair boundary, duration, and frame integrity.

Audio dimensions add intelligibility, voice identity, prosody, event accuracy,
timing, acoustic fit, noise, clipping, loudness, spatial coherence, and full-mix
regression.

AV dimensions add frame/sample/PTS alignment, lip and event sync, stream
integrity, mux, duration, and complete playback.

Operational dimensions include load success, serious failure, OOM, peak memory,
latency, throughput, cache behavior, storage, transfer, determinism, and cost.

## Evidence authority

From weakest to strongest:

1. source claim;
2. normalized discovery metadata;
3. static measurement;
4. runtime observation;
5. controlled qualification measurement;
6. calibrated or adjudicated review;
7. scoped certificate.

Higher authority does not erase contradictory lower evidence. It determines
which facts may satisfy a gate.

## Initial qualification floors

The exact threshold registry is calibrated and frozen before production, but
the following minimum structure applies:

- L2 load smoke: at least one successful bounded output and one clean reload;
- L3 functional candidate: baseline plus at least three matched seeds across a
  minimum four-point initial weight or strength sweep;
- provisional bucket evidence: at least 20 paired outputs across at least five
  distinct benchmark cases, with no unresolved hard failure;
- production certificate: at least 50 paired outputs across at least ten cases,
  required hard gates passing, calibrated critic coverage, rollback proof, and
  confidence/risk bounds inside the bucket policy;
- high-risk pair or bundle: single-component baselines, pairwise comparison,
  full-recipe comparison, and protected-invariant QA;
- bridge certificate: at least ten paired source/bridge outputs across at least
  three target classes plus seam and whole-artifact regression;
- shadow challenger promotion consideration: at least ten successful shadow
  comparisons in addition to offline certificate evidence.

Policies may require higher floors by risk, modality, character count, target,
or certificate scope. Floors never transfer to another hash or bundle.

## Existing Wave64 floors retained

- router: at least 100 valid and 100 adversarial fixtures, zero incompatible
  selections;
- single-character image: at least 30 cases across six or more buckets;
- two-character/contact: at least 24 cases across at least three character
  pairs and four interaction buckets;
- video: at least 12 clips including failed-span repair;
- speech: at least 30 held-out utterances;
- Foley: at least 30 held-out events;
- AV: at least 12 complete clips;
- planner: at least 100 held-out requests;
- reviewer: at least 200 adjudicated panels;
- tool gateway: at least 100 adversarial authorization, path, and injection
  cases;
- autonomy: at least 30 complete shadow jobs before activation.

## Wave30 pilot strategy

Do not begin this strategy until MI-QA-00 passes for the exact activated phase.
After activation, do not run all planned 71,800 renders immediately. First:

1. reconcile all 7,282 discovery rows;
2. deduplicate hashes and family/revision clusters;
3. identify the 187 copy-ready candidates and currently installed models;
4. stratify by engine, role, region, modality, demand, uncertainty, and risk;
5. qualify representative assets and high-value job blockers;
6. use early stopping to remove no-effect and high-regression candidates;
7. expand promising candidates into bucket and interaction benchmarks;
8. keep the long tail discoverable and on-demand-testable.

Copy-ready means eligible for verified acquisition, not runtime authority.

## Ranker validation

Validate the ranking policy through:

- deterministic replay from frozen snapshots;
- zero scores for ineligible candidates;
- lower-confidence benefit and upper-confidence risk behavior;
- sparse-evidence conservatism;
- metadata-prior authority ceiling;
- correct Pareto frontier;
- job-policy weight and normalization versioning;
- tie, fallback, abstention, and challenger behavior;
- ranking regret against held-out outcomes;
- subgroup and capability calibration;
- stale evidence and drift response;
- latency with the full discovery registry.

An LLM explanation is not the ranking calculation.

## Critic calibration

For every VLM, video, or audio reviewer stack:

- bind exact model/runtime/template/parser/quantization/context;
- label held-out cases with artifact, region, frame, span, or stem truth;
- measure false accept, false reject, localization, confidence calibration, and
  disagreement;
- include negative, subtle, multi-character, occluded, temporal, and acoustic
  cases;
- prevent candidate identity leakage where practical;
- compare reviewer revisions before activation;
- retain abstention and disagreement;
- revoke or narrow authority on drift.

Critic observations never override deterministic facts.

## Promotion transaction

A certificate or lifecycle promotion is atomic:

1. freeze source, bundle, workflow, runtime, benchmark, metric, reviewer, and
   policy snapshots;
2. validate every reference and hash;
3. verify sample floors and confidence;
4. verify all applicable hard gates;
5. verify no unresolved serious failure or conflicting authority;
6. verify rollback champion and requalification triggers;
7. issue the policy decision;
8. append the lifecycle event;
9. write the certificate and new projection;
10. invalidate affected selection and cache projections;
11. retain all prior records.

Any failure leaves the prior state authoritative.

## Per-use report acceptance

A report is accepted only if it resolves the exact decision, bundle, context,
parents, outputs, metrics, critic observations, failures, learning eligibility,
and evidence snapshot. Generated notes cite evidence and are labeled as
summaries. Operator annotations are separate records. Missing evidence appears
as missing; it is not synthesized.

## Release blockers

Rows221-260 cannot be called complete while any of these remain:

- complete intended model download has not been declared to the main task;
- expected-download scope manifest is absent, stale, or unresolved;
- download-completion manifest is absent or contains incomplete transfers;
- deterministic binary inventory does not reconcile every in-scope asset;
- any in-scope model is missing, hash-pending, corrupt, quarantined, failed, or
  unresolved;
- main task 019f422f-88b1-7382-872b-21de2089e983 has not acknowledged the exact
  download, inventory, package, source, and preservation evidence and activated
  the required phase;
- unresolved archive or row-count reconciliation;
- selectable asset without verified identity and lifecycle;
- selectable bundle without complete component and workflow hashes;
- untested hard compatibility;
- production route without a matching current certificate;
- rank feature without evidence and policy version;
- per-use execution without a terminal observation;
- direct online score mutation;
- uncalibrated critic used as a hard authority;
- LLM with registry, certificate, credential, or promotion authority;
- unrehearsed drift, revocation, restore, or rollback;
- missing main-task adoption and preservation decision.
"""


HANDOFF = r"""
# Autonomous Model Intelligence Main-Session Handoff

Target main task: 019f422f-88b1-7382-872b-21de2089e983

## Preservation request

Preserve the additive Wave64 Rows221-260 Model Intelligence package. Do not
delete, clean, renumber, merge into the current FLUX.2 lane, or infer runtime
completion from these dirty or untracked files.

This package extends:

- Rows165-172 for exact pass-level capability, compatibility, ranking, first
  pass, specialist, and cross-engine selection;
- Rows197-200 for event store, scheduling, and recovery;
- Rows201-204 for role-separated self-hosted LLM/VLM, RAG, structured output,
  tool authority, and qualification;
- Rows209-212 for scorecards, benchmarks, critics, and release;
- Rows217-220 for phased implementation and main-task adoption.

## Source decision

The supplied Wave30 cumulative and patch archives were inspected read-only.
They are clean metadata archives describing 7,282 artifacts and 3,770 families,
with no model weights. Their selector is a discovery prior, not empirical
production authority. Admit the source at discovery_metadata only.

## Immediate execution decision: deferred

The complete intended model library has not been downloaded. Do not start the
7,282-row staging import, model acquisition/copy/install, inventory admission,
bundle-solver runtime use, pilot qualification, benchmarks, selector/RAG or
LLM/VLM activation, App Mode runtime integration, certificate work, or
production model routing.

The authoritative gate is `wave64_model_library_download_readiness_gate_v1`.
Its current state is `deferred_waiting_for_complete_model_download`, and
`runtime_execution_allowed` is false. This handoff is a notice to preserve the
plan and record the deferral; it is not a claim that downloads are complete and
is not an activation acknowledgement.

When the user later tells the main task that every intended model has finished
downloading, the main task must bind and verify:

- the exact expected-download scope;
- the download-completion manifest with stable paths or URIs, bytes, and
  hashes and no incomplete transfers;
- the deterministic binary inventory report with every in-scope asset
  accounted for, zero unresolved missing or hash-pending assets, and every
  corrupt or unsafe asset explicitly quarantined and excluded from runtime;
- the exact source snapshot, package, and preservation revisions; and
- an explicit main-task acknowledgement naming the activated phase.

The acknowledgement may occur only after verification and does not qualify a
model or authorize production selection.

## Integration order

1. Review the preservation manifest after the active FLUX.2 checkpoint.
2. Formally adopt or reject the Rows221-260 namespace.
3. Keep the Wave30 archives outside Git and keep model-library execution
   deferred while downloads remain incomplete.
4. Freeze the expected logical and unique-binary download scope before the
   user's completion signal; this scope cannot move merely to make completion pass.
5. Wait for the user's download-complete signal to the main task, bind the
   completion manifest, and then run deterministic inventory verification.
6. Record the main-task acknowledgement for `active_staging_only` after every
   prerequisite passes.
7. Import through the source snapshot and implement strict source staging and
   reconciliation.
8. Implement identity, binary inspection, compatibility, and bundle
   construction before model QA execution.
9. Issue a separate transition decision for `active_qualification`; staged
   ingestion never implies GPU qualification, benchmarking, or certificates.
10. Implement the progressive qualification, report, certificate, and drift
   services.
11. Connect contextual selection to the multimodal router in shadow mode only
    after an `active_shadow_selection` transition.
12. Connect RAG and self-hosted roles only through exact-stack qualification
    and an independent role-activation decision.
13. Run the 187-copy-ready pilot and representative installed candidates.
14. Activate autonomous production selection only after held-out and shadow
    release gates pass.

## Status truth

Rows221-222 retain static-control planning status. Rows223-260 are
Deferred_Pending_Complete_Model_Library_Download_Inventory_Verification_And_Main_Task_Acknowledgement.
runtime_completion_claimed is false. Archive integrity, planning validation,
and this notification do not qualify a single model or autonomous role and do
not authorize ingestion or execution.
"""


SECOND_PASS_AUDIT = r"""
# Wave64 Second-Pass Autonomous Workflow and Model Intelligence Assurance Audit

Updated: 2026-07-16 America/Chicago

## Verdict

The strategic baseline is comprehensive and directionally correct. The second
pass closes the highest-risk planning-contract gaps, but it does not claim a
production controller, qualified model library, active self-hosted LLM/VLM,
or certified end-to-end character-to-AV runtime. The truthful state is:

- architecture baseline: complete;
- phase-safe model-library planning and core runtime contract hardening:
  substantially complete;
- canonical migration of every overlapping Rows149-220 record: still open;
- controller, durable event runtime, scheduler, adapters, App/controller UI,
  empirical model qualification, and full release certification: not built.

## Findings closed in this pass

1. The former combined staging-and-qualification state is replaced with an
   ordered ladder: none, staging, qualification, shadow selection, production
   selection. Each state has an exact permission ceiling and one append-only
   transition decision. Download completion can authorize staging only.
2. Expected download scope, download completion, binary inventory
   verification, main-task acknowledgement, and phase transition now have
   strict record contracts. Quarantined assets count as accounted but remain
   runtime-ineligible; missing, hash-pending, or unresolved assets fail closed.
3. The gate is scoped only to the Rows221-260 Model Intelligence program. It
   does not cancel or stall the separately governed FLUX.2 proof lane or the
   MaskFactory task.
4. Model selection now binds typed target/protected contracts, MaskFactory
   ownership, person index, ontology, coordinate transforms, certificate
   requirements, Mode-B draft ceilings, and no-write-gold invariants.
5. Production selection decisions must resolve to an evaluated, eligible,
   certificate-covered, hash-bound bundle on the Pareto frontier. Capability
   certificates, policy decisions, and tool actions receive cross-field gates
   and semantic validators.
6. The ranking policy freezes a replayable numeric v1 baseline: feature
   normalization, confidence methods, weights, missing-data rules, production
   thresholds, tie branching, abstention, assignment probability, and holdout
   controls. It remains subject to versioned empirical recalibration.
7. Every autonomous role remains explicitly inactive until an exact stack,
   role certificate, shadow evidence, tool policy, model-library phase ceiling,
   and separate activation decision all pass. Roles retain no direct execution,
   registry, certificate, credential, or promotion authority.
8. The ComfyUI boundary now has strict contracts for runtime locks, workflow
   releases, idempotent submissions, receipts, safe artifact locators,
   reconciliation, worker leases/fencing, typed event payload envelopes, and
   aggregate transitions.

## ComfyUI runtime truth

ComfyUI is the execution engine, not the durable autonomous authority. Its
queue/history and WebSocket stream are observations that may disappear or
disconnect. The external controller must use an append-only event store,
transactional outbox, unique idempotency keys, runtime leases with fencing,
content-addressed artifact registration, and post-disconnect reconciliation.
An ambiguous submission cannot fail over to another host or promote.

App Mode remains a thin workflow launcher and result surface. Character
Library, multi-workflow DAG state, QA, repair, recovery, model reports, and
route explanations belong to a separate durable controller console or a
purpose-built frontend extension.

Official references:

- https://docs.comfy.org/development/comfyui-server/comms_routes
- https://docs.comfy.org/development/comfyui-server/comms_messages
- https://docs.comfy.org/specs/workflow_json
- https://docs.comfy.org/interface/app-mode
- https://docs.comfy.org/interface/features/subgraph

## Remaining release-critical implementation work

1. Migrate every existing Rows149-220 consumer from its legacy RecordRef form
   to the now-published canonical immutable-reference/deprecation crosswalk.
2. Make `model_execution_bundle` the sole selectable execution unit and bind
   every multimodal route decision to its contextual selection decision.
3. Migrate legacy combined pass records to the now-published separate pass
   specification, execution attempt, diagnosis/repair hypothesis, QA
   evaluation, and promotion/revocation schemas.
4. Replace remaining authority-bearing open payloads with typed schemas and
   semantic validators for DAG acyclicity, ownership, contact reciprocity,
   temporal ordering, certificate freshness, and scope containment.
5. Mark the legacy static orchestrator compiler non-authoritative and prevent
   App or production entrypoints from invoking it.
6. Implement the controller kernel, SQLite-equivalent event store, outbox,
   CAS, fake ComfyUI adapter, restart/cancellation/fault-injection tests, then a
   no-model real-runtime smoke when authorized.
7. Implement Character/Scene/Shot publishers, MaskFactory Mode A adapter,
   single- then two-character image slices, video/audio/AV clocks and repair,
   and finally the operator surfaces.
8. Only after the user reports all intended models downloaded: reconcile the
   frozen scope, enter staging, then advance through separately evidenced
   qualification, shadow, and production phases.

No runtime completion is inferred from this audit or its passing static tests.
"""


COMFYUI_RUNTIME_ARCHITECTURE = r"""
# Wave64 Durable ComfyUI Runtime and Phase-Safe Autonomy Architecture

Updated: 2026-07-16 America/Chicago

## Control boundary

The autonomous control plane owns durable intent, state, leases, idempotency,
evidence, QA, and promotion. Each ComfyUI server is a fenced worker with one
volatile local queue. API workflows are immutable releases compiled from a
canonical UI workflow and bound to an exact runtime lock.

```mermaid
flowchart LR
    U["App Mode launcher / controller console"] --> C["Durable controller"]
    C --> E["Event store + transactional outbox"]
    E --> L["Lease and fencing service"]
    L --> A["ComfyUI adapter"]
    A --> W1["Local ComfyUI worker"]
    A --> W2["EC2 ComfyUI worker"]
    W1 --> R["Receipt and reconciliation"]
    W2 --> R
    R --> S["Content-addressed artifact store"]
    S --> Q["Deterministic + calibrated critic QA"]
    Q --> P["Exactly-once promotion transaction"]
```

## Submission protocol

1. Resolve a certified exact `model_execution_bundle` and compatible
   `workflow_release_manifest` plus current `comfyui_runtime_lock`.
2. Acquire a `runtime_worker_lease` and fencing token.
3. Persist pass attempt, deterministic prompt UUID, unique idempotency key, API
   body hash, output namespace, and outbox row in one transaction.
4. Connect WebSocket before POST when supported, submit once, and record the
   HTTP receipt. Duplicate UUID behavior is never assumed to be exactly-once.
5. Treat WebSocket events and previews as advisory. On terminal event,
   disconnect, timeout, or restart, reconcile jobs/history/queue/files/CAS.
6. Hash and register every output through a safe relative artifact locator.
7. Commit QA and promotion as separate transactions; ambiguous attempts block
   failover and promotion.

## Workflow and runtime release

Legacy UI v0.4 workflows require deterministic migration to canonical v1,
semantic-equivalence evidence, recursive project-subgraph source hashes, a
flattened API graph hash, explicit input/output bindings, and removal of
top-level `_meta` before submission. Runtime locks bind ComfyUI core, frontend,
Python, Torch/CUDA, startup arguments, packages, each custom-node origin and
commit/dirty diff, import status, node signatures, `/object_info`, feature
probes, and folder-root identities.

## Recovery invariants

- ComfyUI queue/history never replaces the external event store.
- Leases require monotonically increasing fencing tokens.
- A stale worker cannot submit, register, QA, or promote.
- Submission and promotion are idempotent and separately unique.
- Absolute paths and traversal are forbidden at the worker boundary.
- Cross-host failover is allowed only after reconciliation proves the prior
  attempt was never submitted or is terminal and non-promotable.
- App Mode never becomes the hidden source of DAG or promotion state.
"""


def render_master_plan() -> str:
    """Append an authoritative, line-addressable catalog for every planned row."""
    lines = MASTER_PLAN.rstrip().splitlines()
    lines.extend(["", "## Authoritative Rows221-260 requirement catalog", ""])
    for row in ROWS:
        lines.extend([
            "### Row%03d - %s" % (row.number, row.title),
            "",
            "- Workstream: `%s`; phase: `%s`; domain: `%s`." % (
                row.workstream, row.phase, row.domain,
            ),
            "- Action: " + row.action,
            "- Acceptance: " + row.acceptance,
            "- Dependencies: " + (dependency_text(row) or "none"),
            "- Runtime truth: `%s`; activation gate required: `%s`." % (
                row_runtime_truth(row), str(row_requires_activation(row)).lower(),
            ),
            "",
        ])
    return "\n".join(lines) + "\n"


def authority_citation_lines(row: PlanRow) -> tuple[int, int]:
    heading = "### Row%03d - %s" % (row.number, row.title)
    lines = render_master_plan().splitlines()
    start = lines.index(heading) + 1
    return start, start + 6


def build_docs() -> dict[str, bytes]:
    return {
        "Plan/00_PROJECT_CONTROL/WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_AND_SELECTION_MASTER_PLAN.md": text_bytes(render_master_plan()),
        "Plan/01_CURRENT_SYSTEM_REVIEW/WAVE30_MODEL_OS_AUTONOMOUS_SELECTION_READINESS_AUDIT.md": text_bytes(READINESS_AUDIT),
        "Plan/01_CURRENT_SYSTEM_REVIEW/WAVE64_SECOND_PASS_AUTONOMOUS_WORKFLOW_AND_MODEL_INTELLIGENCE_ASSURANCE_AUDIT.md": text_bytes(SECOND_PASS_AUDIT),
        "Plan/02_TARGET_ARCHITECTURE/WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_CONTROL_PLANE_ARCHITECTURE.md": text_bytes(ARCHITECTURE),
        "Plan/02_TARGET_ARCHITECTURE/WAVE64_DURABLE_COMFYUI_RUNTIME_AND_PHASE_SAFE_AUTONOMY_ARCHITECTURE.md": text_bytes(COMFYUI_RUNTIME_ARCHITECTURE),
        "Plan/Instructions/AUTONOMOUS_MODEL_LIBRARY_INGESTION_QUALIFICATION_SELECTION_AND_LEARNING_PROTOCOL.md": text_bytes(IMPLEMENTATION_PROTOCOL),
        "Plan/Instructions/QA/AUTONOMOUS_MODEL_INTELLIGENCE_QA_AND_PROMOTION_PROTOCOL.md": text_bytes(QA_PROTOCOL),
        "Plan/Instructions/Hydration_Rehydration/AUTONOMOUS_MODEL_INTELLIGENCE_MAIN_SESSION_HANDOFF.md": text_bytes(HANDOFF),
    }


def provenance(*sources: str) -> dict[str, Any]:
    return {
        "producer": "wave64_autonomous_model_intelligence_package_builder",
        "source_refs": list(sources),
        "evidence_refs": [],
        "registry_snapshot_ids": [],
    }


def rr(record_type: str, record_id: str, revision: str = "1") -> dict[str, Any]:
    return {
        "record_type": record_type,
        "record_id": record_id,
        "revision": revision,
        "sha256": None,
        "path_or_uri": None,
    }


def phase_permissions_for(phase: str) -> dict[str, bool]:
    """Return the exact monotonic ceiling for one model-library phase."""
    permissions = {key: False for key in PHASE_PERMISSION_KEYS}
    if phase in {"staging", "qualification", "shadow_selection", "production_selection"}:
        permissions["source_staging_import"] = True
        permissions["operational_registry_mutation"] = True
    if phase in {"qualification", "shadow_selection", "production_selection"}:
        permissions["execution_bundle_compilation"] = True
        permissions["qualification_execution"] = True
        permissions["benchmark_execution"] = True
        permissions["profile_and_certificate_issuance"] = True
    if phase in {"shadow_selection", "production_selection"}:
        permissions["shadow_selection"] = True
        permissions["app_mode_runtime"] = True
        permissions["autonomous_role_shadow_eligibility"] = True
    if phase == "production_selection":
        permissions["production_selection"] = True
        permissions["autonomous_role_production_eligibility"] = True
    return permissions


def build_activation_gate_record() -> dict[str, Any]:
    """Materialize the current fail-closed model-library execution gate."""
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "model_library_activation_gate",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "revision": "1",
        "status": "deferred_prerequisites_not_satisfied",
        "created_at": UPDATED_AT,
        "main_task_id": MAIN_TASK_ID,
        "gate_state": "deferred_waiting_for_complete_model_download",
        "authorized_phase": "none",
        "activation_scope": {
            "source_snapshot_id": SOURCE_SNAPSHOT["source_snapshot_id"],
            "catalog_artifact_rows": SOURCE_SNAPSHOT["inventory"]["artifact_rows"],
            "scope_authority": "pending_main_task_download_completion_declaration",
            "all_intended_model_binaries_required": True,
            "scope_manifest_ref": None,
            "gate_applies_only_to_package_id": PACKAGE_ID,
            "does_not_block_independently_governed_lanes": True,
            "independently_governed_lane_ids": [
                "main_task_flux2_dev_proof_lane",
                "maskfactory_task_019f4cfc-60c3-7500-8626-261dcf70db5d",
            ],
        },
        "prerequisites": {
            "download_completion_declared": False,
            "download_completion_declaration_ref": None,
            "download_manifest_ref": None,
            "inventory_verification_ref": None,
            "expected_in_scope_assets": None,
            "verified_in_scope_assets": None,
            "missing_in_scope_assets": None,
            "hash_pending_assets": None,
            "quarantined_assets": None,
            "failed_assets": None,
            "unresolved_assets": None,
            "all_intended_assets_accounted_for": False,
            "main_task_acknowledgement_ref": None,
            "main_task_acknowledged": False,
            "all_prerequisites_satisfied": False,
        },
        "pre_activation_allowed_actions": [
            "preserve_and_review_planning_package",
            "validate_generated_schemas_registries_items_trackers_and_tests",
            "retain_existing_read_only_wave30_archive_integrity_audit",
            "observe_download_progress_read_only_when_explicitly_requested",
            "prepare_expected_download_scope_without_operational_ingestion",
            "communicate_deferred_gate_state_to_main_task",
        ],
        "blocked_actions": [
            "authoritative_wave30_staging_import",
            "operational_model_registry_mutation",
            "program_initiated_model_download_copy_or_install",
            "comfyui_loader_exposure_or_model_execution_for_this_program",
            "execution_bundle_solver_runtime_use",
            "model_qualification_sweep_benchmark_or_pilot",
            "model_performance_profile_or_certificate_generation",
            "autonomous_model_router_or_rag_activation",
            "model_intelligence_app_mode_runtime_activation",
            "production_selection_promotion_or_release",
        ],
        "phase_permissions": phase_permissions_for("none"),
        "fail_closed_reason_codes": [
            "DEFERRED_WAITING_EXPECTED_DOWNLOAD_SCOPE",
            "DEFERRED_WAITING_COMPLETE_MODEL_DOWNLOAD",
            "DEFERRED_WAITING_INVENTORY_VERIFICATION",
            "DEFERRED_WAITING_MAIN_TASK_ACKNOWLEDGEMENT",
            "DEFERRED_PREREQUISITE_EVIDENCE_CONFLICT",
        ],
        "activation_authority": (
            "deterministic_inventory_verifier_plus_main_task_"
            "acknowledgement_after_user_download_complete_signal"
        ),
        "activation_decision_ref": None,
        "runtime_execution_allowed": False,
        "last_evaluated_at": UPDATED_AT,
        "provenance": provenance(
            "user_deferred_until_all_models_downloaded",
            "wave30_source_snapshot_metadata_only_model_binary_count_zero",
            "main_task_" + MAIN_TASK_ID,
        ),
    }


def validate_activation_gate_semantics(record: dict[str, Any]) -> list[str]:
    """Validate cross-field gate invariants that JSON Schema cannot compare."""
    errors: list[str] = []
    gate_state = record.get("gate_state")
    is_active = gate_state in ACTIVE_GATE_STATE_TO_PHASE
    expected_phase = ACTIVE_GATE_STATE_TO_PHASE.get(gate_state, "none")
    if record.get("main_task_id") != MAIN_TASK_ID:
        errors.append("activation gate main_task_id mismatch")
    if bool(record.get("runtime_execution_allowed")) != is_active:
        errors.append("runtime execution permission must match the active gate state")
    if record.get("authorized_phase") != expected_phase:
        errors.append("authorized_phase must exactly match gate_state")
    if record.get("phase_permissions") != phase_permissions_for(expected_phase):
        errors.append("phase permissions exceed or differ from the authorized phase ceiling")
    prerequisites = record.get("prerequisites", {})
    scope = record.get("activation_scope", {})
    if is_active:
        if scope.get("scope_authority") != "main_task_declared_complete_scope":
            errors.append("active gate requires main-task-declared scope authority")
        if scope.get("scope_manifest_ref") is None:
            errors.append("active gate requires expected-download scope manifest")
        for field in (
            "download_completion_declaration_ref",
            "download_manifest_ref",
            "inventory_verification_ref",
            "main_task_acknowledgement_ref",
        ):
            if prerequisites.get(field) is None:
                errors.append("active gate requires " + field)
        expected = prerequisites.get("expected_in_scope_assets")
        verified = prerequisites.get("verified_in_scope_assets")
        if not isinstance(expected, int) or expected < 1:
            errors.append("active gate requires positive expected asset count")
        quarantined = prerequisites.get("quarantined_assets")
        failed = prerequisites.get("failed_assets")
        if not isinstance(verified, int) or verified < 1:
            errors.append("active gate requires at least one verified asset")
        if not isinstance(quarantined, int) or quarantined < 0:
            errors.append("active gate requires a nonnegative quarantined count")
        if not isinstance(failed, int) or failed < 0:
            errors.append("active gate requires a nonnegative failed count")
        if all(isinstance(value, int) for value in (verified, quarantined, failed, expected)):
            if verified + quarantined + failed != expected:
                errors.append("verified plus quarantined plus failed must equal expected")
        for field in (
            "missing_in_scope_assets",
            "hash_pending_assets",
            "unresolved_assets",
        ):
            if prerequisites.get(field) != 0:
                errors.append("active gate requires zero " + field)
        for field in (
            "download_completion_declared",
            "all_intended_assets_accounted_for",
            "main_task_acknowledged",
            "all_prerequisites_satisfied",
        ):
            if prerequisites.get(field) is not True:
                errors.append("active gate requires " + field)
        if record.get("activation_decision_ref") is None:
            errors.append("active gate requires activation decision")
        if expected_phase == "staging" and any(
            record["phase_permissions"][key]
            for key in (
                "qualification_execution", "benchmark_execution",
                "profile_and_certificate_issuance", "shadow_selection",
                "production_selection", "autonomous_role_shadow_eligibility",
                "autonomous_role_production_eligibility",
            )
        ):
            errors.append("staging phase cannot authorize qualification or selection")
    return errors


def validate_phase_transition_semantics(record: dict[str, Any]) -> list[str]:
    """Validate that phase decisions never silently skip the ordered phase ladder."""
    errors: list[str] = []
    phases = list(ACTIVATION_PHASES)
    from_phase = record.get("from_phase")
    to_phase = record.get("to_phase")
    decision = record.get("decision")
    if from_phase not in phases or to_phase not in phases:
        return ["unknown activation phase"]
    delta = phases.index(to_phase) - phases.index(from_phase)
    if decision == "authorized" and delta != 1:
        errors.append("authorized transition must advance exactly one phase")
    if decision == "denied" and delta != 0:
        errors.append("denied transition must retain the current phase")
    if decision == "suspended" and to_phase != "none":
        errors.append("suspension must remove operational phase authority")
    if record.get("implicit_phase_cascade") is not False:
        errors.append("implicit phase cascade is forbidden")
    if record.get("other_runtime_lanes_affected") is not False:
        errors.append("model-library transition cannot affect independent lanes")
    return errors


def validate_inventory_report_semantics(record: dict[str, Any]) -> list[str]:
    """Reconcile inventory arithmetic and keep quarantined assets ineligible."""
    errors: list[str] = []
    expected = record.get("expected_binary_count")
    accounted = record.get("accounted_binary_count")
    verified = record.get("hash_verified_binary_count")
    quarantined = record.get("quarantined_binary_count")
    failed = record.get("failed_binary_count")
    if all(isinstance(value, int) for value in (expected, accounted, verified, quarantined, failed)):
        if accounted != expected:
            errors.append("accounted binary count must equal expected binary count")
        if verified + quarantined + failed != accounted:
            errors.append("verified plus quarantined plus failed must equal accounted")
    if record.get("missing_binary_count") != 0:
        errors.append("missing binary count must be zero")
    if record.get("hash_pending_binary_count") != 0:
        errors.append("hash-pending binary count must be zero")
    if record.get("unresolved_binary_count") != 0:
        errors.append("unresolved binary count must be zero")
    if record.get("quarantined_and_failed_excluded_from_runtime") is not True:
        errors.append("quarantined and failed binaries must be excluded from runtime")
    return errors


def validate_selection_decision_semantics(record: dict[str, Any]) -> list[str]:
    """Resolve selected IDs against eligible, certified, Pareto candidates."""
    errors: list[str] = []
    candidates = record.get("evaluated_candidates", [])
    by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        candidate_id = candidate.get("execution_bundle_id")
        if candidate_id in by_id:
            errors.append("duplicate evaluated execution bundle id")
        elif isinstance(candidate_id, str):
            by_id[candidate_id] = candidate
    frontier = set(record.get("pareto_frontier_bundle_ids", []))
    if not frontier.issubset(by_id):
        errors.append("Pareto frontier contains unevaluated bundle")
    if any(not by_id[bundle_id].get("eligible") for bundle_id in frontier if bundle_id in by_id):
        errors.append("Pareto frontier contains ineligible bundle")
    selected_id = record.get("selected_bundle_id")
    selected_ref = record.get("selected_execution_bundle_ref")
    if record.get("decision") == "selected":
        candidate = by_id.get(selected_id)
        if candidate is None:
            errors.append("selected bundle was not evaluated")
        else:
            if candidate.get("eligible") is not True:
                errors.append("selected bundle is not eligible")
            if not candidate.get("certificate_ids"):
                errors.append("selected bundle lacks a scoped certificate")
            if any(candidate.get(field) is None for field in ("quality_lcb", "risk_ucb", "utility")):
                errors.append("selected bundle lacks complete ranking evidence")
        if selected_id not in frontier:
            errors.append("selected bundle is not on the Pareto frontier")
        if not isinstance(selected_ref, dict) or selected_ref.get("record_id") != selected_id:
            errors.append("selected bundle reference does not match selected_bundle_id")
        elif selected_ref.get("sha256") is None:
            errors.append("selected bundle reference must be hash-bound")
    elif selected_id is not None or selected_ref is not None:
        errors.append("non-selected decision cannot bind a selected bundle")
    return errors


def build_registries(schemas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    schema_catalog = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_model_intelligence_schema_catalog_v1",
        "updated_at": UPDATED_AT,
        "status": "planning_complete_runtime_deferred_by_activation_gate",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "schemas": [
            {
                "file": "Plan/08_SCHEMAS/" + name,
                "schema_id": schema["$id"],
                "record_type": (
                    schema.get("properties", {})
                    .get("record_type", {})
                    .get("const", "common_definitions")
                ),
            }
            for name, schema in schemas.items()
        ],
    }
    lifecycle = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_model_lifecycle_and_authority_v1",
        "updated_at": UPDATED_AT,
        "status": "planned_runtime_deferred_by_model_library_activation_gate",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "activation_gate_state": "deferred_waiting_for_complete_model_download",
        "runtime_work_authorized": False,
        "content_based_suppression": False,
        "authority_planes": [
            {
                "plane": "discovery",
                "facts": ["source claims", "taxonomy", "tags", "triggers", "selector priors"],
                "maximum_action": "candidate_retrieval_and_qualification_priority",
            },
            {
                "plane": "operational",
                "facts": ["hash", "binary inspection", "installation", "loader", "runtime", "bundle"],
                "maximum_action": "qualification_execution_only_after_activation_gate_pass",
            },
            {
                "plane": "empirical",
                "facts": ["benchmarks", "observations", "profiles", "certificates", "drift"],
                "maximum_action": "scope_bounded_production_selection_when_certified",
            },
        ],
        "lifecycle_axes": {
            "identity": ["discovered", "canonicalized", "hash_verified", "duplicate_alias"],
            "binary_integrity": ["unscanned", "passed", "quarantined", "failed"],
            "classification": ["unclassified", "proposed", "reviewed", "frozen"],
            "availability": ["remote_only", "cache_pending", "installed_quarantine", "installed_verified", "missing"],
            "runtime": ["untested", "static_passed", "load_smoke_passed", "functional_smoke_passed", "failed", "suspended"],
            "capability_authority": [
                "research_candidate", "benchmark_candidate", "provisional",
                "shadow_challenger", "production_eligible", "suspended",
                "revoked", "superseded",
            ],
            "evidence": ["current", "stale", "contradicted", "revoked"],
        },
        "transition_authorities": {
            "source_admission": "deterministic_intake_policy",
            "installation": "asset_admission_service",
            "runtime_state": "runtime_evidence_policy",
            "certificate": "certificate_policy_service",
            "suspension_revocation": "deterministic_policy_or_release_authority",
            "artifact_promotion": "existing_multimodal_promotion_policy",
        },
        "llm_vlm_authority": {
            "may_propose": True,
            "may_observe": True,
            "may_certify": False,
            "may_promote": False,
            "may_mutate_registry": False,
            "may_use_arbitrary_tools": False,
        },
    }
    ranking = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_model_selection_feature_and_ranking_policy_v1",
        "updated_at": UPDATED_AT,
        "status": "planned_unimplemented_deferred_until_model_library_activation",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "runtime_ranking_authorized": False,
        "source_metadata_role": "discovery_and_qualification_priority_only",
        "hard_filter_order": [
            "lifecycle_and_binary_integrity",
            "installation_and_loader_availability",
            "engine_architecture_and_component_compatibility",
            "pass_intent_target_control_and_mask_support",
            "character_instance_and_protected_scope",
            "current_capability_certificate_scope",
            "runtime_resource_cost_and_health",
            "evidence_freshness_and_prohibited_bundle_rules",
        ],
        "ranking_features": [
            {"feature": "target_effect_quality_lcb", "direction": "higher"},
            {"feature": "identity_morphology_preservation_lcb", "direction": "higher"},
            {"feature": "pose_ownership_preservation_lcb", "direction": "higher"},
            {"feature": "regional_and_mask_quality_lcb", "direction": "higher"},
            {"feature": "temporal_or_audio_quality_lcb", "direction": "higher"},
            {"feature": "serious_failure_rate_ucb", "direction": "lower"},
            {"feature": "protected_drift_ucb", "direction": "lower"},
            {"feature": "oom_crash_instability_ucb", "direction": "lower"},
            {"feature": "latency_memory_storage_transfer_cost", "direction": "lower"},
            {"feature": "bridge_scope_distance_staleness_penalty", "direction": "lower"},
            {"feature": "cache_and_batching_affinity", "direction": "higher"},
        ],
        "formula": {
            "quality": "weighted_lower_confidence_bound_of_applicable_benefit_and_preservation_metrics",
            "risk": "weighted_upper_confidence_bound_of_serious_failure_and_regression_metrics",
            "utility": "quality_minus_risk_minus_resource_bridge_staleness_and_scope_distance_plus_cache_affinity",
            "composite_applied_after": "pareto_frontier",
        },
        "numeric_policy": {
            "policy_revision": "wave64_contextual_ranker_numeric_v1",
            "authority": "frozen_initial_policy_requires_versioned_recalibration_evidence",
            "feature_normalization": {
                "range": [0.0, 1.0],
                "direction_normalized_to": "higher_is_better",
                "method": "certificate_bucket_empirical_cdf_with_frozen_bounds",
                "out_of_range_policy": "clip_and_record_drift_event",
            },
            "quality_feature_weights": {
                "target_effect_quality_lcb": 0.35,
                "identity_morphology_preservation_lcb": 0.25,
                "pose_ownership_preservation_lcb": 0.15,
                "regional_and_mask_quality_lcb": 0.15,
                "temporal_or_audio_quality_lcb": 0.10,
            },
            "risk_feature_weights": {
                "serious_failure_rate_ucb": 0.55,
                "protected_drift_ucb": 0.30,
                "oom_crash_instability_ucb": 0.15,
            },
            "penalty_feature_weights": {
                "latency_memory_storage_transfer_cost": 0.50,
                "bridge_scope_distance_staleness_penalty": 0.50,
            },
            "utility_component_weights": {
                "quality": 0.65,
                "risk_penalty": 0.25,
                "resource_bridge_penalty": 0.10,
                "cache_affinity_bonus_cap": 0.02,
            },
            "pass_class_applicability": {
                "base_image": [
                    "target_effect_quality_lcb", "identity_morphology_preservation_lcb",
                    "pose_ownership_preservation_lcb", "regional_and_mask_quality_lcb",
                ],
                "regional_detail": [
                    "target_effect_quality_lcb", "identity_morphology_preservation_lcb",
                    "pose_ownership_preservation_lcb", "regional_and_mask_quality_lcb",
                ],
                "video": [
                    "target_effect_quality_lcb", "identity_morphology_preservation_lcb",
                    "pose_ownership_preservation_lcb", "temporal_or_audio_quality_lcb",
                ],
                "audio": ["target_effect_quality_lcb", "temporal_or_audio_quality_lcb"],
                "av": [
                    "target_effect_quality_lcb", "identity_morphology_preservation_lcb",
                    "temporal_or_audio_quality_lcb",
                ],
            },
            "missing_data_rules": {
                "mandatory_feature": "candidate_ineligible",
                "optional_nonapplicable_feature": "omit_and_renormalize_with_recorded_denominator",
                "metadata_prior": "qualification_priority_only_never_imputed_as_production_metric",
                "stale_certificate": "candidate_ineligible",
                "critic_only_unvalidated_metric": "exclude_from_hard_gate_and_rank",
            },
            "confidence_methods": {
                "continuous_quality_lcb": "one_sided_95_percent_stratified_bootstrap",
                "binary_failure_ucb": "one_sided_95_percent_wilson",
                "sparse_bucket_policy": "fall_back_to_parent_bucket_for_priority_only_and_abstain_in_production",
            },
            "production_thresholds": {
                "quality_lcb_minimum": 0.80,
                "serious_failure_rate_ucb_maximum": 0.10,
                "character_identity_preservation_lcb_minimum": 0.92,
                "protected_drift_ucb_maximum": 0.05,
                "selection_uncertainty_maximum": 0.20,
                "certificate_freshness_required": True,
            },
            "branch_and_abstention": {
                "near_tie_utility_margin": 0.02,
                "maximum_bounded_candidate_branches": 2,
                "branching_allowed_modes": ["qualification_exploration", "shadow_challenger"],
                "production_near_tie_policy": "select_certified_champion_or_abstain_by_policy",
                "no_eligible_candidate_policy": "abstain_or_explicit_certified_fallback",
            },
            "selection_bias_controls": {
                "record_propensity_or_assignment_probability": True,
                "shadow_assignment_record_required": True,
                "holdout_partition_id_required": True,
                "production_observation_may_directly_rewrite_ranker": False,
            },
        },
        "cold_start": {
            "metadata_priors_production_quality_authority": False,
            "allowed_modes": ["qualification_exploration", "shadow_challenger"],
            "production_required_pass": "certified_champion_or_explicit_fallback_or_abstain",
        },
        "exploration": {
            "methods_allowed": ["expected_information_value", "contextual_thompson_sampling", "uncertainty_ucb"],
            "authority": "shadow_or_qualification_only",
            "accepted_parent_mutation": False,
            "single_success_promotion": False,
        },
        "tie_break_order": [
            "stronger_scope_match",
            "stronger_lower_confidence_quality",
            "lower_upper_confidence_serious_risk",
            "larger_current_sample",
            "fresher_evidence",
            "lower_bridge_and_resource_cost",
            "stable_bundle_id",
        ],
        "replay_requirements": [
            "selection_context_hash",
            "registry_snapshot_ids",
            "certificate_snapshot_ids",
            "feature_snapshot_hash",
            "ranking_policy_id",
            "normalization_and_weight_policy_id",
        ],
    }
    qa = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_model_qualification_and_qa_v1",
        "updated_at": UPDATED_AT,
        "status": "planned_unimplemented_deferred_until_model_library_activation",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "pre_l0_activation_gate": {
            "required": True,
            "current_state": "deferred_waiting_for_complete_model_download",
            "qualification_execution_allowed": False,
            "catalog_dry_run_ingestion_allowed": False,
            "required_evidence": [
                "expected_download_scope_manifest",
                "model_download_completion_manifest",
                "model_binary_inventory_verification_report",
                "main_task_activation_acknowledgement",
            ],
        },
        "qualification_stages": [
            {"stage": "L0", "name": "catalog_qa", "authority_gained": "discovery_only"},
            {"stage": "L1", "name": "binary_qa", "authority_gained": "integrity_only"},
            {"stage": "L2", "name": "load_smoke", "authority_gained": "runtime_load_evidence"},
            {"stage": "L3", "name": "functional_ab", "authority_gained": "functional_candidate"},
            {"stage": "L4", "name": "bucket_benchmark", "authority_gained": "certificate_candidate"},
            {"stage": "L5", "name": "bundle_interaction", "authority_gained": "bundle_certificate_candidate"},
            {"stage": "L6", "name": "cross_engine_bridge", "authority_gained": "pair_certificate_candidate"},
            {"stage": "L7", "name": "shadow_routing", "authority_gained": "shadow_evidence"},
            {"stage": "L8", "name": "production_eligibility", "authority_gained": "bucket_only_authority"},
        ],
        "gate_ids": [
            "MI-QA-01_SOURCE_ARCHIVE",
            "MI-QA-02_IDENTITY_BINARY",
            "MI-QA-03_COMPATIBILITY",
            "MI-QA-04_RUNTIME_RESOURCE",
            "MI-QA-05_TARGET_EFFECT",
            "MI-QA-06_PROTECTED_PRESERVATION",
            "MI-QA-07_REGIONAL_MASK",
            "MI-QA-08_TEMPORAL_AUDIO",
            "MI-QA-09_ATTRIBUTION",
            "MI-QA-10_EVIDENCE_STATISTICS",
            "MI-QA-11_SELECTION_REPLAY",
            "MI-QA-12_AUTONOMOUS_ROLE",
            "MI-QA-13_LIFECYCLE_CERTIFICATE",
            "MI-QA-14_RECOVERY_SECURITY",
        ],
        "initial_sample_floors": {
            "load_smoke": {"bounded_outputs": 1, "clean_reloads": 1},
            "functional_candidate": {"matched_seeds": 3, "initial_strength_points": 4},
            "provisional_bucket": {"paired_outputs": 20, "distinct_cases": 5},
            "production_certificate": {"paired_outputs": 50, "distinct_cases": 10},
            "bridge_certificate": {"paired_outputs": 10, "target_classes": 3},
            "shadow_challenger": {"shadow_comparisons": 10},
        },
        "evidence_authority_order": [
            "source_claim", "discovery_metadata", "static_measurement",
            "runtime_observation", "qualification_measurement",
            "adjudicated_review", "scoped_certificate",
        ],
        "promotion_prohibitions": [
            "metadata_only",
            "one_attractive_sample",
            "load_smoke_only",
            "family_summary_transferred_to_artifact",
            "certificate_transferred_to_other_hash_or_bundle",
            "uncalibrated_critic_only",
            "self_promotion_by_generator_or_reviewer",
        ],
    }
    roles = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_autonomous_model_role_registry_v1",
        "updated_at": UPDATED_AT,
        "status": "roles_defined_stacks_unselected_unqualified_and_activation_deferred",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "runtime_role_activation_allowed": False,
        "roles": [
            {"role": "planner", "outputs": ["planner_proposal"], "may_execute": False, "may_promote": False},
            {"role": "prompt_composer", "outputs": ["prompt_package"], "may_execute": False, "may_promote": False},
            {"role": "retrieval_analyst", "outputs": ["retrieval_evidence_bundle"], "may_execute": False, "may_promote": False},
            {"role": "router_advisor", "outputs": ["candidate_explanation"], "may_execute": False, "may_promote": False},
            {"role": "defect_classifier", "outputs": ["defect_observation", "repair_hypothesis"], "may_execute": False, "may_promote": False},
            {"role": "vlm_critic", "outputs": ["reviewer_observation"], "may_execute": False, "may_promote": False},
            {"role": "audio_critic", "outputs": ["reviewer_observation"], "may_execute": False, "may_promote": False},
            {"role": "report_writer", "outputs": ["cited_generated_summary"], "may_execute": False, "may_promote": False},
            {"role": "summarizer", "outputs": ["context_compaction_summary"], "may_execute": False, "may_promote": False},
            {"role": "drift_triage", "outputs": ["drift_scope_proposal"], "may_execute": False, "may_promote": False},
        ],
        "exact_stack_fields": [
            "model_id", "model_revision", "model_sha256", "runtime",
            "runtime_revision", "quantization", "chat_template_id",
            "structured_output_parser_id", "context_limit",
            "batching_policy", "hardware_envelope_id",
            "role_qualification_certificate_ids",
        ],
        "qualification_floors": {
            "planner_held_out_requests": 100,
            "reviewer_adjudicated_panels": 200,
            "tool_gateway_adversarial_cases": 100,
            "complete_shadow_jobs": 30,
        },
    }
    role_activation = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_autonomous_role_activation_projection_v1",
        "updated_at": UPDATED_AT,
        "status": "all_roles_inactive_stacks_unselected_and_unqualified",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "authorized_model_library_phase": "none",
        "production_role_count": 0,
        "shadow_role_count": 0,
        "role_projections": [
            {
                "role_id": "role_" + role["role"] + "_v1",
                "role": role["role"],
                "selected_stack_id": None,
                "qualification_certificate_ids": [],
                "activation_decision_id": None,
                "activation_state": "inactive_unselected",
                "allowed_operating_modes": [],
                "direct_execution_authority": False,
                "registry_mutation_authority": False,
                "certificate_authority": False,
                "artifact_promotion_authority": False,
            }
            for role in roles["roles"]
        ],
        "activation_rule": (
            "A model-library phase ceiling, exact-stack role certificate, shadow "
            "evidence, tool policy, and autonomous_role_activation_decision are all "
            "required; none is inferred from a role card or model download."
        ),
    }
    runtime_adapter = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_comfyui_runtime_adapter_policy_v1",
        "updated_at": UPDATED_AT,
        "status": "contract_frozen_implementation_not_started",
        "runtime_completion_claimed": False,
        "durable_authority": "external_event_store_outbox_and_content_addressed_artifact_store",
        "comfyui_queue_history_authority": "volatile_observation_only",
        "websocket_authority": "advisory_live_observation_then_history_or_jobs_reconciliation",
        "submission_policy": {
            "connect_websocket_before_post": True,
            "client_supplied_prompt_uuid": True,
            "database_unique_idempotency_key": True,
            "transactional_outbox_required": True,
            "runtime_lease_fencing_required": True,
            "duplicate_prompt_id_assumed_rejected_by_comfyui": False,
            "ambiguous_cross_host_failover_allowed": False,
        },
        "feature_probe_order": [
            "/object_info", "/system_stats", "/prompt", "/ws",
            "/api/jobs/{id}", "/history/{id}", "/queue", "/interrupt",
        ],
        "cancel_policy": [
            "prefer_idempotent_targeted_job_cancel_when_feature_probe_passes",
            "fallback_to_queue_delete_only_for_known_pending_prompt",
            "global_interrupt_requires_single_owned_running_prompt_and_policy_authority",
        ],
        "required_contract_record_types": [
            "comfyui_runtime_lock", "workflow_release_manifest",
            "comfyui_submission_envelope", "comfyui_execution_receipt",
            "comfyui_artifact_locator", "runtime_reconciliation_report",
            "runtime_worker_lease", "orchestrator_event_payload_envelope",
            "orchestrator_state_transition_definition",
        ],
        "official_sources": [
            "https://docs.comfy.org/development/comfyui-server/comms_routes",
            "https://docs.comfy.org/development/comfyui-server/comms_messages",
            "https://github.com/comfyanonymous/ComfyUI/blob/master/script_examples/websockets_api_example.py",
            "https://docs.comfy.org/specs/workflow_json",
            "https://docs.comfy.org/interface/app-mode",
            "https://docs.comfy.org/interface/features/subgraph",
        ],
        "app_boundary": {
            "app_mode_role": "thin_workflow_launcher_and_result_surface",
            "controller_console_role": "separate_durable_multimodule_dag_qa_recovery_surface",
        },
    }
    state_machine = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_autonomous_aggregate_state_transition_registry_v1",
        "updated_at": UPDATED_AT,
        "status": "canonical_transition_baseline_frozen_runtime_enforcement_not_started",
        "event_payloads_must_validate": True,
        "optimistic_aggregate_version_required": True,
        "append_only_hash_chain_required": True,
        "aggregate_states": {
            "job": ["requested", "planned", "running", "blocked", "completed", "cancelled"],
            "dag": ["compiled", "running", "blocked", "completed", "cancelled"],
            "pass": ["specified", "routed", "ready", "running", "qa_pending", "accepted", "repair", "blocked", "cancelled"],
            "attempt": ["created", "outbox_pending", "submitted", "running", "terminal", "ambiguous", "reconciled"],
            "artifact": ["registered", "verified", "qa_pending", "accepted_parent", "rejected", "revoked"],
            "qa": ["requested", "evaluating", "pass", "fail", "blocked", "superseded"],
            "promotion": ["requested", "validated", "committed", "rejected", "revoked"],
            "lease": ["offered", "active", "expired", "fenced", "released"],
            "model_lifecycle": ["discovered", "staged", "verified", "qualified", "shadow", "production", "suspended", "revoked"],
            "role_activation": ["inactive", "qualified_inactive", "shadow_active", "production_active", "suspended", "revoked"],
        },
        "never_waivable_rules": [
            "planned_or_unqualified_execution_bundle_cannot_be_selected",
            "stale_or_revoked_certificate_cannot_authorize_execution",
            "attempt_requires_current_fencing_token",
            "ambiguous_submission_cannot_fail_over_or_promote",
            "qa_failure_cannot_transition_to_promoted",
            "promotion_transaction_is_exactly_once",
            "llm_vlm_cannot_certify_or_promote",
            "mode_b_mask_cannot_satisfy_promotion_gate",
        ],
    }
    assurance = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_second_pass_autonomy_assurance_gap_registry_v1",
        "updated_at": UPDATED_AT,
        "status": "planning_contract_hardening_applied_runtime_gaps_explicit",
        "findings": [
            {"id": "W64-SP-001", "severity": "P0", "topic": "phase_safe_activation", "planning_disposition": "closed_by_split_phase_gate", "runtime_disposition": "deferred"},
            {"id": "W64-SP-002", "severity": "P0", "topic": "typed_activation_prerequisites", "planning_disposition": "closed_by_four_strict_records_and_transition_decision", "runtime_disposition": "deferred"},
            {"id": "W64-SP-003", "severity": "P0", "topic": "selection_certificate_policy_tool_semantics", "planning_disposition": "schema_and_semantic_validation_hardened", "runtime_disposition": "deferred"},
            {"id": "W64-SP-004", "severity": "P0", "topic": "maskfactory_ownership_authority", "planning_disposition": "selection_and_bundle_contracts_hardened", "runtime_disposition": "depends_on_current_maskfactory_release_snapshot"},
            {"id": "W64-SP-005", "severity": "P0", "topic": "comfyui_durable_runtime_boundary", "planning_disposition": "nine_runtime_contracts_and_policy_added", "runtime_disposition": "not_implemented"},
            {"id": "W64-SP-006", "severity": "P0", "topic": "autonomous_role_activation", "planning_disposition": "explicit_inactive_projection_and_decision_contract_added", "runtime_disposition": "no_stack_selected_or_qualified"},
            {"id": "W64-SP-007", "severity": "P1", "topic": "release_dependency_completeness", "planning_disposition": "row260_depends_on_row255", "runtime_disposition": "deferred"},
            {"id": "W64-SP-008", "severity": "P1", "topic": "independent_lane_scope", "planning_disposition": "gate_scope_isolated_from_flux2_and_maskfactory_lanes", "runtime_disposition": "enforced_by_future_controller"},
            {"id": "W64-SP-009", "severity": "P1", "topic": "canonical_reference_and_overlapping_contract_migration", "planning_disposition": "canonical_immutable_ref_and_crosswalk_added_planned_stack_self_eligibility_blocked_remaining_legacy_migration_named", "runtime_disposition": "not_started"},
            {"id": "W64-SP-010", "severity": "P1", "topic": "split_pass_attempt_qa_promotion_records", "planning_disposition": "canonical_split_record_set_added_legacy_combined_contract_deprecated_for_future_runtime", "runtime_disposition": "not_started"},
        ],
        "truthful_readiness": {
            "architecture_baseline": "complete",
            "contract_hardening": "substantial_second_pass_complete_with_named_open_core_migrations",
            "production_controller": "not_built",
            "model_library": "download_incomplete_and_execution_deferred",
            "autonomous_roles": "unselected_unqualified_inactive",
            "end_to_end_runtime_certification": "not_started",
        },
    }
    canonical_contracts = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_canonical_contract_and_deprecation_crosswalk_v1",
        "updated_at": UPDATED_AT,
        "status": "canonical_reference_frozen_remaining_record_migrations_planned",
        "canonical_immutable_reference": {
            "schema_id": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef",
            "required_fields": [
                "schema_id", "record_type", "record_id", "revision",
                "sha256", "bytes", "path_or_uri",
            ],
            "authority_use": "required_for_execution_certificate_qa_and_promotion",
        },
        "legacy_reference_crosswalk": [
            {
                "source": COMMON_SCHEMA_ID + "#/$defs/RecordRef",
                "disposition": "retained_for_discovery_and_unresolved_planning_refs_only",
                "authority_ceiling": "discovery_or_candidate",
                "migration_target": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef",
            },
            {
                "source": "https://comfy-ui-main.local/schemas/multimodal-contract-common/1.0.0#/$defs/RecordRef",
                "disposition": "field_compatible_canonical_alias_pending_schema_id_unification",
                "authority_ceiling": "immutable_when_fully_populated",
                "migration_target": COMMON_SCHEMA_ID + "#/$defs/ImmutableRecordRef",
            },
        ],
        "selectable_unit": {
            "canonical_record_type": "model_execution_bundle",
            "deprecated_overlaps": ["engine_execution_stack_card_as_direct_selection_unit"],
            "rule": "engine stack cards describe capabilities; only an exact hash-bound model_execution_bundle is selectable",
        },
        "decision_crosswalk": {
            "contextual_model_selection_decision": "canonical exact-bundle eligibility and ranking decision",
            "multimodal_pass_route_decision": "orchestration route that must reference the canonical contextual selection decision",
            "self_declared_eligible_flag_is_authority": False,
        },
        "remaining_migrations": [
            "update_rows149_220_route_schema_to_require_contextual_selection_decision_ref",
            "replace_selected_stack_template_with_selected_model_execution_bundle_ref",
            "separate_pass_attempt_qa_and_promotion_records",
            "migrate_all_authority_bearing_open_payloads_to_typed_refs",
        ],
    }
    runtime_entrypoints = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_autonomous_runtime_entrypoint_registry_v1",
        "updated_at": UPDATED_AT,
        "status": "production_entrypoint_not_implemented_legacy_scaffold_blocked",
        "entrypoints": [
            {
                "entrypoint_id": "legacy_wave14_orchestrator_plan_compiler",
                "path": "Plan/07_IMPLEMENTATION/scripts/compile_orchestrator_run_plan.py",
                "authority": "legacy_planning_scaffold_non_authoritative",
                "allowed_modes": ["dry_run_plan_only", "legacy_planning_scaffold"],
                "production_invocation_allowed": False,
                "app_mode_invocation_allowed": False,
                "known_limitations": [
                    "static_pass_list", "hardcoded_sdxl_specialists",
                    "no_durable_event_store", "no_outbox_or_fencing",
                    "no_exact_bundle_certificate_resolution",
                ],
            },
            {
                "entrypoint_id": "wave64_durable_autonomous_controller",
                "path": None,
                "authority": "planned_unimplemented",
                "allowed_modes": [],
                "production_invocation_allowed": False,
                "app_mode_invocation_allowed": False,
                "required_before_registration": [
                    "event_store", "transactional_outbox", "cas",
                    "runtime_lease_fencing", "comfyui_adapter",
                    "reconciliation", "typed_qa", "exactly_once_promotion",
                ],
            },
        ],
    }
    tool_allowlist = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_autonomous_tool_action_allowlist_v1",
        "updated_at": UPDATED_AT,
        "status": "frozen_planning_allowlist_runtime_gateway_not_implemented",
        "default_decision": "deny",
        "actions": [
            {"action": "retrieve_registry_records", "effect": "read_only", "allowed_roles": ["planner", "prompt_composer", "retrieval_analyst", "router_advisor", "defect_classifier", "vlm_critic", "audio_critic", "report_writer", "summarizer", "drift_triage"]},
            {"action": "read_artifact_metadata", "effect": "read_only", "allowed_roles": ["planner", "defect_classifier", "vlm_critic", "audio_critic", "report_writer"]},
            {"action": "submit_structured_proposal", "effect": "proposal_only", "allowed_roles": ["planner", "prompt_composer", "router_advisor", "defect_classifier", "drift_triage"]},
            {"action": "emit_reviewer_observation", "effect": "candidate_evidence_only", "allowed_roles": ["vlm_critic", "audio_critic"]},
            {"action": "emit_cited_summary", "effect": "navigation_only", "allowed_roles": ["report_writer", "summarizer"]},
        ],
        "universally_forbidden": [
            "arbitrary_filesystem_path", "credential_read", "shell_execution",
            "network_target_not_allowlisted", "registry_mutation",
            "certificate_issue", "artifact_promotion", "policy_weight_mutation",
            "hard_compatibility_override", "model_library_phase_activation",
        ],
        "request_authorization_receipt_split_required": True,
        "argument_and_result_schema_hash_required": True,
    }
    operator_binding = {
        "schema_version": SCHEMA_VERSION,
        "registry_id": "wave64_operator_surface_to_controller_binding_v1",
        "updated_at": UPDATED_AT,
        "status": "planned_no_production_surface_implemented",
        "app_mode_boundary": "thin_workflow_launcher_and_result_surface",
        "controller_console_boundary": "durable_jobs_dag_queue_qa_repair_lineage_models_and_recovery",
        "bindings": [
            {"surface": "app_mode", "control": "workflow_inputs", "command": "create_job", "direct_comfyui_mutation": False},
            {"surface": "app_mode", "control": "run", "command": "create_job", "direct_comfyui_mutation": False},
            {"surface": "controller_console", "control": "cancel_attempt", "command": "cancel_attempt", "direct_comfyui_mutation": False},
            {"surface": "controller_console", "control": "request_repair", "command": "request_repair", "direct_comfyui_mutation": False},
            {"surface": "controller_console", "control": "suspend_bundle", "command": "suspend_bundle", "direct_comfyui_mutation": False},
            {"surface": "controller_console", "control": "revoke_certificate", "command": "revoke_certificate", "direct_comfyui_mutation": False},
            {"surface": "controller_console", "control": "acknowledge_staging", "command": "acknowledge_model_library_staging", "direct_comfyui_mutation": False},
            {"surface": "controller_console", "control": "request_phase_transition", "command": "request_phase_transition", "direct_comfyui_mutation": False},
        ],
        "hidden_fields": ["raw_node_ids", "absolute_paths", "credentials", "fencing_tokens"],
        "dead_control_test_required": True,
        "reconnect_and_stale_state_test_required": True,
    }
    work_package = {
        "schema_version": SCHEMA_VERSION,
        "package_id": PACKAGE_ID,
        "updated_at": UPDATED_AT,
        "status": "planning_complete_runtime_deferred_pending_model_library_download_and_main_task_acknowledgement",
        "activation_gate_id": ACTIVATION_GATE_ID,
        "activation_gate_state": "deferred_waiting_for_complete_model_download",
        "runtime_execution_allowed": False,
        "content_based_suppression": False,
        "reserved_row_range": {"first": 221, "last": 260, "count": 40},
        "extends_rows": {
            "engine_model_routing": [165, 172],
            "controller_and_event_store": [197, 200],
            "self_hosted_llm_vlm": [201, 204],
            "qa_and_benchmarks": [209, 212],
            "release": [217, 220],
        },
        "workstreams": [
            {"code": "W64-MI-GOV", "rows": [221, 224], "name": "source_governance"},
            {"code": "W64-MI-CAT", "rows": [225, 228], "name": "catalog_intelligence"},
            {"code": "W64-MI-COMPAT", "rows": [229, 232], "name": "compatibility_and_bundles"},
            {"code": "W64-MI-QUAL", "rows": [233, 236], "name": "qualification"},
            {"code": "W64-MI-SELECT", "rows": [237, 240], "name": "contextual_selection"},
            {"code": "W64-MI-OBS", "rows": [241, 244], "name": "observation_and_learning"},
            {"code": "W64-MI-LLM", "rows": [245, 248], "name": "autonomous_intelligence"},
            {"code": "W64-MI-QA", "rows": [249, 252], "name": "model_qa"},
            {"code": "W64-MI-OPS", "rows": [253, 256], "name": "operations"},
            {"code": "W64-MI-REL", "rows": [257, 260], "name": "release_and_adoption"},
        ],
        "source_snapshot_id": SOURCE_SNAPSHOT["source_snapshot_id"],
        "runtime_completion_claimed": False,
        "activation_gate": {
            "activation_gate_id": ACTIVATION_GATE_ID,
            "state": "deferred_waiting_for_complete_model_download",
            "runtime_execution_allowed": False,
            "complete_model_download_declared": False,
            "inventory_verified": False,
            "main_task_acknowledged": False,
            "authorized_phase": "none",
            "phase_permissions": phase_permissions_for("none"),
            "does_not_block_independently_governed_lanes": True,
        },
        "production_models_certified_by_this_static_package": 0,
        "autonomous_role_stacks_selected_by_this_static_package": 0,
        "main_task": {
            "task_id": MAIN_TASK_ID,
            "status": "notified_of_deferral_preservation_and_later_activation_acknowledgement_required",
        },
    }
    activation_gate = build_activation_gate_record()
    return {
        "wave64_model_intelligence_schema_catalog.json": schema_catalog,
        "wave64_wave30_model_os_source_snapshot.json": SOURCE_SNAPSHOT,
        "wave64_model_lifecycle_and_authority_registry.json": lifecycle,
        "wave64_model_selection_feature_and_ranking_policy_registry.json": ranking,
        "wave64_model_qualification_and_qa_registry.json": qa,
        "wave64_autonomous_model_role_registry.json": roles,
        "wave64_autonomous_role_activation_projection_registry.json": role_activation,
        "wave64_comfyui_runtime_adapter_policy_registry.json": runtime_adapter,
        "wave64_autonomous_aggregate_state_transition_registry.json": state_machine,
        "wave64_second_pass_autonomy_assurance_gap_registry.json": assurance,
        "wave64_canonical_contract_and_deprecation_crosswalk_registry.json": canonical_contracts,
        "wave64_autonomous_runtime_entrypoint_registry.json": runtime_entrypoints,
        "wave64_autonomous_tool_action_allowlist_registry.json": tool_allowlist,
        "wave64_operator_surface_to_controller_binding_registry.json": operator_binding,
        "wave64_autonomous_model_intelligence_work_package_registry.json": work_package,
        "wave64_model_library_activation_gate_registry.json": activation_gate,
    }


def build_examples() -> dict[str, Any]:
    z = "0" * 64
    p = provenance("wave30_source_snapshot", "wave64_model_intelligence_master_plan")
    asset = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "model_asset_intelligence_card",
        "model_asset_card_id": "asset_card_wave30_example_skin_detail_v1",
        "revision": "1",
        "status": "discovery_only_uninstalled_unqualified",
        "created_at": UPDATED_AT,
        "asset_identity": {
            "asset_id": "wave30_artifact_example_skin_detail",
            "family_id": "wave30_family_example_skin_detail",
            "asset_type": "lora",
            "revision_id": "source_revision_example",
            "sha256": None,
            "aliases": ["source metadata example"],
            "duplicate_group_id": None,
            "supersedes_asset_id": None,
        },
        "source_claims": [
            {
                "evidence_id": "source_claim_wave30_example",
                "authority_tier": "discovery_metadata",
                "sha256": None,
                "observed_at": UPDATED_AT,
                "fresh_until": None,
            }
        ],
        "engine_family_claims": ["flux"],
        "capability_hypotheses": [
            {"pass_intent": "skin_detail", "target": "skin_texture", "confidence": 0.6}
        ],
        "trigger_and_parameter_priors": {"default_weight": 0.55, "authority": "source_claim"},
        "availability": {"state": "remote_or_unknown", "verified_instances": 0},
        "lifecycle_axes": {
            "identity": "discovered",
            "binary_integrity": "unscanned",
            "availability": "remote_only",
            "runtime": "untested",
            "capability_authority": "research_candidate",
        },
        "evidence_authority_ceiling": "discovery_metadata",
        "known_conflicts": ["source_behavior_not_measured"],
        "provenance": p,
    }
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "model_execution_bundle",
        "execution_bundle_id": "bundle_sdxl_skin_specialist_example_v1",
        "revision": "1",
        "status": "candidate_example_not_runtime_authority",
        "created_at": UPDATED_AT,
        "engine_family": "sdxl",
        "base_model": rr("model_asset_intelligence_card", "base_sdxl_example"),
        "components": [
            {
                "slot": "skin_detail",
                "record_ref": rr("model_asset_intelligence_card", "lora_skin_example"),
                "order": 0,
                "parameters": {"weight": 0.45},
                "target_instance_ids": ["character_instance_01"],
                "target_regions": ["skin"],
            }
        ],
        "workflow_ref": rr("workflow_module", "regional_inpaint_example"),
        "runtime_ref": rr("runtime_profile", "local_8gib_example"),
        "prompt_profile_ref": None,
        "bundle_sha256": z,
        "compatibility_edge_ids": ["compat_example_1"],
        "certificate_ids": [],
        "mask_and_control_capabilities": {
            "supported_access_modes": ["mode_a_package_read"],
            "supported_truth_tiers": ["approved_package"],
            "supported_control_types": ["regional_inpaint_mask", "protected_mask"],
            "supports_per_instance_ownership": True,
            "supports_protected_mask": True,
            "supports_transform_chain": True,
            "mode_b_authority_ceiling": "machine_draft",
            "writes_gold": False,
        },
        "no_silent_substitution": True,
        "provenance": p,
    }
    scope_value = {
        "modality": "image",
        "pass_intent": "skin_detail",
        "target_types": ["skin_texture"],
        "engine_family": "sdxl",
        "base_model_ids": ["base_sdxl_example"],
        "character_count_min": 1,
        "character_count_max": 1,
        "mask_authority_tiers": ["mode_a_approved"],
        "resolution_or_duration_bucket": "1024_crop",
        "hardware_envelope_id": "local_8gib_example",
    }
    plan = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "model_qualification_plan",
        "qualification_plan_id": "qual_plan_skin_bundle_example_v1",
        "revision": "1",
        "status": "planned_example",
        "created_at": UPDATED_AT,
        "target_bundle_ref": rr("model_execution_bundle", bundle["execution_bundle_id"]),
        "current_authority": "load_smoke_passed",
        "requested_authority": "provisional_candidate",
        "stages": [
            {
                "stage_id": "stage_functional_ab",
                "stage_type": "functional_ab",
                "entry_gates": ["hash_verified", "load_smoke_pass"],
                "exit_gates": ["target_effect", "protected_preservation"],
                "stop_conditions": ["hard_regression", "budget_exhausted"],
            }
        ],
        "benchmark_suite_ids": ["suite_skin_detail_example_v1"],
        "resource_budget": {"max_gpu_minutes": 60, "max_outputs": 20},
        "priority_evidence": {"reason": "active_character_build_need"},
        "provenance": p,
    }
    context = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "model_selection_context",
        "selection_context_id": "context_character01_skin_repair_v1",
        "revision": "1",
        "status": "compiled_example",
        "created_at": UPDATED_AT,
        "job_id": "job_example_001",
        "run_id": "run_example_001",
        "pass_id": "pass_skin_repair",
        "scene_id": "scene_example",
        "shot_id": "shot_example",
        "take_id": "take_01",
        "character_revision_ids": ["character_revision_001"],
        "character_instance_ids": ["character_instance_01"],
        "capability_scope": scope_value,
        "defect_ids": ["skin_texture_too_smooth"],
        "target_contract": {
            "owner_instance_ids": ["character_instance_01"],
            "target_types": ["skin_texture"],
            "target_regions": ["skin"],
            "target_mask_binding_ids": ["mask_binding_skin_example_v1"],
            "coordinate_space": "parent_image_pixels",
            "allow_change_outside_target": False,
        },
        "protected_contract": {
            "protected_instance_ids": ["character_instance_01"],
            "protected_regions": ["face", "hair", "wardrobe", "background"],
            "protected_mask_binding_ids": ["mask_binding_protected_example_v1"],
            "preserve_identity": True,
            "preserve_morphology": True,
            "preserve_pose": True,
            "preserve_camera": True,
            "preserve_background": True,
            "outside_target_metric_ids": [
                "identity_drift", "pose_drift", "outside_mask_change"
            ],
        },
        "control_and_mask_requirements": {
            "mask_applicability": "required",
            "mask_binding_ids": [
                "mask_binding_skin_example_v1", "mask_binding_protected_example_v1"
            ],
            "required_access_modes": ["mode_a_package_read"],
            "required_truth_tiers": ["approved_package"],
            "required_control_types": ["regional_inpaint_mask", "protected_mask"],
            "ownership_required": True,
            "person_index_required": True,
            "ontology_version": "maskfactory_ontology_example_v1",
            "source_coordinate_space": "parent_image_pixels",
            "target_coordinate_space": "regional_crop_pixels",
            "transform_validation_required": True,
            "certificate_required": True,
            "source_image_hash_match_required": True,
            "mode_b_outputs_are_draft_only": True,
            "authority_upgrade_allowed": False,
            "writes_gold": False,
            "promotion_gate_policy": "requires_separately_validated_mode_a_binding",
        },
        "quality_cost_runtime_policy_id": "quality_priority_local_v1",
        "context_sha256": z,
        "provenance": p,
    }
    request = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "contextual_model_selection_request",
        "selection_request_id": "selection_request_skin_repair_v1",
        "revision": "1",
        "status": "requested_example",
        "created_at": UPDATED_AT,
        "selection_context_ref": rr("model_selection_context", context["selection_context_id"]),
        "registry_snapshot_ids": ["registry_snapshot_example"],
        "required_certificate_authority": "production_eligible",
        "preferred_bundle_ids": [],
        "prohibited_bundle_ids": [],
        "exploration_policy": "shadow_challenger_allowed",
        "fallback_policy": "explicit_certified_bundle_only",
        "candidate_limit": 20,
        "provenance": p,
    }
    decision = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "contextual_model_selection_decision",
        "selection_decision_id": "selection_decision_skin_repair_v1",
        "revision": "1",
        "status": "selected_example",
        "created_at": UPDATED_AT,
        "selection_request_ref": rr("contextual_model_selection_request", request["selection_request_id"]),
        "decision": "selected",
        "evaluated_candidates": [
            {
                "execution_bundle_id": "bundle_certified_sdxl_skin_v1",
                "eligible": True,
                "eligibility_reasons": ["all_hard_constraints_pass"],
                "certificate_ids": ["cert_skin_sdxl_v1"],
                "metric_vector": {"target_effect": 0.88, "identity_preservation": 0.96},
                "quality_lcb": 0.82,
                "risk_ucb": 0.08,
                "utility": 0.74,
                "uncertainty": 0.12,
                "evidence_ids": ["profile_skin_sdxl_v1"],
            },
            {
                "execution_bundle_id": "bundle_wave30_metadata_only_candidate",
                "eligible": False,
                "eligibility_reasons": ["binary_missing", "runtime_unproven", "certificate_missing"],
                "certificate_ids": [],
                "metric_vector": {},
                "quality_lcb": None,
                "risk_ucb": None,
                "utility": None,
                "uncertainty": None,
                "evidence_ids": ["source_claim_wave30_example"],
            },
        ],
        "pareto_frontier_bundle_ids": ["bundle_certified_sdxl_skin_v1"],
        "selected_bundle_id": "bundle_certified_sdxl_skin_v1",
        "selected_execution_bundle_ref": {
            "schema_id": "https://comfy-ui-main.local/schemas/model-execution-bundle/1.0.0",
            "record_type": "model_execution_bundle",
            "record_id": "bundle_certified_sdxl_skin_v1",
            "revision": "1",
            "sha256": z,
            "bytes": 1,
            "path_or_uri": "registry://model_execution_bundle/bundle_certified_sdxl_skin_v1/1",
        },
        "challenger_bundle_id": None,
        "ranking_policy_id": "wave64_model_selection_feature_and_ranking_policy_v1",
        "feature_snapshot_sha256": z,
        "selection_reasons": ["scope_match", "strongest_quality_lcb", "current_certificate"],
        "uncertainty": 0.12,
        "fallback_bundle_ids": [],
        "assignment_probability": 1.0,
        "assignment_policy_id": "wave64_contextual_ranker_numeric_v1",
        "holdout_partition_id": "qualification_holdout_example_v1",
        "learning_use_allowed": True,
        "no_silent_substitution": True,
        "provenance": p,
    }
    observation = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "model_use_observation",
        "use_observation_id": "observation_skin_repair_example_v1",
        "revision": "1",
        "status": "terminal_accepted_example",
        "created_at": UPDATED_AT,
        "job_id": "job_example_001",
        "run_id": "run_example_001",
        "pass_id": "pass_skin_repair",
        "attempt_id": "attempt_01",
        "selection_decision_ref": rr("contextual_model_selection_decision", decision["selection_decision_id"]),
        "selection_context_ref": rr("model_selection_context", context["selection_context_id"]),
        "execution_bundle_ref": rr("model_execution_bundle", "bundle_certified_sdxl_skin_v1"),
        "input_artifact_ids": ["artifact_parent_example"],
        "output_artifact_ids": ["artifact_child_example"],
        "metrics": [
            {
                "metric_id": "target_effect_accuracy",
                "value": 0.91,
                "unit": "normalized",
                "direction": "higher_is_better",
                "authority": "calibrated_metric",
                "confidence": 0.9,
                "evidence_ids": ["artifact_child_example"],
            }
        ],
        "review_observation_ids": ["review_obs_example"],
        "failure_codes": [],
        "resource_telemetry": {"peak_vram_mib": 6480, "runtime_seconds": 18.2},
        "qa_disposition": "accepted",
        "learning_eligibility": "eligible_stack_level",
        "learning_exclusion_reasons": ["component_level_attribution_not_claimed"],
        "provenance": p,
    }
    role = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "autonomous_model_role_card",
        "autonomous_role_id": "role_router_advisor_v1",
        "revision": "1",
        "status": "planned_stack_unselected",
        "created_at": UPDATED_AT,
        "role": "router_advisor",
        "allowed_input_record_types": [
            "model_selection_context",
            "autonomous_retrieval_evidence_bundle",
        ],
        "allowed_output_record_types": ["autonomous_planner_proposal"],
        "allowed_tool_actions": ["retrieve_registry_records"],
        "prohibited_authorities": [
            "hard_compatibility_override",
            "ranking_feature_mutation",
            "certificate_issue",
            "artifact_promotion",
        ],
        "context_budget": {"max_tokens": 32768, "reserved_output_tokens": 4096},
        "model_requirements": {"structured_json": True, "citation_grounding": True},
        "escalation_conditions": ["missing_certificate", "conflicting_authority", "no_eligible_candidate"],
        "provenance": p,
    }
    retrieval = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "autonomous_retrieval_evidence_bundle",
        "retrieval_bundle_id": "retrieval_skin_repair_example_v1",
        "revision": "1",
        "status": "compiled_example",
        "created_at": UPDATED_AT,
        "query": {"pass_intent": "skin_detail", "engine_families": ["flux", "sdxl", "pony"]},
        "registry_snapshot_ids": ["registry_snapshot_example"],
        "retrieved_records": [
            {
                "record_ref": rr("model_performance_profile", "profile_skin_sdxl_v1"),
                "citation": "profile_skin_sdxl_v1",
                "authority": "scoped_certificate",
                "freshness": "current",
                "conflict_group_id": None,
            }
        ],
        "negative_evidence_ids": ["failure_skin_bundle_example"],
        "conflicts": [],
        "missing_evidence": ["pony_scope_certificate"],
        "token_budget": 12000,
        "bundle_sha256": z,
        "provenance": p,
    }
    reviewer = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "autonomous_reviewer_observation",
        "reviewer_observation_id": "review_obs_example",
        "revision": "1",
        "status": "candidate_observation",
        "created_at": UPDATED_AT,
        "autonomous_stack_ref": rr("autonomous_model_execution_stack", "vlm_stack_example"),
        "artifact_ids": ["artifact_child_example"],
        "scope_bindings": [{"region": "skin", "owner": "character_instance_01"}],
        "observations": [{"defect": "none_detected", "region": "skin"}],
        "metric_observations": [],
        "uncertainty": 0.18,
        "disagreement_group_id": None,
        "promotion_authority": "none",
        "evidence_ids": ["artifact_child_example"],
        "provenance": p,
    }
    activation_gate = build_activation_gate_record()
    activation_gate["activation_gate_id"] = "wave64_model_library_activation_gate_deferred_example_v1"
    return {
        "wave64_model_asset_intelligence_card.example.json": asset,
        "wave64_model_execution_bundle.example.json": bundle,
        "wave64_model_qualification_plan.example.json": plan,
        "wave64_model_selection_context.example.json": context,
        "wave64_contextual_model_selection_request.example.json": request,
        "wave64_contextual_model_selection_decision.example.json": decision,
        "wave64_model_use_observation.example.json": observation,
        "wave64_autonomous_model_role_card.example.json": role,
        "wave64_autonomous_retrieval_evidence_bundle.example.json": retrieval,
        "wave64_autonomous_reviewer_observation.example.json": reviewer,
        "wave64_model_library_activation_gate_deferred.example.json": activation_gate,
    }


def dependency_text(row: PlanRow) -> str:
    return ", ".join("Row%03d" % value for value in row.dependencies)


def build_requirements() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "package_id": PACKAGE_ID,
        "updated_at": UPDATED_AT,
        "status": "planning_complete_runtime_deferred_pending_model_library_download_and_main_task_acknowledgement",
        "runtime_completion_claimed": False,
        "activation_gate_id": ACTIVATION_GATE_ID,
        "activation_gate_state": "deferred_waiting_for_complete_model_download",
        "runtime_execution_allowed": False,
        "content_based_suppression": False,
        "row_namespace": {
            "wave": 64,
            "first": 221,
            "last": 260,
            "count": 40,
            "workstream_count": 10,
            "rows_per_workstream": 4,
        },
        "source_snapshot_id": SOURCE_SNAPSHOT["source_snapshot_id"],
        "extends_rows": [
            "Rows165-172 pass-level engine/model routing",
            "Rows197-200 controller and event store",
            "Rows201-204 self-hosted LLM/VLM",
            "Rows209-212 multimodal QA and benchmarks",
            "Rows217-220 phased release",
        ],
        "requirements": [
            {
                "row": row.number,
                "requirement_id": "W64-MI-%03d" % row.number,
                "workstream": row.workstream,
                "phase": row.phase,
                "domain": row.domain,
                "category": row.category,
                "title": row.title,
                "implementation_action": row.action,
                "acceptance": row.acceptance,
                "dependencies": list(row.dependencies),
                "runtime_proof_required": row.runtime_proof,
                "review": row.review,
                "priority": row.priority,
                "risk": row.risk,
                "status": row_status(row),
                "planning_truth": "defined",
                "runtime_truth": row_runtime_truth(row),
                "activation_gate_required": row_requires_activation(row),
                "execution_authorized": False,
            }
            for row in ROWS
        ],
    }


def build_item_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in ROWS:
        item_id = "W64-MI-%03d" % row.number
        citation_start, citation_end = authority_citation_lines(row)
        rows.append({
            "Item_ID": item_id,
            "Item_Wave": "Wave64",
            "Item_Type": "Autonomous_Model_Intelligence_Requirement",
            "Item_Title": row.title,
            "Item_Category": row.category,
            "Item_Domain": row.domain,
            "Owner_Domain": row.workstream,
            "Autonomous_Required": "Yes",
            "Human_Input_Allowed": "Yes_For_Policy_Calibration_And_Adjudication",
            "Human_Work_Allowed": "No_Manual_Work_Required_For_Normal_Operation",
            "Codex_Action": row.action,
            "Implementation_Target": "Wave64 Rows221-260 additive child package",
            "Deliverable_Type": "Schema_Registry_Service_Test_Evidence",
            "Acceptance_Criteria": row.acceptance,
            "QA_Gates_Required": "AUTONOMOUS_MODEL_INTELLIGENCE_QA_AND_PROMOTION_PROTOCOL",
            "Visual_Review_Required": "Yes" if row.runtime_proof else "Conditional",
            "Visual_Review_Method": row.review,
            "Test_Required": "Yes",
            "Evidence_Required": "Yes",
            "Runtime_Proof_Required": "Yes" if row.runtime_proof else "No_Static_Control",
            "EC2_Allowed": "Yes_When_Resource_Profile_And_Authority_Pass",
            "Blocker_Policy": "Fail_Closed_With_Typed_Blocker_And_Continue_Unrelated_Work",
            "Source_Plan_Root": "C:/Comfy_UI_Main/Plan",
            "Citation_File": AUTHORITY_REL.name,
            "Citation_Full_Path": CANONICAL_AUTHORITY_FULL_PATH,
            "Citation_Section": "Row%03d" % row.number,
            "Citation_Line_Start": citation_start,
            "Citation_Line_End": citation_end,
            "Citation_Excerpt": row.title,
            "Source_Package": PACKAGE_ID,
            "Source_Type": "Additive_Model_Intelligence_Plan",
            "Source_File_Size": len(text_bytes(render_master_plan())),
            "Priority": row.priority,
            "Risk_Level": row.risk,
            "Status": row_status(row),
            "Created_From": "Wave30 archive audit plus Wave64 Rows165-220 gap analysis",
            "Notes": (
                "Planning-only. Dependencies: " + dependency_text(row)
                + (
                    "; execution deferred by " + ACTIVATION_GATE_ID
                    if row_requires_activation(row)
                    else "; static control work allowed before activation"
                )
            ),
            "Source_Key": item_id,
            "Source_File_Relative": str(AUTHORITY_REL).replace("\\", "/"),
            "Coverage_Level": "Full_Planning_Coverage",
            "Coverage_Audit_Status": (
                "Static_Validated_Runtime_Deferred_By_Activation_Gate"
                if row_requires_activation(row)
                else "Static_Validated_Pre_Activation_Control"
            ),
            "Ultra_Source_Coverage_Record": "Yes",
        })
    return rows


def build_tracker_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in ROWS:
        tracker_id = "W64-MI-TRK-%03d" % row.number
        source_id = "W64-MI-%03d" % row.number
        citation_start, citation_end = authority_citation_lines(row)
        rows.append({
            "Tracker_ID": tracker_id,
            "Wave": "Wave64",
            "Phase": row.phase,
            "Workstream": row.workstream,
            "Priority": row.priority,
            "Risk_Level": row.risk,
            "Owner_Role": "Autonomous_Model_Intelligence_Control_Plane",
            "Environment": "Local_Then_Certified_Target_Runtime",
            "Status": row_status(row),
            "Task_Name": row.title,
            "Detailed_Action": row.action,
            "Completion_Criteria": row.acceptance,
            "Acceptance_Evidence": "Hash-bound schema, registry, tests, runtime evidence, QA, and policy decision as applicable",
            "Dependency_Prerequisite": (
                dependency_text(row)
                + (
                    ", ActivationGate=" + ACTIVATION_GATE_ID
                    if row_requires_activation(row)
                    else ", PreActivationStaticControlOnly"
                )
            ),
            "Validation_Method": "Static validators plus scoped runtime and multimodal QA",
            "Output_Artifact": "W64-MI-%03d evidence and implementation package" % row.number,
            "Source_Path": str(AUTHORITY_REL).replace("\\", "/"),
            "Related_Source_Paths": "Wave30 source snapshot; Wave64 Rows165-220",
            "Package_Top_Level_Directory": "Plan",
            "Autonomous_Execution_Mode": (
                "Deferred_Until_Complete_Download_Inventory_And_Main_Task_Acknowledgement"
                if row_requires_activation(row)
                else "Static_Control_Only_Pre_Activation"
            ),
            "Human_Input_Allowed": "Yes_For_Policy_Calibration_And_Adjudication",
            "Human_Work_Allowed": "No_Manual_Work_Required_For_Normal_Operation",
            "Codex_Desktop_Action": "Implement_Validate_Review_And_Record_Evidence",
            "QA_Strictness": "Hard_Gate_High_Assurance",
            "Visual_Review_Required": "Yes" if row.runtime_proof else "Conditional",
            "Visual_Review_Method": row.review,
            "Test_Required": "Yes",
            "Runtime_Proof_Required": "Yes" if row.runtime_proof else "No_Static_Control",
            "EC2_Allowed": "Yes_When_Explicitly_Routed",
            "Preview_Required": "Yes_For_Media_And_UI",
            "Final_Render_Gate": "Applicable_To_Media_Qualification",
            "Evidence_Path": "Plan/Instructions/QA/Evidence/Wave64/Model_Intelligence/",
            "Citation_File": AUTHORITY_REL.name,
            "Citation_Full_Path": CANONICAL_AUTHORITY_FULL_PATH,
            "Citation_Section": "Row%03d" % row.number,
            "Citation_Line_Start": citation_start,
            "Citation_Line_End": citation_end,
            "Citation_Excerpt": row.title,
            "Source_Package": PACKAGE_ID,
            "Source_Type": "Additive_Model_Intelligence_Plan",
            "Source_Item_ID": source_id,
            "Blocker_Policy": "Typed_Blocker_No_Silent_Substitution",
            "Rerun_Policy": "Material_Hypothesis_Or_Transient_No_Output_Replay",
            "Status_Decision": (
                "Deferred_Pending_Model_Library_Activation_Gate"
                if row_requires_activation(row)
                else "Static_Control_Planning_Allowed_Runtime_Not_Authorized"
            ),
            "Notes": (
                "Do not infer model or LLM qualification from planning validation. "
                "No model-library execution is authorized until the complete-download, "
                "inventory-verification, and main-task acknowledgement gate passes."
            ),
            "Source_Key": tracker_id,
            "Source_File_Relative": str(AUTHORITY_REL).replace("\\", "/"),
            "Coverage_Level": "Full_Planning_Coverage",
            "Coverage_Audit_Status": (
                "Static_Validated_Runtime_Deferred_By_Activation_Gate"
                if row_requires_activation(row)
                else "Static_Validated_Pre_Activation_Control"
            ),
            "Ultra_Source_Coverage_Record": "Yes",
        })
    return rows


def build_coverage(schemas: dict[str, dict[str, Any]], outputs: dict[str, bytes]) -> dict[str, Any]:
    row_numbers = [row.number for row in ROWS]
    return {
        "schema_version": SCHEMA_VERSION,
        "package_id": PACKAGE_ID,
        "generated_at": UPDATED_AT,
        "status": "PASS_PLANNING_COVERAGE_RUNTIME_NOT_CLAIMED",
        "runtime_completion_claimed": False,
        "activation_gate": {
            "activation_gate_id": ACTIVATION_GATE_ID,
            "state": "deferred_waiting_for_complete_model_download",
            "runtime_execution_allowed": False,
            "complete_model_download_declared": False,
            "inventory_verified": False,
            "main_task_acknowledged": False,
        },
        "row_count": len(ROWS),
        "row_range": [min(row_numbers), max(row_numbers)],
        "unique_row_count": len(set(row_numbers)),
        "expected_contiguous_rows": list(range(221, 261)),
        "workstream_count": len(set(row.workstream for row in ROWS)),
        "rows_per_workstream": {
            code: sum(1 for row in ROWS if row.workstream == code)
            for code in sorted(set(row.workstream for row in ROWS))
        },
        "schema_count": len(schemas),
        "generated_output_count_without_preservation_manifest": len(outputs) + 2,
        "source_archive": {
            "logical_sha256": SOURCE_SNAPSHOT["logical_archive"]["sha256"],
            "entries": SOURCE_SNAPSHOT["logical_archive"]["zip_entries"],
            "artifact_rows": SOURCE_SNAPSHOT["inventory"]["artifact_rows"],
            "model_binary_count": 0,
            "authority": "discovery_metadata_only",
        },
        "hard_assertions": {
            "rows_contiguous": row_numbers == list(range(221, 261)),
            "ten_workstreams_four_rows_each": all(
                sum(1 for row in ROWS if row.workstream == code) == 4
                for code in set(row.workstream for row in ROWS)
            ),
            "content_based_suppression": False,
            "metadata_is_not_runtime_authority": True,
            "llm_vlm_self_promotion": False,
            "production_models_certified_by_static_package": 0,
            "bulk_ingestion_or_qualification_before_activation": False,
        },
    }


def build_expected_outputs() -> dict[str, bytes]:
    schemas = build_schemas()
    outputs = build_docs()
    for name, schema in schemas.items():
        outputs["Plan/08_SCHEMAS/" + name] = json_bytes(schema)
    registries = build_registries(schemas)
    work_registry = registries["wave64_autonomous_model_intelligence_work_package_registry.json"]
    work_registry["authority_documents"] = sorted(build_docs())
    work_registry["schema_files"] = sorted("Plan/08_SCHEMAS/" + name for name in schemas)
    work_registry["registry_files"] = sorted(
        "Plan/10_REGISTRIES/" + name for name in registries
    )
    work_registry["example_files"] = sorted(
        "Plan/08_SCHEMAS/examples/model_intelligence/" + name
        for name in build_examples()
    )
    for name, registry in registries.items():
        outputs["Plan/10_REGISTRIES/" + name] = json_bytes(registry)
    for name, example in build_examples().items():
        outputs["Plan/08_SCHEMAS/examples/model_intelligence/" + name] = json_bytes(example)

    requirements = build_requirements()
    outputs[
        "Plan/Items/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_REQUIREMENTS.json"
    ] = json_bytes(requirements)
    outputs[
        "Plan/Tracker/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_REQUIREMENTS.json"
    ] = json_bytes(requirements)
    outputs[
        "Plan/Items/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_ITEM_ROWS.csv"
    ] = csv_bytes(ITEM_HEADER, build_item_rows())
    outputs[
        "Plan/Tracker/Waves/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_TRACKER_ROWS.csv"
    ] = csv_bytes(TRACKER_HEADER, build_tracker_rows())

    coverage = build_coverage(schemas, outputs)
    outputs[
        "Plan/Instructions/QA/Evidence/Wave64/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_PLANNING_COVERAGE.json"
    ] = json_bytes(coverage)
    outputs[
        "Plan/Tracker/Evidence/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_PLANNING_COVERAGE.json"
    ] = json_bytes(coverage)
    return outputs


def build_preservation_manifest(outputs: dict[str, bytes]) -> dict[str, Any]:
    generated = [
        {
            "path": path.replace("/", "\\"),
            "status": "present_intentional_planning_only",
            "sha256": sha256_bytes(data),
            "bytes": len(data),
        }
        for path, data in sorted(outputs.items())
    ]
    static_paths = [
        ".gitignore",
        "Plan/07_IMPLEMENTATION/scripts/build_wave64_autonomous_model_intelligence_control_package.py",
        "Plan/07_IMPLEMENTATION/scripts/compile_orchestrator_run_plan.py",
        "Plan/Instructions/QA/Scripts/test_wave64_autonomous_model_intelligence_control_package.py",
        "Plan/Instructions/WAVE_NAMESPACE_AND_SEQUENCE_CONTROL.md",
        "Plan/Items/README.md",
        "Plan/Tracker/README.md",
        "Plan/Items/Waves/Wave64/README.md",
        "Plan/Tracker/Waves/Wave64/README.md",
    ]
    static: list[dict[str, Any]] = []
    for rel in static_paths:
        path = ROOT / rel
        if path.exists():
            data = path.read_bytes()
            static.append({
                "path": rel.replace("/", "\\"),
                "status": "present_intentional_planning_control",
                "sha256": sha256_bytes(data),
                "bytes": len(data),
            })
        else:
            static.append({
                "path": rel.replace("/", "\\"),
                "status": "expected_missing_until_materialized",
                "sha256": None,
                "bytes": None,
            })
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "wave64_autonomous_model_intelligence_preservation_manifest",
        "package_id": PACKAGE_ID,
        "generated_at": UPDATED_AT,
        "status": "PRESERVE_PENDING_MAIN_TASK_FORMAL_ADOPTION",
        "main_task_id": MAIN_TASK_ID,
        "activation_gate_id": ACTIVATION_GATE_ID,
        "activation_gate_state": "deferred_waiting_for_complete_model_download",
        "runtime_execution_allowed": False,
        "source_archive_snapshot": {
            "source_snapshot_id": SOURCE_SNAPSHOT["source_snapshot_id"],
            "logical_sha256": SOURCE_SNAPSHOT["logical_archive"]["sha256"],
            "patch_sha256": SOURCE_SNAPSHOT["patch_archive"]["sha256"],
            "source_files_remain_outside_git_tracking": True,
            "declared_local_artifact_boundary": "models/loras/List_Review/",
            "local_boundary_ignored_by_git": True,
        },
        "generated_files": generated,
        "static_control_files": static,
        "preserved_parent_packages": [
            "Wave64 Rows001-066 strict AI",
            "Wave64 Rows067-112 autonomous sound intelligence",
            "Wave64 Rows113-148 hyperreal speech",
            "Wave64 Rows149-220 ultimate modular character-to-multimodal workflow",
            "active FLUX.2 main-task work",
            "active MaskFactory task 019f4cfc-60c3-7500-8626-261dcf70db5d",
        ],
        "preservation_rule": (
            "Do not delete, clean, overwrite, renumber, merge into an active "
            "engine lane, or infer runtime completion. Main must review and "
            "record adoption before staging or production implementation."
        ),
    }


def verify_source_directory(source_dir: Path) -> list[str]:
    errors: list[str] = []
    combined = hashlib.sha256()
    for part in SOURCE_SNAPSHOT["parts"]:
        path = source_dir / part["name"]
        if not path.exists():
            errors.append("missing source part: " + str(path))
            continue
        actual_size = path.stat().st_size
        if actual_size != part["bytes"]:
            errors.append("size mismatch: " + str(path))
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                combined.update(chunk)
        if digest.hexdigest() != part["sha256"]:
            errors.append("hash mismatch: " + str(path))
    if not errors and combined.hexdigest() != SOURCE_SNAPSHOT["logical_archive"]["sha256"]:
        errors.append("logical multipart stream hash mismatch")
    patch = source_dir / SOURCE_SNAPSHOT["patch_archive"]["name"]
    if not patch.exists():
        errors.append("missing patch archive: " + str(patch))
    else:
        digest = hashlib.sha256(patch.read_bytes()).hexdigest()
        if digest != SOURCE_SNAPSHOT["patch_archive"]["sha256"]:
            errors.append("patch archive hash mismatch: " + str(patch))
    return errors


def validate_internal() -> list[str]:
    errors: list[str] = []
    numbers = [row.number for row in ROWS]
    if numbers != list(range(221, 261)):
        errors.append("Rows must be exactly contiguous 221-260")
    if len(set(numbers)) != 40:
        errors.append("Rows must be unique")
    workstreams = set(row.workstream for row in ROWS)
    if len(workstreams) != 10:
        errors.append("Exactly ten workstreams required")
    for code in workstreams:
        if sum(1 for row in ROWS if row.workstream == code) != 4:
            errors.append(code + " must contain exactly four rows")
    if SOURCE_SNAPSHOT["authority"]["runtime_selection_allowed"]:
        errors.append("Wave30 source snapshot cannot allow runtime selection")
    if SOURCE_SNAPSHOT["authority"]["promotion_allowed"]:
        errors.append("Wave30 source snapshot cannot allow promotion")
    gate = build_activation_gate_record()
    errors.extend(validate_activation_gate_semantics(gate))
    decision_example = build_examples()[
        "wave64_contextual_model_selection_decision.example.json"
    ]
    errors.extend(validate_selection_decision_semantics(decision_example))
    if gate["runtime_execution_allowed"]:
        errors.append("Current model-library activation gate must remain closed")
    if gate["prerequisites"]["download_completion_declared"]:
        errors.append("Current package cannot claim complete model download")
    if gate["prerequisites"]["main_task_acknowledged"]:
        errors.append("Current package cannot claim main-task activation acknowledgement")
    if gate["authorized_phase"] != "none":
        errors.append("Current package cannot authorize a model-library phase")
    row260 = next(row for row in ROWS if row.number == 260)
    if 255 not in row260.dependencies:
        errors.append("Row260 release certification must depend on Row255 operator UX")
    by_number = {row.number: row for row in ROWS}
    ancestors: set[int] = set()
    pending = [dependency for dependency in row260.dependencies if dependency in by_number]
    while pending:
        number = pending.pop()
        if number in ancestors:
            continue
        ancestors.add(number)
        pending.extend(
            dependency
            for dependency in by_number[number].dependencies
            if dependency in by_number
        )
    missing_release_ancestors = set(range(221, 260)) - ancestors
    if missing_release_ancestors:
        errors.append(
            "Row260 release graph is missing ancestors: "
            + ",".join(str(number) for number in sorted(missing_release_ancestors))
        )
    return errors


def materialize(write: bool, source_dir: Path | None) -> int:
    errors = validate_internal()
    outputs = build_expected_outputs()
    manifest_path = (
        "Plan/Instructions/Hydration_Rehydration/"
        "WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_PRESERVATION_MANIFEST.json"
    )
    if source_dir is not None:
        errors.extend(verify_source_directory(source_dir))

    if write:
        for rel, data in outputs.items():
            path = ROOT / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest = build_preservation_manifest(outputs)
        path = ROOT / manifest_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes(manifest))
    else:
        for rel, expected in outputs.items():
            path = ROOT / rel
            if not path.exists():
                errors.append("missing generated file: " + rel)
                continue
            actual = path.read_bytes()
            if actual != expected:
                errors.append("generated file differs: " + rel)
        manifest_file = ROOT / manifest_path
        if not manifest_file.exists():
            errors.append("missing preservation manifest: " + manifest_path)
        else:
            expected_manifest = json_bytes(build_preservation_manifest(outputs))
            if manifest_file.read_bytes() != expected_manifest:
                errors.append("preservation manifest differs: " + manifest_path)

    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(json.dumps({
        "status": "PASS",
        "mode": "write" if write else "check",
        "package_id": PACKAGE_ID,
        "rows": len(ROWS),
        "schemas": len(build_schemas()),
        "registries": len(build_registries(build_schemas())),
        "examples": len(build_examples()),
        "generated_files_excluding_manifest": len(outputs),
        "runtime_completion_claimed": False,
        "activation_gate_state": "deferred_waiting_for_complete_model_download",
        "runtime_execution_allowed": False,
        "source_verified": source_dir is not None,
    }, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="materialize deterministic package files")
    parser.add_argument(
        "--check",
        action="store_true",
        help="explicit alias for the default read-only deterministic check mode",
    )
    parser.add_argument(
        "--verify-source-dir",
        type=Path,
        default=None,
        help="optional directory containing the six supplied Wave30 archive files",
    )
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")
    return materialize(args.write, args.verify_source_dir)


if __name__ == "__main__":
    raise SystemExit(main())
