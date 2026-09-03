"""Persistência dos dados da API do Cartola.

Dois backends, escolhidos pela variável de ambiente ``MONGO_URL``:

- **MongoDB** (arquitetura Docker): snapshot atual na coleção ``season``
  (documento ``_id="current"``) e um snapshot por dia em ``season_daily``.
  O serviço ``updater`` do docker-compose atualiza 2x ao dia.
- **JSON local** (execução direta, sem Docker): ``data/season.json`` +
  ``data/daily/season-AAAA-MM-DD.json``; ``load_or_refresh`` refaz o download
  quando o arquivo está mais velho que ``max_age_hours``.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import cartola

logger = logging.getLogger(__name__)

MONGO_URL = os.environ.get("MONGO_URL", "").strip()
_mongo_client = None


def _mongo():
    global _mongo_client
    from pymongo import MongoClient

    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    return _mongo_client["remo"]

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SEASON_FILE = DATA_DIR / "season.json"
PROJECTION_FILE = DATA_DIR / "projection.json"
VISITS_FILE = DATA_DIR / "visits.json"

REMO_ID = 364

# A API só traz sigla ("VAS"), apelido ("Gigante da Colina") e slug sem acento
# ("sao-paulo") — nomes reais mapeados aqui, com fallback para o slug.
NOMES_REAIS = {
    262: "Flamengo",
    263: "Botafogo",
    264: "Corinthians",
    265: "Bahia",
    266: "Fluminense",
    267: "Vasco",
    275: "Palmeiras",
    276: "São Paulo",
    277: "Santos",
    280: "Red Bull Bragantino",
    282: "Atlético-MG",
    283: "Cruzeiro",
    284: "Grêmio",
    285: "Internacional",
    287: "Vitória",
    293: "Athletico-PR",
    294: "Coritiba",
    315: "Chapecoense",
    364: "Remo",
    2305: "Mirassol",
}

# Um jogo é considerado encerrado este tempo depois do apito inicial.
MATCH_DURATION_S = 2 * 3600


def register_visit() -> int | None:
    """Registra uma nova sessão e devolve o total acumulado de visitas."""
    updated_at = datetime.now(timezone.utc).isoformat()
    try:
        if MONGO_URL:
            from pymongo import ReturnDocument

            doc = _mongo().metrics.find_one_and_update(
                {"_id": "visits"},
                {"$inc": {"count": 1}, "$set": {"updated_at": updated_at}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return int(doc["count"])

        count = 0
        if VISITS_FILE.exists():
            count = int(json.loads(VISITS_FILE.read_text()).get("count", 0))
        count += 1
        DATA_DIR.mkdir(exist_ok=True)
        VISITS_FILE.write_text(
            json.dumps(
                {"count": count, "updated_at": updated_at},
                ensure_ascii=False,
            )
        )
        return count
    except Exception:
        # A métrica é opcional e nunca deve impedir a abertura do dashboard.
        return None


def refresh() -> dict:
    """Baixa a temporada inteira da API e grava em data/season.json."""
    status = cartola.get_status()
    rodada_final = status.get("rodada_final", 38)

    clubes: dict = {}
    partidas: list = []
    for rodada in range(1, rodada_final + 1):
        payload = cartola.get_partidas(rodada)
        clubes.update(payload.get("clubes", {}))
        for p in payload.get("partidas", []):
            p["rodada"] = rodada
            partidas.append(p)
        time.sleep(0.15)  # educado com a API

    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "clubes": clubes,
        "partidas": partidas,
    }
    hoje = datetime.now().strftime("%Y-%m-%d")
    if MONGO_URL:
        db = _mongo()
        db.season.replace_one({"_id": "current"}, {"_id": "current", **data}, upsert=True)
        db.season_daily.replace_one({"_id": hoje}, {"_id": hoje, **data}, upsert=True)
    else:
        DATA_DIR.mkdir(exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False)
        SEASON_FILE.write_text(payload)
        daily_dir = DATA_DIR / "daily"
        daily_dir.mkdir(exist_ok=True)
        (daily_dir / f"season-{hoje}.json").write_text(payload)

    try:
        refresh_atletas(status)  # plantel + pontuações por rodada
    except Exception:
        pass  # partidas/classificação seguem valendo mesmo se atletas falhar
    try:
        refresh_copa()  # chaveamento da Copa do Brasil (API do ge)
    except Exception:
        pass
    try:
        refresh_libertadores()  # grupos + chaveamento da Libertadores (API do ge)
    except Exception:
        pass
    try:
        refresh_ligas()  # Séries B e C em pontos corridos (API do ge)
    except Exception:
        pass
    try:
        refresh_serie_d()  # chaveamento da Série D (API do ge)
    except Exception:
        pass
    return data


ATLETAS_FILE = DATA_DIR / "atletas.json"
PONTUADOS_DIR = DATA_DIR / "pontuados"


def _store_atletas(doc: dict):
    hoje = datetime.now().strftime("%Y-%m-%d")
    if MONGO_URL:
        db = _mongo()
        db.atletas.replace_one({"_id": "current"}, {"_id": "current", **doc}, upsert=True)
        db.atletas_daily.replace_one({"_id": hoje}, {"_id": hoje, **doc}, upsert=True)
    else:
        DATA_DIR.mkdir(exist_ok=True)
        ATLETAS_FILE.write_text(json.dumps(doc, ensure_ascii=False))


def load_atletas() -> dict | None:
    if MONGO_URL:
        doc = _mongo().atletas.find_one({"_id": "current"})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    if ATLETAS_FILE.exists():
        return json.loads(ATLETAS_FILE.read_text())
    return None


def _stored_pontuados_rounds() -> set[int]:
    if MONGO_URL:
        return {d["_id"] for d in _mongo().pontuados.find({}, {"_id": 1})}
    if PONTUADOS_DIR.exists():
        return {int(f.stem.split("-")[1]) for f in PONTUADOS_DIR.glob("rodada-*.json")}
    return set()


def _store_pontuados(rodada: int, payload: dict):
    if MONGO_URL:
        _mongo().pontuados.replace_one({"_id": rodada}, {"_id": rodada, **payload},
                                       upsert=True)
    else:
        PONTUADOS_DIR.mkdir(parents=True, exist_ok=True)
        (PONTUADOS_DIR / f"rodada-{rodada:02d}.json").write_text(
            json.dumps(payload, ensure_ascii=False))


def load_pontuados_all() -> dict[int, dict]:
    """Todas as rodadas com pontuação armazenada: {rodada: payload}."""
    out: dict[int, dict] = {}
    if MONGO_URL:
        for d in _mongo().pontuados.find({}):
            out[int(d.pop("_id"))] = d
        return out
    if PONTUADOS_DIR.exists():
        for f in sorted(PONTUADOS_DIR.glob("rodada-*.json")):
            out[int(f.stem.split("-")[1])] = json.loads(f.read_text())
    return out


COPA_FILE = DATA_DIR / "copa.json"


def _store_copa(doc: dict):
    if MONGO_URL:
        _mongo().copa.replace_one({"_id": "bracket"}, {"_id": "bracket", **doc},
                                  upsert=True)
    else:
        DATA_DIR.mkdir(exist_ok=True)
        COPA_FILE.write_text(json.dumps(doc, ensure_ascii=False))


def load_copa() -> dict | None:
    if MONGO_URL:
        doc = _mongo().copa.find_one({"_id": "bracket"})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    if COPA_FILE.exists():
        return json.loads(COPA_FILE.read_text())
    return None


def refresh_copa() -> dict:
    from . import copa

    doc = copa.fetch_bracket()
    doc["fetched_at"] = datetime.now(timezone.utc).isoformat()
    _store_copa(doc)
    return doc


def ensure_copa(max_age_hours: float = 24.0) -> dict:
    doc = load_copa()
    if doc:
        fetched_at = datetime.fromisoformat(doc["fetched_at"])
        age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        if age_h < max_age_hours:
            return doc
    return refresh_copa()


LIBERTADORES_FILE = DATA_DIR / "libertadores.json"


def _store_libertadores(doc: dict):
    if MONGO_URL:
        _mongo().libertadores.replace_one(
            {"_id": "bracket"}, {"_id": "bracket", **doc}, upsert=True)
    else:
        DATA_DIR.mkdir(exist_ok=True)
        LIBERTADORES_FILE.write_text(json.dumps(doc, ensure_ascii=False))


def load_libertadores() -> dict | None:
    if MONGO_URL:
        doc = _mongo().libertadores.find_one({"_id": "bracket"})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    if LIBERTADORES_FILE.exists():
        return json.loads(LIBERTADORES_FILE.read_text())
    return None


def refresh_libertadores() -> dict:
    from . import libertadores

    doc = libertadores.fetch_bracket()
    doc["fetched_at"] = datetime.now(timezone.utc).isoformat()
    _store_libertadores(doc)
    return doc


def ensure_libertadores(max_age_hours: float = 24.0) -> dict:
    doc = load_libertadores()
    if doc:
        fetched_at = datetime.fromisoformat(doc["fetched_at"])
        age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        if age_h < max_age_hours:
            return doc
    return refresh_libertadores()


SERIE_D_FILE = DATA_DIR / "serie_d.json"


def _store_serie_d(doc: dict):
    if MONGO_URL:
        _mongo().serie_d.replace_one({"_id": "bracket"},
                                     {"_id": "bracket", **doc}, upsert=True)
    else:
        DATA_DIR.mkdir(exist_ok=True)
        SERIE_D_FILE.write_text(json.dumps(doc, ensure_ascii=False))


def load_serie_d() -> dict | None:
    if MONGO_URL:
        doc = _mongo().serie_d.find_one({"_id": "bracket"})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    if SERIE_D_FILE.exists():
        return json.loads(SERIE_D_FILE.read_text())
    return None


def refresh_serie_d() -> dict:
    from . import serie_d

    doc = serie_d.fetch_bracket()
    doc["fetched_at"] = datetime.now(timezone.utc).isoformat()
    _store_serie_d(doc)
    return doc


LIGA_FILE = DATA_DIR / "ligas"


def _store_liga(doc: dict):
    chave = doc["chave"]
    if MONGO_URL:
        _mongo().ligas.replace_one({"_id": chave}, {"_id": chave, **doc},
                                   upsert=True)
    else:
        LIGA_FILE.mkdir(parents=True, exist_ok=True)
        (LIGA_FILE / f"{chave}.json").write_text(
            json.dumps(doc, ensure_ascii=False)
        )


def load_liga(chave: str = "serie_b") -> dict | None:
    if MONGO_URL:
        doc = _mongo().ligas.find_one({"_id": chave})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    arquivo = LIGA_FILE / f"{chave}.json"
    if arquivo.exists():
        return json.loads(arquivo.read_text())
    return None


def refresh_liga(chave: str = "serie_b") -> dict:
    from . import liga

    doc = liga.fetch_liga(liga.LIGAS[chave])
    _store_liga(doc)
    return doc


def refresh_ligas() -> None:
    """Atualiza cada liga por conta própria: uma falha não derruba as outras."""
    from . import liga

    for chave in liga.LIGAS:
        try:
            refresh_liga(chave)
        except Exception as exc:
            # A liga mantém o último documento válido, mas o worker precisa
            # deixar a causa visível. Antes, um 403 da ESPN era descartado e
            # a execução terminava com uma mensagem enganosa de sucesso.
            logger.warning(
                "Falha ao atualizar %s: %s: %s",
                liga.LIGAS[chave].nome,
                type(exc).__name__,
                exc,
            )


def ensure_liga(chave: str = "serie_b", max_age_hours: float = 24.0) -> dict:
    doc = load_liga(chave)
    if doc:
        fetched_at = datetime.fromisoformat(doc["fetched_at"])
        age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        if age_h < max_age_hours:
            return doc
    return refresh_liga(chave)


def refresh_atletas(status: dict | None = None) -> dict:
    """Baixa o mercado de atletas (plantel + estatísticas da temporada) e as
    pontuações por rodada que ainda faltam (rodadas antigas são imutáveis)."""
    status = status or cartola.get_status()
    mercado = cartola.get_atletas_mercado()
    doc = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "posicoes": mercado.get("posicoes", {}),
        "status_atletas": mercado.get("status", {}),
        "atletas": mercado.get("atletas", []),
    }
    _store_atletas(doc)

    rodada_atual = status.get("rodada_atual", 1)
    ja_tem = _stored_pontuados_rounds()
    for r in range(1, rodada_atual + 1):
        if r in ja_tem and r < rodada_atual - 1:
            continue
        try:
            p = cartola.get_pontuados(r)
        except Exception:
            continue
        if p and p.get("atletas"):
            _store_pontuados(r, {"rodada": r, "atletas": p["atletas"]})
        time.sleep(0.1)
    return doc


def ensure_atletas(max_age_hours: float = 24.0) -> dict:
    doc = load_atletas()
    if doc:
        fetched_at = datetime.fromisoformat(doc["fetched_at"])
        age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        if age_h < max_age_hours:
            return doc
    return refresh_atletas()


def load_snapshot() -> dict | None:
    """Último snapshot salvo (Mongo ou JSON), sem bater na API."""
    if MONGO_URL:
        doc = _mongo().season.find_one({"_id": "current"})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    if SEASON_FILE.exists():
        return json.loads(SEASON_FILE.read_text())
    return None


def save_projection(doc: dict) -> None:
    """Persiste o último pacote de projeções gerado pelo updater."""
    if MONGO_URL:
        _mongo().projections.replace_one(
            {"_id": "current"}, {"_id": "current", **doc}, upsert=True
        )
    else:
        DATA_DIR.mkdir(exist_ok=True)
        PROJECTION_FILE.write_text(json.dumps(doc, ensure_ascii=False))


def load_projection() -> dict | None:
    """Carrega projeções sem treinar modelos ou chamar APIs externas."""
    if MONGO_URL:
        doc = _mongo().projections.find_one({"_id": "current"})
        if doc:
            doc.pop("_id", None)
            return doc
        return None
    if PROJECTION_FILE.exists():
        return json.loads(PROJECTION_FILE.read_text())
    return None


def load_or_refresh(max_age_hours: float = 24.0) -> dict:
    data = load_snapshot()
    if data:
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        age_h = (datetime.now(timezone.utc) - fetched_at).total_seconds() / 3600
        if age_h < max_age_hours:
            return data
    return refresh()


def matches_df(data: dict) -> pd.DataFrame:
    """Todas as partidas da temporada em um DataFrame.

    Nota: ``valida: false`` no Cartola marca jogos antecipados/adiados que não
    contam para o fantasy naquela rodada — mas são jogos reais do Brasileirão
    e contam para a tabela, então entram aqui.
    """
    rows = []
    for p in data["partidas"]:
        rows.append(
            {
                "rodada": p["rodada"],
                "partida_id": p["partida_id"],
                "data": p.get("partida_data"),
                "timestamp": p.get("timestamp"),
                "local": p.get("local"),
                "casa_id": p["clube_casa_id"],
                "fora_id": p["clube_visitante_id"],
                "gols_casa": p.get("placar_oficial_mandante"),
                "gols_fora": p.get("placar_oficial_visitante"),
            }
        )
    df = pd.DataFrame(rows)
    df["gols_casa"] = pd.to_numeric(df["gols_casa"], errors="coerce")
    df["gols_fora"] = pd.to_numeric(df["gols_fora"], errors="coerce")
    return df.sort_values(["timestamp", "partida_id"]).reset_index(drop=True)


def split_played_future(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa jogos encerrados (com placar oficial) dos jogos futuros."""
    now = time.time()
    ended = df["timestamp"].fillna(0) + MATCH_DURATION_S < now
    has_score = df["gols_casa"].notna() & df["gols_fora"].notna()
    played = df[ended & has_score].copy()
    future = df[~(ended & has_score)].copy()
    return played, future


def clube_nome(clubes: dict, clube_id: int) -> str:
    if clube_id in NOMES_REAIS:
        return NOMES_REAIS[clube_id]
    c = clubes.get(str(clube_id)) or clubes.get(clube_id) or {}
    slug = c.get("slug")
    if slug:
        return slug.replace("-", " ").title()
    return c.get("apelido") or c.get("nome") or str(clube_id)


def clube_escudo(clubes: dict, clube_id: int, size: str = "30x30") -> str | None:
    c = clubes.get(str(clube_id)) or clubes.get(clube_id) or {}
    return (c.get("escudos") or {}).get(size)
