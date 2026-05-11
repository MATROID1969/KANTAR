import streamlit as st
from sqlalchemy.orm import Session

from db import crud

# ---------------------------------------------------------------------------
# Segédadatok – az Excel Nyitóoldal lapjából
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

KATEGORIA_OPTIONS = ["Ügynökség", "Kantar", "Hazai ügyfél", "Nemzetközi ügyfél"]

KONTAKT_OPTIONS = ["Döntéshozó", "Döntés-előkészítő", "Felhasználó", "Beszerző"]

KERETSZERZODES_OPTIONS = ["Nincs", "Van"]

DOMAIN_OPTIONS = [
    "Analytics",
    "Brand",
    "Commerce",
    "Creative",
    "Customer Experience",
    "Innovation",
    "Media",
    "Public",
    "TGI",
    "Egyéb",
]

UZLETSZERZO_OPTIONS = [
    "Falus Tamás",
    "Harcos Andrea",
    "Hegedüs László",
    "Hoffmann Márta",
    "Jüttner Ádám",
    "Kovács Brigitta",
    "Loránt Andrea",
    "Nagy Attila",
    "Paár György",
    "Perjés Tamás",
    "Szilágyi Ákos",
    "Tolnai Gábor",
    "van der Wildt Peter",
]

ELFOGADAS_LABELS = [
    "10%",
    "20%",
    "30%",
    "40%",
    "50%",
    "60%",
    "70%",
    "80%",
    "90%",
    "100%",
]
ELFOGADAS_VALUES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

DIVIZION_OPTIONS = ["B - Belső", "K - MI divízió", "M - Média divízió"]


def _idx(options: list, value):
    """
    Biztonságos index-keresés a selectbox előtöltéséhez.
    None-t ad vissza, ha az érték nincs beállítva – így a widget üres marad.
    """
    if value is None or value not in options:
        return None
    return options.index(value)


def _label(text: str, filled: bool) -> str:
    """
    Sötétkék (erős színű) labelt ad, ha a mező már ki van töltve.
    Streamlit a label-ben támogatja a Markdown egy részét.
    """
    if filled:
        return f":blue[**{text}** ✓]"
    return text


# ---------------------------------------------------------------------------
# Nyitóoldal form renderelése
# ---------------------------------------------------------------------------


