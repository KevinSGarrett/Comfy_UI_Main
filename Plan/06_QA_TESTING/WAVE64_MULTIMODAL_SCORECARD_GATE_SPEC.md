# Wave64 Multimodal Scorecard Gate Spec

## Scope

TRK-W64-033 / ITEM-W64-033 is an aggregation-only evaluator. It consumes exact, hash-bound JSON records for:

- image review record
- video temporal review record
- strict-audio review report
- global-audio review report
- AV-sync certification report
- artifact manifest record (legacy Wave34 required-field contract)
- release gate decision record (legacy Wave34 required-field contract)

The evaluator never performs modality re-analysis. It only validates trust boundaries, lineage, contracts, and scorecard decisions.

## Hard Requirements

1. Canonical-root containment and symlink-safe path resolution for all bound records.
2. Exact path/sha256/bytes verification for all request bindings.
3. Strict JSON parser behavior:
   - duplicate keys rejected
   - non-finite numeric tokens rejected
4. Unknown-key rejection at request/report schema boundaries.
5. Output collision rejection and atomic output write.
6. Caller-injected aggregate/decision fields are ignored for final decisioning.
7. Legacy Wave34 schemas are interpreted as required-field contracts only.
8. Draft 2020-12 schema validation is mandatory for modern strict/global/av-sync reports; missing validation capability fails closed.

## Lineage and Trust

The evaluator binds common lineage across applicable records:

- `run_id` must agree across image, video, strict-audio, global-audio (review run), and AV-sync.
- `scene_id` / `shot_id` / `take_id` must agree across image, video, and AV-sync.
- `strict_audio_report.is_synthetic` and `global_audio_report.is_synthetic` must agree with the request and AV/image/video provenance.
- Existing image/video evidence that omits lineage is treated as a dependency blocker (blocked report, exit 2), not an invalid request.
- Mixed lineage, stale lineage, missing lineage fields, synthetic relabeling, and synthetic-to-production promotion attempts are blocked.
- Wrong nested lineage/strict-decision/gate types in image/video records are dependency blockers (blocked report, exit 2), never operational failures.

## Authority Binding

- Authority approval is object-exact, not cross-product allowlist based.
- `authority_id` + `bundle_id` pairs are validated as exact pairs with duplicate-pair and cross-product rejection.
- Each authority object binds `artifact_id`, `run_id`, `scene_id`, `shot_id`, `take_id`, `release_id`, `is_synthetic`, and all seven bound input artifacts (`path` repo-relative + `sha256` + `bytes`).
- `artifact_manifest.release_id` must match `release_gate_decision.release_id`, and the matched authority object must bind that release.
- `artifact_manifest.release_gate_decision_ref` must resolve exactly to the bound `release_gate_decision` artifact (canonical repo-relative or manifest-relative filename, no escape).
- Production approval additionally requires strict audio producer identities compatible with exact authority binding, all global production authority booleans true, and AV production authority gate PASS.

Source identity contract requirements:

- Image contract binds `tracker_id=TRK-W64-018`, `item_id=ITEM-W64-018`, and source `artifact_id` via `evidence_id == request.artifact_id`.
- Video contract binds `tracker_id=TRK-W64-021`, `item_id=ITEM-W64-021`, and source `artifact_id` via `evidence_id == request.artifact_id`.
- Missing or mismatched source identities are dependency blockers.

## Categories and Scores

Universal categories (required):

- specification compliance
- technical integrity
- quality level
- usability/deployability
- evidence completeness

Required modality categories:

- image realism and anatomy
- video temporal consistency and motion realism
- audio clarity and content accuracy
- prompt control and contamination resistance

Each category is scored 0-5 with deterministic derivations from upstream gates/contracts.

## Decision Rules

- **Approved**: no blocking defects, complete trusted evidence, every required upstream gate passes, every required category >= 3, exact approved authority/bundle, and genuine non-synthetic production provenance.
- **Conditionally approved**: only non-blocking documented defects and every required category >= 3. This may be used in isolated fixture-authority tests and must be labeled non-production.
- **Rejected**: evidence is present but fails required gates/categories.
- **Blocked**: missing/untrusted prerequisites, lineage contradictions, authority mismatch, release/authority binding mismatch, blocker collections present, or schema/contract/provenance trust failures.
- Canonical promotion decision handling:
  - unknown/ill-typed: blocked (untrusted dependency)
  - canonical `blocked_missing_proof`: blocked
  - canonical `repair_required` or `blocked_failed_QA`: rejected (present failure) when no higher-priority dependency blockers exist
  - canonical release-allowed decisions (`release_architecture_pack`, `release_runtime_certified`, `release_with_runtime_boundaries`): continue

A missing/untrusted dependency overrides numeric scores.

## CLI Exit Codes

- `0`: approved or conditionally approved
- `2`: evaluated rejected or blocked
- `1`: invalid request or operational failure

Fixture reachability contract:

- A dedicated fixture test must prove exact production-authority reachability when all seven bindings and lineage/source/release identities are exact, non-synthetic strict producers are bound, global authority booleans are true, and AV production authority gate is PASS.

No partial output is written on invalid requests.
