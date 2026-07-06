# Wave 33 Proxy Preview, Animatic, and Realism Budget Architecture

Wave 33 makes cheap previews mandatory before expensive final renders.

## Core objects
- proxy_preview_plan
- animatic_plan
- realism_budget
- compute_budget
- preview_qa_report
- final_render_preflight
- budget_escalation_record

## Purpose
Use low-cost previews to test composition, identity, pose, motion, contact, continuity, audio timing, and scene logic before running expensive EC2 final rendering.

## Rule
The system should spend the least possible compute until the planned output has passed preview QA.
