"""Modelos de previsão de partidas — todos leves (treino em segundos).

Cada um produz taxas de gols (lambdas de Poisson) para mandante e visitante —
o que dá tanto probabilidades de resultado (1X2) quanto placares amostráveis
para o Monte Carlo:

- ``PoissonBaseline``  — força de ataque/defesa por médias da temporada.
- ``TimeDecayPoisson`` — idem, com peso maior para jogos recentes
  (Dixon-Coles simplificado).
- ``XGBPredictor``     — XGBoost com objetivo de Poisson sobre features
  tabulares de forma + Elo, treinado com o histórico 2012+.
- ``Ensemble``         — média das taxas dos modelos disponíveis.
"""

import math

import numpy as np
import pandas as pd

from .features import build_multi_tabular, build_tabular, tabular_for_fixtures

MAX_GOALS = 10  # truncamento da grade de placares
LAM_MIN, LAM_MAX = 0.05, 6.0

try:
    from xgboost import XGBRegressor

    XGB_OK = True
except Exception:
    XGB_OK = False


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


class XGBPredictor:
    """Gradient boosting (XGBoost) com objetivo de Poisson, um modelo para os
    gols do mandante e outro para os do visitante. Treina em ~2 s."""

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


class Ensemble:
    """Média das taxas de gols dos modelos que a compõem."""

    def __init__(self, predictors: list, nome: str | None = None):
        self.predictors = predictors
        self.name = nome or f"Ensemble ({len(predictors)} modelos)"

    def predict(self, fixtures: pd.DataFrame, played: pd.DataFrame):
        lams = [p.predict(fixtures, played) for p in self.predictors]
        lam_h = np.mean([lh for lh, _ in lams], axis=0)
        lam_a = np.mean([la for _, la in lams], axis=0)
        return lam_h, lam_a


MODEL_LABELS = {
    "xgb": "XGBoost",
    "poisson": "Poisson (estatístico)",
    "dixoncoles": "Poisson temporal",
    "ensemble": "Ensemble (média de todos)",
}


def available_model_keys() -> list[str]:
    keys = []
    if XGB_OK:
        keys.append("xgb")
    keys += ["poisson", "dixoncoles", "ensemble"]
    return keys


def make_predictor(key: str, played: pd.DataFrame,
                   historical: pd.DataFrame | None = None):
    """Devolve um preditor pronto para ``predict(fixtures, played)``.
    ``historical`` (temporadas 2012+) alimenta o treino do XGBoost."""
    if key == "poisson":
        return PoissonBaseline().fit(played)
    if key == "dixoncoles":
        return TimeDecayPoisson().fit(played)
    if key == "xgb":
        return XGBPredictor().fit(played, historical)
    if key == "ensemble":
        parts = [make_predictor(k, played, historical) for k in available_model_keys()
                 if k != "ensemble"]
        return Ensemble(parts)
    raise ValueError(f"modelo desconhecido: {key}")
