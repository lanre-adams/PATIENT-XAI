"""Longitudinal model: GRU encoder over irregular visit sequences + static context,
with a discrete-time survival head over the 1..5-year horizons.

Why a GRU and not a Transformer: sequences are short (3-13 visits) and the cohort is
small, so a single-layer recurrent encoder with explicit time-gap and missingness
inputs is the simplest defensible sequence model. A temporal Transformer is listed
in the roadmap for the PhD, where longer and richer sequences justify it.

Uncertainty: a deep ensemble (independently initialised members). The spread of the
members is an approximate measure of epistemic uncertainty, not a calibrated
confidence interval for the individual's true risk.

Attribution: integrated gradients (Sundararajan et al., 2017) on the ensemble-mean
cumulative risk at a chosen horizon, giving per-visit, per-feature attributions that
sum (approximately) to f(x) - f(baseline).
"""

from __future__ import annotations

import copy

import numpy as np
import torch
from torch import nn

from ..config import HORIZONS

K = len(HORIZONS)


class TrajectoryGRU(nn.Module):
    def __init__(self, n_features: int, n_static: int, hidden: int = 32, dropout: float = 0.1):
        super().__init__()
        self.inp = nn.Linear(n_features, hidden)
        self.gru = nn.GRU(hidden, hidden, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden + n_static, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, K))

    def encode(self, X: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """Latent patient state z_t at the index (last observed) visit."""
        out, _ = self.gru(torch.relu(self.inp(X)))
        idx = (lengths - 1).clamp(min=0).view(-1, 1, 1).expand(-1, 1, out.size(-1))
        return out.gather(1, idx).squeeze(1)

    def forward(self, X, lengths, S):
        z = self.encode(X, lengths)
        return self.head(torch.cat([z, S], dim=1))  # hazard logits per year


def survival_targets(event: np.ndarray, time: np.ndarray):
    y = np.zeros((len(event), K), dtype=np.float32)
    m = np.zeros((len(event), K), dtype=np.float32)
    for i, (e, t) in enumerate(zip(event, time, strict=True)):
        if e:
            last = int(min(max(np.ceil(t), 1), K))
            y[i, last - 1] = 1
        else:
            last = int(min(np.floor(t), K))
        m[i, :last] = 1
    return y, m


def survival_nll(logits, y, m):
    """Discrete-time survival negative log-likelihood (censoring via the mask)."""
    bce = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="none")
    return (bce * m).sum() / m.sum().clamp(min=1)


def risk_from_logits(logits: torch.Tensor) -> torch.Tensor:
    return 1 - torch.cumprod(1 - torch.sigmoid(logits), dim=1)


def train_member(data_tr, data_va, *, n_features, n_static, hidden, epochs, patience, lr, seed):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = TrajectoryGRU(n_features, n_static, hidden)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    Xtr, Ltr, Str, ytr, mtr = (torch.as_tensor(a) for a in data_tr)
    Xva, Lva, Sva, yva, mva = (torch.as_tensor(a) for a in data_va)
    best, best_state, wait, history = np.inf, None, 0, []
    gen = torch.Generator().manual_seed(seed)
    for _ in range(epochs):
        model.train()
        perm = torch.randperm(len(Xtr), generator=gen)
        for b in range(0, len(perm), 128):
            i = perm[b:b + 128]
            opt.zero_grad()
            loss = survival_nll(model(Xtr[i], Ltr[i], Str[i]), ytr[i], mtr[i])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(survival_nll(model(Xva, Lva, Sva), yva, mva))
        history.append(vl)
        if vl < best - 1e-4:
            best, best_state, wait = vl, copy.deepcopy(model.state_dict()), 0
        else:
            wait += 1
            if wait >= patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, history


class GRUEnsemble:
    name = "GRU deep ensemble (longitudinal)"

    def __init__(self, members: list[TrajectoryGRU]):
        self.members = members

    @torch.no_grad()
    def predict_members(self, X, lengths, S) -> np.ndarray:
        X, L, S = (torch.as_tensor(np.array(a)) for a in (X, lengths, S))
        return np.stack([risk_from_logits(m(X, L, S)).numpy() for m in self.members])

    def predict_risk(self, X, lengths, S) -> np.ndarray:
        return self.predict_members(X, lengths, S).mean(0)

    @torch.no_grad()
    def embed(self, X, lengths) -> np.ndarray:
        X, L = torch.as_tensor(np.array(X)), torch.as_tensor(np.array(lengths))
        return self.members[0].encode(X, L).numpy()

    def integrated_gradients(self, x: np.ndarray, length: int, s: np.ndarray,
                             horizon_idx: int, steps: int = 32):
        """IG attributions for one patient. Baseline: all-zero standardised inputs
        (training-mean continuous values, no treatment, nothing measured).

        Returns (attr_seq[length, F], attr_static[S], f_x, f_baseline).
        """
        x = torch.as_tensor(x[None, :length])
        s = torch.as_tensor(s[None])
        L = torch.tensor([length])
        x0, s0 = torch.zeros_like(x), torch.zeros_like(s)
        alphas = torch.linspace(1.0 / steps, 1.0, steps).view(-1, 1, 1)
        xs = (x0 + alphas * (x - x0)).requires_grad_(True)
        ss = (s0 + alphas.view(-1, 1) * (s - s0)).requires_grad_(True)
        Ls = L.repeat(steps)
        out = torch.stack([risk_from_logits(m(xs, Ls, ss))[:, horizon_idx] for m in self.members]).mean(0)
        gx, gs = torch.autograd.grad(out.sum(), [xs, ss])
        attr_x = ((x - x0) * gx.mean(0, keepdim=True))[0].detach().numpy()
        attr_s = ((s - s0) * gs.mean(0, keepdim=True))[0].detach().numpy()
        with torch.no_grad():
            f_x = float(np.mean([risk_from_logits(m(x, L, s))[0, horizon_idx] for m in self.members]))
            f_0 = float(np.mean([risk_from_logits(m(x0, L, s0))[0, horizon_idx] for m in self.members]))
        return attr_x, attr_s, f_x, f_0

    def state_dicts(self):
        return [m.state_dict() for m in self.members]
