"""Quais resultados levam cada clube à melhor posição possível na Série A.

A ideia evita o "cenário otimista" ingênuo (vencer tudo e torcer para os
rivais perderem tudo, o que é matematicamente correto e inútil): entre as
temporadas já sorteadas pelo Monte Carlo, recorta as que terminaram melhor
para o clube e mede **o que aconteceu nelas**. Um resultado que aparece em
90% dos bons cenários e em 40% do conjunto completo é o que realmente
distingue o melhor caminho — próprio ou dos rivais.

Roda apenas no updater, junto da simulação; o dashboard lê o resultado
pronto do snapshot publicado.
"""

import numpy as np
import pandas as pd

from .simulate import ScenarioDetails

TOP_FRAC = 0.01        # recorte de melhores cenários por clube
MIN_CENARIOS = 200     # piso amostral para a probabilidade condicional
MAX_RIVAIS = 15        # jogos de terceiros listados por clube

RESULTADOS = ("casa", "empate", "fora")


def _ordem_cenarios(positions: np.ndarray, points: np.ndarray, t: int) -> np.ndarray:
    """Simulações ordenadas do melhor para o pior desfecho do clube ``t``:
    posição final crescente e, no empate, mais pontos primeiro."""
    return np.lexsort((-points[:, t], positions[:, t]))


def _freq(outcomes: np.ndarray) -> np.ndarray:
    """(n_jogos, 3) com a frequência de cada resultado no recorte."""
    return np.stack([(outcomes == r).mean(axis=0) for r in range(3)], axis=1)


def best_case(
    details: ScenarioDetails,
    fixtures: pd.DataFrame,
    team_ids: list[int],
) -> dict:
    """Para cada clube, o recorte de melhores cenários e os resultados que os
    distinguem. Índices em ``jogo`` são posicionais em ``fixtures``."""
    outcomes = details.outcomes
    positions = details.positions
    points = details.points
    n_sims = outcomes.shape[0]
    n_top = min(n_sims, max(MIN_CENARIOS, int(round(n_sims * TOP_FRAC))))

    casa_ids = fixtures["casa_id"].to_numpy()
    fora_ids = fixtures["fora_id"].to_numpy()
    base = _freq(outcomes)  # conjunto completo, para comparação

    analise = {}
    for t, team_id in enumerate(team_ids):
        recorte = _ordem_cenarios(positions, points, t)[:n_top]
        cond = _freq(outcomes[recorte])
        pos_top = positions[recorte, t]
        pos_corte = int(pos_top.max())

        proprio = (casa_ids == team_id) | (fora_ids == team_id)
        em_casa = casa_ids == team_id

        proprios = []
        for j in np.flatnonzero(proprio):
            # do ponto de vista do clube, não do mandante
            vitoria, derrota = (0, 2) if em_casa[j] else (2, 0)
            proprios.append({
                "jogo": int(j),
                "p_vitoria": round(float(cond[j, vitoria]), 4),
                "p_empate": round(float(cond[j, 1]), 4),
                "p_derrota": round(float(cond[j, derrota]), 4),
                "base_vitoria": round(float(base[j, vitoria]), 4),
            })

        # nos jogos alheios, o resultado que mais se destaca no recorte
        alheios = np.flatnonzero(~proprio)
        ganho = cond[alheios] - base[alheios]
        melhor = ganho.argmax(axis=1)
        linhas = np.arange(len(alheios))
        prioridade = np.argsort(-ganho[linhas, melhor])[:MAX_RIVAIS]

        rivais = []
        for k in prioridade:
            j = int(alheios[k])
            r = int(melhor[k])
            rivais.append({
                "jogo": j,
                "resultado": RESULTADOS[r],
                "p_cond": round(float(cond[j, r]), 4),
                "p_base": round(float(base[j, r]), 4),
            })

        analise[str(team_id)] = {
            "n_cenarios": int(n_top),
            "pos_melhor": int(positions[:, t].min()),
            "pos_corte": pos_corte,
            "pos_media": round(float(pos_top.mean()), 2),
            "pts_media": round(float(points[recorte, t].mean()), 1),
            "p_corte": round(float((positions[:, t] <= pos_corte).mean()), 4),
            "proprios": proprios,
            "rivais": rivais,
        }
    return analise
