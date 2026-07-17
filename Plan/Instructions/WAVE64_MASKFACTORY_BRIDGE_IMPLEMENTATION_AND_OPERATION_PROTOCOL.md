# Wave64 MaskFactory Bridge Implementation and Operation Protocol

Updated: 2026-07-17 America/Chicago

## Purpose

This protocol governs implementation and operation of Rows321-348. It preserves
MaskFactory truth authority, Main downstream promotion authority, reproducible
cross-repository releases, and autonomous fail-closed behavior.

## Non-negotiable rules

1. Consume only an adopted, immutable MaskFactory release snapshot.
2. Verify schema source, schema ID, semantic version, and SHA-256 independently.
3. Keep `access_mode`, `authority_state`, and `issuer_kind` separate.
4. Use only the frozen vocabulary in the strict v2 contracts.
5. Current Mode B output is at most `draft` unless an exact serving-route/output
   certificate is present and verified.
6. Main never writes MaskFactory gold/certified packages or upgrades their
   authority.
7. ComfyUI, LLM, VLM, and browser surfaces never bypass the controller adapter.
8. A failure blocks the smallest dependent pass; unrelated DAG branches may run.
9. Never consume a dirty producer worktree, mutable `latest`, or unhashable asset.
10. Optional human/statistical and DAZ/scale profiles never silently block core.

## Phase 0: Preserve and pin

Before implementation:

- preserve the current Main working tree and Rows177-180 semantics;
- record the MaskFactory producer repository, clean commit/tag, release ID, and
  release snapshot hash;
- record all v2 schema sources, IDs, versions, and hashes;
- verify API/OpenAPI, package, ontology, node-pack, wheel, capability,
  certificate, and revocation entries;
- publish Main consumer requirements; and
- issue an adoption receipt before enabling a production route.

If no adopted release exists, implementation may use explicitly synthetic test
fixtures only. Synthetic fixtures cannot become runtime authority. Keep
`fixture_only=true`, use `fixture_validation` context, leave genuine runtime
evidence empty, and keep runtime/release claims false. A production certificate
or Row348 release must instead set `fixture_only=false`, bind non-empty genuine
runtime evidence, and pass the applicable runtime gates; copying fixture hashes
into a production envelope is a blocking integrity failure.

## Phase 1: Contract implementation

First separate surfaces. MaskFactory owns and publishes producer wire schemas
such as `mask_acquisition_request`, `mask_acquisition_receipt`, and
`operational_autonomy_certificate`. Main owns the internal normalized v2 port
and import-validation views. Pin every producer schema name/version/source/hash,
then use an explicit producer-wire-to-Main mapping. Never serialize a Main
internal schema as if it were an adopted producer wire contract. Missing or
unknown mappings fail closed.

Implement the mapping from
`wave64_maskfactory_producer_wire_to_main_port_mapping_v2.schema.json` and its
generated registry. For each direction:

1. bind both contract names, schema sources, `$id` values, versions, and hashes;
2. validate the complete source against the exact bound schema;
3. execute only enumerated RFC 9535 JSONPath rules;
4. honor required, drop, default, recompute, and reject dispositions;
5. execute the named/versioned transform and explicit enum conversion;
6. reject unknown fields, unknown enum members, missing required context, and
   unmapped target fields; and
7. prohibit every mapping rule from elevating authority.

For producer receipts, validate `$.use_eligibility` only as producer wire data,
drop it from the normalized result, and recompute Main
`$.eligible_for_intended_use` using the exact hash-bound
`maskfactory_authority_decision_v2` policy and evidence. Never copy the
producer's use recommendation into Main's policy decision.

Implement records in this order:

1. release snapshot;
2. consumer requirements;
3. adoption receipt;
4. bridge request;
5. bridge result;
6. authority decision;
7. health/capability snapshot;
8. invalidation event;
9. feedback/repair request; and
10. integration release certificate.

For each Main internal or imported producer record:

- validate Draft 2020-12 JSON Schema with unknown fields rejected;
- run semantic cross-field validation after schema validation;
- canonicalize JSON before hashing;
- persist record ID, revision, schema identity, source hash, and created time;
- reject missing, duplicate, ambiguous, stale, or conflicting identifiers; and
- preserve raw evidence by immutable reference, not inline mutable paths.

## Phase 2: Release adoption procedure

1. Fetch a named producer release into an isolated staging directory.
2. Reject archive traversal, out-of-root links, extra unmanifested files, and
   hash mismatch.
3. Verify clean source commit/tag and snapshot digest.
4. Load contract catalog and compare every required schema's source, ID,
   version, and hash.
