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
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import store
from src.copa import jogos_do_time
from src.liga import LIGAS
from src.projections import published_liga, published_simulation
from src.standings import compute_standings, cumulative_points, team_last_results
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

@st.cache_resource(max_entries=1, show_spinner="Carregando projeções publicadas…")
def projecao_publicada(ttl_bucket: int) -> dict | None:
    """O snapshot publicado é grande (megabytes) e é lido várias vezes por
    render — fica em cache de processo, revalidado a cada poucos minutos."""
    return store.load_projection()


def load_data(projection: dict | None) -> dict:
    data = projection.get("season") if projection else store.load_snapshot()
    if not data:
        raise RuntimeError("snapshot público da temporada não encontrado")
    return data


@st.cache_data(show_spinner="Carregando backtest publicado…")
def run_backtest(fetched_at: str, n_rounds: int) -> pd.DataFrame:
    projection = projecao_publicada(int(time.time()) // 300)
    if not projection:
        return pd.DataFrame()
    return pd.DataFrame(projection.get("backtest", []))


@st.cache_data(show_spinner="Carregando simulações publicadas…")
def run_sim(fetched_at: str, model_key: str, n_sims: int) -> dict | None:
    projection = projecao_publicada(int(time.time()) // 300)
    if not projection:
        return None
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
    st.html(
        f"""
        <div class="copa-match-card">
            <div class="copa-match-top">
                <div class="copa-match-label">{html.escape(rotulo)}</div>
                <div class="{status_class}">{status}</div>
            </div>
            <div class="copa-scoreline">
                <div class="copa-team">{html.escape(jogo['mandante'] or 'a definir')}</div>
                <div class="copa-score-box">
                    <div class="copa-score-main">{placar}</div>
                    {penais}
                </div>
                <div class="copa-team is-away">{html.escape(jogo['visitante'] or 'a definir')}</div>
            </div>
            <div class="copa-match-meta">{data_local}</div>
        </div>
        """,
    )


def _render_copa_tie_card(tie: dict, destaque: str | None = None) -> None:
    jogos = tie.get("jogos", [])
    duelo = "a definir"
    if jogos:
        duelo = (f"{jogos[0]['mandante'] or 'a definir'} × "
                 f"{jogos[0]['visitante'] or 'a definir'}")

    badge = (
        f"<div class='copa-tie-badge'>{html.escape(destaque)}</div>"
        if destaque else ""
    )
    st.html(
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
    )
    for j, jogo in enumerate(jogos, start=1):
        _render_copa_match_card(jogo, "Jogo de ida" if j == 1 else "Jogo de volta")


def _render_chaveamento_fase(ties: list[dict]) -> None:
    colunas = st.columns(2)
    for i, tie in enumerate(ties):
        with colunas[i % 2]:
            _render_copa_tie_card(tie)


# ---------------------------------------------------------------- gráficos

def fig_pos_dist(res, team_ids, selected_team_id: int,
                 selected_team_name: str) -> go.Figure:
    i = team_ids.index(selected_team_id)
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
    return apply_layout(
        fig,
        title=f"Onde o {selected_team_name} termina o campeonato? (simulações)",
    )


def fig_points_evolution(played, selected_team_id: int,
                         selected_team_name: str) -> go.Figure:
    cum = cumulative_points(played, selected_team_id)
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
    return apply_layout(fig, title=f"Evolução de pontos do {selected_team_name}")


def fig_prob_bar(names: list[str], values: np.ndarray, team_mask: list[bool],
                 title: str) -> go.Figure:
    colors = [BLUE if selected else OTHERS for selected in team_mask]
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
    positions = list(range(1, n + 1))
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
            x=positions,
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
    fig.update_xaxes(
        title_text="posição final",
        side="top",
        showgrid=False,
        tickmode="array",
        tickvals=positions,
        range=[0.5, n + 0.5],
    )

    zones = [
        (1, 4, "LIBERTADORES · 1º–4º", "#238636", "rgba(35, 134, 54, 0.10)"),
        (n - 3, n, f"Z4 · {n - 3}º–{n}º", "#c9362b",
         "rgba(201, 54, 43, 0.10)"),
    ]
    for start, end, label, color, fillcolor in zones:
        fig.add_vrect(
            x0=start - 0.5,
            x1=end + 0.5,
            fillcolor=fillcolor,
            line=dict(color=color, width=2),
            layer="above",
        )
        fig.add_annotation(
            x=(start + end) / 2,
            y=1.075,
            xref="x",
            yref="paper",
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(color=color, size=12),
        )

    fig = apply_layout(
        fig,
        height=650,
        title="Distribuição de posições finais (todas as equipes)",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=84, b=10))
    return fig


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


def render_melhor_cenario(analise: dict, fixtures, clubes: dict,
                          time_id: int, nome_time: str, n_sims: int) -> None:
    """Seção de melhor cenário — serve a Série A e às ligas do ge."""
    st.markdown(f"### 🎯 O melhor cenário possível para o {nome_time}")
    st.caption(
        f"Entre as {n_sims:,} temporadas simuladas, estas são as "
        f"{analise['n_cenarios']} em que o {nome_time} terminou mais "
        "alto. As probabilidades abaixo são condicionais a esse recorte: dizem "
        "o que aconteceu nele, não o que é mais provável em "
        "geral.".replace(",", ".")
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Melhor posição atingida", f"{analise['pos_melhor']}º")
    m2.metric("Teto do recorte", f"até {analise['pos_corte']}º")
    m3.metric("Posição média no recorte", f"{analise['pos_media']:.1f}º")
    m4.metric("Pontos no recorte", f"{analise['pts_media']:.0f}")
    st.caption(f"Terminar em {analise['pos_corte']}º ou melhor acontece em "
               f"{pct(analise['p_corte'])} de todos os cenários simulados.")
    st.subheader(f"O que o {nome_time} precisa fazer")
    proprios = []
    for item in analise["proprios"]:
        m = fixtures.iloc[item["jogo"]]
        em_casa = m["casa_id"] == time_id
        proprios.append({
            "Rodada": int(m["rodada"]),
            "Adversário": store.clube_nome(
                clubes, m["fora_id"] if em_casa else m["casa_id"]),
            "Mando": "🏠 Casa" if em_casa else "✈️ Fora",
            "Vitória": item["p_vitoria"],
            "Empate": item["p_empate"],
            "Derrota": item["p_derrota"],
            "Vitória (geral)": item["base_vitoria"],
        })
    df_proprios = pd.DataFrame(proprios).sort_values("Rodada")
    st.dataframe(
        df_proprios, hide_index=True,
        height=38 * (len(df_proprios) + 1) + 3,
        column_config={
            c: st.column_config.ProgressColumn(
                c, format="percent", min_value=0, max_value=1)
            for c in ["Vitória", "Empate", "Derrota", "Vitória (geral)"]
        },
    )
    st.caption("**Vitória (geral)** é a chance do mesmo jogo em todos os "
               "cenários — a distância entre as duas colunas mostra onde o "
               "melhor caminho exige mais do que o esperado.")
    st.subheader("O que precisa acontecer nos outros jogos")
    st.caption("Ordenado pelo quanto cada resultado se destaca no recorte em "
               "relação à média — são os tropeços e vitórias alheias que mais "
               "separam o melhor caminho do caminho comum.")
    rivais = []
    for item in analise["rivais"]:
        m = fixtures.iloc[item["jogo"]]
        casa = store.clube_nome(clubes, m["casa_id"])
        fora = store.clube_nome(clubes, m["fora_id"])
        rotulo = {"casa": f"{casa} vence", "empate": "Empate",
                  "fora": f"{fora} vence"}[item["resultado"]]
        rivais.append({
            "Rodada": int(m["rodada"]),
            "Jogo": f"{casa} × {fora}",
            "Resultado necessário": rotulo,
            "No melhor cenário": item["p_cond"],
            "Na média geral": item["p_base"],
        })
    df_rivais = pd.DataFrame(rivais)
    st.dataframe(
        df_rivais, hide_index=True,
        height=38 * (len(df_rivais) + 1) + 3,
        column_config={
            c: st.column_config.ProgressColumn(
                c, format="percent", min_value=0, max_value=1)
            for c in ["No melhor cenário", "Na média geral"]
        },
    )
    st.caption("Nenhum desses resultados é uma previsão: é o retrato do que "
               "aconteceu nas temporadas simuladas que terminaram melhor para "
               "o clube. Estimativas para diversão, não aposta. 🦁")


# ---------------------------------------------------------------- app

projection = projecao_publicada(int(time.time()) // 300)
data = load_data(projection)
clubes = data["clubes"]
status = data["status"]
df = store.matches_df(data)
played, future = store.split_played_future(df)
team_ids = sorted(set(df["casa_id"]) | set(df["fora_id"]))
selected_team_id = int(st.session_state.get("selected_team_id", store.REMO_ID))
if selected_team_id not in team_ids:
    selected_team_id = store.REMO_ID if store.REMO_ID in team_ids else team_ids[0]
    st.session_state.selected_team_id = selected_team_id
selected_team_name = store.clube_nome(clubes, selected_team_id)

model_key = projection.get("model_key", "ensemble") if projection else "ensemble"
n_sims = int(projection.get("n_sims", 0)) if projection else 0

# A página do Brasileirão empilha todas as seções da Série A numa rolagem só;
# as de competição renderizam apenas a sua. Daqui para baixo nada de
# ``st.stop()``: numa página empilhada ele derrubaria as seções seguintes.
PAGINAS_EMPILHADAS = {"brasileirao", *LIGAS}
SECOES_BRASILEIRAO = (
    "remo", "classificacao", "proximos_jogos", "simulacoes",
    "cenarios", "elenco", "partidas", "modelo",
)
_SIMULATION_PAGES = ("remo", "simulacoes", "cenarios", "proximos_jogos")


def ativa(*nomes: str) -> bool:
    """Se alguma das seções pedidas entra na página atual."""
    if SELECTED_PAGE == "brasileirao":
        return any(nome in SECOES_BRASILEIRAO for nome in nomes)
    return SELECTED_PAGE in nomes


def secao(titulo: str) -> None:
    """Cabeçalho que separa as seções de uma página empilhada."""
    if SELECTED_PAGE in PAGINAS_EMPILHADAS:
        st.divider()
        st.header(titulo)


standings = compute_standings(played, clubes, team_ids)
sim = None
if ativa(*_SIMULATION_PAGES):
    if future.empty:
        st.info("Temporada encerrada — não há jogos futuros para simular.")
    else:
        sim = run_sim(data["fetched_at"], model_key, n_sims)
        if sim is None:
            st.info("As projeções ainda estão sendo preparadas. "
                    "Tente novamente em breve.")
sim_ok = sim is not None
if sim_ok:
    res = sim["res"]
    fixtures = sim["fixtures"]
    selected_team_index = team_ids.index(selected_team_id)

_rodada_atual = status.get("rodada_atual", 1)


def rotulo_rodada(r: int) -> str:
    """Rodadas antigas com jogo pendente são adiamentos (ex.: FLA×MIR da 4ª)."""
    return f"Rodada {r} · jogo adiado" if r < _rodada_atual else f"Rodada {r}"

@st.cache_data(show_spinner=False)
def heatmap_publicado(fetched_at: str) -> go.Figure:
    """Cacheado por snapshot: independe do time em destaque."""
    return fig_heatmap(res, clubes)


# ---- dados de atletas (usados por Elenco e Partidas)
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


atletas_ok = False
if ativa("partidas", "elenco"):
    atletas_doc, pontuados = load_atletas_data(data["fetched_at"])
    if not atletas_doc:
        st.info("Os dados de atletas ainda estão sendo preparados.")
    else:
        atletas_ok = True
        posicoes_map = {
            int(k): v["nome"] for k, v in atletas_doc["posicoes"].items()
        }
        status_map = {
            int(k): v["nome"] for k, v in atletas_doc["status_atletas"].items()
        }


# ---- página do time selecionado
if ativa("remo") and sim_ok:
    secao(f"⚽ {selected_team_name}")
    team_row = standings[standings["clube_id"] == selected_team_id].iloc[0]
    ultimos = team_last_results(played, selected_team_id)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Posição", f"{team_row['Pos']}º")
    c2.metric("Pontos", int(team_row["PTS"]))
    c3.metric("Jogos", int(team_row["J"]))
    c4.metric("Aproveitamento", pct(team_row["Aproveitamento"] / 100))
    c5.metric("Últimos 5", "".join(FORM_ICON[r] for r in ultimos))

    st.caption("Probabilidades nas simulações do restante da temporada "
               f"({res.n_sims:,} cenários · modelo: {sim['model']}):".replace(",", "."))
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("🏆 Título", pct(res.p_titulo[selected_team_index]))
    p2.metric("🌎 Libertadores (G4)", pct(res.p_g4[selected_team_index]))
    p3.metric("✈️ G6", pct(res.p_g6[selected_team_index]))
    p4.metric("🚨 Rebaixamento (Z4)", pct(res.p_z4[selected_team_index]))

    team_fixtures = fixtures[
        (fixtures["casa_id"] == selected_team_id)
        | (fixtures["fora_id"] == selected_team_id)
    ].sort_values("timestamp")
    if not team_fixtures.empty:
        prox = team_fixtures.iloc[0]
        casa = store.clube_nome(clubes, prox["casa_id"])
        fora = store.clube_nome(clubes, prox["fora_id"])
        st.info(f"**Próximo jogo:** {casa} × {fora} — {prox['data']} — {prox['local']}  \n"
                f"Mandante {pct(prox['p_casa'])} · Empate {pct(prox['p_empate'])} · "
                f"Visitante {pct(prox['p_fora'])}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            fig_pos_dist(res, team_ids, selected_team_id, selected_team_name),
            width="stretch",
        )
    with col_b:
        st.plotly_chart(
            fig_points_evolution(played, selected_team_id, selected_team_name),
            width="stretch",
        )

    if not team_fixtures.empty:
        prox_ordenados = team_fixtures.sort_values("timestamp")
        st.subheader(
            f"Todos os próximos jogos do {selected_team_name} "
            f"({len(prox_ordenados)} restantes)"
        )
        exp_pts_restantes = float(
            (3 * prox_ordenados.apply(
                lambda m: m["p_casa"]
                if m["casa_id"] == selected_team_id else m["p_fora"], axis=1)
             + prox_ordenados["p_empate"]).sum()
        )
        st.caption(f"Pontos esperados nos jogos restantes: **+{exp_pts_restantes:.1f}** "
                   f"→ projeção final: **{res.exp_pts[selected_team_index]:.1f} pts** "
                   f"(modelo: {sim['model']}).")

        linhas = []
        for m in prox_ordenados.itertuples():
            em_casa = m.casa_id == selected_team_id
            adversario = store.clube_nome(clubes, m.fora_id if em_casa else m.casa_id)
            quando = pd.to_datetime(m.data)
            linhas.append({
                "Rodada": m.rodada,
                "Data": quando.strftime("%d/%m/%Y %H:%M"),
                "Adversário": adversario,
                "Mando": "🏠 Casa" if em_casa else "✈️ Fora",
                "Estádio": m.local,
                f"Vitória do {selected_team_name}": m.p_casa if em_casa else m.p_fora,
                "Empate": m.p_empate,
                "Derrota": m.p_fora if em_casa else m.p_casa,
            })
        tabela_time = pd.DataFrame(linhas)
        st.dataframe(
            tabela_time,
            hide_index=True,
            height=38 * (len(tabela_time) + 1) + 3,
            column_config={
                c: st.column_config.ProgressColumn(
                    c, format="percent", min_value=0, max_value=1)
                for c in [f"Vitória do {selected_team_name}", "Empate", "Derrota"]
            },
        )
    if selected_team_id == store.REMO_ID:
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
                   "simulações ao vivo. A Libertadores (sem o Remo em 2026) "
                   "também tem página própria.")

# ---- página Classificação
if ativa("classificacao"):
    secao("📊 Classificação")
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
        lambda row: [
            f"background-color: {BLUE_LIGHT}"
            if row.name == selected_team_id else ""
        ] * len(row),
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

# ---- página Próximos jogos
if ativa("proximos_jogos") and sim_ok:
    secao("📅 Próximos jogos")
    rodadas_futuras = sorted(fixtures["rodada"].unique())
    rodada_sel = st.selectbox("Rodada", rodadas_futuras,
                              format_func=rotulo_rodada,
                              key="rodada_proximos")
    jogos = fixtures[fixtures["rodada"] == rodada_sel].sort_values("timestamp")
    st.plotly_chart(fig_next_matches(jogos, clubes), width="stretch")
    st.caption("Probabilidades do modelo para cada jogo (vitória do mandante, "
               "empate, vitória do visitante).")

# ---- página Simulações
if ativa("simulacoes") and sim_ok:
    secao("🔮 Simulações")
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

    st.plotly_chart(heatmap_publicado(data["fetched_at"]), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        top = probs_df[probs_df["Título"] >= 0.001].head(8)
        st.plotly_chart(
            fig_prob_bar(top["Time"].tolist(), top["Título"].to_numpy(),
                         (top["clube_id"] == selected_team_id).tolist(),
                         "Probabilidade de título"),
            width="stretch",
        )
    with col2:
        z4 = probs_df[probs_df["Rebaixamento (Z4)"] >= 0.001].sort_values(
            "Rebaixamento (Z4)", ascending=False).head(8)
        st.plotly_chart(
            fig_prob_bar(z4["Time"].tolist(), z4["Rebaixamento (Z4)"].to_numpy(),
                         (z4["clube_id"] == selected_team_id).tolist(),
                         "Probabilidade de rebaixamento"),
            width="stretch",
        )

    st.divider()
    st.markdown("### 🏁 Classificação projetada ao fim do Brasileirão")
    st.caption(
        "Projeção após a última rodada. A posição média agrega todos os "
        "cenários e pode conter valores decimais."
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

# ---- página Melhor cenário
analise = None
if ativa("cenarios") and sim_ok:
    secao("🎯 Melhor cenário")
    league = (projection or {}).get("league") or {}
    analise = (league.get("cenarios") or {}).get(str(selected_team_id))
    if not analise:
        st.info("A análise de cenários é gerada junto com as simulações, 2× ao "
                "dia. Ela aparece aqui no próximo ciclo de atualização.")

if analise:
    render_melhor_cenario(analise, fixtures, clubes, selected_team_id,
                          selected_team_name, res.n_sims)

# ---- página Elenco (disponibilidade para o próximo jogo)
POS_ORDEM = {"Goleiro": 0, "Lateral": 1, "Zagueiro": 2, "Meia": 3,
             "Atacante": 4, "Técnico": 5}
FORMACAO_433 = {"Goleiro": 1, "Lateral": 2, "Zagueiro": 2, "Meia": 3,
                "Atacante": 3, "Técnico": 1}

if ativa("elenco") and atletas_ok:
    secao("👥 Elenco")
    team_fixtures = future[
        (future["casa_id"] == selected_team_id)
        | (future["fora_id"] == selected_team_id)
    ].sort_values("timestamp")
    elenco = []
    for a in atletas_doc["atletas"]:
        if a.get("clube_id") != selected_team_id:
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
            "scout": {c: scout.get(c, 0) for c in SCOUT_COLS},
        })
    elenco.sort(key=lambda e: (POS_ORDEM.get(e["pos"], 9), -e["media"]))

    if not team_fixtures.empty:
        p = team_fixtures.iloc[0]
        adversario = store.clube_nome(
            clubes,
            p["fora_id"] if p["casa_id"] == selected_team_id else p["casa_id"],
        )
        mando = "em casa" if p["casa_id"] == selected_team_id else "fora"
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
        "Média": e["media"], "Jogos": e["jogos"], "Preço (C$)": e["preco"],
        **e["scout"],
    } for e in elenco])
    st.dataframe(
        df_e, hide_index=True, height=min(740, 38 * (len(df_e) + 1) + 3),
        column_config={
            "Foto": st.column_config.ImageColumn("", width=40),
            "Média": st.column_config.NumberColumn(format="%.1f"),
            "Preço (C$)": st.column_config.NumberColumn(format="%.2f"),
            **{c: st.column_config.NumberColumn(c, help=SCOUT_HELP[c], width=44)
               for c in SCOUT_COLS},
        },
    )
    st.caption("Scout do Cartola — " +
               " · ".join(f"**{c}** {SCOUT_HELP[c]}" for c in SCOUT_COLS))
    st.caption("Status vem do mercado do Cartola (atualizado pela Globo ao longo "
               "da semana). O ciclo de amarelos é estimado pelo scout do Cartola: "
               "a cada 3 amarelos há suspensão automática — jogos antecipados/"
               "adiados não pontuam no Cartola e podem não entrar nessa conta.")

