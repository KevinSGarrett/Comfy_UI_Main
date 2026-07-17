# Wave64 Production Operator Application and ComfyUI App Mode Strategy

## Product decision

The primary product is a standalone local controller console backed by the
durable autonomous controller. ComfyUI App Mode provides small workflow-specific
launchers. An optional frontend extension links ComfyUI diagnostics to the
controller. This division preserves ComfyUI's strengths while avoiding hidden
state spread across workflow files and browser sessions.

## Information architecture

### Home

Readiness summary, active projects, current runs, blockers, incidents, pending
reviews, storage/worker health, and safe next actions.

### Projects

Project revisions, deliverables, characters, scenes, timelines, continuity,
policies, budgets, artifacts, and release status. Draft/published revisions are
separate; autosave never publishes.

### Character Library

Identity/body/surface/wardrobe/accessory/voice packages, views, adapters,
benchmarks, continuity history, accepted/failure examples, and per-engine
capability. Multi-character scene instances reference packages; they do not
merge character authority.

### Scene Builder

Environment, lighting, props, surfaces, characters, ownership, spatial layout,
actions, dialogue, audio expectations, and continuity parents. Provide schema
forms plus an evidence-aware natural-language assistant. The assistant proposes
structured changes. Interactive operator review is optional; autonomous mode
may execute only after schema/semantic validation and deterministic policy
authorization, without a human dependency.

### Shot Timeline

Multi-track editor for shots, camera, characters, pose, masks, contacts,
keyframes, passes, defects, dialogue, voice, breath, foley, ambience, music,
automation, and promotion. Support zoom, snapping to rational clock boundaries,
range selection, markers, compare, branch/take views, undo, optimistic conflicts,
and read-only artifact overlays.

### Pose and Masks

Per-character skeleton/depth/silhouette, provider person index, render order,
contacts, target/protected masks, ontology, transforms, truth tier, certificate,
and round-trip visualization. Mode A package reads and Mode B prediction/refine
drafts are visibly distinct, but access mode and authority are independent.
Neither mode grants promotion authority; every production use requires a
current exact-output operational certificate whose scope matches the artifact,
person instance, ontology, transforms, issuer, workflow, model, and runtime.

### Image, Video, Audio, and AV workspaces

Each workspace shows source authority, planned passes, exact selected bundles,
candidate branches, progress, artifacts, metrics, defects, repairs, and release
state. Video adds synchronized frame/flow/track views. Audio adds waveform,
spectrogram, loudness, stems, objects, buses, and automation. AV adds frame,
waveform, phoneme/viseme, event, offset, and drift overlays.

### Runs

Live DAG, pass/attempt state, worker/lease, queue, resource budget, receipts,
logs, lineage, cancellation, reconciliation, and recovery. A stale or ambiguous
attempt is explicit. The UI offers only commands safe for the current state.

### QA and Compare

Synchronized side-by-side, wipe, onion skin, difference, flicker, audio A/B,
null, and AV overlays. Blind labels are available. Metrics link to evidence and
calibration. Operator annotations are immutable records. Approve/reject/repair
are commands, never direct field edits.

### Models and Capabilities

Discovery metadata, exact installed bundles, compatibility, certificates,
benchmarks, performance profiles, failure notes, drift, quarantine, and route
explanations. Make "why selected," "why filtered," uncertainty, and evidence
freshness understandable. Planned models never look production-ready.

### Runtime and Workers

Runtime locks, workers, leases/fencing, queues, VRAM/RAM/disk, model residency,
latency, incidents, receipts, reconciliation, and safe recovery. Credentials and
raw remote commands are never rendered.

## Interaction modes

- Guided: intent, curated choices, previews, plain-language QA.
- Director: scene/shot/timeline/candidate/repair control.
- Expert: exact bundles, parameters within certified envelopes, detailed metrics.
- Diagnostic: node/runtime/evidence detail; always visibly non-promotional.

Mode changes affect visibility, not authority.

## State design

Every page implements loading, empty, ready, dirty, saving, queued, running,
cancelling, reconciling, blocked, failed, offline, stale, and completed states.
Errors preserve input, identify the exact failed authority/dependency, show a
correlation ID, and offer only safe actions. Projection freshness is always
visible when it matters.

## Accessibility and responsive behavior

Target WCAG 2.2 AA, full keyboard navigation, visible focus, accessible names,
semantic landmarks, captions/transcripts, non-color status signals, reduced
motion, scalable text, waveform/spectrogram alternatives, and screen-reader
summaries for charts/timelines. Mobile App Mode remains useful for quick
workflows; the full timeline targets desktop/tablet with a simplified mobile
review experience.

## Application tests

Contract-test every control-to-command/query binding. Component-test every
state. Visual-regress critical screens and media overlays. Accessibility-test
keyboard and assistive semantics. Fault-test disconnects, restarts, stale
versions, duplicate commands, lease loss, ambiguous submissions, corrupt
artifacts, disk full, model unload, and projection lag. E2E-test one-character,
two-character, video repair, voice/foley mix, AV repair, and release paths using
synthetic then certified fixtures.
