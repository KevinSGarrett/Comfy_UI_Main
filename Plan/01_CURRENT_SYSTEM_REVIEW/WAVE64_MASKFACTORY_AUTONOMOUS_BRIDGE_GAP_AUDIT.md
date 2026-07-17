# Wave64 MaskFactory Autonomous Bridge Gap Audit

Updated: 2026-07-17 America/Chicago

## Verified verdict

A partial bridge already exists, but a production integration release does not.
MaskFactory has a local API and a read-only ComfyUI node pack design. The Main
project has strong binding concepts and planned Rows177-180. The missing layer
is an executable controller adapter plus a versioned producer/consumer release
handshake that prevents schema, package, ontology, node-pack, certificate, and
authority drift.

This package closes the planning-contract gap only. It does not claim a running
service, installed-current node pack, completed adapter, certified live-predict
route, or end-to-end runtime proof.

## What is already useful

- MaskFactory exposes planned Mode A approved-package reading and Mode B live
  predict/refine access.
- Its service boundary is local and its generated outputs are kept separate
  from package truth.
- A MaskFactory node pack can load packages and request live drafts inside
  ComfyUI workflows.
- Main Rows177-180 already describe approved-package access, live draft access,
  normalized arbitration, and promotion-aware availability.
- Main already models image hash, person index, ontology, coordinate space,
  transforms, mask type, truth tier, provider, and certificate concepts.

## P0 gaps found

### Release and compatibility

1. No canonical immutable MaskFactory integration release snapshot is pinned by
   Main.
2. No producer artifact manifest binds commit/tag, API/OpenAPI, schemas,
   package format, ontology, node pack, wheel, capability registry,
   certificates, and revocations by hash.
3. No Main adoption receipt records exact accepted, partial, or rejected
   compatibility.
4. No consumer-requirements manifest lets MaskFactory test what Main actually
   needs.
5. No explicit schema-source/version/hash drift gate prevents two same-named but
   incompatible contracts from being treated as equivalent.

### Runtime adapter

1. Main has no production `MaskFactoryAdapter` implementation.
2. No one request/result envelope spans both access modes while preserving
   their distinct source lineage.
3. No complete typed error taxonomy exists for unavailable service, timeout,
   unknown submission, missing package, owner ambiguity, ontology drift,
   transform failure, stale or revoked certificate, output hash mismatch, and
   unsupported label.
4. Retry, idempotency, circuit-breaker, cache, restart, and invalidation
   behaviors are not frozen end to end.
5. ComfyUI node-pack installation is not equivalent to controller integration
   and cannot act as durable authority.

### Authority

1. Older terms risk collapsing package location, access mode, QA state, and
   certification into one implied truth level.
2. Mode A can contain artifacts with different authority; it is not synonymous
   with certified.
3. Mode B is currently draft, but the architecture needs a future-safe exact
   certificate path without ever upgrading all Mode B outputs globally.
4. Human anchors were incorrectly allowed to appear as a universal completion
   prerequisite. They are optional for independent real-accuracy claims.
5. There is no frozen crosswalk for `authority_state` and `issuer_kind` across
   Main and MaskFactory.

### Ownership, geometry, and derivation

1. Multi-character ownership requires explicit character instance and provider
   person-index mapping, not one flattened mask.
2. Crop, resize, pad, flip, projection, and inverse transforms need exact
   roundtrip evidence.
3. Target and protected masks need independent ownership and overlap policy.
4. Union, intersection, refinement, dilation, feathering, and projection must
   be recorded as derived artifacts and must not inflate authority.
5. Disagreement between providers needs bounded arbitration and repair, not an
   unexplained seed loop or newest-output-wins policy.

### Session coordination

1. The two autonomous tasks cannot safely reuse each other's progress by
   reading dirty worktrees or editing each other's trackers.
2. There is no immutable producer release / consumer receipt handshake.
3. There is no append-only invalidation path for ontology changes, certificate
   revocation, champion-route changes, or superseded release snapshots.
4. There is no typed feedback/repair request that lets Main report a failure to
   MaskFactory without writing MaskFactory gold or changing its authority.

## Completion-gate correction

The critical path is `core_autonomous_runtime`. It does not require a
human-annotated corpus, CVAT correction, a fixed package count, broad DAZ asset
qualification, or a seven-day DAZ soak. Those belong to optional profiles:

- `independent_real_accuracy`: independent/human-labelled statistical claims;
- `scale_daz_maturity`: corpus, DAZ, soak, and scale maturity.

Autonomous MaskFactory authority is valid when issued as
`maskfactory_autonomous` and bound to sufficient evidence and scope. Optional
human authority uses `human_anchor_optional`. Absence of either issuer is
`none`. The authority state remains one of `invalid`, `hypothesis`, `draft`,
`qa_passed_noncertified`, or `certified`.

## Required fail-closed conditions

The dependent pass must block, without globally stopping unrelated work, when:

- release snapshot, schema source, schema version, or schema hash differs;
- package, ontology, API, node pack, wheel, route, output, or certificate is not
  compatible with the consumer requirements;
- source image hash/dimensions/coordinate space do not match;
- character owner or provider person index is absent or ambiguous;
- transform roundtrip exceeds tolerance;
- target/protected mask rules are violated;
- a certificate is expired, revoked, wrong-scope, wrong-route, or wrong-output;
- Mode B claims more than `draft` without an exact serving-route/output
  certificate;
- cached material depends on a superseded or invalidated record;
- service state or submission outcome is unknown and cannot be reconciled.

## Anti-patterns rejected

