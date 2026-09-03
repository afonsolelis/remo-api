import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.standings import team_match_history


def test_team_match_history_calculates_running_campaign() -> None:
    played = pd.DataFrame(
        [
            {
                "rodada": 1,
                "partida_id": 10,
                "data": "2026-04-01T19:00:00",
                "timestamp": 100,
                "casa_id": 1,
                "fora_id": 2,
                "gols_casa": 2,
                "gols_fora": 0,
            },
            {
                "rodada": 2,
                "partida_id": 11,
                "data": "2026-04-08T21:00:00",
                "timestamp": 200,
                "casa_id": 3,
                "fora_id": 1,
                "gols_casa": 1,
                "gols_fora": 1,
            },
            {
                "rodada": 3,
                "partida_id": 12,
                "data": "2026-04-15T21:00:00",
                "timestamp": 300,
                "casa_id": 1,
                "fora_id": 3,
                "gols_casa": 0,
                "gols_fora": 3,
            },
        ]
    )
    clubes = {
        "1": {"apelido": "Remo"},
        "2": {"apelido": "Rival A"},
        "3": {"apelido": "Rival B"},
    }

    history = team_match_history(played, clubes, team_id=1)

    assert history["resultado"].tolist() == ["V", "E", "D"]
    assert history["mando"].tolist() == ["Casa", "Fora", "Casa"]
    assert history["gols_pro"].tolist() == [2, 1, 0]
    assert history["gols_contra"].tolist() == [0, 1, 3]
    assert history["pontos_acumulados"].tolist() == [3, 4, 4]
    assert history["saldo_acumulado"].tolist() == [2, 2, -1]
    esperado = [1, 2 / 3, 4 / 9]
    assert all(
        math.isclose(atual, previsto)
        for atual, previsto in zip(history["aproveitamento"], esperado)
    )


if __name__ == "__main__":
    test_team_match_history_calculates_running_campaign()
    print("ok — histórico de partidas validado")
