import streamlit as st
from datetime import date, timedelta
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

    KUTATAS_TIPUSA_OPTIONS = ["Szemiotika", "Kvalitátív", "Kvantitatív"]

    st.caption(
        "A **\\* csillaggal jelölt mezők** kötelezően kitöltendők – ezek nélkül "
        "a Kalkuláció fül nem érhető el."
    )

    with st.form(f"form_tartalom_{offer_id}"):

        # ── Önálló alapparaméterek ──────────────────────────────────────────
        saved_kutatas_tipusa = t.kutatas_tipusa if t else None
        # Kutatás típusa: mentés után zárolva (kalkuláció ehhez kötve).
        # Célcsoport a Kalkuláció fülre került, ott szabadon változtatható.
        kutatas_tipusa_locked = bool(saved_kutatas_tipusa)

        kutatas_tipusa_idx = (
            KUTATAS_TIPUSA_OPTIONS.index(saved_kutatas_tipusa)
            if saved_kutatas_tipusa in KUTATAS_TIPUSA_OPTIONS
            else None
        )
        kutatas_tipusa = st.selectbox(
            "Kutatás típusa \\*",
            KUTATAS_TIPUSA_OPTIONS,
            index=kutatas_tipusa_idx,
            placeholder="Válassz kutatástípust…",
            disabled=(not is_editable) or kutatas_tipusa_locked,
            help=(
                "Mentés után már nem módosítható, mert a kalkuláció ehhez van kötve."
                if kutatas_tipusa_locked
                else "Kötelező mező – ez határozza meg, melyik kalkulációs sablon töltődik be."
            ),
        )
        # Letiltott mezőknél a Streamlit None-t ad vissza – használjuk a mentett értéket.
        if kutatas_tipusa_locked:
            kutatas_tipusa = saved_kutatas_tipusa

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

        KANTAR_TERMEK_OPTIONS = [
            "Nincs",
            "TRI*M",
            "Needscope",
            "Link",
            "Conversion Model",
            "AdEffect",
            "Holistic Brand Guidance",
            "ContextLab",
            "CrossMedia",
            "Brand Lift Insights (BLI)",
            "AdNow",
            "Meaningfully Different Framework (MDF)",
        ]

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
            fobb_lepesek = st.text_area(
                "Főbb lépések",
                value=t.fobb_lepesek or "" if t else "",
                height=120,
                disabled=not is_editable,
                help="Soronként egy lépést adj meg.",
                placeholder="1. Anyaggyűjtés és előzetes elemzés\n2. Kódok és jelek azonosítása\n3. ...",
            )
            # Kantar márkázott termék – Kvalitatív és Kvantitatív kutatástípusnál jelenik meg
            kantar_markezett_termek = None
            if kutatas_tipusa in ("Kvalitátív", "Kvantitatív"):
                saved_kantar = t.kantar_markezett_termek if t else None
                kantar_idx = (
                    KANTAR_TERMEK_OPTIONS.index(saved_kantar)
                    if saved_kantar in KANTAR_TERMEK_OPTIONS
                    else 0
                )
                kantar_markezett_termek = st.selectbox(
                    "Kantar márkázott termék",
                    KANTAR_TERMEK_OPTIONS,
                    index=kantar_idx,
                    disabled=not is_editable,
                    help="Kantar-tulajdonú eszköz, ha releváns (kvalitatív / kvantitatív kutatásnál).",
                )

        # ── 3. Időkeret ──────────────────────────────────────────────────────
        with st.expander("3. Időkeret", expanded=False):
            ajanlat_elbiralasa = st.date_input(
                "Az ajánlat elbírálásának várható időpontja",
                value=(
                    t.ajanlat_elbiralasa if t and t.ajanlat_elbiralasa else date.today()
                ),
                disabled=not is_editable,
                format="YYYY.MM.DD",
            )
            col1, col2 = st.columns(2)
            tervezett_indulas = col1.date_input(
                "Tervezett indulás",
                value=(
                    t.tervezett_indulas if t and t.tervezett_indulas else date.today()
                ),
                disabled=not is_editable,
                format="YYYY.MM.DD",
            )
            # A várható befejezés nem lehet korábbi, mint tervezett indulás + 1 nap.
            befejezes_min = tervezett_indulas + timedelta(days=1)
            saved_befejezes = t.varhato_befejezes if t and t.varhato_befejezes else None
            befejezes_value = (
                saved_befejezes
                if saved_befejezes and saved_befejezes >= befejezes_min
                else befejezes_min
            )
            varhato_befejezes = col2.date_input(
                "Várható befejezés",
                value=befejezes_value,
                min_value=befejezes_min,
                disabled=not is_editable,
                format="YYYY.MM.DD",
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
                        "kutatasi_kerdesek": kutatasi_kerdesek,
                        "elemzendo_anyagok": elemzendo_anyagok,
                        "kutatasi_eszkozok": kutatasi_eszkozok,
                        "fobb_lepesek": fobb_lepesek,
                        "kantar_markezett_termek": kantar_markezett_termek,
                        "ajanlat_elbiralasa": ajanlat_elbiralasa,
                        "tervezett_indulas": tervezett_indulas,
                        "varhato_befejezes": varhato_befejezes,
                    },
                )
                st.toast("Tartalom mentve!")
                st.rerun()
        else:
            st.form_submit_button("Mentés", disabled=True)
