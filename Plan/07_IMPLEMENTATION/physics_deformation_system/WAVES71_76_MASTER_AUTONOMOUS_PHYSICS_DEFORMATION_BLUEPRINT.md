# Waves71-76 Master Autonomous Physics And Deformation Blueprint

Status: Deferred_Required_Not_Complete.

This blueprint captures the future end-to-end autonomous body-physics and deformation system for Comfy_UI_Main. It is intentionally not the next implementation target. The current project should continue the active ComfyUI foundation, workflow lanes, cost-control system, runtime proofing, Mask Factory evidence, and current QA milestones before this future layer is activated.

## Core Architecture

The target architecture is:

1. DAZ prototype sculpt/reference input.
2. Blender-owned universal production base figure.
3. Automated prototype-to-production fitting.
4. Production rig, collision, gravity, and soft-body map generation.
5. Simulation backend adapter execution.
6. Render-pass and physics-map export.
7. ComfyUI physics conditioning package creation.
8. Generated image/video/audio output.
9. Strict technical, visual, temporal, audio, and safety QA.

DAZ is not the production physics authority. DAZ is a fast prototype sculpt/reference source. The production system must fit a stable, high-end Blender-owned base figure to the DAZ prototype so the final system has stable topology, UVs, vertex groups, rig landmarks, mask IDs, and physics map IDs.

## Deferred Priority Rule

Do not activate Waves 71-76 until a source-cited project decision says the current ComfyUI generation foundation is stable enough to absorb the physics/deformation system without causing loop/drift, EC2-cost risk, or abandonment of nearer runtime goals.

Permitted before activation:

- schema planning;
- row/source coverage;
- adapter stub planning;
- non-executing validation;
- source-cited QA standards;
- inventory checks that do not install tools, start EC2, or displace active runtime work.

Not permitted before activation:

- backend installation loops;
- EC2 starts for physics simulation setup;
- generic reindexing or Wave65 churn;
- declaring physics coverage complete from these docs;
- marking rows complete without generated artifacts and strict QA.

## DAZ Prototype Role

DAZ may be used to sculpt a universal A-pose or T-pose character prototype and optionally prototype hair, clothing, materials, and reference renders.

The system must register the DAZ prototype as input data, not as a production-ready rig. Required registration metadata:

- `character_prototype_id`;
- DAZ source file path;
- export package path;
- hashes for exported FBX/OBJ/textures/reference renders;
- Genesis/version metadata if available;
- body measurement profile;
- landmark profile;
- body type / build / mass class;
- hair and clothing reference metadata;
- body/safety metadata if relevant;
- allowed-use and provenance notes.

After the DAZ prototype is registered, all subsequent conversion, fitting, production rebuild, map generation, routing, QA, and blocker recording must be autonomous.

## Universal Production Base Figure

The production base figure should be Blender-owned and versioned. It must provide:

- stable topology and vertex order;
- stable UVs;
- production edge loops around face, mouth, eyes, shoulders, elbows, wrists, hands, fingers, hips, pelvis, knees, ankles, feet, and toes;
- stable rig landmarks;
- named vertex groups;
- Wave70 mask region labels;
- Wave71 physics map identifiers;
- soft-body zones;
- protected anchors;
- collision proxy anchors;
- support-surface contact anchors;
- multi-character separation/contact anchors;
- ComfyUI export landmarks.

The system should fit this production base to the DAZ prototype using automated alignment, measurements, landmarks, silhouette matching, wrapping/lattice/shrinkwrap/fitting, and QA. The production topology must remain unchanged.

## Production Fitting Gates

A fitted production body cannot be promoted unless:

- A/T pose alignment passes;
- body measurements match the DAZ prototype within configured thresholds;
- silhouette error is below threshold across front, side, back, and three-quarter references;
- landmark error is below threshold for face, shoulders, elbows, wrists, hands, fingers, pelvis, hips, knees, ankles, feet, and toes;
- topology, UVs, vertex order, and required groups are unchanged;
- Wave70 mask labels are preserved;
- Wave71 physics map anchors are preserved;
- hands, feet, face, and joints are not distorted;
- visual overlays prove fit quality;
- a blocker is recorded if any threshold fails.

## Physics Map System

Wave71 defines the map layer. The system must support or explicitly declare fallback/no-native-equivalent for:

- vertex weight maps;
- skin weight maps;
- soft-body goal maps;
- pin/anchor maps;
- spring/stiffness maps;
- damping maps;
- bend/stretch/shear maps;
- pressure/inflation maps;
- collision/backstop maps;
- morph target / blendshape maps;
- corrective shape / pose-space deformation maps;
- delta vertex maps;
- displacement maps;
- vector displacement maps;
- normal/bump/detail maps;
- tension/compression maps;
- muscle/jiggle influence maps;
- SDF/volume collision fields;
- mass/density maps;
- elasticity/restitution maps;
- friction/stiction maps;
- contact normal maps;
- penetration-depth maps;
- rest-shape maps;
- temporal decay/settling maps;
- global gravity vector maps;
- body-part gravity sensitivity maps;
- contact load-transfer maps;
- inertia/momentum maps;
- gravity + collision response maps.

