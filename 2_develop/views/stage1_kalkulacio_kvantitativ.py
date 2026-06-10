"""
Szakasz 1 – Kalkuláció: Kvantitatív kutatás.

A Kvantitatív lap (1_documents/kvantitativ.xlsx) alapján képezzük le a
paramétereket és a hozzájuk tartozó munkaóra-képleteket.

Blokkok:
  1) Terepmunka – adatfelvételi módszertan (CATI / CAPI in-hall / CAPI in-home /
     CAPI helyszíni / CAWI), a Szervezés automatikusan számolódik
  2) Napló (kvalitatív képlettel)
  3) Megfigyelés (kvalitatív képlettel)
  4) DP
  5) Feldolgozás
  6) Analytics (Conjoint / KANO / Szegmentáció / Modellezés)
  7) Plusz szolgáltatások
  8) Egyéb

Munkaóra-kategóriák (10): a Kvalitatívhoz képest ÚJ az „Ellenőrzési" kategória.

Megjegyzések / nyitott pontok (későbbi specifikáció szerint módosulhat):
  - Ország: egyelőre csak Magyarország (ORSZAG_ALAP). A több ország eset
    később kerül specifikálásra; CATI / CAWI / nem-magyar CAPI esetén a
    Szervezés = 0.
  - „Emlékeztetők kiküldése" DP-órája a specifikációban még nincs meghatározva
    (xlsx K48 = ???); egyelőre 0, lásd EMLEKEZTETO_DP_ORA.
  - Napló / Megfigyelés: a kvalitatív kalkuláció képleteit vettük át.
  - Egyelőre csak munkaóra-számítás történik (alvállalkozói díj / egyéb költség /
    ajándék külön specifikáció szerint kerül később megvalósításra).
"""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st
from sqlalchemy.orm import Session

from db import crud

# ---------------------------------------------------------------------------
# Nyitott / későbbi specifikációra váró értékek
# ---------------------------------------------------------------------------

# Egyelőre csak Magyarország. Több ország eset később kerül specifikálásra.
ORSZAG_ALAP = "Magyarország"

# xlsx K48 „Emlékeztetők kiküldése" képlete a specifikációban még nincs
# meghatározva (???). Egyelőre 0 órát ad; ha definiálják, itt kell pótolni.
EMLEKEZTETO_DP_ORA = 0.0


# ---------------------------------------------------------------------------
# Konstansok – legördülő opciók (label-listák; index 1-től, hacsak nem 0-tól)
# ---------------------------------------------------------------------------

TEREP_TIPUSOK = [
    "1. CATI",
    "2. CAPI in-hall",
    "3. CAPI in-home",
    "4. CAPI helyszíni",
    "5. CAWI",
    "6. Napló",
    "7. Megfigyelés",
]

MEGKERDEZETT_KOR = [
    "1. lakosság",
    "2. vállalati",
    "3. orvos",
    "4. szakértő",
]

INCIDENCE_RATE = [
    "1. 5% alatt",
    "2. 5-9%",
    "3. 10-19%",
    "4. 20-39%",
    "5. 40-59%",
    "6. 60+ %",
]

KONTAKTLISTA = [
    "1. nincs kontaktlista",
    "2. Kantar Hoffmann készíti",
    "3. ügyfél adja",
    "4. panel",
]

MINTAVETEL_KOMPLEXITAS = [
    "1. egyszerű (pl. véletlen)",
    "2. átlagos (könnyű kvóta)",
    "3. nehéz",
    "4. extrém",
]

KERDOIV_HOSSZ = [
    "1. 5-10 perc",
    "2. 11-15 perc",
    "3. 16-20 perc",
    "4. 21-25 perc",
    "5. 26-30 perc",
    "6. 31-35 perc",
    "7. 36-40 perc",
    "8. 41-45 perc",
    "9. 46-50 perc",
    "10. 51-55 perc",
    "11. 56-60 perc",
]

NAPI_IDO_OPTIONS = [
    ("1. 15 perc", 15),
    ("2. 30 perc", 30),
    ("3. 45 perc", 45),
    ("4. 60 perc", 60),
]

# 0/1/2 típusú legördülők (index 0-tól)
PROGRAMOZAS_OPTIONS = ["0. Nem", "1. Házon kívül", "2. Házon belül"]
KVOTAFELUGYELET_OPTIONS = ["0. Nem", "1. Házon kívül", "2. Házon belül"]
EMLEKEZTETO_OPTIONS = ["0. Nem", "1. Házon kívül", "2. Házon belül"]
ADATBAZIS_KESZ_OPTIONS = ["0. Nem", "1. Házon kívül", "2. Házon belül"]

FORDITAS_OPTIONS = [
    "0. nincs",
    "1. fordítóval",
    "2. fordítóval, lektorálva",
    "3. szoftverrel",
]
EXTRA_ROVID_OPTIONS = ["1. normál", "2. extra rövid (1,2× szorzó)"]
NEM_IGEN = ["0. Nem", "1. Igen"]
NINCS_VAN = ["0. Nincs", "1. Van"]


# A munkaóra-kategóriák kulcsa → megjelenítendő név (10 kategória).
# A Kvalitatívhoz képest ÚJ: "ellenorzesi" (Ellenőrzési).
MUNKAORA_CATS = [
    ("szervezoi", "Szervezői"),
    ("ellenorzesi", "Ellenőrzési"),
    ("szervezesi_vez", "Szervezési vezetői"),
    ("dp", "DP"),
    ("dp_vez", "DP vezetői"),
    ("junior_kut", "Junior kutatói"),
    ("executive_kut", "Executive kutatói"),
    ("szenior_kut", "Szenior kutatói"),
    ("kut_ig", "Kutatási igazgatói"),
    ("gad", "GAD"),
]

# Analytics lookup (xlsx 96-99. sor + a 67/69/71/73. sorok képletei beépítve).
# Kulcs → végső munkaóra-bontás kategóriánként.
ANALYTICS_LOOKUP = {
    "conjoint": {"dp": 30, "szenior_kut": 15, "kut_ig": 2, "gad": 1},
    "kano": {"dp": 3, "szenior_kut": 3, "kut_ig": 0.5, "gad": 0.5},
    "szegmentacio": {"dp": 20, "szenior_kut": 15, "kut_ig": 2, "gad": 1},
    "modellezes": {"dp": 20, "szenior_kut": 15, "kut_ig": 2, "gad": 1},
}


# ---------------------------------------------------------------------------
# Alapértelmezett paraméter-struktúra
# ---------------------------------------------------------------------------