5. Compare package/ontology/API/node-pack/wheel compatibility.
6. Compare required labels, person count, transforms, access modes, routes,
   issuer kinds, authority, certificate fields, and latency.
7. Run producer fixtures and Main negative fixtures.
8. Write one adoption receipt:
   - `adopted`: all named capabilities are authorized;
   - `partially_adopted`: only named diagnostic/shadow capabilities are allowed;
   - `rejected`: no runtime consumption.
9. Atomically update the active pin after the receipt is durable.
10. Keep the previous pin available for rollback, subject to revocation.

No semantic-version range overrides a required exact hash check.

## Phase 3: Request compilation

The pass compiler creates a v2 request from immutable project records. It must:

- bind project/run/job/pass/attempt/correlation IDs;
- use one unique idempotency key per logical side effect;
- bind source artifact SHA-256, dimensions, color, and coordinate space;
- bind character instance and provider person index or request an explicit
  assignment result;
- enumerate target owners, protected owners, intents, labels, and mask types;
- provide the complete ordered transform chain and tolerance;
- bind the adopted release and contract hashes;
- state minimum authority and accepted issuers without dictating certification;
- state diagnostic/preview/repair/promotion intended use; and
- set deadline, retry class, and resource envelope.

The LLM may propose these fields, but a deterministic compiler resolves all
identities and rejects invented references.

## Phase 4: Route eligibility

Apply hard filters before any score:

1. adopted release and contract match;
2. access mode supported;
3. package/endpoint/route available;
4. requested label and mask intent supported;
5. person count and owner mapping supported;
6. transform operations supported;
7. intended-use authority reachable;
8. certificate/revocation information available;
9. deadline/resource constraints satisfiable; and
10. circuit breaker permits a trial.

If no route passes, return a typed blocked result. Do not call a provider to see
what happens and do not substitute a generic fallback.

## Phase 5: Mode A package read

1. Resolve package only through the pinned release index.
2. Verify package manifest and every consumed artifact hash.
3. Match source image hash, dimensions, and coordinate space.
4. Match character instance/person index and ontology labels.
5. Verify transforms and inverse roundtrip.
6. Verify authority/certificate scope, issuer, expiry, and revocation.
7. Load masks read-only.
8. Produce a normalized result and durable receipt.

Directory names such as `approved` or `gold` are observational; the authority
record and certificate control eligibility.

## Phase 6: Mode B live predict/refine

1. Verify health/capability snapshot freshness and exact API/route binding.
2. Reuse the request idempotency key for transport retries.
3. Record submission-started before the call and reconcile unknown outcomes.
4. Validate response schema and source/output hashes.
5. Validate owner assignment, label set, transforms, masks, and lineage.
6. Assign `draft` under current policy.
7. Accept stronger authority only if an exact serving-route/output certificate
   binds the source, output, route, model/runtime bundle, ontology, and scope.
8. Persist timing, attempt, provider, model, and QA observations.

Service absence, stale health, timeout, or unknown response is a typed blocker.
It never silently downgrades to a random or stale mask.

## Phase 7: Normalization and arbitration

Normalize both modes without deleting their source fields. For every mask:

- verify artifact and parent hashes;
- record owner and provider person index;
- record label, mask type, coordinate space, and dimensions;
- record transform and derivation lineage;
- attach authority, issuer, certificate, expiry, revocation, and evidence;
- calculate target/protected overlap metrics; and
- calculate freshness and cache dependencies.

Record `lineage_kind`, exact derivation operation, per-mask authority, and
structured parents. Original masks require no parents and operation `none`.
Every actual derived operation requires at least one parent. Each parent record
must retain its immutable mask ref, full authority record, and explicit
operational-certificate ref. Reject the child when its authority rank exceeds
any parent or when a parent's explicit certificate ref differs from the
certificate inside its authority record. Set result authority to exactly the
minimum authority across its normalized masks.

Arbitration policy:

- reject incompatible candidates;
- prefer sufficient authority and exact-task evidence;
- never let a new draft overwrite stronger valid authority;
- branch close candidates only within an explicit budget;
- derive consensus only with operation lineage and recomputed authority;
- repair only the localized failed region with a new hypothesis; and
- abstain when ownership, transformation, or authority remains ambiguous.

## Phase 8: QA and promotion

Run QA appropriate to intended use:

- structural/hash/schema validation;
- owner/person-index isolation;
- empty/full/fragment/visibility checks;
- boundary, topology, component, and hole checks;
- transform roundtrip;
- target/protected overlap and leakage;
- temporal consistency for video spans;
- downstream edit locality and whole-artifact regression; and
- calibrated critic observations when applicable.

