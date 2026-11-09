# explainer2 - Ambient Escape animated explainer Shorts (v2)

Approved by Omar on 2026-11-08. Flat illustrated scenes that fill the 9:16 frame, faceless characters
with real poses, fixed text zones, one font family (Poppins; Amiri only for Arabic), camera push-ins,
word-by-word captions, cross-fades. Narration: Kokoro (Apache-2.0) with a different male voice on
every video. Sound: voice + small sound effects only (no background, no music).

- `explainer2.py` - specs, voice rotation, narration, timeline, render (`make(path, spec, index=k)` for job files)
- `scenes.py` - the illustrated scenes
- `art.py` - drawing kit and the posed characters
- `textkit.py` - all text and the safe zones
- `fonts/` - Poppins and Amiri (SIL Open Font License)

```
pip install pycairo kokoro-onnx soundfile opencv-python pillow numpy
python explainer2.py render S01 S03
```
The Kokoro model is taken from KOKORO_DIR / ./kokoro / the laptop's _system/assets/tools, or downloaded once.
