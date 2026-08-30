"""Série D via API de tabela do ge (mesmo cliente de ``copa.py``).

Duas particularidades em relação à Copa e à Libertadores:

- **Os playoffs de acesso correm em paralelo ao título.** Os quatro
  semifinalistas já garantiram a vaga na Série C; os playoffs definem as
  outras duas entre clubes eliminados antes. Essa fase aparece no
  chaveamento da página, mas fica fora da contagem de fases até o título —
  senão os rótulos da simulação saem deslocados.
- **Nenhum clube está na Série A**, então o modelo da elite não conhece a
  força de nenhum deles. Ela é estimada pela campanha no próprio mata-mata,
  na mesma escala multiplicativa do ``PoissonBaseline`` (1.0 = média da
  competição), com encolhimento para a média por serem poucos jogos.
"""

from . import copa

# Edição 2026 — o UUID muda a cada temporada (atributo
# ``data-bs-resource-id`` da página ge.globo.com/futebol/brasileirao-serie-d/).
TABELA_UUID = "5b2a5692-2d5c-47e8-8b24-be84447b62fd"
NOME_PADRAO = "Série D"

# Mesmo encolhimento usado pelo PoissonBaseline da Série A.
SHRINK_GAMES = 5

jogos_do_time = copa.jogos_do_time


def fora_do_titulo(fase: dict) -> bool:
    """Fases que não fazem parte do caminho até o título."""
    return "acesso" in (fase.get("nome") or "").lower()


def fetch_bracket() -> dict:
    return copa.fetch_bracket(TABELA_UUID, NOME_PADRAO)


def forca_por_chaveamento(doc: dict) -> dict[int, tuple[float, float]]:
    """Estimativa (ataque, defesa) de cada clube pelos jogos já disputados.

    ``ataque`` > 1 marca mais que a média da competição; ``defesa`` < 1 sofre
    menos. Sem jogos com placar devolve dict vazio.
    """
    gols_pro: dict[int, int] = {}
    gols_contra: dict[int, int] = {}
    jogos: dict[int, int] = {}
    for fase in doc.get("fases", []):
        for chave in fase.get("chaves") or []:
            for jogo in chave.get("jogos") or []:
                casa, fora = jogo.get("mandante_id"), jogo.get("visitante_id")
                gm, gv = jogo.get("gols_mandante"), jogo.get("gols_visitante")
                if casa is None or fora is None or gm is None or gv is None:
                    continue
                for time_, marcou, sofreu in ((casa, gm, gv), (fora, gv, gm)):
                    gols_pro[time_] = gols_pro.get(time_, 0) + int(marcou)
                    gols_contra[time_] = gols_contra.get(time_, 0) + int(sofreu)
                    jogos[time_] = jogos.get(time_, 0) + 1

    total_gols = sum(gols_pro.values())
    total_jogos = sum(jogos.values())
    if not total_jogos or not total_gols:
        return {}
    gpg = total_gols / total_jogos  # gols por time por jogo

    forca: dict[int, tuple[float, float]] = {}
    for time_, n in jogos.items():
        shrink = n / (n + SHRINK_GAMES)
        atk = shrink * (gols_pro[time_] / n) / gpg + (1 - shrink)
        dfn = shrink * (gols_contra[time_] / n) / gpg + (1 - shrink)
        forca[int(time_)] = (float(atk), float(dfn))
    return forca
