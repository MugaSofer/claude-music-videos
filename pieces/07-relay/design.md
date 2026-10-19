# Relay: design

**The idea.** A melody really was passed between AI models (see relay.md). The film shows the
tune travelling downriver on a paper boat. At each stage a different hand reaches in, changes
exactly one thing and lets it go. It's the true provenance of the tune, told gently and credited
honestly, including the hand that didn't manage it.

## Music (84 bpm; 8 bars = 32 beats = 22.9 s)
| section | hand | what plays | ~time |
|---|---|---|---|
| 1 | Claude (seed) | solo piano, bare: the tune once, then again with a low drone | 0-46 |
| 2 | Grok | plucked strings (Karplus-Strong) take over; the changed note (bar 7 B4) rings as a bell | 46-92 |
| 3 | ChatGPT | a warm reed/organ pad joins; the last note becomes C5 and hangs unresolved (fermata) | 92-138 |
| 4 | Gemini | the hand reaches, hesitates, withdraws. The tune plays once, unchanged, as a ghost in reverb over the drone. A held breath | 138-161 |
| 5 | Claude (last) | the final rest becomes A4 and the tune loops. It becomes a ROUND: each version (seed, Grok, ChatGPT, Gemini=seed-ish, last) enters 2 bars apart on its own instrument, layered, then thins to the last hand alone | 161-215 |

The changed note in each section is the event: a slight swell, a bell doubling and a visual glow.

## Picture (paper-cut layers, craft.py `day`, then `night` presets)
- A river scrolls right to left, with parallax banks: reeds, willows, stones, fields and a town.
  Time of day moves with the hands: dawn (seed), bright morning (Grok), gold afternoon
  (ChatGPT), blue fog at dusk (Gemini), night (the last hand, the round).
- **The boat** is a folded paper boat carrying the melody as a string of 32 small paper
  lanterns, one per beat. Each note's lantern lights as it sounds; height = pitch, like a
  melody line strung along a thread.
- **The hands**: at each section a hand reaches in from above the frame, each drawn in its own
  style (I drew all of them, in a style I picked for each model; the models only changed the tune). Grok is angular and dark with a spark. ChatGPT is rounded and soft teal. Gemini is
  made of faint gradient stars: it reaches, hovers and withdraws, and the fog thickens. Claude is
  warm terracotta, drawn in ink. The hand plucks one lantern, and a new one in the hand's colour
  replaces it.
- **The round**: in the finale Claude's hand ties the lantern string's end to its start. The
  string becomes a ring and lifts off the boat, and the ring's copies (one per version, each
  showing its changed lantern in its hand's colour) circle like a slow carousel over the dark
  river. The last image is a single ring of lanterns reflected in black water.
- Captions, small and hand-lettered: "Claude", "Grok: 'cleaner, more resolved'", "ChatGPT: 'a
  little unresolved tension'", "Gemini: (dropped the baton)" (v4: "an error each time; the tune went on unchanged"), "Claude: 'so it can be passed around
  forever'".