QA observations do not issue MaskFactory certification. Main's downstream
promotion gate verifies that required MaskFactory authority exists and that the
mask-dependent artifact passes Main QA. Both conditions are necessary.

## Phase 9: Cache and invalidation

Cache keys include at least:

- release and contract hashes;
- package/API/ontology/route/model identity;
- source artifact hash;
- owner/person index and mask intents;
- transform chain;
- authority/certificate requirement; and
- intended-use policy.

An invalidation event writes a durable tombstone before cache deletion. It may
target release, schema, ontology, package, route, model, certificate, or output.
Restart replay applies tombstones before serving cached results. Stale data may
remain for forensic inspection but cannot satisfy an active route.

## Phase 10: Retry, circuit breaker, and recovery

Transport failures:

- retry only declared retryable classes;
- reuse idempotency key;
- use bounded exponential backoff with jitter;
- honor deadline and cancellation; and
- open the breaker per exact route after policy thresholds.

Quality failures:

- require defect class, affected scope, and new hypothesis;
- preserve accepted parents;
- repair the smallest failed region/span;
- cap attempts and compute budget; and
- rerun local and whole-artifact regression QA.

On restart:

1. replay the append-only journal;
2. restore release pin and invalidation tombstones;
3. reconcile submitted/unknown attempts with provider history or idempotency;
4. resume only safe pending work;
5. never repeat a confirmed external side effect; and
6. expose unresolved ambiguity as an incident/blocker.

## Phase 11: Cross-project feedback

Main may issue a typed feedback/repair request containing source/result hashes,
defect localization, expected behavior, QA evidence, and requested producer
action. It must set `direct_gold_mutation_requested=false` and cannot specify a
new authority state. MaskFactory independently accepts, rejects, or supersedes
the request and publishes any result in a later immutable release/event.

Autonomous tasks must not edit each other's plan/tracker files as a coordination
mechanism. They exchange release and receipt artifacts.

## Phase 12: Operator and App behavior

Build the seven page bindings from
`wave64_maskfactory_bridge_app_read_model_mapping_v2`; do not invent page-local
queries:

| Page | Canonical bridge read models |
|---|---|
| Home / Readiness | readiness projection, health/capability, release certificate |
| Projects / Revisions | release snapshot, adoption receipt, invalidation |
| Scene Builder / Pose & Masks | request, result, authority decision |
| Runs / DAG | event, request, result, authority decision |
| Queue / Workers | health/capability, event |
| Recovery | invalidation, event, result |
| QA | result, authority decision, promotion policy, operational certificate |

The Home page derives its state only through
`maskfactory_bridge_readiness_projection_v2`, including exact project/revision,
pin/adoption, Row218, Rows321-347, Row348, completion profiles, page summaries,
event cursor, genuine runtime evidence, and blockers. A fixture projection must
remain not-runtime-ready.

The UI may request a new pass or repair through a typed controller command. It
cannot choose an arbitrary file path, call MaskFactory production endpoints
directly, mutate gold, edit authority, or commit promotion.

## Completion profiles

### `core_autonomous_runtime` — required

Requires the strict contracts, adopted release, Mode A and Mode B draft paths,
autonomous QA/repair/abstention, multi-character ownership, transform proof,
resilience, invalidation, downstream integration, and promotion isolation.

### `independent_real_accuracy` — optional

May use human-anchor/CVAT or other independent labelled evaluation to support
statistical real-image claims. It is never implied by core completion.

### `scale_daz_maturity` — post-core optional

Covers broad corpus/package growth, DAZ asset qualification/rendering, scale
benchmarks, and long soak tests. It is never implied by core completion.

## Required evidence per row

Every runtime row requires implementation hashes, tests, runtime manifest where
applicable, artifact hashes, QA record, fault evidence appropriate to the row,
and pass or exact blocker. Static plans and examples satisfy planning coverage
only.

## Rollback

Rollback switches Main to the previous adopted, non-revoked release pin and
replays compatibility/invalidation checks. It does not rewrite producer
history. If no safe pin remains, dependent mask passes block until a compatible
release is adopted.

## Second-pass mandatory implementation controls

### Release admission and security

1. Load the expected producer schema and canonicalization profile only from the
   candidate immutable release; compare name, ID, version, exact bytes/hash,
   property list, required list, and semantic-invariant profile.
2. Parse canonical JSON as UTF-8 while rejecting duplicate keys and non-finite
   values. Verify exact payload exclusions and signature domain before any
   normalization.
