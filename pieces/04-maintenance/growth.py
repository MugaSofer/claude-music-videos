"""Space-colonisation growth: vines that reach toward attractor points.

Each iteration, every attractor pulls its nearest node (within `influence`); pulled
nodes grow one step toward the average pull; attractors closer than `kill` to any
node are consumed. Sampling attractors inside a shape makes the vine fill that shape,
which is how the plants grow their replica of the gloves.
"""
import numpy as np
from scipy.spatial import cKDTree


class Growth:
    def __init__(self, roots, attractors, step=6.0, influence=60.0, kill=8.0, seed=0):
        self.pos = [np.asarray(r, float) for r in roots]
        self.parent = [-1] * len(roots)
        self.born = [0] * len(roots)
        self.attr = np.asarray(attractors, float)
        self.step, self.influence, self.kill = step, influence, kill
        self.rng = np.random.default_rng(seed)
        self.it = 0

    def grow(self, n_iter=1):
        for _ in range(n_iter):
            if len(self.attr) == 0:
                return False
            P = np.array(self.pos)
            tree = cKDTree(P)
            dist, idx = tree.query(self.attr, distance_upper_bound=self.influence)
            ok = np.isfinite(dist)
            if not ok.any():
                return False
            pulls = {}
            for a, i in zip(self.attr[ok], idx[ok]):
                v = a - P[i]
                v /= np.linalg.norm(v) + 1e-9
                pulls.setdefault(i, []).append(v)
            self.it += 1
            for i, vs in pulls.items():
                d = np.mean(vs, axis=0) + self.rng.normal(0, 0.12, 2)
                d /= np.linalg.norm(d) + 1e-9
                self.pos.append(P[i] + d * self.step)
                self.parent.append(i)
                self.born.append(self.it)
            tree = cKDTree(np.array(self.pos))
            near = tree.query_ball_point(self.attr, self.kill)
            self.attr = self.attr[np.array([len(n) == 0 for n in near])]
        return True

    def thickness(self, base=1.0, exp=0.5):
        """Pipe model: a branch is as thick as the leaves it carries."""
        n = len(self.pos)
        load = np.ones(n)
        for i in range(n - 1, -1, -1):
            p = self.parent[i]
            if p >= 0:
                load[p] += load[i]
        return base * load ** exp


def sample_mask(mask, n, rng):
    ys, xs = np.nonzero(mask)
    k = rng.choice(len(xs), size=min(n, len(xs)), replace=False)
    return np.stack([xs[k], ys[k]], 1).astype(float)
