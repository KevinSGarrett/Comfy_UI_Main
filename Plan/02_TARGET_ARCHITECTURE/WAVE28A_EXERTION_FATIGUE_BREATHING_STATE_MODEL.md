# Wave 28A Exertion, Fatigue, and Breathing State Model

Breathing intensity is not guessed from prompt words alone. It is computed from state.

## Main state variables
- exertion_level: none, low, medium, high, recovery
- fatigue_level: fresh, warming_up, tired, exhausted, recovering
- breath_rate: calm, active, heavy, irregular, recovering
- sweat_state: none, light, visible, heavy
- posture_stability: stable, strained, trembling, recovering
- action_repetition_count

## Example rules
- If exertion is none and the subject is idle, use calm/low breathing.
- If repeated action count rises and fatigue rises, increase breathing amplitude and frequency.
- If fatigue reaches exhausted, add visible recovery behaviors: heavier breathing, posture settling, small tremble, slower reaction, and more sweat continuity.
- If the scene is calm after exertion, transition through recovery rather than instantly returning to calm.