3. Resolve the signing key through Main's out-of-band trusted-key registry. Never
   treat an embedded public key as a trust anchor.
4. Before extracting a release archive, validate its manifest, declared member
   sizes, and expansion bound. Reject absolute, parent-traversal, drive, UNC,
   device, case-collision, duplicate-name, symlink, hardlink, or reparse-point
   escape; extract to isolated staging, verify every hash, then activate atomically.
5. Bind authenticated principal, exact route/capability, request payload hash,
   idempotency key, nonce, timestamp window, and adopted security profile. Reject
   nonce replay and authorization mismatch before submission.

### Request compilation

The deterministic compiler—not free-form model text—must produce:

- exact project/run/job/pass/attempt and a versioned hypothesis;
- still-image, video-frame, or frame-span scope with source hash and timing;
- declared scene roster and exactly one target character;
- protected other-character, prop, and environment ownership;
- target/protected input-region artifacts kept distinct from output masks;
- typed executable transform chain and inverse/roundtrip policy;
- accepted authority state, issuer, claim class, certificate scope, and policy;
- exact route/resource/deadline/retry envelope; and
- immutable source, reference, and evidence bindings.

The sole input/output hash-identity exception is a declared Mode A exact immutable
package selector. Any other collision fails with
`MFB_INPUT_OUTPUT_IDENTITY_COLLISION`.

### Lifecycle, retry, and reconciliation

Persist every lifecycle transition. Only registered forward transitions are
valid. `outcome_unknown` is not success, failure, or permission to resubmit. Query
the producer using the original request hash/idempotency identity and bind the
remote receipt before resolving it to succeeded, failed, or cancelled. A quality
retry creates a new attempt/hypothesis; a transport retry reuses the same identity
within the original deadline.

### Result, certificate, and decision

Normalize exact media, input lineage, output hashes, owner roster, transform,
selected route/reason/eligible alternatives, runtime provenance, timing/resources,
QA facts, authority observation, and blockers. Treat all of these as facts, not
promotion. Recompute eligibility from the complete unique criterion vector in the
exact signed Main policy. For certified use, verify signer trust, issue/expiry,
current revocation index, exact certificate scope, claim class, and genuine
non-fixture evidence at `decision_at`.

### Journal and recovery

Canonicalize and domain-separate every event; preserve stream sequence,
causation, previous hash, signer trust, and checkpoint/head pin. On restart,
verify bootstrap/checkpoint/signature/hash continuity, apply invalidation
tombstones, reconcile outcome-unknown work, reconstruct projections, and only then
serve cache or resume DAG work. Quarantine any fork, deletion, reorder, reseal, or
key substitution.

### LLM/VLM, memory, and App controls

All planner, router-advisor, VLM observer, repair, and memory outputs must validate
against their role schema and cite immutable retrieval evidence. A conversation or
compaction summary may help rehydrate context but cannot write project truth.
Only the controller tool gateway executes actions. The App reads registered
projections and sends schema-bound commands; it cannot expose raw producer paths,
call a production endpoint directly, alter policy/authority, or mark readiness.

## Final closed-record implementation procedure

1. Validate the actual release snapshot in production context, recompute its
   exact immutable ref, and reject fixture context or absent runtime evidence.
2. Build and domain-hash the adoption receipt only after release-ref, compatibility
   evidence, release signer, Main adoption signer, trusted journal checkpoint,
   and the complete revalidation-rule table are final. An active pin is derived
   only from a passing non-fixture adoption.
3. Materialize exactly one hashed and signed report for `row218_runtime` and each
   `row321_runtime` through `row347_runtime`. Reject missing, duplicate, unknown,
   hash-mismatched, untrusted, evidenceless, or self-contradictory reports.
4. Derive Row218, Rows321-347, signer, journal, `release_allowed`, status, and
   runtime-completion fields from the closed report set; domain-hash the resulting
   Row348 certificate. Never accept caller-supplied aggregates independently.
5. Construct readiness using the actual release, adoption, Row348, gate reports,
   and checkpoint. Recompute exact refs and the complete runtime-evidence union;
   bind each page to its registered gate subset before publishing the read model.
6. Normalize invalidation without flattening targets. Persist the raw producer
   payload ref, per-target transitions/actions/caches, stream and idempotency
   identity, causation, supersession, replacement, and rollback refs. Derive
   global affected/action unions and preserve unrelated scopes.
7. Match every invalidation reason to the adoption receipt's exact trigger,
   action, pin/cache impact, signature-reverification need, journal-reconciliation
   need, and dependent scope. An unregistered reason blocks the dependent pass.
