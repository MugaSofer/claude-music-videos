"""The tune, and how it changes hands.

Degrees are scale steps from the tonic: 0 = do, 2 = mi, 4 = sol, 7 = do',
negative = below (−3 = low sol). Durations are in beats. The "parlour" version
(3/4, 16 bars) is the canonical one; the others are derived from it or from their
predecessor by transmission rules.
"""

# 16 bars of 3/4. A (bars 1-8) asks, B (9-16) reaches higher and comes home.
PARLOUR = [
    (-3, 1),                                   # pickup: low sol
    (0, 2), (2, 1),                            # 1  do - mi
    (4, 2), (5, 1),                            # 2  sol - la
    (4, 1), (2, 1), (0, 1),                    # 3  sol mi do
    (1, 3),                                    # 4  re (held: a question)
    (2, 2), (1, 1),                            # 5  mi - re
    (0, 1), (-2, 1), (-3, 1),                  # 6  do la, sol,
    (-2, 1), (0, 1), (1, 1),                   # 7  la, do re
    (0, 2),                                    # 8  do (breath, leaves a beat for the pickup)
    (4, 1),                                    #    pickup: sol
    (2, 2), (4, 1),                            # 9  mi - sol
    (7, 2), (6, 1),                            # 10 do' - ti   (the high point)
    (5, 1), (4, 1), (2, 1),                    # 11 la sol mi
    (4, 3),                                    # 12 sol (held)
    (5, 1.5), (4, 0.5), (2, 1),                # 13 la. sol mi
    (1, 1), (0, 1), (-2, 1),                   # 14 re do la,
    (-3, 1), (0, 1), (1, 1),                   # 15 sol, do re
    (0, 3),                                    # 16 do
]

MAJOR = [0, 2, 4, 5, 7, 9, 11]
PENTA_MAJOR = [0, 2, 4, 7, 9]


def semis(deg, scale=MAJOR):
    o, i = divmod(deg, 7)
    return 12 * o + scale[i]


def beats(t):
    return sum(d for _, d in t)


if __name__ == '__main__':
    print('parlour beats:', beats(PARLOUR), '=', beats(PARLOUR) / 3, 'bars of 3/4')
    print('range (degrees):', min(d for d, _ in PARLOUR), 'to', max(d for d, _ in PARLOUR))
