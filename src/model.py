"""Modelos de previsão de partidas.

Todos produzem taxas de gols (lambdas de Poisson) para mandante e visitante —
o que dá tanto probabilidades de resultado (1X2) quanto placares amostráveis
para o Monte Carlo:

- ``PoissonBaseline``  — força de ataque/defesa por médias da temporada.
- ``TimeDecayPoisson`` — idem, com peso maior para jogos recentes
  (Dixon-Coles simplificado).
- ``RNNPredictor``     — rede recorrente (LSTM ou GRU) que lê a sequência dos
  últimos K jogos de cada equipe (regressão de Poisson).
- ``XGBPredictor``     — XGBoost com objetivo de Poisson sobre features
  tabulares de forma.
- ``Ensemble``         — média das taxas dos modelos disponíveis.
"""

import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .features import (
    K,
    N_FEAT,
    build_multi_tabular,
    build_multi_training,
    build_tabular,
    build_training_data,
    current_sequences,
    tabular_for_fixtures,
)
from .store import MODELS_DIR

HISTORY_FILE = MODELS_DIR / "history.jsonl"

MAX_GOALS = 10  # truncamento da grade de placares
LAM_MIN, LAM_MAX = 0.05, 6.0

try:
    import torch
    import torch.nn as nn

    TORCH_OK = True
except Exception:  # torch ausente -> app segue com os demais modelos
    TORCH_OK = False

try:
    from xgboost import XGBRegressor

    XGB_OK = True
except Exception:
    XGB_OK = False


def _rnn_file(arch: str):
    return MODELS_DIR / f"{arch}.pt"


def _metrics_file(arch: str):
    return MODELS_DIR / f"metrics-{arch}.json"


def outcome_probs(lam_h: np.ndarray, lam_a: np.ndarray):
    """P(vitória mandante), P(empate), P(vitória visitante) por Poisson."""
    lam_h = np.atleast_1d(np.asarray(lam_h, dtype=float))
    lam_a = np.atleast_1d(np.asarray(lam_a, dtype=float))
    g = np.arange(MAX_GOALS + 1)
    fact = np.array([math.factorial(i) for i in g], dtype=float)
    # pmf shape: (n_jogos, n_gols)
    ph = np.exp(-lam_h[:, None]) * lam_h[:, None] ** g[None, :] / fact[None, :]
    pa = np.exp(-lam_a[:, None]) * lam_a[:, None] ** g[None, :] / fact[None, :]
    joint = ph[:, :, None] * pa[:, None, :]  # (n, gols_casa, gols_fora)
    p_home = np.tril(np.ones((MAX_GOALS + 1,) * 2), -1)[None]  # casa > fora
    p_draw = np.eye(MAX_GOALS + 1)[None]
    home = (joint * p_home).sum(axis=(1, 2))
    draw = (joint * p_draw).sum(axis=(1, 2))
    return home, draw, 1.0 - home - draw


# ------------------------------------------------------------- estatísticos

class PoissonBaseline:
    """Ataque/defesa multiplicativos com encolhimento para a média da liga."""

    name = "Poisson (estatístico)"

    def _weights(self, played: pd.DataFrame) -> np.ndarray:
        return np.ones(len(played))

    def fit(self, played: pd.DataFrame):
        w = self._weights(played)
        gc = played["gols_casa"].to_numpy(dtype=float)
        gf = played["gols_fora"].to_numpy(dtype=float)
        self.mu_home = np.average(gc, weights=w)
        self.mu_away = np.average(gf, weights=w)
        gpg = np.average((gc + gf) / 2, weights=w)

        atk, dfn = {}, {}
        casa_ids = played["casa_id"].to_numpy()
        fora_ids = played["fora_id"].to_numpy()
        for t in set(casa_ids) | set(fora_ids):
            em_casa = casa_ids == t
            fora = fora_ids == t
            wt = np.concatenate([w[em_casa], w[fora]])
            meus = np.concatenate([gc[em_casa], gf[fora]])
            deles = np.concatenate([gf[em_casa], gc[fora]])
            jogos = em_casa.sum() + fora.sum()
            shrink = jogos / (jogos + 5)  # encolhimento com poucos jogos
            atk[t] = shrink * np.average(meus, weights=wt) / gpg + (1 - shrink)
            dfn[t] = shrink * np.average(deles, weights=wt) / gpg + (1 - shrink)
        self.atk, self.dfn = atk, dfn
        return self

    def predict(self, fixtures: pd.DataFrame, played: pd.DataFrame):
        lam_h = np.array(
            [self.mu_home * self.atk.get(m.casa_id, 1) * self.dfn.get(m.fora_id, 1)
             for m in fixtures.itertuples()]
        )
        lam_a = np.array(
            [self.mu_away * self.atk.get(m.fora_id, 1) * self.dfn.get(m.casa_id, 1)
             for m in fixtures.itertuples()]
        )
        return np.clip(lam_h, LAM_MIN, LAM_MAX), np.clip(lam_a, LAM_MIN, LAM_MAX)


