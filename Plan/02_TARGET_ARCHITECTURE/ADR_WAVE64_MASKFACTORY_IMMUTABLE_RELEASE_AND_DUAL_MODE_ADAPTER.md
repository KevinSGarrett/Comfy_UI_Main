# ADR-W64-MFB-001: Immutable MaskFactory Release Handshake and Dual-Mode Controller Adapter

**Status:** Accepted for planned implementation
**Date:** 2026-07-17
**Deciders:** Main ComfyUI controller authority and Ultimate MaskFactory authority

## Context

Main needs MaskFactory masks for character, pose, regional image repair, video,
and later multimodal passes. MaskFactory is an independent system with its own
packages, API, ontology, models, evidence, and certification authority. A
ComfyUI node pack provides useful workflow access but cannot safely coordinate
version drift, multi-workflow DAGs, durable retries, revocation, or promotion.

The projects must collaborate while autonomous tasks run independently. Direct
dirty-worktree sharing would be quick but non-reproducible and unsafe. A giant
shared monorepo or distributed event platform would add cost without solving the
core authority problem. The bridge must support package reads and live service
requests while keeping access mode separate from authority.

Constraints:

- local-first personal deployment;
- independent repositories and autonomous tasks;
- no direct Main writes to MaskFactory gold/certified authority;
- no authority inference from Mode A/Mode B or filesystem names;
- exact schema source/version/hash compatibility;
- multi-character owner and transform integrity;
- dependent-pass-only failure isolation;
- future stronger live certificates without globally upgrading Mode B; and
- core autonomy cannot be blocked by optional human-accuracy or DAZ maturity
  programs.

## Decision

Adopt two coordinated bridge surfaces:

1. Main owns a controller-side `MaskFactoryAdapter` with
   `mode_a_package_read`, `mode_b_live_predict`, and
   `mode_b_live_refine`. It emits one normalized v2 result while preserving
   exact source and authority lineage.
2. MaskFactory publishes immutable, hash-bound integration release snapshots.
   Main pins an exact snapshot and publishes consumer requirements plus an
   adoption receipt. Both projects run contract tests against the pin and
   process append-only invalidation events.
3. The producer/Main mapping is a generated, strict, hash-bound executable
   registry with complete direction-specific JSONPath field coverage, named
   transforms, explicit enum conversion, and fail-closed unknown handling.
   Producer `use_eligibility` is ignored for Main policy and recomputed in a
   separate Main authority decision.
4. Normalized masks preserve original/derived lineage, per-mask authority, and
   per-parent authority/certificate refs. A child cannot exceed any parent and
   result authority is the minimum mask authority.
5. Fixtures may validate contracts but cannot satisfy production certification
   or Row348. Those paths require non-fixture genuine runtime evidence.
6. The App uses seven explicit read-only page/read-model bindings and a strict
   readiness projection; it cannot infer runtime readiness from fixtures.

ComfyUI nodes remain thin read/request helpers behind controller-issued plans.
They do not own truth, routing, retries, event history, or promotion.

Authority uses the fixed states `invalid`, `hypothesis`, `draft`,
`qa_passed_noncertified`, and `certified`. Issuers are
`maskfactory_autonomous`, `human_anchor_optional`, or `none`. Mode B remains
`draft` in the current compatibility registry until an exact serving-route and
output certificate is verified.

## Options considered

### Option A: Shared mutable worktrees or editable installs

| Dimension | Assessment |
|---|---|
| Complexity | Low initially, high during drift/recovery |
| Reproducibility | Poor |
| Authority isolation | Poor |
| Autonomous task safety | Poor |
| Local cost | Low |

**Pros:** Immediate access to newest code; minimal release ceremony.

**Cons:** Dirty state is not reproducible, hashes are unstable, tasks can erase
or reinterpret each other's work, and package/API/schema compatibility is
implicit.

### Option B: Node-pack-only integration

| Dimension | Assessment |
|---|---|
| Complexity | Low |
| Workflow usability | Good for bounded graphs |
| Durable orchestration | Poor |
| Revocation/recovery | Poor |
| Promotion safety | Insufficient |

**Pros:** Fits ComfyUI and supports interactive workflows.

**Cons:** Node IDs and graph state cannot own cross-workflow DAGs, durable
receipts, retries, cache invalidation, or producer/consumer adoption.

### Option C: Controller adapter plus immutable release handshake

| Dimension | Assessment |
|---|---|
| Complexity | Medium |
| Reproducibility | High |
| Authority isolation | High |
| Autonomous task safety | High |
| Local cost | Low to medium |

**Pros:** Exact pins, typed contracts, fail-closed drift, durable evidence,
separate authority, controlled invalidation, and bounded ComfyUI integration.

**Cons:** Requires release manifests, adapter implementation, CI fixtures, and
event/recovery logic.

### Option D: Shared database and distributed event broker

