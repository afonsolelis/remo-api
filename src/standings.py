"""Classificação do Brasileirão calculada a partir dos resultados.

Critérios de desempate aplicados: pontos, vitórias, saldo de gols, gols pró.
(Confronto direto e cartões, usados pela CBF em empates persistentes, não são
aplicados aqui.)
"""

import pandas as pd

from .store import clube_nome


def compute_standings(played: pd.DataFrame, clubes: dict, all_team_ids: list[int]) -> pd.DataFrame:
    stats = {
        t: {"clube_id": t, "PTS": 0, "J": 0, "V": 0, "E": 0, "D": 0, "GP": 0, "GC": 0}
        for t in all_team_ids
    }
    for m in played.itertuples():
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        casa, fora = stats[m.casa_id], stats[m.fora_id]
        casa["J"] += 1
        fora["J"] += 1
        casa["GP"] += gc
        casa["GC"] += gf
        fora["GP"] += gf
        fora["GC"] += gc
        if gc > gf:
            casa["V"] += 1
            casa["PTS"] += 3
            fora["D"] += 1
        elif gc < gf:
            fora["V"] += 1
            fora["PTS"] += 3
            casa["D"] += 1
        else:
            casa["E"] += 1
            fora["E"] += 1
            casa["PTS"] += 1
            fora["PTS"] += 1

    df = pd.DataFrame(stats.values())
    df["SG"] = df["GP"] - df["GC"]
    df["Aproveitamento"] = (df["PTS"] / (df["J"] * 3).clip(lower=1) * 100).round(1)
    df["Time"] = df["clube_id"].map(lambda t: clube_nome(clubes, t))
    df = df.sort_values(["PTS", "V", "SG", "GP"], ascending=False).reset_index(drop=True)
    df.insert(0, "Pos", df.index + 1)
    return df


def team_last_results(played: pd.DataFrame, team_id: int, n: int = 5) -> list[str]:
    """Últimos n resultados do time: 'V', 'E' ou 'D' (mais recente por último)."""
    out = []
    mine = played[(played["casa_id"] == team_id) | (played["fora_id"] == team_id)]
    for m in mine.sort_values("timestamp").itertuples():
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        mandante = m.casa_id == team_id
        meus, deles = (gc, gf) if mandante else (gf, gc)
        out.append("V" if meus > deles else "E" if meus == deles else "D")
    return out[-n:]


def team_match_history(
    played: pd.DataFrame,
    clubes: dict,
    team_id: int,
) -> pd.DataFrame:
    """Campanha do time, jogo a jogo, com os totais após cada partida."""
    rows = []
    pontos = 0
    gols_pro = 0
    gols_contra = 0
    mine = played[(played["casa_id"] == team_id) | (played["fora_id"] == team_id)]

    for m in mine.sort_values(["timestamp", "partida_id"]).itertuples():
        em_casa = m.casa_id == team_id
        adversario_id = m.fora_id if em_casa else m.casa_id
        meus, deles = (
            (int(m.gols_casa), int(m.gols_fora))
            if em_casa
            else (int(m.gols_fora), int(m.gols_casa))
        )
        resultado = "V" if meus > deles else "E" if meus == deles else "D"
        pontos_jogo = 3 if resultado == "V" else 1 if resultado == "E" else 0
        pontos += pontos_jogo
        gols_pro += meus
        gols_contra += deles
        jogos = len(rows) + 1
        rows.append(
            {
                "rodada": int(m.rodada),
                "data": m.data,
                "adversario": clube_nome(clubes, adversario_id),
                "mando": "Casa" if em_casa else "Fora",
                "gols_pro": meus,
                "gols_contra": deles,
                "resultado": resultado,
                "pontos": pontos_jogo,
                "pontos_acumulados": pontos,
                "saldo_acumulado": gols_pro - gols_contra,
                "aproveitamento": pontos / (jogos * 3),
            }
        )

    return pd.DataFrame(rows)


def cumulative_points(played: pd.DataFrame, team_id: int) -> pd.DataFrame:
    """Pontos acumulados do time por rodada jogada."""
    rows = []
    total = 0
    mine = played[(played["casa_id"] == team_id) | (played["fora_id"] == team_id)]
    for m in mine.sort_values("timestamp").itertuples():
        gc, gf = int(m.gols_casa), int(m.gols_fora)
        mandante = m.casa_id == team_id
        meus, deles = (gc, gf) if mandante else (gf, gc)
        total += 3 if meus > deles else 1 if meus == deles else 0
        rows.append({"rodada": m.rodada, "pontos": total})
    return pd.DataFrame(rows)
