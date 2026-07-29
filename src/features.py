"""Features tabulares para os modelos: indicadores de forma acumulada das
duas equipes antes de cada jogo (pontos por jogo, média de gols nos últimos 5,
desempenho por mando) mais o **rating Elo**, atualizado jogo a jogo durante a
varredura cronológica; entre temporadas históricas ele é regredido para a
média (elencos mudam).
"""

import numpy as np
import pandas as pd

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
    """Features das duas equipes antes de cada jogo (sem vazamento de futuro).
    Retorna (X, y_casa, y_fora) como numpy; ``elo`` é mutado (permite carregar
    o rating entre temporadas)."""
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
    """Temporadas históricas (Elo carregado entre elas, com regressão à média)
    + temporada atual. Retorna (X, y_casa, y_fora, pesos) — temporadas antigas
    pesam ``HIST_DECAY`` por ano de distância."""
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
    """Features dos jogos futuros com a forma atual das equipes."""
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
