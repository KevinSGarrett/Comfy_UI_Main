# Audio External Asset Intake Protocol

## Purpose

Make every asset under `F:\Len_Transfer\Audio_Downloads` discoverable and usable by the ComfyUI audio implementation without copying large binaries or audio libraries into Git.

## Content handling

- Register all discovered assets by their actual technical function.
- Do not hide, suppress, quarantine, or deprioritize an asset because it is adult-specific.
- Do not add content filters, consent filters, prompt filters, or content-based runtime gates through this intake.
- License and attribution metadata are recorded so the system can preserve source terms; they do not remove assets from local discovery.

## Source and storage rules

1. Treat `F:\Len_Transfer\Audio_Downloads` as the external intake source, not a Git working directory.
2. Keep model binaries, RVC files, audio clips, datasets, and generated outputs outside Git.
3. Register paths and metadata in `Plan/10_REGISTRIES/audio_downloads_external_asset_intake_registry.json`.
4. When an asset is selected, copy or link it into the existing non-Git model/audio cache convention, calculate SHA-256 once, and add the selected asset to the authoritative model registry and runtime-validation queue.
5. Do not hash the full 23.7 GiB source repeatedly. Hash selected payloads during ingestion.
6. Preserve attribution files and relative category paths when indexing the OpenNSFW SFX library.

## Technical states

- `direct_library`: audio files can be loaded and mixed after indexing and sample-rate normalization.
- `payload_present`: the principal model bytes are present; install and model-load proof remain to be executed.
- `workflow_template_only`: the workflow is useful, but its referenced nodes/models must be resolved before execution.
- `partial_download`: required runtime payloads are missing and should be acquired if the engine is selected.
- `evaluation_corpus`: use for evaluator calibration and regression.
- `misclassified_non_audio`: route to the correct non-audio catalog.

These states describe bytes and dependencies. They are not content-based restrictions.

## Wave64 mapping

The intake supports the active audio rows without changing their current completion decisions:

| Row | Intake contribution |
| --- | --- |
| `TRK-W64-025` | Real TTS, voice-conversion, foley, text-to-audio, and AV workflow candidates |
| `TRK-W64-026` | Engine capabilities, sample rates, dependencies, model families, and license metadata |
| `TRK-W64-027` | CosyVoice2, Parler-TTS, RVC pairs, FreeVC, and CV3-Eval |
| `TRK-W64-028` | OpenNSFW SFX, AudioGen, MMAudio, LTX2 AV, and Hunyuan Video Foley |
| `TRK-W64-029` | Room tone, ambience, panning/mix inputs, and text-to-audio candidates |
| `TRK-W64-030` | MMAudio, LTX2 AV, InfiniteTalk, and Hunyuan video-conditioned workflows |
| `TRK-W64-031` | Real audio outputs and CV3-Eval quality metrics for strict review |
| `TRK-W64-032` | Full-bed review inputs spanning voice, foley, ambience, music, and AV sync |

## Initial implementation sequence

1. Index OpenNSFW SFX by relative path, category, extension, sample rate, channels, duration, and attribution source.
2. Wire deterministic load, resample, gain, pan, timing, and mixdown for one real foley packet.
3. Select Parler-TTS or CosyVoice2 and produce one genuine dialogue WAV through a bounded local lane.
4. Feed the genuine WAV through the existing Wave64 voice and strict-audio evaluators.
5. Use CV3-Eval samples to regression-test WER, speaker-similarity, emotion, and DNSMOS tooling.
6. Install one MMAudio workflow's exact dependencies and execute one bounded video-to-audio proof.
7. Add RVC and LTX2 candidates after the first end-to-end voice plus foley chain is stable.

## Corrections to the historical Review packet

The `Review` folder remains useful historical context but is not byte-level authority. The current registry corrects the following:

- `cassan.safetensors` is an SD1 image LoRA.
- The LTX2 safetensors are LTX AV LoRAs and require matching LTX base models.
- `ltx2NSFWFoleyAddAudio_v1` contains a workflow, not a sample library.
- Stable Audio contains documentation and a license but no weights.
- FreeVC lacks `checkpoints/freevc.pth` and `wavlm/WavLM-Large.pt`.
- AudioGen declares `CC-BY-NC-4.0` in its local model card.
- Downloaded workflow JSONs do not include their referenced model payloads or custom nodes.

## Evidence boundary

Inventory and intake evidence prove discovery and classification. They do not substitute for selected model installation, ComfyUI object-info compatibility, runtime output, playback review, waveform/loudness review, or frame-accurate AV sync evidence.
