# Craft research (subagent report, 2026-09-28): how the strong code-made music videos were built

Could not fetch X directly; no repo was found for "Not Yet Written", "TO WHAT END" or Hesamation's piece.

## Key sources
- **PDoomVideo** https://github.com/JohnHeibel/PDoomVideo: p5.js + p5.brush, headless Chrome, resumable parallel render. ANIMATION_GUIDE.md style rules: wash + ink outlines; watercolour bleed; no pure black/white; **line boil reseeded 12×/s**; backOut/elasticOut, squash, anticipation; `pulse(t)` on beats; camera always drifting/pushing; shots 1.4–4 s, one clear focal action with a big silhouette; deterministic (`hash(i)`); paper texture + grain + vignette on every frame; iris/flash transitions; contact sheets. Starter kit: https://github.com/JohnHeibel/ClaudeAnimationBase ("handmade, alive, one piece, no text, transitions always, something happens in every scene").
- **claude-absolutely-right** https://github.com/eszn/claude-absolutely-right: Klatt formant voice, DP rap flow, a full mix chain to −14 LUFS, pixel art 320×180 ×6, analysis QA.
- **A Small Odyssey** https://github.com/IshiakiZ/a-small-odyssey: watercolour by recursive Gaussian polygon deformation plus translucent glazes and darkened edges, granulation, paper grain, fibres; a piecewise beat grid; visuals one frame early; painter + art-director agents, ≥2 critique rounds.
- Kevin Ngo's method (https://www.iart.ai/blog/ai-javascript-animation): `draw(ctx,t)`, seeded, one shared timeline object for picture and music, a 10–20 shot list first, contact sheets every 0.5 s.
- claude-animation-studio (score file drives audio and frames; a sync verifier at ±20 ms; loudness/true-peak checks; storyboard gate; half-res drafts). javascript-animation-skills (the render fails if a cut misses the beat). dev.to "this video is about how this video was made" (Whisper + difflib lyric alignment; reviewer agent; pixel-stat checks). opus-5.5-musical-cartoon (pre-painted seeded sprites; the model inspects frames).

## Cross-cutting
1. A textured surface beats flat shapes. 2. Secondary motion is what makes it feel alive. 3. One timeline for sound and picture, verified by script. 4. Short shots, clear silhouettes, cuts on downbeats. 5. Storyboard → style guide → painters → critic → revise; deterministic, resumable renders.

## Ranked upgrades for my pipeline
1. **Finishing pass** (grain per frame, paper multiply, vignette, **halation**, grade). ~50 lines. Biggest jump.
2. **Boil/jitter** outlines (reseed 8–12×/s).
3. **Easing + secondary motion** library; the camera always drifts/pushes; beat pulses.
4. **Watercolour/ink fills** (Tyler Hobbs deformation), pre-rendered as seeded sprites.
5. Motion blur via sub-frame averaging (fast shots only).
6. **One timeline + sync verifier** (demucs stems, per-stem onsets drive pulses; assert hits within ±1 frame).
7. **moderngl shaders** (fBm skies/water, SDF + smin, bloom), cheap on the RTX 2060.
8. **Review loop**: 2 fps contact sheets, a critic subagent with a rubric, ≥2 rounds, half-res drafts.
9. **Style guide before code** (palette, shot lengths, easing, texture stack, frame budget).
10. Optional: Rocket-style keyframe tracks (pyrocket).
