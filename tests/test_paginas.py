"""Executa cada página do dashboard e falha em qualquer exceção não tratada."""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

PAGINAS = ["brasileirao", "serie_b", "copa", "libertadores"]

# a página do Brasileirão empilha todas as seções da Série A, nesta ordem
SECOES = [
    "⚽ Remo", "📊 Classificação", "📅 Próximos jogos", "🔮 Simulações",
    "🎯 Melhor cenário", "👥 Elenco", "📋 Partidas", "🧠 Modelo",
]


def _roda(pagina: str) -> AppTest:
    at = AppTest.from_file(str(RAIZ / "pages" / f"{pagina}.py"), default_timeout=180)
    at.run()
    return at


def test_todas_as_paginas_renderizam():
    for pagina in PAGINAS:
        at = _roda(pagina)
        assert not at.exception, (
            f"{pagina}: {[e.value for e in at.exception]}"
        )
        print(f"  {pagina}: ok · {len(at.dataframe)} tabelas · "
              f"{len(at.markdown)} blocos de texto")


def test_serie_b_tem_suas_secoes():
    at = _roda("serie_b")
    assert [h.value for h in at.header] == [
        "📊 Classificação", "🔮 Simulações", "🎯 Melhor cenário",
        "📅 Próximos jogos", "🧠 Modelo",
    ]
    # a divisão tem seletor próprio: o do cabeçalho é de clubes da Série A
    assert "Time em destaque na Série B" in [s.label for s in at.selectbox]


def test_brasileirao_empilha_todas_as_secoes():
    at = _roda("brasileirao")
    assert [h.value for h in at.header] == SECOES

    titulos = [s.value for s in at.subheader]
    assert "O que o Remo precisa fazer" in titulos
    assert "O que precisa acontecer nos outros jogos" in titulos


if __name__ == "__main__":
    test_todas_as_paginas_renderizam()
    test_brasileirao_empilha_todas_as_secoes()
    test_serie_b_tem_suas_secoes()
    print("ok — páginas renderizam e as seções aparecem na ordem esperada")
