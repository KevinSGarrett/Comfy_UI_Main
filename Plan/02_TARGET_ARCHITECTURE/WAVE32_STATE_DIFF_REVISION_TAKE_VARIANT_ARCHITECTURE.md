# Wave 32 State Diff, Revisions, Takes, and Variants Architecture

Wave 32 gives the system a production memory for generated runs.

## Core objects
- planned_state: what the system intended to produce
- generated_state: what the generated output appears to contain
- state_diff: where planned and generated state disagree
- revision: a controlled change to plan or runtime configuration
- take: one generated attempt
- variant: a branch of a planned output or take
- targeted_rerun: a rerun scoped to failed domains only
- learning_record: a reusable lesson from a successful or failed run

## Purpose
Avoid blind full reruns. The system should know what changed, what failed, what passed, what to rerun, and what to reuse.
