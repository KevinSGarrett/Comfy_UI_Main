# Pass Planning State Machine

States:
created, compiled, preflight_pending, preflight_passed, preflight_failed, queued, running, collecting_history, qa_pending, qa_passed, qa_failed, rerun_planned, rerun_running, completed, promotion_ready, promotion_blocked, stopped.

The system must stop on fatal preflight errors, missing required runtime dependencies, cost guard, or exhausted attempts.
