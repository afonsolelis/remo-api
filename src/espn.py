"""Ligas internacionais pela API pública da ESPN (MLS e afins).

Terceira fonte do projeto, ao lado do Cartola e do ge. O placar e o
calendário inteiro da temporada vêm numa requisição só; a classificação
traz a divisão em conferências e as faixas de classificação aos playoffs.

O retorno imita o snapshot do Cartola (``clubes`` + ``partidas`` +
``status``), como em ``liga.py``, e acrescenta ``grupos`` — o mapa de clube
para conferência — para que a tabela seja calculada dentro de cada uma.

Como toda fonte remota, é tratada como não confiável: quem chama preserva o
último documento válido se algo falhar.
"""

from datetime import datetime, timezone

import requests

BASE = "https://site.api.espn.com/apis"
TIMEOUT = 40

_session = requests.Session()
_session.headers.update({"User-Agent": "Mozilla/5.0 (remo-api; uso pessoal)"})


def _get(url: str) -> dict:
    r = _session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _clube(team: dict) -> dict:
    """Clube no formato do snapshot do Cartola."""
    escudo = team.get("logo") or (team.get("logos") or [{}])[0].get("href")
    return {
        "id": int(team["id"]),
        "nome": team.get("displayName"),
        "apelido": team.get("shortDisplayName") or team.get("displayName"),
        "abreviacao": team.get("abbreviation"),
        "escudos": {tam: escudo for tam in ("30x30", "45x45", "60x60")},
    }


def _partida(evento: dict, rodada: int) -> dict | None:
    """Partida no formato de ``data["partidas"]`` do Cartola."""
    competicao = (evento.get("competitions") or [{}])[0]
    casa = fora = None
    for lado in competicao.get("competitors") or []:
        if lado.get("homeAway") == "home":
            casa = lado
        elif lado.get("homeAway") == "away":
            fora = lado
    if not casa or not fora:
        return None

    encerrado = (evento.get("status") or {}).get("type", {}).get("completed")
    def placar(lado):
        if not encerrado:
            return None
        try:
            return int(lado.get("score"))
        except (TypeError, ValueError):
            return None

    quando = evento.get("date")  # ISO em UTC, ex.: 2026-08-30T23:30Z
    try:
        instante = datetime.fromisoformat(quando.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None

    return {
        "rodada": rodada,
        "partida_id": int(evento["id"]),
        "partida_data": instante.isoformat(),
        "timestamp": instante.timestamp(),
        "local": ((competicao.get("venue") or {}).get("fullName")),
        "clube_casa_id": int(casa["team"]["id"]),
        "clube_visitante_id": int(fora["team"]["id"]),
        "placar_oficial_mandante": placar(casa),
        "placar_oficial_visitante": placar(fora),
    }


def _conferencias(slug: str) -> tuple[dict[str, str], list[dict]]:
    """Mapa clube -> conferência e as faixas de classificação de cada uma.

    As faixas saem das notas que a própria ESPN publica ("Qualifies for MLS
    Cup Playoffs - …"), contadas por descrição — o mesmo princípio usado com
    as faixas coloridas do ge. A lista de entradas **não vem ordenada**, por
    isso a posição é recalculada por pontos.
    """
    payload = _get(f"{BASE}/v2/sports/soccer/{slug}/standings")
    grupos: dict[str, str] = {}
    faixas: list[dict] = []
    for grupo in payload.get("children") or []:
        nome_grupo = grupo.get("name") or grupo.get("abbreviation")
        entradas = ((grupo.get("standings") or {}).get("entries")) or []
        for e in entradas:
            grupos[str(e["team"]["id"])] = nome_grupo

        # tamanho de cada faixa = quantos clubes carregam aquela nota
        contagem: dict[str, int] = {}
        for e in entradas:
            descricao = (e.get("note") or {}).get("description")
            if descricao:
                contagem[descricao] = contagem.get(descricao, 0) + 1
        posicao = 1
        # da nota mais forte para a mais fraca: a ESPN descreve a fase que o
        # clube alcança, e quem entra direto aparece antes do repescagem
        for descricao in sorted(contagem, key=lambda d: "Wild Card" in d):
            n = contagem[descricao]
            faixas.append({
                "grupo": nome_grupo,
                "nome": descricao.replace("Qualifies for ", ""),
                "posicoes": list(range(posicao, posicao + n)),
            })
            posicao += n
    return grupos, faixas


def fetch_liga(liga) -> dict:
    """Temporada regular inteira da liga: uma requisição de calendário e uma
    de classificação. ``liga`` é um ``liga.Liga`` com ``espn_slug``."""
    ano = datetime.now(timezone.utc).year
    payload = _get(
        f"{BASE}/site/v2/sports/soccer/{liga.espn_slug}/scoreboard"
        f"?dates={ano}0101-{ano}1231&limit=1000"
    )
    eventos = [
        e for e in payload.get("events") or []
        if (e.get("season") or {}).get("slug") == "regular-season"
    ]
    if not eventos:
        raise RuntimeError(f"{liga.nome}: temporada regular sem jogos na ESPN")
    eventos.sort(key=lambda e: e.get("date") or "")
    grupos, faixas = _conferencias(liga.espn_slug)

    clubes: dict[str, dict] = {}
    partidas = []
    for evento in eventos:
        # a ESPN não numera rodadas; a data serve de referência para a UI
        partida = _partida(evento, rodada=0)
        if not partida:
            continue
        # o jogo das estrelas entra como temporada regular na ESPN: só valem
        # confrontos entre clubes que a classificação reconhece
        if (str(partida["clube_casa_id"]) not in grupos
                or str(partida["clube_visitante_id"]) not in grupos):
            continue
        partidas.append(partida)
        for lado in evento["competitions"][0]["competitors"]:
            clubes.setdefault(str(lado["team"]["id"]), _clube(lado["team"]))

    # rodada aproximada por semana de calendário, só para agrupar a UI
    if partidas:
        base = min(p["timestamp"] for p in partidas)
        for p in partidas:
            p["rodada"] = int((p["timestamp"] - base) // (7 * 86400)) + 1

    rodadas = [p["rodada"] for p in partidas]
    disputados = [p for p in partidas if p["placar_oficial_mandante"] is not None]
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "chave": liga.chave,
        "nome": liga.nome,
        "clubes": clubes,
        "partidas": partidas,
        "grupos": grupos,
        "faixas": faixas,
        "fase": {"slug": "regular-season", "nome": "Temporada regular"},
        "status": {
            "temporada": ano,
            "rodada_atual": max((p["rodada"] for p in disputados), default=1),
            "rodada_final": max(rodadas, default=1),
            "nome": f"{liga.nome} {ano}",
        },
    }
