"""Entrypoint e moldura compartilhada do dashboard."""

from datetime import datetime, timezone
import streamlit as st

from src import store


st.set_page_config(
    page_title="Meu time no Brasileirão",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)


pages = {
    "Visão geral": [
        st.Page("pages/remo.py", title="Meu time", icon="⚽", default=True),
        st.Page("pages/classificacao.py", title="Classificação", icon="📊"),
        st.Page("pages/proximos_jogos.py", title="Próximos jogos", icon="📅"),
    ],
    "Análises": [
        st.Page("pages/simulacoes.py", title="Simulações", icon="🔮"),
        st.Page(
            "pages/classificacao_projetada.py",
            title="Classificação projetada",
            icon="🏁",
        ),
        st.Page("pages/modelo.py", title="Modelo", icon="🧠"),
    ],
    "Competições": [
        st.Page("pages/copa.py", title="Copa do Brasil", icon="🏆"),
        st.Page("pages/libertadores.py", title="Libertadores", icon="🌎"),
    ],
    "Dados": [
        st.Page("pages/elenco.py", title="Elenco", icon="👥"),
        st.Page("pages/partidas.py", title="Partidas e elenco", icon="📋"),
    ],
    "Admin": [
        st.Page("pages/admin.py", title="Admin", icon="🔒"),
    ],
}

current_page = st.navigation(pages, position="top")

projection = store.load_projection()
data = projection.get("season") if projection else store.load_snapshot()
if not data:
    st.error("Os dados públicos ainda estão sendo preparados. Tente novamente em breve.")
    st.stop()
status = data["status"]
clubes = data["clubes"]
team_ids = sorted(
    {int(team_id) for team_id in clubes},
    key=lambda team_id: store.clube_nome(clubes, team_id),
)
if not team_ids:
    st.error("Nenhum clube foi encontrado nos dados da temporada.")
    st.stop()
if st.session_state.get("selected_team_id") not in team_ids:
    st.session_state.selected_team_id = (
        store.REMO_ID if store.REMO_ID in team_ids else team_ids[0]
    )
if "visit_count" not in st.session_state:
    st.session_state.visit_count = store.register_visit()

with st.container(border=True):
    brand, selector, publication, visits = st.columns(
        [2.2, 1.8, 2.2, 1.0], vertical_alignment="center"
    )
    with brand:
        selected_team_name = store.clube_nome(
            clubes, st.session_state.selected_team_id
        )
        st.markdown(f"### ⚽ {selected_team_name} no Brasileirão")
        st.caption(
            f"Temporada {status.get('temporada')} · Rodada "
            f"{status.get('rodada_atual')} de {status.get('rodada_final', 38)}"
        )
    with selector:
        st.selectbox(
            "Time em destaque",
            team_ids,
            format_func=lambda team_id: store.clube_nome(clubes, team_id),
            key="selected_team_id",
        )
    with publication:
        if projection:
            generated = datetime.fromisoformat(projection["generated_at"]).astimezone()
            st.markdown(
                f"**{projection['model_name']} · "
                f"{projection['n_sims']:,} simulações**".replace(",", ".")
            )
            st.caption(f"Projeção atualizada em {generated:%d/%m/%Y às %H:%M}")
        else:
            st.warning("As projeções estão sendo preparadas pelo atualizador.")
    with visits:
        visit_count = st.session_state.visit_count
        formatted_count = (
            f"{visit_count:,}".replace(",", ".")
            if visit_count is not None
            else "—"
        )
        st.metric("👁️ Visitas", formatted_count)

fetched = datetime.fromisoformat(data["fetched_at"])
age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
origin = "MongoDB" if store.MONGO_URL else "JSON local"
st.caption(f"Dados atualizados há {age_h:.1f} h · {origin} · atualização automática 2× ao dia")

current_page.run()
