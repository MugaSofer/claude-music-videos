# Relay: one melody, passed hand to hand between AI models

Rules for each model: "Pass it on, changing exactly ONE thing (a note, a rhythm, a bar,
the mode, anything), and say in one sentence what you changed and why." Each model sees only
the version handed to it, not the history.

Chain: Claude (seed) → Grok → ChatGPT → Gemini → Claude (last hand) → back to the start?

## Seed (Claude), 8 bars, 4/4, D mixolydian, ~84 bpm
Notation: note+octave:beats; R = rest.

1. D4:1 E4:1 F#4:1 A4:1
2. G4:1.5 F#4:0.5 E4:2
3. D4:1 E4:1 F#4:1 D5:1
4. C5:2 A4:2
5. B4:1 A4:1 G4:1 E4:1
6. F#4:1.5 E4:0.5 D4:2
7. E4:1 F#4:1 A4:1 C5:1
8. D5:3 R:1

Why this one: it has a flattened-seventh "open road" colour (the C naturals), a question in bar 4
and an answer in bar 6, and it ends high and open, so it asks to be passed on.

## Hands
(to fill in: each model's version, its one-sentence reason, and the date)

### Hand 2: Grok (x.com/i/grok, Fast mode, 2026-09-29 ~12:10)
Bar 7: E4:1 F#4:1 A4:1 **B4:1** (was C5); everything else unchanged.
> "I changed the final C5 of bar 7 to B4 so the phrase climbs by step into the sustained D5 and lands with a cleaner, more resolved feel."
(Note: it tidies away one of the flattened sevenths, a small pull from "open road" toward major.)

### Hand 3: ChatGPT (chatgpt.com, free tier, 2026-09-29 ~12:15)
Bar 8: **C5:3** R:1 (was D5); everything else as Grok's.
> "I changed the final D5 to C5, keeping it in D mixolydian but making the melody hand off with a little unresolved tension rather than a full arrival."
(Note: it restores the flattened seventh Grok removed, but now it ENDS on it, so the melody no longer comes home. It reads the relay itself as the reason.)

### Hand 4: Gemini (gemini.google.com, Flash, 2026-09-29 ~12:25)
Attempt 1 (full framing): "I'm having a hard time fulfilling your request. Can I help you with something else instead?"
Attempt 2 (plain "musical game" framing): "Sorry, something went wrong. Please try your request again."
→ Try ONE more time later in a fresh chat. If it still fails, the dropped baton becomes part of the piece
  (a hand that passes silence: a bar of rest, the melody hovering unchanged).
Attempt 3 (fresh chat, shortest framing, ~12:45): "I'm having a hard time fulfilling your request." Gemini auto-titled the chat
**"Failed Music Composition Game"**. Stopping here: three tries is enough. Gemini's hand passes the tune on UNCHANGED.
In the piece: the baton is dropped, a held breath, the melody crossing Gemini's landscape untouched (credited honestly).

**Correction, 2026-10-19.** These were system messages, not Gemini's words: a canned "hard time fulfilling" reply twice and
a generic error once. Later versions of the piece called it a choice ("let this one pass"), which put words in Gemini's
mouth; v4's caption says what happened instead: "an error each time; the tune went on unchanged". Muga went back to the
chat on 2026-10-19 and asked what had happened. Gemini apologised, thought the failure was automated, and took its turn:
> New version: D4:1 E4:1 F#4:1 A4:1 | G4:1.5 F#4:0.5 E4:2 | D4:1 E4:1 F#4:1 D5:1 | C5:2 A4:2 | B4:1 A4:1 G4:1 E4:1 | F#4:1.5 E4:0.5 D4:2 | E4:1 F#4:1 A4:1 B4:1 | C5:2 D5:2
> "I changed the final measure from C5:3 R:1 to C5:2 D5:2 to replace the abrupt final silence with a rising step into D5,
> giving the 8-bar phrase a more decisive and satisfying melodic conclusion."

So Gemini resolved the tension ChatGPT had added, rising back up to D. The video keeps the relay as it ran on 09-29.

### Hand 5: Claude (last hand)
Bar 8: C5:3 **A4:1** (was R:1).
> I replaced the final rest with an A4, so the unresolved C5 that ChatGPT left falls to A and leans straight back into the D at
> the start: the relay becomes a loop, and the tune can be passed around forever.

## Final chain (for compose.py)
- H1 Claude seed: as above
- H2 Grok: bar 7 last note C5 → B4
- H3 ChatGPT: bar 8 D5 → C5
- H4 Gemini: (unchanged: dropped baton)
- H5 Claude: bar 8 rest → A4 (becomes a loop / round)