Each map must declare:

- map type;
- owner character;
- target body region;
- protected anchors;
- value range;
- frame range if temporal;
- coordinate convention;
- body-space or image-space convention;
- backend source;
- ComfyUI equivalent if one exists;
- whether it is true physics, approximation, or visual-only guidance;
- QA gates;
- generated artifacts;
- hash manifest.

## Gravity Requirements

Gravity must be first-class, not a vague soft-body property.

Required gravity concepts:

- global gravity vector;
- scene orientation;
- body gravity maps;
- body-part gravity sensitivity maps;
- per-region mass/density;
- pose-aware sag;
- hanging/draping;
- support/contact gravity;
- contact load transfer;
- inertia/momentum;
- gravity plus collision response;
- rebound and settling/decay;
- gravity plausibility QA.

No generated image or video can pass physics certification if gravity is visually impossible, if body parts sag opposite the declared gravity vector without explanation, or if support/contact surfaces do not visually carry load.

## Body Region Requirements

The system must cover:

- abdomen/stomach;
- waist/hips;
- thighs;
- calves;
- upper arms;
- hands/fingers;
- feet/toes;
- face/cheeks/neck;
- hair;
- clothing/fabric;
- support surfaces;
- held props;
- multi-character contact regions;
- audio-event contact regions.

Body regions anatomical regions must remain safety-gated and must not be routed accidentally from normal requests.

## Backend Adapter Strategy

The backend adapter layer must not make ComfyUI own 3D physics directly. It must produce clean packages that ComfyUI can consume.

Preferred order:

1. Blender first for free, scriptable, local/background MVP execution.
2. Houdini for advanced procedural/SDF/Vellum-style simulation when available.
3. Unreal for physics assets, animation, real-time simulation, and render passes when available.
4. DAZ for neutral A/T-pose prototype export only; no DAZ dForce, grip posing, hand posing, runtime morphing, production rigging, or production deformation after registration.
5. Marvelous/CLO for clothing simulation when licensed/available.
6. ComfyUI-only approximation when no true physics backend is available.

Every adapter must provide:

- availability check;
- command template;
- timeout/watchdog;
- log path;
- deterministic request hash;
- output manifest;
- hash manifest;
- validation report;
- blocker/fallback behavior.

## Simulation Package Contract

Every backend must export a standard package:

- `SIMULATION_REQUEST.json`;
- `SIMULATION_PACKAGE_MANIFEST.json`;
- reference frames or video;
- pose maps;
- depth maps;
- normal maps;
- segmentation/body-part masks;
- contact masks;
- deformation maps;
- gravity maps;
- collision/proxy evidence;
- optical flow or motion-vector maps when available;
- audio-event maps when relevant;
- backend logs;
- validation report;
- QA-ready previews/overlays.

Large binary outputs must not be committed to Git. Use local artifacts, S3/cache, or configured artifact storage.

## ComfyUI Conditioning Package

ComfyUI should consume simulation outputs as:

- ControlNet pose maps;
- ControlNet depth maps;
- ControlNet normal maps;
- lineart/canny/soft-edge where appropriate;
- SAM/segmentation/inpaint masks;
- regional prompt masks;
- temporal masks;
- optical-flow/motion reference frames;
- audio-event timing maps;
- whole-artifact QA preview overlays.

ComfyUI outputs must label whether physics guidance is true simulation-derived, backend approximation, or ComfyUI-only approximation. The system must not claim true physical simulation when it only used 2D guidance maps.

## Strict QA And Certification

Certification requires:

- schema validation;
- source citation;
- hash manifests;
- map value range validation;
- dimension/frame-count alignment;
- visual overlay review;
- generated output proof;
- whole-image/full-frame review;
- full-duration video review when applicable;
- full-duration audio review when applicable;
- no clipping;
- no floating contact;
- no impossible gravity;
- no identity drift;
- no body-shape drift;
- no broken hands, feet, face, eyes, or joints;
- no clothing ownership drift;
- no multi-character merge or identity bleed;
- no target-region-only pass if unrelated full-frame defects exist.

For video, representative frame grids are not enough by themselves. The system must also review playback/full duration and temporal continuity.

For audio, event timing must align with visual contact, footsteps, hand contact, clothing rustle, support compression, mouth/breath/chest motion, and impact events.

## Failure Handling

Failures must be classified as:

- prototype intake failure;
- universal base fit failure;
- production rig failure;
- physics map failure;
- backend adapter failure;
- simulation package failure;
- ComfyUI route failure;
- generated output failure;
- visual QA failure;
- video QA failure;
- audio QA failure;
- body/geometry route failure;
- cost-control failure.

On failure, write a precise blocker with evidence and continue the nearest active source-cited project task. Do not start broad housekeeping, generic index refreshes, or repeated validators without changed inputs.

## Relationship To Wave70

Wave70 says what body, scene, contact, interaction, body regions, and protected-neighbor mask regions exist.

Waves71-76 say how those regions receive physics/deformation maps, production body fitting, backend simulation, ComfyUI conditioning, and strict QA.

Wave70 rows and Waves71-76 rows are requirements, not proof. They become complete only through generated artifacts, evidence, and strict QA.