def default_params() -> dict:
    return {
        "orszag": ORSZAG_ALAP,  # egyelőre fix; több ország eset később
        "terepmunka": {
            "active": False,
            "tipus": None,  # 1..5 (None = nincs kiválasztva)
            "megkerdezett_kor": 1,
            "incidence_rate": 1,
            "kontaktlista": 1,
            "mintanagysag": 0,
            "mintavetel_komplexitas": 1,
            "kvotaszempontok": 0,
            "kerdoiv_hossz": 1,
            "fieldnapok": 0,
            "budapest_pct": 0,
            "videk_pct": 0,
            # Napló
            "naplo_napok": 0,
            "naplo_resztvevok": 0,
            "naplo_napi_ido_idx": 1,
            # Megfigyelés
            "mf_helyszinek": 0,
            "mf_oraszam": 0.0,
            "mf_budapest_pct": 0,
            "mf_videk_pct": 0,
        },
        "dp": {
            "ugyfel_adatbazis": 0,
            "programozas": 0,
            "hosting": 0,
            "kvotafelugyelet": 0,
            "emlekezteto": 0,
            "statuszriport": 0,
            "adatbazis_keszites": 0,
        },
        "feldolgozas": {
            "adatbazis": 0,
            "top_line": 0,
            "egyszeru_elemzes": 0,
            "melyelemzes": 0,
            "management_summary": 0,
            "prezentacio": 0,
            "segident": 0,
            "conjoint_tool": 0,
            "score_card": 0,
            "dashboard": 0,
            "workshop_ora": 0.0,
        },
        "analytics": {
            "conjoint": 0,
            "kano": 0,
            "szegmentacio": 0,
            "modellezes": 0,
        },
        "plusz_szolg": {
            "forditas": 0,
            "szinkrontolmacs_ora": 0.0,
            "terembarles": 0,
            "catering": 0,
            "extra_rovid": 1,
            "trening": 0,
        },
        "egyeb": {
            "munkaora": 0.0,
            "koltseg": 0.0,
            "megjegyzes": "",
        },
    }


# ---------------------------------------------------------------------------
# Kalkulációs logika
# ---------------------------------------------------------------------------


def _new_hours() -> dict:
    return {k: 0.0 for k, _ in MUNKAORA_CATS}


def _add(h: dict, key: str, val: float):
    h[key] = h.get(key, 0.0) + val


# ---------------------------------------------------------------------------
# Szorzótáblák (PLACEHOLDER – finomhangolásra vár)
# ---------------------------------------------------------------------------

# Incidence Rate szorzó (CAPI in-hall / helyszíni; IR sávok 1-6).
# Minél alacsonyabb az IR, annál több szervezési ráfordítás → nagyobb szorzó.
# Finomhangolás szükséges.
_IR_SZORZO = {1: 2.0, 2: 1.8, 3: 1.6, 4: 1.4, 5: 1.2, 6: 1.0}

# Kontaktlista szorzó (CAPI in-hall / helyszíni).
# 1=nincs lista (legdrágább), 4=panel (legolcsóbb). PLACEHOLDER.
_KONTAKT_SZORZO = {1: 1.2, 2: 1.0, 3: 0.9, 4: 0.8}


def _szervezesi_szorzo(terep: dict) -> float:
    """A magyarországi CAPI in-hall / helyszíni Szervezői óraszorzó.

    Szorzó = Megkérdezettek köre × Mintanagyság × Mintavétel komplexitás
             × Incidence Rate × Kontaktlista.
    (Utóbbi kettő PLACEHOLDER – finomhangolásra vár.)
    """
    kor = int(terep.get("megkerdezett_kor") or 1)
    minta = float(terep.get("mintanagysag") or 0)
    kompl = int(terep.get("mintavetel_komplexitas") or 1)
    ir = int(terep.get("incidence_rate") or 6)  # alapért. legkedvezőbb sáv
    kontakt = int(terep.get("kontaktlista") or 2)  # alapért. Kantar készíti
    sz_kor = 1.3 if kor in (2, 3, 4) else 1.0
    sz_minta = 1.1 if minta > 1000 else 1.0
    sz_kompl = 1.1 if kompl in (2, 3, 4) else 1.0
    sz_ir = _IR_SZORZO.get(ir, 1.0)
    sz_kontakt = _KONTAKT_SZORZO.get(kontakt, 1.0)
    return sz_kor * sz_minta * sz_kompl * sz_ir * sz_kontakt


