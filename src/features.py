"""Features para os modelos.

Sequenciais (RNNs): cada time vira uma sequência dos últimos K jogos; cada
jogo é um vetor [gols pró, gols contra, pontos, mando, força do adversário,
diferença de Elo], normalizado para ~[-1, 1].

Tabulares (XGBoost): indicadores de forma acumulada das duas equipes antes do
jogo (pontos por jogo, média de gols nos últimos 5, desempenho por mando, Elo).

O rating Elo é atualizado jogo a jogo durante a varredura cronológica; entre
temporadas históricas ele é regredido para a média (elencos mudam).
"""

import numpy as np
import pandas as pd

K = 6        # tamanho da janela de forma recente
N_FEAT = 6

ELO_START = 1500.0
ELO_K = 20.0
ELO_HFA = 60.0        # vantagem de mando (pontos de Elo) no resultado esperado
ELO_CARRY = 0.75      # regressão à média entre temporadas
HIST_DECAY = 0.85     # peso das temporadas antigas no treino (por ano)


def _elo_update(elo: dict, casa: int, fora: int, gc: int, gf: int):
    ra, rb = elo.get(casa, ELO_START), elo.get(fora, ELO_START)
    esperado = 1 / (1 + 10 ** (-((ra + ELO_HFA) - rb) / 400))
    real = 1.0 if gc > gf else 0.5 if gc == gf else 0.0
    delta = ELO_K * (real - esperado)
    elo[casa] = ra + delta
    elo[fora] = rb - delta


def _feature_vector(gf: int, ga: int, is_home: bool, opp_ppg: float,
                    elo_diff: float) -> list[float]:
    pts = 3 if gf > ga else 1 if gf == ga else 0
    return [gf / 3.0, ga / 3.0, pts / 3.0, 1.0 if is_home else 0.0,
            opp_ppg / 3.0, elo_diff / 400.0]


def _padded(history: list[list[float]], k: int) -> np.ndarray:
    """Últimos k vetores, com zeros à esquerda quando o histórico é curto."""
    seq = np.zeros((k, N_FEAT), dtype=np.float32)
    tail = history[-k:]
    if tail:
        seq[-len(tail):] = np.asarray(tail, dtype=np.float32)
    return seq


def build_training_data(played: pd.DataFrame, k: int = K, elo: dict | None = None):
    """Percorre os jogos em ordem cronológica montando, para cada partida, as
    sequências de forma das duas equipes ANTES do jogo, e o placar como alvo.

    ``elo`` é opcional e mutado (permite carregar o rating entre temporadas).
    Retorna (X_casa, X_fora, y, rodadas) — arrays numpy.
    """
    if elo is None:
        elo = {}
    history: dict[int, list[list[float]]] = {}
    points: dict[int, int] = {}
    games: dict[int, int] = {}

    X_h, X_a, y, rodadas = [], [], [], []
    for m in played.sort_values("timestamp").itertuples():
        casa, fora = m.casa_id, m.fora_id
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        for t in (casa, fora):
            history.setdefault(t, [])
            points.setdefault(t, 0)
            games.setdefault(t, 0)

        if history[casa] and history[fora]:
            X_h.append(_padded(history[casa], k))
            X_a.append(_padded(history[fora], k))
            y.append([gc, gf])
            rodadas.append(m.rodada)

        # atualiza os históricos DEPOIS de gerar o exemplo (sem vazamento)
        ppg_casa = points[casa] / max(games[casa], 1)
        ppg_fora = points[fora] / max(games[fora], 1)
        ed = elo.get(casa, ELO_START) - elo.get(fora, ELO_START)
        history[casa].append(_feature_vector(gc, gf, True, ppg_fora, ed))
        history[fora].append(_feature_vector(gf, gc, False, ppg_casa, -ed))
        points[casa] += 3 if gc > gf else 1 if gc == gf else 0
        points[fora] += 3 if gf > gc else 1 if gc == gf else 0
        games[casa] += 1
        games[fora] += 1
        _elo_update(elo, casa, fora, gc, gf)

    return (
        np.asarray(X_h, dtype=np.float32),
        np.asarray(X_a, dtype=np.float32),
        np.asarray(y, dtype=np.float32),
        np.asarray(rodadas),
    )


