# MaskFactory Autonomous Bridge Main Session Handoff

Updated: 2026-07-17 America/Chicago

## Recipient

Main ComfyUI project task: `019f422f-88b1-7382-872b-21de2089e983`

MaskFactory producer task: `019f4cfc-60c3-7500-8626-261dcf70db5d`

## Preservation instruction

Do not delete, clean, overwrite, or treat the Rows321-348 package as accidental
dirty work. It is an additive planning package for formal Main adoption. It
does not alter the status or semantics of Rows177-180, Row218, or other Wave64
rows.

## What this package answers

Yes, the projects should have a bridge. A partial node/API bridge already
exists conceptually and in bounded producer artifacts, but it is not a complete
production bridge. The adopted target has two parts:

1. Main controller `MaskFactoryAdapter` for Mode A package reads and Mode B live
   predict/refine requests; and
2. immutable MaskFactory release snapshots, Main consumer requirements,
   adoption receipts, compatibility CI, invalidation events, and typed feedback.

The repositories do not consume dirty worktrees or edit one another's tracker
state. They exchange immutable releases and receipts.

## Frozen decisions

- Access modes: `mode_a_package_read`, `mode_b_live_predict`,
  `mode_b_live_refine`.
- Authority states: `invalid`, `hypothesis`, `draft`,
  `qa_passed_noncertified`, `certified`.
- Issuer kinds: `maskfactory_autonomous`, `human_anchor_optional`, `none`.
- Access mode never implies authority.
- Current Mode B remains `draft` unless an exact serving-route/output
  certificate is verified.
- Main never mutates MaskFactory gold or upgrades its authority.
- MaskFactory owns producer wire schemas; Main imports their exact release
  hashes and maps them to a separately owned normalized v2 port through the
  generated executable field mapping. Every direction has complete producer
  and Main path coverage, required/drop/default/recompute/reject behavior,
  named transforms, enum conversions, and fail-closed unknown handling.
- Normalized results do not self-declare promotion eligibility; a separate
  exact consumer-policy decision derives intended-use eligibility.
- Producer `use_eligibility` is explicitly dropped and recomputed by Main.
- Original/derived lineage and per-mask/per-parent authority and certificate
  refs are mandatory; a child cannot exceed any parent.
- `fixture_only` evidence can validate fixtures but cannot certify production
  or release Row348; those paths require genuine non-fixture runtime evidence.
- App pages are bound explicitly for Home/readiness, Projects/revisions, Scene
  Builder Pose & Masks, Runs/DAG, Queue/Workers, Recovery, and QA.
- Human anchors are optional for `independent_real_accuracy`, not required for
  `core_autonomous_runtime`.
- DAZ/corpus/soak scale belongs to optional `scale_daz_maturity`.
- Preserve `Plan/Items/Reports/ITEM-W64-012_image_mask_control.json` byte-for-byte
  as historical evidence. Its former manual-mask blocker is profile-scoped
  history and cannot block the new autonomous core path.

## Added scope

Rows321-348 contain seven four-row workstreams:

- release snapshot and pinning;
- strict adapter request/result and dual-mode access;
- authority, certificate, promotion, and revocation;
- multi-character ownership, transforms, derivation, and repair;
- health, retry, cache, invalidation, event journal, and recovery;
- consumer requirements, adoption receipt, compatibility CI, and feedback;
- contract/fault assurance, strict readiness/App projections, integrated proof,
  and release.

Rows177-180 are transitive parents. Row348 directly depends on Row218 and cannot
claim core runtime release before the Character-to-Image vertical slice passes.

## Adoption procedure

1. Review the master plan, gap audit, ADR, architecture, operation protocol, and
   QA protocol.
2. Run the focused builder, validator, and test suite.
3. Confirm the Items and Tracker sidecars remain additive and planned.
4. Confirm preservation hashes and coverage evidence.
5. Record formal adoption in the Main task.
6. Schedule implementation after current canonical package work and in the
   dependency order defined by Rows321-348.
