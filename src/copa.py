"""Copa do Brasil via API de tabela do ge (api.globoesporte.globo.com).

Os IDs de clube são os mesmos do Cartola (base SDE da Globo), então o modelo
de previsão da Série A funciona direto nos confrontos entre clubes da elite.

O cliente da API é genérico (``fetch_bracket(tabela_uuid)``) e também serve a
Libertadores (``src/libertadores.py``): fases de mata-mata viram ``chaves`` e
fases de pontos corridos em grupos viram ``grupos``.

Também contém a simulação Monte Carlo do mata-mata: ida e volta por Poisson,
agregado, pênaltis 50/50, chaveamento padrão (O1×O2, O3×O4… nas fases
seguintes), mando futuro alternado e, opcionalmente, final em jogo único.
"""

import re

import numpy as np
import requests

# Edição 2026 — o UUID muda a cada temporada (está no atributo
# ``data-bs-resource-id`` da página ge.globo.com/futebol/copa-do-brasil/).
TABELA_UUID = "11c5766c-f8f6-4e1b-b5e0-7309f67b54e9"
BASE_URL = "https://api.globoesporte.globo.com/tabela"
TIMEOUT = 20

_session = requests.Session()
_session.headers.update({"User-Agent": "Mozilla/5.0 (remo-api; uso pessoal)"})


def _get(url: str) -> dict:
    r = _session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _parse_jogo(j: dict) -> dict:
    eq = j.get("equipes", {})
    m, v = eq.get("mandante", {}), eq.get("visitante", {})
    return {
        "mandante_id": m.get("id"),
        "mandante": m.get("nome_popular"),
        "mandante_escudo": m.get("escudo"),
        "visitante_id": v.get("id"),
        "visitante": v.get("nome_popular"),
        "visitante_escudo": v.get("escudo"),
        "data": j.get("data_realizacao"),
        "hora": j.get("hora_realizacao"),
        "sede": (j.get("sede") or {}).get("nome_popular"),
        "gols_mandante": j.get("placar_oficial_mandante"),
        "gols_visitante": j.get("placar_oficial_visitante"),
        "pen_mandante": j.get("placar_penaltis_mandante"),
        "pen_visitante": j.get("placar_penaltis_visitante"),
    }


def _parse_chaves(payload: dict) -> list[dict]:
    chaves = []
    for secao in payload.get("secao", []):
        for c in secao.get("chave", []):
            chaves.append({
                "nome": c.get("nome"),
                "jogos": [_parse_jogo(j) for j in c.get("jogos", [])
                          if j.get("exibir_jogo", True)],
            })
    return chaves


def _parse_grupos(payload: dict) -> list[dict]:
    """Fases de pontos corridos em grupos (ex.: fase de grupos da
    Libertadores): classificação de cada grupo, já ordenada pela API."""
    grupos = []
    for g in payload.get("grupos", []):
        tabela = []
        for c in g.get("classificacao", []):
            tabela.append({
                "ordem": c.get("ordem"),
                "equipe_id": c.get("equipe_id"),
                "nome": c.get("nome_popular"),
                "sigla": c.get("sigla"),
                "escudo": c.get("escudo"),
                "pontos": c.get("pontos"),
                "jogos": c.get("jogos"),
                "vitorias": c.get("vitorias"),
                "empates": c.get("empates"),
                "derrotas": c.get("derrotas"),
                "gols_pro": c.get("gols_pro"),
                "gols_contra": c.get("gols_contra"),
                "saldo_gols": c.get("saldo_gols"),
                "faixa_cor": c.get("faixa_classificacao_cor"),
            })
        grupos.append({"nome": g.get("nome_grupo"), "classificacao": tabela})
    return grupos


def _numero_chave(nome: str | None) -> int:
    m = re.search(r"(\d+)\s*$", nome or "")
    return int(m.group(1)) if m else 0


def ordenar_chaves(chaves: list[dict]) -> list[dict]:
    """Ordena as chaves pelo número no nome ("Oitavas 1", "Oitavas 2", …).

    A API devolve as chaves agrupadas em seções (os pares da fase seguinte),
    não necessariamente em ordem; a simulação assume O1×O2, O3×O4, … ."""
    if all(_numero_chave(c.get("nome")) for c in chaves):
        return sorted(chaves, key=lambda c: _numero_chave(c.get("nome")))
    return list(chaves)


def fetch_bracket(tabela_uuid: str = TABELA_UUID,
                  nome_padrao: str = "Copa do Brasil") -> dict:
    """Todas as fases da edição: {'edicao', 'fase_atual', 'fases': [{slug,
    nome, atual, chaves, grupos}]} — uma requisição por fase, sem
    autenticação. ``chaves`` vem de fases de mata-mata e ``grupos`` de fases
    de pontos corridos em grupos (lista vazia quando não se aplica)."""
    atual = _get(f"{BASE_URL}/{tabela_uuid}/classificacao/")
    fases = []
    for f in atual.get("fases_navegacao", []):
        slug = f["slug"]
        try:
            payload = atual if f.get("atual") else _get(
                f"{BASE_URL}/{tabela_uuid}/fase/{slug}/classificacao/")
            chaves = ordenar_chaves(_parse_chaves(payload))
            grupos = _parse_grupos(payload)
        except Exception:
            chaves, grupos = [], []
        fases.append({"slug": slug, "nome": f.get("nome"), "atual": bool(f.get("atual")),
                      "chaves": chaves, "grupos": grupos})
    return {
        "edicao": atual.get("edicao", {}).get("nome", nome_padrao),
        "fase_atual": atual.get("fase", {}).get("slug"),
        "fases": fases,
    }