class TimeDecayPoisson(PoissonBaseline):
    """Poisson com decaimento exponencial: jogos recentes pesam mais
    (à la Dixon-Coles). ``half_life_days`` controla a memória."""

    name = "Poisson temporal (recentes pesam mais)"

    def __init__(self, half_life_days: float = 90.0):
        self.half_life_days = half_life_days

    def _weights(self, played: pd.DataFrame) -> np.ndarray:
        ts = played["timestamp"].to_numpy(dtype=float)
        idade_dias = (ts.max() - ts) / 86400
        return np.power(0.5, idade_dias / self.half_life_days)


# ------------------------------------------------------------------- RNNs

if TORCH_OK:

    class MatchRNN(nn.Module):
        """Codifica a forma recente das duas equipes e prevê taxas de gols."""

        def __init__(self, arch: str = "lstm", n_feat: int = N_FEAT, hidden: int = 32):
            super().__init__()
            rnn_cls = {"lstm": nn.LSTM, "gru": nn.GRU}[arch]
            self.rnn = rnn_cls(n_feat, hidden, batch_first=True)
            self.head = nn.Sequential(
                nn.Linear(2 * hidden, 64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, 2),
            )

        def _encode(self, seq):
            _, h = self.rnn(seq)
            if isinstance(h, tuple):  # LSTM devolve (h, c)
                h = h[0]
            return h[-1]

        def forward(self, seq_casa, seq_fora):
            out = self.head(torch.cat([self._encode(seq_casa), self._encode(seq_fora)], dim=1))
            lam = nn.functional.softplus(out) + 0.05
            return lam[:, 0], lam[:, 1]


