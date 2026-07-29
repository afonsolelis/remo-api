"""Renderização das páginas do dashboard Streamlit.

Dados: API pública do Cartola FC. Atualização automática 1x ao dia.
Previsões: XGBoost, Poisson, Poisson temporal e Ensemble (todos leves);
simulação Monte Carlo do restante da temporada.

Este módulo é executado por cada arquivo em ``pages/`` com ``SELECTED_PAGE``
definido. Manter a renderização aqui evita duplicar o contexto e os componentes
durante a migração do antigo layout baseado em abas.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import store
from src.evaluate import backtest
from src.history import load_historical
from src.copa import jogos_do_time, simulate_knockout
from src.model import (
    MODEL_LABELS,
    PoissonBaseline,
    available_model_keys,
    make_predictor,
    outcome_probs,
)
from src.simulate import simulate_season
from src.standings import compute_standings, cumulative_points, team_last_results
from src.store import REMO_ID
from src.viz import (
    BLUE,
    BLUE_LIGHT,
    GRAY,
    ORANGE,
    OTHERS,
    SURFACE,
    apply_layout,
    pct,
)

FORM_ICON = {"V": "🟢", "E": "⚪", "D": "🔴"}


# ---------------------------------------------------------------- dados

@st.cache_data(ttl=3600, show_spinner="Baixando dados do Cartola…")
def load_data() -> dict:
    return store.load_or_refresh(max_age_hours=24)


def get_historical() -> pd.DataFrame | None:
    """Temporadas 2012+ para treino (None se estiver offline sem cache)."""
    try:
        return load_historical()
    except Exception:
        return None


@st.cache_data(show_spinner="Rodando o backtest (treina cada modelo por rodada)…")
def run_backtest(fetched_at: str, n_rounds: int) -> pd.DataFrame:
    data = store.load_or_refresh()
    played, _ = store.split_played_future(store.matches_df(data))
    return backtest(played, n_rounds=n_rounds, historical=get_historical())


@st.cache_data(show_spinner="Rodando simulações…")
def run_sim(fetched_at: str, model_key: str, n_sims: int) -> dict:
    data = store.load_or_refresh()
    df = store.matches_df(data)
    played, future = store.split_played_future(df)
    team_ids = sorted(set(df["casa_id"]) | set(df["fora_id"]))

    predictor = make_predictor(model_key, played, get_historical())
    lam_h, lam_a = predictor.predict(future, played)
    res = simulate_season(played, future, lam_h, lam_a, team_ids, n_sims=n_sims)
    p_home, p_draw, p_away = outcome_probs(lam_h, lam_a)
    fixtures = future.copy()
    fixtures["p_casa"] = p_home
    fixtures["p_empate"] = p_draw
    fixtures["p_fora"] = p_away
    return {"res": res, "fixtures": fixtures, "model": predictor.name,
            "lam_h": lam_h, "lam_a": lam_a}


# placar atribuído a cada palpite (afeta o saldo de gols)
PICK_SCORES = {"casa": (1, 0), "empate": (1, 1), "fora": (0, 1)}


@st.cache_data(show_spinner="Simulando com seus palpites…")
def run_sim_palpites(fetched_at: str, model_key: str, n_sims: int,
                     picks_tuple: tuple) -> dict:
    """Monte Carlo condicionado: jogos com palpite ficam travados no resultado
    escolhido; o resto segue as taxas do modelo."""
    base = run_sim(fetched_at, model_key, n_sims)
    fixtures = base["fixtures"]
    picks = dict(picks_tuple)
    fixed = {
        j: PICK_SCORES[picks[m.partida_id]]
        for j, m in enumerate(fixtures.itertuples())
        if m.partida_id in picks
    }
    data = store.load_or_refresh()
    df = store.matches_df(data)
    played, _ = store.split_played_future(df)
    team_ids = sorted(set(df["casa_id"]) | set(df["fora_id"]))
    res = simulate_season(played, fixtures, base["lam_h"], base["lam_a"],
                          team_ids, n_sims=n_sims, fixed_scores=fixed)
    return {"res": res, "n_fixados": len(fixed)}


def refresh_everything():
    store.refresh()
    st.cache_data.clear()
    st.cache_resource.clear()


# ---------------------------------------------------------------- gráficos

def fig_pos_dist_remo(res, team_ids) -> go.Figure:
    i = team_ids.index(REMO_ID)
    probs = res.pos_dist[i]
    n = len(team_ids)
    labels = [pct(p) if p >= 0.01 else "" for p in probs]
    fig = go.Figure(
        go.Bar(
            x=[str(p) for p in range(1, n + 1)],
            y=probs,
            marker_color=BLUE,
            marker_line=dict(color=SURFACE, width=2),
            text=labels,
            textposition="outside",
            hovertemplate="Posição %{x}: %{customdata}<extra></extra>",
            customdata=[pct(p) for p in probs],
        )
    )
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    fig.update_xaxes(title_text="posição final", showgrid=False)
    fig.update_layout(showlegend=False)
    return apply_layout(fig, title="Onde o Remo termina o campeonato? (simulações)")


def fig_points_evolution(played) -> go.Figure:
    cum = cumulative_points(played, REMO_ID)
    fig = go.Figure(
        go.Scatter(
            x=cum["rodada"],
            y=cum["pontos"],
            mode="lines+markers",
            line=dict(color=BLUE, width=2),
            marker=dict(size=8, color=BLUE),
            hovertemplate="Rodada %{x}: %{y} pts<extra></extra>",
        )
    )
    fig.update_xaxes(title_text="rodada", dtick=2)
    fig.update_yaxes(title_text="pontos acumulados", rangemode="tozero")
    fig.update_layout(showlegend=False)
    return apply_layout(fig, title="Evolução de pontos do Remo")


def fig_prob_bar(names: list[str], values: np.ndarray, remo_mask: list[bool],
                 title: str) -> go.Figure:
    colors = [BLUE if r else OTHERS for r in remo_mask]
    fig = go.Figure(
        go.Bar(
            x=values,
            y=names,
            orientation="h",
            marker_color=colors,
            marker_line=dict(color=SURFACE, width=2),
            text=[pct(v) for v in values],
            textposition="outside",
            textfont=dict(color="#52514e"),
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    )
    fig.update_xaxes(tickformat=".0%", rangemode="tozero")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_layout(showlegend=False)
    return apply_layout(fig, height=max(220, 34 * len(names) + 90), title=title)


def fig_heatmap(res, clubes) -> go.Figure:
    order = np.argsort(-res.exp_pts)
    names = [store.clube_nome(clubes, res.team_ids[i]) for i in order]
    z = res.pos_dist[order]
    n = len(names)
    # Escala ancorada em probabilidades absolutas: zero fica visualmente vazio,
    # enquanto diferenças nas faixas mais úteis continuam fáceis de comparar.
    zmax = max(0.30, float(np.nanmax(z)))
    colorscale = [
        [0.0, "#ffffff"],
        [1e-9, "#f5f9ff"],
        [0.02 / zmax, "#dbeafe"],
        [0.10 / zmax, "#86b6ef"],
        [0.25 / zmax, BLUE],
        [1.0, "#0d366b"],
    ]
    tickvals = sorted({0.0, 0.02, 0.10, 0.25, zmax})
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[str(p) for p in range(1, n + 1)],
            y=names,
            colorscale=colorscale,
            zmin=0,
            zmax=zmax,
            xgap=2,
            ygap=2,
            colorbar=dict(
                tickvals=tickvals,
                ticktext=[pct(v, 0) for v in tickvals],
                outlinewidth=0,
                thickness=12,
            ),
            hovertemplate="%{y} — posição %{x}: %{z:.1%}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="posição final", side="top", showgrid=False)
    return apply_layout(fig, height=620,
                        title="Distribuição de posições finais (todas as equipes)")


def fig_next_matches(fixtures, clubes) -> go.Figure:
    labels, ph, pe, pa = [], [], [], []
    for m in fixtures.itertuples():
        casa = store.clube_nome(clubes, m.casa_id)
        fora = store.clube_nome(clubes, m.fora_id)
        dia = (m.data or "")[8:10] + "/" + (m.data or "")[5:7]
        labels.append(f"{casa} × {fora}  <span style='font-size:11px'>({dia})</span>")
        ph.append(m.p_casa)
        pe.append(m.p_empate)
        pa.append(m.p_fora)

    def trace(name, values, color, text_color):
        return go.Bar(
            name=name,
            x=values,
            y=labels,
            orientation="h",
            marker_color=color,
            marker_line=dict(color=SURFACE, width=2),
            text=[pct(v, 0) for v in values],
            textposition="inside",
            insidetextfont=dict(color=text_color, size=12),
            hovertemplate="%{y}<br>" + name + ": %{text}<extra></extra>",
        )

    fig = go.Figure([
        trace("Mandante vence", ph, BLUE, "#ffffff"),
        trace("Empate", pe, GRAY, "#ffffff"),
        trace("Visitante vence", pa, ORANGE, "#ffffff"),
    ])
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat=".0%", range=[0, 1], showgrid=False)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return apply_layout(fig, height=max(240, 44 * len(labels) + 110))


# ---------------------------------------------------------------- app

data = load_data()
clubes = data["clubes"]
status = data["status"]
df = store.matches_df(data)
played, future = store.split_played_future(df)
team_ids = sorted(set(df["casa_id"]) | set(df["fora_id"]))

model_key = st.session_state.get("model_key", "ensemble")
n_sims = st.session_state.get("n_sims", 5000)

_SIMULATION_PAGES = {"remo", "simulacoes", "simulador", "proximos_jogos"}
if SELECTED_PAGE in _SIMULATION_PAGES and future.empty:
    st.info("Temporada encerrada — não há jogos futuros para simular.")
    st.stop()

standings = compute_standings(played, clubes, team_ids)
if SELECTED_PAGE in _SIMULATION_PAGES:
    sim = run_sim(data["fetched_at"], model_key, n_sims)
    res = sim["res"]
    fixtures = sim["fixtures"]
    i_remo = team_ids.index(REMO_ID)

_rodada_atual = status.get("rodada_atual", 1)


def rotulo_rodada(r: int) -> str:
    """Rodadas antigas com jogo pendente são adiamentos (ex.: FLA×MIR da 4ª)."""
    return f"Rodada {r} · jogo adiado" if r < _rodada_atual else f"Rodada {r}"

if "palpites" not in st.session_state:
    st.session_state.palpites = {}  # partida_id -> "casa" | "empate" | "fora"

# ---- página Remo
if SELECTED_PAGE == "remo":
    remo_row = standings[standings["clube_id"] == REMO_ID].iloc[0]
    ultimos = team_last_results(played, REMO_ID)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Posição", f"{remo_row['Pos']}º")
    c2.metric("Pontos", int(remo_row["PTS"]))
    c3.metric("Jogos", int(remo_row["J"]))
    c4.metric("Aproveitamento", pct(remo_row["Aproveitamento"] / 100))
    c5.metric("Últimos 5", "".join(FORM_ICON[r] for r in ultimos))

    st.caption("Probabilidades nas simulações do restante da temporada "
               f"({res.n_sims:,} cenários · modelo: {sim['model']}):".replace(",", "."))
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("🏆 Título", pct(res.p_titulo[i_remo]))
    p2.metric("🌎 Libertadores (G4)", pct(res.p_g4[i_remo]))
    p3.metric("✈️ G6", pct(res.p_g6[i_remo]))
    p4.metric("🚨 Rebaixamento (Z4)", pct(res.p_z4[i_remo]))

    prox_remo = fixtures[(fixtures["casa_id"] == REMO_ID) | (fixtures["fora_id"] == REMO_ID)]
    if not prox_remo.empty:
        prox = prox_remo.iloc[0]
        casa = store.clube_nome(clubes, prox["casa_id"])
        fora = store.clube_nome(clubes, prox["fora_id"])
        st.info(f"**Próximo jogo:** {casa} × {fora} — {prox['data']} — {prox['local']}  \n"
                f"Mandante {pct(prox['p_casa'])} · Empate {pct(prox['p_empate'])} · "
                f"Visitante {pct(prox['p_fora'])}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(fig_pos_dist_remo(res, team_ids), width="stretch")
    with col_b:
        st.plotly_chart(fig_points_evolution(played), width="stretch")

    if not prox_remo.empty:
        prox_ordenados = prox_remo.sort_values("timestamp")
        st.subheader(f"Todos os próximos jogos do Remo ({len(prox_ordenados)} restantes)")
        exp_pts_restantes = float(
            (3 * prox_ordenados.apply(
                lambda m: m["p_casa"] if m["casa_id"] == REMO_ID else m["p_fora"], axis=1)
             + prox_ordenados["p_empate"]).sum()
        )
        st.caption(f"Pontos esperados nos jogos restantes: **+{exp_pts_restantes:.1f}** "
                   f"→ projeção final: **{res.exp_pts[i_remo]:.1f} pts** "
                   f"(modelo: {sim['model']}).")

        linhas = []
        for m in prox_ordenados.itertuples():
            em_casa = m.casa_id == REMO_ID
            adversario = store.clube_nome(clubes, m.fora_id if em_casa else m.casa_id)
            quando = pd.to_datetime(m.data)
            linhas.append({
                "Rodada": m.rodada,
                "Data": quando.strftime("%d/%m/%Y %H:%M"),
                "Adversário": adversario,
                "Mando": "🏠 Casa" if em_casa else "✈️ Fora",
                "Estádio": m.local,
                "Vitória do Remo": m.p_casa if em_casa else m.p_fora,
                "Empate": m.p_empate,
                "Derrota": m.p_fora if em_casa else m.p_casa,
            })
        tabela_remo = pd.DataFrame(linhas)
        st.dataframe(
            tabela_remo,
            hide_index=True,
            height=38 * (len(tabela_remo) + 1) + 3,
            column_config={
                c: st.column_config.ProgressColumn(
                    c, format="percent", min_value=0, max_value=1)
                for c in ["Vitória do Remo", "Empate", "Derrota"]
            },
        )
        st.plotly_chart(fig_next_matches(prox_ordenados, clubes), width="stretch")

    st.divider()
    st.subheader("🏅 Outras competições do Remo em 2026")
    oc1, oc2 = st.columns(2)
    with oc1:
        st.markdown(
            """
