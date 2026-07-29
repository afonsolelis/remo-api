"""Backtest walk-forward: para cada rodada recente, treina os modelos apenas
com os jogos anteriores e avalia as previsões nos jogos daquela rodada.

Métricas (quanto menor, melhor, exceto acurácia):
- log loss  — penaliza probabilidade baixa no resultado que aconteceu;
- RPS       — ranked probability score, padrão para 1X2 no futebol
  (leva em conta que "vitória" está mais perto de "empate" que de "derrota");
- acurácia  — % de acerto do resultado mais provável.
"""

import numpy as np
import pandas as pd

from .model import (
    XGB_OK,
    Ensemble,
    MODEL_LABELS,
    PoissonBaseline,
    TimeDecayPoisson,
    XGBPredictor,
    outcome_probs,
)

MIN_TRAIN_GAMES = 60


def backtest(played: pd.DataFrame, n_rounds: int = 5,
             historical: pd.DataFrame | None = None) -> pd.DataFrame:
    """Replay das últimas ``n_rounds`` rodadas disputadas — todos os modelos
    retreinam a cada rodada só com o passado (são leves, leva segundos)."""
    rodadas = sorted(played["rodada"].unique())[-n_rounds:]
    preds: dict[str, list] = {}
    reais: list[int] = []

    for rodada in rodadas:
        train = played[played["rodada"] < rodada]
        test = played[played["rodada"] == rodada]
        if len(train) < MIN_TRAIN_GAMES or test.empty:
            continue
        models = {}
        if XGB_OK:
            models["xgb"] = XGBPredictor().fit(train, historical)
        models["poisson"] = PoissonBaseline().fit(train)
        models["dixoncoles"] = TimeDecayPoisson().fit(train)
        models["ensemble"] = Ensemble(list(models.values()))
        reais.extend(
            0 if m.gols_casa > m.gols_fora else 1 if m.gols_casa == m.gols_fora else 2
            for m in test.itertuples()
        )
        for key, model in models.items():
            lh, la = model.predict(test, train)
            ph, pe, pa = outcome_probs(lh, la)
            preds.setdefault(key, []).append(np.stack([ph, pe, pa], axis=1))

    y = np.asarray(reais)
    rows = []
    for key, chunks in preds.items():
        p = np.clip(np.vstack(chunks), 1e-9, 1.0)  # (n_jogos, 3)
        p = p / p.sum(axis=1, keepdims=True)
        logloss = float(-np.log(p[np.arange(len(y)), y]).mean())
        obs = np.eye(3)[y]
        rps = float((np.cumsum(p - obs, axis=1)[:, :2] ** 2).sum(axis=1).mean() / 2)
        acc = float((p.argmax(axis=1) == y).mean())
        rows.append({
            "chave": key,
            "Modelo": MODEL_LABELS[key],
            "Jogos": len(y),
            "Acurácia 1X2": acc,
            "Log loss": logloss,
            "RPS": rps,
        })

    df = pd.DataFrame(rows).sort_values("RPS").reset_index(drop=True)
    df.insert(0, "Ranking", df.index + 1)
    return df
