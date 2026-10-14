"""Shared timeline for Maintenance: sound and picture both read these times (seconds)."""

TOTAL = 140.0

# camera push: (time, zoom) keys, plus which area it looks at
CAM = [(0, 1.0), (15, 1.35), (35, 1.8), (55, 2.4), (85, 3.2), (110, 3.4), (140, 3.5)]

TAP_GRIP = 19.0         # tendril reaches the tap handle
TAP_TURN = (24.0, 26.5)  # handle turns a quarter
STREAM = (26.5, 31.0)    # thin stream into the pot, then it stops
POT_NUDGE = (38.0, 41.5)
PANE_PROP = (45.0, 52.0)
GLOVE_FIND = 58.0
REPLICA = (62.0, 86.0)   # the replica grows
HUM = (90.0, 102.0)      # the gardener's tune, remembered
LIFT = (112.0, 116.0)    # the replica lifts the can
POUR = (116.0, 121.0)
LAST_DROP = 127.0
DAWN = (122.0, 136.0)

# the metallophone: (time, midi) sparse notes, a pentatonic around D, later ones closer together
METAL = [(8, 62), (24.0, 69), (30, 66), (39, 64), (46, 62), (51, 69), (60, 74), (64, 71), (68, 69), (72, 74),
         (76, 76), (80, 74), (84, 71), (106, 62), (116.0, 69), (129, 62)]