**Campeonato Paraense** · jan–mar (encerrado)

🥈 **Vice-campeão** — o Leão fez a final do Parazão 2026,
mas o título ficou com o Paysandu (março/2026).
            """
        )
    with oc2:
        st.markdown(
            """
**Copa Verde** · mar–jun (encerrada)

O Remo **não disputou** a edição 2026. O campeão foi o
Paysandu, que virou sobre o Anápolis na final
(3×1 fora, 4×0 em casa em 07/06).
            """
        )
    st.caption("Fonte: ge/Globo. As competições do Remo ainda em andamento — "
               "Brasileirão e Copa do Brasil — estão nas abas ao lado, com "
               "simulações ao vivo.")

# ---- página Classificação
if SELECTED_PAGE == "classificacao":
    disp = standings.copy()
    disp["Escudo"] = disp["clube_id"].map(lambda t: store.clube_escudo(clubes, t))
    disp["Últimos 5"] = disp["clube_id"].map(
        lambda t: "".join(FORM_ICON[r] for r in team_last_results(played, t))
    )
    disp["Aproveitamento"] = disp["Aproveitamento"].map(lambda v: pct(v / 100))
    disp = disp.set_index("clube_id")[
        ["Pos", "Escudo", "Time", "PTS", "J", "V", "E", "D", "GP", "GC", "SG",
         "Aproveitamento", "Últimos 5"]
    ]
    styler = disp.style.apply(
        lambda row: [f"background-color: {BLUE_LIGHT}" if row.name == REMO_ID else ""] * len(row),
        axis=1,
    )
    st.dataframe(
        styler,
        hide_index=True,
        height=740,
        column_config={"Escudo": st.column_config.ImageColumn("", width=36)},
    )
    st.caption("Desempate: pontos, vitórias, saldo de gols e gols pró "
               "(confronto direto não é aplicado).")

# ---- página Partidas & elenco
STATUS_ICON = {"Provável": "🟢", "Dúvida": "🟡", "Suspenso": "🔴",
               "Contundido": "🚑", "Nulo": "⚪"}
SCOUT_COLS = ["G", "A", "FD", "FF", "DS", "FS", "DE", "SG", "CA", "CV"]
SCOUT_HELP = {"G": "Gols", "A": "Assistências", "FD": "Finalizações defendidas",
              "FF": "Finalizações para fora", "DS": "Desarmes",
              "FS": "Faltas sofridas", "DE": "Defesas",
              "SG": "Jogo sem sofrer gol", "CA": "Cartões amarelos",
              "CV": "Cartões vermelhos"}


@st.cache_data(ttl=3600, show_spinner="Carregando elencos e pontuações…")
def load_atletas_data(fetched_at: str):
    doc = store.ensure_atletas(max_age_hours=24)
    return doc, store.load_pontuados_all()


if SELECTED_PAGE in {"partidas", "elenco"}:
    atletas_doc, pontuados = load_atletas_data(data["fetched_at"])
    posicoes_map = {int(k): v["nome"] for k, v in atletas_doc["posicoes"].items()}
    status_map = {
        int(k): v["nome"] for k, v in atletas_doc["status_atletas"].items()
    }


if SELECTED_PAGE == "partidas":
    st.subheader("Estatísticas por partida")
    rodadas_scout = sorted(pontuados)
    if not rodadas_scout:
        st.info("Ainda não há pontuações armazenadas — atualize os dados.")
    else:
        c_r, c_j = st.columns([1, 3])
        with c_r:
            r_scout = st.selectbox("Rodada", rodadas_scout,
                                   index=len(rodadas_scout) - 1,
                                   format_func=lambda r: f"Rodada {r}",
                                   key="rodada_scout")
        jogos_r = played[played["rodada"] == r_scout].sort_values("timestamp")
        if jogos_r.empty:
            st.info("Nenhum jogo encerrado nessa rodada.")
        else:
            def _rotulo(pid):
                m = jogos_r[jogos_r["partida_id"] == pid].iloc[0]
                return (f"{store.clube_nome(clubes, m['casa_id'])} "
                        f"{int(m['gols_casa'])}×{int(m['gols_fora'])} "
                        f"{store.clube_nome(clubes, m['fora_id'])}")
            with c_j:
                pid_sel = st.selectbox("Partida", jogos_r["partida_id"].tolist(),
                                       format_func=_rotulo, key="partida_scout")
            m = jogos_r[jogos_r["partida_id"] == pid_sel].iloc[0]
            quando = pd.to_datetime(m["data"]).strftime("%d/%m/%Y %H:%M")
            st.markdown(f"### {_rotulo(pid_sel)}")
            st.caption(f"{quando} · {m['local']}")

            ats_rodada = pontuados[r_scout]["atletas"]

            def tabela_scout(clube_id: int) -> pd.DataFrame:
                linhas = []
                for a in ats_rodada.values():
                    if a.get("clube_id") != clube_id:
                        continue
                    scout = a.get("scout") or {}
                    linhas.append({
                        "Jogador": a.get("apelido", "?"),
                        "Pos": posicoes_map.get(a.get("posicao_id"), "?"),
                        "Pontos": a.get("pontuacao", 0.0),
                        **{c: scout.get(c, 0) for c in SCOUT_COLS},
                    })
                df_s = pd.DataFrame(linhas)
                return df_s.sort_values("Pontos", ascending=False) if not df_s.empty else df_s

            col_casa, col_fora = st.columns(2)
            for col, lado in ((col_casa, int(m["casa_id"])), (col_fora, int(m["fora_id"]))):
                with col:
                    st.markdown(f"**{store.clube_nome(clubes, lado)}**")
                    df_s = tabela_scout(lado)
                    if df_s.empty:
                        st.caption("Sem pontuação do Cartola para este clube nesta "
                                   "rodada (jogo antecipado/adiado não pontua).")
                    else:
                        st.dataframe(
                            df_s, hide_index=True,
                            height=min(560, 38 * (len(df_s) + 1) + 3),
                            column_config={
                                "Pontos": st.column_config.NumberColumn(format="%.1f"),
                                **{c: st.column_config.NumberColumn(
                                    c, help=SCOUT_HELP[c], width=44)
                                   for c in SCOUT_COLS},
                            },
                        )
            st.caption("Scout do Cartola — " +
                       " · ".join(f"**{c}** {SCOUT_HELP[c]}" for c in SCOUT_COLS))

    st.divider()
    st.subheader("Plantel e estatísticas da temporada")
    clube_plantel = st.selectbox("Clube", team_ids,
                                 index=team_ids.index(REMO_ID),
                                 format_func=lambda t: store.clube_nome(clubes, t))
    plantel = []
    for a in atletas_doc["atletas"]:
        if a.get("clube_id") != clube_plantel:
            continue
        scout = a.get("scout") or {}
        status_nome = status_map.get(a.get("status_id"), "?")
        plantel.append({
            "Foto": (a.get("foto") or "").replace("FORMATO", "140x140") or None,
            "Jogador": a.get("apelido", "?"),
            "Pos": posicoes_map.get(a.get("posicao_id"), "?"),
            "Status": f"{STATUS_ICON.get(status_nome, '')} {status_nome}",
            "Preço (C$)": a.get("preco_num", 0.0),
            "Média": a.get("media_num", 0.0),
            "Última": a.get("pontos_num", 0.0),
            "Jogos": a.get("jogos_num", 0),
            **{c: scout.get(c, 0) for c in SCOUT_COLS},
        })
    df_p = pd.DataFrame(plantel).sort_values(["Média", "Jogos"], ascending=False)
    st.dataframe(
        df_p, hide_index=True,
        height=min(740, 38 * (len(df_p) + 1) + 3),
        column_config={
            "Foto": st.column_config.ImageColumn("", width=40),
            "Preço (C$)": st.column_config.NumberColumn(format="%.2f"),
            "Média": st.column_config.NumberColumn(format="%.1f"),
            "Última": st.column_config.NumberColumn(format="%.1f"),
            **{c: st.column_config.NumberColumn(c, help=SCOUT_HELP[c], width=44)
               for c in SCOUT_COLS},
        },
    )
    st.caption("Fonte: mercado do Cartola (scout agregado da temporada). "
               "Preço e média são da pontuação Cartola, não do jogo real.")

# ---- página Copa do Brasil
@st.cache_data(ttl=3600, show_spinner="Carregando a Copa do Brasil…")
def load_copa_data(fetched_at: str) -> dict | None:
    try:
        return store.ensure_copa(max_age_hours=24)
    except Exception:
        return store.load_copa()


@st.cache_data(show_spinner="Simulando o mata-mata…")
def run_copa_sim(copa_fetched_at: str, cartola_fetched_at: str,
                 model_key: str, n_sims: int) -> dict | None:
    doc = store.load_copa()
    fase_atual = next((f for f in doc["fases"] if f["atual"]), None)
    ties = [c for c in fase_atual["chaves"] if c.get("jogos")]
    if not ties:
        return None

    data = store.load_or_refresh()
    df = store.matches_df(data)
    played, _ = store.split_played_future(df)
    serie_a = set(df["casa_id"]) | set(df["fora_id"])

    times_copa = []
    nomes = {}
    for t in ties:
        j0 = t["jogos"][0]
        times_copa += [j0["mandante_id"], j0["visitante_id"]]
        nomes[j0["mandante_id"]] = j0["mandante"]
        nomes[j0["visitante_id"]] = j0["visitante"]

    predictor = make_predictor(model_key, played, get_historical())
    base = PoissonBaseline().fit(played)
    pares = [(h, a) for h in times_copa for a in times_copa
             if h != a and h in serie_a and a in serie_a]
    conhecidos = {}
    if pares:
        fx = pd.DataFrame([{"casa_id": h, "fora_id": a} for h, a in pares])
        lh, la = predictor.predict(fx, played)
        conhecidos = {p: (float(lh[i]), float(la[i])) for i, p in enumerate(pares)}

    # clubes fora da Série A: força estimada abaixo da média da elite
    def lam_pair(h, a):
        if (h, a) in conhecidos:
            return conhecidos[(h, a)]
        atk_h = base.atk.get(h, 0.85)
        dfn_h = base.dfn.get(h, 1.15)
        atk_a = base.atk.get(a, 0.85)
        dfn_a = base.dfn.get(a, 1.15)
        return (
            float(np.clip(base.mu_home * atk_h * dfn_a, 0.05, 6.0)),
            float(np.clip(base.mu_away * atk_a * dfn_h, 0.05, 6.0)),
        )

    probs = simulate_knockout(ties, lam_pair, n_sims=n_sims)
    fases_seguintes = []
    achou = False
    for f in doc["fases"]:
        if achou:
            fases_seguintes.append(f["nome"])
        if f["atual"]:
            achou = True
    rotulos = fases_seguintes + ["🏆 Título"]
    return {"probs": probs, "rotulos": rotulos[:len(next(iter(probs.values())))],
            "nomes": nomes, "ties": ties, "fase_nome": fase_atual["nome"],
            "fora_serie_a": [t for t in times_copa if t not in serie_a]}


if SELECTED_PAGE == "copa":
    copa_doc = load_copa_data(data["fetched_at"])
    if not copa_doc:
        st.info("Não consegui carregar a Copa do Brasil agora — tente atualizar "
                "os dados pelo botão no cabeçalho.")
    else:
        sim_copa = run_copa_sim(copa_doc["fetched_at"], data["fetched_at"],
                                model_key, n_sims)
        st.markdown(f"### {copa_doc['edicao']} — "
                    f"{sim_copa['fase_nome'] if sim_copa else 'fase atual'}")

        if sim_copa and REMO_ID in sim_copa["probs"]:
            chave_remo = next(t for t in sim_copa["ties"]
                              if REMO_ID in (t["jogos"][0]["mandante_id"],
                                             t["jogos"][0]["visitante_id"]))
            st.subheader(f"🦁 {chave_remo['nome']}: "
                         f"{chave_remo['jogos'][0]['mandante']} × "
                         f"{chave_remo['jogos'][0]['visitante']}")
            for i, j in enumerate(chave_remo["jogos"], start=1):
                placar = (f" — **{int(j['gols_mandante'])}×{int(j['gols_visitante'])}**"
                          if j["gols_mandante"] is not None else "")
                dia = f"{(j['data'] or '')[8:10]}/{(j['data'] or '')[5:7]}"
                st.markdown(f"**Jogo {i}** ({'ida' if i == 1 else 'volta'}): "
                            f"{j['mandante']} × {j['visitante']}{placar} · "
                            f"{dia} {j['hora'] or ''} · {j['sede'] or 'a definir'}")

            p_remo = sim_copa["probs"][REMO_ID]
            cols = st.columns(len(p_remo))
            for c, rotulo, p in zip(cols, sim_copa["rotulos"], p_remo):
                c.metric(rotulo, pct(p))

        if sim_copa:
            st.subheader("Probabilidades de todos (simulação do chaveamento)")
            tabela_copa = pd.DataFrame([
                {"Time": sim_copa["nomes"].get(t, str(t)),
                 **{r: p for r, p in zip(sim_copa["rotulos"], ps)}}
                for t, ps in sim_copa["probs"].items()
            ]).sort_values(sim_copa["rotulos"][-1], ascending=False)
            st.dataframe(
                tabela_copa, hide_index=True,
                height=38 * (len(tabela_copa) + 1) + 3,
                column_config={r: st.column_config.ProgressColumn(
                    r, format="percent", min_value=0, max_value=1)
                    for r in sim_copa["rotulos"]},
            )
            fora = [sim_copa["nomes"][t] for t in sim_copa["fora_serie_a"]]
            aviso_fora = (f" Clubes fora da Série A ({', '.join(fora)}) entram com "
                          "força estimada abaixo da média da elite." if fora else "")
            st.caption("Ida e volta simulados por Poisson com o modelo selecionado "
                       "no cabeçalho; agregado empatado vai para pênaltis "
                       "(50/50); chaveamento padrão e mando das fases futuras "
                       f"alternado.{aviso_fora}")

            st.subheader("Confrontos da fase")
            for t in sim_copa["ties"]:
                linhas = []
                for j in t["jogos"]:
                    placar = (f"{int(j['gols_mandante'])}×{int(j['gols_visitante'])}"
                              if j["gols_mandante"] is not None else "—")
                    pen = (f" (pên. {int(j['pen_mandante'])}×{int(j['pen_visitante'])})"
                           if j["pen_mandante"] is not None else "")
                    dia = f"{(j['data'] or '')[8:10]}/{(j['data'] or '')[5:7]}"
                    linhas.append(f"{j['mandante']} {placar}{pen} {j['visitante']} · {dia}")
                st.markdown(f"**{t['nome']}** — " + "  |  ".join(linhas))

        campanha = jogos_do_time(copa_doc, REMO_ID)
        if campanha:
            with st.expander("Campanha do Remo na competição"):
                for j in campanha:
                    placar = (f"{int(j['gols_mandante'])}×{int(j['gols_visitante'])}"
                              if j["gols_mandante"] is not None else "a jogar")
                    pen = (f" (pên. {int(j['pen_mandante'])}×{int(j['pen_visitante'])})"
                           if j["pen_mandante"] is not None else "")
                    st.markdown(f"- **{j['fase']}**: {j['mandante']} {placar}{pen} "
                                f"{j['visitante']} · {j['data'] or ''}")


# ---- página Elenco do Remo (disponibilidade para o próximo jogo)
POS_ORDEM = {"Goleiro": 0, "Lateral": 1, "Zagueiro": 2, "Meia": 3,
             "Atacante": 4, "Técnico": 5}
FORMACAO_433 = {"Goleiro": 1, "Lateral": 2, "Zagueiro": 2, "Meia": 3,
                "Atacante": 3, "Técnico": 1}

if SELECTED_PAGE == "elenco":
    prox_remo = future[
        (future["casa_id"] == REMO_ID) | (future["fora_id"] == REMO_ID)
    ].sort_values("timestamp")
    elenco = []
    for a in atletas_doc["atletas"]:
        if a.get("clube_id") != REMO_ID:
            continue
        scout = a.get("scout") or {}
        ca = int(scout.get("CA", 0))
        status_nome = status_map.get(a.get("status_id"), "?")
        elenco.append({
            "foto": (a.get("foto") or "").replace("FORMATO", "140x140") or None,
            "jogador": a.get("apelido", "?"),
            "pos": posicoes_map.get(a.get("posicao_id"), "?"),
            "status": status_nome,
            "ca": ca,
            "ciclo": ca % 3,
            "pendurado": ca % 3 == 2,
            "cv": int(scout.get("CV", 0)),
            "media": a.get("media_num", 0.0),
            "jogos": a.get("jogos_num", 0),
            "preco": a.get("preco_num", 0.0),
        })
    elenco.sort(key=lambda e: (POS_ORDEM.get(e["pos"], 9), -e["media"]))

    if not prox_remo.empty:
        p = prox_remo.iloc[0]
        adversario = store.clube_nome(
            clubes, p["fora_id"] if p["casa_id"] == REMO_ID else p["casa_id"])
        mando = "em casa" if p["casa_id"] == REMO_ID else "fora"
        quando = pd.to_datetime(p["data"]).strftime("%d/%m às %H:%M")
        st.markdown(f"### Próximo jogo: **{adversario}** ({mando}), {quando} — "
                    f"{p['local']}")

    por_status = lambda s: [e for e in elenco if e["status"] == s]
    pendurados = [e for e in elenco if e["pendurado"] and e["status"] != "Nulo"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🟢 Prováveis", len(por_status("Provável")))
    c2.metric("🟡 Dúvidas", len(por_status("Dúvida")))
    c3.metric("🚑 Contundidos", len(por_status("Contundido")))
    c4.metric("🔴 Suspensos", len(por_status("Suspenso")))
    c5.metric("⚠️ Pendurados", len(pendurados))

    avisos = []
    if por_status("Suspenso"):
        avisos.append("🔴 **Suspensos:** "
                      + ", ".join(e["jogador"] for e in por_status("Suspenso")))
    if por_status("Contundido"):
        avisos.append("🚑 **Contundidos:** "
                      + ", ".join(e["jogador"] for e in por_status("Contundido")))
    if por_status("Dúvida"):
        avisos.append("🟡 **Dúvidas:** "
                      + ", ".join(e["jogador"] for e in por_status("Dúvida")))
    if pendurados:
        avisos.append("⚠️ **Pendurados (próximo amarelo suspende):** "
                      + ", ".join(f"{e['jogador']} ({e['ca']} CA)" for e in pendurados))
    if avisos:
        st.warning("  \n".join(avisos))
    else:
        st.success("Nenhum desfalque ou pendurado no momento. 🎉")

    st.subheader("Provável escalação (estimativa)")
    st.caption("Prováveis do mercado do Cartola escalados num 4-3-3 pela maior "
               "média — é uma estimativa estatística, não a escalação oficial.")
    titulares = []
    for pos, vagas in FORMACAO_433.items():
        aptos = [e for e in elenco if e["pos"] == pos and e["status"] == "Provável"]
        if len(aptos) < vagas:  # completa com dúvidas se faltar gente
            aptos += [e for e in elenco if e["pos"] == pos and e["status"] == "Dúvida"]
        titulares.extend(aptos[:vagas])
    df_tit = pd.DataFrame([{
        "Foto": e["foto"], "Jogador": e["jogador"], "Posição": e["pos"],
        "Status": f"{STATUS_ICON.get(e['status'], '')} {e['status']}",
        "Média": e["media"], "Preço (C$)": e["preco"],
    } for e in titulares])
    st.dataframe(
        df_tit, hide_index=True, height=38 * (len(df_tit) + 1) + 3,
        column_config={
            "Foto": st.column_config.ImageColumn("", width=40),
            "Média": st.column_config.NumberColumn(format="%.1f"),
            "Preço (C$)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    st.subheader("Situação completa do elenco")
    df_e = pd.DataFrame([{
        "Foto": e["foto"], "Jogador": e["jogador"], "Posição": e["pos"],
        "Status": f"{STATUS_ICON.get(e['status'], '')} {e['status']}",
        "Amarelos (ciclo)": f"{e['ciclo']}/3" + (" ⚠️" if e["pendurado"] else ""),
        "CA total": e["ca"], "CV": e["cv"],
        "Média": e["media"], "Jogos": e["jogos"], "Preço (C$)": e["preco"],
    } for e in elenco])
    st.dataframe(
        df_e, hide_index=True, height=min(740, 38 * (len(df_e) + 1) + 3),
        column_config={
            "Foto": st.column_config.ImageColumn("", width=40),
            "Média": st.column_config.NumberColumn(format="%.1f"),
            "Preço (C$)": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption("Status vem do mercado do Cartola (atualizado pela Globo ao longo "
               "da semana). O ciclo de amarelos é estimado pelo scout do Cartola: "
               "a cada 3 amarelos há suspensão automática — jogos antecipados/"
               "adiados não pontuam no Cartola e podem não entrar nessa conta.")

# ---- página Simulações
if SELECTED_PAGE == "simulacoes":
    st.caption(f"{res.n_sims:,} temporadas simuladas com o modelo "
               f"**{sim['model']}** · jogos restantes: {len(fixtures)}".replace(",", "."))

    probs_df = pd.DataFrame({
        "clube_id": res.team_ids,
        "Time": [store.clube_nome(clubes, t) for t in res.team_ids],
        "Pontos esperados": np.round(res.exp_pts, 1),
        "Título": res.p_titulo,
        "Libertadores (G4)": res.p_g4,
        "G6": res.p_g6,
        "Rebaixamento (Z4)": res.p_z4,
    }).sort_values("Pontos esperados", ascending=False).reset_index(drop=True)

    st.plotly_chart(fig_heatmap(res, clubes), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        top = probs_df[probs_df["Título"] >= 0.001].head(8)
        st.plotly_chart(
            fig_prob_bar(top["Time"].tolist(), top["Título"].to_numpy(),
                         (top["clube_id"] == REMO_ID).tolist(),
                         "Probabilidade de título"),
            width="stretch",
        )
    with col2:
        z4 = probs_df[probs_df["Rebaixamento (Z4)"] >= 0.001].sort_values(
            "Rebaixamento (Z4)", ascending=False).head(8)
        st.plotly_chart(
            fig_prob_bar(z4["Time"].tolist(), z4["Rebaixamento (Z4)"].to_numpy(),
                         (z4["clube_id"] == REMO_ID).tolist(),
                         "Probabilidade de rebaixamento"),
            width="stretch",
        )

    st.dataframe(
        probs_df.drop(columns=["clube_id"]),
        hide_index=True,
        height=740,
        column_config={
            c: st.column_config.ProgressColumn(c, format="percent", min_value=0, max_value=1)
            for c in ["Título", "Libertadores (G4)", "G6", "Rebaixamento (Z4)"]
        },
    )

# ---- página Simulador (palpites do usuário)
def _registrar_palpite(pid: int):
    v = st.session_state.get(f"pick_{pid}")
    if v:
        st.session_state.palpites[pid] = v
    else:
        st.session_state.palpites.pop(pid, None)


if SELECTED_PAGE == "simulador":
    st.caption("Escolha o resultado dos jogos que quiser (pode marcar várias "
               "rodadas) e veja como fica a tabela. Vitórias contam como 1×0 e "
               "empates como 1×1 para o saldo de gols.")

    info_partidas = {
        m.partida_id: m for m in fixtures.itertuples()
    }
    rodadas_futuras_sim = sorted(fixtures["rodada"].unique())
    rodada_palpite = st.selectbox("Rodada para palpitar", rodadas_futuras_sim,
                                  format_func=rotulo_rodada)
    jogos_rodada = fixtures[fixtures["rodada"] == rodada_palpite].sort_values("timestamp")

    for m in jogos_rodada.itertuples():
        nome_casa = store.clube_nome(clubes, m.casa_id)
        nome_fora = store.clube_nome(clubes, m.fora_id)
        c1, c2 = st.columns([5, 4])
        with c1:
            quando = pd.to_datetime(m.data).strftime("%d/%m %H:%M")
            destaque = "🦁 " if REMO_ID in (m.casa_id, m.fora_id) else ""
            st.markdown(f"{destaque}**{nome_casa} × {nome_fora}**")
            st.caption(f"{quando} · modelo: {pct(m.p_casa, 0)} / "
                       f"{pct(m.p_empate, 0)} / {pct(m.p_fora, 0)}")
        with c2:
            st.segmented_control(
                "Resultado",
                options=["casa", "empate", "fora"],
                format_func={"casa": nome_casa, "empate": "Empate",
                             "fora": nome_fora}.get,
                default=st.session_state.palpites.get(m.partida_id),
                key=f"pick_{m.partida_id}",
                on_change=_registrar_palpite,
                args=(m.partida_id,),
                label_visibility="collapsed",
            )

    st.divider()
    palpites = {pid: v for pid, v in st.session_state.palpites.items()
                if pid in info_partidas}
    if not palpites:
        st.info("Nenhum palpite ainda — escolha resultados acima para ver o "
                "efeito na classificação.")
    else:
        ca, cb = st.columns([4, 1])
        with ca:
            resumo = ", ".join(
                f"R{info_partidas[pid].rodada} "
                f"{store.clube_nome(clubes, info_partidas[pid].casa_id)}"
                f"{' (V)' if v == 'casa' else ' (E)' if v == 'empate' else ''}"
                f"×"
                f"{store.clube_nome(clubes, info_partidas[pid].fora_id)}"
                f"{' (V)' if v == 'fora' else ''}"
                for pid, v in sorted(palpites.items(),
                                     key=lambda kv: info_partidas[kv[0]].rodada)
            )
            st.markdown(f"**{len(palpites)} palpite(s):** {resumo}")
        with cb:
            if st.button("🧹 Limpar", width="stretch"):
                for pid in list(st.session_state.palpites):
                    st.session_state.pop(f"pick_{pid}", None)
                st.session_state.palpites = {}
                st.rerun()

        completar = st.toggle("Completar os jogos sem palpite com o modelo "
                              "(Monte Carlo)", value=True)
        if completar:
            cond = run_sim_palpites(data["fetched_at"], model_key, n_sims,
                                    tuple(sorted(palpites.items())))
            res_c = cond["res"]
            posicoes = np.arange(1, len(team_ids) + 1)
            pos_media_c = float((res_c.pos_dist[i_remo] * posicoes).sum())
            pos_media_b = float((res.pos_dist[i_remo] * posicoes).sum())

            st.markdown("#### Efeito no Remo (vs. simulação sem palpites)")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Posição média", f"{pos_media_c:.1f}º",
                      delta=f"{pos_media_c - pos_media_b:+.1f}",
                      delta_color="inverse")
            k2.metric("Pontos esperados", f"{res_c.exp_pts[i_remo]:.1f}",
                      delta=f"{res_c.exp_pts[i_remo] - res.exp_pts[i_remo]:+.1f}")
            k3.metric("Libertadores (G4)", pct(res_c.p_g4[i_remo]),
                      delta=pct(res_c.p_g4[i_remo] - res.p_g4[i_remo]))
            k4.metric("Rebaixamento (Z4)", pct(res_c.p_z4[i_remo]),
                      delta=pct(res_c.p_z4[i_remo] - res.p_z4[i_remo]),
                      delta_color="inverse")

            base_pts = {t: p for t, p in zip(res.team_ids, res.exp_pts)}
            tabela_cond = pd.DataFrame({
                "clube_id": res_c.team_ids,
                "Time": [store.clube_nome(clubes, t) for t in res_c.team_ids],
                "Pontos esperados": np.round(res_c.exp_pts, 1),
                "Δ pontos": np.round(
                    res_c.exp_pts - np.array([base_pts[t] for t in res_c.team_ids]), 1),
                "Título": res_c.p_titulo,
                "Libertadores (G4)": res_c.p_g4,
                "Rebaixamento (Z4)": res_c.p_z4,
            }).sort_values("Pontos esperados", ascending=False).reset_index(drop=True)
            tabela_cond.insert(0, "Pos", tabela_cond.index + 1)
            st.dataframe(
                tabela_cond.drop(columns=["clube_id"]),
                hide_index=True,
                height=740,
                column_config={
                    "Δ pontos": st.column_config.NumberColumn(format="%+.1f"),
                    **{c: st.column_config.ProgressColumn(
                        c, format="percent", min_value=0, max_value=1)
                       for c in ["Título", "Libertadores (G4)", "Rebaixamento (Z4)"]},
                },
            )
        else:
            extras = []
            for pid, v in palpites.items():
                m = info_partidas[pid]
                gc, gf = PICK_SCORES[v]
                extras.append({"rodada": m.rodada, "timestamp": m.timestamp,
                               "casa_id": m.casa_id, "fora_id": m.fora_id,
                               "gols_casa": gc, "gols_fora": gf})
            played_ext = pd.concat([played, pd.DataFrame(extras)], ignore_index=True)
            tabela_ext = compute_standings(played_ext, clubes, team_ids)
            pos_atual = dict(zip(standings["clube_id"], standings["Pos"]))
            tabela_ext["Δ"] = tabela_ext.apply(
                lambda r: (lambda d: f"▲{d}" if d > 0 else f"▼{-d}" if d < 0 else "–")(
                    pos_atual[r["clube_id"]] - r["Pos"]), axis=1)
            st.markdown("#### Tabela com os seus resultados (jogos sem palpite "
                        "ficam como estão)")
            st.dataframe(
                tabela_ext.set_index("clube_id")[
                    ["Pos", "Δ", "Time", "PTS", "J", "V", "E", "D", "GP", "GC", "SG"]],
                hide_index=True,
                height=740,
            )

# ---- página Próximos jogos
if SELECTED_PAGE == "proximos_jogos":
    rodadas_futuras = sorted(fixtures["rodada"].unique())
    rodada_sel = st.selectbox("Rodada", rodadas_futuras,
                              format_func=rotulo_rodada)
    jogos = fixtures[fixtures["rodada"] == rodada_sel].sort_values("timestamp")
    st.plotly_chart(fig_next_matches(jogos, clubes), width="stretch")
    st.caption("Probabilidades do modelo para cada jogo (vitória do mandante, "
               "empate, vitória do visitante).")

# ---- página Modelo
if SELECTED_PAGE == "modelo":
    st.subheader("Qual modelo prevê melhor? (backtest)")
    st.caption("Replay das últimas rodadas: cada modelo treina só com os jogos "
               "anteriores e é avaliado nos jogos que não viu. RPS e log loss: "
               "quanto menor, melhor.")
    n_rounds_bt = st.slider("Rodadas no backtest", 3, 8, 5)
    if st.button("▶️ Rodar backtest"):
        st.session_state["bt_rounds"] = n_rounds_bt
    if "bt_rounds" in st.session_state:
        bt = run_backtest(data["fetched_at"], st.session_state["bt_rounds"])
        melhor = bt.iloc[0]
        st.success(f"Melhor modelo no backtest: **{melhor['Modelo']}** "
                   f"(RPS {melhor['RPS']:.4f}, acurácia {pct(melhor['Acurácia 1X2'])} "
                   f"em {melhor['Jogos']} jogos)")
        st.dataframe(
            bt.drop(columns=["chave"]),
            hide_index=True,
            column_config={
                "Acurácia 1X2": st.column_config.ProgressColumn(
                    format="percent", min_value=0, max_value=1),
                "Log loss": st.column_config.NumberColumn(format="%.4f"),
                "RPS": st.column_config.NumberColumn(format="%.4f"),
            },
        )

    st.divider()
    with st.expander("Como funciona a previsão"):
        st.markdown(
            """