def build_multi_training(historical: pd.DataFrame, played: pd.DataFrame, k: int = K):
    """Concatena temporadas históricas (Elo carregado entre elas, com regressão
    à média) + temporada atual. Retorna (X_h, X_a, y, pesos), com temporadas
    antigas pesando ``HIST_DECAY`` por ano de distância."""
    parts, elo = [], {}
    if historical is not None and len(historical):
        ano_ref = int(historical["season"].max()) + 1
        for season in sorted(historical["season"].unique()):
            Xh, Xa, y, _ = build_training_data(
                historical[historical["season"] == season], k, elo
            )
            w = np.full(len(y), HIST_DECAY ** (ano_ref - int(season)), dtype=np.float32)
            parts.append((Xh, Xa, y, w))
            elo = {t: ELO_START + ELO_CARRY * (r - ELO_START) for t, r in elo.items()}

    Xh, Xa, y, _ = build_training_data(played, k)  # ids do Cartola: Elo próprio
    parts.append((Xh, Xa, y, np.ones(len(y), dtype=np.float32)))

    return (
        np.concatenate([p[0] for p in parts]),
        np.concatenate([p[1] for p in parts]),
        np.concatenate([p[2] for p in parts]),
        np.concatenate([p[3] for p in parts]),
    )


def current_sequences(played: pd.DataFrame, k: int = K) -> dict[int, np.ndarray]:
    """Sequência de forma atual (últimos k jogos) de cada time."""
    elo: dict[int, float] = {}
    history: dict[int, list[list[float]]] = {}
    points: dict[int, int] = {}
    games: dict[int, int] = {}

    for m in played.sort_values("timestamp").itertuples():
        casa, fora = m.casa_id, m.fora_id
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        for t in (casa, fora):
            history.setdefault(t, [])
            points.setdefault(t, 0)
            games.setdefault(t, 0)
        ppg_casa = points[casa] / max(games[casa], 1)
        ppg_fora = points[fora] / max(games[fora], 1)
        ed = elo.get(casa, ELO_START) - elo.get(fora, ELO_START)
        history[casa].append(_feature_vector(gc, gf, True, ppg_fora, ed))
        history[fora].append(_feature_vector(gf, gc, False, ppg_casa, -ed))
        points[casa] += 3 if gc > gf else 1 if gc == gf else 0
        points[fora] += 3 if gf > gc else 1 if gc == gf else 0
        games[casa] += 1
        games[fora] += 1
        _elo_update(elo, casa, fora, gc, gf)

    return {t: _padded(h, k) for t, h in history.items()}


# ------------------------------------------------------------- tabulares

class _RollingStats:
    """Estatísticas acumuladas por time durante a varredura cronológica."""

    def __init__(self):
        self.pts = 0
        self.jogos = 0
        self.gf: list[int] = []
        self.ga: list[int] = []
        self.pts_casa = 0
        self.jogos_casa = 0
        self.pts_fora = 0
        self.jogos_fora = 0

    def row(self, is_home: bool, elo_self: float, elo_opp: float,
            last: int = 5) -> list[float]:
        ppg = self.pts / max(self.jogos, 1)
        gf5 = float(np.mean(self.gf[-last:])) if self.gf else 0.0
        ga5 = float(np.mean(self.ga[-last:])) if self.ga else 0.0
        pts5 = ppg if not self.gf else sum(
            3 if f > a else 1 if f == a else 0
            for f, a in zip(self.gf[-last:], self.ga[-last:])
        ) / len(self.gf[-last:])
        mando_ppg = (
            self.pts_casa / max(self.jogos_casa, 1)
            if is_home
            else self.pts_fora / max(self.jogos_fora, 1)
        )
        return [ppg, pts5, gf5, ga5, mando_ppg,
                (elo_self - ELO_START) / 400.0, (elo_self - elo_opp) / 400.0]

    def update(self, gf: int, ga: int, is_home: bool):
        pts = 3 if gf > ga else 1 if gf == ga else 0
        self.pts += pts
        self.jogos += 1
        self.gf.append(gf)
        self.ga.append(ga)
        if is_home:
            self.pts_casa += pts
            self.jogos_casa += 1
        else:
            self.pts_fora += pts
            self.jogos_fora += 1


