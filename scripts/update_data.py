#!/usr/bin/env python3
"""Atualização diária dos dados (e retreino opcional do modelo).

Uso:
    python scripts/update_data.py            # só baixa os dados
    python scripts/update_data.py --train    # baixa e retreina a LSTM

Exemplo de cron (todo dia às 08:00):
    0 8 * * * cd /caminho/para/remo-api && .venv/bin/python scripts/update_data.py --train
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import store
from src.history import load_historical
from src.model import TORCH_OK, train_daily


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", action="store_true",
                        help="retreina as redes (LSTM e GRU) após atualizar")
    args = parser.parse_args()

    print("Baixando temporada da API do Cartola…")
    data = store.refresh()
    df = store.matches_df(data)
    played, future = store.split_played_future(df)
    print(f"  temporada {data['status'].get('temporada')} · "
          f"rodada atual {data['status'].get('rodada_atual')}")
    print(f"  {len(played)} jogos disputados · {len(future)} jogos futuros")

    if args.train:
        if not TORCH_OK:
            print("PyTorch não instalado — pulando treino.")
            return
        try:
            historical = load_historical()
            print(f"  histórico: {len(historical)} jogos "
                  f"({historical['season'].min()}–{historical['season'].max()})")
        except Exception as e:
            historical = None
            print(f"  histórico indisponível ({e}); treinando só com a temporada atual")
        for arch in ("lstm", "gru"):
            print(f"Treinando {arch.upper()}…")
            m = train_daily(played, arch, historical)
            print(f"  {m['n_samples']} exemplos · NLL val {m['best_val_nll']:.3f} · "
                  f"acurácia 1X2 val {m['val_acc_1x2']:.1%} "
                  f"(baseline mandante {m['naive_home_acc']:.1%})")


if __name__ == "__main__":
    main()
