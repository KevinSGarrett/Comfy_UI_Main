# RunPod Autonomous Multimodal QA Operating Protocol

Program: `W64-AQA`

## 1. Authority and preflight

1. Work only from `C:/Comfy_UI_Main` and record branch, HEAD, upstream, and exact
   dirty ownership before edits or promotion.
2. Query RunPod through configured credentials without printing secrets.
3. Bind pod, GPU, volume, image, cost, overlay, ComfyUI health, Ollama health,
   model digests, queue state, and foreign process state to a timestamped receipt.
4. Never start EC2 or local ComfyUI for a current RunPod claim.
5. Treat all supplied sibling repositories, transfers, backups, WSL images,
   MaskFactory stores, and `F:/Models` as read-only evidence unless a separate
   exact-path reconciliation authorizes bytes.

## 2. Storage rules

- `/workspace` is the durable RunPod root.
- Set `OLLAMA_MODELS=/workspace/ollama` before serving or listing reviewers.
- Keep model binaries, ComfyUI inputs/outputs, reviewer artifacts, and evidence
  off the 20 GB overlay.
- Warn at 75% overlay use; block new downloads at 85% until reconciled.
- S3 writes require an exact bucket/prefix, content hash, manifest, encryption
  policy, cost posture, and a non-secret receipt.

## 3. Exclusive GPU phases

### Generation phase

1. Confirm no foreign lease or unknown job owns the queue.
2. Unload Ollama reviewers with `keep_alive=0`.
3. Reconcile GPU memory and submit one authorized ComfyUI job.
4. Wait using bounded event/status checks; do not create an infinite monitor.
5. Record generation receipt and wait until the ComfyUI queue is idle.

### Review phase

1. Confirm the generated artifact hash and complete required measurements.
2. Use the approved ComfyUI unload/free helper and record free VRAM.
3. Confirm the reviewer digest and role-registry state.
4. Run only the allowed artifact/crop/frame package through the strict prompt.
5. Validate the response against the decision schema.
6. Record raw-response hash, latency, VRAM, and disposition.
7. Unload the reviewer before returning to generation.

Never run the strict 32B reviewer concurrently with generation without a later
exact combination certificate.

## 4. Reviewer roles

- `qwen2.5vl:32b`: strict image and sampled-video reviewer only within its
  calibrated scope. Its PASS still requires deterministic gates.
- 4B/7B/8B/13B installed models: connectivity, triage, crop/frame selection,
  and known-bad smoke tests only.
- Text-only models: summarization or correction-plan formatting only; no visual,
  audio, mask, promotion, or runtime authority.
- Future audio, independent-juror, matting, and giant-model roles: blocked until
  the registry activation contract is satisfied.

## 5. Bounded repair execution

1. Freeze the accepted parent and baseline receipt.
2. Convert blocking findings to typed defect codes and exact target spans.
3. Select one allowlisted repair patch; validate IDs, ranges, nodes, and models.
4. Create a candidate without mutating the accepted parent.
5. Rerun failed gates, adjacent/protected gates, and a reduced regression set.
6. Accept only measured improvement with no protected regression.
7. Otherwise revert and increment the defect/global attempt counters.
8. Stop at two attempts per defect, four total generations, or two no-progress
   cycles. Emit a typed terminal decision rather than lowering standards.

## 6. Workflow review and patch execution

1. Snapshot the accepted workflow JSON, object-info/node inventory, installed
   models, custom-node lock, runtime policy, and accepted output receipt.
2. Run graph schema, node existence, connection type, required input, model
   identity, compatibility, path, parameter range, and resource validation.
3. Provide only these snapshots, defect JSON, logs, and approved patch points to
   the qualified workflow-engineer service.
4. Require a typed patch with rationale, expected effect, risks, target nodes,
   protected invariants, and rollback parent; reject arbitrary code or shell.
5. Apply the patch to a candidate copy, rerun static validation, and execute one
   bounded sandbox job under the phase lease.
6. Run applicable media/mask QA and workflow regressions. Promote only through
   integration authority when the candidate improves with no invariant regression.
7. Revert automatically on validation, execution, QA, cost, or regression failure.

## 7. Secrets and external systems

- Never display or store `.env` values, API keys, tokens, SSH private keys, or
  temporary credentials.
- GitHub, AWS/S3, RunPod, and MaskFactory mutations remain integration-authority
  actions with exact targets and receipts.
- Historical EC2 artifacts in S3 remain readable evidence but cannot authorize
  EC2 or claim current deployment.
- Recurring Admission/Cursor/Claude/Health/Lifecycle tasks remain disabled.

## 8. Incident and recovery

On crash, timeout, invalid JSON, OOM, queue conflict, missing model, storage
pressure, or network failure:

1. Stop new submissions.
2. Preserve foreign jobs and accepted parents.
3. Record the last durable state, active phase lease, process and queue facts.
4. Unload only processes owned by this receipt when safe.
5. Reconcile artifact hashes and state transitions.
6. Resume from the last proven state or emit `BLOCKED`; never infer success.

## 9. Shift continuation

After each accepted bounded increment, update truthful evidence, commit/push
only reviewed exact paths, recompute dependencies, and move to the next
unblocked tracker row. A single accepted artifact or blocked GPU lane is not a
shift-complete condition.
