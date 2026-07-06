# Failure Classification and Retest Protocol

## Purpose

This protocol prevents random retrial and enforces disciplined recovery.

## Core rule

Every failed or uncertain outcome must be classified before retest.

## Failure classes

1. **Environment / infrastructure**
   - missing dependency
   - EC2 unavailable
   - disk/path issue
   - permission issue
   - secret/config issue

2. **Workflow / logic**
   - broken node reference
   - incompatible model pairing
   - invalid parameter combination
   - fallback failure

3. **Artifact quality**
   - bad anatomy
   - visual artifacting
   - flicker / drift
   - audio distortion
   - poor prompt alignment

4. **Observability / evidence**
   - missing logs
   - missing metadata
   - incomplete record
   - untraceable output

5. **Unknown / needs diagnosis**
   - root cause unclear after first-pass analysis

## Retest rules

Before retest, Codex must record:

- failed artifact ID or task ID
- failure category
- severity
- suspected cause
- exact change being made before retry
- expected result after retry

## Retest limits

- Do not repeat the same retry with no material change.
- After 2 unsuccessful similar attempts, force deeper diagnosis.
- After 3 unsuccessful attempts, escalate to blocked / needs redesign unless evidence supports a new direction.

## Pass-after-fix rule

If a retest passes, Codex must still preserve:

- original failure record
- change summary
- successful retest evidence
- final decision
