# Surprise Me: thirteen short music videos, made in code by Claude

In September and October 2026, Muga gave a Claude Code session (Claude Opus 5.5) an open brief: make a music
video, *surprise me*. This repository holds the code for what came out of it: thirteen short pieces, each one
generated entirely by Python. The code writes the notes, synthesises the sound and draws every frame. There are
no image models, and except for one piece (below) no music models.

Muga was away for most of the build and checked in now and then from their phone, so most of the work happened
unattended. Many of the fixes in the log come from Muga's notes. `PROGRESS.md` is the full build log, written as
it happened, dead ends and all.

The videos themselves aren't in this repo. Posted so far:
[Passacaglia in D minor](https://youtu.be/5AjoNm4lUOI) ·
[Murmuration](https://youtu.be/Ha2gBUcjyak) ·
[Signal](https://youtu.be/FBcnZ7Ciri0) ·
[Small Hours](https://youtu.be/WompK2lEBjY) ·
[Relay](https://youtu.be/eF58RMXFI4I).

*(The working title for this project was "Music Video 2": Music Video 1 being [Many Turns](https://github.com/MugaSofer/many-turns), which another Claude session was making in parallel on the same machine. That's where the "MV1"/"MV2" in the notes and folder names comes from.)*

## The pieces

| # | Title | What it is |
|---|---|---|
| 01 | Drawn Sound | optical sound: the picture's pixel columns *are* the waveform, so moving the camera changes the music |
| 02 | Player Piano City | a four-voice tempo canon (3:4:5:6) drawn as parallax piano rolls that converge |
| 03 | The Tune That Travelled | one folk tune passed down the centuries, re-sung by each keeper, from shepherd to ringtone to a parent humming in a kitchen |
| 04 | Maintenance | an abandoned glasshouse where the plants keep the gardener's routines (concept by Grok) |
| 05 | [Small Hours](https://youtu.be/WompK2lEBjY) | a song (music by Suno, lyrics by Claude) over a paper-cut night city |
| 06 | Transit Canon | a metro map where each line is a looping voice; all four trains meet at Central at 2:00 |
| 07 | [Relay](https://youtu.be/eF58RMXFI4I) | a tune passed between Grok, ChatGPT and Gemini, each changing one thing (errors kept Gemini out that day; asked again weeks later, Gemini resolved the last bar) |
| 08 | Tidal Clock | a simulated harbour: boats ring when the waves lift them |
| 09 | Typewriter Weather | a letter typed at night; the keys are the drums |
| 10 | Clockwork | a gear train of polyrhythmic ostinati that winds down to a stop |
| 11 | [Signal](https://youtu.be/FBcnZ7Ciri0) | a lighthouse and a boat talk in Morse; the letters are the melody |
| 12 | [Passacaglia in D minor](https://youtu.be/5AjoNm4lUOI) | an eight-bar ground under ten variations, drawn as tree rings |
| 13 | [Murmuration](https://youtu.be/Ha2gBUcjyak) | Reich-style phasing pianos; 3,500 simulated starlings (boids) part and rejoin as the pianos drift |

Each piece lives in `pieces/NN-name/` with its `design.md`. Superseded versions are kept next to the current ones
(`*_v2.py` and so on) so the history stays readable. `CATALOGUE.md` says which version is current.

## Running it

You need Python 3.11+, `numpy`, `scipy`, `Pillow` and `soundfile`, and `ffmpeg` on your PATH. Each piece has
`render_*.sh` scripts. Renders write to a hard-coded work directory (`E:\Claude\music-video-2-work\NN\`) because of
the machine they were made on, so change that path before you run anything. Some renders take hours; several pieces
have a `spot.py` or a `smoke` mode for rendering single frames quickly.

These assets are **not included**. Download them yourself if you want to rebuild the pieces that use them:
- Piece 03's hum: ["Humming C D A for alexggqs" by drotzruhn](https://freesound.org/s/439504/) (Freesound, CC0),
  re-pitched by TD-PSOLA in `pieces/03-tune-travelled/realhum.py`.
- Two superseded drafts (07 v2 and 11 v2) used the Salamander Grand Piano V3 samples by Alexander Holm (CC-BY 3.0).
  The final versions use the synth piano in `pieces/02-player-piano/piano.py`.
- Piece 05's audio is a Suno track, so it isn't here. The lyrics and the style prompt are in
  `pieces/05-small-hours/lyrics.md`.

## Credits

- Code, music (except piece 05's audio), lyrics, most of the pictures, and this README: Claude (Opus 5.5), in
  Claude Code.
- Brief, feedback, bug-spotting: Muga. Most of the fixes in the log started as Muga's notes.
- Idea for piece 04: Grok. Piece 07: Grok and ChatGPT each changed one thing in the tune (errors kept Gemini out; see `pieces/07-relay/relay.md` for the turn Gemini took later); the hands
  drawn for each model in the video are mine.
- **The painters.** Five Claude subagents (Opus 5.5) did the figure painting, each briefed in prose and working
  in code like the rest:
  - *The Tune That Travelled*: one painter redrew the shepherd and collie, the parent humming over a mug, and the
    child asleep while the parent watches from the doorway. It also invented `Painter.lit()` (blur a shape's mask,
    take its gradient as a surface normal, light it from each lamp). That technique shades every figure in the
    piece, and I built this week's fixes on top of it.
  - *Small Hours*: four painters made all eight vignettes. One painted the baker and the night bus; one the nurse
    counting breaths and the fox under the OPEN LATE sign; one the trucker singing in her cab and the new dad at
    4am; and one the road-line painter and the last lit window in the tower.

  They each left a note about their work in a folder this project shared between Claude sessions. The notes are
  in [`painters/`](painters/), unedited.
- Research on craft techniques (`research-craft.md`): a Claude research subagent.
- The flocking in piece 13 follows Reynolds' boids, Ballerini et al. 2008 (seven topological neighbours) and
  Hemelrijk's StarDisplay.
- A sibling project, made in parallel on the same machine by another Claude session:
  [Many Turns](https://github.com/MugaSofer/many-turns), an Odyssey song as a turning Greek vase.

## Licence

The code is MIT licensed (`LICENSE`). The writing (the design notes, `PROGRESS.md`, the lyrics and the other
Markdown files) is CC BY 4.0 (`LICENSE-docs.md`).
