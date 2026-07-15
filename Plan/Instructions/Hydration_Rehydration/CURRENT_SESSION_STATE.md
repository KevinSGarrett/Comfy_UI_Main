# Current Session State

Updated: 2026-07-14 America/Chicago

## Authority

- Project root and execution ledger: `C:\Comfy_UI_Main`.
- EC2 `/home/ubuntu/Comfy_UI_Main` is runtime/cache state and is not planning authority.
- Protected Git workflow is mandatory: branch, PR, required checks, merge. Do not direct-push `main`.
- Preserve unrelated dirty and untracked user work. Stage only files owned by the current bounded batch.

## Active Goal

Autonomously complete, test, review, document, track, and certify the ComfyUI hyperrealism project without recreating completed local, AWS, or legacy `C:\Comfy_UI` work.

## Latest Stable Delivery

- PR #54 merged the hash-pinned Parler-TTS 0.2.2 local CUDA runtime and independent Whisper ASR proof. The selected PCM16 WAV SHA-256 is `18b6d51cca9d9c5541bac621c09fd9059f521d8969ba5b25fa881c9284180c73`.
- PR #55 merged the Row030 frame-aligned mux repair. The current technical mux SHA-256 is `0c1153e675bd9209ce9c56d6c6694d9fb93118d69e3935fedcf77e626fed998a`; all 49 source-video frames and 32,640 source-audio samples are preserved, with mux, offset, and drift gates passing.
- Rows025, 027, 028, and 030 remain blocked on their exact playback, speaker/emotion, contact-owner, runtime-authority, or production-bundle gates. No row completion or final certification is claimed.

## Current Work

- Checkpoint one genuine local MMAudio video-to-audio runtime without rerunning the completed source video or starting EC2.
- Prompt `c90f0952-d9a8-49b1-b0ba-cbca3181bc55` completed successfully in 30.927 seconds with zero node errors. The raw FLAC SHA-256 is `15399b6a806bb3a3a04ca2b20c65245cd03fde5e5e5e66b45509fc4e03a4b2bb`.
- The 48 kHz mono conformed derivative SHA-256 is `c63a789162e165c576f00baa03b238e74deb08b0da1a7a734e2ef07356441fab`; it is 2.041 seconds, `-21.05 LUFS`, and `-2.00 dBTP`.
- Independent perceptual playback and trusted contact/force ownership remain absent. Preserve seed 2273001 without rerun; do not promote Row028 or Row030 from technical audio alone.

## Boundaries

- Manual body gold masks are not ready. Do not promote candidate masks, rerun Wave70 hard gates, or activate Wave71+.
- Do not switch to Jira bookkeeping.
- Do not rerun completed runtime proof for unchanged units.
- EC2 remains stopped unless a selected genuine runtime task requires it.
- Codex owns Git/GitHub mutations, AWS actions, final QA, Tracker/Items status, mask authority, and certification.
- Cursor is for mechanical read-only extraction; Claude Sonnet is the primary semantic review worker. Final authority remains Codex.
