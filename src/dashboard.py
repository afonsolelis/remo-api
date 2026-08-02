"""Renderização das páginas do dashboard Streamlit.

Dados: API pública do Cartola FC. Atualização automática 2x ao dia.
Previsões: XGBoost, Poisson, Poisson temporal e Ensemble (todos leves);
simulação Monte Carlo do restante da temporada.

Este módulo é executado por cada arquivo em ``pages/`` com ``SELECTED_PAGE``
definido. Manter a renderização aqui evita duplicar o contexto e os componentes
durante a migração do antigo layout baseado em abas.
"""

import html
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import store
from src.copa import jogos_do_time
from src.projections import published_simulation
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

def load_data() -> dict:
    projection = store.load_projection()
    data = projection.get("season") if projection else store.load_snapshot()
    if not data:
        raise RuntimeError("snapshot público da temporada não encontrado")
    return data


@st.cache_data(show_spinner="Carregando backtest publicado…")
def run_backtest(fetched_at: str, n_rounds: int) -> pd.DataFrame:
    projection = store.load_projection()
    if not projection:
        return pd.DataFrame()
    return pd.DataFrame(projection.get("backtest", []))


@st.cache_data(show_spinner="Carregando simulações publicadas…")
def run_sim(fetched_at: str, model_key: str, n_sims: int) -> dict:
    projection = store.load_projection()
    if not projection:
        st.info("As projeções ainda estão sendo preparadas. Tente novamente em breve.")
        st.stop()
    return published_simulation(projection)


def _fmt_data_hora(data: str | None, hora: str | None = None) -> str:
    if not data:
        return "a definir"
    texto = f"{data[8:10]}/{data[5:7]}"
    if hora:
        texto = f"{texto} {hora}"
    return texto


def _fmt_placar_jogo(jogo: dict) -> str:
    if jogo["gols_mandante"] is None:
        return "—"
    placar = f"{int(jogo['gols_mandante'])}×{int(jogo['gols_visitante'])}"
    if jogo["pen_mandante"] is not None:
        placar += f" (pên. {int(jogo['pen_mandante'])}×{int(jogo['pen_visitante'])})"
    return placar


def _fmt_agregado_tie(tie: dict) -> str:
    totais: dict[int, int] = {}
    nomes: dict[int, str] = {}
    penais: str | None = None
    for jogo in tie["jogos"]:
        mandante_id = jogo["mandante_id"]
        visitante_id = jogo["visitante_id"]
        nomes[mandante_id] = jogo["mandante"]
        nomes[visitante_id] = jogo["visitante"]
        totais.setdefault(mandante_id, 0)
        totais.setdefault(visitante_id, 0)
        if jogo["gols_mandante"] is not None:
            totais[mandante_id] += int(jogo["gols_mandante"])
            totais[visitante_id] += int(jogo["gols_visitante"])
        if jogo["pen_mandante"] is not None:
            penais = (
                f"pên. {int(jogo['pen_mandante'])}×{int(jogo['pen_visitante'])}"
            )

    if len(nomes) != 2:
        return "a definir"

    time_a, time_b = list(nomes.keys())
    agregado = f"{nomes[time_a]} {totais[time_a]}×{totais[time_b]} {nomes[time_b]}"
    if penais:
        agregado = f"{agregado} ({penais})"
    if all(jogo["gols_mandante"] is None for jogo in tie["jogos"]):
        return "ainda sem jogos disputados"
    return agregado


