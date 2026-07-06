# Wave 30 Breathing Audio and Exertion Binding

Breathing audio is driven by the same state engine added in Wave 28A and Wave 29.

## Breathing audio states
- calm breath
- active breath
- heavy breath
- irregular/recovery breath
- held breath
- breath tremble

## Triggers
- fatigue_level
- exertion_level
- repetition_count
- recovery state
- stress/tension state
- visible torso breathing micro-motion

## Rule
If visual breathing intensity changes, the breathing audio layer must either match it or be explicitly muted.