def calc_munkaora(p: dict) -> dict:
    """Az egyes blokkok munkaóra-bontásának kiszámolása az xlsx alapján."""
    h = _new_hours()

    terep = p.get("terepmunka", {})
    terep_active = bool(terep.get("active"))
    t_tipus = int(terep.get("tipus") or 0) if terep_active else 0
    is_cawi = t_tipus == 5
    minta = float(terep.get("mintanagysag") or 0)
    kvota = float(terep.get("kvotaszempontok") or 0)
    sav = int(terep.get("kerdoiv_hossz") or 1)
    sav_inc = sav - 1  # kérdőívhossz-sávonkénti növekmény (a legrövidebb = 0)
    fieldnap = float(terep.get("fieldnapok") or 0)

    # Magyarországon vagyunk-e (egyelőre mindig igen; később több ország)
    is_hu = (p.get("orszag") or ORSZAG_ALAP) == "Magyarország"

    # ------------------------------------------------------------------
    # 1) Terepmunka – Szervezés (csak Magyarország + CAPI in-hall/in-home/helyszíni)
    # ------------------------------------------------------------------
    if terep_active and is_hu and t_tipus in (2, 3, 4):
        if t_tipus == 2:  # CAPI in-hall
            szorzo = _szervezesi_szorzo(terep)
            _add(h, "szervezoi", 7 + 10 * szorzo)
            _add(h, "ellenorzesi", 10 * fieldnap)
            _add(h, "szervezesi_vez", 1)
        elif t_tipus == 3:  # CAPI in-home
            _add(h, "szervezoi", 10 + (minta / 100.0 * 0.5))
            _add(h, "ellenorzesi", minta / 20.0)
            _add(h, "szervezesi_vez", 2)
        elif t_tipus == 4:  # CAPI helyszíni
            szorzo = _szervezesi_szorzo(terep)
            _add(h, "szervezoi", 7 + 10 * szorzo)
            _add(h, "ellenorzesi", 10 * fieldnap)
            _add(h, "szervezesi_vez", 1)

    # Kérdőív hossza → Szervezői: 6 + sávonként +2 óra (csak CAPI, CATI/CAWI-t
    # az alvállalkozó áraz, ott nem szervezünk)
    if terep_active and t_tipus in (2, 3, 4):
        _add(h, "szervezoi", 6 + sav_inc * 2)

    # ------------------------------------------------------------------
    # 2) Napló (kvalitatív képlet) – csak ha a módszertan = 6. Napló
    # ------------------------------------------------------------------
    if terep_active and t_tipus == 6:
        naplo_napok = float(terep.get("naplo_napok") or 0)
        naplo_reszt = float(terep.get("naplo_resztvevok") or 0)
        if naplo_napok > 0 and naplo_reszt > 0:
            _add(h, "szervezesi_vez", 1)
            _add(h, "executive_kut", 2 + (1 + naplo_reszt / 100.0) * 2 * naplo_napok)
            _add(h, "gad", 2)
            _add(h, "szervezoi", naplo_reszt * 0.8 + 3)

    # ------------------------------------------------------------------
    # 3) Megfigyelés (kvalitatív képlet) – csak ha a módszertan = 7. Megfigyelés
    # ------------------------------------------------------------------
    if terep_active and t_tipus == 7:
        mf_ora = float(terep.get("mf_oraszam") or 0)
        mf_bp = float(terep.get("mf_budapest_pct") or 0) / 100.0
        mf_vd = float(terep.get("mf_videk_pct") or 0) / 100.0
        if mf_ora > 0:
            _add(h, "szervezesi_vez", 1)
            _add(h, "gad", 1)
            if mf_bp > 0:
                _add(h, "executive_kut", (3 + mf_ora * 1.2 + 1) * mf_bp)
            if mf_vd > 0:
                _add(h, "executive_kut", (3 + mf_ora * 1.2 + 4) * mf_vd)

    # ------------------------------------------------------------------
    # 4) DP
    # ------------------------------------------------------------------
    dp = p.get("dp", {})
    a = p.get("analytics", {})
    conjoint_on = int(a.get("conjoint") or 0) == 1
    szegm_on = int(a.get("szegmentacio") or 0) == 1

    # Ügyfél adatbázisának kezelése (K40 = 3)
    if int(dp.get("ugyfel_adatbazis") or 0) == 1:
        _add(h, "dp", 3)

    # Programozás (házon belül = 2)
    prog = int(dp.get("programozas") or 0)
    if prog == 2:
        if conjoint_on or szegm_on:
            _add(h, "dp", 6 + sav_inc * 2 + 5)  # K43
            _add(h, "szenior_kut", 2)  # O43
        else:
            _add(h, "dp", 6 + sav_inc * 2)  # K42
        _add(h, "dp_vez", 1)  # L42
        _add(h, "junior_kut", sav_inc * 1)  # M42
        _add(h, "szervezoi", sav_inc * 1)  # H42

    # Hosting (csak CAWI)
    if is_cawi and int(dp.get("hosting") or 0) == 1:
        _add(h, "dp_vez", 1)  # L45
        _add(h, "executive_kut", 2)  # N45

    # Kvótafelügyelet (csak CAWI; házon belül = 2)
    if is_cawi and int(dp.get("kvotafelugyelet") or 0) == 2:
        _add(h, "dp", minta / 200.0 * (1 + kvota / 10.0))  # K47

    # Emlékeztetők kiküldése (csak CAWI; képlet még nincs definiálva → 0)
    if is_cawi and int(dp.get("emlekezteto") or 0) in (1, 2):
        _add(h, "dp", EMLEKEZTETO_DP_ORA)  # K48 = ??? (nyitott)

    # Rendszeres jelentés (státuszriport): K49 = jelentések száma
    statusz = float(dp.get("statuszriport") or 0)
    if statusz > 0:
        _add(h, "dp", statusz)

    # Adatbázis-készítés
    adk = int(dp.get("adatbazis_keszites") or 0)
    if adk == 1:  # házon kívül
        _add(h, "dp", (1 + kvota / 10.0) * 3)  # K51
    elif adk == 2:  # házon belül
        _add(
            h,
            "dp",
            sav_inc * 0.5
            + 0.005 * minta
            + 4
            + minta / 100.0 * 4 * sav_inc
            + 0.1 * (1 + kvota / 10.0),
        )  # K52
        _add(h, "dp_vez", 1)  # L52
        _add(h, "executive_kut", 1)  # N52

    # ------------------------------------------------------------------
    # 5) Feldolgozás
    # ------------------------------------------------------------------
    f = p.get("feldolgozas", {})
    feld_keys = (
        "adatbazis",
        "top_line",
        "egyszeru_elemzes",
        "melyelemzes",
        "management_summary",
        "prezentacio",
        "segident",
        "conjoint_tool",
        "score_card",
        "dashboard",
        "workshop_ora",
    )
    feld_active = any((f.get(k) or 0) > 0 for k in feld_keys)
    if feld_active:
        # Feldolgozási alap (xlsx 93-95. sor: alap + sáv-/mintanövekmény)
        base_inc = sav_inc * 1 + (minta / 200.0) * 0.5
        _add(h, "dp", 6 + base_inc)  # K93
        _add(h, "dp_vez", 1)  # L93
        _add(h, "executive_kut", 8 + base_inc)  # N93
        _add(h, "szenior_kut", 0.5)  # O93
        _add(h, "kut_ig", 0.5)  # P93

        # Adatbázis (és syntax): K=2, N=2
        n = float(f.get("adatbazis") or 0)
        if n > 0:
            _add(h, "dp", n * 2)
            _add(h, "executive_kut", n * 2)

        # Top-line / Táblariport: K=2, N=4, Q=1
        n = float(f.get("top_line") or 0)
        if n > 0:
            _add(h, "dp", n * 2)
            _add(h, "executive_kut", n * 4)
            _add(h, "gad", n * 1)

        # Egyszerű elemzés: K=4, M=10, N=8, P=0.5, Q=2
        n = float(f.get("egyszeru_elemzes") or 0)
        if n > 0:
            _add(h, "dp", n * 4)
            _add(h, "junior_kut", n * 10)
            _add(h, "executive_kut", n * 8)
            _add(h, "kut_ig", n * 0.5)
            _add(h, "gad", n * 2)

        # Mélyelemzés (deepdive): képletes
        mely_inc = sav_inc * 1 + (minta / 200.0) * 0.5
        n = float(f.get("melyelemzes") or 0)
        if n > 0:
            _add(h, "dp", n * (8 + mely_inc))  # K58
            _add(h, "junior_kut", n * (20 + mely_inc))  # M58
            _add(h, "executive_kut", n * (8 + mely_inc))  # N58
            _add(h, "szenior_kut", n * (8 + mely_inc))  # O58
            _add(h, "kut_ig", n * 1)  # P58
            _add(h, "gad", n * 4)  # Q58

        # Management summary: O=5, P=2, Q=2 (önállóan nem rendelhető)
        n = float(f.get("management_summary") or 0)
        if n > 0:
            _add(h, "szenior_kut", n * 5)
            _add(h, "kut_ig", n * 2)
            _add(h, "gad", n * 2)

        # Prezentáció: O=2, Q=2 (önállóan nem rendelhető)
        n = float(f.get("prezentacio") or 0)
        if n > 0:
            _add(h, "szenior_kut", n * 2)
            _add(h, "gad", n * 2)

        # Segident / modellezés: K=8, O=1 (csak Modellezés=1)
        n = float(f.get("segident") or 0)
        if n > 0:
            _add(h, "dp", n * 8)
            _add(h, "szenior_kut", n * 1)

        # Conjoint Excel Tool: K=5, O=1 (csak Conjoint=1)
        n = float(f.get("conjoint_tool") or 0)
        if n > 0:
            _add(h, "dp", n * 5)
            _add(h, "szenior_kut", n * 1)

        # Score card: K=4+növekmény, N=1+növekmény
        n = float(f.get("score_card") or 0)
        if n > 0:
            sc_inc = sav_inc * 1 + (minta / 200.0) * 0.5
            _add(h, "dp", n * (4 + sc_inc))  # K63
            _add(h, "executive_kut", n * (1 + sc_inc))  # N63

        # Dashboard (házon kívül): nincs belső munkaóra

        # Workshop: O=2+óra, P=2+óra, Q=2+óra
        ws = float(f.get("workshop_ora") or 0)
        if ws > 0:
            _add(h, "szenior_kut", 2 + ws)  # O65
            _add(h, "kut_ig", 2 + ws)  # P65
            _add(h, "gad", 2 + ws)  # Q65

    # ------------------------------------------------------------------
    # 6) Analytics
    # ------------------------------------------------------------------
    for key in ("conjoint", "kano", "szegmentacio", "modellezes"):
        if int(a.get(key) or 0) == 1:
            for cat, v in ANALYTICS_LOOKUP[key].items():
                _add(h, cat, v)

    # ------------------------------------------------------------------
    # 7) Plusz szolgáltatások – Extra rövid határidő (×1,2 minden belső órára)
    # ------------------------------------------------------------------
    ps = p.get("plusz_szolg", {})
    if int(ps.get("extra_rovid") or 1) == 2:
        for k in h:
            h[k] = h[k] * 1.2

    # ------------------------------------------------------------------
    # 8) Egyéb extra munkaóra (Szervezőire adódik, a szorzó után)
    # ------------------------------------------------------------------
    eg = p.get("egyeb", {})
    extra = float(eg.get("munkaora") or 0)
    if extra > 0:
        _add(h, "szervezoi", extra)

    return h


