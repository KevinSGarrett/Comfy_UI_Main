# Wave64 Forced-Alignment and Audio-Event Expanded Calibration Protocol

This protocol governs the prospective matrix in
`Plan/10_REGISTRIES/wave64_forced_alignment_audio_event_expansion_plan.json`.
It expands the already accepted four-fixture Wav2Vec2 result; it does not
replace or retroactively reinterpret that evidence.

## Execution boundary

1. Verify every retained source by exact path, byte count, SHA-256, and PCM
   geometry before upload or execution.
2. Run only the calibration partition first. Freeze any empirical thresholds
   from that partition before inspecting held-out results.
3. Run each held-out partition once per immutable model, source, configuration,
   and threshold identity. An unchanged rerun is forbidden.
4. Treat Spanish and code-switch cases as measurements until an exact
   language-scoped aligner is independently qualified.
5. Require refusal for transcript mismatch, nonspeech, and two-speaker overlap
   before granting broader forced-alignment authority.
6. Audio-event labels are label families, not exact prompt strings. CLAP or any
   other single embedding route is supporting evidence only and cannot grant
   event-recognition or product authority alone.
7. If a candidate becomes promotion-eligible, require a separate independent
   audio-review packet. Automated metrics must never fabricate listening.

## Fail-closed authority

The frozen package grants only exact-source admission and prospective case
binding. It grants no general forced alignment, multilingual alignment,
overlap alignment, event recognition, independent listening, operational role
activation, golden-mask authority, or product promotion. Runtime evidence must
state the exact accepted partition and keep every broader authority false.
