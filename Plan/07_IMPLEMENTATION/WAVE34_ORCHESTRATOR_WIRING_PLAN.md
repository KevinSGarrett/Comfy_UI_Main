# Wave 34 Orchestrator Wiring Plan

## Required orchestrator routes
- intake_to_scene_plan
- scene_plan_to_app_mode
- app_mode_to_preview_plan
- preview_to_preview_QA
- preview_QA_to_state_diff
- state_diff_to_targeted_rerun
- preview_pass_to_final_preflight
- final_preflight_to_local_or_EC2
- runtime_outputs_to_manifests
- manifests_to_QA_certification
- QA_certification_to_release_decision
- release_decision_to_handoff

## Hard block
No route may jump directly from intake to EC2 final render.
