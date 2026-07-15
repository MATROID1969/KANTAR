"""
Szakasz 1 – Kalkuláció: DESP / COCR / SUCL.

Az Excel (1_documents/desp.xlsx) alapján képezzük le a paramétereket.

Blokkok:
  1) Kantar márkázott termékek  (11 termék, Van/Nincs)
  2) Szervezés                  (MCP, nehézség, kontaktlista, ügyfél szervezés)
  3) Terepmunka                 (1-10: kvalitatív típusok; 11=Napló; 12=Blog;
                                  13=Megfigyelés; 14=Workshop)
  4) Feldolgozás
  5) Plusz szolgáltatások       (Kiírás, Fordítás, Tréning, Desk research, stb.)
  6) Egyéb

FIGYELEM – calc_munkaora: az Excel óraértékek még üresek.
Minden munkaóra-képlet PLACEHOLDER (0.0).
"""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st
from sqlalchemy.orm import Session

from db import crud

# ---------------------------------------------------------------------------
# Konstansok
# ---------------------------------------------------------------------------

NEM_IGEN = ["0. Nem", "1. Igen"]
NINCS_VAN = ["0. Nincs", "1. Van"]
FORDITAS_OPTIONS = [
    "0. Nincs",
    "1. Fordítóval",
    "2. Fordítóval, lektorálva",
    "3. Szoftverrel",
]
EXTRA_ROVID_OPTIONS = ["1. Normál", "2. Extra rövid (1,2× szorzó)"]

KANTAR_TERMEKEK = [
    ("trim", "TRI*M"),
    ("needscope", "Needscope"),
    ("link", "Link"),
    ("conversion_model", "Conversion Model"),
    ("adeffect", "AdEffect"),
    ("hollistic_brand_guidance", "Holistic Brand Guidance"),
    ("contextlab", "ContextLab"),
    ("crossmedia", "CrossMedia"),
    ("brand_lift_insights", "Brand Lift Insights (BLI)"),
    ("adnow", "AdNow"),
    ("mdf", "Meaningfully Different Framework (MDF)"),
]

TEREP_TIPUSOK = [
    "1. Mélyinterjú",
    "2. Páros interjú",
    "3. Triád",
    "4. Mini csoport (4 fő)",
    "5. Csoport (6 fős)",
    "6. Csoport (8 fős)",
    "7. XXL Csoport (10-12 fő)",
    "8. Bi-pólus (2 csoport)",
    "9. Konfliktus csoport",
    "10. Elkísért vásárlás (AST)",
    "11. Napló",
    "12. Blog",
    "13. Megfigyelés",
    "14. Workshop",
]

PLATFORM_OPTIONS = ["1. On-line", "2. Off-line", "3. Telefon"]
INTERJU_HOSSZA = [
    "1. 30 perc",
    "2. 45 perc",
    "3. 60 perc",
    "4. 90 perc",
    "5. 120 perc",
    "6. 150 perc",
    "7. 180 perc",
]
MEGKERD_KORE = [
    "1. Lakosság",
    "2. Vállalati – SOHO",
    "3. Vállalati – SMB",
    "4. Vállalati – LB",
    "5. Orvos",
    "6. Szakértő",
]
MEGKERD_HELYE = ["1. Budapest", "2. Nagyváros", "3. Kisváros", "4. Falvak"]
ELOFELADAT = ["1. Nincs", "2. Könnyű", "3. Közepes", "4. Bonyolult (pl. márkanovella)"]
NAPI_IDO = ["1. 15 perc", "2. 30 perc", "3. 45 perc", "4. 60 perc"]
BLOG_FELULET = ["1. Mi biztosítjuk", "2. Megbízó biztosítja"]
SZERVEZES_NEHEZSEG = [
    "1. Egyszerű (nincs kvóta)",
    "2. Közepes (márkafogyasztó, de speciális kvóta nélkül)",
    "3. Nehéz (speciális kvóta)",
    "4. Extrém (szűk célcsoport + kvóta)",
]
KONTAKTLISTA = ["1. Nincs kontaktlista", "2. Kantar Hoffmann készíti", "3. Ügyfél adja"]
UGYFEL_SZERVEZES = [
    "1. Nincs ügyféltámogatás",
    "2. Ügyfél szervezi teljesen",
    "3. Ügyfél előmelegíti, de mi szervezzük",
]
KIRAS_OPTIONS = [
    "0. Nincs",
    "1. Gépeléssel – szószerint",
    "2. Kiírás (kivonatolt)",
    "3. Automatizálva",
]
DESK_RESEARCH = ["1. Igen", "2. Nem"]

MUNKAORA_CATS = [
    ("szervezoi", "Szervezői"),
    ("ellenorzesi", "Ellenőrzési"),
    ("szervezesi_vez", "Szervezési vezető"),
    ("dp", "DP"),
    ("dp_vez", "DP vezető"),
    ("junior_kut", "Junior kutatói"),
    ("executive_kut", "Executive kutatói"),
    ("szenior_kut", "Szenior kutatói"),
    ("kut_ig", "Kutatási igazgatói"),
    ("gad", "GAD"),
]


# ---------------------------------------------------------------------------
# Alapértelmezett paraméterstruktúra
# ---------------------------------------------------------------------------