def jogos_do_time(doc: dict, team_id: int) -> list[dict]:
    """Campanha do time na competição (todas as fases, em ordem)."""
    out = []
    for fase in doc.get("fases", []):
        for chave in fase.get("chaves", []):
            for j in chave.get("jogos", []):
                if team_id in (j.get("mandante_id"), j.get("visitante_id")):
                    out.append({**j, "fase": fase.get("nome")})
    return out


# ---------------------------------------------------------------- simulação

# Fator de força para clubes fora da Série A (sem dados no nosso modelo):
# ataque abaixo e defesa acima da média da elite.
UNKNOWN_ATK = 0.85
UNKNOWN_DEF = 1.15


def simulate_knockout(
    ties: list[dict],
    lam_pair,
    n_sims: int = 5000,
    seed: int = 7,
    final_jogo_unico: bool = False,
):
    """Simula o mata-mata a partir da fase atual.

    ``ties``: lista de chaves da fase atual, cada uma com ``jogos`` (ida/volta,
    placares preenchidos quando já disputados). ``lam_pair(h, a)`` devolve
    (lam_casa, lam_fora) para um jogo h×a. Com ``final_jogo_unico`` a última
    rodada é decidida em partida única em campo neutro (Libertadores): as
    taxas de gols são a média do jogo em casa e fora de cada lado. Retorna
    dict team_id -> [P(avançar fase 1), P(avançar fase 2), …] até o título.
    """
    rng = np.random.default_rng(seed)

    # times na ordem das chaves: [A1, B1, A2, B2, …]
    teams: list[int] = []
    for t in ties:
        j0 = t["jogos"][0]
        teams.append(j0["mandante_id"])
        teams.append(j0["visitante_id"])
    idx = {t: i for i, t in enumerate(teams)}
    n_t = len(teams)

    lam_h = np.zeros((n_t, n_t))
    lam_a = np.zeros((n_t, n_t))
    for i, ti in enumerate(teams):
        for k, tk in enumerate(teams):
            if i == k:
                continue
            lam_h[i, k], lam_a[i, k] = lam_pair(ti, tk)

    def _leg(home_idx, away_idx):
        lh = lam_h[home_idx, away_idx]
        la = lam_a[home_idx, away_idx]
        return rng.poisson(lh), rng.poisson(la)

    n_rounds = int(np.log2(n_t))
    alive = np.tile(np.arange(n_t), (n_sims, 1))  # (n_sims, times vivos)
    advanced = np.zeros((n_rounds, n_t))

    for rodada in range(n_rounds):
        n_ties = alive.shape[1] // 2
        winners = np.zeros((n_sims, n_ties), dtype=int)
        for k in range(n_ties):
            a = alive[:, 2 * k]
            b = alive[:, 2 * k + 1]
            if rodada == 0 and k < len(ties):
                # usa mando real e placares já disputados da fase atual
                jogos = ties[k]["jogos"]
                ga = np.zeros(n_sims)
                gb = np.zeros(n_sims)
                for j in jogos:
                    hi = idx[j["mandante_id"]]
                    ai = idx[j["visitante_id"]]
                    if j["gols_mandante"] is not None:
                        gm = float(j["gols_mandante"])
                        gv = float(j["gols_visitante"])
                    else:
                        gm, gv = _leg(np.full(n_sims, hi), np.full(n_sims, ai))
                    # soma no agregado de cada lado da chave
                    ga = ga + np.where(a == hi, gm, gv)
                    gb = gb + np.where(b == hi, gm, gv)
                    if j.get("pen_mandante") is not None:
                        # disputa de pênaltis já realizada decide o agregado
                        pen_vence_m = j["pen_mandante"] > j["pen_visitante"]
                        ga = ga + np.where(a == hi, 0.5 if pen_vence_m else -0.5,
                                           -0.5 if pen_vence_m else 0.5)
            elif final_jogo_unico and rodada == n_rounds - 1:
                # final única em campo neutro: média do mando de cada lado
                la = (lam_h[a, b] + lam_a[b, a]) / 2
                lb = (lam_a[a, b] + lam_h[b, a]) / 2
                ga = rng.poisson(la).astype(float)
                gb = rng.poisson(lb).astype(float)
            else:
                g1m, g1v = _leg(a, b)  # ida: A manda
                g2m, g2v = _leg(b, a)  # volta: B manda
                ga = g1m + g2v
                gb = g1v + g2m
            empate = ga == gb
            penaltis = rng.random(n_sims) < 0.5
            a_vence = (ga > gb) | (empate & penaltis)
            winners[:, k] = np.where(a_vence, a, b)
        alive = winners
        for t in range(n_t):
            advanced[rodada, t] = (alive == t).any(axis=1).mean()

    return {teams[t]: advanced[:, t].tolist() for t in range(n_t)}
