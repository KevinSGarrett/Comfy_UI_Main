# Wave 31 Camera Distance, Panning, and Reverb Model

## Camera distance
Camera distance controls perceived loudness, directness, and detail.

## Panning
Panning follows source position relative to the camera/listener:
- left of frame → left pan
- right of frame → right pan
- center → centered
- off-screen → pan and attenuation based on last known/source position

## Reverb
Reverb follows room size, material, and source distance:
- small soft room → short/dry reverb
- large hard room → longer/bright reverb
- outdoor/open space → low room reverb, possible environment bed
