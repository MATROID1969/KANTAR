import streamlit as st
import pandas as pd

from db.database import get_session
from db import crud
from config import APP_TITLE
from views.stage1_nyitooldal import UZLETSZERZO_OPTIONS

# ---------------------------------------------------------------------------
# Segédadatok (az Excel Nyitóoldal lapjából)
# ---------------------------------------------------------------------------
SZEKTOR_OPTIONS = [
    "A - Agrárszektor",
    "C - Autóipar",
    "D - Tartós fogyasztási cikkek",
    "E - Közmüvek és energia",
    "F - FMCG",
    "H - Health Care",
    "I - ICT",
    "K - Közlekedés",
    "M - Média",
    "P - Pénzügy",
    "R - Retail / HORECA",
    "S - Social / NGO / GO",
    "T - Turizmus",
    "X - Egyéb",
]

STATUS_LABELS = {
    "folyamatban": "Folyamatban",
    "lezarva": "Lezárva",
    "elutasitva": "Elutasítva",
}


# ---------------------------------------------------------------------------
# Új ajánlat dialog
# ---------------------------------------------------------------------------


@st.dialog("Új ajánlat létrehozása")
def _new_offer_dialog():
    db = get_session()
    clients = crud.get_all_clients(db)

    if not clients:
        st.warning("Nincs ügyfél az adatbázisban. Futtasd le a seed_data.py-t!")
        db.close()
        return

    client_names = [c.nev for c in clients]
    client_map = {c.nev: c.id for c in clients}

    ugyfel_nev = st.selectbox("Ügyfél *", client_names)
    szektor = st.selectbox(
        "Ügyfélszektor *",
        SZEKTOR_OPTIONS,
        help="Ez határozza meg a nyilvántartó szám betűjelét.",
    )
    projekt_neve = st.text_input("Projekt neve *", placeholder="pl. Márkakövetés 2026")
    uzletszerzo = st.selectbox(
        "Üzletszerző *",
        UZLETSZERZO_OPTIONS,
        index=None,
        placeholder="— Válassz üzletszerzőt —",
    )

    st.caption("A nyilvántartó szám (pl. 26I001) automatikusan generálódik.")

    col1, col2 = st.columns(2)
    if col1.button("Mégse", use_container_width=True):
        st.session_state.show_new_offer = False
        db.close()
        st.rerun()

    if col2.button("Létrehozás", type="primary", use_container_width=True):
        if not projekt_neve.strip():
            st.error("A projekt neve kötelező!")
        elif uzletszerzo is None:
            st.error("Az üzletszerző megadása kötelező!")
        else:
            offer = crud.create_offer(
                db=db,
                szektor=szektor,
                owner_id=st.session_state.current_user_id,
                projekt_neve=projekt_neve.strip(),
            )
            crud.upsert_stage1_nyitooldal(
                db,
                offer.id,
                {
                    "ugyfel_id": client_map[ugyfel_nev],
                    "ugyfel_szektor": szektor,
                    "uzletszerzo": uzletszerzo,
                },
            )
            st.session_state.show_new_offer = False
            st.session_state.selected_offer_id = offer.id
            st.session_state.page = "detail"
            db.close()
            st.rerun()

    db.close()


# ---------------------------------------------------------------------------
# Fő nézet: ajánlat lista
# ---------------------------------------------------------------------------


def render_offer_list():
    db = get_session()
    current_user = crud.get_user_by_id(db, st.session_state.current_user_id)

    st.title(APP_TITLE)
    st.caption(
        f"👤 Developer mód  –  {current_user.nev if current_user else 'Ismeretlen felhasználó'}"
    )
    st.divider()

    col_title, col_btn = st.columns([5, 1])
    col_title.subheader("Ajánlatok")

    if col_btn.button("＋ Új ajánlat", type="primary", use_container_width=True):
        st.session_state.show_new_offer = True

    if st.session_state.get("show_new_offer"):
        _new_offer_dialog()

    offers = crud.get_all_offers(db)

    if not offers:
        st.info(
            "Még nincs felvitt ajánlat. Kattints az **＋ Új ajánlat** gombra az első létrehozásához."
        )
        db.close()
        return

    rows = []
    for o in offers:
        ugyfel_nev = "—"
        if o.stage1_nyitooldal and o.stage1_nyitooldal.ugyfel:
            ugyfel_nev = o.stage1_nyitooldal.ugyfel.nev
        rows.append(
            {
                "_id": o.id,
                "Szám": o.nyilvantarto_szam,
                "Projekt neve": o.projekt_neve or "—",
                "Ügyfél": ugyfel_nev,
                "Üzletszerző": (
                    o.stage1_nyitooldal.uzletszerzo
                    if o.stage1_nyitooldal and o.stage1_nyitooldal.uzletszerzo
                    else "—"
                ),
                "Szakasz": f"Szakasz {o.current_stage}",
                "Státusz": STATUS_LABELS.get(o.status, o.status),
                "Felelős": o.current_owner.nev if o.current_owner else "—",
                "Létrehozva": o.created_at.strftime("%Y-%m-%d"),
            }
        )

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_id"])

    event = st.dataframe(
        display_df,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
    )

    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_id = rows[selected_idx]["_id"]
        if st.button("Megnyitás →", type="primary"):
            db.close()
            st.session_state.selected_offer_id = selected_id
            st.session_state.page = "detail"
            st.rerun()
    else:
        st.caption("Kattints egy sorra a kijelöléshez, majd nyisd meg.")

    db.close()