def _render_copa_styles() -> None:
    st.markdown(
        """
        <style>
        .copa-tie-card {
            border: 1px solid rgba(49, 51, 63, 0.18);
            border-radius: 18px;
            padding: 1rem 1rem 1.1rem;
            background: linear-gradient(180deg, rgba(247, 249, 252, 0.96), rgba(255, 255, 255, 1));
            margin-bottom: 1rem;
        }
        .copa-tie-header {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: baseline;
            margin-bottom: 0.35rem;
        }
        .copa-tie-name {
            font-size: 1rem;
            font-weight: 700;
            color: #0f172a;
        }
        .copa-tie-badge {
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #0b5ed7;
            background: rgba(11, 94, 215, 0.10);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            white-space: nowrap;
        }
        .copa-tie-duel {
            font-size: 0.9rem;
            color: #475569;
            margin-bottom: 0.7rem;
        }
        .copa-agg-box {
            background: #0f172a;
            color: #f8fafc;
            border-radius: 14px;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.85rem;
        }
        .copa-agg-label {
            display: block;
            font-size: 0.72rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            opacity: 0.75;
            margin-bottom: 0.2rem;
        }
        .copa-agg-value {
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.3;
        }
        .copa-match-card {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 14px;
            padding: 0.85rem 0.95rem;
            background: #ffffff;
            margin-top: 0.7rem;
        }
        .copa-match-top {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: center;
            margin-bottom: 0.7rem;
        }
        .copa-match-label {
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #475569;
        }
        .copa-match-status {
            font-size: 0.76rem;
            font-weight: 700;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            background: #e2e8f0;
            color: #334155;
            white-space: nowrap;
        }
        .copa-match-status.is-played {
            background: rgba(22, 163, 74, 0.12);
            color: #166534;
        }
        .copa-scoreline {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
            align-items: center;
            gap: 0.6rem;
        }
        .copa-team {
            font-size: 0.98rem;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.25;
        }
        .copa-team.is-away {
            text-align: right;
        }
        .copa-score-box {
            min-width: 7.5rem;
            text-align: center;
            border-radius: 12px;
            background: #eff6ff;
            padding: 0.55rem 0.7rem;
        }
        .copa-score-main {
            font-size: 1.55rem;
            line-height: 1;
            font-weight: 800;
            color: #0b5ed7;
        }
        .copa-score-sub {
            font-size: 0.76rem;
            color: #475569;
            margin-top: 0.28rem;
        }
        .copa-match-meta {
            margin-top: 0.75rem;
            font-size: 0.82rem;
            color: #64748b;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_copa_match_card(jogo: dict, rotulo: str) -> None:
    placar = "a jogar"
    penais = ""
    status = "agendado"
    status_class = "copa-match-status"
    if jogo["gols_mandante"] is not None:
        placar = f"{int(jogo['gols_mandante'])}×{int(jogo['gols_visitante'])}"
        status = "encerrado"
        status_class = "copa-match-status is-played"
    if jogo["pen_mandante"] is not None:
        penais = (
            f"<div class='copa-score-sub'>pênaltis "
            f"{int(jogo['pen_mandante'])}×{int(jogo['pen_visitante'])}</div>"
        )

    data_local = (
        f"{html.escape(_fmt_data_hora(jogo['data'], jogo['hora']))} · "
        f"{html.escape(jogo['sede'] or 'local a definir')}"
    )
    st.markdown(
        f"""
        <div class="copa-match-card">
            <div class="copa-match-top">
                <div class="copa-match-label">{html.escape(rotulo)}</div>
                <div class="{status_class}">{status}</div>
            </div>
            <div class="copa-scoreline">
                <div class="copa-team">{html.escape(jogo['mandante'])}</div>
                <div class="copa-score-box">
                    <div class="copa-score-main">{placar}</div>
                    {penais}
                </div>
                <div class="copa-team is-away">{html.escape(jogo['visitante'])}</div>
            </div>
            <div class="copa-match-meta">{data_local}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_copa_tie_card(tie: dict, destaque: str | None = None) -> None:
    jogos = tie.get("jogos", [])
    duelo = "a definir"
    if jogos:
        duelo = f"{jogos[0]['mandante']} × {jogos[0]['visitante']}"

    badge = (
        f"<div class='copa-tie-badge'>{html.escape(destaque)}</div>"
        if destaque else ""
    )
    st.markdown(
        f"""
        <div class="copa-tie-card">
            <div class="copa-tie-header">
                <div class="copa-tie-name">{html.escape(tie['nome'])}</div>
                {badge}
            </div>
            <div class="copa-tie-duel">{html.escape(duelo)}</div>
            <div class="copa-agg-box">
                <span class="copa-agg-label">Agregado</span>
                <div class="copa-agg-value">{html.escape(_fmt_agregado_tie(tie))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for j, jogo in enumerate(jogos, start=1):
        _render_copa_match_card(jogo, "Jogo de ida" if j == 1 else "Jogo de volta")


def _render_chaveamento_fase(ties: list[dict]) -> None:
    colunas = st.columns(2)
    for i, tie in enumerate(ties):
        with colunas[i % 2]:
            _render_copa_tie_card(tie)


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

projection = store.load_projection()
model_key = projection.get("model_key", "ensemble") if projection else "ensemble"
n_sims = int(projection.get("n_sims", 0)) if projection else 0

_SIMULATION_PAGES = {
    "remo",
    "simulacoes",
    "classificacao_projetada",
    "proximos_jogos",
}
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
    doc = store.load_atletas()
    return doc, store.load_pontuados_all()


if SELECTED_PAGE in {"partidas", "elenco"}:
    atletas_doc, pontuados = load_atletas_data(data["fetched_at"])
    if not atletas_doc:
        st.info("Os dados de atletas ainda estão sendo preparados.")
        st.stop()
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
    return store.load_copa()


@st.cache_data(show_spinner="Carregando projeção da Copa do Brasil…")
def run_copa_sim(copa_fetched_at: str, cartola_fetched_at: str,
                 model_key: str, n_sims: int) -> dict | None:
    projection = store.load_projection()
    if not projection or not projection.get("copa"):
        return None
    copa = projection["copa"]
    return {
        **copa,
        "probs": {int(time): valores for time, valores in copa["probs"].items()},
        "nomes": {int(time): nome for time, nome in copa["nomes"].items()},
        "fora_serie_a": [int(time) for time in copa["fora_serie_a"]],
    }


if SELECTED_PAGE == "copa":
    copa_doc = load_copa_data(data["fetched_at"])
    if not copa_doc:
        st.info("Não consegui carregar a Copa do Brasil agora — tente atualizar "
                "os dados pelo botão no cabeçalho.")
    else:
        _render_copa_styles()
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
            _render_copa_tie_card(chave_remo, destaque="Confronto do Remo")

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
            _render_chaveamento_fase(sim_copa["ties"])

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

# ---- página Classificação projetada
if SELECTED_PAGE == "classificacao_projetada":
    st.markdown("## 🏁 Classificação projetada ao fim do Brasileirão")
    st.caption(
        f"Projeção após a última rodada baseada em {res.n_sims:,} temporadas "
        f"simuladas com **{sim['model']}**. A posição média agrega todos os "
        "cenários e pode conter valores decimais.".replace(",", ".")
    )

    posicoes = np.arange(1, len(res.team_ids) + 1)
    pos_media = res.pos_dist @ posicoes
    pos_mais_provavel = np.argmax(res.pos_dist, axis=1) + 1
    pos_atual = dict(zip(standings["clube_id"], standings["Pos"]))

    projecao = pd.DataFrame({
        "clube_id": res.team_ids,
        "Time": [store.clube_nome(clubes, t) for t in res.team_ids],
        "Posição média": pos_media,
        "Posição mais provável": pos_mais_provavel,
        "Pontos projetados": res.exp_pts,
        "Posição atual": [pos_atual[t] for t in res.team_ids],
        "Título": res.p_titulo,
        "G4": res.p_g4,
        "G6": res.p_g6,
        "Z4": res.p_z4,
    }).sort_values(
        ["Posição média", "Pontos projetados"], ascending=[True, False]
    ).reset_index(drop=True)

    projecao.insert(0, "Pos. projetada", np.arange(1, len(projecao) + 1))
    projecao["Variação"] = (
        projecao["Posição atual"] - projecao["Pos. projetada"]
    ).map(lambda v: f"▲ {v}" if v > 0 else (f"▼ {abs(v)}" if v < 0 else "—"))

    n_times = len(projecao)

    def zona(posicao: int) -> str:
        if posicao <= 4:
            return "🌎 Libertadores"
        if posicao <= 6:
            return "✈️ G6"
        if posicao >= n_times - 3:
            return "🚨 Z4"
        return "Série A"

    projecao["Zona"] = projecao["Pos. projetada"].map(zona)

    st.dataframe(
        projecao.drop(columns=["clube_id"]),
        hide_index=True,
        height=775,
        column_order=[
            "Pos. projetada",
            "Time",
            "Pontos projetados",
            "Posição média",
            "Posição mais provável",
            "Posição atual",
            "Variação",
            "Zona",
            "Título",
            "G4",
            "G6",
            "Z4",
        ],
        column_config={
            "Pos. projetada": st.column_config.NumberColumn(
                "Pos.", format="%d", width="small"
            ),
            "Pontos projetados": st.column_config.NumberColumn(
                "Pontos", format="%.1f"
            ),
            "Posição média": st.column_config.NumberColumn(format="%.1f"),
            "Posição mais provável": st.column_config.NumberColumn(
                "Pos. mais provável", format="%d"
            ),
            **{
                c: st.column_config.ProgressColumn(
                    c, format="percent", min_value=0, max_value=1
                )
                for c in ["Título", "G4", "G6", "Z4"]
            },
        },
    )
    st.caption(
        "A ordem usa a posição média em todos os cenários; por isso, pontos "
        "projetados e posição mais provável são indicadores complementares e "
        "não representam uma única temporada simulada."
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
               "quanto menor, melhor. Resultado atualizado automaticamente "
               "duas vezes ao dia.")
    bt = run_backtest(data["fetched_at"], 0)
    if bt.empty:
        st.info("O backtest publicado ainda está sendo preparado.")
    else:
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