TABULAR_COLS = [
    "casa_ppg", "casa_ppg5", "casa_gf5", "casa_ga5", "casa_mando_ppg",
    "casa_elo", "casa_elo_diff",
    "fora_ppg", "fora_ppg5", "fora_gf5", "fora_ga5", "fora_mando_ppg",
    "fora_elo", "fora_elo_diff",
]


def build_tabular(played: pd.DataFrame, elo: dict | None = None):
    """Features tabulares (forma acumulada das duas equipes antes do jogo)
    para modelos de árvore. Retorna (X, y_casa, y_fora) como numpy."""
    if elo is None:
        elo = {}
    stats: dict[int, _RollingStats] = {}
    X, y_h, y_a = [], [], []
    for m in played.sort_values("timestamp").itertuples():
        casa = stats.setdefault(m.casa_id, _RollingStats())
        fora = stats.setdefault(m.fora_id, _RollingStats())
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        e_c = elo.get(m.casa_id, ELO_START)
        e_f = elo.get(m.fora_id, ELO_START)
        if casa.jogos and fora.jogos:
            X.append(casa.row(True, e_c, e_f) + fora.row(False, e_f, e_c))
            y_h.append(gc)
            y_a.append(gf)
        casa.update(gc, gf, True)
        fora.update(gf, gc, False)
        _elo_update(elo, m.casa_id, m.fora_id, gc, gf)
    return (
        np.asarray(X, dtype=np.float32),
        np.asarray(y_h, dtype=np.float32),
        np.asarray(y_a, dtype=np.float32),
    )


def build_multi_tabular(historical: pd.DataFrame, played: pd.DataFrame):
    """Versão multi-temporada de ``build_tabular`` (com pesos por recência)."""
    parts, elo = [], {}
    if historical is not None and len(historical):
        ano_ref = int(historical["season"].max()) + 1
        for season in sorted(historical["season"].unique()):
            X, y_h, y_a = build_tabular(
                historical[historical["season"] == season], elo
            )
            w = np.full(len(X), HIST_DECAY ** (ano_ref - int(season)), dtype=np.float32)
            parts.append((X, y_h, y_a, w))
            elo = {t: ELO_START + ELO_CARRY * (r - ELO_START) for t, r in elo.items()}

    X, y_h, y_a = build_tabular(played)
    parts.append((X, y_h, y_a, np.ones(len(X), dtype=np.float32)))

    return (
        np.concatenate([p[0] for p in parts]),
        np.concatenate([p[1] for p in parts]),
        np.concatenate([p[2] for p in parts]),
        np.concatenate([p[3] for p in parts]),
    )


def tabular_for_fixtures(fixtures: pd.DataFrame, played: pd.DataFrame) -> np.ndarray:
    """Features tabulares dos jogos futuros com a forma atual das equipes."""
    elo: dict[int, float] = {}
    stats: dict[int, _RollingStats] = {}
    for m in played.sort_values("timestamp").itertuples():
        casa = stats.setdefault(m.casa_id, _RollingStats())
        fora = stats.setdefault(m.fora_id, _RollingStats())
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        casa.update(gc, gf, True)
        fora.update(gf, gc, False)
        _elo_update(elo, m.casa_id, m.fora_id, gc, gf)
    vazio = _RollingStats()
    X = []
    for m in fixtures.itertuples():
        e_c = elo.get(m.casa_id, ELO_START)
        e_f = elo.get(m.fora_id, ELO_START)
        X.append(
            stats.get(m.casa_id, vazio).row(True, e_c, e_f)
            + stats.get(m.fora_id, vazio).row(False, e_f, e_c)
        )
    return np.asarray(X, dtype=np.float32)