class RNNPredictor:
    """LSTM ou GRU treinada nos resultados da temporada."""

    def __init__(self, arch: str = "lstm", hidden: int = 32):
        assert arch in ("lstm", "gru")
        self.arch = arch
        self.hidden = hidden
        self.model = None
        self.metrics: dict | None = None

    @property
    def name(self) -> str:
        return f"{self.arch.upper()} (rede neural)"

    def fit(self, played: pd.DataFrame, historical: pd.DataFrame | None = None,
            epochs: int = 500, lr: float = 1e-3, patience: int = 60, seed: int = 42):
        """Treina com validação temporal (15% de jogos mais recentes de fora).

        Com ``historical``, treina também nas temporadas passadas, com peso
        decrescente por ano de distância (perda de Poisson ponderada).
        """
        if not TORCH_OK:
            raise RuntimeError("PyTorch não está instalado.")
        torch.manual_seed(seed)
        np.random.seed(seed)

        if historical is not None and len(historical):
            X_h, X_a, y, w = build_multi_training(historical, played)
        else:
            X_h, X_a, y, _ = build_training_data(played)
            w = np.ones(len(y), dtype=np.float32)
        n = len(y)
        if n < 40:
            raise RuntimeError(f"Poucos jogos para treinar ({n}); aguarde mais rodadas.")

        n_val = max(int(n * 0.15), 10)
        tr = slice(0, n - n_val)
        va = slice(n - n_val, n)
        t = lambda a: torch.tensor(a)

        model = MatchRNN(self.arch, hidden=self.hidden)
        opt = torch.optim.Adam(model.parameters(), lr=lr)
        loss_el = nn.PoissonNLLLoss(log_input=False, full=True, reduction="none")
        w_tr = torch.tensor(w[tr])

        best_val, best_state, best_epoch = float("inf"), None, 0
        hist_train, hist_val = [], []
        for epoch in range(epochs):
            model.train()
            opt.zero_grad()
            lh, la = model(t(X_h[tr]), t(X_a[tr]))
            per_jogo = loss_el(lh, t(y[tr, 0])) + loss_el(la, t(y[tr, 1]))
            loss = (per_jogo * w_tr).sum() / w_tr.sum()
            loss.backward()
            opt.step()

            model.eval()
            with torch.no_grad():
                lh_v, la_v = model(t(X_h[va]), t(X_a[va]))
                val = (loss_el(lh_v, t(y[va, 0])) + loss_el(la_v, t(y[va, 1]))).mean().item()
            hist_train.append(loss.item())
            hist_val.append(val)
            if val < best_val - 1e-4:
                best_val, best_epoch = val, epoch
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
            elif epoch - best_epoch > patience:
                break

        model.load_state_dict(best_state)
        model.eval()
        self.model = model

        # acurácia 1X2 na validação vs. chute "sempre mandante"
        with torch.no_grad():
            lh_v, la_v = model(t(X_h[va]), t(X_a[va]))
        ph, pd_, pa = outcome_probs(lh_v.numpy(), la_v.numpy())
        pred = np.argmax(np.stack([ph, pd_, pa]), axis=0)
        real = np.where(y[va, 0] > y[va, 1], 0, np.where(y[va, 0] == y[va, 1], 1, 2))
        self.metrics = {
            "arch": self.arch,
            "n_samples": n,
            "n_hist": int((w < 1.0).sum()),
            "n_val": n_val,
            "epochs_run": len(hist_train),
            "best_epoch": best_epoch,
            "best_val_nll": best_val,
            "val_acc_1x2": float((pred == real).mean()),
            "naive_home_acc": float((real == 0).mean()),
            "loss_train": hist_train,
            "loss_val": hist_val,
        }
        return self

    def predict(self, fixtures: pd.DataFrame, played: pd.DataFrame):
        """Lambdas para cada jogo futuro, usando a forma atual das equipes."""
        seqs = current_sequences(played)
        zero = np.zeros((K, N_FEAT), dtype=np.float32)
        X_h = np.stack([seqs.get(m.casa_id, zero) for m in fixtures.itertuples()])
        X_a = np.stack([seqs.get(m.fora_id, zero) for m in fixtures.itertuples()])
        with torch.no_grad():
            lh, la = self.model(torch.tensor(X_h), torch.tensor(X_a))
        return (
            np.clip(lh.numpy().astype(float), LAM_MIN, LAM_MAX),
            np.clip(la.numpy().astype(float), LAM_MIN, LAM_MAX),
        )

    def save(self):
        MODELS_DIR.mkdir(exist_ok=True)
        torch.save(
            {"state_dict": self.model.state_dict(), "arch": self.arch,
             "hidden": self.hidden, "k": K},
            _rnn_file(self.arch),
        )

    @staticmethod
    def available(arch: str) -> bool:
        return TORCH_OK and _rnn_file(arch).exists()

    @classmethod
    def load(cls, arch: str) -> "RNNPredictor":
        ckpt = torch.load(_rnn_file(arch), weights_only=True)
        p = cls(arch=ckpt.get("arch", arch), hidden=ckpt["hidden"])
        p.model = MatchRNN(p.arch, hidden=p.hidden)
        p.model.load_state_dict(ckpt["state_dict"])
        p.model.eval()
        return p


def train_daily(played: pd.DataFrame, arch: str = "lstm",
                historical: pd.DataFrame | None = None) -> dict:
    """Treina, salva o modelo do dia e registra as métricas no histórico."""
    p = RNNPredictor(arch=arch).fit(played, historical)
    p.save()

    hoje = datetime.now().strftime("%Y-%m-%d")
    daily_dir = MODELS_DIR / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": p.model.state_dict(), "arch": arch, "hidden": p.hidden, "k": K},
        daily_dir / f"{arch}-{hoje}.pt",
    )

    metrics = {"date": hoje,
               "trained_at": datetime.now(timezone.utc).isoformat(),
               **p.metrics}
    _metrics_file(arch).write_text(json.dumps(metrics))
    # histórico de treinos (sem as curvas, uma linha por execução)
    record = {k: v for k, v in metrics.items() if not k.startswith("loss_")}
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return metrics


