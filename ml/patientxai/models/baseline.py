"""Transparent baseline: discrete-time survival logistic regression.

Each patient contributes one row per year at risk after the index visit
(person-period format). The hazard in year y is

    logit h_y = b_y + w . x

where x are standardised last-observation / trend features. The cumulative risk
at horizon k is 1 - prod_{y<=k}(1 - h_y), which is monotone in k by construction
and uses censored follow-up correctly (a patient censored in year y contributes
only the years fully observed).

Attribution is exact for this model on the hazard-logit scale: the contribution
of feature j is w_j * x_j relative to the training mean (x is standardised).
Uncertainty comes from refitting on bootstrap resamples of the training patients.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

from ..config import HORIZONS

K = len(HORIZONS)


def person_period(X: np.ndarray, event: np.ndarray, time: np.ndarray):
    rows, ys = [], []
    for i in range(len(X)):
        if event[i]:
            last = int(min(max(np.ceil(time[i]), 1), K))
        else:
            last = int(min(np.floor(time[i]), K))
        for y in range(1, last + 1):
            onehot = np.zeros(K)
            onehot[y - 1] = 1
            rows.append(np.concatenate([X[i], onehot]))
            ys.append(1 if (event[i] and y == last) else 0)
    return np.asarray(rows), np.asarray(ys)


def _design(X: np.ndarray) -> np.ndarray:
    """Expand each patient to K rows (one per year) for prediction."""
    n = len(X)
    rep = np.repeat(X, K, axis=0)
    eye = np.tile(np.eye(K), (n, 1))
    return np.hstack([rep, eye])


class DiscreteTimeLogistic:
    name = "Discrete-time logistic regression (baseline)"

    def __init__(self, C: float = 0.5, n_bootstrap: int = 30, seed: int = 0):
        self.C = C
        self.n_bootstrap = n_bootstrap
        self.seed = seed
        self.model: LogisticRegression | None = None
        self.boot: list[LogisticRegression] = []

    def _fit_one(self, X, event, time):
        Xp, yp = person_period(X, event, time)
        m = LogisticRegression(C=self.C, max_iter=3000, fit_intercept=False)
        m.fit(Xp, yp)
        return m

    def fit(self, X, event, time):
        self.model = self._fit_one(X, event, time)
        rng = np.random.default_rng(self.seed)
        self.boot = []
        for _ in range(self.n_bootstrap):
            idx = rng.integers(0, len(X), len(X))
            self.boot.append(self._fit_one(X[idx], event[idx], time[idx]))
        return self

    @staticmethod
    def _curve(m: LogisticRegression, X: np.ndarray) -> np.ndarray:
        h = m.predict_proba(_design(X))[:, 1].reshape(len(X), K)
        return 1 - np.cumprod(1 - h, axis=1)

    def predict_risk(self, X: np.ndarray) -> np.ndarray:
        return self._curve(self.model, X)

    def predict_members(self, X: np.ndarray) -> np.ndarray:
        """Bootstrap member predictions, shape [B, N, K]."""
        return np.stack([self._curve(m, X) for m in self.boot])

    @property
    def weights(self) -> np.ndarray:
        return self.model.coef_[0][:-K]

    def attributions(self, x: np.ndarray) -> np.ndarray:
        """Exact contribution of each feature to the hazard logit (same for every year)."""
        return self.weights * x