def _validate_feldolgozas(p: dict) -> list[str]:
    """Feldolgozás-függőségek ellenőrzése.

    - Management summary / Prezentáció önállóan nem rendelhetők meg.
    - Segident / modellezés csak Modellezés=1 mellett.
    - Conjoint Excel Tool csak Conjoint=1 mellett.
    """
    errs = []
    f = p.get("feldolgozas", {})
    a = p.get("analytics", {})

    deps = {"management_summary": "Management summary", "prezentacio": "Prezentáció"}
    sibling_keys = (
        "adatbazis",
        "top_line",
        "egyszeru_elemzes",
        "melyelemzes",
        "segident",
        "conjoint_tool",
        "score_card",
        "dashboard",
        "workshop_ora",
    )
    for k, name in deps.items():
        if (f.get(k) or 0) > 0:
            has_sibling = any((f.get(s) or 0) > 0 for s in sibling_keys)
            other_dep = [
                v for kk, v in deps.items() if kk != k and (f.get(kk) or 0) > 0
            ]
            if not has_sibling and not other_dep:
                errs.append(f"{name} (önállóan nem rendelhető)")

    if (f.get("segident") or 0) > 0 and int(a.get("modellezes") or 0) != 1:
        errs.append("Segident / modellezés (csak Modellezés=1 esetén)")
    if (f.get("conjoint_tool") or 0) > 0 and int(a.get("conjoint") or 0) != 1:
        errs.append("Conjoint Excel Tool (csak Conjoint=1 esetén)")
    return errs


# ---------------------------------------------------------------------------
# UI – Bal oldali paraméter-blokkok renderelése
# ---------------------------------------------------------------------------


