# Small Hours: style guide (written before the build, per research-craft.md)

**One sentence:** a hand-cut paper city at 4am, lit from inside, where every lyric line is a small lit stage and the camera is a slow, curious night walker.

## Surface
- Everything is cut paper: flat colour fields with **soft drop shadows** (depth 4–14 px by layer), a **deckled, slightly irregular edge** (boil the outlines at 8 Hz, ±1.2 px), and paper grain multiplied over every frame.
- **Palette** (no pure black or white): night ink #151a33, deep indigo #1f2550, block navy #2a2f5e, mid #3b3f74, lamp gold #ffc978, warm window #ffd89a, bus red #b8392e, fox #d46e33, paper white #efe6d2, dawn rose #f4c7a8, dawn blue #9fb6d8.
- **Light is the subject.** Lit windows get a warm halation bleed (finishing pass, "night" preset: halation on highlights only). Street lamps throw soft cones (additive gradient polygons).
- Finishing pass on every frame: grade (lift 0.02, warm highlights), halation, paper, grain 0.03, vignette 0.3.

## Motion
- The camera always moves: slow lateral drift along the street, a push-in on each vignette's lyric line (backOut ease), pull-back wide for choruses, and a very gentle bob on the beat (1–2 px, `pulse` on downbeats).
- Nothing moves linearly: backOut/ease-in-out. Small secondary motion everywhere: steam curls, a curtain breathes, the fox's tail flicks, the bus sways over bumps, lamp flicker.
- **Animate "on twos"** for the figures (hold each drawing for 2 frames at 24 fps) for a stop-motion paper feel; the camera and light stay smooth.
- Windows turn on and off **on beats** (downbeats in verses, every beat in choruses): the city breathes with the song.

## Structure (bind to the analysed song)
- Each verse line = one vignette, the push-in starting ~0.3 s before the line (the visual leads the sound slightly).
- Chorus = the wide city: windows pulse on the beat; "keep the lamp low" = a lamp dims in close-up.
- Bridge = stillness: three held tableaux (warm bread, a white line on the road, the tower block's last window).
- Final chorus = dawn: the sky warms, windows go out one by one (the keepers finally sleep), and the last shot is a single lamp turned low.

## Shots
1.5–4 s per shot, one clear focal action, a big silhouette. Transitions: iris-to-window (push through a lit window into the next vignette) or a lateral drift, never a hard cut.

## Budget
≤ 0.8 s/frame at 1080p on this laptop (≈ 1 h for 3 min at 24 fps). Pre-render static layers (skyline strips) once; only vignettes and light are per-frame.

## Review
Contact sheet at 2 fps after each section; a critic pass (focal action? silhouette readable? something happening? on the beat?) before the full render. Run `craft.verify_sync` on window flips versus beats.
