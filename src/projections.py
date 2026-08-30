"""Geração offline dos resultados publicados pelo dashboard.

Este módulo é chamado apenas pelo updater. As sessões públicas do Streamlit
leem o documento persistido e nunca treinam modelos nem executam Monte Carlo.
"""

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import libertadores, store
from .copa import UNKNOWN_ATK, UNKNOWN_DEF, simulate_knockout
from .evaluate import backtest
from .history import load_historical
from .model import PoissonBaseline, make_predictor, outcome_probs
from .scenarios import best_case
from .simulate import SimulationResult, simulate_season

MODEL_KEY = os.environ.get("SIMULATION_MODEL", "ensemble")
N_SIMS = int(os.environ.get("SIMULATION_COUNT", "20000"))
BACKTEST_ROUNDS = int(os.environ.get("BACKTEST_ROUNDS", "6"))


def _historical() -> pd.DataFrame | None:
    try:
        return load_historical()
    except Exception:
        return None


def _json_records(df: pd.DataFrame) -> list[dict]:
    """Converte DataFrame para tipos JSON/BSON seguros."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _league_projection(
    data: dict,
    played: pd.DataFrame,
    future: pd.DataFrame,
    team_ids: list[int],
    predictor,
) -> dict:
    lam_h, lam_a = predictor.predict(future, played)
    result = simulate_season(
        played, future, lam_h, lam_a, team_ids, n_sims=N_SIMS,
        keep_details=True,
    )
    p_home, p_draw, p_away = outcome_probs(lam_h, lam_a)
    fixtures = future.copy()
    fixtures["p_casa"] = p_home
    fixtures["p_empate"] = p_draw
    fixtures["p_fora"] = p_away
    return {
        "team_ids": result.team_ids,
        "pos_dist": result.pos_dist.tolist(),
        "exp_pts": result.exp_pts.tolist(),
        "p_titulo": result.p_titulo.tolist(),
        "p_g4": result.p_g4.tolist(),
        "p_g6": result.p_g6.tolist(),
        "p_z4": result.p_z4.tolist(),
        "fixtures": _json_records(fixtures),
        "cenarios": best_case(result.details, fixtures, result.team_ids),
    }


def _knockout_projection(
    doc: dict | None,
    data: dict,
    played: pd.DataFrame,
    predictor,
    final_jogo_unico: bool = False,
    forca_extra: dict[int, tuple[float, float]] | None = None,
) -> dict | None:
    """Simula o mata-mata de uma competição (documento do ge) a partir da
    fase atual. ``forca_extra`` dá (ataque, defesa) para clubes fora da Série
    A — quem não estiver nem lá entra com a força genérica ``UNKNOWN_*``."""
    if not doc:
        return None
    fase_atual = next((fase for fase in doc["fases"] if fase["atual"]), None)
    if not fase_atual:
        return None
    ties = [chave for chave in fase_atual["chaves"] if chave.get("jogos")]
    if not ties:
        return None
    for tie in ties:
        jogo = tie["jogos"][0]
        if jogo["mandante_id"] is None or jogo["visitante_id"] is None:
            return None  # chave ainda sem os dois clubes definidos

    df = store.matches_df(data)
    serie_a = set(df["casa_id"]) | set(df["fora_id"])
    times_copa: list[int] = []
    nomes: dict[int, str] = {}
    for tie in ties:
        jogo = tie["jogos"][0]
        times_copa += [jogo["mandante_id"], jogo["visitante_id"]]
        nomes[jogo["mandante_id"]] = jogo["mandante"]
        nomes[jogo["visitante_id"]] = jogo["visitante"]

    base = PoissonBaseline().fit(played)
    forca_extra = forca_extra or {}
    pares = [
        (casa, fora)
        for casa in times_copa
        for fora in times_copa
        if casa != fora and casa in serie_a and fora in serie_a
    ]
    conhecidos: dict[tuple[int, int], tuple[float, float]] = {}
    if pares:
        fixtures = pd.DataFrame(
            [{"casa_id": casa, "fora_id": fora} for casa, fora in pares]
        )
        lam_h, lam_a = predictor.predict(fixtures, played)
        conhecidos = {
            par: (float(lam_h[i]), float(lam_a[i]))
            for i, par in enumerate(pares)
        }

    def forca(time: int) -> tuple[float, float]:
        if time in base.atk:
            return base.atk[time], base.dfn[time]
        if time in forca_extra:
            return forca_extra[time]
        return UNKNOWN_ATK, UNKNOWN_DEF

    def lam_pair(casa: int, fora: int) -> tuple[float, float]:
        if (casa, fora) in conhecidos:
            return conhecidos[(casa, fora)]
        atk_h, dfn_h = forca(casa)
        atk_a, dfn_a = forca(fora)
        return (
            float(np.clip(base.mu_home * atk_h * dfn_a, 0.05, 6.0)),
            float(np.clip(base.mu_away * atk_a * dfn_h, 0.05, 6.0)),
        )

    probs = simulate_knockout(
        ties, lam_pair, n_sims=N_SIMS, final_jogo_unico=final_jogo_unico
    )
    fases_seguintes = []
    encontrou_atual = False
    for fase in doc["fases"]:
        if encontrou_atual:
            fases_seguintes.append(fase["nome"])
        if fase["atual"]:
            encontrou_atual = True
    rotulos = fases_seguintes + ["🏆 Título"]
    n_fases = len(next(iter(probs.values())))
    estimados = [
        time for time in times_copa
        if time not in serie_a and time in forca_extra
    ]
    return {
        "probs": {str(time): list(valores) for time, valores in probs.items()},
        "rotulos": rotulos[:n_fases],
        "nomes": {str(time): nome for time, nome in nomes.items()},
        "ties": ties,
        "fase_nome": fase_atual["nome"],
        "fora_serie_a": [time for time in times_copa if time not in serie_a],
        "forca_estimada": estimados,
        "final_jogo_unico": final_jogo_unico,
    }


def _copa_projection(data: dict, played: pd.DataFrame, predictor) -> dict | None:
    return _knockout_projection(store.load_copa(), data, played, predictor)


def _libertadores_projection(
    data: dict, played: pd.DataFrame, predictor
) -> dict | None:
    doc = store.load_libertadores()
    if not doc:
        return None
    return _knockout_projection(
        doc, data, played, predictor,
        final_jogo_unico=True,
        forca_extra=libertadores.forca_por_grupos(doc),
    )


def generate(data: dict | None = None) -> dict:
    """Treina, simula e devolve um snapshot integral pronto para publicação."""
    data = data or store.load_snapshot()
    if not data:
        raise RuntimeError("snapshot da temporada não encontrado")
    df = store.matches_df(data)
    played, future = store.split_played_future(df)
    if future.empty:
        raise RuntimeError("não há jogos futuros para simular")
    team_ids = sorted(set(df["casa_id"]) | set(df["fora_id"]))
    historical = _historical()
    predictor = make_predictor(MODEL_KEY, played, historical)

    league = _league_projection(data, played, future, team_ids, predictor)
    copa = _copa_projection(data, played, predictor)
    liberta = _libertadores_projection(data, played, predictor)
    evaluation = backtest(
        played, n_rounds=BACKTEST_ROUNDS, historical=historical
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_fetched_at": data["fetched_at"],
        "season": data,
        "model_key": MODEL_KEY,
        "model_name": predictor.name,
        "n_sims": N_SIMS,
        "league": league,
        "copa": copa,
        "libertadores": liberta,
        "backtest": _json_records(evaluation),
        "backtest_rounds": BACKTEST_ROUNDS,
    }


def generate_and_save(data: dict | None = None) -> dict:
    doc = generate(data)
    store.save_projection(doc)
    return doc


def simulation_result(doc: dict) -> SimulationResult:
    """Reconstrói o objeto usado pelas visualizações a partir do snapshot."""
    league = doc["league"]
    return SimulationResult(
        team_ids=[int(time) for time in league["team_ids"]],
        pos_dist=np.asarray(league["pos_dist"], dtype=float),
        exp_pts=np.asarray(league["exp_pts"], dtype=float),
        p_titulo=np.asarray(league["p_titulo"], dtype=float),
        p_g4=np.asarray(league["p_g4"], dtype=float),
        p_g6=np.asarray(league["p_g6"], dtype=float),
        p_z4=np.asarray(league["p_z4"], dtype=float),
        n_sims=int(doc["n_sims"]),
    )


def published_simulation(doc: dict) -> dict:
    return {
        "res": simulation_result(doc),
        "fixtures": pd.DataFrame(doc["league"]["fixtures"]),
        "model": doc["model_name"],
    }
