#!/usr/bin/env python3
"""Migração única do MongoDB para o armazenamento em JSON.

Lê os documentos atuais do banco em ``MONGO_MIGRATION_URL`` e os grava no
layout JSON de ``src/store.py`` (``data/``). Roda na subida do contêiner
pelo ``start.sh`` e não faz nada se a variável não estiver definida ou se a
migração já tiver sido feita (marcador ``data/.migrated-from-mongo``).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import liga, store

MARKER = store.DATA_DIR / ".migrated-from-mongo"


def main():
    url = os.environ.get("MONGO_MIGRATION_URL", "").strip()
    if not url or MARKER.exists():
        return

    # As funções de store escolhem o backend por store.MONGO_URL a cada
    # chamada: lê tudo com o Mongo ligado e grava com ele desligado.
    store.MONGO_URL = url
    season = store.load_snapshot()
    atletas = store.load_atletas()
    pontuados = store.load_pontuados_all()
    copa = store.load_copa()
    libertadores = store.load_libertadores()
    serie_d = store.load_serie_d()
    ligas = [doc for chave in liga.LIGAS if (doc := store.load_liga(chave))]
    projection = store.load_projection()
    visits = store._mongo().metrics.find_one({"_id": "visits"})

    store.MONGO_URL = ""
    if season:
        store._write_json(store.SEASON_FILE, season)
    if atletas:
        store._store_atletas(atletas)
    for rodada, payload in pontuados.items():
        store._store_pontuados(rodada, payload)
    if copa:
        store._store_copa(copa)
    if libertadores:
        store._store_libertadores(libertadores)
    if serie_d:
        store._store_serie_d(serie_d)
    for doc in ligas:
        store._store_liga(doc)
    if projection:
        store.save_projection(projection)
    if visits:
        store._write_json(store.VISITS_FILE, {
            "count": int(visits["count"]),
            "updated_at": visits.get("updated_at"),
        })

    MARKER.write_text("ok\n")
    print(f"migração do MongoDB concluída: {len(pontuados)} rodadas pontuadas, "
          f"{len(ligas)} ligas", flush=True)


if __name__ == "__main__":
    main()
