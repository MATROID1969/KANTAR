import streamlit as st

from db.database import init_db
from config import APP_TITLE, DEV_USER_ID

# ── Oldal konfiguráció ──────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Adatbázis inicializálás (első induláskor létrehozza a táblákat) ──────────
init_db()

# ── Session state alapértékek ────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "list"

if "selected_offer_id" not in st.session_state:
    st.session_state.selected_offer_id = None

if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = DEV_USER_ID

if "show_new_offer" not in st.session_state:
    st.session_state.show_new_offer = False

if "show_handoff" not in st.session_state:
    st.session_state.show_handoff = False

# ── Navigáció ────────────────────────────────────────────────────────────────
from views.offer_list import render_offer_list
from views.offer_detail import render_offer_detail

if st.session_state.page == "list":
    render_offer_list()
elif st.session_state.page == "detail" and st.session_state.selected_offer_id:
    render_offer_detail(st.session_state.selected_offer_id)
else:
    st.session_state.page = "list"
    st.rerun()
