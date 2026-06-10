"""
Szakasz 1 – Kalkuláció: Kvalitatív kutatás.

A Kvalitatív lap (1_documents/kvalitativ.xlsx) alapján képezzük le a
paramétereket és a hozzájuk tartozó munkaóra-képleteket.

Blokkok:
  1) Rekrutálás
  2) Terepmunka – interjúk / csoportok (egy session-konfiguráció)
  3) Napló / blog
  4) Megfigyelés
  5) Feldolgozás (Szemiotikához hasonló, eltérő Workshop-képlettel)
  6) Plusz szolgáltatások
  7) Egyéb

A „Plusz szolgáltatások / Extra rövid határidő” = 2 (extra rövid) esetén
minden számolt munkaóra 1,2-szeresével szorozzuk.

A részletek és cellahivatkozások a kvalitativ.xlsx-ben:
  - Rekrutálás: H20/I20/M20/P20 fix óraértékek
  - Terepmunka: H23/H24, M23/M24, M25/M26, M30..N33, M36, M38, H38
  - Napló/blog: H40, I39, M39, P39
  - Megfigyelés: I42, P42, M43, M44
  - Feldolgozás: M46..P54 (Workshop: 2+óra mindenkire)
"""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st
from sqlalchemy.orm import Session

from db import crud

# ---------------------------------------------------------------------------
# Konstansok – legördülő opciók (label-listák; index 1-től)
# ---------------------------------------------------------------------------

INTERJU_TIPUSOK = [
    "1. Mélyinterjú (1 fő)",
    "2. Páros interjú (2 fő)",
    "3. Triád (3 fő)",
    "4. Mini csoport (4 fő)",
    "5. Csoport (6 fős)",
    "6. Csoport (8 fős)",
    "7. XXL Csoport (10 fő)",
    "8. Bi-pólus (12 fő)",
    "9. Konfliktus csoport (12 fő)",
    "10. Elkísért vásárlás / AST (1 fő)",
    "11. Napló / blog",
    "12. Megfigyelés",
]
# Interjú-típusúak: 1,2,3,10. A többi csoport. 11=Napló/blog, 12=Megfigyelés (külön logika).
INTERJU_INDEXEK = {1, 2, 3, 10}

# Típusonkénti fix alanyszám (alanyok száma / session); 11,12 = 0
TIPUS_ALANYSZAM = {
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 6,
    6: 8,
    7: 10,
    8: 12,
    9: 12,
    10: 1,
    11: 0,
    12: 0,
}

PLATFORM_OPTIONS = ["1. online", "2. off-line", "3. telefon"]
HOSSZ_OPTIONS = [
    ("1. 30 perc", 30),
    ("2. 45 perc", 45),
    ("3. 60 perc", 60),
    ("4. 90 perc", 90),
    ("5. 120 perc", 120),
    ("6. 150 perc", 150),
    ("7. 180 perc", 180),
]
MEGKERDEZETT_KOR = [
    "1. lakosság",
    "2. vállalati – SOHO",
    "3. vállalati – SMB",
    "4. vállalati – LB",
    "5. orvos",
    "6. szakértő",
]
HELYSZIN_OPTIONS = ["1. Budapest", "2. nagyváros", "3. kisváros", "4. falu"]
ELOFELADAT_OPTIONS = [
    "1. nincs",
    "2. könnyű",
    "3. közepes",
    "4. bonyolult (pl. márkanovella)",
]
NAPI_IDO_OPTIONS = [
    ("1. 15 perc", 15),
    ("2. 30 perc", 30),
    ("3. 45 perc", 45),
    ("4. 60 perc", 60),
]
SZERVEZES_NEHEZSEG = [
    "1. egyszerű (nincs kvóta)",
    "2. közepes (márkafogyasztó, speciális kvóta nélkül)",
    "3. nehéz (speciális kvóta)",
    "4. extrém (szűk célcsoport + kvóta)",
]
KONTAKTLISTA = [
    "1. nincs kontaktlista",
    "2. Kantar Hoffmann készíti",
    "3. ügyfél adja",
]
UGYFEL_SZERVEZES = [
    "1. nincs ügyféltámogatás",
    "2. ügyfél szervezi teljesen",
    "3. ügyfél előmelegíti, mi szervezzük",
]
KIIRAS_OPTIONS = [
    "0. nincs",
    "1. gépeléssel – szó szerint",
    "2. kiírás (kivonatolt)",
    "3. automatizálva",
]
FORDITAS_OPTIONS = [
    "0. nincs",
    "1. fordítóval",
    "2. fordítóval, lektorálva",
    "3. szoftverrel",
]
EXTRA_ROVID_OPTIONS = ["1. normál", "2. extra rövid (1,2× szorzó)"]
NEM_IGEN = ["0. Nem", "1. Igen"]


