"""Formatação das ligas de pontos corridos do ge, sem rede."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import store
from src.liga import _faixas, _partida

CLASSIFICACAO = {
    "faixas_classificacao": [
        {"cor": "#0000ff", "nome": "Acesso à Série A"},
        {"cor": "#ff0000", "nome": "Rebaixados à Série C"},
    ],
    "classificacao": [
        {"ordem": 1, "faixa_classificacao_cor": "#0000ff"},
        {"ordem": 2, "faixa_classificacao_cor": "#0000ff"},
        {"ordem": 3, "faixa_classificacao_cor": None},
        {"ordem": 4, "faixa_classificacao_cor": "#ff0000"},
    ],
}

JOGO = {
    "id": 349357,
    "data_realizacao": "2026-08-28T19:30",
    "placar_oficial_mandante": 2,
    "placar_oficial_visitante": 1,
    "sede": {"nome_popular": "Serrinha"},
    "equipes": {
        "mandante": {"id": 290, "nome_popular": "Goiás", "sigla": "GOI"},
        "visitante": {"id": 2880, "nome_popular": "São Bernardo", "sigla": "SBD"},
    },
}


def test_faixas_saem_do_regulamento_publicado():
    faixas = {f["nome"]: f["posicoes"] for f in _faixas(CLASSIFICACAO)}
    assert faixas == {"Acesso à Série A": [1, 2], "Rebaixados à Série C": [4]}


def test_faixa_sobrevive_a_empate_na_ordem():
    """O ge repete ``ordem`` em empate (a Série C traz …4, 5, 5, 7…): a faixa
    precisa continuar sendo um intervalo contíguo do tamanho certo."""
    payload = {
        "faixas_classificacao": [{"cor": "#0000ff", "nome": "Classificados"}],
        "classificacao": [
            {"ordem": 1, "faixa_classificacao_cor": "#0000ff"},
            {"ordem": 2, "faixa_classificacao_cor": "#0000ff"},
            {"ordem": 2, "faixa_classificacao_cor": "#0000ff"},
            {"ordem": 4, "faixa_classificacao_cor": "#0000ff"},
            {"ordem": 5, "faixa_classificacao_cor": None},
        ],
    }
    faixa = _faixas(payload)[0]
    assert faixa["posicoes"] == [1, 2, 3, 4]


def test_partida_no_formato_do_cartola():
    p = _partida(JOGO, rodada=25)
    # o mesmo shape que store.matches_df consome
    df = store.matches_df({"partidas": [p]})
    linha = df.iloc[0]
    assert linha["casa_id"] == 290 and linha["fora_id"] == 2880
    assert linha["gols_casa"] == 2 and linha["gols_fora"] == 1
    assert linha["rodada"] == 25 and linha["timestamp"] > 0


def test_chave_sem_os_dois_clubes_e_descartada():
    jogo = {**JOGO, "equipes": {"mandante": {}, "visitante": {}}}
    assert _partida(jogo, rodada=1) is None


if __name__ == "__main__":
    test_faixas_saem_do_regulamento_publicado()
    test_faixa_sobrevive_a_empate_na_ordem()
    test_partida_no_formato_do_cartola()
    test_chave_sem_os_dois_clubes_e_descartada()
    print("ok — formatação da liga validada")