- shared mutable code or editable-install authority across repositories;
- reading whichever checkout happens to be newest;
- inferring `certified` from Mode A, `gold`, high confidence, file path, or UI;
- globally treating every Mode B output as draft forever or certified at once;
- allowing Main, ComfyUI, an LLM, or a VLM to mutate MaskFactory gold;
- silent fallback to a generic mask after a service or certificate failure;
- one shared person mask for multi-character scenes;
- transferring incompatible latent state instead of decoded masks/artifacts;
- retrying quality failures with only a new seed;
- making optional human/statistical or DAZ/scale programs block core autonomy.

## Planning closure delivered by Rows321-348

The additive package freezes:

- immutable release snapshot, consumer requirements, adoption receipt, and
  invalidation records;
- strict Main-internal v2 request, result, authority, health, feedback, event,
  release, readiness-projection, and executable mapping contracts;
- closed-world producer/Main field mappings with exact schema hashes, JSONPaths,
  required/drop/default/recompute/reject actions, named transforms, explicit
  enum conversion, and producer `use_eligibility` drop/Main recomputation;
- exact access/authority vocabulary and crosswalk;
- Mode A/Mode B normalization without authority inference;
- multi-character ownership, transform, derived-mask, and protected-region
  policies, including per-mask and per-parent authority/certificate lineage and
  a machine-enforced child-authority ceiling;
- idempotency, retry, circuit-breaker, cache, event-journal, and restart rules;
- cross-repository contract CI and no-dirty-worktree policy;
- optional completion profiles separated from core release;
- fixture-versus-production certificate/release gates that prevent synthetic
  evidence from satisfying runtime authority;
- exact App read models for Home/readiness, Projects/revisions, Scene Builder
  Pose & Masks, Runs/DAG, Queue/Workers, Recovery, and QA; and
- a Row218-gated integrated release plan.

## Remaining runtime work

- publish the first immutable MaskFactory integration release;
- replace the planning-time producer schema observations in the mapping
  registry only through the exact hashes in that adopted release;
- implement the Main adapter and persistent event records;
- prove package and live draft routes under the pinned release;
- qualify any stronger live-output certificate before using it;
- run single- and multi-character ownership/transform fixtures;
- inject drift, revocation, outage, duplicate, timeout, restart, and stale-cache
  faults;
- execute the Character-to-Image vertical slice after Row218; and
- issue a core bridge release certificate from genuine, non-fixture runtime
  evidence.

Static planning coverage is not runtime readiness.

## Second-pass residual-gap audit

The second pass found and closed the following **planning-contract** gaps:

- self-signed or embedded-key substitution is excluded by an out-of-band Main
  trusted-key registry and explicit signature-trust records;
- certificate expiry/revocation is evaluated at the exact Main decision time
  against a current revocation index;
- producer `use_eligibility`, QA status, App state, LLM/VLM observations, and
  conversation summaries cannot become Main authority;
- operational artifact eligibility is separated from independent accuracy and
  training-gold claims;
- target/protected input regions are distinct from generated outputs, with one
  explicit Mode A exact-selector exception;
- character, other-character, prop, and environment ownership is roster-bound;
- transforms are executable typed chains with continuity, inverse, side-swap,
  canonical hash, and roundtrip requirements;
- still, frame, and frame-span scope prevents cross-frame authority reuse;
- execution identity, alternatives, resources, runtime kind, and timing are
  recorded without promoting the result;
- event history has trusted signed checkpoints and rejects fork, deletion,
  reorder, reseal, or substituted keys;
- `outcome_unknown` is a first-class nonterminal state requiring reconciliation;
- canonicalization, authentication, nonce/replay, and safe archive/path controls
  are explicit; and
- readiness separates core blockers from optional-profile blockers and rejects
  fixture/runtime contradictions.

The remaining gaps are implementation and evidence gaps, not missing strategy:

1. MaskFactory must freeze its final 12 producer schemas and semantic-invariant
   packet. Current Main producer bindings are provisional and must not be adopted.
2. Main must implement the adapter, trusted-key/revocation stores, event journal,
   state machine, cache/invalidation layer, and App read-model projections.
3. MaskFactory must publish a clean immutable release plus a reachable compatible
   service/package surface.
4. The integrated single-character, multi-character/prop/environment,
   still/frame/span, failure/recovery, and exact-certified-output proofs must run
   with genuine non-fixture evidence.
5. Row218 and Rows321-347 must pass before Row348 can release.

No amount of additional planning fixtures closes those runtime gaps. Conversely,
optional human-anchor statistical benchmarking and DAZ-scale maturity cannot be
silently reintroduced as core blockers.

## Final-review closure

The final adversarial pass also closed four planning-contract gaps that were
still capable of producing false green state:

1. Release and adoption fixture state is now checked on both actual records;
   production requires exact cross-hashes, runtime contexts/evidence, trusted
   release/adoption/checkpoint signatures, passing checks, and an active pin.
2. Row348 now requires a closed unique set of Row218 plus Rows321-347 signed,
   domain-separated, hash-bound gate reports. All row/trust/journal/release
   aggregates are derived and contradictory caller fields are rejected.
3. Runtime readiness now validates the actual release, adoption, Row348,
   checkpoint, gate reports, per-page gate subsets, and exact evidence union.
   The readiness JSON cannot establish readiness by internal consistency alone.
4. Invalidation now preserves raw producer payload identity and heterogeneous
   per-target authority/certificate/action/cache transitions, causation,
   idempotency, supersession, replacement, and rollback. Adoption revalidation
   covers every producer reason plus signer/trust, artifact/package, capability,
   policy/profile/node, journal, and revocation-index lifecycle changes.

These are frozen planning requirements. Runtime implementation and proof remain
open exactly as listed above.