def _render_terepmunka(p: dict, is_editable: bool, key_prefix: str):
    t = p["terepmunka"]
    with st.expander("1) Terepmunka", expanded=False):
        t["active"] = st.checkbox(
            "Van terepmunka",
            value=bool(t.get("active")),
            key=f"{key_prefix}_terep_active",
            disabled=not is_editable,
        )
        if not t["active"]:
            return

        saved_tipus = t.get("tipus")
        _tipus_idx = (int(saved_tipus) - 1) if saved_tipus is not None else None
        _tipus_label = st.selectbox(
            "Adatfelvételi módszertan",
            TEREP_TIPUSOK,
            index=_tipus_idx,
            placeholder="Válassz módszertant…",
            key=f"{key_prefix}_terep_tipus",
            disabled=not is_editable,
        )
        t["tipus"] = int(_tipus_label.split(".")[0]) if _tipus_label else None
        tipus = t["tipus"]
        if tipus is None:
            return

        # ── 1-5: CATI / CAPI / CAWI kérdőíves terepmunka ──────────────────
        if tipus in (1, 2, 3, 4, 5):
            t["megkerdezett_kor"] = int(
                st.selectbox(
                    "Megkérdezettek köre",
                    MEGKERDEZETT_KOR,
                    index=int(t.get("megkerdezett_kor") or 1) - 1,
                    key=f"{key_prefix}_terep_kor",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["incidence_rate"] = int(
                st.selectbox(
                    "Incidence Rate",
                    INCIDENCE_RATE,
                    index=int(t.get("incidence_rate") or 1) - 1,
                    key=f"{key_prefix}_terep_ir",
                    disabled=not is_editable,
                    help="Egyelőre csak az alvállalkozói díjat befolyásolja (későbbi spec).",
                ).split(".")[0]
            )
            t["kontaktlista"] = int(
                st.selectbox(
                    "Kontaktlista",
                    KONTAKTLISTA,
                    index=int(t.get("kontaktlista") or 1) - 1,
                    key=f"{key_prefix}_terep_kontakt",
                    disabled=not is_editable,
                    help="Egyelőre csak az alvállalkozói díjat befolyásolja (későbbi spec).",
                ).split(".")[0]
            )
            t["mintanagysag"] = st.number_input(
                "Mintanagyság (fő / látogatás)",
                min_value=0,
                step=10,
                value=int(t.get("mintanagysag") or 0),
                key=f"{key_prefix}_terep_minta",
                disabled=not is_editable,
            )
            t["mintavetel_komplexitas"] = int(
                st.selectbox(
                    "Mintavétel komplexitás",
                    MINTAVETEL_KOMPLEXITAS,
                    index=int(t.get("mintavetel_komplexitas") or 1) - 1,
                    key=f"{key_prefix}_terep_kompl",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            t["kvotaszempontok"] = st.number_input(
                "Kvótaszempontok száma (0–9)",
                min_value=0,
                max_value=9,
                step=1,
                value=int(t.get("kvotaszempontok") or 0),
                key=f"{key_prefix}_terep_kvota",
                disabled=not is_editable,
            )
            t["kerdoiv_hossz"] = int(
                st.selectbox(
                    "Kérdőív hossza",
                    KERDOIV_HOSSZ,
                    index=int(t.get("kerdoiv_hossz") or 1) - 1,
                    key=f"{key_prefix}_terep_hossz",
                    disabled=not is_editable,
                ).split(".")[0]
            )

            # Fieldnapok: csak CAPI in-hall (2) vagy helyszíni (4), Magyarországon
            if tipus in (2, 4):
                t["fieldnapok"] = st.number_input(
                    "Fieldnapok száma",
                    min_value=0,
                    step=1,
                    value=int(t.get("fieldnapok") or 0),
                    key=f"{key_prefix}_terep_fieldnap",
                    disabled=not is_editable,
                )

            # Megkérdezés helye (BP/Vidék %): csak CAPI helyszíni (4)
            if tipus == 4:
                col1, col2 = st.columns(2)
                t["budapest_pct"] = col1.number_input(
                    "Budapest aránya (%)",
                    min_value=0,
                    max_value=100,
                    step=5,
                    value=int(t.get("budapest_pct") or 0),
                    key=f"{key_prefix}_terep_bp",
                    disabled=not is_editable,
                )
                t["videk_pct"] = col2.number_input(
                    "Vidék aránya (%)",
                    min_value=0,
                    max_value=100,
                    step=5,
                    value=int(t.get("videk_pct") or 0),
                    key=f"{key_prefix}_terep_vd",
                    disabled=not is_editable,
                )
                if t["budapest_pct"] + t["videk_pct"] not in (0, 100):
                    st.warning("Budapest + Vidék % összege 100 kell legyen.")

        # ── 6: Napló (kvalitatív képlet) ──────────────────────────────────
        elif tipus == 6:
            t["naplo_napok"] = st.number_input(
                "Napok száma",
                min_value=0,
                step=1,
                value=int(t.get("naplo_napok") or 0),
                key=f"{key_prefix}_naplo_napok",
                disabled=not is_editable,
            )
            t["naplo_resztvevok"] = st.number_input(
                "Résztvevők száma",
                min_value=0,
                step=1,
                value=int(t.get("naplo_resztvevok") or 0),
                key=f"{key_prefix}_naplo_reszt",
                disabled=not is_editable,
            )
            t["naplo_napi_ido_idx"] = int(
                st.selectbox(
                    "Napi időráfordítás",
                    [opt for opt, _ in NAPI_IDO_OPTIONS],
                    index=int(t.get("naplo_napi_ido_idx") or 1) - 1,
                    key=f"{key_prefix}_naplo_napi_ido",
                    disabled=not is_editable,
                ).split(".")[0]
            )

        # ── 7: Megfigyelés (kvalitatív képlet) ────────────────────────────
        elif tipus == 7:
            t["mf_helyszinek"] = st.number_input(
                "Helyszínek száma",
                min_value=0,
                step=1,
                value=int(t.get("mf_helyszinek") or 0),
                key=f"{key_prefix}_mf_helyszinek",
                disabled=not is_editable,
            )
            t["mf_oraszam"] = st.number_input(
                "Megfigyelési munkaórák száma",
                min_value=0.0,
                step=0.5,
                value=float(t.get("mf_oraszam") or 0),
                key=f"{key_prefix}_mf_ora",
                disabled=not is_editable,
            )
            col1, col2 = st.columns(2)
            t["mf_budapest_pct"] = col1.number_input(
                "Budapest aránya (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(t.get("mf_budapest_pct") or 0),
                key=f"{key_prefix}_mf_bp",
                disabled=not is_editable,
            )
            t["mf_videk_pct"] = col2.number_input(
                "Vidék aránya (%)",
                min_value=0,
                max_value=100,
                step=5,
                value=int(t.get("mf_videk_pct") or 0),
                key=f"{key_prefix}_mf_vd",
                disabled=not is_editable,
            )
            if t["mf_oraszam"] > 0 and t["mf_budapest_pct"] + t["mf_videk_pct"] not in (
                0,
                100,
            ):
                st.warning("Budapest + Vidék % összege 100 kell legyen.")


def _render_dp(p: dict, is_editable: bool, key_prefix: str):
    dp = p["dp"]
    t = p.get("terepmunka", {})
    is_cawi = bool(t.get("active")) and int(t.get("tipus") or 0) == 5
    with st.expander("2) DP", expanded=False):
        dp["ugyfel_adatbazis"] = int(
            st.selectbox(
                "Ügyfél adatbázisának kezelése",
                NEM_IGEN,
                index=int(dp.get("ugyfel_adatbazis") or 0),
                key=f"{key_prefix}_dp_ugyfel",
                disabled=not is_editable,
            ).split(".")[0]
        )
        dp["programozas"] = int(
            st.selectbox(
                "Programozás",
                PROGRAMOZAS_OPTIONS,
                index=int(dp.get("programozas") or 0),
                key=f"{key_prefix}_dp_prog",
                disabled=not is_editable,
            ).split(".")[0]
        )
        if is_cawi:
            dp["hosting"] = int(
                st.selectbox(
                    "Hosting",
                    NEM_IGEN,
                    index=int(dp.get("hosting") or 0),
                    key=f"{key_prefix}_dp_hosting",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            dp["kvotafelugyelet"] = int(
                st.selectbox(
                    "Kvótafelügyelet",
                    KVOTAFELUGYELET_OPTIONS,
                    index=int(dp.get("kvotafelugyelet") or 0),
                    key=f"{key_prefix}_dp_kvota",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            dp["emlekezteto"] = int(
                st.selectbox(
                    "Emlékeztetők kiküldése",
                    EMLEKEZTETO_OPTIONS,
                    index=int(dp.get("emlekezteto") or 0),
                    key=f"{key_prefix}_dp_emlek",
                    disabled=not is_editable,
                    help="A munkaóra-képlet még nincs meghatározva (egyelőre 0 óra).",
                ).split(".")[0]
            )
        else:
            st.caption("Hosting / Kvótafelügyelet / Emlékeztetők csak CAWI esetén.")
        dp["statuszriport"] = st.number_input(
            "Rendszeres jelentés (státuszriport) – db",
            min_value=0,
            step=1,
            value=int(dp.get("statuszriport") or 0),
            key=f"{key_prefix}_dp_statusz",
            disabled=not is_editable,
        )
        dp["adatbazis_keszites"] = int(
            st.selectbox(
                "Adatbázis-készítés (kódolás, labelezés, tisztítás, súlyozás)",
                ADATBAZIS_KESZ_OPTIONS,
                index=int(dp.get("adatbazis_keszites") or 0),
                key=f"{key_prefix}_dp_adatbazis",
                disabled=not is_editable,
            ).split(".")[0]
        )


def _render_feldolgozas(p: dict, is_editable: bool, key_prefix: str):
    f = p["feldolgozas"]
    with st.expander("3) Feldolgozás", expanded=False):
        st.caption(
            "Minden tétel alapértéke 0; írd felül a darabszámokkal. "
            "A „Feldolgozási alap” automatikusan számolódik, ha bármelyik > 0."
        )
        int_params = [
            ("adatbazis", "Adatbázis (és syntax) (db)"),
            ("top_line", "Top-line / Táblariport (db)"),
            ("egyszeru_elemzes", "Egyszerű elemzés (db)"),
            ("melyelemzes", "Mélyelemzés / deepdive (db)"),
            ("management_summary", "Management summary (db) – önállóan nem rendelhető"),
            ("prezentacio", "Prezentáció (db) – önállóan nem rendelhető"),
            ("segident", "Segident / modellezés (db) – csak Modellezés=1"),
            ("conjoint_tool", "Conjoint Excel Tool (db) – csak Conjoint=1"),
            ("score_card", "Score card (db)"),
            ("dashboard", "Dashboard (házon kívül) (db)"),
        ]
        for key, label in int_params:
            f[key] = st.number_input(
                label,
                min_value=0,
                step=1,
                value=int(f.get(key) or 0),
                key=f"{key_prefix}_f_{key}",
                disabled=not is_editable,
            )
        f["workshop_ora"] = st.number_input(
            "Workshop hossza (óra)",
            min_value=0.0,
            step=0.5,
            value=float(f.get("workshop_ora") or 0),
            key=f"{key_prefix}_f_workshop",
            disabled=not is_editable,
        )

        errs = _validate_feldolgozas(p)
        if errs:
            st.error("Figyelem: " + "; ".join(errs))


def _render_analytics(p: dict, is_editable: bool, key_prefix: str):
    a = p["analytics"]
    with st.expander("4) Analytics", expanded=False):
        for key, label in (
            ("conjoint", "Conjoint"),
            ("kano", "KANO-modell"),
            ("szegmentacio", "Szegmentáció"),
            ("modellezes", "Modellezés"),
        ):
            a[key] = int(
                st.selectbox(
                    label,
                    NINCS_VAN,
                    index=int(a.get(key) or 0),
                    key=f"{key_prefix}_an_{key}",
                    disabled=not is_editable,
                ).split(".")[0]
            )


def _render_plusz_szolg(p: dict, is_editable: bool, key_prefix: str):
    ps = p["plusz_szolg"]
    with st.expander("5) Plusz szolgáltatások", expanded=False):
        ps["forditas"] = int(
            st.selectbox(
                "Fordítás",
                FORDITAS_OPTIONS,
                index=int(ps.get("forditas") or 0),
                key=f"{key_prefix}_ps_ford",
                disabled=not is_editable,
            ).split(".")[0]
        )
        ps["szinkrontolmacs_ora"] = st.number_input(
            "Szinkrontolmács (óra)",
            min_value=0.0,
            step=0.5,
            value=float(ps.get("szinkrontolmacs_ora") or 0),
            key=f"{key_prefix}_ps_tolmacs",
            disabled=not is_editable,
        )
        col1, col2 = st.columns(2)
        ps["terembarles"] = int(
            col1.selectbox(
                "Terembérlés",
                NEM_IGEN,
                index=int(ps.get("terembarles") or 0),
                key=f"{key_prefix}_ps_terem",
                disabled=not is_editable,
            ).split(".")[0]
        )
        ps["catering"] = int(
            col2.selectbox(
                "Catering (meleg étel)",
                NEM_IGEN,
                index=int(ps.get("catering") or 0),
                key=f"{key_prefix}_ps_cat",
                disabled=not is_editable,
            ).split(".")[0]
        )
        ps["extra_rovid"] = int(
            st.selectbox(
                "Határidő",
                EXTRA_ROVID_OPTIONS,
                index=int(ps.get("extra_rovid") or 1) - 1,
                key=f"{key_prefix}_ps_extra",
                disabled=not is_editable,
                help="„Extra rövid” esetén minden belső munkaóra 1,2× szorzót kap.",
            ).split(".")[0]
        )
        ps["trening"] = int(
            st.selectbox(
                "Tréning",
                NEM_IGEN,
                index=int(ps.get("trening") or 0),
                key=f"{key_prefix}_ps_tren",
                disabled=not is_editable,
            ).split(".")[0]
        )


def _render_egyeb(p: dict, is_editable: bool, key_prefix: str):
    e = p["egyeb"]
    with st.expander("6) Egyéb", expanded=False):
        e["munkaora"] = st.number_input(
            "Egyéb munkaóra (Szervezői sorra adódik)",
            min_value=0.0,
            step=0.5,
            value=float(e.get("munkaora") or 0),
            key=f"{key_prefix}_e_ora",
            disabled=not is_editable,
        )
        e["koltseg"] = st.number_input(
            "Egyéb költség (Ft)",
            min_value=0.0,
            step=1000.0,
            value=float(e.get("koltseg") or 0),
            key=f"{key_prefix}_e_koltseg",
            disabled=not is_editable,
        )
        e["megjegyzes"] = st.text_area(
            "Megjegyzés",
            value=e.get("megjegyzes") or "",
            key=f"{key_prefix}_e_meg",
            disabled=not is_editable,
        )


# ---------------------------------------------------------------------------
# Jobb oldali panelek (munkaóra-összegzés, paraméter-összegzés)
# ---------------------------------------------------------------------------


def _render_munkaora_panel(h: dict, extra_rovid: bool):
    badge_extra = (
        " &nbsp; <span style='background:#fff3bf; color:#7a5a00; padding:2px 8px; "
        "border-radius:4px; font-size:0.75rem; font-weight:600;'>×1,2 extra rövid</span>"
        if extra_rovid
        else ""
    )

    panel_html = [
        "<div style='border:1px solid #d6dde8; border-radius:8px; padding:1rem; "
        "background:#f7f9fc;'>",
        "<div style='font-size:0.85rem; color:#0b3d91; font-weight:600; "
        "letter-spacing:0.04em; text-transform:uppercase; margin-bottom:0.25rem;'>"
        "Számolt munkaóra</div>",
        f"<div style='font-size:0.8rem; color:#5a6b80; margin-bottom:1rem;'>"
        f"Kvantitatív kutatás{badge_extra}</div>",
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
            f"<div style='background:{bg}; border:1px solid #e3e8f0; "
            "border-radius:6px; padding:0.6rem 0.7rem;'>"
            f"<div style='font-size:0.72rem; color:{lbl_col}; line-height:1.2; "
            f"min-height:2.4em;'>{label} munkaóra</div>"
            f"<div style='font-size:1.5rem; font-weight:700; color:{val_col}; "
            f"line-height:1.1; margin-top:0.25rem;'>{v_str}"
            "<span style='font-size:0.7rem; font-weight:500; color:#5a6b80; "
            "margin-left:0.3rem;'>óra</span></div>"
            "</div>"
        )
    panel_html.append("</div>")

    osszesen = sum(h.values())
    panel_html.append(
        "<div style='display:flex; justify-content:space-between; "
        "padding:0.6rem 0.75rem; margin-top:0.8rem; background:#eef3fb; "
        "border-radius:6px;'>"
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
            f"<span style='color:{val_col}; font-weight:600; font-size:0.95rem;'>"
            f"{v_disp}"
            + (
                f" <span style='color:#8a96a8; font-weight:500; font-size:0.85rem;'>{unit}</span>"
                if unit
                else ""
            )
            + "</span></div>"
        )

    sections = []

    t = p.get("terepmunka", {})
    t_tipus = int(t.get("tipus") or 0) if t.get("active") else 0
    if t.get("active") and t_tipus:
        tipus_label = (
            TEREP_TIPUSOK[t_tipus - 1] if 1 <= t_tipus <= len(TEREP_TIPUSOK) else "—"
        )
        if t_tipus in (1, 2, 3, 4, 5):
            terep_rows = [
                row("Módszertan", tipus_label),
                row(
                    "Megkérdezettek",
                    MEGKERDEZETT_KOR[int(t.get("megkerdezett_kor") or 1) - 1],
                ),
                row(
                    "Incidence Rate",
                    INCIDENCE_RATE[int(t.get("incidence_rate") or 1) - 1],
                ),
                row("Kontaktlista", KONTAKTLISTA[int(t.get("kontaktlista") or 1) - 1]),
                row("Mintanagyság", t.get("mintanagysag"), "fő"),
                row(
                    "Mintavétel komplexitás",
                    MINTAVETEL_KOMPLEXITAS[
                        int(t.get("mintavetel_komplexitas") or 1) - 1
                    ],
                ),
                row("Kvótaszempontok", t.get("kvotaszempontok"), "db"),
                row(
                    "Kérdőív hossza",
                    KERDOIV_HOSSZ[int(t.get("kerdoiv_hossz") or 1) - 1],
                ),
            ]
            if t_tipus in (2, 4):
                terep_rows.append(row("Fieldnapok", t.get("fieldnapok"), "nap"))
            if t_tipus == 4:
                terep_rows.append(row("Budapest aránya", t.get("budapest_pct"), "%"))
                terep_rows.append(row("Vidék aránya", t.get("videk_pct"), "%"))
        elif t_tipus == 6:
            try:
                napi_label = NAPI_IDO_OPTIONS[
                    int(t.get("naplo_napi_ido_idx") or 1) - 1
                ][0]
            except Exception:
                napi_label = "—"
            terep_rows = [
                row("Módszertan", tipus_label),
                row("Napok", t.get("naplo_napok"), "nap"),
                row("Résztvevők", t.get("naplo_resztvevok"), "fő"),
                row("Napi időráfordítás", napi_label),
            ]
        elif t_tipus == 7:
            terep_rows = [
                row("Módszertan", tipus_label),
                row("Helyszínek", t.get("mf_helyszinek"), "db"),
                row("Megfigyelési órák", t.get("mf_oraszam"), "óra"),
                row("Budapest aránya", t.get("mf_budapest_pct"), "%"),
                row("Vidék aránya", t.get("mf_videk_pct"), "%"),
            ]
        else:
            terep_rows = [row("Módszertan", tipus_label)]
        sections.append(("Terepmunka", terep_rows))

    dp = p.get("dp", {})
    sections.append(
        (
            "DP",
            [
                row("Ügyfél adatbázis", NEM_IGEN[int(dp.get("ugyfel_adatbazis") or 0)]),
                row(
                    "Programozás", PROGRAMOZAS_OPTIONS[int(dp.get("programozas") or 0)]
                ),
                row("Hosting", NEM_IGEN[int(dp.get("hosting") or 0)]),
                row(
                    "Kvótafelügyelet",
                    KVOTAFELUGYELET_OPTIONS[int(dp.get("kvotafelugyelet") or 0)],
                ),
                row(
                    "Emlékeztetők", EMLEKEZTETO_OPTIONS[int(dp.get("emlekezteto") or 0)]
                ),
                row("Státuszriport", dp.get("statuszriport"), "db"),
                row(
                    "Adatbázis-készítés",
                    ADATBAZIS_KESZ_OPTIONS[int(dp.get("adatbazis_keszites") or 0)],
                ),
            ],
        )
    )

    f = p.get("feldolgozas", {})
    feld_rows = [
        row("Adatbázis", f.get("adatbazis"), "db"),
        row("Top-line", f.get("top_line"), "db"),
        row("Egyszerű elemzés", f.get("egyszeru_elemzes"), "db"),
        row("Mélyelemzés (deepdive)", f.get("melyelemzes"), "db"),
        row("Management summary", f.get("management_summary"), "db"),
        row("Prezentáció", f.get("prezentacio"), "db"),
        row("Segident / modellezés", f.get("segident"), "db"),
        row("Conjoint Excel Tool", f.get("conjoint_tool"), "db"),
        row("Score card", f.get("score_card"), "db"),
        row("Dashboard", f.get("dashboard"), "db"),
        row("Workshop hossza", f.get("workshop_ora"), "óra"),
    ]
    alap = 1 if any((f.get(k) or 0) > 0 for k in f) else 0
    alap_label = "1 – Igen" if alap == 1 else "0 – Nem"
    feld_rows.append(
        "<div style='display:flex; justify-content:space-between; "
        "padding:0.5rem 0.7rem; margin-top:0.3rem; background:#eef3fb; "
        "border-radius:6px;'>"
        "<span style='color:#0b3d91; font-weight:600; font-size:0.95rem;'>"
        "Feldolgozási alap (automatikus)</span>"
        f"<span style='color:#0b3d91; font-weight:700; font-size:0.95rem;'>{alap_label}</span>"
        "</div>"
    )
    sections.append(("Feldolgozás", feld_rows))

    a = p.get("analytics", {})
    if any(int(a.get(k) or 0) == 1 for k in a):
        sections.append(
            (
                "Analytics",
                [
                    row("Conjoint", NINCS_VAN[int(a.get("conjoint") or 0)]),
                    row("KANO-modell", NINCS_VAN[int(a.get("kano") or 0)]),
                    row("Szegmentáció", NINCS_VAN[int(a.get("szegmentacio") or 0)]),
                    row("Modellezés", NINCS_VAN[int(a.get("modellezes") or 0)]),
                ],
            )
        )

    ps = p.get("plusz_szolg", {})
    sections.append(
        (
            "Plusz szolgáltatások",
            [
                row("Fordítás", FORDITAS_OPTIONS[int(ps.get("forditas") or 0)]),
                row("Szinkrontolmács", ps.get("szinkrontolmacs_ora"), "óra"),
                row("Terembérlés", NEM_IGEN[int(ps.get("terembarles") or 0)]),
                row("Catering", NEM_IGEN[int(ps.get("catering") or 0)]),
                row(
                    "Határidő", EXTRA_ROVID_OPTIONS[int(ps.get("extra_rovid") or 1) - 1]
                ),
                row("Tréning", NEM_IGEN[int(ps.get("trening") or 0)]),
            ],
        )
    )

    eg = p.get("egyeb", {})
    if (
        (eg.get("munkaora") or 0) > 0
        or (eg.get("koltseg") or 0) > 0
        or eg.get("megjegyzes")
    ):
        sections.append(
            (
                "Egyéb",
                [
                    row("Egyéb munkaóra", eg.get("munkaora"), "óra"),
                    row("Egyéb költség", eg.get("koltseg"), "Ft"),
                    row("Megjegyzés", eg.get("megjegyzes") or "—"),
                ],
            )
        )

    html_parts = []
    for title, rows_html in sections:
        html_parts.append(
            "<div style='margin-bottom:0.8rem;'>"
            "<div style='font-size:0.78rem; color:#0b3d91; font-weight:700; "
            "letter-spacing:0.04em; text-transform:uppercase; "
            "margin-bottom:0.3rem;'>"
            f"{title}</div>"
            "<div style='border:1px solid #e3e8f0; border-radius:6px; overflow:hidden;'>"
            + "".join(rows_html)
            + "</div></div>"
        )

    with st.expander("Paraméterek összegzése", expanded=False):
        st.markdown("".join(html_parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Multi-job állapotkezelés (pontosan a kvalitatív mintájára)
# ---------------------------------------------------------------------------


def _is_job_complete(p: dict) -> bool:
    """Egy munkafül 'kitöltött' (zöld), ha a terepmunka aktív és van típus."""
    t = p.get("terepmunka", {})
    return bool(t.get("active") and t.get("tipus") is not None)


def _load_state(record_json: Optional[str]) -> dict:
    """DB JSON → belső state struktúra. Régi egyszeres dict formátumot migrál."""
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
            # Régi egyszeres formátum (single params dict)
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
        n = len(state["jobs"])
        state["active_job"] = min(max(0, state["active_job"]), n - 1)
    except Exception:
        state["jobs"] = [default_params()]
        state["active_job"] = 0
    return state


def _render_job_tabs(state: dict, state_key: str, is_editable: bool):
    """Fülek sávja (pontosan a kvalitatív megjelenítésével)."""
    jobs: list = state["jobs"]
    active: int = state["active_job"]
    n = len(jobs)

    complete_flags = [_is_job_complete(jobs[i]) for i in range(n)]

    css_rules = []
    for i, done in enumerate(complete_flags):
        is_active = i == active
        # Kvantitatív: mindig zöld sémát használunk (mint a kvalitatívnál),
        # a "kitöltöttségtől" függetlenül.
        bg = "#198754" if is_active else "#d4edda"
        fg = "#ffffff" if is_active else "#155724"
        border = "#198754" if is_active else "#28a745"
        css_rules.append(
            f".st-key-{state_key}_tab_{i} button {{"
            " min-height: 1.7rem !important;"
            " height: 1.7rem !important;"
            " min-width: 6.2rem !important;"
            " width: 6.2rem !important;"
            " max-width: 6.2rem !important;"
            " padding: 0.05rem 0.45rem !important;"
            " font-size: 0.82rem !important;"
            " font-weight: 500 !important;"
            " line-height: 1 !important;"
            " border-radius: 0.3rem !important;"
            f" background-color: {bg} !important;"
            f" color: {fg} !important;"
            f" border-color: {border} !important;"
            "}"
        )
    css_rules.append(
        f".st-key-{state_key}_add_job button {{"
        " min-height: 1.7rem !important;"
        " height: 1.7rem !important;"
        " min-width: 1.8rem !important;"
        " width: 1.8rem !important;"
        " max-width: 1.8rem !important;"
        " padding: 0.1rem 0.3rem !important;"
        " font-size: 1.05rem !important;"
        " line-height: 1 !important;"
        " border-radius: 0.3rem !important;"
        "}"
    )
    css_rules.append(
        f".st-key-{state_key}_del_job button {{"
        " min-height: 1.7rem !important;"
        " height: 1.7rem !important;"
        " min-width: 1.8rem !important;"
        " width: 1.8rem !important;"
        " max-width: 1.8rem !important;"
        " padding: 0.1rem 0.3rem !important;"
        " font-size: 1.05rem !important;"
        " line-height: 1 !important;"
        " border-radius: 0.3rem !important;"
        "}"
    )
    if css_rules:
        st.markdown("<style>" + "".join(css_rules) + "</style>", unsafe_allow_html=True)

    # 1. sor: + és olló ikonok (csak szerkesztési módban)
    if is_editable:
        icon_c1, icon_c2, _ = st.columns([0.28, 0.28, 12])
        if icon_c1.button(
            "\u271a",
            key=f"{state_key}_add_job",
            help="Új munka hozzáadása",
        ):
            state["jobs"].append(default_params())
            state["active_job"] = len(state["jobs"]) - 1
            st.rerun()
        if icon_c2.button(
            "\u2702",
            key=f"{state_key}_del_job",
            help=f"Munka {active + 1} törlése",
            disabled=n <= 1,
        ):
            state["jobs"].pop(active)
            state["active_job"] = max(0, active - 1)
            st.rerun()

    # 2. sor: munkafülek
    tab_cols = st.columns([0.78] * n + [12], vertical_alignment="center")
    for i in range(n):
        prefix = "\u2713 " if complete_flags[i] else ""
        label = f"{prefix}Munka {i + 1}"
        if tab_cols[i].button(label, key=f"{state_key}_tab_{i}"):
            state["active_job"] = i
            st.rerun()


# ---------------------------------------------------------------------------
# Fő belépőpont
# ---------------------------------------------------------------------------


def render_stage1_kalkulacio_kvantitativ(offer_id: int, is_editable: bool, db: Session):
    if not is_editable:
        st.info(
            "Ez a szakasz lezárult – a kalkuláció csak olvasható módban jelenik meg."
        )

    st.markdown("#### Kalkuláció – Kvantitatív kutatás")
    st.caption(
        "Blokkokat töltsd ki a paraméterekkel. "
        "A jobb oldali munkaóra-bontás folyamatosan újraszámolódik. (Ország: Magyarország.)"
    )

    state_key = f"kvanti_kalk_{offer_id}"
    if state_key not in st.session_state:
        record = crud.get_stage1_kalk_kvantitativ(db, offer_id)
        st.session_state[state_key] = _load_state(
            record.params_json if record else None
        )

    state: dict = st.session_state[state_key]
    jobs: list = state["jobs"]

    # Munkafülek sávja
    _render_job_tabs(state, state_key, is_editable)

    # Aktív munka
    active_idx: int = state.get("active_job", 0)
    if active_idx >= len(jobs):
        active_idx = 0
        state["active_job"] = 0
    p: dict = jobs[active_idx]
    job_key = f"{state_key}_j{active_idx}"

    left, right = st.columns([1, 1])

    with left:
        _render_terepmunka(p, is_editable, job_key)
        _render_dp(p, is_editable, job_key)
        _render_feldolgozas(p, is_editable, job_key)
        _render_analytics(p, is_editable, job_key)
        _render_plusz_szolg(p, is_editable, job_key)
        _render_egyeb(p, is_editable, job_key)

    with right:
        # Összesített munkaórák – minden munkafül összege
        h_total = _new_hours()
        for job_p in jobs:
            h_job = calc_munkaora(job_p)
            for k in h_total:
                h_total[k] += h_job.get(k, 0.0)

        extra_rovid_any = any(
            int(job_p.get("plusz_szolg", {}).get("extra_rovid") or 1) == 2
            for job_p in jobs
        )
        _render_munkaora_panel(h_total, extra_rovid=extra_rovid_any)
        _render_param_summary_panel(p)

    if is_editable:
        st.divider()
        if st.button(
            "Kalkuláció mentése",
            type="primary",
            key=f"{state_key}_save",
        ):
            errs = _validate_feldolgozas(p)
            if errs:
                st.error("Mentés sikertelen: " + "; ".join(errs))
            else:
                save_data = {
                    "jobs": jobs,
                    "active_job": active_idx,
                }
                crud.upsert_stage1_kalk_kvantitativ(
                    db, offer_id, json.dumps(save_data, ensure_ascii=False)
                )
                st.toast("Kalkuláció mentve!")
