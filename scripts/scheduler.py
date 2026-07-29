#!/usr/bin/env python3
"""Agendador do serviço ``updater`` (Docker): atualiza os dados da API do
Cartola e retreina as redes nos horários de ``UPDATE_TIMES`` (padrão
``08:00,22:00``, no fuso do contêiner — ``TZ`` no docker-compose).

Na subida, roda imediatamente se ainda não há snapshot ou se ele está velho.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import store
from src.history import load_historical
from src.model import TORCH_OK, train_daily

UPDATE_TIMES = [
    tuple(int(x) for x in t.strip().split(":"))
    for t in os.environ.get("UPDATE_TIMES", "08:00,22:00").split(",")
]
STALE_HOURS = 14  # na subida, atualiza se o snapshot for mais velho que isso


def log(msg: str):
    print(f"[{datetime.now():%d/%m %H:%M:%S}] {msg}", flush=True)


def run_update():
    log("atualizando dados da API do Cartola…")
    data = store.refresh()
    df = store.matches_df(data)
    played, future = store.split_played_future(df)
    log(f"rodada {data['status'].get('rodada_atual')} · "
        f"{len(played)} jogos disputados · {len(future)} futuros")

    if not TORCH_OK:
        log("PyTorch indisponível — pulando treino")
        return
    try:
        historical = load_historical()
    except Exception as e:
        historical = None
        log(f"histórico indisponível ({e}); treinando só com a temporada atual")
    for arch in ("lstm", "gru"):
        m = train_daily(played, arch, historical)
        log(f"{arch.upper()}: {m['n_samples']} exemplos · "
            f"NLL val {m['best_val_nll']:.3f} · acurácia {m['val_acc_1x2']:.1%}")
    log("atualização concluída")


def next_run(now: datetime) -> datetime:
    horarios = []
    for h, m in UPDATE_TIMES:
        t = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        horarios.append(t)
    return min(horarios)


def main():
    log(f"updater iniciado · horários: "
        + ", ".join(f"{h:02d}:{m:02d}" for h, m in UPDATE_TIMES))
    snapshot = store.load_snapshot()
    idade_h = None
    if snapshot:
        from datetime import timezone
        fetched = datetime.fromisoformat(snapshot["fetched_at"])
        idade_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    if snapshot is None or idade_h > STALE_HOURS:
        run_update()
    else:
        log(f"snapshot recente ({idade_h:.1f} h) — aguardando o próximo horário")

    while True:
        alvo = next_run(datetime.now())
        log(f"próxima atualização: {alvo:%d/%m %H:%M}")
        time.sleep(max(1.0, (alvo - datetime.now()).total_seconds()))
        try:
            run_update()
        except Exception as e:
            log(f"ERRO na atualização: {e} — tento de novo no próximo horário")


if __name__ == "__main__":
    main()
