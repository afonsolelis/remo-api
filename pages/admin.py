"""Página administrativa: login simples + atualização manual dos dados."""

import os
from datetime import datetime, timezone

import streamlit as st

from src import store
from src.projections import generate_and_save

ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

st.markdown("### 🔒 Administração")

if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

if not st.session_state.admin_ok:
    if not (ADMIN_USER and ADMIN_PASSWORD):
        st.warning("Login não configurado (defina ADMIN_USER e ADMIN_PASSWORD).")
        st.stop()
    with st.form("admin_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")
    if entrar:
        if usuario == ADMIN_USER and senha == ADMIN_PASSWORD:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
    st.stop()

top = st.columns([4, 1])
with top[0]:
    st.caption(f"Sessão de **{ADMIN_USER}**")
with top[1]:
    if st.button("Sair"):
        st.session_state.admin_ok = False
        st.rerun()

snapshot = store.load_snapshot()
if snapshot:
    fetched = datetime.fromisoformat(snapshot["fetched_at"]).astimezone()
    st.caption(f"Última atualização dos dados: {fetched:%d/%m/%Y às %H:%M}")

st.markdown(
    "Baixa a temporada, elenco/pontuações, Copa do Brasil e Libertadores, e "
    "re-treina os modelos e simulações publicadas. O mesmo processo do atualizador "
    "automático (08h e 22h)."
)

if st.button("🔄 Atualizar sistema agora", type="primary"):
    try:
        with st.spinner("Baixando temporada, elenco, Copa do Brasil e Libertadores…"):
            data = store.refresh()
        with st.spinner("Treinando modelos e gerando projeções…"):
            projection = generate_and_save(data)
    except Exception as e:
        st.error(f"Falha na atualização: {e}")
    else:
        st.success(
            f"Atualizado — rodada {data['status'].get('rodada_atual')} · "
            f"{projection['n_sims']:,} simulações · {projection['model_name']}"
            .replace(",", ".")
        )
        st.caption(
            f"Concluído em "
            f"{datetime.now(timezone.utc).astimezone():%d/%m/%Y às %H:%M}"
        )
