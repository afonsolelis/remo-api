"""Teste da análise de melhor cenário com um campeonato sintético."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.scenarios import best_case
from src.simulate import simulate_season


def _liga(n_times=6):
    """Turno único: todo mundo joga contra todo mundo uma vez."""
    jogos = [(c, f) for c in range(n_times) for f in range(n_times) if c != f]
    return pd.DataFrame([{"casa_id": c, "fora_id": f} for c, f in jogos])


def test_recorte_e_probabilidades():
    team_ids = list(range(6))
    fixtures = _liga()
    played = pd.DataFrame(columns=["casa_id", "fora_id", "gols_casa", "gols_fora"])
    n = len(fixtures)
    lam_h = np.full(n, 1.4)
    lam_a = np.full(n, 1.1)

    res = simulate_season(played, fixtures, lam_h, lam_a, team_ids,
                          n_sims=4000, keep_details=True)
    assert res.details is not None
    assert res.details.outcomes.shape == (4000, n)
    assert set(np.unique(res.details.outcomes)) <= {0, 1, 2}

    analise = best_case(res.details, fixtures, team_ids)
    assert set(analise) == {str(t) for t in team_ids}

    for team_id in team_ids:
        a = analise[str(team_id)]
        # o recorte é o piso amostral, já que 1% de 4000 = 40 < 200
        assert a["n_cenarios"] == 200
        assert a["pos_melhor"] <= a["pos_corte"]
        assert a["pos_melhor"] >= 1
        assert a["pos_media"] <= a["pos_corte"]
        assert 0 < a["p_corte"] <= 1

        # todos os jogos do próprio clube entram; nenhum jogo alheio entra
        proprios = {p["jogo"] for p in a["proprios"]}
        esperado = set(np.flatnonzero(
            (fixtures["casa_id"] == team_id) | (fixtures["fora_id"] == team_id)
        ).tolist())
        assert proprios == esperado
        assert not proprios & {r["jogo"] for r in a["rivais"]}

        for p in a["proprios"]:
            soma = p["p_vitoria"] + p["p_empate"] + p["p_derrota"]
            assert abs(soma - 1.0) < 1e-6, soma
            # nos melhores cenários o clube vence mais do que na média geral
            assert p["p_vitoria"] >= p["base_vitoria"]

        # os jogos alheios listados são os de maior ganho sobre a base
        ganhos = [r["p_cond"] - r["p_base"] for r in a["rivais"]]
        assert ganhos == sorted(ganhos, reverse=True)
        assert all(g > 0 for g in ganhos)


def test_detalhes_desligados_por_padrao():
    team_ids = list(range(4))
    fixtures = _liga(4)
    played = pd.DataFrame(columns=["casa_id", "fora_id", "gols_casa", "gols_fora"])
    n = len(fixtures)
    res = simulate_season(played, fixtures, np.full(n, 1.3), np.full(n, 1.0),
                          team_ids, n_sims=500)
    assert res.details is None


if __name__ == "__main__":
    test_recorte_e_probabilidades()
    test_detalhes_desligados_por_padrao()
    print("ok — todos os testes passaram")
