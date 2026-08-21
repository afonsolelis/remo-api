"""Copa Libertadores via API de tabela do ge (mesmo cliente de ``copa.py``).

A edição tem fases preliminares e de grupos antes do mata-mata; a simulação
Monte Carlo roda a partir da fase atual do mata-mata (oitavas em diante) com
final em **jogo único** em campo neutro.

Clubes estrangeiros não existem no modelo da Série A. Para não tratá-los como
um time genérico fraco, a força (ataque/defesa) deles é estimada pela campanha
na própria fase de grupos da Libertadores, na mesma escala multiplicativa do
``PoissonBaseline`` (1.0 = média da competição), com encolhimento para a média
por serem poucos jogos.
"""

from . import copa

# Edição 2026 — o UUID muda a cada temporada (atributo
# ``data-bs-resource-id`` da página ge.globo.com/futebol/libertadores/).
TABELA_UUID = "83ad0ca5-f84e-4906-9242-a40d6585ebca"
NOME_PADRAO = "Libertadores"

# Mesmo encolhimento usado pelo PoissonBaseline da Série A.
SHRINK_GAMES = 5

jogos_do_time = copa.jogos_do_time


def fetch_bracket() -> dict:
    return copa.fetch_bracket(TABELA_UUID, NOME_PADRAO)


def fase_de_grupos(doc: dict) -> dict | None:
    """Fase de grupos da edição (a única com ``grupos`` preenchidos)."""
    return next((f for f in doc.get("fases", []) if f.get("grupos")), None)


def forca_por_grupos(doc: dict) -> dict[int, tuple[float, float]]:
    """Estimativa (ataque, defesa) de cada clube pela fase de grupos.

    ``ataque`` > 1 marca mais que a média da competição; ``defesa`` < 1 sofre
    menos. Sem fase de grupos disponível devolve dict vazio.
    """
    fase = fase_de_grupos(doc)
    if not fase:
        return {}
    linhas = [c for g in fase["grupos"] for c in g["classificacao"]
              if c.get("equipe_id") is not None and (c.get("jogos") or 0) > 0]
    total_gols = sum(int(c["gols_pro"] or 0) for c in linhas)
    total_jogos = sum(int(c["jogos"]) for c in linhas)  # cada jogo conta 2×
    if not total_jogos or not total_gols:
        return {}
    gpg = total_gols / total_jogos  # gols por time por jogo

    forca: dict[int, tuple[float, float]] = {}
    for c in linhas:
        jogos = int(c["jogos"])
        shrink = jogos / (jogos + SHRINK_GAMES)
        atk = shrink * (int(c["gols_pro"] or 0) / jogos) / gpg + (1 - shrink)
        dfn = shrink * (int(c["gols_contra"] or 0) / jogos) / gpg + (1 - shrink)
        forca[int(c["equipe_id"])] = (float(atk), float(dfn))
    return forca