7. Ask MaskFactory to publish its first immutable v2-compatible integration
   release snapshot when producer artifacts are ready.

## Runtime implementation is not included

This handoff provides planning-contract coverage only. It does not claim that
the adapter, producer release, current node pack, live service, certified Mode B
route, runtime vertical slice, or Row348 release certificate exists.

## Main implementation order

1. Release/adoption verifier and contract fixtures.
2. Mode A single- and multi-person reads.
3. Mode B health and draft predict/refine client.
4. Normalization, authority, promotion, invalidation, and recovery.
5. Read-only controller/App projections from the generated seven-page registry
   and readiness-projection v2 contract.
6. Row218 integrated Character-to-Image proof.
7. Row348 `core_autonomous_runtime` release certification from genuine,
   non-fixture runtime evidence.

Do not let optional human/statistical or DAZ/scale programs redefine core
end-to-end completion.

## Second-pass freeze for the main session

Preserve the following additions when integrating this work:

- out-of-band Main trusted-key verification; embedded/self-signed keys cannot
  establish authenticity;
- decision-time certificate issuance/expiry/revocation and current-revocation
  evaluation;
- typed claim classes, with `operationally_certified_artifact` limited to exact
  core use and never treated as independent accuracy or training gold;
- exact still/frame/span media binding;
- separate target/protected input-region artifacts and generated outputs, with
  only the explicit Mode A exact-selector collision exception;
- complete target/other-character/prop/environment roster ownership;
- typed executable transforms with per-step continuity, side swaps, inverse,
  canonical hash, and roundtrip enforcement;
- exact execution identity, selected route/reason/alternatives, timing/resources,
  and conditional native/container provenance as factual non-promotion evidence;
- signed checkpointed event history, fork/reseal rejection, and explicit
  `outcome_unknown` reconciliation;
- canonicalization, auth, nonce/replay, and safe archive/path policies;
- schema-bound LLM/VLM/tool/memory authority boundaries; conversation summaries
  are not durable truth; and
- strict readiness projection with optional-profile blockers separated from core.
- production fixture firewall across both release and adoption, exact receipt
  hashing/signing, and the complete revalidation trigger/action table;
- exactly 28 signed/hash-bound Row348 inputs (Row218 and Rows321-347), with every
  aggregate derived from the closed report set;
- cross-document readiness validation against actual release/adoption/Row348,
  current checkpoint, page-specific gate refs, and the exact runtime-evidence
  union; and
- lossless per-target invalidation transitions with raw producer payload,
  old/new authority and certificate state, heterogeneous actions, stream,
  idempotency, causation, supersession, replacement, and rollback lineage.

Current generated package size after this pass remains 28 rows, 16 Main schemas,
10 registries, 14 examples, and 47 generated files including the preservation
manifest. Those numbers are planning-package coverage, not runtime completion.

The producer planning freeze is final at MaskingUltimate commit `938b469`, branch
`codex/mask-autonomy-bridge-plan`, PR
`https://github.com/KevinSGarrett/MaskingUltimate/pull/2`, with 113-entry planning
preservation-manifest SHA-256
`13fda3eab823e4a544f171c5570ceed99e77cd246ccbc13e686879616682bde2`.
The exact 12-schema bindings are final design-time provenance. They are not a
runtime adoption pin: the signed runtime release is still
`unpublished_unadopted`, so implementation must verify and adopt the future
production release before enabling production consumption.

The 7,282-record model-library workflow remains
`deferred_waiting_for_complete_model_download`. Do not ingest, pilot-qualify,
activate the bundle solver/benchmark runner, or connect model routes to the
autonomous LLM/VLM/App until the user or main task explicitly declares the
intended downloads complete and Main verifies the exact inventory. This bridge
cannot clear that gate; Rows223-260 remain the sole model-intelligence owner.

The main task must not delete these files as incidental dirty/untracked work. It
must also not claim core runtime release until Row218 and Rows321-347 pass with
genuine non-fixture evidence and Row348 issues its release certificate.
