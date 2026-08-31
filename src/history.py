"""Histórico do Brasileirão (2012+) via football-data.co.uk.

Usado apenas para TREINAR os modelos de ML com mais dados — a temporada atual
continua vindo da API do Cartola. Os times viram ids sintéticos estáveis por
nome (não precisam casar com os ids do Cartola: as features são de forma, não
de identidade).
"""

import time
from datetime import datetime

import pandas as pd
import requests

from .store import DATA_DIR

HIST_BASE = "https://www.football-data.co.uk/new"
HIST_DIR = DATA_DIR / "historical"
ARQUIVO_PADRAO = "BRA.csv"  # Brasileirão Série A
MAX_AGE_DAYS = 3
_SYNTH_OFFSET = 100_000  # evita colisão com ids do Cartola


def _download(arquivo: str, destino) -> None:
    r = requests.get(f"{HIST_BASE}/{arquivo}", timeout=60)
    r.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)


def load_historical(current_season: int = 2026,
                    arquivo: str = ARQUIVO_PADRAO) -> pd.DataFrame:
    """Partidas históricas em formato compatível com ``matches_df``
    (+ coluna ``season``). Exclui a temporada atual (vem da fonte ao vivo).

    ``arquivo`` escolhe a liga no football-data (``BRA.csv``, ``USA.csv``…);
    todas usam o mesmo layout, e os ids são sintéticos por nome — as
    features são de forma e Elo, não de identidade.
    """
    HIST_FILE = HIST_DIR / arquivo
    stale = (
        not HIST_FILE.exists()
        or (time.time() - HIST_FILE.stat().st_mtime) > MAX_AGE_DAYS * 86400
    )
    if stale:
        try:
            _download(arquivo, HIST_FILE)
        except Exception:
            if not HIST_FILE.exists():
                raise  # sem arquivo local e sem rede

    raw = pd.read_csv(HIST_FILE, encoding="utf-8-sig")
    raw = raw[(raw["Season"] < current_season)
              & raw["HG"].notna() & raw["AG"].notna()].copy()

    nomes = sorted(set(raw["Home"]) | set(raw["Away"]))
    ids = {n: _SYNTH_OFFSET + i for i, n in enumerate(nomes)}

    df = pd.DataFrame({
        "season": raw["Season"].astype(int),
        "casa_id": raw["Home"].map(ids),
        "fora_id": raw["Away"].map(ids),
        "gols_casa": raw["HG"].astype(float),
        "gols_fora": raw["AG"].astype(float),
        "timestamp": [
            datetime.strptime(f"{d} {h or '16:00'}", "%d/%m/%Y %H:%M").timestamp()
            for d, h in zip(raw["Date"], raw["Time"].fillna("16:00"))
        ],
    })
    df = df.sort_values("timestamp").reset_index(drop=True)
    # rodada aproximada (só informativa; as features não dependem dela)
    df["rodada"] = df.groupby("season").cumcount() // 10 + 1
    return df
