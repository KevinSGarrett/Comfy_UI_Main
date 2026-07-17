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
