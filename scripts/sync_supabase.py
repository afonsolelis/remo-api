"""Baixa os campeonatos e as notícias dos clubes no ge e grava no Postgres (Supabase).

Uso: DATABASE_URL=postgresql://... python scripts/sync_supabase.py            # tudo
     DATABASE_URL=postgresql://... python scripts/sync_supabase.py noticias   # só notícias
"""

import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import requests

BASE_URL = "https://api.globoesporte.globo.com/tabela"
SCHEMA = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
BRASILIA = timezone(timedelta(hours=-3))
MATCH_DURATION = timedelta(hours=2)

# "pontos": o site simula a tabela da primeira fase; "copa": mostra fases e chaves.
# O UUID da tabela muda a cada temporada, então é lido a cada execução da página do
# campeonato no ge (atributo data-bs-resource-id). O UUID fixo é só o reserva, caso
# a página mude de formato.
LIGAS = {
    "serie_a": ("Série A", "pontos", "futebol/brasileirao-serie-a", "d1a37fa4-e948-43a6-ba53-ab24ab3a45b1"),
    "serie_b": ("Série B", "pontos", "futebol/brasileirao-serie-b", "009b5a68-dd09-46b8-95b3-293a2d494366"),
    "parazao": ("Parazão", "copa", "pa/futebol/campeonato-paraense", "28da6ccd-6407-4602-9ceb-8cc33e05165d"),
    "copa_verde": ("Copa Verde", "copa", "futebol/copa-verde", "0b037b4f-c04d-4cdc-8461-4ecdec0ba1e0"),
}

NOTICIAS_POR_CLUBE = 10
FEED = "https://falkor-cda.bastian.globo.com/tenants/ge/instances/{}/posts/page/1"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (remo-api; uso pessoal)"})


def get(path: str) -> dict | list:
    r = session.get(f"{BASE_URL}/{path}", timeout=20)
    r.raise_for_status()
    time.sleep(0.1)
    return r.json()


# Páginas em que o UUID não foi achado nesta execução; o main trata como falha.
usou_reserva: set[str] = set()


def uuid_atual(pagina: str, reserva: str) -> str:
    """UUID da edição corrente, lido da página do campeonato no ge."""
    try:
        r = session.get(f"https://ge.globo.com/{pagina}/", timeout=20)
        r.raise_for_status()
        achados = re.findall(r'data-bs-resource-id="([0-9a-f-]{36})"', r.text)
        if achados:
            return achados[0]
    except requests.RequestException:
        pass
    print(f"{pagina}: UUID não encontrado na página, usando o reserva")
    usou_reserva.add(pagina)
    return reserva


def zonas(faixas: list, linhas: list) -> list[dict]:
    """Faixas da tabela (acesso, Libertadores, rebaixamento...) como intervalos de posição."""
    nomes = {f["cor"]: f["nome"] for f in faixas or []}
    ordens: dict[str, list[int]] = {}
    for t in linhas:
        cor = t.get("faixa_classificacao_cor")
        if cor in nomes:
            ordens.setdefault(cor, []).append(int(t["ordem"]))
    return [
        {"nome": nomes[cor], "cor": cor, "posicoes": list(range(min(p), min(p) + len(p)))}
        for cor, p in ordens.items()
    ]


def grupo(nome: str, faixas: list, linhas: list) -> dict:
    """Tabela oficial de um grupo (ou da fase inteira) como o ge publica."""
    return {
        "nome": nome,
        "zonas": zonas(faixas, linhas),
        "times": [
            {
                "id": t.get("equipe_id"), "pontos": t.get("pontos"), "jogos": t.get("jogos"),
                "vitorias": t.get("vitorias"), "empates": t.get("empates"),
                "derrotas": t.get("derrotas"), "saldo": t.get("saldo_gols"),
            }
            for t in linhas
        ],
    }


def local_do_jogo(jogo: dict) -> tuple:
    """(estádio, horário definido, link da página do jogo no ge) para a aba Jogos de hoje."""
    estadio = (jogo.get("sede") or {}).get("nome_popular") or None
    link = (jogo.get("transmissao") or {}).get("url") or ""
    return estadio, bool(jogo.get("hora_realizacao")), link if link.startswith("https://ge.globo.com/") else None


