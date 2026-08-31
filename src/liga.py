"""Ligas de pontos corridos pela API de tabela do ge (Série B, C, D…).

Mesmo cliente HTTP da Copa (``copa.py``), outro formato de fase: aqui a
competição é um turno-returno inteiro. O retorno imita o snapshot do Cartola
(``clubes`` + ``partidas`` + ``status``), de modo que ``store.matches_df``,
``standings``, ``model`` e ``simulate`` funcionam sem adaptação.

Os ids de clube são os do SDE da Globo — os mesmos do Cartola —, então um
clube mantém o id ao subir ou descer de divisão.

O regulamento (quantas vagas de acesso, playoff e rebaixamento) não fica
cravado aqui: vem das faixas coloridas que a própria API publica na
classificação, o que mantém o código válido quando o formato muda.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .copa import BASE_URL, _get


@dataclass(frozen=True)
class Liga:
    chave: str              # identificador interno (coleção/arquivo no store)
    nome: str
    tabela_uuid: str = ""   # fonte ge — muda a cada temporada
    espn_slug: str = ""     # fonte ESPN (ex.: "usa.1")
    historico: str = ""     # arquivo do football-data para treinar o XGBoost


# Edição 2026 — o UUID está no atributo ``data-bs-resource-id`` da página
# ge.globo.com/futebol/brasileirao-serie-b/.
SERIE_B = Liga(
    chave="serie_b",
    nome="Brasileirão Série B",
    tabela_uuid="009b5a68-dd09-46b8-95b3-293a2d494366",
)

# A Série C é turno único: a primeira fase classifica oito para os
# quadrangulares. Enquanto a fase seguinte não é sorteada, o ge devolve
# ``grupos: []`` e só a tabela da fase corrente existe.
SERIE_C = Liga(
    chave="serie_c",
    nome="Brasileirão Série C",
    tabela_uuid="1339e172-bd81-4490-af97-27ff29b9c3df",
)

# A MLS vem da ESPN: o ge não cobre a liga, e o football-data publica o
# histórico dela desde 2012 no mesmo formato do Brasileirão.
MLS = Liga(
    chave="mls",
    nome="Major League Soccer",
    espn_slug="usa.1",
    historico="USA.csv",
)

LIGAS = {liga.chave: liga for liga in (SERIE_B, SERIE_C, MLS)}


def _timestamp(data_realizacao: str | None) -> float | None:
    if not data_realizacao:
        return None
    try:
        return datetime.fromisoformat(data_realizacao).timestamp()
    except ValueError:
        return None


def _clube(equipe: dict) -> dict:
    """Clube no formato do snapshot do Cartola."""
    escudo = equipe.get("escudo")
    return {
        "id": equipe.get("id"),
        "nome": equipe.get("nome_popular"),
        "apelido": equipe.get("nome_popular"),
        "abreviacao": equipe.get("sigla"),
        "escudos": {tam: escudo for tam in ("30x30", "45x45", "60x60")},
    }


def _partida(jogo: dict, rodada: int) -> dict | None:
    """Partida no formato de ``data["partidas"]`` do Cartola."""
    equipes = jogo.get("equipes") or {}
    mandante = equipes.get("mandante") or {}
    visitante = equipes.get("visitante") or {}
    if mandante.get("id") is None or visitante.get("id") is None:
        return None
    data = jogo.get("data_realizacao")
    return {
        "rodada": rodada,
        "partida_id": jogo.get("id"),
        "partida_data": data,
        "timestamp": _timestamp(data),
        "local": (jogo.get("sede") or {}).get("nome_popular"),
        "clube_casa_id": mandante["id"],
        "clube_visitante_id": visitante["id"],
        "placar_oficial_mandante": jogo.get("placar_oficial_mandante"),
        "placar_oficial_visitante": jogo.get("placar_oficial_visitante"),
    }


def _faixas(classificacao: dict) -> list[dict]:
    """Zonas da tabela (acesso, playoff, rebaixamento) e suas posições.

    ``ordem`` se repete quando há empate na tabela do ge (a Série C traz
    ``…4, 5, 5, 7…``), então a faixa é reconstruída como um intervalo
    contíguo: tantas posições quantos forem os clubes marcados com a cor.
    """
    nomes = {f["cor"]: f["nome"] for f in classificacao.get("faixas_classificacao", [])}
    ordens: dict[str, list[int]] = {}
    for time_ in classificacao.get("classificacao", []):
        cor = time_.get("faixa_classificacao_cor")
        if cor in nomes:
            ordens.setdefault(cor, []).append(int(time_["ordem"]))
    return [
        {
            "nome": nomes[cor],
            "cor": cor,
            "posicoes": list(range(min(pos), min(pos) + len(pos))),
        }
        for cor, pos in ordens.items()
    ]


def fetch_liga(liga: Liga = SERIE_B) -> dict:
    """Baixa classificação e todas as rodadas da edição corrente."""
    if liga.espn_slug:
        from . import espn

        return espn.fetch_liga(liga)
    classificacao = _get(f"{BASE_URL}/{liga.tabela_uuid}/classificacao/")
    fase = classificacao["fase"]["slug"]
    rodada = classificacao.get("rodada") or {}
    ultima = int(rodada.get("ultima") or 0)
    edicao = classificacao.get("edicao") or {}

    clubes: dict[str, dict] = {}
    partidas = []
    for r in range(1, ultima + 1):
        jogos = _get(f"{BASE_URL}/{liga.tabela_uuid}/fase/{fase}/rodada/{r}/jogos/")
        for jogo in jogos:
            partida = _partida(jogo, r)
            if not partida:
                continue  # rodada ainda sem os dois clubes definidos
            partidas.append(partida)
            for equipe in (jogo["equipes"]["mandante"], jogo["equipes"]["visitante"]):
                clubes.setdefault(str(equipe["id"]), _clube(equipe))

    if not partidas:
        # fase corrente sem jogos por rodada (ex.: grupos ainda não sorteados)
        # — quem chamou preserva o documento anterior
        raise RuntimeError(f"{liga.nome}: fase {fase} não tem jogos por rodada")

    inicio = edicao.get("data_inicio") or ""
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "chave": liga.chave,
        "nome": liga.nome,
        "clubes": clubes,
        "partidas": partidas,
        "faixas": _faixas(classificacao),
        "fase": {
            "slug": fase,
            "nome": next((f["nome"] for f in classificacao.get("fases_navegacao", [])
                          if f.get("atual")), None),
        },
        "status": {
            "temporada": int(inicio[:4]) if inicio[:4].isdigit() else None,
            "rodada_atual": int(rodada.get("atual") or 1),
            "rodada_final": ultima,
            "nome": edicao.get("nome") or liga.nome,
        },
    }
