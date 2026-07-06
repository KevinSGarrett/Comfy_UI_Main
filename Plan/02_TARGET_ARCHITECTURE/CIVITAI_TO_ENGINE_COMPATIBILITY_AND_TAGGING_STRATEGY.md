# Civitai to Engine Compatibility and Tagging Strategy

## Problem

The system has many models from different engines and model families. If the AI project manager treats them as interchangeable, the flow breaks.

A Flux LoRA cannot be loaded into an SDXL path. A Pony-style model should not be treated as a generic SDXL realism model unless a specific pass is designed for it. Video, audio, ControlNet, VAE, and upscaler assets must be routed differently.

## Required normalized engine families

The AI system must normalize raw Civitai/base-model values into one of these internal engine families:

```text
flux
sdxl
pony
sd15
sd2
sd3
z_image
video
audio
controlnet
vae
upscale
ipadapter
unknown
```

## Compatibility mapping

| Raw evidence | Internal engine family |
|---|---|
| `Flux.1 D`, `Flux`, `FLUX.1-dev`, `Flux Dev` | `flux` |
| `SDXL 1.0`, `Stable Diffusion XL`, `XL` | `sdxl` |
| `Pony`, `Pony Diffusion`, `Pony XL` | `pony` |
| `SD 1.5`, `Stable Diffusion 1.5` | `sd15` |
| `SD 2.1`, `SD 2.0` | `sd2` |
| `SD3`, `Stable Diffusion 3` | `sd3` |
| `Wan`, `Hunyuan`, `LTXV`, `AnimateDiff` | `video` |
| voice, SFX, music, foley, speech | `audio` |
| ControlNet, T2I Adapter, preprocessor model | `controlnet` |
| VAE | `vae` |
| ESRGAN, upscaler | `upscale` |
| IPAdapter, CLIP Vision, FaceID support | `ipadapter` |

## Tagging dimensions

Every model must be tagged along multiple axes:

```text
engine_family
asset_type
model_type
base_model
character_identity_role
body_shape_role
skin_detail_role
face_detail_role
hand_detail_role
pose_camera_role
environment_role
lighting_role
fabric_role
contact_role
video_role
audio_role
qa_risk
runtime_requirement
```

## Pass-scope routing

Model roles must map to pass scopes:

| Role | Default pass |
|---|---|
| neutral realism checkpoint | base or refine |
| identity LoRA | identity/detail pass, usually masked for multi-character |
| skin texture LoRA | masked skin detail pass |
| body shape LoRA | large-mask body shape pass or controlled base, not random global activation |
| hand LoRA | hand detail crop/mask pass |
| contact/deformation LoRA | contact-zone masked pass |
| camera/pose LoRA | base pose/camera pass only if compatible and proven |
| fabric LoRA | masked fabric/clothing pass |
| environment model | environment/base or background pass |
| video motion model | video/GIF pass only |
| audio model | audio lane only |

## Rejected/superseded assets

If Civitai metadata, tracker metadata, or prior local evidence marks an asset as rejected or superseded, the AI system must keep the record but not select it for generation unless explicitly allowed in an experiment plan.

## QA risk classification

Every model should receive risk scores:

```text
identity_drift_risk
pose_drift_risk
style_drift_risk
anatomy_risk
artifact_risk
bleed_risk
```

These do not block use by themselves. They determine required QA.

## Multi-character rule

Character-specific models must not be applied globally in multi-character scenes unless the pass is designed to affect all characters.

Preferred multi-character strategy:

```text
person instance mask
→ per-character identity/detail pass
→ per-character LoRA/reference selection
→ crop QA
```

## Final rule

Model organization must be evidence-based, not folder-name-only.

Use this priority order:

```text
1. file hash match
2. Civitai modelVersion metadata
3. Civitai model metadata
4. existing Wave42 tracker/manifest metadata
5. filename/folder inference
6. manual/AI PM review note
```