def fetch_liga(uuid: str) -> dict:
    raiz = get(f"{uuid}/classificacao/")
    fases_nav = raiz.get("fases_navegacao") or [{"slug": raiz["fase"]["slug"], "nome": "Fase única"}]
    agora = datetime.now(timezone.utc)
    clubes, partidas, fases = {}, {}, []

    def add_jogo(jogo: dict, rodada: int, fase: str, ordem: int, chave: str | None) -> None:
        casa = (jogo.get("equipes") or {}).get("mandante") or {}
        fora = (jogo.get("equipes") or {}).get("visitante") or {}
        if casa.get("id") is None or fora.get("id") is None:
            return  # confronto ainda sem os dois clubes definidos
        for e in (casa, fora):
            clubes[e["id"]] = (e["id"], e.get("nome_popular"), e.get("sigla"), e.get("escudo"))
        data = None
        if jogo.get("data_realizacao"):
            data = datetime.fromisoformat(jogo["data_realizacao"]).replace(tzinfo=BRASILIA)
        gc, gf = jogo.get("placar_oficial_mandante"), jogo.get("placar_oficial_visitante")
        encerrada = gc is not None and gf is not None and data is not None and data + MATCH_DURATION < agora
        partidas[jogo["id"]] = (
            jogo["id"], rodada, data, casa["id"], fora["id"], gc, gf, encerrada,
            fase, ordem, chave, jogo.get("placar_penaltis_mandante"), jogo.get("placar_penaltis_visitante"),
            *local_do_jogo(jogo),
        )

    for ordem, f in enumerate(fases_nav, 1):
        p = raiz if f["slug"] == raiz["fase"]["slug"] else get(f"{uuid}/fase/{f['slug']}/classificacao/")
        nome = f.get("nome") or "Fase única"
        if p.get("classificacao") or p.get("grupos"):
            # pontos corridos: tabela única ou grupos, jogos por rodada
            if p.get("classificacao"):
                grupos = [grupo(nome, p.get("faixas_classificacao"), p["classificacao"])]
                linhas_por_grupo = {nome: p["classificacao"]}
                ultima = int((p.get("rodada") or {}).get("ultima") or 0)
            else:
                grupos = [grupo(g["nome_grupo"], p.get("faixas_classificacao"), g["classificacao"]) for g in p["grupos"]]
                linhas_por_grupo = {g["nome_grupo"]: g["classificacao"] for g in p["grupos"]}
                ultima = max(int((g.get("rodada") or {}).get("ultima") or 0) for g in p["grupos"])
            grupo_do_time = {t["equipe_id"]: g for g, ls in linhas_por_grupo.items() for t in ls}
            for ls in linhas_por_grupo.values():
                for t in ls:
                    clubes.setdefault(t["equipe_id"], (t["equipe_id"], t.get("nome_popular"), t.get("sigla"), t.get("escudo")))
            for rodada in range(1, ultima + 1):
                for jogo in get(f"{uuid}/fase/{f['slug']}/rodada/{rodada}/jogos/"):
                    mandante = ((jogo.get("equipes") or {}).get("mandante") or {}).get("id")
                    add_jogo(jogo, rodada, nome, ordem, grupo_do_time.get(mandante) if len(grupos) > 1 else None)
            fases.append({"nome": nome, "tipo": "pontos", "grupos": grupos})
        else:
            # mata-mata: confrontos em secao -> chave -> jogos
            for secao in p.get("secao") or []:
                for c in secao.get("chave") or []:
                    for i, jogo in enumerate(j for j in c.get("jogos") or [] if j.get("exibir_jogo", True)):
                        add_jogo(jogo, i + 1, nome, ordem, c.get("nome"))
            fases.append({"nome": nome, "tipo": "mata", "grupos": []})

    return {
        "zonas": fases[0]["grupos"][0]["zonas"] if fases[0]["grupos"] else [],
        "fases": fases,
        "rodada_atual": (raiz.get("rodada") or {}).get("atual"),
        "clubes": clubes,
        "partidas": list(partidas.values()),
    }


# ---------- notícias ----------