# ---------------------------------------------------------------- XGBoost

class XGBPredictor:
    """Gradient boosting (XGBoost) com objetivo de Poisson, um modelo para os
    gols do mandante e outro para os do visitante."""

    name = "XGBoost"

    _params = dict(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        min_child_weight=5,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="count:poisson",
        random_state=42,
        n_jobs=2,
    )

    def fit(self, played: pd.DataFrame, historical: pd.DataFrame | None = None):
        if not XGB_OK:
            raise RuntimeError("xgboost não está instalado.")
        if historical is not None and len(historical):
            X, y_h, y_a, w = build_multi_tabular(historical, played)
        else:
            X, y_h, y_a = build_tabular(played)
            w = np.ones(len(X), dtype=np.float32)
        if len(X) < 40:
            raise RuntimeError(f"Poucos jogos para treinar ({len(X)}).")
        self.m_casa = XGBRegressor(**self._params).fit(X, y_h, sample_weight=w)
        self.m_fora = XGBRegressor(**self._params).fit(X, y_a, sample_weight=w)
        return self

    def predict(self, fixtures: pd.DataFrame, played: pd.DataFrame):
        X = tabular_for_fixtures(fixtures, played)
        return (
            np.clip(self.m_casa.predict(X).astype(float), LAM_MIN, LAM_MAX),
            np.clip(self.m_fora.predict(X).astype(float), LAM_MIN, LAM_MAX),
        )


# ---------------------------------------------------------------- ensemble

class Ensemble:
    """Média das taxas de gols dos modelos que a compõem."""

    def __init__(self, predictors: list):
        self.predictors = predictors
        self.name = f"Ensemble ({len(predictors)} modelos)"

    def predict(self, fixtures: pd.DataFrame, played: pd.DataFrame):
        lams = [p.predict(fixtures, played) for p in self.predictors]
        lam_h = np.mean([lh for lh, _ in lams], axis=0)
        lam_a = np.mean([la for _, la in lams], axis=0)
        return lam_h, lam_a


# ---------------------------------------------------------------- registro

MODEL_LABELS = {
    "lstm": "LSTM (rede neural)",
    "gru": "GRU (rede neural)",
    "xgb": "XGBoost",
    "poisson": "Poisson (estatístico)",
    "dixoncoles": "Poisson temporal",
    "ensemble": "Ensemble (média de todos)",
}


def available_model_keys() -> list[str]:
    keys = []
    if TORCH_OK:
        keys += ["lstm", "gru"]
    if XGB_OK:
        keys.append("xgb")
    keys += ["poisson", "dixoncoles", "ensemble"]
    return keys


def make_predictor(key: str, played: pd.DataFrame,
                   historical: pd.DataFrame | None = None):
    """Devolve um preditor pronto para ``predict(fixtures, played)``.

    Para as RNNs, usa o modelo do dia salvo em disco quando existir (treinado
    pela atualização diária); senão treina em memória. ``historical`` (jogos
    de temporadas passadas) alimenta o treino das RNNs e do XGBoost.
    """
    if key == "poisson":
        return PoissonBaseline().fit(played)
    if key == "dixoncoles":
        return TimeDecayPoisson().fit(played)
    if key == "xgb":
        return XGBPredictor().fit(played, historical)
    if key in ("lstm", "gru"):
        if RNNPredictor.available(key):
            return RNNPredictor.load(key)
        return RNNPredictor(arch=key).fit(played, historical)
    if key == "ensemble":
        parts = [make_predictor(k, played, historical) for k in available_model_keys()
                 if k != "ensemble"]
        return Ensemble(parts)
    raise ValueError(f"modelo desconhecido: {key}")


def load_metrics(arch: str = "lstm") -> dict | None:
    f = _metrics_file(arch)
    if f.exists():
        return json.loads(f.read_text())
    return None


def load_history() -> list[dict]:
    """Todas as execuções de treino já registradas (uma por linha)."""
    if not HISTORY_FILE.exists():
        return []
    out = []
    for line in HISTORY_FILE.read_text().splitlines():
        if line:
            rec = json.loads(line)
            rec.setdefault("arch", "lstm")
            out.append(rec)
    return out
