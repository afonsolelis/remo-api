"""Simulação Monte Carlo do restante do Brasileirão.

Cada jogo futuro recebe taxas de gols (lambdas) do modelo escolhido; os
placares são amostrados de Poisson milhares de vezes e a tabela final é
recalculada em cada simulação (pontos, vitórias, saldo e gols pró como
desempate). O resultado é a distribuição de posições finais de cada clube.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ScenarioDetails:
    """Recorte bruto de cada temporada simulada (só o updater consome)."""

    outcomes: np.ndarray         # (n_sims, n_jogos) int8: 0 casa, 1 empate, 2 fora
    positions: np.ndarray        # (n_sims, n_times) posição final
    points: np.ndarray           # (n_sims, n_times) pontos finais


@dataclass
class SimulationResult:
    team_ids: list[int]          # ordem das linhas das matrizes abaixo
    pos_dist: np.ndarray         # (n_times, n_times) P(time t terminar na posição p+1)
    exp_pts: np.ndarray          # pontos finais esperados
    p_titulo: np.ndarray
    p_g4: np.ndarray
    p_g6: np.ndarray
    p_z4: np.ndarray
    n_sims: int
    details: ScenarioDetails | None = None   # só quando ``keep_details``


def simulate_season(
    played: pd.DataFrame,
    fixtures: pd.DataFrame,
    lam_h: np.ndarray,
    lam_a: np.ndarray,
    team_ids: list[int],
    n_sims: int = 5000,
    seed: int = 7,
    fixed_scores: dict[int, tuple[int, int]] | None = None,
    keep_details: bool = False,
) -> SimulationResult:
    """``fixed_scores`` trava placares escolhidos pelo usuário: mapeia o índice
    posicional do jogo em ``fixtures`` para (gols_casa, gols_fora) — esses jogos
    deixam de ser sorteados e a simulação fica condicionada a eles.

    ``keep_details`` devolve também o desfecho de cada jogo em cada cenário,
    consumido pela análise de melhor cenário (``src/scenarios.py``)."""
    rng = np.random.default_rng(seed)
    n_t = len(team_ids)
    idx = {t: i for i, t in enumerate(team_ids)}

    # ponto de partida: campanha já disputada
    pts0 = np.zeros(n_t)
    win0 = np.zeros(n_t)
    sg0 = np.zeros(n_t)
    gp0 = np.zeros(n_t)
    for m in played.itertuples():
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        c, f = idx[m.casa_id], idx[m.fora_id]
        gp0[c] += gc
        gp0[f] += gf
        sg0[c] += gc - gf
        sg0[f] += gf - gc
        if gc > gf:
            pts0[c] += 3
            win0[c] += 1
        elif gc < gf:
            pts0[f] += 3
            win0[f] += 1
        else:
            pts0[c] += 1
            pts0[f] += 1

    n_f = len(fixtures)
    casa_idx = np.array([idx[m.casa_id] for m in fixtures.itertuples()])
    fora_idx = np.array([idx[m.fora_id] for m in fixtures.itertuples()])

    # amostra todos os placares de uma vez: (n_sims, n_jogos)
    g_casa = rng.poisson(lam_h[None, :], size=(n_sims, n_f))
    g_fora = rng.poisson(lam_a[None, :], size=(n_sims, n_f))
    if fixed_scores:
        for j, (gc, gf) in fixed_scores.items():
            g_casa[:, j] = gc
            g_fora[:, j] = gf
    casa_vence = g_casa > g_fora
    empate = g_casa == g_fora

    pts = np.tile(pts0, (n_sims, 1))
    win = np.tile(win0, (n_sims, 1))
    sg = np.tile(sg0, (n_sims, 1))
    gp = np.tile(gp0, (n_sims, 1))
    for j in range(n_f):  # acumula jogo a jogo, vetorizado nas simulações
        c, f = casa_idx[j], fora_idx[j]
        gc, gf = g_casa[:, j], g_fora[:, j]
        cv, em = casa_vence[:, j], empate[:, j]
        pts[:, c] += 3 * cv + em
        pts[:, f] += 3 * (~cv & ~em) + em
        win[:, c] += cv
        win[:, f] += ~cv & ~em
        sg[:, c] += gc - gf
        sg[:, f] += gf - gc
        gp[:, c] += gc
        gp[:, f] += gf

    # ranking com desempates: pontos > vitórias > saldo > gols pró (+ ruído p/ empate total)
    score = (
        pts * 1e12
        + win * 1e9
        + (sg + 1000) * 1e5
        + gp * 10
        + rng.uniform(0, 1, size=pts.shape)
    )
    positions = np.argsort(np.argsort(-score, axis=1), axis=1) + 1  # (n_sims, n_t)

    pos_dist = np.zeros((n_t, n_t))
    for t in range(n_t):
        pos_dist[t] = np.bincount(positions[:, t], minlength=n_t + 1)[1:] / n_sims

    details = None
    if keep_details:
        details = ScenarioDetails(
            outcomes=np.where(casa_vence, 0, np.where(empate, 1, 2)).astype(np.int8),
            positions=positions.astype(np.int16),
            points=pts.astype(np.int16),
        )

    return SimulationResult(
        team_ids=team_ids,
        pos_dist=pos_dist,
        exp_pts=pts.mean(axis=0),
        p_titulo=(positions == 1).mean(axis=0),
        p_g4=(positions <= 4).mean(axis=0),
        p_g6=(positions <= 6).mean(axis=0),
        p_z4=(positions >= n_t - 3).mean(axis=0),
        n_sims=n_sims,
        details=details,
    )