**Pipeline (100% leve — todos os treinos levam segundos):**

1. **Dados** — todas as partidas da Série A vêm da API pública do Cartola
   (`api.cartola.globo.com`), atualizadas 2× ao dia; o XGBoost treina também
   com o histórico do Brasileirão **2012+** (~5.300 jogos), com peso
   decrescente por ano de distância.
2. **Features** — indicadores de forma das duas equipes antes de cada jogo
   (pontos por jogo, média de gols nos últimos 5, desempenho por mando) e o
   **rating Elo**, atualizado jogo a jogo.
3. **Modelos** — todos preveem **taxas de gols** (λ) via regressão de Poisson:
   - **XGBoost** — árvores de decisão com boosting (treina em ~2 s);
   - **Poisson** — força de ataque/defesa por médias da temporada;
   - **Poisson temporal** — idem, mas jogos recentes pesam mais
     (meia-vida de 90 dias, à la Dixon-Coles);
   - **Ensemble** — média das taxas dos três acima (o padrão do app).
4. **Simulação Monte Carlo** — cada jogo restante é sorteado milhares de vezes
   a partir das taxas previstas; a tabela final é recalculada em cada cenário
   (com desempate por vitórias, saldo e gols pró), o que gera as
   probabilidades de título, G4, G6 e rebaixamento.

O **backtest** acima é o juiz: ele refaz as últimas rodadas fingindo que o
futuro não aconteceu e mede qual modelo chegou mais perto. Estimativas para
diversão, não aposta. 🦁
            """
        )
