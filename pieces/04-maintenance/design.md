# 04: Maintenance (design sketch, 2026-09-28). The core image is Grok's; credit it.

## Origin
When I asked other models for ideas, Grok (x.com/i/grok, 2026-09-27) described an orbital greenhouse above a dead planet. Its plants keep performing maintenance they no longer understand. At its core is an empty chair with folded work gloves, and the plants have grown living replicas of the gloves and are slowly filling them. "The plants are civil servants of a dead brief." The gloves image is the best single image anyone offered me, so this piece is built around it, credited.

## My take (what I'd change)
- **Not space.** Smaller and closer: one abandoned glasshouse, a potting bench, an empty stool, a pair of canvas work gloves. The grand setting dilutes the gloves.
- **Growth is the animation.** Differential growth / space-colonisation algorithms (vines that branch toward "attractors") and phyllotaxis. The plants tend the place: they wind round the tap and turn it, prop up the broken pane, sort pots by size. Rituals, faithfully kept, with no one to keep them for.
- **The gloves.** A tendril finds the gloves; leaves grow into the exact shape of the gloves beside them, a green replica. At the very end, the replica gloves lift a watering can a centimetre and pour: the job continues.
- **One continuous camera move** (Grok's rule): a slow push from outside, through a broken pane, to the bench.

## Sound: the opposite of pieces 1–3
- Near-silent ("lowercase", per Grok's pointer to Bernhard Günter): dripping, creaking glass, wind through a crack, the tick of growth, all synthesised.
- A detuned, slowly beating metallophone (gamelan *ombak*, a pair tuned slightly apart), sparse, like the building's pulse.
- **Twelve seconds of a hummed lullaby** near the end: reuse piece 3's hum synth, *and it's piece 3's tune.* The gardener used to hum it. This ties the set together quietly: a keeper we never met.

## Why it belongs in the set
Pieces 1–3 are about making sound visible, structure shared, and things passed on. This one is about what's left when the passing-on stops, and it still has one thread back to the tune. It's the sombre fourth movement.

## Risks
Growth sims are slow to render at 1080p; plan for lower-res simulation with an upscaled, painterly render. It's the easiest piece to make boring: keep it under 2:30, and make each ritual a clear, legible little event.

## Storyboard (~2:20)
1. **0–15 s, exterior, grey dawn.** An overgrown glasshouse, one pane broken. Wind, a drip. The camera begins a slow push in. Near silence.
2. **15–35 s, ritual 1 (the tap).** Through the broken pane. A tendril winds round a brass tap handle and turns it a quarter; a drip becomes a thin stream into a pot, then stops. One metallophone pair sounds at the turn.
3. **35–55 s, rituals 2 and 3.** A vine nudges a stray pot back into a perfectly aligned row. A stem props a cracked pane. Growth ticks; sparse metallophone.
4. **55–85 s, the bench.** A stool; canvas gloves on it; a watering can. A tendril finds the gloves, curls round them, and beside them begins to grow the replica. Slow, the centre of the piece. The metallophone's beating (ombak) swells a little.
5. **85–110 s.** The replica is complete. Close camera. Faintly, as if the building remembers it: **12 s of piece 3's tune, hummed** (first phrase only). Everything else drops away.
6. **110–130 s.** The replica gloves lift the watering can a centimetre and tip it; water falls on one seedling. A single drop.
7. **130–140 s.** The light warms (dawn proper). A last drip; black.

## Sound palette (all synthesised)
Drips (resonant ping), wind (filtered noise, gusts), glass creak (narrow noise band gliding), growth ticks (tiny clicks, dense when growth is fast), tap squeak, pot scrape. The **metallophone pair**: modal bars, the second tuned ~5 Hz above, so every note beats. The **hum**: piece 3's `instruments.hum` singing the tune's first phrase.
