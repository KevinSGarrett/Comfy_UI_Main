# Wave 16 — SDXL, Pony, Flux, and Flux2 Specialty Pass Boundaries

This document defines what each engine family is allowed to do during refinement.

## SDXL / RealVisXL

Primary role:

- low-denoise global polish;
- regional inpaint/detail;
- face/hands/material cleanup;
- fabric/contact edge cleanup;
- final realism consolidation.

SDXL/RealVisXL is the default refinement target because the current system already has a large SDXL-oriented detail inventory and an inpaint/detail lane.

## Pony / Pony-SDXL

Primary role:

- masked specialty pass only;
- used when a specific specialty behavior is required and SDXL/Flux lacks a proven profile.

Restrictions:

- no global full-frame Pony repaint after approved base;
- no silent realism-style replacement;
- must be followed by QA and, if needed, SDXL cleanup;
- strict denoise cap.

## Flux1

Primary role:

- base generation;
- possible future specialty/reference refine only after local proof.

Restrictions:

- do not use Flux LoRAs inside SDXL or Pony chains;
- do not treat a Flux smoke workflow as a production refiner;
- do not move Flux latent objects into SDXL.

## Flux2

Primary role:

- planned first-class base-generation lane;
- possible future reference/edit/refine lane after local proof.

Restrictions:

- Flux2 refinement remains held until its ComfyUI workflow, model references, reference-conditioning behavior, and low-denoise preservation tests pass locally;
- no default Flux2 refiner over an approved SDXL/Pony image until proven.

## Z-Image

Primary role:

- base or proxy generation;
- bridge into SDXL/RealVisXL low-denoise refinement through decoded image.

Restrictions:

- Z-Image model objects and latents do not directly enter SDXL;
- bridge must be decoded-image based;
- output must pass preservation QA.

## SD1.5

Primary role:

- last-resort tiny artifact repair only.

Restrictions:

- no full-frame use;
- no identity-sensitive repair unless explicitly proven;
- no general body/composition rebuild.
