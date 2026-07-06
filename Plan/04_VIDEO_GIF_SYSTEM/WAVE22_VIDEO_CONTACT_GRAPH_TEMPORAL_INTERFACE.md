# Wave 22 Video Contact Graph Temporal Interface

## Purpose
For video/GIF, each contact graph edge needs temporal continuity.

## Required temporal fields
- start frame
- end frame
- duration class
- pressure curve
- occlusion curve
- contact-state curve
- rebound/release phase
- expected audio alignment point

## Temporal QA
Reject if contact flickers, source/target ownership changes between frames, or pressure/rebound behavior contradicts the Wave 21 soft-body profile.