def slug(texto: str) -> str:
    """'São Paulo' -> 'sao-paulo', como no endereço da página do time no ge."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def paginas_dos_times() -> dict[str, str]:
    """slug -> página do time, a partir dos links nas páginas dos campeonatos."""
    paginas = {}
    for _, _, pagina, _ in LIGAS.values():
        try:
            r = session.get(f"https://ge.globo.com/{pagina}/", timeout=20)
            r.raise_for_status()
        except requests.RequestException:
            continue
        for url in re.findall(r'https://ge\.globo\.com/[a-z/-]*?futebol/times/[a-z0-9-]+/', r.text):
            paginas.setdefault(url.rstrip("/").rsplit("/", 1)[1], url)
    return paginas


def feed_do_time(pagina: str) -> str | None:
    """Id do feed de notícias que a página do time usa."""
    r = session.get(pagina, timeout=20)
    r.raise_for_status()
    achado = re.search(r"tenants/ge/instances/([0-9a-f-]{36})/posts", r.text)
    return achado.group(1) if achado else None


def fetch_noticias(feed: str) -> list[tuple]:
    """Matérias do feed: (id, título, resumo, url, imagem, publicação). Vídeos ficam de fora."""
    r = session.get(FEED.format(feed), timeout=20)
    r.raise_for_status()
    noticias = []
    for item in r.json().get("items") or []:
        c = item.get("content") or {}
        url = c.get("url") or ""
        if item.get("type") != "materia" or not c.get("title") or not url.startswith("https://ge.globo.com/"):
            continue
        imagem = (((c.get("image") or {}).get("sizes") or {}).get("S") or {}).get("url")
        if imagem and not imagem.startswith("https://"):
            imagem = None
        noticias.append((item["id"], c["title"], c.get("summary"), url, imagem, item["publication"]))
    return noticias[:NOTICIAS_POR_CLUBE]


def clubes_do_banco(conn) -> dict[int, str]:
    return dict(conn.execute("select distinct id, nome from remo_clubes").fetchall())


def sync_noticias(conn) -> list[str]:
    """Regrava as notícias de cada clube, um por transação. Devolve as falhas."""
    clubes = clubes_do_banco(conn)
    paginas = paginas_dos_times()
    if not paginas:
        return ["Notícias: nenhuma página de time achada nas páginas dos campeonatos"]
    gravados = 0
    for id, nome in clubes.items():
        pagina = paginas.get(slug(nome))
        if not pagina:
            continue  # clube pequeno, sem página no ge
        try:
            feed = feed_do_time(pagina)
            noticias = fetch_noticias(feed) if feed else []
        except Exception as e:  # mantém as notícias anteriores desse clube
            print(f"Notícias de {nome}: falhou ({e})")
            continue
        if not noticias:
            continue
        with conn.transaction(), conn.cursor() as cur:
            cur.execute("delete from remo_noticias where clube_id = %s", (id,))
            cur.executemany(
                """insert into remo_noticias (clube_id, noticia_id, titulo, resumo, url, imagem, publicado_em)
                   values (%s, %s, %s, %s, %s, %s, %s)""",
                [(id, *n) for n in noticias],
            )
        gravados += 1
    # Clubes que saíram de todos os campeonatos deixam de ter notícias.
    conn.execute("delete from remo_noticias where clube_id not in (select id from remo_clubes)")
    conn.commit()
    print(f"Notícias: {gravados} clubes atualizados.")
    if clubes and not gravados:
        return ["Notícias: nenhum clube teve notícias gravadas (o ge mudou o formato?)"]
    return []


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Defina DATABASE_URL.")

    usou_reserva.clear()
    falhas = []  # avisam o mantenedor: o Actions marca a execução como falha (AD-aviso-por-falha)

    with psycopg.connect(url, prepare_threshold=None) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
        conn.commit()

        so_noticias = sys.argv[1:] == ["noticias"]
        for liga, (nome, tipo, pagina, reserva) in ({} if so_noticias else LIGAS).items():
            uuid = uuid_atual(pagina, reserva)
            if pagina in usou_reserva:
                falhas.append(f"{nome}: UUID da edição não encontrado na página do ge, usado o reserva")
            try:
                d = fetch_liga(uuid)
                if tipo == "pontos":  # só a primeira fase entra na tabela simulada
                    primeira = d["fases"][0]["nome"]
                    d["partidas"] = [p for p in d["partidas"] if p[8] == primeira]
            except Exception as e:  # mantém o último dado gravado dessa liga
                print(f"{nome}: falhou ({e})")
                falhas.append(f"{nome}: {e}")
                continue
            if not d["partidas"]:
                print(f"{nome}: sem jogos, mantendo dados anteriores")
                continue

            with conn.transaction(), conn.cursor() as cur:
                cur.execute(
                    """insert into remo_ligas (liga, nome, tipo, zonas, fases, rodada_atual, atualizado_em)
                       values (%s, %s, %s, %s, %s, %s, now())
                       on conflict (liga) do update set nome = excluded.nome, tipo = excluded.tipo,
                         zonas = excluded.zonas, fases = excluded.fases,
                         rodada_atual = excluded.rodada_atual, atualizado_em = now()""",
                    (liga, nome, tipo, json.dumps(d["zonas"], ensure_ascii=False),
                     json.dumps(d["fases"], ensure_ascii=False), d["rodada_atual"]),
                )
                cur.execute("delete from remo_partidas where liga = %s", (liga,))
                cur.execute("delete from remo_clubes where liga = %s", (liga,))
                cur.executemany(
                    "insert into remo_clubes (liga, id, nome, abreviacao, escudo) values (%s, %s, %s, %s, %s)",
                    [(liga, *c) for c in d["clubes"].values()],
                )
                cur.executemany(
                    """insert into remo_partidas (liga, partida_id, rodada, data, casa_id, fora_id,
                         gols_casa, gols_fora, encerrada, fase, fase_ordem, chave, pen_casa, pen_fora,
                       estadio, hora_definida, link)
                       values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    [(liga, *p) for p in d["partidas"]],
                )
            print(f"{nome}: {tipo}, {len(d['clubes'])} clubes, {len(d['partidas'])} partidas, "
                  f"{sum(p[7] for p in d['partidas'])} encerradas.")

        falhas += sync_noticias(conn)

    if falhas:
        sys.exit("Atualização com falhas:\n" + "\n".join(f"- {f}" for f in falhas))


if __name__ == "__main__":
    main()