# ---- página Partidas
if ativa("partidas") and atletas_ok:
    secao("📋 Partidas")
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


# ---- página Modelo
if ativa("modelo"):
    secao("🧠 Modelo")
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

# ---- páginas de mata-mata (Copa do Brasil e Libertadores)
@st.cache_data(ttl=3600, show_spinner="Carregando a Copa do Brasil…")
def load_copa_data(fetched_at: str) -> dict | None:
    return store.load_copa()


@st.cache_data(ttl=3600, show_spinner="Carregando a Libertadores…")
def load_libertadores_data(fetched_at: str) -> dict | None:
    return store.load_libertadores()


@st.cache_data(show_spinner="Carregando projeção do mata-mata…")
def run_knockout_sim(competicao: str, doc_fetched_at: str,
                     cartola_fetched_at: str, model_key: str,
                     n_sims: int) -> dict | None:
    projection = store.load_projection()
    if not projection or not projection.get(competicao):
        return None
    sim = projection[competicao]
    return {
        **sim,
        "probs": {int(time): valores for time, valores in sim["probs"].items()},
        "nomes": {int(time): nome for time, nome in sim["nomes"].items()},
        "fora_serie_a": [int(time) for time in sim["fora_serie_a"]],
        "forca_estimada": [int(time) for time in sim.get("forca_estimada", [])],
    }