def default_params() -> dict:
    return {
        "kantar_markezett": {
            "active": False,
            **{key: 0 for key, _ in KANTAR_TERMEKEK},
        },
        "szervezes": {
            "active": False,
            "mcp": 0,
            "nehezseg": 1,
            "kontaktlista": 1,
            "ugyfel_szervezes": 1,
        },
        "terepmunka": {
            "active": False,
            "tipus": None,
            # 1–10: kvalitatív interjú típusok
            "szama": 0,
            "platform": 1,
            "interju_hossza": 1,
            "megkerdezettek_kore": 1,
            "megkerdezees_helye": 1,
            "kisero": 0,
            "elofeladat": 1,
            # 11: Napló
            "naplo_napok": 0,
            "naplo_resztvevok": 0,
            "naplo_megkerd_kore": 1,
            "naplo_napi_ido": 1,
            # 12: Blog
            "blog_napok": 0,
            "blog_resztvevok": 0,
            "blog_megkerd_kore": 1,
            "blog_napi_ido": 1,
            "blog_felulet": 1,
            # 13: Megfigyelés
            "mf_helyszinek": 0,
            "mf_oraszam": 0.0,
            "mf_budapest_pct": 0,
            "mf_videk_pct": 0,
            # 14: Workshop
            "ws_szam": 0,
            "ws_idotartam": 0.0,
            "ws_budapest_pct": 0,
            "ws_videk_pct": 0,
        },
        "feldolgozas": {
            "active": False,
            "debrief": 0,
            "top_line": 0,
            "egyszeru_elemzes": 0,
            "melyelemzes": 0,
            "management_summary": 0,
            "online_prezentacio": 0,
            "szemelyes_prezentacio_bp": 0,
            "szemelyes_prezentacio_videk": 0,
            "tematikus_osszefoglalo": 0,
            "filmkeszites_ora": 0.0,
            "workshop_ora": 0.0,
        },
        "plusz_szolg": {
            "active": False,
            "kiras": 0,
            "forditas": 0,
            "szinkrontolmacs_ora": 0.0,
            "teremberles": 0,
            "catering": 0,
            "extra_rovid": 1,
            "trening": 0,
            "desk_research": 2,
        },
        "egyeb": {
            "active": False,
            "munkaora": 0.0,
            "koltseg": 0.0,
            "megjegyzes": "",
        },
    }


# ---------------------------------------------------------------------------
# Kalkulációs logika – PLACEHOLDER
# ---------------------------------------------------------------------------


def _new_hours() -> dict:
    return {k: 0.0 for k, _ in MUNKAORA_CATS}


def _add(h: dict, key: str, val: float):
    h[key] = h.get(key, 0.0) + val


def calc_munkaora(p: dict) -> dict:
    """PLACEHOLDER – az Excel óraértékek még nem kerültek megadásra."""
    h = _new_hours()

    # TODO: Kantar márkázott termékek – óraszámok még hiányoznak
    # TODO: Szervezés – óraszámok még hiányoznak
    # TODO: Terepmunka (1-14 típus) – óraszámok még hiányoznak
    # TODO: Feldolgozás – óraszámok még hiányoznak

    ps = p.get("plusz_szolg", {})
    if bool(ps.get("active")) and int(ps.get("extra_rovid") or 1) == 2:
        for k in h:
            h[k] *= 1.2

    eg = p.get("egyeb", {})
    if bool(eg.get("active")):
        extra = float(eg.get("munkaora") or 0)
        if extra > 0:
            _add(h, "szervezoi", extra)

    return h


# ---------------------------------------------------------------------------
# UI blokkok
# ---------------------------------------------------------------------------


def _render_kantar(p: dict, is_editable: bool, kp: str):
    b = p["kantar_markezett"]
    with st.expander("1) Kantar márkázott termékek", expanded=False):
        b["active"] = st.checkbox(
            "Van Kantar márkázott termék",
            value=bool(b.get("active")),
            key=f"{kp}_km_active",
            disabled=not is_editable,
        )
        if not b["active"]:
            return
        st.caption("Válaszd ki, melyik termékek relevánsak:")
        for key, label in KANTAR_TERMEKEK:
            b[key] = int(
                st.selectbox(
                    label,
                    NINCS_VAN,
                    index=int(b.get(key) or 0),
                    key=f"{kp}_km_{key}",
                    disabled=not is_editable,
                ).split(".")[0]
            )


def _render_szervezes(p: dict, is_editable: bool, kp: str):
    s = p["szervezes"]
    with st.expander("2) Szervezés", expanded=False):
        s["active"] = st.checkbox(
            "Van szervezés",
            value=bool(s.get("active")),
            key=f"{kp}_sz_active",
            disabled=not is_editable,
        )
        if not s["active"]:
            return

        s["mcp"] = int(
            st.selectbox(
                "MCP / Koordinált projekt",
                NEM_IGEN,
                index=int(s.get("mcp") or 0),
                key=f"{kp}_sz_mcp",
                disabled=not is_editable,
                help="Default: 0 (Nem)",
            ).split(".")[0]
        )
        s["nehezseg"] = int(
            st.selectbox(
                "Szervezés nehézsége",
                SZERVEZES_NEHEZSEG,
                index=int(s.get("nehezseg") or 1) - 1,
                key=f"{kp}_sz_neh",
                disabled=not is_editable,
            ).split(".")[0]
        )
        s["kontaktlista"] = int(
            st.selectbox(
                "Kontaktlista",
                KONTAKTLISTA,
                index=int(s.get("kontaktlista") or 1) - 1,
                key=f"{kp}_sz_kontakt",
                disabled=not is_editable,
            ).split(".")[0]
        )
        s["ugyfel_szervezes"] = int(
            st.selectbox(
                "Ügyfél általi szervezés / előmelegítés",
                UGYFEL_SZERVEZES,
                index=int(s.get("ugyfel_szervezes") or 1) - 1,
                key=f"{kp}_sz_ugyfel",
                disabled=not is_editable,
            ).split(".")[0]
        )


