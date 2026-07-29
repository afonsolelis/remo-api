#!/usr/bin/env python3
"""Atualização manual dos dados (partidas, elencos e pontuações).

Uso:
    python scripts/update_data.py

Exemplo de cron (todo dia às 08:00), para uso sem Docker:
    0 8 * * * cd /caminho/para/remo-api && .venv/bin/python scripts/update_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import store


def main():
    print("Baixando temporada da API do Cartola…")
    data = store.refresh()
    df = store.matches_df(data)
    played, future = store.split_played_future(df)
    print(f"  temporada {data['status'].get('temporada')} · "
          f"rodada atual {data['status'].get('rodada_atual')}")
    print(f"  {len(played)} jogos disputados · {len(future)} jogos futuros")


if __name__ == "__main__":
    main()
