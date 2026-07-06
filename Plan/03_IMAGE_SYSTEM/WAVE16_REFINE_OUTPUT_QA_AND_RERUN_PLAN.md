# Wave 16 — Refine Output QA and Rerun Plan

## QA layers

A refine output is scored against the original approved base image.

QA checks:

1. output file exists and decodes;
2. dimensions are expected;
3. input and output hashes are recorded;
4. denoise policy passed;
5. engine compatibility passed;
6. identity was preserved;
7. pose was preserved;
8. framing/body visibility was preserved;
9. environment/lighting remained continuous;
10. mask ownership passed;
11. no visible edge artifacts;
12. no realism/style regression.

## Rerun behavior

When QA fails:

- lower denoise first;
- tighten mask second;
- reduce specialty profile influence third;
- fallback to same-family SDXL fourth;
- stop after repeated high-severity drift.

## Never rerun blindly

Every rerun must have a failure reason and a changed parameter.

## Promotion threshold

A refined output may only be promoted if:

- no high-severity drift exists;
- QA score meets the selected tier;
- all required evidence files exist;
- the pass did not violate engine-family rules.
