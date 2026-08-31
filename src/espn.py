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


def _rank(entrada: dict) -> int | None:
    for stat in entrada.get("stats") or []:
        if stat.get("name") == "rank" and stat.get("value") is not None:
            return int(stat["value"])
    return None


def _grupos_e_faixas(slug: str) -> tuple[dict[str, str], list[dict], bool]:
    """Mapa clube -> grupo, faixas de classificação, e se há conferências.

    As faixas saem das notas que a ESPN publica em cada clube ("Champions
    League", "Relegation", "Qualifies for MLS Cup Playoffs - …") — o mesmo
    princípio das faixas coloridas do ge. A posição de cada faixa vem do
    ``rank`` de quem a carrega, e não da ordem do array, que não vem
    ordenado: assim uma faixa de rebaixamento cai na base da tabela, não no
    topo.
    """
    payload = _get(f"{BASE}/v2/sports/soccer/{slug}/standings")
    filhos = payload.get("children") or []
    tem_conferencias = len(filhos) > 1

    grupos: dict[str, str] = {}
    faixas: list[dict] = []
    for grupo in filhos:
        nome_grupo = (grupo.get("name") or grupo.get("abbreviation")
                      if tem_conferencias else None)
        entradas = ((grupo.get("standings") or {}).get("entries")) or []
        for e in entradas:
            if nome_grupo:
                grupos[str(e["team"]["id"])] = nome_grupo

        ranks: dict[str, list[int]] = {}
        for e in entradas:
            descricao = (e.get("note") or {}).get("description")
            posicao = _rank(e)
            if descricao and posicao:
                ranks.setdefault(descricao, []).append(posicao)
        for descricao, posicoes in ranks.items():
            inicio = min(posicoes)
            faixas.append({
                "grupo": nome_grupo,
                "nome": descricao.replace("Qualifies for ", ""),
                "posicoes": list(range(inicio, inicio + len(posicoes))),
            })
    faixas.sort(key=lambda f: (f["grupo"] or "", f["posicoes"][0]))
    return grupos, faixas, tem_conferencias


def _ano_inicial(cruzada: bool) -> int:
    """Ano em que a temporada corrente começou. Ligas europeias viram em
    julho; MLS e brasileiras seguem o ano civil."""
    agora = datetime.now(timezone.utc)
    if cruzada and agora.month < 7:
        return agora.year - 1
    return agora.year


def _janela(ano: int, cruzada: bool) -> str:
    if cruzada:
        return f"{ano}0701-{ano + 1}0630"
    return f"{ano}0101-{ano}1231"


def _eventos(slug: str, janela: str) -> list[dict]:
    """Eventos de uma janela, restritos à temporada dominante nela.

    Descarta o que não pertence à competição principal daquele intervalo —
    a ESPN mistura amistosos e jogos de exibição no mesmo calendário.
    """
    payload = _get(
        f"{BASE}/site/v2/sports/soccer/{slug}/scoreboard"
        f"?dates={janela}&limit=1000"
    )
    eventos = payload.get("events") or []
    if not eventos:
        return []
    contagem: dict[str, int] = {}
    for e in eventos:
        chave = (e.get("season") or {}).get("slug") or ""
        contagem[chave] = contagem.get(chave, 0) + 1
    dominante = max(contagem, key=contagem.get)
    eventos = [e for e in eventos
               if (e.get("season") or {}).get("slug") == dominante]
    eventos.sort(key=lambda e: e.get("date") or "")
    return eventos


def _monta(eventos: list[dict], validos: set[str]) -> tuple[dict, list[dict]]:
    """Clubes e partidas de uma temporada, no formato do snapshot do Cartola."""
    clubes: dict[str, dict] = {}
    partidas = []
    for evento in eventos:
        partida = _partida(evento, rodada=0)
        if not partida:
            continue
        # o jogo das estrelas da MLS entra como temporada regular: só valem
        # confrontos entre clubes que a classificação reconhece
        if (str(partida["clube_casa_id"]) not in validos
                or str(partida["clube_visitante_id"]) not in validos):
            continue
        partidas.append(partida)
        for lado in evento["competitions"][0]["competitors"]:
            clubes.setdefault(str(lado["team"]["id"]), _clube(lado["team"]))

    # a ESPN não numera rodadas; a semana de calendário serve para a UI
    if partidas:
        base = min(p["timestamp"] for p in partidas)
        for p in partidas:
            p["rodada"] = int((p["timestamp"] - base) // (7 * 86400)) + 1
    return clubes, partidas


def fetch_liga(liga) -> dict:
    """Temporada corrente da liga, com a anterior anexada para treino.

    Ligas europeias começam em agosto: com poucas rodadas jogadas, a
    temporada passada é a única informação de peso disponível. Ela vem da
    mesma fonte, com os mesmos ids de clube, e entra apenas no treino dos
    modelos — a tabela exibida é só da temporada corrente.
    """
    cruzada = bool(getattr(liga, "temporada_cruzada", False))
    ano = _ano_inicial(cruzada)
    grupos, faixas, tem_conferencias = _grupos_e_faixas(liga.espn_slug)

    eventos = _eventos(liga.espn_slug, _janela(ano, cruzada))
    if not eventos:
        raise RuntimeError(f"{liga.nome}: temporada sem jogos na ESPN")
    validos = set(grupos) if grupos else {
        str(lado["team"]["id"]) for e in eventos
        for lado in e["competitions"][0]["competitors"]
    }
    clubes, partidas = _monta(eventos, validos)

    anteriores: list[dict] = []
    if getattr(liga, "usa_temporada_anterior", False):
        try:
            passados = _eventos(liga.espn_slug, _janela(ano - 1, cruzada))
            ids_passados = {
                str(lado["team"]["id"]) for e in passados
                for lado in e["competitions"][0]["competitors"]
            }
            _, anteriores = _monta(passados, ids_passados)
        except Exception:
            anteriores = []  # o treino cai para a temporada corrente

    rodadas = [p["rodada"] for p in partidas]
    disputados = [p for p in partidas if p["placar_oficial_mandante"] is not None]
    return {
        "partidas_anteriores": anteriores,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "chave": liga.chave,
        "nome": liga.nome,
        "clubes": clubes,
        "partidas": partidas,
        "grupos": grupos,
        "faixas": faixas,
        "fase": {"slug": "temporada", "nome": "Temporada regular"},
        "status": {
            "temporada": ano,
            "rodada_atual": max((p["rodada"] for p in disputados), default=1),
            "rodada_final": max(rodadas, default=1),
            "nome": f"{liga.nome} {ano}/{str(ano + 1)[2:]}" if cruzada
                    else f"{liga.nome} {ano}",
        },
    }
