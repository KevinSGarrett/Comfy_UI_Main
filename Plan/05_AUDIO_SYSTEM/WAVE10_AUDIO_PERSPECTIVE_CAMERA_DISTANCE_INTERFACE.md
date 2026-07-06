# Wave 10 Audio Perspective and Camera Distance Interface

## Purpose

Audio should react to camera/world perspective when the scene is audio-visual.

## Camera-to-Audio Mapping

```text
close-up → near voice / intimate room tone
medium shot → normal voice distance
wide shot → roomier voice/environment balance
distant shot → more environment/reverb, lower direct voice
moving camera → audio perspective may change gradually
```

## Required Fields

Future audio/AV plans should include:

- camera distance
- room profile
- subject distance from microphone/camera
- environmental reverb
- occlusion/muffling if subject is behind object
- motion sync if camera changes distance

## Boundary

Audio is included in the full system, but audio runtime proof requires its own audio workflow, evidence, and QA.
