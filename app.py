"""Entrypoint e moldura compartilhada do dashboard."""

from datetime import datetime, timezone
import streamlit as st

from src import store


st.set_page_config(
    page_title="Remo no Brasileirão",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="collapsed",
)


pages = {
    "Visão geral": [
        st.Page("pages/remo.py", title="Remo", icon="🦁", default=True),
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
    ],
    "Dados": [
        st.Page("pages/elenco.py", title="Elenco do Remo", icon="👥"),
        st.Page("pages/partidas.py", title="Partidas e elenco", icon="📋"),
    ],
}

current_page = st.navigation(pages, position="top")

projection = store.load_projection()
data = projection.get("season") if projection else store.load_snapshot()
if not data:
    st.error("Os dados públicos ainda estão sendo preparados. Tente novamente em breve.")
    st.stop()
status = data["status"]

with st.container(border=True):
    brand, publication = st.columns([2.4, 2.2], vertical_alignment="center")
    with brand:
        st.markdown("### 🦁 Remo no Brasileirão")
        st.caption(
            f"Temporada {status.get('temporada')} · Rodada "
            f"{status.get('rodada_atual')} de {status.get('rodada_final', 38)}"
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

fetched = datetime.fromisoformat(data["fetched_at"])
age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
origin = "MongoDB" if store.MONGO_URL else "JSON local"
st.caption(f"Dados atualizados há {age_h:.1f} h · {origin} · atualização automática 2× ao dia")

current_page.run()
