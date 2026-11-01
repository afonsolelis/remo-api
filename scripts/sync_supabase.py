"""Baixa as Séries A e B da API de tabelas do ge e grava no Postgres (Supabase).

Uso: DATABASE_URL=postgresql://... python scripts/sync_supabase.py
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import requests

BASE_URL = "https://api.globoesporte.globo.com/tabela"
SCHEMA = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
BRASILIA = timezone(timedelta(hours=-3))
MATCH_DURATION = timedelta(hours=2)

# O UUID muda a cada temporada: atributo data-bs-resource-id da página
# ge.globo.com/futebol/brasileirao-serie-a/ (e .../brasileirao-serie-b/).
LIGAS = {
    "serie_a": ("Série A", "d1a37fa4-e948-43a6-ba53-ab24ab3a45b1"),
    "serie_b": ("Série B", "009b5a68-dd09-46b8-95b3-293a2d494366"),
}

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (remo-api; uso pessoal)"})


def get(path: str) -> dict | list:
    r = session.get(f"{BASE_URL}/{path}", timeout=20)
    r.raise_for_status()
    return r.json()


def zonas(classificacao: dict) -> list[dict]:
    """Faixas da tabela (acesso, Libertadores, rebaixamento...) como intervalos de posição."""
    nomes = {f["cor"]: f["nome"] for f in classificacao.get("faixas_classificacao", [])}
    ordens: dict[str, list[int]] = {}
    for t in classificacao.get("classificacao", []):
        cor = t.get("faixa_classificacao_cor")
        if cor in nomes:
            ordens.setdefault(cor, []).append(int(t["ordem"]))
    return [
        {"nome": nomes[cor], "cor": cor, "posicoes": list(range(min(p), min(p) + len(p)))}
        for cor, p in ordens.items()
    ]


def fetch_liga(uuid: str) -> tuple[dict, dict, list]:
    classificacao = get(f"{uuid}/classificacao/")
    fase = classificacao["fase"]["slug"]
    ultima = int((classificacao.get("rodada") or {}).get("ultima") or 38)
    agora = datetime.now(timezone.utc)

    clubes, partidas = {}, []
    for rodada in range(1, ultima + 1):
        for jogo in get(f"{uuid}/fase/{fase}/rodada/{rodada}/jogos/"):
            casa = (jogo.get("equipes") or {}).get("mandante") or {}
            fora = (jogo.get("equipes") or {}).get("visitante") or {}
            if casa.get("id") is None or fora.get("id") is None:
                continue
            for e in (casa, fora):
                clubes[e["id"]] = (e["id"], e.get("nome_popular"), e.get("sigla"), e.get("escudo"))
            data = None
            if jogo.get("data_realizacao"):
                data = datetime.fromisoformat(jogo["data_realizacao"]).replace(tzinfo=BRASILIA)
            gc, gf = jogo.get("placar_oficial_mandante"), jogo.get("placar_oficial_visitante")
            encerrada = gc is not None and gf is not None and data is not None and data + MATCH_DURATION < agora
            partidas.append((jogo["id"], rodada, data, casa["id"], fora["id"], gc, gf, encerrada))
        time.sleep(0.15)
    return classificacao, clubes, partidas


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Defina DATABASE_URL.")

    with psycopg.connect(url, prepare_threshold=None) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        conn.commit()

        for liga, (nome, uuid) in LIGAS.items():
            try:
                classificacao, clubes, partidas = fetch_liga(uuid)
            except Exception as e:  # mantém o último dado gravado dessa liga
                print(f"{nome}: falhou ({e})")
                continue
            if not partidas:
                print(f"{nome}: sem jogos, mantendo dados anteriores")
                continue

            with conn.transaction(), conn.cursor() as cur:
                cur.execute(
                    """insert into remo_ligas (liga, nome, zonas, rodada_atual, atualizado_em)
                       values (%s, %s, %s, %s, now())
                       on conflict (liga) do update set nome = excluded.nome, zonas = excluded.zonas,
                         rodada_atual = excluded.rodada_atual, atualizado_em = now()""",
                    (liga, nome, json.dumps(zonas(classificacao), ensure_ascii=False),
                     (classificacao.get("rodada") or {}).get("atual")),
                )
                cur.execute("delete from remo_partidas where liga = %s", (liga,))
                cur.execute("delete from remo_clubes where liga = %s", (liga,))
                cur.executemany(
                    "insert into remo_clubes (liga, id, nome, abreviacao, escudo) values (%s, %s, %s, %s, %s)",
                    [(liga, *c) for c in clubes.values()],
                )
                cur.executemany(
                    """insert into remo_partidas (liga, partida_id, rodada, data, casa_id, fora_id,
                         gols_casa, gols_fora, encerrada) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [(liga, *p) for p in partidas],
                )
            print(f"{nome}: {len(clubes)} clubes, {len(partidas)} partidas, "
                  f"{sum(p[-1] for p in partidas)} encerradas.")


if __name__ == "__main__":
    main()