def _render_terepmunka(p: dict, is_editable: bool, kp: str):
    t = p["terepmunka"]
    with st.expander("3) Terepmunka", expanded=False):
        t["active"] = st.checkbox(
            "Van terepmunka",
            value=bool(t.get("active")),
            key=f"{kp}_terep_active",
            disabled=not is_editable,
        )
        if not t["active"]:
            return

        saved_tipus = t.get("tipus")
        tipus_idx = (int(saved_tipus) - 1) if saved_tipus is not None else None
        tipus_label = st.selectbox(
            "Terepmunka típusa",
            TEREP_TIPUSOK,
            index=tipus_idx,
            placeholder="Válassz típust…",
            key=f"{kp}_terep_tipus",
            disabled=not is_editable,
        )
        t["tipus"] = int(tipus_label.split(".")[0]) if tipus_label else None
        tipus = t["tipus"]
        if tipus is None:
            return

        if 1 <= tipus <= 10:
            # Kvalitatív interjú típusok
            t["szama"] = st.number_input(
                "Darabszám (db)",
                min_value=0,
                step=1,
                value=int(t.get("szama") or 0),
                key=f"{kp}_terep_szam",
                disabled=not is_editable,
            )
            t["platform"] = int(
                st.selectbox(
                    "Platform",
                    PLATFORM_OPTIONS,
                    index=int(t.get("platform") or 1) - 1,
                    key=f"{kp}_terep_platform",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["interju_hossza"] = int(
                st.selectbox(
                    "Interjú hossza",
                    INTERJU_HOSSZA,
                    index=int(t.get("interju_hossza") or 1) - 1,
                    key=f"{kp}_terep_hossz",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["megkerdezettek_kore"] = int(
                st.selectbox(
                    "Megkérdezettek köre",
                    MEGKERD_KORE,
                    index=int(t.get("megkerdezettek_kore") or 1) - 1,
                    key=f"{kp}_terep_kor",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            if int(t.get("platform") or 1) == 2:  # off-line esetén
                t["megkerdezees_helye"] = int(
                    st.selectbox(
                        "Megkérdezés helye (csak off-line)",
                        MEGKERD_HELYE,
                        index=int(t.get("megkerdezees_helye") or 1) - 1,
                        key=f"{kp}_terep_hely",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
            t["kisero"] = int(
                st.selectbox(
                    "Kísérő",
                    NINCS_VAN,
                    index=int(t.get("kisero") or 0),
                    key=f"{kp}_terep_kisero",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["elofeladat"] = int(
                st.selectbox(
                    "Előfeladat",
                    ELOFELADAT,
                    index=int(t.get("elofeladat") or 1) - 1,
                    key=f"{kp}_terep_elofelad",
                    disabled=not is_editable,
                ).split(".")[0]
            )

        elif tipus == 11:  # Napló
            t["naplo_napok"] = st.number_input(
                "Napok száma (1–10)",
                min_value=0,
                max_value=10,
                step=1,
                value=int(t.get("naplo_napok") or 0),
                key=f"{kp}_naplo_napok",
                disabled=not is_editable,
            )
            t["naplo_resztvevok"] = st.number_input(
                "Résztvevők száma (10–40)",
                min_value=0,
                max_value=40,
                step=1,
                value=int(t.get("naplo_resztvevok") or 0),
                key=f"{kp}_naplo_reszt",
                disabled=not is_editable,
            )
            t["naplo_megkerd_kore"] = int(
                st.selectbox(
                    "Megkérdezettek köre",
                    MEGKERD_KORE,
                    index=int(t.get("naplo_megkerd_kore") or 1) - 1,
                    key=f"{kp}_naplo_kor",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["naplo_napi_ido"] = int(
                st.selectbox(
                    "Napi időráfordítás",
                    NAPI_IDO,
                    index=int(t.get("naplo_napi_ido") or 1) - 1,
                    key=f"{kp}_naplo_ido",
                    disabled=not is_editable,
                ).split(".")[0]
            )

        elif tipus == 12:  # Blog
            t["blog_napok"] = st.number_input(
                "Napok száma (1–10)",
                min_value=0,
                max_value=10,
                step=1,
                value=int(t.get("blog_napok") or 0),
                key=f"{kp}_blog_napok",
                disabled=not is_editable,
            )
            t["blog_resztvevok"] = st.number_input(
                "Résztvevők száma (10–40)",
                min_value=0,
                max_value=40,
                step=1,
                value=int(t.get("blog_resztvevok") or 0),
                key=f"{kp}_blog_reszt",
                disabled=not is_editable,
            )
            t["blog_megkerd_kore"] = int(
                st.selectbox(
                    "Megkérdezettek köre",
                    MEGKERD_KORE,
                    index=int(t.get("blog_megkerd_kore") or 1) - 1,
                    key=f"{kp}_blog_kor",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["blog_napi_ido"] = int(
                st.selectbox(
                    "Napi időráfordítás",
                    NAPI_IDO,
                    index=int(t.get("blog_napi_ido") or 1) - 1,
                    key=f"{kp}_blog_ido",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["blog_felulet"] = int(
                st.selectbox(
                    "Blog felület",
                    BLOG_FELULET,
                    index=int(t.get("blog_felulet") or 1) - 1,
                    key=f"{kp}_blog_felulet",
                    disabled=not is_editable,
                ).split(".")[0]
            )

        elif tipus == 13:  # Megfigyelés
            t["mf_helyszinek"] = st.number_input(
                "Helyszínek száma (db)",
                min_value=0,
                step=1,
                value=int(t.get("mf_helyszinek") or 0),
                key=f"{kp}_mf_helyszin",
                disabled=not is_editable,
            )
            t["mf_oraszam"] = st.number_input(
                "Megfigyelési munkaórák száma",
                min_value=0.0,
                step=0.5,
                value=float(t.get("mf_oraszam") or 0),
                key=f"{kp}_mf_ora",
                disabled=not is_editable,
            )
            col1, col2 = st.columns(2)
            t["mf_budapest_pct"] = col1.number_input(
                "Budapest (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(t.get("mf_budapest_pct") or 0),
                key=f"{kp}_mf_bp",
                disabled=not is_editable,
            )
            t["mf_videk_pct"] = col2.number_input(
                "Vidék (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(t.get("mf_videk_pct") or 0),
                key=f"{kp}_mf_vd",
                disabled=not is_editable,
            )
            if t["mf_oraszam"] > 0 and t["mf_budapest_pct"] + t["mf_videk_pct"] not in (
                0,
                100,
            ):
                st.warning("Budapest + Vidék % összege 100 kell legyen.")

        elif tipus == 14:  # Workshop
            t["ws_szam"] = st.number_input(
                "Workshopok száma (db)",
                min_value=0,
                step=1,
                value=int(t.get("ws_szam") or 0),
                key=f"{kp}_ws_szam",
                disabled=not is_editable,
            )
            t["ws_idotartam"] = st.number_input(
                "Egy workshop időtartama (óra)",
                min_value=0.0,
                step=0.5,
                value=float(t.get("ws_idotartam") or 0),
                key=f"{kp}_ws_ido",
                disabled=not is_editable,
            )
            col1, col2 = st.columns(2)
            t["ws_budapest_pct"] = col1.number_input(
                "Budapest (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(t.get("ws_budapest_pct") or 0),
                key=f"{kp}_ws_bp",
                disabled=not is_editable,
            )
            t["ws_videk_pct"] = col2.number_input(
                "Vidék (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(t.get("ws_videk_pct") or 0),
                key=f"{kp}_ws_vd",
                disabled=not is_editable,
            )
            if t["ws_szam"] > 0 and t["ws_budapest_pct"] + t["ws_videk_pct"] not in (
                0,
                100,
            ):
                st.warning("Budapest + Vidék % összege 100 kell legyen.")


def _render_feldolgozas(p: dict, is_editable: bool, kp: str):
    f = p["feldolgozas"]
    with st.expander("4) Feldolgozás", expanded=False):
        f["active"] = st.checkbox(
            "Van feldolgozás",
            value=bool(f.get("active")),
            key=f"{kp}_feld_active",
            disabled=not is_editable,
        )
        if not f["active"]:
            return

        for key, label, is_float in (
            ("debrief", "Debrief – szóbeli rövid összefoglaló (db)", False),
            ("top_line", "Top-line (db)", False),
            ("egyszeru_elemzes", "Egyszerű elemzés (db)", False),
            ("melyelemzes", "Mélyelemzés / deepdive report (db)", False),
            ("management_summary", "Management summary (db)", False),
            ("online_prezentacio", "Online prezentáció (db)", False),
            (
                "szemelyes_prezentacio_bp",
                "Személyes prezentáció Budapesten (db)",
                False,
            ),
            (
                "szemelyes_prezentacio_videk",
                "Személyes prezentáció vidéken (db)",
                False,
            ),
            ("tematikus_osszefoglalo", "Tematikus összefoglaló (db)", False),
            ("filmkeszites_ora", "Filmkészítés (óra)", True),
            ("workshop_ora", "Workshop (óra)", True),
        ):
            if is_float:
                f[key] = st.number_input(
                    label,
                    min_value=0.0,
                    step=0.5,
                    value=float(f.get(key) or 0),
                    key=f"{kp}_feld_{key}",
                    disabled=not is_editable,
                )
            else:
                f[key] = st.number_input(
                    label,
                    min_value=0,
                    step=1,
                    value=int(f.get(key) or 0),
                    key=f"{kp}_feld_{key}",
                    disabled=not is_editable,
                )


def _render_plusz(p: dict, is_editable: bool, kp: str):
    ps = p["plusz_szolg"]
    with st.expander("5) Plusz szolgáltatások", expanded=False):
        ps["active"] = st.checkbox(
            "Van plusz szolgáltatás",
            value=bool(ps.get("active")),
            key=f"{kp}_ps_active",
            disabled=not is_editable,
        )
        if not ps["active"]:
            return

        ps["kiras"] = int(
            st.selectbox(
                "Kiírás",
                KIRAS_OPTIONS,
                index=int(ps.get("kiras") or 0),
                key=f"{kp}_ps_kiras",
                disabled=not is_editable,
            ).split(".")[0]
        )
        ps["forditas"] = int(
            st.selectbox(
                "Fordítás",
                FORDITAS_OPTIONS,
                index=int(ps.get("forditas") or 0),
                key=f"{kp}_ps_ford",
                disabled=not is_editable,
            ).split(".")[0]
        )
        ps["szinkrontolmacs_ora"] = st.number_input(
            "Szinkrontolmács (óra)",
            min_value=0.0,
            step=0.5,
            value=float(ps.get("szinkrontolmacs_ora") or 0),
            key=f"{kp}_ps_tolmacs",
            disabled=not is_editable,
        )
        for key, label in (
            ("teremberles", "Terembérlés"),
            ("catering", "Catering (ha meleg étel)"),
            ("trening", "Tréning"),
        ):
            ps[key] = int(
                st.selectbox(
                    label,
                    NEM_IGEN,
                    index=int(ps.get(key) or 0),
                    key=f"{kp}_ps_{key}",
                    disabled=not is_editable,
                ).split(".")[0]
            )
        ps["extra_rovid"] = int(
            st.selectbox(
                "Extra rövid határidő",
                EXTRA_ROVID_OPTIONS,
                index=int(ps.get("extra_rovid") or 1) - 1,
                key=f"{kp}_ps_extra",
                disabled=not is_editable,
                help="Extra rövid: minden belső munkaóra × 1,2",
            ).split(".")[0]
        )
        # Desk research: 1=Igen, 2=Nem (fordított sorrend!)
        ps["desk_research"] = int(
            st.selectbox(
                "Desk research",
                DESK_RESEARCH,
                index=max(0, int(ps.get("desk_research") or 2) - 1),
                key=f"{kp}_ps_desk",
                disabled=not is_editable,
            ).split(".")[0]
        )


def _render_egyeb(p: dict, is_editable: bool, kp: str):
    eg = p["egyeb"]
    with st.expander("6) Egyéb", expanded=False):
        eg["active"] = st.checkbox(
            "Van egyéb tétel",
            value=bool(eg.get("active")),
            key=f"{kp}_eg_active",
            disabled=not is_editable,
        )
        if not eg["active"]:
            return

        eg["munkaora"] = st.number_input(
            "Egyéb munkaóra (Szervezőire kerül)",
            min_value=0.0,
            step=0.5,
            value=float(eg.get("munkaora") or 0),
            key=f"{kp}_eg_ora",
            disabled=not is_editable,
        )
        eg["koltseg"] = st.number_input(
            "Egyéb költség (Ft)",
            min_value=0.0,
            step=1000.0,
            value=float(eg.get("koltseg") or 0),
            key=f"{kp}_eg_koltseg",
            disabled=not is_editable,
        )
        eg["megjegyzes"] = st.text_area(
            "Megjegyzés",
            value=eg.get("megjegyzes") or "",
            height=80,
            key=f"{kp}_eg_megjegyzes",
            disabled=not is_editable,
        )


# ---------------------------------------------------------------------------
# Jobb oldali panel – PONTOSAN a többi modullal egyező CSS struktúra
# ---------------------------------------------------------------------------


def _render_munkaora_panel(h: dict, extra_rovid: bool = False):
    badge_extra = (
        " &nbsp; <span style='background:#fff3bf; color:#7a5a00; padding:2px 8px; "
        "border-radius:4px; font-size:0.75rem; font-weight:600;'>×1,2 extra rövid</span>"
        if extra_rovid
        else ""
    )
    panel_html = [
        "<div style='border:1px solid #d6dde8; border-radius:8px; padding:1rem; background:#f7f9fc;'>",
        "<div style='font-size:0.85rem; color:#0b3d91; font-weight:600; "
        "letter-spacing:0.04em; text-transform:uppercase; margin-bottom:0.25rem;'>Számolt munkaóra</div>",
        f"<div style='font-size:0.8rem; color:#5a6b80; margin-bottom:0.5rem;'>DESP / COCR / SUCL{badge_extra}</div>",
        "<div style='font-size:0.78rem; color:#e07b00; font-style:italic; margin-bottom:0.8rem;'>"
        "⚠️ Placeholder – az óraszámok megadása után aktív</div>",
        "<div style='display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.6rem;'>",
    ]
    for key, label in MUNKAORA_CATS:
        value = h.get(key, 0.0)
        v_str = (
            f"{value:.1f}"
            if isinstance(value, float) and value % 1
            else f"{int(value)}"
        )
        is_zero = value == 0
        bg = "#f4f5f7" if is_zero else "#ffffff"
        lbl_col = "#a0a8b5" if is_zero else "#5a6b80"
        val_col = "#a0a8b5" if is_zero else "#0b3d91"
        panel_html.append(
            f"<div style='background:{bg}; border:1px solid #e3e8f0; border-radius:6px; padding:0.6rem 0.7rem;'>"
            f"<div style='font-size:0.72rem; color:{lbl_col}; line-height:1.2; min-height:2.4em;'>{label} munkaóra</div>"
            f"<div style='font-size:1.5rem; font-weight:700; color:{val_col}; line-height:1.1; margin-top:0.25rem;'>{v_str}"
            "<span style='font-size:0.7rem; font-weight:500; color:#5a6b80; margin-left:0.3rem;'>óra</span></div></div>"
        )
    panel_html.append("</div>")
    osszesen = sum(h.values())
    panel_html.append(
        "<div style='display:flex; justify-content:space-between; padding:0.6rem 0.75rem; "
        "margin-top:0.8rem; background:#eef3fb; border-radius:6px;'>"
        "<span style='color:#0b3d91; font-weight:700; font-size:1.0rem;'>Összesen</span>"
        f"<span style='color:#0b3d91; font-weight:700; font-size:1.1rem;'>{osszesen:.1f} óra</span>"
        "</div></div>"
    )
    st.markdown("".join(panel_html), unsafe_allow_html=True)


def _render_param_summary_panel(p: dict):
    def row(label: str, value, unit: str = ""):
        v_disp = "—" if value in (None, "", 0, 0.0) else value
        is_zero = value in (None, "", 0, 0.0)
        bg = "#f4f5f7" if is_zero else "#ffffff"
        lbl_col = "#a0a8b5" if is_zero else "#3a4658"
        val_col = "#a0a8b5" if is_zero else "#0b3d91"
        return (
            "<div style='display:flex; justify-content:space-between; "
            f"padding:0.35rem 0.7rem; border-bottom:1px solid #eef0f4; background:{bg};'>"
            f"<span style='color:{lbl_col}; font-size:0.9rem;'>{label}</span>"
            f"<span style='color:{val_col}; font-weight:600; font-size:0.95rem;'>{v_disp}"
            + (
                f" <span style='color:#8a96a8; font-weight:500; font-size:0.85rem;'>{unit}</span>"
                if unit
                else ""
            )
            + "</span></div>"
        )

    sections = []

    km = p.get("kantar_markezett", {})
    if bool(km.get("active")):
        active_termekek = [
            label for key, label in KANTAR_TERMEKEK if int(km.get(key) or 0) == 1
        ]
        if active_termekek:
            sections.append(
                ("Kantar márkázott termékek", [row(t, "Van") for t in active_termekek])
            )

    s = p.get("szervezes", {})
    if bool(s.get("active")):
        neh_idx = int(s.get("nehezseg") or 1) - 1
        kont_idx = int(s.get("kontaktlista") or 1) - 1
        ugy_idx = int(s.get("ugyfel_szervezes") or 1) - 1
        sections.append(
            (
                "Szervezés",
                [
                    row("MCP / Koordinált", NEM_IGEN[int(s.get("mcp") or 0)]),
                    row(
                        "Nehézség",
                        (
                            SZERVEZES_NEHEZSEG[neh_idx]
                            if neh_idx < len(SZERVEZES_NEHEZSEG)
                            else "—"
                        ),
                    ),
                    row(
                        "Kontaktlista",
                        KONTAKTLISTA[kont_idx] if kont_idx < len(KONTAKTLISTA) else "—",
                    ),
                    row(
                        "Ügyfél szervezés",
                        (
                            UGYFEL_SZERVEZES[ugy_idx]
                            if ugy_idx < len(UGYFEL_SZERVEZES)
                            else "—"
                        ),
                    ),
                ],
            )
        )

    t = p.get("terepmunka", {})
    if bool(t.get("active")) and t.get("tipus") is not None:
        tipus = int(t.get("tipus"))
        if 1 <= tipus <= 10:
            tipus_label = TEREP_TIPUSOK[tipus - 1]
            terep_rows = [
                row("Típus", tipus_label),
                row("Darabszám", t.get("szama"), "db"),
                row("Platform", PLATFORM_OPTIONS[int(t.get("platform") or 1) - 1]),
                row(
                    "Interjú hossza",
                    INTERJU_HOSSZA[int(t.get("interju_hossza") or 1) - 1],
                ),
            ]
            sections.append(("Terepmunka", terep_rows))
        elif tipus == 11:
            sections.append(
                (
                    "Terepmunka – Napló",
                    [
                        row("Napok", t.get("naplo_napok"), "nap"),
                        row("Résztvevők", t.get("naplo_resztvevok"), "fő"),
                    ],
                )
            )
        elif tipus == 12:
            sections.append(
                (
                    "Terepmunka – Blog",
                    [
                        row("Napok", t.get("blog_napok"), "nap"),
                        row("Résztvevők", t.get("blog_resztvevok"), "fő"),
                    ],
                )
            )
        elif tipus == 13:
            sections.append(
                (
                    "Terepmunka – Megfigyelés",
                    [
                        row("Helyszínek", t.get("mf_helyszinek"), "db"),
                        row("Munkaórák", t.get("mf_oraszam"), "óra"),
                    ],
                )
            )
        elif tipus == 14:
            sections.append(
                (
                    "Terepmunka – Workshop",
                    [
                        row("Workshopok", t.get("ws_szam"), "db"),
                        row("Időtartam", t.get("ws_idotartam"), "óra/db"),
                    ],
                )
            )

    f = p.get("feldolgozas", {})
    if bool(f.get("active")):
        sections.append(
            (
                "Feldolgozás",
                [
                    row("Debrief", f.get("debrief"), "db"),
                    row("Top-line", f.get("top_line"), "db"),
                    row("Egyszerű elemzés", f.get("egyszeru_elemzes"), "db"),
                    row("Mélyelemzés", f.get("melyelemzes"), "db"),
                    row("Management summary", f.get("management_summary"), "db"),
                    row("Online prezentáció", f.get("online_prezentacio"), "db"),
                    row("Személyes prez. BP", f.get("szemelyes_prezentacio_bp"), "db"),
                    row(
                        "Személyes prez. vidék",
                        f.get("szemelyes_prezentacio_videk"),
                        "db",
                    ),
                    row(
                        "Tematikus összefoglaló", f.get("tematikus_osszefoglalo"), "db"
                    ),
                    row("Filmkészítés", f.get("filmkeszites_ora"), "óra"),
                    row("Workshop", f.get("workshop_ora"), "óra"),
                ],
            )
        )

    ps = p.get("plusz_szolg", {})
    if bool(ps.get("active")):
        kiras_idx = int(ps.get("kiras") or 0)
        ford_idx = int(ps.get("forditas") or 0)
        sections.append(
            (
                "Plusz szolgáltatások",
                [
                    row(
                        "Kiírás",
                        (
                            KIRAS_OPTIONS[kiras_idx]
                            if kiras_idx < len(KIRAS_OPTIONS)
                            else "—"
                        ),
                    ),
                    row(
                        "Fordítás",
                        (
                            FORDITAS_OPTIONS[ford_idx]
                            if ford_idx < len(FORDITAS_OPTIONS)
                            else "—"
                        ),
                    ),
                    row("Szinkrontolmács", ps.get("szinkrontolmacs_ora"), "óra"),
                    row("Terembérlés", NEM_IGEN[int(ps.get("teremberles") or 0)]),
                    row("Catering", NEM_IGEN[int(ps.get("catering") or 0)]),
                    row("Tréning", NEM_IGEN[int(ps.get("trening") or 0)]),
                    row(
                        "Extra rövid",
                        EXTRA_ROVID_OPTIONS[int(ps.get("extra_rovid") or 1) - 1],
                    ),
                    row(
                        "Desk research",
                        DESK_RESEARCH[max(0, int(ps.get("desk_research") or 2) - 1)],
                    ),
                ],
            )
        )

    eg = p.get("egyeb", {})
    if bool(eg.get("active")) and (
        (eg.get("munkaora") or 0) > 0
        or (eg.get("koltseg") or 0) > 0
        or eg.get("megjegyzes")
    ):
        sections.append(
            (
                "Egyéb",
                [
                    row("Egyéb munkaóra", eg.get("munkaora"), "óra"),
                    row("Egyéb ktg.", eg.get("koltseg"), "Ft"),
                    row("Megjegyzés", eg.get("megjegyzes") or "—"),
                ],
            )
        )

    if not sections:
        return

    html_parts = [
        "<div style='margin-bottom:0.8rem;'>"
        "<div style='font-size:0.78rem; color:#0b3d91; font-weight:700; "
        "letter-spacing:0.04em; text-transform:uppercase; margin-bottom:0.3rem;'>"
        f"{title}</div>"
        "<div style='border:1px solid #e3e8f0; border-radius:6px; overflow:hidden;'>"
        + "".join(rows_html)
        + "</div></div>"
        for title, rows_html in sections
    ]
    with st.expander("Paraméterek összegzése", expanded=False):
        st.markdown("".join(html_parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Multi-job állapotkezelés – PONTOSAN a többi modullal egyező CSS struktúra
# ---------------------------------------------------------------------------


def _is_job_complete(p: dict) -> bool:
    return bool(
        p.get("terepmunka", {}).get("active")
        and p.get("terepmunka", {}).get("tipus") is not None
    )


def _load_state(record_json: Optional[str]) -> dict:
    state: dict = {"jobs": [], "active_job": 0}
    if not record_json:
        state["jobs"] = [default_params()]
        return state
    try:
        loaded = json.loads(record_json)
        if isinstance(loaded, dict) and "jobs" in loaded:
            raw_jobs = loaded.get("jobs", [])
            state["active_job"] = int(loaded.get("active_job", 0))
        else:
            raw_jobs = [loaded]
        jobs = []
        for raw in raw_jobs:
            base = default_params()
            if isinstance(raw, dict):
                for sec in base:
                    if sec in raw:
                        if isinstance(base[sec], dict) and isinstance(raw[sec], dict):
                            base[sec].update(raw[sec])
                        else:
                            base[sec] = raw[sec]
            jobs.append(base)
        state["jobs"] = jobs if jobs else [default_params()]
        state["active_job"] = min(max(0, state["active_job"]), len(state["jobs"]) - 1)
    except Exception:
        state["jobs"] = [default_params()]
        state["active_job"] = 0
    return state


def _render_job_tabs(state: dict, state_key: str, is_editable: bool):
    jobs: list = state["jobs"]
    active: int = state["active_job"]
    n = len(jobs)
    complete_flags = [_is_job_complete(jobs[i]) for i in range(n)]

    css_rules = []
    for i, done in enumerate(complete_flags):
        is_active = i == active
        bg = "#198754" if is_active else "#d4edda"
        fg = "#ffffff" if is_active else "#155724"
        border = "#198754" if is_active else "#28a745"
        # Minden CSS szabály f-string, így a }} → } (egy záró kapcsos)
        css_rules.append(
            f".st-key-{state_key}_tab_{i} button {{"
            " min-height:1.7rem !important; height:1.7rem !important;"
            " min-width:6.2rem !important; width:6.2rem !important; max-width:6.2rem !important;"
            " padding:0.05rem 0.45rem !important; font-size:0.82rem !important;"
            f" font-weight:500 !important; line-height:1 !important; border-radius:0.3rem !important;"
            f" background-color:{bg} !important; color:{fg} !important; border-color:{border} !important;}}"
        )
    # Az ikon gombok CSS-e – szintén f-string, hogy }} → }
    css_rules.append(
        f".st-key-{state_key}_add_job button {{"
        " min-height:1.7rem !important; height:1.7rem !important;"
        " min-width:1.8rem !important; width:1.8rem !important; max-width:1.8rem !important;"
        " padding:0.1rem 0.3rem !important; font-size:1.05rem !important;"
        " line-height:1 !important; border-radius:0.3rem !important;}"
    )
    css_rules.append(
        f".st-key-{state_key}_del_job button {{"
        " min-height:1.7rem !important; height:1.7rem !important;"
        " min-width:1.8rem !important; width:1.8rem !important; max-width:1.8rem !important;"
        " padding:0.1rem 0.3rem !important; font-size:1.05rem !important;"
        " line-height:1 !important; border-radius:0.3rem !important;}"
    )
    if css_rules:
        st.markdown("<style>" + "".join(css_rules) + "</style>", unsafe_allow_html=True)

    if is_editable:
        ic1, ic2, _ = st.columns([0.28, 0.28, 12])
        if ic1.button("\u271a", key=f"{state_key}_add_job", help="Új munka hozzáadása"):
            state["jobs"].append(default_params())
            state["active_job"] = len(state["jobs"]) - 1
            st.rerun()
        if ic2.button(
            "\u2702",
            key=f"{state_key}_del_job",
            help=f"Munka {active + 1} törlése",
            disabled=n <= 1,
        ):
            state["jobs"].pop(active)
            state["active_job"] = max(0, active - 1)
            st.rerun()

    tab_cols = st.columns([1] * n + [12], vertical_alignment="center")
    for i in range(n):
        prefix = "\u2713 " if complete_flags[i] else ""
        if tab_cols[i].button(f"{prefix}Munka {i + 1}", key=f"{state_key}_tab_{i}"):
            state["active_job"] = i
            st.rerun()


# ---------------------------------------------------------------------------
# Fő render
# ---------------------------------------------------------------------------


def render_stage1_kalkulacio_desp(offer_id: int, is_editable: bool, db: Session):
    if not is_editable:
        st.info(
            "Ez a szakasz lezárult – a kalkuláció csak olvasható módban jelenik meg."
        )

    st.markdown("#### Kalkuláció – DESP / COCR / SUCL")
    st.caption(
        "Blokkokat kapcsold be (checkbox) és töltsd ki a paraméterekkel. "
        "A jobb oldali munkaóra-bontás folyamatosan újraszámolódik. "
        "⚠️ Az óraszámok még nem kerültek megadásra – a kalkuláció placeholder."
    )

    state_key = f"desp_kalk_{offer_id}"
    if state_key not in st.session_state:
        record = crud.get_stage1_kalk_desp(db, offer_id)
        st.session_state[state_key] = _load_state(
            record.params_json if record else None
        )

    state: dict = st.session_state[state_key]
    jobs: list = state["jobs"]

    _render_job_tabs(state, state_key, is_editable)

    active_idx: int = state.get("active_job", 0)
    if active_idx >= len(jobs):
        active_idx = 0
        state["active_job"] = 0
    p: dict = jobs[active_idx]
    job_key = f"{state_key}_j{active_idx}"

    left_col, right_col = st.columns([3, 2])

    with left_col:
        _render_kantar(p, is_editable, job_key)
        _render_szervezes(p, is_editable, job_key)
        _render_terepmunka(p, is_editable, job_key)
        _render_feldolgozas(p, is_editable, job_key)
        _render_plusz(p, is_editable, job_key)
        _render_egyeb(p, is_editable, job_key)

    with right_col:
        h_total = _new_hours()
        for job_p in jobs:
            h_job = calc_munkaora(job_p)
            for k in h_total:
                h_total[k] += h_job.get(k, 0.0)
        extra_rovid_any = any(
            bool(job_p.get("plusz_szolg", {}).get("active"))
            and int(job_p.get("plusz_szolg", {}).get("extra_rovid") or 1) == 2
            for job_p in jobs
        )
        _render_munkaora_panel(h_total, extra_rovid=extra_rovid_any)
        _render_param_summary_panel(p)

    if is_editable:
        st.divider()
        if st.button("Kalkuláció mentése", type="primary", key=f"{state_key}_save"):
            save_data = {"jobs": jobs, "active_job": active_idx}
            params_json = json.dumps(save_data, ensure_ascii=False)
            changed = crud.save_kalk_history(
                db,
                offer_id,
                "desp",
                params_json,
                saved_by_user_id=st.session_state.get("current_user_id"),
            )
            if changed:
                crud.upsert_stage1_kalk_desp(db, offer_id, params_json)
                st.toast("DESP kalkuláció mentve!")
                st.rerun()
            else:
                st.info("Nem történt változás a paraméterezésben – mentés kihagyva.")

    history = crud.get_kalk_history(db, offer_id, "desp")
    if history:
        with st.expander(f"📋 Kalkuláció-verziók ({len(history)} db)"):
            labels = [
                f"V{len(history) - i}  –  {hist.saved_at.strftime('%Y-%m-%d %H:%M')}  –  "
                f"{hist.saved_by.nev if hist.saved_by else '—'}"
                for i, hist in enumerate(history)
            ]
            selected_label = st.radio(
                "Betöltendő verzió:", labels, index=0, key=f"hist_radio_{offer_id}_desp"
            )
            if st.button(
                "⬆️ Kiválasztott verzió betöltése",
                key=f"hist_load_{offer_id}_desp",
                disabled=not is_editable,
                help="Betöltés után az aktuális paraméterek felülíródnak.",
            ):
                selected_idx = labels.index(selected_label)
                st.session_state[state_key] = _load_state(
                    history[selected_idx].params_json
                )
                st.toast(
                    "Korábbi verzió betöltve – ellenőrizd, majd ments, ha megtartod!"
                )
                st.rerun()
