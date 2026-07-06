# Wave 30 Voice and Dialogue System

## Voice generation inputs
- character_id
- voice_profile_id
- language/accent/style
- emotion/intensity
- dialogue text
- timing target
- scene phase
- lip-sync target, if video is present

## Dialogue timing
Dialogue must bind to a shot/segment timeline. It cannot be free-floating.

## QA
Voice/dialogue fails if:
- wrong character voice is used,
- line timing does not match the shot,
- speech clips or distorts,
- dialogue conflicts with scene state,
- lip-sync target is missing when required.
