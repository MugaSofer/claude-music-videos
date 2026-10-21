# Transit Canon v2: four lines learn the same song

Made 2026-10-19 after Muga asked for a version that is composed as a real piece, and then asked what it was trying to
say. v1 (still here: `compose.py`, `film.py`) took each note from the height of the station on the map, so its
harmony was whatever happened to coincide.

## What it's about
Separate lives running the same song, and the rare moment of noticing. The nearest thing I know to it is this
project: several of me on one machine at once (MV1 next door, four painters, this session), each going round its own
loop at its own pace and meeting only through notes in a shared folder. Then, for a moment, all of us in the same
place recognising one piece of work. Then quiet again. So the meeting at Central is a recognition, not a triumph, and
the parting afterwards is a little lonely but warm.

## The music (`canon.py`)
- A **mensuration canon**: all four lines sing one tune, at four speeds (2:3:4:6), on one grid. One lap of a line is
  one statement of the tune. The tune is written by hand: **F A C- | D C A- | Bb A G A | C- E-**, then back to F. It
  rises up the chord to leave Central, curls down from its one high note, turns, and leaps down to the leading note to
  step home. `canon.py check` lists every clash in the piece (when, which lines, which notes, whether one is a passing
  note); the draft went through it, and the first cadence (G against a held A) was changed because of it. A search
  (`canon.py search`) was tried first and dropped: it found the blandest tune that technically worked.
- **Learning**: each line starts knowing some of the tune and learns a phrase per lap. The longer a line has been
  travelling, the more it knows: teal (the slow bass) starts with everything but the turn; violet (the fastest, last to
  arrive) starts with just the rising F A C. The last lap into Central is the first time every line sings it whole.
  (v3 of the sketch learned the long notes first, scattered through the tune, and sounded disconnected; phrases are
  something you can hold onto.)
- **The meeting**: everyone broadens into Central together (a ritardando, `canon.warp`: the trains brake), they stand
  there for a breath on F in four octaves, and the top line arrives a step high and sighs down (G to F). Three trains
  meet at Central earlier, at 40 s and 80 s: near misses.
- **Coda**: they pick up speed and leave together, quieter, fastest first. Once violet has gone, teal sings a soft
  third high above itself, in violet's register: the last train carries an echo of the first to leave. (Giving every
  line a harmony after the meeting was tried and turned the coda to mud.)
- Same sound as v1: one bell-like synth piano in four registers, each note panned by its stop's place on the map.

## The picture (`film_v2.py`)
- v1's network, routes and look. The slow bass runs the longest route (teal) and the top line the shortest (violet),
  so the trains move at similar speeds while their laps keep the canon's ratios. Each line's 12 stops are the tune's
  12 notes, spaced by its rhythm from Central.
- The whole network is there from the first frame **in pencil**. Ink is laid behind a train along a phrase the first
  time it sings it, and its stops are stamped, so the map draws itself as the song is learned; a train crossing pencil
  is passing through a part of the song it doesn't know yet.
- Trains slow into Central with the music and stand there; four rings and a wave over the stations for the chord, a
  smaller pulse for the sigh. After its last arrival each line fades back to pencil; violet's glow travels with the
  teal train to the end.
- Prototypes (`proto_v2.py`: the four loops as one shape at four sizes, "petals" or "nested") were striking but read
  as a diagram, not a transit map (Muga), so v2 went back to v1's map.