def _render_grupos(fase: dict) -> None:
    """Tabelas finais da fase de grupos (Libertadores), dois grupos por linha."""
    grupos = fase.get("grupos", [])
    colunas = st.columns(2)
    for i, grupo in enumerate(grupos):
        tabela = pd.DataFrame([
            {
                "Escudo": c["escudo"],
                "Time": c["nome"],
                "P": c["pontos"],
                "J": c["jogos"],
                "V": c["vitorias"],
                "E": c["empates"],
                "D": c["derrotas"],
                "GP": c["gols_pro"],
                "GC": c["gols_contra"],
                "SG": c["saldo_gols"],
            }
            for c in grupo["classificacao"]
        ])
        with colunas[i % 2]:
            st.markdown(f"**{grupo['nome']}**")
            st.dataframe(
                tabela, hide_index=True,
                height=38 * (len(tabela) + 1) + 3,
                column_config={
                    "Escudo": st.column_config.ImageColumn("", width="small"),
                },
            )
    st.caption("Os dois primeiros de cada grupo avançaram às oitavas; os "
               "terceiros foram para os playoffs da Sul-Americana.")


def _render_mata_mata_page(
    doc: dict | None, competicao: str, nome_competicao: str,
    aviso_erro: str,
) -> None:
    if not doc:
        st.info(f"Não consegui carregar a {nome_competicao} agora — {aviso_erro}")
        return
    _render_copa_styles()
    sim = run_knockout_sim(competicao, doc["fetched_at"], data["fetched_at"],
                           model_key, n_sims)
    fase_atual = next((f for f in doc["fases"] if f["atual"]), None)
    fase_nome = sim["fase_nome"] if sim else (
        fase_atual["nome"] if fase_atual else "fase atual")
    st.markdown(f"### {doc['edicao']} — {fase_nome}")
    campanha = jogos_do_time(doc, selected_team_id)

    if sim and selected_team_id in sim["probs"]:
        team_tie = next(
            (
                tie for tie in sim["ties"]
                if selected_team_id in (
                    tie["jogos"][0]["mandante_id"],
                    tie["jogos"][0]["visitante_id"],
                )
            ),
            None,
        )
        if team_tie:
            st.subheader(f"⚽ {team_tie['nome']}: "
                         f"{team_tie['jogos'][0]['mandante']} × "
                         f"{team_tie['jogos'][0]['visitante']}")
            _render_copa_tie_card(
                team_tie, destaque=f"Confronto do {selected_team_name}"
            )

        team_probs = sim["probs"][selected_team_id]
        cols = st.columns(len(team_probs))
        for c, rotulo, p in zip(cols, sim["rotulos"], team_probs):
            c.metric(rotulo, pct(p))
    elif not campanha:
        st.info(f"O {selected_team_name} não disputa a {nome_competicao} "
                "nesta temporada.")
    elif sim:
        st.info(f"O {selected_team_name} não está nesta fase da competição.")

    if sim:
        st.subheader("Probabilidades de todos (simulação do chaveamento)")
        tabela = pd.DataFrame([
            {"Time": sim["nomes"].get(t, str(t)),
             **{r: p for r, p in zip(sim["rotulos"], ps)}}
            for t, ps in sim["probs"].items()
        ]).sort_values(sim["rotulos"][-1], ascending=False)
        st.dataframe(
            tabela, hide_index=True,
            height=38 * (len(tabela) + 1) + 3,
            column_config={r: st.column_config.ProgressColumn(
                r, format="percent", min_value=0, max_value=1)
                for r in sim["rotulos"]},
        )
        estimados = set(sim["forca_estimada"])
        com_grupos = [sim["nomes"][t] for t in sim["fora_serie_a"] if t in estimados]
        sem_dados = [sim["nomes"][t] for t in sim["fora_serie_a"]
                     if t not in estimados]
        avisos = ""
        if com_grupos:
            avisos += (f" Clubes fora da Série A ({', '.join(com_grupos)}) têm "
                       "ataque e defesa estimados pela campanha na fase de grupos.")
        if sem_dados:
            avisos += (f" Clubes fora da Série A ({', '.join(sem_dados)}) entram "
                       "com força estimada abaixo da média da elite.")
        final_txt = ("final em jogo único em campo neutro"
                     if sim.get("final_jogo_unico") else
                     "mando das fases futuras alternado")
        st.caption("Ida e volta simulados por Poisson com o modelo selecionado "
                   "no cabeçalho; agregado empatado vai para pênaltis "
                   f"(50/50); chaveamento padrão e {final_txt}.{avisos}")

        st.subheader("Confrontos da fase")
        _render_chaveamento_fase(sim["ties"])
    else:
        ties = [c for c in (fase_atual or {}).get("chaves", []) if c.get("jogos")]
        if ties:
            st.info("A simulação do mata-mata ainda não foi publicada pelo "
                    "atualizador — abaixo, os confrontos da fase atual.")
            st.subheader("Confrontos da fase")
            _render_chaveamento_fase(ties)

    if campanha:
        with st.expander(f"Campanha do {selected_team_name} na competição"):
            for j in campanha:
                placar = (f"{int(j['gols_mandante'])}×{int(j['gols_visitante'])}"
                          if j["gols_mandante"] is not None else "a jogar")
                pen = (f" (pên. {int(j['pen_mandante'])}×{int(j['pen_visitante'])})"
                       if j["pen_mandante"] is not None else "")
                st.markdown(f"- **{j['fase']}**: {j['mandante']} {placar}{pen} "
                            f"{j['visitante']} · {j['data'] or ''}")


