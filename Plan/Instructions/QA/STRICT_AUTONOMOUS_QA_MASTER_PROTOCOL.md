# Strict Autonomous QA Master Protocol

## 1. Mission

This protocol defines how Codex Desktop performs autonomous QA across code, scripts, models, prompts, ComfyUI workflows, images, video, audio, and any other generated artifact.

Codex must behave as:

- QA lead
- reviewer
- tester
- defect recorder
- re-test coordinator
- evidence collector
- release certifier

## 2. Mandatory QA principles

1. **No file-existence completion** — files alone are not evidence of correctness.
2. **Trust execution over intention** — claims must be validated through test runs, inspection, or recorded proof.
3. **Traceability required** — each artifact must link to its test evidence, QA record, and final status.
4. **Failure visibility required** — defects, blockers, and uncertain results must be recorded explicitly.
5. **Retry discipline required** — failures must be classified before retest.
6. **Done gates are absolute** — if the evidence is incomplete, the item is not complete.

## 3. QA object types

Codex must apply QA to the following object types whenever relevant:

- instruction documents
- scripts and automations
- ComfyUI workflow JSON graphs
- checkpoints, LoRAs, VAEs, ControlNet assets, and supporting models
- prompts and negative prompts
- image outputs
- video outputs
- audio outputs
- logs, manifests, and registries
- EC2 runtime outputs and pulled-back artifacts

## 4. End-to-end QA lifecycle

### Stage A — Intake
- Identify artifact type and owner task.
- Assign or create artifact ID.
- Define expected outcome.
- Define required tests and review modalities.

### Stage B — Preconditions
- Confirm required files exist.
- Confirm dependencies are available.
- Confirm required environment or runtime is available.
- Confirm known constraints.

### Stage C — Execution
- Run the relevant generation, validation, or testing process.
- Capture runtime logs, screenshots, sample outputs, or error output.

### Stage D — Review
- Apply the relevant review checklist.
- Score artifact quality.
- Record defects by severity.

### Stage E — Classification
- Pass
- Pass with non-blocking issues
- Fail
- Blocked / not testable
- Needs clarification

### Stage F — Repair / Retest
- Record failure category.
- Apply fix or mitigation.
- Re-run required tests.
- Re-inspect changed output.

### Stage G — Certification
- Update tracker and itemized list.
- Record evidence paths.
- Create done certification only if all done gates pass.

## 5. Severity system

- **S0 Critical** — dangerous corruption, destructive behavior, severe security issue, invalid artifact, or unrecoverable runtime failure.
- **S1 High** — artifact unfit for intended use; major quality or correctness defect.
- **S2 Medium** — noticeable defect that degrades quality or reliability and requires correction before sign-off unless explicitly waived.
- **S3 Low** — minor issue that does not block functional use but should be improved.
- **S4 Informational** — observation, note, or possible future optimization.

## 6. Evidence requirements by class

### Scripts / code
- command run record
- stdout/stderr or log extract
- expected vs actual summary
- final status

### ComfyUI workflows
- workflow file path
- dependency check result
- test prompt or invocation reference
- output artifact reference
- runtime log
- pass/fail notes

### Models / LoRAs / checkpoints
- file path
- metadata record
- compatibility record
- load validation result
- sample generation result
- QA notes

### Images / video / audio
- artifact path
- prompt reference
- model / workflow reference
- reviewer notes
- scorecard result
- defect log

### Wave70 masks and overlays
- named `mask_type_id`
- taxonomy citation and protected regions
- mask artifact path and preview overlay path
- semantic mask-alignment result
- protected-neighbor result
- generated-output stability result, if a generated output exists
- explicit separation between `generated_output_safe_pass` and `mask_alignment_semantic_pass`
- tracker/item status that blocks completion when mask alignment needs revision or fails

For Wave70 masks, generated-output stability cannot override a failed or uncertain overlay/alignment review. Use `Plan/Instructions/QA/WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md` before marking any mask row as locally passed or certification-ready.
- final disposition

## 7. Minimal required record per artifact

Each artifact must have, at minimum:

- artifact_id
- artifact_type
- source task or tracker ID
- created/updated timestamp
- test method used
- reviewer role
- qa_status
- evidence paths
- known issues
- next action

## 8. Prohibited behaviors

Codex must not:

- mark items complete without evidence
- silently skip review categories
- suppress failure information
- confuse “generated” with “approved”
- re-run endlessly without recording why previous runs failed
- overwrite prior evidence without preserving history or summary

## 9. Completion rule

An item is complete only if all of the following exist:

- implementation finished
- relevant test run performed
- QA record created
- artifact inspection completed
- tracker updated
- itemized list updated if applicable
- known issues reviewed
- done certification created

If any required element is missing, status must remain one of:

- in_progress
- pending_validation
- failed
- blocked
- needs_retest

## 10. Session-start QA rehydration

At session start, Codex must:

1. Read the latest rehydration files.
2. Open unresolved QA failures first.
3. Identify artifacts lacking evidence.
4. Prioritize closing high-severity failures and pending validations.
5. Resume from the most advanced valid state rather than starting over.
