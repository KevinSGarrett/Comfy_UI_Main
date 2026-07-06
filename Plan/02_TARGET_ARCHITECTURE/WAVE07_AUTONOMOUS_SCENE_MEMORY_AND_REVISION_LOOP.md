# Wave 07 Autonomous Scene Memory and Revision Loop

## Purpose

The Scene Director must support iteration. A first output will often fail some QA goals. The system needs a structured way to determine what changed and what should be rerun.

## Scene state

Each plan creates scene state:

- request ID
- plan ID
- normalized request
- scene graph
- camera plan
- mask plan
- engine route
- pass plan
- QA goals
- output artifacts
- failed QA checks
- accepted outputs
- revision notes

## State diff

After runtime and QA, compare actual evidence against the plan.

Examples:

- planned full body, output cropped feet
- planned one person, output shows two
- planned skin detail only, background changed
- planned contact zone, source/target unclear
- planned SDXL detail pass, wrong model family selected
- planned video temporal stability, frames flicker

## Revision routing

Failures map to rerun decisions:

| Failure | Rerun decision |
|---|---|
| wrong camera/framing | rerun base/layout |
| wrong subject count | rerun base/layout |
| wrong identity | rerun identity/reference pass |
| poor anatomy | rerun base or targeted anatomy detail pass |
| mask bleed | rerun mask generation/regional pass |
| weak microdetail | rerun microdetail pass |
| contact unreadable | rerun contact graph and regional pass |
| flicker | rerun video temporal plan/frame repair |
| audio out of sync | rerun audio force timeline/mix |

## Learning loop

The system should record:

- what prompt/plan worked
- which model stack worked
- which masks worked
- which engine route worked
- which QA checks failed
- how the issue was fixed

This does not promote by itself. It provides future ranking signals.