if ativa("copa"):
    _render_mata_mata_page(
        load_copa_data(data["fetched_at"]), "copa", "Copa do Brasil",
        "tente atualizar os dados pelo botão no cabeçalho.",
    )

@st.cache_data(ttl=3600, show_spinner="Carregando a Série D…")
def load_serie_d_data(fetched_at: str) -> dict | None:
    return store.load_serie_d()


if ativa("serie_d"):
    _render_mata_mata_page(
        load_serie_d_data(data["fetched_at"]), "serie_d", "Série D",
        "o chaveamento é atualizado pelo mesmo ciclo das outras competições.",
    )

if ativa("libertadores"):
    libertadores_doc = load_libertadores_data(data["fetched_at"])
    _render_mata_mata_page(
        libertadores_doc, "libertadores", "Libertadores",
        "os dados são baixados pelo atualizador (08h e 22h) ou pela página Admin.",
    )
    if libertadores_doc:
        fase_grupos = next(
            (f for f in libertadores_doc["fases"] if f.get("grupos")), None
        )
        if fase_grupos:
            with st.expander("Fase de grupos (classificação final)",
                             expanded=bool(fase_grupos["atual"])):
                _render_grupos(fase_grupos)

# ---- páginas de ligas de pontos corridos do ge (Séries B e C)
def _tabelas_por_grupo(doc: dict, tabela, team_ids: list[int]) -> list[tuple]:
    """(nome do grupo, tabela reordenada, ids) — um item só quando a liga não
    tem conferências. A ordem de desempate da tabela geral é preservada."""
    mapa = doc.get("grupos") or {}
    if not mapa:
        return [(None, tabela, team_ids)]
    blocos = []
    for nome in sorted({mapa[str(t)] for t in team_ids}):
        ids = [t for t in team_ids if mapa[str(t)] == nome]
        parcial = tabela[tabela["clube_id"].isin(ids)].copy()
        parcial["Pos"] = range(1, len(parcial) + 1)
        blocos.append((nome, parcial, ids))
    return blocos


