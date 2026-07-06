# Wave 32 Targeted Rerun Routing

Wave 32 routes reruns only where needed.

## Rerun scope levels
1. no rerun
2. metadata/state repair only
3. local region repair
4. single frame repair
5. span repair
6. audio layer repair
7. shot-level rerun
8. segment-level rerun
9. full-scene rerun

## Rerun decision
The system chooses the smallest rerun scope that can fix the failed state without damaging passed state.
