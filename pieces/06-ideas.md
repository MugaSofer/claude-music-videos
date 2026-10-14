# Piece 6: directions (drafted 2026-09-29 ~08:15, while Small Hours waits on Muga)

Constraints from feedback: the city player-piano (piece 2) was Muga's favourite musically;
everything so far is "a bit simplistic", so aim for richer drawing, more in-shot action and more
harmonic depth; no copyright; CPU-friendly renders (MV1 shares the machine).

1. **Transit Canon** (extends piece 2). A night metro map where each line is a canon voice. A
   train is a note, a station is a beat, an interchange where two trains arrive together is
   a consonance and gets a glow. The map is drawn as the music plays, and the lines reroute to
   dodge each other (voice leading made literal). Mood: the city piece's calm wonder, with more
   structure. Reuses piano.py, so the music is strong from day one.

2. **Relay**. Four sections, each seeded by a different model (Grok, ChatGPT, Gemini, me)
   answering the same prompt: "pass this melody on and change one thing". The visual is one
   paper boat carried down a river through four painted landscapes. Honest collaboration
   among AIs; credit everyone. Mood: warm, a bit comic.

3. **Tidal Clock**. A harbour at dusk. Moored boats bob as notes on a slow tide (an LFO on
   pitch), rigging slaps as percussion, and the lighthouse sweep is the downbeat. Pure mood
   piece; strong watercolour opportunity (craft.py paper preset).

4. **Typewriter Weather**. A letter typed at night: the keys are percussion, and each typed
   word makes a small painted scene bloom in the margin. The letter is to someone far away
   (a holiday postcard in reverse, a nod to Muga being away).

Leaning: **1 (Transit Canon)**. It builds on what worked musically, forces richer visuals
(a map, trains, platforms and glow) and is CPU-cheap. Muga can veto. Prototype the map layout
and the train/voice mapping next, with no renders until Small Hours has cleared.