def render_liga(bloco: dict) -> None:
    """Tabela sempre; simulações só quando a fase corrente tem jogo futuro.

    Em ligas com conferências (MLS) todos os jogos contam para a tabela, mas
    a classificação e as faixas valem dentro de cada uma.
    """
    res = bloco["res"]
    fixtures = bloco["fixtures"]
    doc = bloco["liga"]
    clubes = doc["clubes"]
    info = doc["status"]
    faixas = doc["faixas"]
    played, _ = store.split_played_future(store.matches_df(doc))
    team_ids = ([int(t) for t in res.team_ids] if res
                else sorted({int(t) for t in clubes}))
    tabela = compute_standings(played, clubes, team_ids)
    blocos = _tabelas_por_grupo(doc, tabela, team_ids)
    indice = {t: i for i, t in enumerate(team_ids)}

    padrao = (selected_team_id if selected_team_id in team_ids
              else int(tabela.iloc[0]["clube_id"]))
    ordenados = sorted(team_ids, key=lambda t: store.clube_nome(clubes, t))
    time_id = st.selectbox(
        f"Time em destaque na {' '.join(doc['nome'].split()[-2:])}",
        ordenados,
        index=ordenados.index(padrao),
        format_func=lambda t: store.clube_nome(clubes, t),
        key=f"time_{doc['chave']}",
    )
    nome_time = store.clube_nome(clubes, time_id)

    fase_nome = (doc.get("fase") or {}).get("nome")
    contexto = f"{info['nome']} · rodada {info['rodada_atual']} de {info['rodada_final']}"
    if fase_nome:
        contexto += f" · {fase_nome}"
    st.caption(contexto + (f" · projeções com **{bloco['model']}**" if res else ""))

    def faixas_do_grupo(grupo):
        return [f for f in faixas if f.get("grupo") in (None, grupo)]

    secao("📊 Classificação")
    for grupo, parcial, _ids in blocos:
        if grupo:
            st.markdown(f"**{grupo}**")
        zona = {p: f["nome"] for f in faixas_do_grupo(grupo) for p in f["posicoes"]}
        disp = parcial.copy()
        disp["Escudo"] = disp["clube_id"].map(lambda t: store.clube_escudo(clubes, t))
        disp["Últimos 5"] = disp["clube_id"].map(
            lambda t: "".join(FORM_ICON[r] for r in team_last_results(played, t)))
        disp["Zona"] = disp["Pos"].map(lambda p: zona.get(p, "—"))
        disp["Aproveitamento"] = disp["Aproveitamento"].map(lambda v: pct(v / 100))
        disp = disp.set_index("clube_id")[
            ["Pos", "Escudo", "Time", "PTS", "J", "V", "E", "D", "GP", "GC", "SG",
             "Aproveitamento", "Últimos 5", "Zona"]
        ]
        st.dataframe(
            disp.style.apply(
                lambda row: [f"background-color: {BLUE_LIGHT}"
                             if row.name == time_id else ""] * len(row),
                axis=1,
            ),
            hide_index=True,
            height=38 * (len(disp) + 1) + 3,
            column_config={"Escudo": st.column_config.ImageColumn("", width=36)},
        )

    if not res:
        st.info(f"**{fase_nome or 'Fase atual'} encerrada.** A fase seguinte "
                "ainda não foi sorteada pela CBF — quando o ge publicar os "
                "confrontos, as simulações e o melhor cenário aparecem aqui "
                "automaticamente.")
        return

    secao("🔮 Simulações")
    st.caption(f"{res.n_sims:,} temporadas simuladas · jogos restantes: "
               f"{len(fixtures)}".replace(",", "."))
    treino = int(bloco.get("jogos_treino") or len(played))
    if treino > len(played) * 1.5:
        st.warning(
            f"**Temporada no começo:** só {len(played)} jogos disputados. O "
            f"modelo treina com {treino} partidas incluindo a temporada "
            "passada, então a projeção reflete sobretudo o ano anterior — e "
            "clubes recém-promovidos, sem campanha anterior na divisão, "
            "aparecem puxados para a média. A incerteza cai rodada a rodada."
        )
    st.plotly_chart(fig_heatmap(res, clubes), width="stretch")

    por_grupo = res.pos_dist_grupo is not None
    dist = res.pos_dist_grupo if por_grupo else res.pos_dist
    for grupo, _parcial, ids in blocos:
        if grupo:
            st.markdown(f"**{grupo}**")
        linhas_grupo = [indice[t] for t in ids]
        sub = dist[linhas_grupo][:, :len(ids)]
        colunas = {
            "Time": [store.clube_nome(clubes, t) for t in ids],
            "Pontos projetados": np.round(res.exp_pts[linhas_grupo], 1),
            "Posição média": sub @ np.arange(1, len(ids) + 1),
        }
        if por_grupo:
            colunas["🏆 Supporters' Shield"] = res.p_titulo[linhas_grupo]
        else:
            colunas["Título"] = sub[:, 0]
        for f in faixas_do_grupo(grupo):
            colunas[f["nome"]] = sub[:, [p - 1 for p in f["posicoes"]]].sum(axis=1)
        projecao = pd.DataFrame(colunas).sort_values(
            "Posição média").reset_index(drop=True)
        projecao.insert(0, "Pos.", np.arange(1, len(projecao) + 1))
        percentuais = [c for c in projecao.columns
                       if c not in ("Pos.", "Time", "Pontos projetados",
                                    "Posição média")]
        st.dataframe(
            projecao,
            hide_index=True,
            height=38 * (len(projecao) + 1) + 3,
            column_config={
                "Pos.": st.column_config.NumberColumn(format="%d", width="small"),
                "Pontos projetados": st.column_config.NumberColumn(format="%.1f"),
                "Posição média": st.column_config.NumberColumn(format="%.1f"),
                **{c: st.column_config.ProgressColumn(
                    c, format="percent", min_value=0, max_value=1)
                   for c in percentuais},
            },
        )
    st.caption("As zonas vêm do regulamento que a própria fonte publica para "
               "esta edição, não de valores fixos no código." +
               (" Na MLS todos os jogos contam para a tabela, mas a posição "
                "vale dentro da conferência; o Supporters' Shield é a melhor "
                "campanha geral." if por_grupo else ""))

    secao("🎯 Melhor cenário")
    analise = (bloco["cenarios"] or {}).get(str(time_id))
    if analise:
        render_melhor_cenario(analise, fixtures, clubes, time_id, nome_time,
                              res.n_sims)
    else:
        st.info("A análise de cenários aparece no próximo ciclo do atualizador.")

    secao("📅 Próximos jogos")
    rodada = st.selectbox("Rodada", sorted(fixtures["rodada"].unique()),
                          format_func=lambda r: f"Rodada {r}",
                          key=f"rodada_{doc['chave']}")
    st.plotly_chart(
        fig_next_matches(
            fixtures[fixtures["rodada"] == rodada].sort_values("timestamp"),
            clubes),
        width="stretch",
    )

    secao("🧠 Modelo")
    bt = pd.DataFrame(bloco["backtest"])
    if bt.empty:
        st.info("O backtest desta divisão ainda está sendo preparado.")
    else:
        st.caption("Replay das últimas rodadas da própria competição. O "
                   "XGBoost fica atrás dos modelos estatísticos mesmo onde há "
                   "histórico para treiná-lo, por isso a simulação usa só "
                   "estes últimos.")
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


for _chave in LIGAS:
    if ativa(_chave):
        _bloco = published_liga(projection, _chave) if projection else None
        if _bloco:
            render_liga(_bloco)
        else:
            st.info("As projeções desta divisão são geradas pelo atualizador "
                    "2× ao dia. Elas aparecem aqui no próximo ciclo.")
