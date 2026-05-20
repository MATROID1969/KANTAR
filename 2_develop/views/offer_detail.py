import streamlit as st

from db.database import get_session
from db import crud
from views.stage1_nyitooldal import render_stage1_nyitooldal
from views.stage1_tartalom import render_stage1_tartalom
from views.stage1_kalkulacio import render_stage1_kalkulacio
from views.stage_placeholder import render_stage_placeholder

STAGE_NAMES = {
    1: "Ajánlatkészítés",
    2: "Véglegesítés",
    3: "Megvalósítás",
    4: "Számlázás",
}

STATUS_LABELS = {
    "folyamatban": "Folyamatban",
    "lezarva": "Lezárva",
    "elutasitva": "Elutasítva",
}


# ---------------------------------------------------------------------------
# Szakasz lezárása és átadása – dialog
# ---------------------------------------------------------------------------


@st.dialog("Szakasz lezárása és átadása")
def _handoff_dialog(offer_id: int, from_stage: int):
    db = get_session()
    users = crud.get_all_users(db)

    if not users:
        st.error("Nincs felhasználó az adatbázisban.")
        db.close()
        return

    user_names = [u.nev for u in users]
    user_map = {u.nev: u.id for u in users}

    st.markdown(f"**Szakasz {from_stage} → Szakasz {from_stage + 1}** lezárása")
    st.divider()

    to_user_nev = st.selectbox("Következő felelős *", user_names)
    megjegyzes = st.text_area("Megjegyzés (opcionális)", max_chars=500)

    col1, col2 = st.columns(2)
    if col1.button("Mégse", use_container_width=True):
        st.session_state.show_handoff = False
        db.close()
        st.rerun()

    if col2.button("Lezárás és átadás", type="primary", use_container_width=True):
        crud.handoff_and_advance(
            db=db,
            offer_id=offer_id,
            from_user_id=st.session_state.current_user_id,
            to_user_id=user_map[to_user_nev],
            megjegyzes=megjegyzes,
        )
        st.session_state.show_handoff = False
        db.close()
        st.rerun()

    db.close()


# ---------------------------------------------------------------------------
# Fő nézet: ajánlat részlet
# ---------------------------------------------------------------------------


def render_offer_detail(offer_id: int):
    db = get_session()
    offer = crud.get_offer_by_id(db, offer_id)

    if not offer:
        st.error("Az ajánlat nem található.")
        if st.button("← Vissza a listához"):
            st.session_state.page = "list"
            st.rerun()
        db.close()
        return

    # Vissza gomb
    if st.button("← Vissza a listához"):
        db.close()
        st.session_state.page = "list"
        st.session_state.selected_offer_id = None
        st.rerun()

    # Fejléc – nyilvántartási szám szövegesen, nem ikonnal
    st.title(f"Nyilvántartási száma: {offer.nyilvantarto_szam}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Szakasz", f"Szakasz {offer.current_stage} – {STAGE_NAMES[offer.current_stage]}"
    )
    col2.metric("Státusz", STATUS_LABELS.get(offer.status, offer.status))
    col3.metric("Felelős", offer.current_owner.nev if offer.current_owner else "—")
    col4.metric("Létrehozva", offer.created_at.strftime("%Y-%m-%d"))
    st.divider()

    # ── Csak az aktuális + már lezárt szakaszok jelennek meg tabként ────────
    # Nincs előreugrási lehetőség – a felhasználó csak oda kattinthat,
    # ahol a projekt jelenleg van vagy ahol már járt.
    visible_stages = list(range(1, offer.current_stage + 1))

    tab_labels = [
        STAGE_NAMES[i] + (" (lezárva)" if offer.current_stage > i else "")
        for i in visible_stages
    ]
    tabs = st.tabs(tab_labels)

    for tab, stage_num in zip(tabs, visible_stages):
        with tab:
            if stage_num == 1:
                _render_stage1(offer, db)
            else:
                render_stage_placeholder(stage_num=stage_num, offer=offer)

    db.close()


# ---------------------------------------------------------------------------
# Szakasz 1 fülek (Nyitóoldal / Tartalom / Kalkuláció)
# A "Lezárás és átadás" gomb CSAK a Kalkuláció fülön jelenik meg.
# ---------------------------------------------------------------------------


def _render_stage1(offer, db):
    is_editable = offer.current_stage == 1 and offer.status == "folyamatban"

    # A Kalkuláció fül csak akkor jelenik meg egyáltalán, ha a Tartalom fülön
    # mindkét kötelező mező (Kutatás típusa, Célcsoport) ki van töltve.
    tartalom = crud.get_stage1_tartalom(db, offer.id)
    hianyzo = []
    if not (tartalom and tartalom.kutatas_tipusa):
        hianyzo.append("Kutatás típusa")
    if not (tartalom and tartalom.celcsoport):
        hianyzo.append("Célcsoport")
    kalk_elerheto = not hianyzo

    if kalk_elerheto:
        sub_tab_labels = ["Nyitóoldal", "Tartalom", "Kalkuláció"]
    else:
        sub_tab_labels = ["Nyitóoldal", "Tartalom"]
    sub_tabs = st.tabs(sub_tab_labels)

    with sub_tabs[0]:
        render_stage1_nyitooldal(offer_id=offer.id, is_editable=is_editable, db=db)

    with sub_tabs[1]:
        if not kalk_elerheto:
            st.info(
                "A **Kalkuláció** fül akkor válik elérhetővé, ha kitöltöd az alábbi "
                "kötelező mezőket: **" + ", ".join(hianyzo) + "**."
            )
        render_stage1_tartalom(offer_id=offer.id, is_editable=is_editable, db=db)

    if kalk_elerheto:
        with sub_tabs[2]:
            render_stage1_kalkulacio(offer_id=offer.id, is_editable=is_editable, db=db)

            if is_editable:
                st.divider()
                _, col_btn = st.columns([5, 2])
                if col_btn.button(
                    "Lezárás és átadás",
                    type="primary",
                    use_container_width=True,
                    key=f"handoff_btn_stage1_{offer.id}",
                ):
                    st.session_state.show_handoff = True

                if st.session_state.get("show_handoff"):
                    _handoff_dialog(offer.id, from_stage=1)
