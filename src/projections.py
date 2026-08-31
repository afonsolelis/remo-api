"""Geração offline dos resultados publicados pelo dashboard.

Este módulo é chamado apenas pelo updater. As sessões públicas do Streamlit
leem o documento persistido e nunca treinam modelos nem executam Monte Carlo.
"""

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import liga, libertadores, serie_d, store
from .copa import UNKNOWN_ATK, UNKNOWN_DEF, simulate_knockout
from .evaluate import backtest
from .history import load_historical
from .model import Ensemble, PoissonBaseline, make_predictor, outcome_probs
from .scenarios import best_case
from .simulate import SimulationResult, simulate_season

MODEL_KEY = os.environ.get("SIMULATION_MODEL", "ensemble")
N_SIMS = int(os.environ.get("SIMULATION_COUNT", "20000"))
BACKTEST_ROUNDS = int(os.environ.get("BACKTEST_ROUNDS", "6"))

# Ligas do ge não têm o histórico 2012+ (o football-data.co.uk só cobre a
# Série A), então o XGBoost treina com poucos jogos e piora o resultado. No
# walk-forward das últimas 6 rodadas da Série B: RPS 0,242 sozinho e 0,220 no
# ensemble com ele, contra 0,213 sem. A liga usa só os modelos estatísticos.
LIGA_MODEL_KEYS = ("poisson", "dixoncoles")


def _historical() -> pd.DataFrame | None:
    try:
        return load_historical()
    except Exception:
        return None