| Dimension | Assessment |
|---|---|
| Complexity | High |
| Scale ceiling | High |
| Local operational burden | High |
| Current necessity | Low |
| Authority isolation | Medium without extra contracts |

**Pros:** Rich event streaming and multi-worker scale.

**Cons:** Overbuilt for one local deployment; still requires immutable
contracts and does not inherently prevent authority confusion.

## Trade-off analysis

Option C adds deliberate release and verification work but directly addresses
the highest-risk failures: silent drift, stale node packs, ambiguous authority,
multi-character misbinding, and autonomous tasks consuming uncommitted state.
Its local implementation can use JSON manifests, Git/release artifacts, SQLite
or append-only journals, and localhost HTTP. It does not preclude a future
broker if measured scale requires one.

Mode A and Mode B share a normalized result only after validation; their access
details remain visible. This avoids duplicated downstream logic without erasing
source differences. Separate authority fields make future live certification
possible without rewriting the access-mode vocabulary.

## Consequences

- MaskFactory must publish an immutable integration release before Main treats
  new producer state as production-compatible.
- Main must pin and verify exact release and contract hashes.
- Any producer field/schema change requires a new explicit mapping revision and
  exact hash adoption; same-name drift blocks.
- Installed node-pack version is checked against the release, not assumed.
- Service unavailability becomes a typed dependent-pass blocker.
- Main cannot upgrade MaskFactory authority or mutate certified packages.
- Cached bindings are invalidated on release, ontology, route, certificate, or
  schema events.
- LLM/VLM recommendations remain proposals; validators and policy own
  eligibility and promotion.
- Optional independent accuracy and scale/DAZ programs remain separately
  reportable without blocking core autonomy.
- App implementation must consume the canonical read-model registry rather than
  page-local ad hoc queries.

## Action items

1. [ ] Implement Rows321-324 release snapshot, pin, drift, and revocation logic.
2. [ ] Implement Rows325-328 strict dual-mode adapter and normalization.
3. [ ] Implement Rows329-332 authority crosswalk and promotion gates.
4. [ ] Implement Rows333-336 owner, transform, derivation, and repair controls.
5. [ ] Implement Rows337-340 resilience, cache, event, and recovery behavior.
6. [ ] Implement Rows341-344 cross-repository requirements/receipt/CI/feedback.
7. [ ] Implement Rows345-348 assurance, App projection, vertical slice, and
   core release certification after Row218.

## Revisit triggers

Reconsider transport or storage only if measured concurrency, remote workers,
or event volume exceeds the local controller design. Do not reconsider the
immutable release, typed authority, or no-direct-gold-mutation boundaries.

## Hardening addendum: accepted decisions

The following decisions are part of this ADR and cannot be weakened by an App
control, prompt, conversation summary, producer convenience field, or retry path:

- Main owns consumer eligibility and promotion. MaskFactory owns its release,
  evidence, and certificates; neither side mutates the other's truth.
- Production authenticity begins at Main's out-of-band trusted-key registry.
  Embedded keys never bootstrap trust, and signer/certificate/revocation validity
  is evaluated at the decision timestamp.
- Canonical payload profile and signature domain are exact release bindings.
  Unknown canonicalization, duplicate keys, non-finite numbers, nonce replay,
  authorization mismatch, or unsafe archive/path members fail before activation.
- The normalized port preserves exact source media/frame/span, scene roster,
  target/protected input artifacts, generated output artifacts, typed transform
  chain, runtime provenance, execution facts, claim class, and signed evidence.
- Cross-engine or decoded-artifact consumers may use a MaskFactory mask only for
  the exact intended use accepted by Main policy; operational certification is
  not an independent-accuracy or training-gold assertion.
- The event journal uses a trusted signed bootstrap/checkpoint/head model.
  Forked, deleted, reordered, or resealed history is quarantined, and an unknown
  submission outcome is reconciled before any resubmission.
- LLM/VLM roles are advisory planners, diagnosticians, and reviewers. Their
  outputs must be schema-bound; deterministic validators, signed evidence, and
  pinned policy own admission and promotion.
- App Mode and the standalone controller console consume registered read models.
  They expose no raw producer path, credential, direct production endpoint,
  authority mutation, or runtime-readiness inference.
- Production adoption rejects either-side fixtures and binds the exact release,
  adoption signature, checkpoint, compatibility evidence, and complete
  invalidation-to-revalidation rule table.
- Row348 is derived from exactly Row218 and Rows321-347 signed gate reports; no
  caller Boolean, aggregate percentage, or single umbrella check may release it.
- Readiness is validated across the actual release/adoption/Row348/gate/journal
  records and page-specific evidence subsets, never from one isolated projection.
- Invalidation retains raw producer payload identity and per-target transitions,
  actions, cache impacts, stream/idempotency/causation, supersession,
  replacement, and rollback without flattening unrelated scopes.

The producer-schema binding table is finalized only from one signed frozen
MaskFactory release. Preview hashes are deliberately non-authoritative.