# A munkaóra-kategóriák kulcsa → megjelenítendő név
MUNKAORA_CATS = [
    ("szervezoi", "Szervezői"),
    ("szervezesi_vez", "Szervezési vezetői"),
    ("dp", "DP"),
    ("dp_vez", "DP vezetői"),
    ("junior_kut", "Junior kutatói"),
    ("executive_kut", "Executive kutatói"),
    ("szenior_kut", "Szenior kutatói"),
    ("kut_ig", "Kutatási igazgatói"),
    ("gad", "GAD"),
]


# ---------------------------------------------------------------------------
# Alapértelmezett paraméter-struktúra
# ---------------------------------------------------------------------------


def default_params() -> dict:
    return {
        "rekrutalas": {
            "active": False,
            "szervezes_nehezseg": 1,
            "kontaktlista": 1,
            "ugyfel_szervezes": 1,
        },
        "terepmunka": {
            "active": False,
            "tipus": None,  # None = nincs kiválasztva
            "darab": 0,
            "platform": 1,
            "hossz_perc_idx": 3,  # 1-7 index a HOSSZ_OPTIONS-ban → érték: 60 perc
            "megkerdezett_kor": 1,
            "helyszin": 1,
            "elofeladat": 1,
            # Napló / blog (tipus=11) paraméterei
            "napok": 0,
            "resztvevok": 0,
            "napi_ido_idx": 1,
            # Megfigyelés (tipus=12) paraméterei
            "oraszam": 0.0,
            "budapest_pct": 0,
            "videk_pct": 0,
        },
        "feldolgozas": {
            "debrief": 0,
            "top_line": 0,
            "egyszeru_elemzes": 0,
            "melyelemzes": 0,
            "management_summary": 0,
            "prezentacio": 0,
            "filmkeszites_ora": 0.0,
            "workshop_ora": 0.0,
        },
        "plusz_szolg": {
            "kiiras": 0,
            "forditas": 0,
            "szinkrontolmacs_ora": 0.0,
            "terembarles": 0,
            "catering": 0,
            "extra_rovid": 1,
            "trening": 0,
            "desk_research": 0,
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


def calc_munkaora(p: dict, celcsoport: Optional[str]) -> dict:
    """Az egyes blokkok munkaóra-bontásának kiszámolása az xlsx alapján."""
    is_lak = celcsoport == "Lakossági"
    h = _new_hours()

    # 1) Rekrutálás (H20/I20/M20/P20) – csak ha aktív
    rek = p.get("rekrutalas", {})
    if rek.get("active"):
        # H20 = 3 + 1,5×alanyszám×0,5 + 3,5×csoport + interjúszám×0,8
        terep = p.get("terepmunka", {})
        tipus_rek = int(terep.get("tipus") or 0)
        if terep.get("active") and 1 <= tipus_rek <= 10:
            darab = float(terep.get("darab") or 0)
            is_interju = tipus_rek in INTERJU_INDEXEK
            csoport_n = 0.0 if is_interju else darab
            interju_n = darab if is_interju else 0.0
            alanyszam = float(TIPUS_ALANYSZAM.get(tipus_rek, 0)) * darab
        elif terep.get("active") and tipus_rek == 11:
            # Napló/blog: a resztvevők az alanyszám, nincs csoport/interjú bontás
            csoport_n = 0.0
            interju_n = 0.0
            alanyszam = float(terep.get("resztvevok") or 0)
        else:
            # Megfigyelés (12) vagy nincs terepmunka: nincs mintaméret
            csoport_n = 0.0
            interju_n = 0.0
            alanyszam = 0.0
        _add(
            h,
            "szervezoi",
            3 + 1.5 * alanyszam * 0.5 + 3.5 * csoport_n + interju_n * 0.8,
        )
        _add(h, "szervezesi_vez", 1)
        _add(h, "executive_kut", 3)
        _add(h, "gad", 2)

    # 2) Terepmunka (1-10) / Naplo-blog (11) / Megfigyeles (12)
    terep = p.get("terepmunka", {})
    t_tipus = int(terep.get("tipus") or 0)
    if terep.get("active") and 1 <= t_tipus <= 10 and (terep.get("darab") or 0) > 0:
        tipus = t_tipus
        darab = float(terep.get("darab") or 0)
        platform = int(terep.get("platform") or 1)
        hossz_idx = int(terep.get("hossz_perc_idx") or 1) - 1
        hossz_perc = (
            HOSSZ_OPTIONS[hossz_idx][1] if 0 <= hossz_idx < len(HOSSZ_OPTIONS) else 60
        )
        # A képletek "hossz" mértékegysége óra → percek/60
        hossz_ora = hossz_perc / 60.0
        kor = int(terep.get("megkerdezett_kor") or 1)
        helyszin = int(terep.get("helyszin") or 1)
        elofeladat = int(terep.get("elofeladat") or 1)
        is_interju = tipus in INTERJU_INDEXEK

        # Szervezői (H23/H24)
        if is_interju:
            _add(h, "szervezoi", darab * 4)
        else:
            _add(h, "szervezoi", darab * 1)

        # Kut. ig. (O23/O24): 1 mindkét esetben
        _add(h, "kut_ig", 1)
        # GAD (P23/P24)
        _add(h, "gad", darab * 1 if is_interju else 0)

        # Executive (M23/M24)
        if is_interju:
            _add(h, "executive_kut", 4 + darab * hossz_ora * 1.2)
        else:
            _add(h, "executive_kut", 4 + darab * hossz_ora * 1.5)

        # Platform off-line bónusz (M25/M26)
        if platform == 2:  # off-line
            if is_interju:
                _add(h, "executive_kut", darab * 0.25)
            else:
                _add(h, "executive_kut", darab * 0.5)

        # Vállalati (2-4) vagy orvos/szakértő (5-6) → Szenior sorra
        # (Helyettesíti vagy kiegészíti az Executive sort? Az xlsx alapján
        # ezek külön Szenior munkaórát adnak hozzá – nem helyettesítenek.)
        if kor in (2, 3, 4):
            if is_interju:
                _add(h, "szenior_kut", 4 + darab * hossz_ora * 1.2)
            else:
                _add(h, "szenior_kut", 4 + darab * hossz_ora * 1.5)
        elif kor in (5, 6):
            # Az 1,5-ös szorzó már bele van építve a fenti képletbe, és a
            # "Szervezői szorzó 1,5" a Szervezői sorra hat (H30/H31/H32/H33
            # mind 1,2/1,5 szorzókat ír óraszámra). Itt a Szenior alapot
            # azonosan számoljuk a vállalati ággal, az orvos/szakértő
            # többletet a Szervezői sorra is rátesszük (1,5×).
            if is_interju:
                _add(h, "szenior_kut", 4 + darab * hossz_ora * 1.2)
            else:
                _add(h, "szenior_kut", 4 + darab * hossz_ora * 1.5)
            # Szervezői óraszorzó 1,5 (csak a most hozzáadott execve.)
            # Itt nem nyúlunk vissza, helyette egy +50%-os pótlékot adunk
            # a darabra/hosszra:
            _add(h, "szervezoi", (darab * (4 if is_interju else 1)) * 0.5)
        elif kor in (2, 3, 4):
            # Vállalati óraszorzó 1,2: +20% a fenti Szervezői blokkra
            _add(h, "szervezoi", (darab * (4 if is_interju else 1)) * 0.2)

        # Helyszín: nem-Budapesti offline → M36 = csoport*3 + interjú*3
        if platform == 2 and helyszin in (2, 3, 4):
            _add(h, "executive_kut", darab * 3)

        # Előfeladat 2-4 → M38 = csoport*2 + interjú*0,5; H38 szorzó 1,2
        if elofeladat in (2, 3, 4):
            if is_interju:
                _add(h, "executive_kut", darab * 0.5)
            else:
                _add(h, "executive_kut", darab * 2)
            # H38 1,2x szorzó a Szervezői most számolt alapra
            _add(h, "szervezoi", (darab * (4 if is_interju else 1)) * 0.2)

    # 3) Napló / blog (I39/M39/P39 + H40)
    elif terep.get("active") and t_tipus == 11:
        napok_nb = float(terep.get("napok") or 0)
        resztvevok_nb = float(terep.get("resztvevok") or 0)
        if napok_nb > 0 and resztvevok_nb > 0:
            _add(h, "szervezesi_vez", 1)
            _add(h, "executive_kut", 2 + (1 + resztvevok_nb / 100.0) * 2 * napok_nb)
            _add(h, "gad", 2)
            _add(h, "szervezoi", resztvevok_nb * 0.8 + 3)

    # 4) Megfigyelés (I42/P42/M43/M44)
    elif terep.get("active") and t_tipus == 12:
        oraszam_mf = float(terep.get("oraszam") or 0)
        bp_pct = float(terep.get("budapest_pct") or 0) / 100.0
        videk_pct = float(terep.get("videk_pct") or 0) / 100.0
        if oraszam_mf > 0:
            _add(h, "szervezesi_vez", 1)
            _add(h, "gad", 1)
            if bp_pct > 0:
                _add(h, "executive_kut", (3 + oraszam_mf * 1.2 + 1) * bp_pct)
            if videk_pct > 0:
                _add(h, "executive_kut", (3 + oraszam_mf * 1.2 + 4) * videk_pct)

    # 5) Feldolgozás (Workshop képlet eltér: 2+óra minden szegmensre)
    f = p.get("feldolgozas", {})
    fp_alap_active = any(
        (f.get(k) or 0) > 0
        for k in (
            "debrief",
            "top_line",
            "egyszeru_elemzes",
            "melyelemzes",
            "management_summary",
            "prezentacio",
            "filmkeszites_ora",
            "workshop_ora",
        )
    )
    if fp_alap_active:
        # M46/N46 = 25, O46=2, P46=1, L46=2+résztvevők×1
        # "résztvevők" itt = terepmunka.darab + naplo.resztvevok (heurisztika)
        if t_tipus == 11:
            resztvevok_total = float(terep.get("resztvevok") or 0)
        elif 1 <= t_tipus <= 10:
            resztvevok_total = float(terep.get("darab") or 0)
        else:
            resztvevok_total = 0.0
        _add(h, "junior_kut", 2 + resztvevok_total * 1)
        if is_lak:
            _add(h, "executive_kut", 25)
        else:
            _add(h, "szenior_kut", 25)
        _add(h, "kut_ig", 2)
        _add(h, "gad", 1)

        # Per-tétel paraméterek
        per_unit = {
            "debrief": (2, 2),
            "top_line": (5, 1),
            "egyszeru_elemzes": (8, 1),
            "melyelemzes": (15, 2),
            "management_summary": (5, 2),
            "prezentacio": (2, 2),
        }
        for key, (kut_h, gad_h) in per_unit.items():
            n = float(f.get(key) or 0)
            if n > 0:
                if is_lak:
                    _add(h, "executive_kut", n * kut_h)
                else:
                    _add(h, "szenior_kut", n * kut_h)
                _add(h, "gad", n * gad_h)
                # Mélyelemzés és mgmt summary: O50/O51 = 2 (kut. ig.)
                if key in ("melyelemzes", "management_summary"):
                    _add(h, "kut_ig", 2)

        # Filmkészítés
        film_ora = float(f.get("filmkeszites_ora") or 0)
        if film_ora > 0:
            _add(h, "szenior_kut", film_ora)
            _add(h, "gad", 2)

        # Workshop (2 + óra MINDEN munkaóra-kategóriára: M54/N54/O54/P54)
        ws = float(f.get("workshop_ora") or 0)
        if ws > 0:
            ws_val = 2 + ws
            if is_lak:
                _add(h, "executive_kut", ws_val)
            else:
                _add(h, "szenior_kut", ws_val)
            _add(h, "kut_ig", ws_val)
            _add(h, "gad", ws_val)

    # 6) Plusz szolgáltatások – Extra rövid határidő szorzó (1,2x)
    ps = p.get("plusz_szolg", {})
    if int(ps.get("extra_rovid") or 1) == 2:
        for k in h:
            h[k] = h[k] * 1.2

    # 7) Egyéb extra munkaóra (Szervezőire dobjuk)
    eg = p.get("egyeb", {})
    extra_ora = float(eg.get("munkaora") or 0)
    if extra_ora > 0:
        _add(h, "szervezoi", extra_ora)

    return h


def _calc_feldolgozasi_alap(f: dict) -> int:
    keys = (
        "debrief",
        "top_line",
        "egyszeru_elemzes",
        "melyelemzes",
        "management_summary",
        "prezentacio",
        "filmkeszites_ora",
        "workshop_ora",
    )
    return 1 if any((f.get(k) or 0) > 0 for k in keys) else 0


def _validate_dependents(f: dict) -> list[str]:
    """Mgmt. summary / Prezentáció önállóan nem rendelhetők meg."""
    deps = {"management_summary": "Management summary", "prezentacio": "Prezentáció"}
    errs = []
    sibling_keys = (
        "debrief",
        "top_line",
        "egyszeru_elemzes",
        "melyelemzes",
        "filmkeszites_ora",
        "workshop_ora",
    )
    for k, name in deps.items():
        if (f.get(k) or 0) > 0:
            has_sibling = any((f.get(s) or 0) > 0 for s in sibling_keys)
            other_dep = [
                v for kk, v in deps.items() if kk != k and (f.get(kk) or 0) > 0
            ]
            if not has_sibling and not other_dep:
                errs.append(name)
    return errs


# ---------------------------------------------------------------------------
# UI – Bal oldali paraméter-blokkok renderelése
# ---------------------------------------------------------------------------


def _render_rekrutalas(p: dict, is_editable: bool, key_prefix: str):
    rek = p["rekrutalas"]
    with st.expander("1) Rekrutálás", expanded=False):
        rek["active"] = st.checkbox(
            "Van rekrutálás",
            value=bool(rek.get("active")),
            key=f"{key_prefix}_rek_active",
            disabled=not is_editable,
        )
        if rek["active"]:
            rek["szervezes_nehezseg"] = (
                st.selectbox(
                    "Szervezés nehézsége",
                    SZERVEZES_NEHEZSEG,
                    index=int(rek.get("szervezes_nehezseg") or 1) - 1,
                    key=f"{key_prefix}_rek_nehezseg",
                    disabled=not is_editable,
                    help="Csak az Alvállalkozói díjat befolyásolja.",
                )
                .split(".")[0]
                .strip()
                or "1"
            )
            rek["szervezes_nehezseg"] = int(rek["szervezes_nehezseg"])
            rek["kontaktlista"] = int(
                st.selectbox(
                    "Kontaktlista",
                    KONTAKTLISTA,
                    index=int(rek.get("kontaktlista") or 1) - 1,
                    key=f"{key_prefix}_rek_kontakt",
                    disabled=not is_editable,
                ).split(".")[0]
            )
            rek["ugyfel_szervezes"] = int(
                st.selectbox(
                    "Ügyfél általi szervezés / előmelegítés",
                    UGYFEL_SZERVEZES,
                    index=int(rek.get("ugyfel_szervezes") or 1) - 1,
                    key=f"{key_prefix}_rek_ugyfel",
                    disabled=not is_editable,
                ).split(".")[0]
            )


def _render_terepmunka(p: dict, is_editable: bool, key_prefix: str):
    t = p["terepmunka"]
    with st.expander("2) Terepmunka", expanded=False):
        t["active"] = st.checkbox(
            "Van terepmunka",
            value=bool(t.get("active")),
            key=f"{key_prefix}_terep_active",
            disabled=not is_editable,
        )
        if t["active"]:
            # Típus – None ha még nincs kiválasztva
            saved_tipus = t.get("tipus")
            _tipus_idx = (int(saved_tipus) - 1) if saved_tipus is not None else None
            _tipus_label = st.selectbox(
                "Típus",
                INTERJU_TIPUSOK,
                index=_tipus_idx,
                placeholder="Válassz terepmunka-típust…",
                key=f"{key_prefix}_terep_tipus",
                disabled=not is_editable,
            )
            if _tipus_label is not None:
                t["tipus"] = int(_tipus_label.split(".")[0])
            else:
                t["tipus"] = None
            tipus = t["tipus"]
            if tipus is not None and 1 <= tipus <= 10:
                t["darab"] = st.number_input(
                    "Darabszám",
                    min_value=0,
                    step=1,
                    value=int(t.get("darab") or 0),
                    key=f"{key_prefix}_terep_darab",
                    disabled=not is_editable,
                )
                t["platform"] = int(
                    st.selectbox(
                        "Platform",
                        PLATFORM_OPTIONS,
                        index=int(t.get("platform") or 1) - 1,
                        key=f"{key_prefix}_terep_platform",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
                t["hossz_perc_idx"] = int(
                    st.selectbox(
                        "Interjú / csoport hossza",
                        [opt for opt, _ in HOSSZ_OPTIONS],
                        index=int(t.get("hossz_perc_idx") or 3) - 1,
                        key=f"{key_prefix}_terep_hossz",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
                t["megkerdezett_kor"] = int(
                    st.selectbox(
                        "Megkérdezettek köre",
                        MEGKERDEZETT_KOR,
                        index=int(t.get("megkerdezett_kor") or 1) - 1,
                        key=f"{key_prefix}_terep_kor",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
                t["helyszin"] = int(
                    st.selectbox(
                        "Megkérdezés helye",
                        HELYSZIN_OPTIONS,
                        index=int(t.get("helyszin") or 1) - 1,
                        key=f"{key_prefix}_terep_helyszin",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
                t["elofeladat"] = int(
                    st.selectbox(
                        "Előfeladat",
                        ELOFELADAT_OPTIONS,
                        index=int(t.get("elofeladat") or 1) - 1,
                        key=f"{key_prefix}_terep_elof",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
            elif tipus == 11:
                t["napok"] = st.number_input(
                    "Napok száma (1–10)",
                    min_value=0,
                    max_value=10,
                    step=1,
                    value=int(t.get("napok") or 0),
                    key=f"{key_prefix}_terep_napok",
                    disabled=not is_editable,
                )
                t["resztvevok"] = st.number_input(
                    "Résztvevők száma (10–40)",
                    min_value=0,
                    max_value=40,
                    step=1,
                    value=int(t.get("resztvevok") or 0),
                    key=f"{key_prefix}_terep_resztvevok",
                    disabled=not is_editable,
                )
                t["napi_ido_idx"] = int(
                    st.selectbox(
                        "Napi időráfordítás",
                        [opt for opt, _ in NAPI_IDO_OPTIONS],
                        index=int(t.get("napi_ido_idx") or 1) - 1,
                        key=f"{key_prefix}_terep_napi_ido",
                        disabled=not is_editable,
                    ).split(".")[0]
                )
            elif tipus == 12:
                t["oraszam"] = st.number_input(
                    "Megfigyelési óraszám",
                    min_value=0.0,
                    step=0.5,
                    value=float(t.get("oraszam") or 0),
                    key=f"{key_prefix}_terep_oraszam",
                    disabled=not is_editable,
                )
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


def _render_feldolgozas(p: dict, is_editable: bool, key_prefix: str):
    f = p["feldolgozas"]
    with st.expander("3) Feldolgozás", expanded=False):
        st.caption(
            "Minden paraméter alapértéke 0; írd felül a tényleges értékekkel. "
            "A „Feldolgozási alap” automatikusan számolódik."
        )
        int_params = [
            ("debrief", "Debrief (db)"),
            ("top_line", "Top-line (db)"),
            ("egyszeru_elemzes", "Egyszerű elemzés (db)"),
            ("melyelemzes", "Mélyelemzés / deepdive (db)"),
            (
                "management_summary",
                "Management summary (db) – önállóan nem rendelhető",
            ),
            ("prezentacio", "Prezentáció (db) – önállóan nem rendelhető"),
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
        for key, label in (
            ("filmkeszites_ora", "Filmkészítés (óra)"),
            ("workshop_ora", "Workshop hossza (óra)"),
        ):
            f[key] = st.number_input(
                label,
                min_value=0.0,
                step=0.5,
                value=float(f.get(key) or 0),
                key=f"{key_prefix}_f_{key}",
                disabled=not is_editable,
            )

        errs = _validate_dependents(f)
        if errs:
            st.error(
                "A következő tételek önállóan nem rendelhetők meg, kell mellé "
                "legalább még egy >0 elem: " + ", ".join(errs)
            )


def _render_plusz_szolg(p: dict, is_editable: bool, key_prefix: str):
    ps = p["plusz_szolg"]
    with st.expander("4) Plusz szolgáltatások", expanded=False):
        ps["kiiras"] = int(
            st.selectbox(
                "Kiírás",
                KIIRAS_OPTIONS,
                index=int(ps.get("kiiras") or 0),
                key=f"{key_prefix}_ps_kiiras",
                disabled=not is_editable,
            ).split(".")[0]
        )
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
                help="„Extra rövid” esetén minden munkaóra 1,2× szorzót kap.",
            ).split(".")[0]
        )
        col3, col4 = st.columns(2)
        ps["trening"] = int(
            col3.selectbox(
                "Tréning",
                NEM_IGEN,
                index=int(ps.get("trening") or 0),
                key=f"{key_prefix}_ps_tren",
                disabled=not is_editable,
            ).split(".")[0]
        )
        ps["desk_research"] = int(
            col4.selectbox(
                "Desk research",
                NEM_IGEN,
                index=int(ps.get("desk_research") or 0),
                key=f"{key_prefix}_ps_desk",
                disabled=not is_editable,
            ).split(".")[0]
        )


def _render_egyeb(p: dict, is_editable: bool, key_prefix: str):
    e = p["egyeb"]
    with st.expander("5) Egyéb", expanded=False):
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


def _render_munkaora_panel(h: dict, celcsoport: Optional[str], extra_rovid: bool):
    """Jobb oldali panel – csempés (3 oszlop) elrendezésben a munkaóra-kategóriák.
    A Szemiotika kalkuláció paneljével vizuálisan harmonizáló stílus."""
    cs_label = celcsoport or "—"
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
        f"Célcsoport: <b>{cs_label}</b>{badge_extra}</div>",
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

    # Összesen sor
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
    """Részletes paraméter-összegzés – expanderbe csomagolva (sok blokk)."""

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

    rek = p.get("rekrutalas", {})
    if rek.get("active"):
        sections.append(
            (
                "Rekrutálás",
                [
                    row(
                        "Szervezés nehézsége",
                        SZERVEZES_NEHEZSEG[int(rek.get("szervezes_nehezseg") or 1) - 1],
                    ),
                    row(
                        "Kontaktlista",
                        KONTAKTLISTA[int(rek.get("kontaktlista") or 1) - 1],
                    ),
                    row(
                        "Ügyfél szervezés",
                        UGYFEL_SZERVEZES[int(rek.get("ugyfel_szervezes") or 1) - 1],
                    ),
                ],
            )
        )

    t = p.get("terepmunka", {})
    t_tipus = int(t.get("tipus") or 0) if t.get("active") else 0
    if t.get("active") and t_tipus:
        tipus_label = (
            INTERJU_TIPUSOK[t_tipus - 1]
            if 1 <= t_tipus <= len(INTERJU_TIPUSOK)
            else "—"
        )
        if 1 <= t_tipus <= 10:
            try:
                hossz_label = HOSSZ_OPTIONS[int(t.get("hossz_perc_idx") or 1) - 1][0]
            except Exception:
                hossz_label = "—"
            terep_rows = [
                row("Típus", tipus_label),
                row("Darabszám", t.get("darab"), "db"),
                row("Platform", PLATFORM_OPTIONS[int(t.get("platform") or 1) - 1]),
                row("Hossz", hossz_label),
                row(
                    "Megkérdezettek",
                    MEGKERDEZETT_KOR[int(t.get("megkerdezett_kor") or 1) - 1],
                ),
                row("Helyszín", HELYSZIN_OPTIONS[int(t.get("helyszin") or 1) - 1]),
                row(
                    "Előfeladat",
                    ELOFELADAT_OPTIONS[int(t.get("elofeladat") or 1) - 1],
                ),
            ]
        elif t_tipus == 11:
            try:
                napi_label = NAPI_IDO_OPTIONS[int(t.get("napi_ido_idx") or 1) - 1][0]
            except Exception:
                napi_label = "—"
            terep_rows = [
                row("Típus", tipus_label),
                row("Napok", t.get("napok"), "nap"),
                row("Résztvevők", t.get("resztvevok"), "fő"),
                row("Napi időráfordítás", napi_label),
            ]
        elif t_tipus == 12:
            terep_rows = [
                row("Típus", tipus_label),
                row("Óraszám", t.get("oraszam"), "óra"),
                row("Budapest aránya", t.get("budapest_pct"), "%"),
                row("Vidék aránya", t.get("videk_pct"), "%"),
            ]
        else:
            terep_rows = [row("Típus", tipus_label)]
        sections.append(("Terepmunka", terep_rows))

    f = p.get("feldolgozas", {})
    feld_rows = [
        row("Debrief", f.get("debrief"), "db"),
        row("Top-line", f.get("top_line"), "db"),
        row("Egyszerű elemzés", f.get("egyszeru_elemzes"), "db"),
        row("Mélyelemzés (deepdive)", f.get("melyelemzes"), "db"),
        row("Management summary", f.get("management_summary"), "db"),
        row("Prezentáció", f.get("prezentacio"), "db"),
        row("Filmkészítés", f.get("filmkeszites_ora"), "óra"),
        row("Workshop hossza", f.get("workshop_ora"), "óra"),
    ]
    alap = _calc_feldolgozasi_alap(f)
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

    ps = p.get("plusz_szolg", {})
    ps_rows = [
        row("Kiírás", KIIRAS_OPTIONS[int(ps.get("kiiras") or 0)]),
        row("Fordítás", FORDITAS_OPTIONS[int(ps.get("forditas") or 0)]),
        row("Szinkrontolmács", ps.get("szinkrontolmacs_ora"), "óra"),
        row("Terembérlés", NEM_IGEN[int(ps.get("terembarles") or 0)]),
        row("Catering", NEM_IGEN[int(ps.get("catering") or 0)]),
        row("Határidő", EXTRA_ROVID_OPTIONS[int(ps.get("extra_rovid") or 1) - 1]),
        row("Tréning", NEM_IGEN[int(ps.get("trening") or 0)]),
        row("Desk research", NEM_IGEN[int(ps.get("desk_research") or 0)]),
    ]
    sections.append(("Plusz szolgáltatások", ps_rows))

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


def _render_feldolg_alap_panel(p: dict):
    alap = _calc_feldolgozasi_alap(p.get("feldolgozas", {}))
    alap_label = "1 – Igen" if alap == 1 else "0 – Nem"
    st.markdown(
        "<div style='border:1px solid #d6dde8; border-radius:8px; padding:0.7rem 0.9rem; "
        "background:#ffffff; margin-top:1rem; display:flex; justify-content:space-between;'>"
        "<span style='color:#0b3d91; font-weight:600;'>Feldolgozási alap (automatikus)</span>"
        f"<span style='color:#0b3d91; font-weight:700;'>{alap_label}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Multi-job helpers
# ---------------------------------------------------------------------------


def _is_job_complete(p: dict) -> bool:
    """Egy munkafül 'kitöltött' (zöld), ha legalább egy fő szekció aktív."""
    rek_ok = p.get("rekrutalas", {}).get("active", False)
    terep = p.get("terepmunka", {})
    terep_ok = terep.get("active", False) and terep.get("tipus") is not None
    return bool(rek_ok or terep_ok)


def _load_state(record_json: Optional[str]) -> dict:
    """DB JSON → belső state struktúra. Régi (egyszeres dict) formátumot migrál."""
    state: dict = {"jobs": [], "active_job": 0}
    if not record_json:
        state["jobs"] = [default_params()]
        return state
    try:
        loaded = json.loads(record_json)
        if isinstance(loaded, dict) and "jobs" in loaded:
            # Új formátum
            raw_jobs = loaded.get("jobs", [])
            state["active_job"] = int(loaded.get("active_job", 0))
        else:
            # Régi egyszeres formátum
            raw_jobs = [loaded]
        jobs = []
        for raw in raw_jobs:
            base = default_params()
            if isinstance(raw, dict):
                for sec in base:
                    if sec in raw and isinstance(raw[sec], dict):
                        base[sec].update(raw[sec])
            jobs.append(base)
        state["jobs"] = jobs if jobs else [default_params()]
        # bounds check (a jobs fallback után!)
        n = len(state["jobs"])
        state["active_job"] = min(max(0, state["active_job"]), n - 1)
    except Exception:
        state["jobs"] = [default_params()]
        state["active_job"] = 0
    return state


def _render_job_tabs(state: dict, state_key: str, is_editable: bool):
    """Fülek sávja a munkák között, + gomb új munkához, × a törölhöz."""
    jobs: list = state["jobs"]
    active: int = state["active_job"]
    n = len(jobs)

    # CSS: kompakt, alacsony fülek; a kitöltött fülek zöldek.
    complete_flags = [_is_job_complete(jobs[i]) for i in range(n)]
    css_rules = []
    for i, done in enumerate(complete_flags):
        is_active = i == active
        if done:
            bg = "#198754" if is_active else "#d4edda"
            fg = "#ffffff" if is_active else "#155724"
            border = "#198754" if is_active else "#28a745"
        elif is_active:
            bg = "#f1f3f5"
            fg = "#495057"
            border = "#ced4da"
        else:
            bg = "#ffffff"
            fg = "#6c757d"
            border = "#dee2e6"
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
        btn_type = "primary" if i == active else "secondary"
        if tab_cols[i].button(
            label,
            key=f"{state_key}_tab_{i}",
        ):
            state["active_job"] = i
            st.rerun()


# ---------------------------------------------------------------------------
# Fő belépőpont
# ---------------------------------------------------------------------------


def render_stage1_kalkulacio_kvalitativ(offer_id: int, is_editable: bool, db: Session):
    if not is_editable:
        st.info(
            "Ez a szakasz lezárult – a kalkuláció csak olvasható módban jelenik meg."
        )

    tartalom = crud.get_stage1_tartalom(db, offer_id)
    _CS_OPTIONS = ["Lakossági", "Egyéb"]
    _saved_cs = tartalom.celcsoport if tartalom else None
    _cs_idx = _CS_OPTIONS.index(_saved_cs) if _saved_cs in _CS_OPTIONS else 0
    _cs_col, _ = st.columns([1, 3])
    celcsoport = _cs_col.selectbox(
        "Célcsoport",
        _CS_OPTIONS,
        index=_cs_idx,
        disabled=not is_editable,
        key=f"celcsoport_kvali_{offer_id}",
        help="A kalkulált munkaórák ettől függnek (Executive vs. Szenior sor).",
    )

    st.markdown("#### Kalkuláció – Kvalitatív kutatás")
    st.caption(
        "Blokkokat kapcsold be (checkbox) és töltsd ki a paramétereket. "
        "A jobb oldali munkaóra-bontás folyamatosan újraszámolódik."
    )

    # Session-state-be töltés (perzisztens munka-állapot)
    state_key = f"kvali_kalk_{offer_id}"
    if state_key not in st.session_state:
        record = crud.get_stage1_kalk_kvalitativ(db, offer_id)
        st.session_state[state_key] = _load_state(
            record.params_json if record else None
        )

    state: dict = st.session_state[state_key]
    jobs: list = state["jobs"]

    # Fülek sávja
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
        _render_rekrutalas(p, is_editable, job_key)
        _render_terepmunka(p, is_editable, job_key)
        _render_feldolgozas(p, is_editable, job_key)
        _render_plusz_szolg(p, is_editable, job_key)
        _render_egyeb(p, is_editable, job_key)

    with right:
        # Összesített munkaórák (minden munkafül összege)
        h_total = _new_hours()
        for job_p in jobs:
            h_job = calc_munkaora(job_p, celcsoport)
            for k in h_total:
                h_total[k] += h_job.get(k, 0.0)

        extra_rovid_any = any(
            int(job_p["plusz_szolg"].get("extra_rovid") or 1) == 2 for job_p in jobs
        )
        _render_munkaora_panel(h_total, celcsoport, extra_rovid=extra_rovid_any)
        _render_feldolg_alap_panel(p)
        _render_param_summary_panel(p)

    if is_editable:
        st.divider()
        if st.button(
            "Kalkuláció mentése",
            type="primary",
            key=f"{state_key}_save",
        ):
            errs = _validate_dependents(p.get("feldolgozas", {}))
            if errs:
                st.error(
                    "Mentés sikertelen: a következő tételek önállóan nem "
                    "rendelhetők meg: " + ", ".join(errs)
                )
            else:
                crud.upsert_stage1_tartalom(db, offer_id, {"celcsoport": celcsoport})
                save_data = {
                    "jobs": jobs,
                    "active_job": active_idx,
                }
                crud.upsert_stage1_kalk_kvalitativ(
                    db, offer_id, json.dumps(save_data, ensure_ascii=False)
                )
                st.toast("Kalkuláció mentve!")