def _json_records(df: pd.DataFrame) -> list[dict]:
    """Converte DataFrame para tipos JSON/BSON seguros."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _league_projection(
    played: pd.DataFrame,
    future: pd.DataFrame,
    team_ids: list[int],
    predictor,
    grupos: list[int] | None = None,
    treino: pd.DataFrame | None = None,
) -> dict:
    # ``treino`` pode incluir a temporada anterior; a tabela simulada parte
    # apenas da campanha corrente
    lam_h, lam_a = predictor.predict(future, played if treino is None else treino)
    result = simulate_season(
        played, future, lam_h, lam_a, team_ids, n_sims=N_SIMS,
        keep_details=True, grupos=grupos,
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
        "pos_dist_grupo": (result.pos_dist_grupo.tolist()
                           if result.pos_dist_grupo is not None else None),
    }


def _knockout_projection(
    doc: dict | None,
    data: dict,
    played: pd.DataFrame,
    predictor,
    final_jogo_unico: bool = False,
    forca_extra: dict[int, tuple[float, float]] | None = None,
    ignora_fase=None,
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
        if encontrou_atual and not (ignora_fase and ignora_fase(fase)):
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


def _liga_projection(chave: str) -> dict | None:
    """Liga de pontos corridos do ge (Série B) com a mesma máquina da Série A.

    Sem o histórico 2012+ — o football-data.co.uk só cobre a Série A —, então
    os modelos treinam apenas com a própria temporada.
    """
    doc = store.load_liga(chave)
    if not doc:
        return None
    df = store.matches_df(doc)
    played, future = store.split_played_future(df)

    # ligas europeias começam em agosto: a temporada passada entra só no
    # treino e no backtest, com rodadas deslocadas para o negativo para não
    # se misturarem às da corrente no walk-forward
    treino = played
    anteriores = doc.get("partidas_anteriores") or []
    if anteriores:
        passado, _ = store.split_played_future(
            store.matches_df({"partidas": anteriores})
        )
        if not passado.empty:
            passado = passado.copy()
            passado["rodada"] = passado["rodada"] - 1000
            treino = pd.concat([passado, played], ignore_index=True)
            treino = treino.sort_values("timestamp").reset_index(drop=True)

    if future.empty or len(treino) < 40:
        # fase encerrada ou recém-começada: só a tabela, sem simulação
        return {
            "liga": {k: v for k, v in doc.items() if k != "partidas_anteriores"},
            "model_name": None, "league": None, "backtest": [],
        }
    team_ids = sorted(set(df["casa_id"]) | set(df["fora_id"]))

    # conferências (MLS): todos os jogos contam, mas a posição é apurada
    # dentro do próprio grupo
    mapa_grupos = doc.get("grupos") or {}
    nomes_grupos = sorted({mapa_grupos[str(t)] for t in team_ids}) if mapa_grupos else []
    grupos = ([nomes_grupos.index(mapa_grupos[str(t)]) for t in team_ids]
              if nomes_grupos else None)

    # o histórico do football-data só entra no backtest: nas ligas medidas
    # até aqui o XGBoost fica atrás dos modelos estatísticos mesmo com ele
    config = liga.LIGAS.get(chave)
    historico = None
    if config and config.historico:
        try:
            historico = load_historical(arquivo=config.historico)
        except Exception:
            historico = None

    predictor = Ensemble(
        [make_predictor(chave_modelo, treino) for chave_modelo in LIGA_MODEL_KEYS],
        nome="Ensemble Poisson (2 modelos)",
    )
    league = _league_projection(played, future, team_ids, predictor, grupos,
                               treino=treino)
    # a temporada anterior serviu ao treino; publicá-la só inflaria o
    # snapshot que o dashboard carrega a cada render
    publicado = {k: v for k, v in doc.items() if k != "partidas_anteriores"}
    return {
        "liga": publicado,
        "model_name": predictor.name,
        "grupos_ordem": nomes_grupos,
        "jogos_treino": int(len(treino)),
        "league": league,
        "backtest": _json_records(
            backtest(treino, n_rounds=BACKTEST_ROUNDS, historical=historico)
        ),
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


def _serie_d_projection(data: dict, played: pd.DataFrame, predictor) -> dict | None:
    doc = store.load_serie_d()
    if not doc:
        return None
    return _knockout_projection(
        doc, data, played, predictor,
        forca_extra=serie_d.forca_por_chaveamento(doc),
        ignora_fase=serie_d.fora_do_titulo,
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

    league = _league_projection(played, future, team_ids, predictor)
    copa = _copa_projection(data, played, predictor)
    liberta = _libertadores_projection(data, played, predictor)
    try:
        serie_d_proj = _serie_d_projection(data, played, predictor)
    except Exception:
        serie_d_proj = None
    evaluation = backtest(
        played, n_rounds=BACKTEST_ROUNDS, historical=historical
    )
    ligas = {}
    for chave in liga.LIGAS:
        try:
            ligas[chave] = _liga_projection(chave)
        except Exception:
            ligas[chave] = None  # a Série A publica mesmo se o ge falhar
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
        "serie_d": serie_d_proj,
        **ligas,
        "backtest": _json_records(evaluation),
        "backtest_rounds": BACKTEST_ROUNDS,
    }


def generate_and_save(data: dict | None = None) -> dict:
    doc = generate(data)
    store.save_projection(doc)
    return doc


def _result_from(league: dict, n_sims: int) -> SimulationResult:
    return SimulationResult(
        team_ids=[int(time) for time in league["team_ids"]],
        pos_dist=np.asarray(league["pos_dist"], dtype=float),
        exp_pts=np.asarray(league["exp_pts"], dtype=float),
        p_titulo=np.asarray(league["p_titulo"], dtype=float),
        p_g4=np.asarray(league["p_g4"], dtype=float),
        p_g6=np.asarray(league["p_g6"], dtype=float),
        p_z4=np.asarray(league["p_z4"], dtype=float),
        n_sims=n_sims,
        pos_dist_grupo=(np.asarray(league["pos_dist_grupo"], dtype=float)
                        if league.get("pos_dist_grupo") else None),
    )


def simulation_result(doc: dict) -> SimulationResult:
    """Reconstrói o objeto usado pelas visualizações a partir do snapshot."""
    return _result_from(doc["league"], int(doc["n_sims"]))


def published_liga(doc: dict, chave: str = "serie_b") -> dict | None:
    """Bloco pronto para a página de uma liga de pontos corridos do ge."""
    bloco = doc.get(chave)
    if not bloco:
        return None
    league = bloco.get("league")  # ausente quando a fase não tem jogo futuro
    return {
        "res": _result_from(league, int(doc["n_sims"])) if league else None,
        "grupos_ordem": bloco.get("grupos_ordem") or [],
        "fixtures": pd.DataFrame(league["fixtures"]) if league else None,
        "cenarios": (league or {}).get("cenarios") or {},
        "model": bloco.get("model_name"),
        "liga": bloco["liga"],
        "backtest": bloco.get("backtest") or [],
    }


def published_simulation(doc: dict) -> dict:
    return {
        "res": simulation_result(doc),
        "fixtures": pd.DataFrame(doc["league"]["fixtures"]),
        "model": doc["model_name"],
    }
