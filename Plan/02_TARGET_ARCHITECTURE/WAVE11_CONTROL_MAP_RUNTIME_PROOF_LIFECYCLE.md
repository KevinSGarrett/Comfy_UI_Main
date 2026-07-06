# Wave 11 Runtime Proof Lifecycle

## Lifecycle

1. Static plan exists.
2. Node availability proven through `/object_info`.
3. Model reference resolved through registry.
4. Control map generated.
5. Control map QA passes.
6. Workflow module executes.
7. Output evidence manifest is written.
8. Creative/technical QA passes.
9. Promotion decision is allowed.

## Blocked States

- `blocked_missing_object_info`
- `blocked_missing_preprocessor_node`
- `blocked_missing_controlnet_model`
- `blocked_missing_control_map_file`
- `blocked_dimension_mismatch`
- `blocked_failed_keypoint_qa`
- `blocked_failed_depth_order_qa`
- `blocked_failed_output_action_qa`

## Current Wave 11 Status

This pack completes static design and validation. Runtime proof remains required for all new pose/depth/normal/lineart modules.
