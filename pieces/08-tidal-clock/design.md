# Tidal Clock: design (piece 8)

**The rule:** the sea is the composer. Nothing is sequenced by hand; every sound comes from a
simulated harbour.

- **Swell:** a sum of a few deep-water wave trains (dispersion w = sqrt(g k)) travelling across
  the harbour from the mouth (left) to the quay (right). Trains with close wavelengths beat, so
  waves arrive in **sets**, and sets are phrases.
- **Boats and bells:** about 12 moored boats sit at fixed x positions. Each rings its bell (one
  note) when the water under it rises through that boat's threshold, then can't ring again for a
  short refractory time. Pitch follows position: near the mouth is low, by the quay high, on a
  D-major-pentatonic ladder. Because a crest travels left to right, **every wave plays a rising
  arpeggio**, at the speed the physics gives it. Heavy boats (low bells) have high thresholds, so
  they only ring on the big waves of a set.
- **Rigging:** when a boat rolls hard (steep local slope), its halyard slaps the mast with a soft
  metallic tick, a percussion texture that comes and goes with the sea state.
- **Tide:** the swell amplitude rises for two thirds of the piece (the sea gets up at dusk), then
  eases into a still night. Density follows it: sparse, then busy sets, then single bells.
- **Lighthouse:** its beam sweeps every 12 s. As it crosses the harbour there's a very low bell
  and the water lights up under the beam.

**Picture:** a side-on harbour at dusk, then night, drawn in watercolour washes (craft.py paper
presets, soft edges, pigment granulation). A layered sea surface is drawn from the same wave
function that makes the sound, so what you see bobbing is literally what you hear. Each boat's
masthead lamp flares when its bell rings. The lighthouse is on the left headland and its beam
sweeps the frame. Gulls sit on the quay and lift off in the busiest set. At the end the water
stills to a mirror, and the last bell rings with its reflection.
