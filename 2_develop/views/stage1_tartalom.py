import streamlit as st
from datetime import date
from sqlalchemy.orm import Session

from db import crud

# ---------------------------------------------------------------------------
# Tartalom form renderelése (Excel Tartalom lap alapján)
# Accordion (expander) szekciók: Háttér és cél | Módszertan | Időkeret | Várt eredmények
# ---------------------------------------------------------------------------


def render_stage1_tartalom(offer_id: int, is_editable: bool, db: Session):
    tartalom = crud.get_stage1_tartalom(db, offer_id)

    if not is_editable:
        st.info("Ez a szakasz lezárult – az adatok csak olvasható módban jelennek meg.")

    # Pre-fill értékek
    t = tartalom  # rövidítés

    KUTATAS_TIPUSA_OPTIONS = ["Szemiotika"]
    CELCSOPORT_OPTIONS = ["Lakossági", "Egyéb"]

    with st.form(f"form_tartalom_{offer_id}"):

        # ── Önálló alapparaméterek ──────────────────────────────────────────
        saved_kutatas_tipusa = t.kutatas_tipusa if t else None
        kutatas_tipusa_idx = (
            KUTATAS_TIPUSA_OPTIONS.index(saved_kutatas_tipusa)
            if saved_kutatas_tipusa in KUTATAS_TIPUSA_OPTIONS
            else None
        )
        kt_col, cs_col = st.columns(2)
        kutatas_tipusa = kt_col.selectbox(
            "Kutatás típusa",
            KUTATAS_TIPUSA_OPTIONS,
            index=kutatas_tipusa_idx,
            placeholder="Válassz kutatástípust…",
            disabled=not is_editable,
        )
        saved_celcsoport = t.celcsoport if t else None
        celcsoport_idx = (
            CELCSOPORT_OPTIONS.index(saved_celcsoport)
            if saved_celcsoport in CELCSOPORT_OPTIONS
            else None
        )
        celcsoport = cs_col.selectbox(
            "Célcsoport",
            CELCSOPORT_OPTIONS,
            index=celcsoport_idx,
            placeholder="Válassz célcsoportot…",
            disabled=not is_editable,
        )

        # ── 1. Háttér és cél ────────────────────────────────────────────────
        with st.expander("1. Háttér és cél", expanded=True):
            cel = st.text_area(
                "Cél",
                value=t.cel or "" if t else "",
                height=100,
                disabled=not is_editable,
                help="Mit szeretne elérni a megrendelő ezzel a kutatással?",
            )
            kutatasi_kerdesek = st.text_area(
                "Kutatási kérdések",
                value=t.kutatasi_kerdesek or "" if t else "",
                height=120,
                disabled=not is_editable,
                help="Soronként egy kérdést adj meg.",
                placeholder="- Milyen szimbolikus jelentések jelennek meg...\n- Hogyan értelmezik a fogyasztók...",
            )

        # ── 2. Módszertan ────────────────────────────────────────────────────
        with st.expander("2. Módszertan", expanded=False):
            elemzendo_anyagok = st.text_area(
                "Elemzendő anyagok",
                value=t.elemzendo_anyagok or "" if t else "",
                height=80,
                disabled=not is_editable,
                placeholder="Pl. reklámkampányok, online tartalmak, vizuális kommunikáció...",
            )
            kutatasi_eszkozok = st.text_area(
                "Kutatási eszközök",
                value=t.kutatasi_eszkozok or "" if t else "",
                height=80,
                disabled=not is_editable,
                placeholder="Pl. szemiotikai elemzés, fókuszcsoportok, mélyinterjúk...",
            )
            kulsos_alvallalkozo = st.text_area(
                "Külsős alvállalkozó",
                value=t.kulsos_alvallalkozo or "" if t else "",
                height=60,
                disabled=not is_editable,
                placeholder="Ha szükséges, a bevonandó alvállalkozó neve / köre.",
            )
            fobb_lepesek = st.text_area(
                "Főbb lépések",
                value=t.fobb_lepesek or "" if t else "",
                height=120,
                disabled=not is_editable,
                help="Soronként egy lépést adj meg.",
                placeholder="1. Anyaggyűjtés és előzetes elemzés\n2. Kódok és jelek azonosítása\n3. ...",
            )

        # ── 3. Időkeret ──────────────────────────────────────────────────────
        with st.expander("3. Időkeret", expanded=False):
            kutatas_idotartama = st.text_input(
                "Kutatás időtartama",
                value=t.kutatas_idotartama or "" if t else "",
                disabled=not is_editable,
                placeholder="Pl. 4-6 hét",
            )
            col1, col2 = st.columns(2)
            tervezett_indulas = col1.date_input(
                "Tervezett indulás",
                value=(
                    t.tervezett_indulas if t and t.tervezett_indulas else date.today()
                ),
                disabled=not is_editable,
            )
            varhato_befejezes = col2.date_input(
                "Várható befejezés",
                value=(
                    t.varhato_befejezes if t and t.varhato_befejezes else date.today()
                ),
                disabled=not is_editable,
            )

        # ── 4. Várt eredmények ───────────────────────────────────────────────
        with st.expander("4. Várt eredmények", expanded=False):
            vart_eredmenyek = st.text_area(
                "Várt eredmények",
                value=t.vart_eredmenyek or "" if t else "",
                height=120,
                disabled=not is_editable,
                help="Soronként egy eredményt adj meg.",
                placeholder="- Átfogó szemiotikai térkép...\n- Fogyasztói visszacsatolások...",
            )

        if is_editable:
            submitted = st.form_submit_button("Mentés", type="primary")
            if submitted:
                crud.upsert_stage1_tartalom(
                    db,
                    offer_id,
                    {
                        "cel": cel,
                        "kutatas_tipusa": kutatas_tipusa,
                        "celcsoport": celcsoport,
                        "kutatasi_kerdesek": kutatasi_kerdesek,
                        "elemzendo_anyagok": elemzendo_anyagok,
                        "kutatasi_eszkozok": kutatasi_eszkozok,
                        "kulsos_alvallalkozo": kulsos_alvallalkozo,
                        "fobb_lepesek": fobb_lepesek,
                        "kutatas_idotartama": kutatas_idotartama,
                        "tervezett_indulas": tervezett_indulas,
                        "varhato_befejezes": varhato_befejezes,
                        "vart_eredmenyek": vart_eredmenyek,
                    },
                )
                st.toast("Tartalom mentve!")
        else:
            st.form_submit_button("Mentés", disabled=True)