def render_stage1_nyitooldal(offer_id: int, is_editable: bool, db: Session):
    nyitooldal = crud.get_stage1_nyitooldal(db, offer_id)
    clients = crud.get_all_clients(db)
    client_names = [c.nev for c in clients]
    client_ids = [c.id for c in clients]

    # Pre-fill értékek az adatbázisból
    saved_client_id = nyitooldal.ugyfel_id if nyitooldal else None
    saved_kategoria = nyitooldal.ugyfel_kategoria if nyitooldal else None
    saved_szektor = nyitooldal.ugyfel_szektor if nyitooldal else None
    saved_kontakt = nyitooldal.kontakt if nyitooldal else None
    saved_keretszerzodes = nyitooldal.keretszerzodes if nyitooldal else None
    saved_domain = nyitooldal.domain if nyitooldal else None
    saved_uzletszerzo = nyitooldal.uzletszerzo if nyitooldal else None
    saved_elfogadas = nyitooldal.elfogadas_eselye if nyitooldal else None
    saved_divizion = nyitooldal.divizion if nyitooldal else None
    saved_orszagok = nyitooldal.orszagok_szama if nyitooldal else 1

    client_idx = (
        client_ids.index(saved_client_id) if saved_client_id in client_ids else None
    )

    if not is_editable:
        st.info("Ez a szakasz lezárult – az adatok csak olvasható módban jelennek meg.")

    # ── Az ügyfél és a szektor a nyilvántartási szám alapját képezi,
    #    ezért külön (zárolt) blokkban jelenik meg, sötétkék kiemeléssel.
    identity_locked = nyitooldal is not None
    saved_ugyfel_nev = None
    if saved_client_id is not None:
        for c in clients:
            if c.id == saved_client_id:
                saved_ugyfel_nev = c.nev
                break

    with st.container(border=True):
        st.markdown("##### Nyilvántartási szám alapadatai (nem módosítható)")
        st.write("")
        ic1, ic2 = st.columns(2)
        with ic1:
            st.markdown("**Ügyfélnév**")
            st.markdown(
                f"<div style='color:#0b3d91; font-weight:700; font-size:1.05rem; "
                f"padding:0.6rem 0.8rem; background:#eef3fb; border-radius:6px; "
                f"margin-bottom:0.5rem;'>"
                f"{saved_ugyfel_nev or '—'}</div>",
                unsafe_allow_html=True,
            )
        with ic2:
            st.markdown("**Ügyfélszektor**")
            st.markdown(
                f"<div style='color:#0b3d91; font-weight:700; font-size:1.05rem; "
                f"padding:0.6rem 0.8rem; background:#eef3fb; border-radius:6px; "
                f"margin-bottom:0.5rem;'>"
                f"{saved_szektor or '—'}</div>",
                unsafe_allow_html=True,
            )
        st.write("")

    # A form értékeit visszaadjuk a mentéshez (nem módosíthatók)
    ugyfel_nev = saved_ugyfel_nev
    ugyfel_szektor = saved_szektor

    with st.form(f"form_nyitooldal_{offer_id}"):
        col1, col2 = st.columns(2)

        with col1:
            ugyfel_kategoria = st.selectbox(
                _label("Ügyfélkategória", saved_kategoria is not None),
                KATEGORIA_OPTIONS,
                index=_idx(KATEGORIA_OPTIONS, saved_kategoria),
                placeholder="Válassz…",
                disabled=not is_editable,
            )
            kontakt = st.selectbox(
                _label("Kontakt típusa", saved_kontakt is not None),
                KONTAKT_OPTIONS,
                index=_idx(KONTAKT_OPTIONS, saved_kontakt),
                placeholder="Válassz…",
                disabled=not is_editable,
            )
            keretszerzodes = st.selectbox(
                _label("Keretszerződés", saved_keretszerzodes is not None),
                KERETSZERZODES_OPTIONS,
                index=_idx(KERETSZERZODES_OPTIONS, saved_keretszerzodes),
                placeholder="Válassz…",
                disabled=not is_editable,
            )
            uzletszerzo = st.selectbox(
                _label("Üzletszerző", saved_uzletszerzo is not None),
                UZLETSZERZO_OPTIONS,
                index=_idx(UZLETSZERZO_OPTIONS, saved_uzletszerzo),
                placeholder="Válassz üzletszerzőt…",
                disabled=not is_editable,
            )

        with col2:
            domain = st.selectbox(
                _label("Domain", saved_domain is not None),
                DOMAIN_OPTIONS,
                index=_idx(DOMAIN_OPTIONS, saved_domain),
                placeholder="Válassz…",
                disabled=not is_editable,
            )
            elfogadas_label = st.selectbox(
                _label("Elfogadás esélye", saved_elfogadas is not None),
                ELFOGADAS_LABELS,
                index=_idx(ELFOGADAS_VALUES, saved_elfogadas),
                placeholder="Válassz…",
                disabled=not is_editable,
            )
            divizion = st.selectbox(
                _label("Divízió", saved_divizion is not None),
                DIVIZION_OPTIONS,
                index=_idx(DIVIZION_OPTIONS, saved_divizion),
                placeholder="Válassz…",
                disabled=not is_editable,
            )
            orszagok_szama = st.number_input(
                _label("Országok száma", nyitooldal is not None),
                min_value=1,
                max_value=50,
                value=saved_orszagok if nyitooldal else 1,
                step=1,
                disabled=not is_editable,
                help="Ennyi ország-fül fog megnyílni a kalkulációban.",
            )

        if is_editable:
            submitted = st.form_submit_button("Mentés", type="primary")
            if submitted:
                ugyfel_id = saved_client_id  # zárolt – nem változik
                elfogadas_ertek = (
                    ELFOGADAS_VALUES[ELFOGADAS_LABELS.index(elfogadas_label)]
                    if elfogadas_label
                    else None
                )
                crud.upsert_stage1_nyitooldal(
                    db,
                    offer_id,
                    {
                        "ugyfel_id": ugyfel_id,
                        "ugyfel_kategoria": ugyfel_kategoria,
                        "ugyfel_szektor": ugyfel_szektor,
                        "kontakt": kontakt,
                        "keretszerzodes": keretszerzodes,
                        "domain": domain,
                        "uzletszerzo": uzletszerzo,
                        "elfogadas_eselye": elfogadas_ertek,
                        "divizion": divizion,
                        "orszagok_szama": int(orszagok_szama),
                    },
                )
                st.toast("Nyitóoldal adatok mentve!")
        else:
            st.form_submit_button("Mentés", disabled=True)
