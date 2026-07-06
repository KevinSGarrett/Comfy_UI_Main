# Wave 32 Variant and Rerun Test Matrix

## Required tests
- one-domain mismatch reroutes to local repair
- multi-domain mismatch reroutes to shot rerun
- audio-only mismatch reroutes to audio layer repair
- frame-only mismatch reroutes to frame repair
- winning variant promotes with parent linkage
- losing variant records failure reason
- successful take creates learning record
- failed take creates anti-pattern record when useful
