# 01: "Everything Here Is Heard": score and design

## What the rule allows (worked out 2026-09-27)
**Stillness = the 24 Hz overtone series.** A pattern repeating k times per frame sounds at 24k Hz and doesn't move. So the "in tune" world is the harmonic series on 24 Hz, in just intonation:
- k=8 G(192), 9 A, 10 B, 11 C+ (the 11th partial, between C and C#), 12 D, 13 E- (flat), 14 F- (the harmonic 7th), 15 F#, 16 G.
- Triads available (4:5:6 shapes): **G** = 8:10:12 / 16:20:24; **D** = 12:15:18; **B** = 20:25:30; **A** = 36:45:54; "F7-ish" = 28:35:42. **Bm** = 10:12:15 (minor 10:12:15). No C major, no Em: the world is Mixolydian / overtone-flavoured, with a chromatic-mediant **B major** as the magic chord.
- Bass on hills: k=2 (48 Hz), 3 (72, D), 4 (96, G), 5 (120, B), 6 (144, D), 7 (168, F-).
- Progressions: G–Bm–D–G; G–F7–G (mixolydian sigh); G → B major (the "light changes" moment).

**Motion = detuning (checked numerically, and corrected).** Anything scrolling left at v px/frame sounds at ratio 1920/(1920−v) of its still pitch, and its spacing shrinks by the same ratio; this is independent of k. But smooth-looking motion needs v well under the pattern's period, so it only buys a few cents: v=10 → +9 cents, v=30 → +27 cents. Larger v aliases (wagon-wheel): moving exactly one period per frame looks still (and is just a different integer k).
- So motion = slight detune = beating/chorus against still things. **Things that move together stay in tune with each other; something moving against a still world beats against it.** Tension = motion, resolution = stillness, as a real acoustic fact.
- A "flight = whole-tone modulation" is NOT possible smoothly (I thought it was; the check disproved it). Key changes happen by the landscape re-forming (counts changing), not by panning.

**Other mappings**
- Prominence = loudness. Soft edges = mellow; hard edges = bright or buzzy.
- A static lone object = a 24 Hz-periodic hum with its silhouette as timbre (keep figures soft, or use it as a drone on purpose).
- Rain (random streaks per frame) = noise; density = loudness. Lightning = a broadband crack.
- Text is sound: the title card buzzes with the timbre of its letters.
- The town skyline is *stacked* periodic shapes (houses every 1920/k1, towers every 1920/k2 ...), so the town is a chord. Lit windows = upper partials.

## Arc (~3:00, 4320 frames)
1. **0:00–0:20 Teaching the rule.** Black and silent. One soft vertical line: a low 24 Hz throb. It splits into 2, 4, 8 lines; a tone emerges out of the throb as the count rises. The viewer learns "count = pitch" without a word.
2. **0:20–0:45 Dawn.** The lines lean and soften into the horizon; the sky gradient comes up (silent: gradients make no sound). Hills rise: the bass (k=4, G). Far mountains add a quiet fifth.
3. **0:45–1:25 Morning: the town and the birds.** The skyline builds house by house (the chord G). Birds arrive; their number is the melody. A tune in the overtone scale, over G–Bm–D–G.
4. **1:25–1:55 Weather.** Clouds (soft, nearly silent) darken the light. Wind: the birds get blown off-station (drift = out of tune). Rain = hiss; density swells. Lightning cracks. The bass slips to F7 (k=7): the hills get more humps, sharper and stormier.
5. **1:55–2:15 Clearing (the climax).** The rain stops. The wind drops; everything that was drifting (beating, out of tune) slows and settles into stillness, and the beating resolves into clean intervals you can hear locking in. The hills re-form from 7 humps to 5, the town re-stacks, and we land on **B major** (the mediant): new light, a new colour. The birds come back and hover still. The loudest, fullest moment.
6. **2:15–2:45 Night.** Still again. Windows light up across the town (upper partials, a shimmering chord). Stars (faint high sparkle). The birds roost; the melody falls to the root.
7. **2:45–3:00 Coda.** Things go out one by one; the hills flatten to a line; the line splits back to a single soft stroke; silence. End card: text that itself buzzes, fading.

## Art direction
Flat paper-theatre layers (Charley Harper / Mary Blair / McLaren's Synchromy colour fields) with depth from atmospheric colour, not perspective. Gradients everywhere they're free (they're silent). Silent paper grain (zero column mean). A palette that changes with the harmony: G = warm dawn gold, Bm = dusk rose, D = clear blue, B major = unreal teal-violet, F7 storm = grey-green.
Keep everything that sounds deliberate. If it doesn't need to make sound, make it a gradient or a column-balanced texture.

## Honesty statement (for the post)
"Every sound in this film is the picture. Each frame is 1/24 s of audio; each pixel column is one sample; the column's brightness is the sample. The soundtrack was decoded from the finished frames by a 30-line script. Only a fixed gain and a 20 Hz high-pass were applied."
