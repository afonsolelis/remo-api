"""Baixa o Brasileirão da API do Cartola e grava no Postgres (Supabase).

Uso: DATABASE_URL=postgresql://... python scripts/sync_supabase.py
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests

BASE_URL = "https://api.cartola.globo.com"
SCHEMA = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
MATCH_DURATION_S = 2 * 3600

NOMES = {
    262: "Flamengo", 263: "Botafogo", 264: "Corinthians", 265: "Bahia",
    266: "Fluminense", 267: "Vasco", 275: "Palmeiras", 276: "São Paulo",
    277: "Santos", 280: "Red Bull Bragantino", 282: "Atlético-MG",
    283: "Cruzeiro", 284: "Grêmio", 285: "Internacional", 287: "Vitória",
    293: "Athletico-PR", 294: "Coritiba", 315: "Chapecoense", 364: "Remo",
    2305: "Mirassol",
}

session = requests.Session()
session.headers.update({"User-Agent": "remo-api/0.2 (uso pessoal)"})


def get(path: str) -> dict:
    r = session.get(f"{BASE_URL}{path}", timeout=20)
    r.raise_for_status()
    return r.json()


def fetch() -> tuple[dict, dict, list]:
    status = get("/mercado/status")
    clubes, partidas = {}, []
    for rodada in range(1, status.get("rodada_final", 38) + 1):
        payload = get(f"/partidas/{rodada}")
        clubes.update(payload.get("clubes", {}))
        for p in payload.get("partidas", []):
            p["rodada"] = rodada
            partidas.append(p)
        time.sleep(0.15)
    return status, clubes, partidas


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Defina DATABASE_URL.")

    status, clubes, partidas = fetch()
    agora = time.time()

    clube_rows = [
        (
            int(c["id"]),
            NOMES.get(int(c["id"])) or c.get("apelido") or c.get("nome"),
            c.get("abreviacao"),
            (c.get("escudos") or {}).get("60x60"),
        )
        for c in clubes.values()
    ]
    partida_rows = []
    for p in partidas:
        gc, gf = p.get("placar_oficial_mandante"), p.get("placar_oficial_visitante")
        ts = p.get("timestamp") or 0
        encerrada = gc is not None and gf is not None and ts + MATCH_DURATION_S < agora
        data = datetime.fromtimestamp(ts, timezone.utc) if ts else None
        partida_rows.append(
            (p["partida_id"], p["rodada"], data, p["clube_casa_id"],
             p["clube_visitante_id"], gc, gf, encerrada)
        )

    with psycopg.connect(url, prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
        cur.executemany(
            """insert into remo_clubes (id, nome, abreviacao, escudo) values (%s, %s, %s, %s)
               on conflict (id) do update set nome = excluded.nome,
                 abreviacao = excluded.abreviacao, escudo = excluded.escudo""",
            clube_rows,
        )
        cur.executemany(
            """insert into remo_partidas (partida_id, rodada, data, casa_id, fora_id,
                 gols_casa, gols_fora, encerrada)
               values (%s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (partida_id) do update set rodada = excluded.rodada,
                 data = excluded.data, casa_id = excluded.casa_id,
                 fora_id = excluded.fora_id, gols_casa = excluded.gols_casa,
                 gols_fora = excluded.gols_fora, encerrada = excluded.encerrada""",
            partida_rows,
        )
        # Jogos que sumiram da API (remarcados para outro id) saem da tabela.
        cur.execute(
            "delete from remo_partidas where partida_id <> all(%s)",
            ([r[0] for r in partida_rows],),
        )
        cur.execute(
            """insert into remo_atualizacao (id, executado_em, rodada_atual) values (1, now(), %s)
               on conflict (id) do update set executado_em = now(),
                 rodada_atual = excluded.rodada_atual""",
            (status.get("rodada_atual"),),
        )
    print(f"OK: {len(clube_rows)} clubes, {len(partida_rows)} partidas.")


if __name__ == "__main__":
    main()
