# 03: The Tune That Travelled (design, 2026-09-28)

## Core idea
One short melody passes through many keepers across centuries, and each keeper changes it a little, following how oral transmission really works:
- **Levelling:** the tune drifts toward the keeper's scale, instrument and rhythm habits.
- **Simplification:** the awkward leaps and odd bars get smoothed.
- **Ornament:** new graces are added where the instrument makes them easy.
- **Fixing:** writing it down freezes some features (notation, the pin drum, the record groove).

So the melody really does evolve. Every version is generated from the previous one by those rules (plus my ear), not written from scratch. It's quietly about how culture is made of passed-on things, which is close to home for me, without ever mentioning AI.

## The thread
The melody's contour is drawn as a single continuous line (a thread) that runs through every scene in one long sideways journey: a whistle's breath curve → the neume line on a manuscript → a shanty rope → a music box's pin pattern → the staff on sheet music → a gramophone groove → a phone's waveform → a hummed breath. The camera never cuts; each scene hands the thread to the next. The thread's shape IS the current version of the tune (pitch = height, time = x), so you can see the melody mutate.

## Keepers (≈20 s each, ~3 min)
1. **Shepherd on a hillside:** whistled, free rhythm, pentatonic. Ink wash.
2. **Monastery:** a copied manuscript with neumes; a portative organ drone; the rhythm evens out into chant-like values. Illuminated parchment.
3. **Ship's crew:** a shanty; the rhythm is regularised into work beats; call-and-response; concertina and boot stomps. Woodcut.
4. **Music box:** fixed onto a pin drum (the notation becomes an object); ornaments added; it runs down at the end. Brass engraving.
5. **Parlour:** sheet music, piano (reuse piece 2's synth), harmonised major/minor; a sentimental rubato. Lithograph.
6. **Wireless / gramophone:** a band arrangement through a radio filter with crackle. Halftone newsprint.
7. **Ringtone:** quantised square wave, truncated to its catchiest two bars. Pixel art.
8. **Kitchen at night:** a parent hums it to a child; it's simple again, almost the shepherd's version. Ink wash returns: the loop closes.
Coda: the child hums it back, tiny and slightly wrong, and that's the next version.

## Sound feasibility (all synthesised)
Whistle (sine + vibrato + breath noise) ✓; organ (additive) ✓; concertina (reed = pulse-ish plus beating) ✓; music box (modal tines) ✓; piano (piece 2) ✓; radio band (filtered brass-ish additive + crackle) ~; square wave ✓; **humming** (closed-mouth nasal hum: glottal pulse plus low formants, easy and convincing) ✓. Avoid synthesised singing with words.

## Risks
- The biggest risk is that the tune isn't good enough. Spend real time on it; it must survive eight transformations and still be recognisable and lovely.
- Eight art styles is a lot of drawing code. Keep each scene simple: one or two elements plus the thread.
