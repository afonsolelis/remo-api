"""Cliente da API pública do Cartola FC (https://api.cartola.globo.com)."""

import requests

BASE_URL = "https://api.cartola.globo.com"
TIMEOUT = 20

_session = requests.Session()
_session.headers.update({"User-Agent": "remo-api/0.1 (uso pessoal, local)"})


def get_status() -> dict:
    """Status do mercado: rodada_atual, temporada, rodada_final etc."""
    r = _session.get(f"{BASE_URL}/mercado/status", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_partidas(rodada: int) -> dict:
    """Partidas de uma rodada: {'clubes': {...}, 'partidas': [...], 'rodada': n}."""
    r = _session.get(f"{BASE_URL}/partidas/{rodada}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_atletas_mercado() -> dict:
    """Mercado de atletas: plantel de todos os clubes com preço, média, status
    e scout agregado da temporada."""
    r = _session.get(f"{BASE_URL}/atletas/mercado", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_pontuados(rodada: int) -> dict:
    """Pontuação e scout de cada atleta que jogou na rodada."""
    r = _session.get(f"{BASE_URL}/atletas/pontuados/{rodada}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()
