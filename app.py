"""Entrypoint e moldura compartilhada do dashboard."""

from datetime import datetime, timezone
import streamlit as st

from src import store
from src.model import MODEL_LABELS, available_model_keys


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
        st.Page("pages/simulador.py", title="Simulador", icon="🎮"),
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

data = store.load_or_refresh(max_age_hours=24)
status = data["status"]
model_options = {MODEL_LABELS[key]: key for key in available_model_keys()}
labels_by_key = {key: label for label, key in model_options.items()}

with st.container(border=True):
    brand, model_col, sims_col, update_col = st.columns(
        [2.4, 2.1, 1.7, 1.2], vertical_alignment="bottom"
    )
    with brand:
        st.markdown("### 🦁 Remo no Brasileirão")
        st.caption(
            f"Temporada {status.get('temporada')} · Rodada "
            f"{status.get('rodada_atual')} de {status.get('rodada_final', 38)}"
        )
    with model_col:
        selected_label = st.selectbox(
            "Modelo de previsão",
            list(model_options),
            index=list(model_options).index(
                labels_by_key.get(st.session_state.get("model_key", "ensemble"),
                                  MODEL_LABELS["ensemble"])
            ),
            key="_model_label",
        )
        st.session_state.model_key = model_options[selected_label]
    with sims_col:
        st.select_slider(
            "Nº de simulações",
            options=list(range(1000, 20001, 1000)),
            value=st.session_state.get("n_sims", 5000),
            key="n_sims",
        )
    with update_col:
        if st.button("🔄 Atualizar", width="stretch"):
            with st.spinner("Atualizando dados…"):
                store.refresh()
                st.cache_data.clear()
                st.cache_resource.clear()
            st.rerun()

fetched = datetime.fromisoformat(data["fetched_at"])
age_h = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
origin = "MongoDB" if store.MONGO_URL else "JSON local"
st.caption(
    f"Dados da API do Cartola atualizados há {age_h:.1f} h · {origin}"
)

current_page.run()
