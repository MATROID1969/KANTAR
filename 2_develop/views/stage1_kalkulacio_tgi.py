"""
Szakasz 1 – Kalkuláció: TGI (Target Group Index).

A TGI lap (1_documents/TGI.xlsx) alapján képezzük le a paramétereket
és a hozzájuk tartozó munkaóra-képleteket.

Blokkok:
  1) Adatbázis & Feldolgozás
  2) Workshop
  3) Analytics (Advance Statistics / Szegmentáció / Modellezés)
  4) Plusz szolgáltatások
  5) Egyéb

Megjegyzések:
  - Egyszerű elemzés / Mélyelemzés mellé automatikusan hozzáadódnak a
    Táblariport munkaórái (per db).
  - Management summary és Prezentáció önállóan nem rendelhetők meg.
  - Segident csak Modellezés=1 esetén rendelhető meg.
  - Adatbázis-típusok egyedileg árazandók (min. 1 000 000 Ft) – a munkaóra
    mégis megjelenik az összesítésben.
"""

from __future__ import annotations

import json
from typing import Optional

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from db import crud

# ---------------------------------------------------------------------------
# Konstansok
# ---------------------------------------------------------------------------

ADATBAZIS_OPTIONS = [
    "0. Nincs",
    "1. Standard form – 1 év",
    "2. SPSS – 1 év",
    "3. Speciális változókkal kiegészítve",
    "4. Egyéb",
]

ANALYTICS_OPTIONS = ["0. Nincs", "1. Van"]
NEM_IGEN = ["0. Nem", "1. Igen"]
FORDITAS_OPTIONS = [
    "0. Nincs",
    "1. Fordítóval",
    "2. Fordítóval, lektorálva",
    "3. Szoftverrel",
]
EXTRA_ROVID_OPTIONS = ["1. Normál", "2. Extra rövid (1,2× szorzó)"]

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

# Táblariport alap-munkaóra (× db, minden Táblariport-alapú sorhoz hozzáadódik)
_TABLARIPORT_H = {
    "dp": 8,
    "dp_vez": 0,
    "junior_kut": 4,
    "executive_kut": 4,
    "gad": 1,
}

# Analytics lookup (xlsx 14–19. sorok)
_ANALYTICS_LOOKUP = {
    "advance_statistics": {"dp": 30, "szenior_kut": 15, "kut_ig": 2, "gad": 1},
    "szegmentacio": {"dp": 20, "szenior_kut": 15, "kut_ig": 2, "gad": 1},
    "modellezes": {"dp": 20, "szenior_kut": 15, "kut_ig": 2, "gad": 1},
}


# ---------------------------------------------------------------------------
# Alapértelmezett paraméterstruktúra
# ---------------------------------------------------------------------------


def default_params() -> dict:
    return {
        "feldolgozas": {
            "active": False,
            "adatbazis_szintaxis": 0,
            "adatbazis_szintaxis_ar": 0,
            "szoftver_adatbazis": 0,
            "szoftver_adatbazis_ar": 0,
            "tablariport": 0,
            "egyszeru_elemzes": 0,
            "melyelemzes": 0,
            "management_summary": 0,
            "prezentacio": 0,
            "segident": 0,
            "workshop_ora": 0.0,
        },
        "analytics": {
            "advance_statistics": 0,
            "szegmentacio": 0,
            "modellezes": 0,
        },
        "plusz_szolg": {
            "active": False,
            "forditas": 0,
            "forditas_ora": 0.0,
            "teremberles": 0,
            "catering": 0,
            "extra_rovid": 1,
            "trening": 0,
        },
        "egyeb": {
            "active": False,
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


def calc_munkaora(p: dict) -> dict:
    h = _new_hours()
    f = p.get("feldolgozas", {})
    feld_active = bool(f.get("active"))

    if feld_active:
        # 1) Adatbázis (és syntax): flat hours ha kiválasztva (> 0)
        if int(f.get("adatbazis_szintaxis") or 0) > 0:
            _add(h, "dp", 3)
            _add(h, "dp_vez", 3)
            _add(h, "gad", 5)

        # 2) Szoftverben elérhető adatbázis: flat hours ha kiválasztva
        if int(f.get("szoftver_adatbazis") or 0) > 0:
            _add(h, "dp", 3)
            _add(h, "dp_vez", 3)
            _add(h, "gad", 10)

        # 3) Táblariport × db
        tabl = float(f.get("tablariport") or 0)
        if tabl > 0:
            for cat, v in _TABLARIPORT_H.items():
                _add(h, cat, tabl * v)

        # 4) Egyszerű elemzés × db  (+ táblariport/db)
        egysz = float(f.get("egyszeru_elemzes") or 0)
        if egysz > 0:
            _add(h, "dp", egysz * 4)
            _add(h, "junior_kut", egysz * 5)
            _add(h, "executive_kut", egysz * 5)
            _add(h, "kut_ig", egysz * 0.5)
            _add(h, "gad", egysz * 2)
            for cat, v in _TABLARIPORT_H.items():
                _add(h, cat, egysz * v)

        # 5) Mélyelemzés × db  (+ táblariport/db)
        mely = float(f.get("melyelemzes") or 0)
        if mely > 0:
            _add(h, "dp", mely * 10)
            _add(h, "dp_vez", mely * 4)
            _add(h, "junior_kut", mely * 10)
            _add(h, "executive_kut", mely * 25)
            _add(h, "szenior_kut", mely * 5)
            _add(h, "kut_ig", mely * 2)
            _add(h, "gad", mely * 2)
            for cat, v in _TABLARIPORT_H.items():
                _add(h, cat, mely * v)

        # 6) Management summary × db
        mgmt = float(f.get("management_summary") or 0)
        if mgmt > 0:
            _add(h, "szenior_kut", mgmt * 5)
            _add(h, "kut_ig", mgmt * 2)
            _add(h, "gad", mgmt * 2)

        # 7) Prezentáció × db
        prez = float(f.get("prezentacio") or 0)
        if prez > 0:
            _add(h, "szenior_kut", prez * 2)
            _add(h, "gad", prez * 2)

        # 8) Segident / modellezés × db  (csak Modellezés=1 esetén)
        segident = float(f.get("segident") or 0)
        if segident > 0:
            _add(h, "dp", segident * 8)
            _add(h, "szenior_kut", segident * 1)

        # 9) Workshop: Szenior / Kut.ig. / GAD = 2 + workshop_óra
        ws_ora = float(f.get("workshop_ora") or 0)
        if ws_ora > 0:
            _add(h, "szenior_kut", 2 + ws_ora)
            _add(h, "kut_ig", 2 + ws_ora)
            _add(h, "gad", 2 + ws_ora)

    # 10) Analytics (mindig számol)
    a = p.get("analytics", {})
    for key, hours in _ANALYTICS_LOOKUP.items():
        if int(a.get(key) or 0) == 1:
            for cat, v in hours.items():
                _add(h, cat, v)

    # 11) Extra rövid határidő ×1,2 (csak ha plusz aktiválva)
    ps = p.get("plusz_szolg", {})
    if bool(ps.get("active")) and int(ps.get("extra_rovid") or 1) == 2:
        for k in h:
            h[k] *= 1.2

    # 12) Egyéb extra munkaóra (csak ha egyéb aktiválva)
    eg = p.get("egyeb", {})
    if bool(eg.get("active")):
        extra = float(eg.get("munkaora") or 0)
        if extra > 0:
            _add(h, "szervezoi", extra)

    return h


# ---------------------------------------------------------------------------
# Validáció
# ---------------------------------------------------------------------------


def _validate(p: dict) -> list[str]:
    errs: list[str] = []
    f = p.get("feldolgozas", {})
    a = p.get("analytics", {})

    if not bool(f.get("active")):
        return errs

    # Management summary / Prezentáció: önállóan nem rendelhető
    sibling_keys = ("tablariport", "egyszeru_elemzes", "melyelemzes", "segident")
    has_analysis = any((f.get(k) or 0) > 0 for k in sibling_keys)
    for key, label in (
        ("management_summary", "Management summary"),
        ("prezentacio", "Prezentáció"),
    ):
        if (f.get(key) or 0) > 0 and not has_analysis:
            errs.append(f"{label} (önállóan nem rendelhető meg)")

    # Segident csak Modellezés=1 esetén
    if (f.get("segident") or 0) > 0 and int(a.get("modellezes") or 0) != 1:
        errs.append("Segident / modellezés (csak Modellezés=1 esetén rendelhető)")

    return errs


# ---------------------------------------------------------------------------
# UI blokkok
# ---------------------------------------------------------------------------


def _render_feldolgozas(p: dict, is_editable: bool, kp: str):
    f = p["feldolgozas"]
    with st.expander("1) Feldolgozás", expanded=False):
        f["active"] = st.checkbox(
            "Van feldolgozás",
            value=bool(f.get("active")),
            key=f"{kp}_feld_active",
            disabled=not is_editable,
        )
        if not f["active"]:
            return

        st.caption(
            "Management summary és Prezentáció önállóan nem rendelhetők meg. "
            "Segident csak Modellezés=1 esetén rendelhető."
        )

        col_sel, col_ar = st.columns([2, 1])
        f["adatbazis_szintaxis"] = int(
            col_sel.selectbox(
                "Adatbázis (és syntax) átadás – 1 év",
                ADATBAZIS_OPTIONS,
                index=int(f.get("adatbazis_szintaxis") or 0),
                key=f"{kp}_feld_adat_szint",
                disabled=not is_editable,
                help="DP=3 óra, DP vez.=3 óra, GAD=5 óra (fix)",
            ).split(".")[0]
        )
        if int(f.get("adatbazis_szintaxis") or 0) > 0:
            f["adatbazis_szintaxis_ar"] = col_ar.number_input(
                "Ár (Ft)",
                min_value=1_000_000,
                step=100_000,
                value=int(f.get("adatbazis_szintaxis_ar") or 1_000_000),
                key=f"{kp}_feld_adat_szint_ar",
                disabled=not is_editable,
                help="Min. 1 000 000 Ft – kalkulációtól független",
            )

        col_sel2, col_ar2 = st.columns([2, 1])
        f["szoftver_adatbazis"] = int(
            col_sel2.selectbox(
                "Szoftverben elérhető adatbázis – 1 év",
                ADATBAZIS_OPTIONS,
                index=int(f.get("szoftver_adatbazis") or 0),
                key=f"{kp}_feld_adat_szoftver",
                disabled=not is_editable,
                help="DP=3 óra, DP vez.=3 óra, GAD=10 óra (fix)",
            ).split(".")[0]
        )
        if int(f.get("szoftver_adatbazis") or 0) > 0:
            f["szoftver_adatbazis_ar"] = col_ar2.number_input(
                "Ár (Ft)",
                min_value=1_000_000,
                step=100_000,
                value=int(f.get("szoftver_adatbazis_ar") or 1_000_000),
                key=f"{kp}_feld_szoftver_ar",
                disabled=not is_editable,
                help="Min. 1 000 000 Ft – kalkulációtól független",
            )

        st.divider()

        for key, label in (
            ("tablariport", "Táblariport (db)"),
            ("egyszeru_elemzes", "Egyszerű elemzés (db)  +  táblariport/db"),
            ("melyelemzes", "Mélyelemzés / deepdive report (db)  +  táblariport/db"),
            (
                "management_summary",
                "Management summary (db)  –  önállóan nem rendelhető",
            ),
            ("prezentacio", "Prezentáció (db)  –  önállóan nem rendelhető"),
            ("segident", "Segident / modellezés (db)  –  csak Modellezés=1 esetén"),
        ):
            f[key] = st.number_input(
                label,
                min_value=0,
                step=1,
                value=int(f.get(key) or 0),
                key=f"{kp}_feld_f_{key}",
                disabled=not is_editable,
            )

        st.divider()

        f["workshop_ora"] = st.number_input(
            "Workshop hossza (óra)",
            min_value=0.0,
            step=0.5,
            value=float(f.get("workshop_ora") or 0),
            key=f"{kp}_feld_ws_ora",
            disabled=not is_editable,
            help="Szenior = Kut.ig. = GAD = 2 + workshop_óra",
        )


def _render_analytics(p: dict, is_editable: bool, kp: str):
    a = p["analytics"]
    with st.expander("2) Analytics", expanded=False):
        for key, label in (
            ("advance_statistics", "Advance Statistics"),
            ("szegmentacio", "Szegmentáció"),
            ("modellezes", "Modellezés"),
        ):
            a[key] = int(
                st.selectbox(
                    label,
                    ANALYTICS_OPTIONS,
                    index=int(a.get(key) or 0),
                    key=f"{kp}_a_{key}",
                    disabled=not is_editable,
                ).split(".")[0]
            )


def _render_plusz(p: dict, is_editable: bool, kp: str):
    ps = p["plusz_szolg"]
    with st.expander("3) Plusz szolgáltatások", expanded=False):
        ps["active"] = st.checkbox(
            "Van plusz szolgáltatás",
            value=bool(ps.get("active")),
            key=f"{kp}_ps_active",
            disabled=not is_editable,
        )
        if not ps["active"]:
            return

        ps["forditas"] = int(
            st.selectbox(
                "Fordítás",
                FORDITAS_OPTIONS,
                index=int(ps.get("forditas") or 0),
                key=f"{kp}_ps_ford",
                disabled=not is_editable,
            ).split(".")[0]
        )
        if int(ps.get("forditas") or 0) > 0:
            ps["forditas_ora"] = st.number_input(
                "Fordítandó anyag terjedelme (óra)",
                min_value=0.0,
                step=0.5,
                value=float(ps.get("forditas_ora") or 0),
                key=f"{kp}_ps_ford_ora",
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


def _render_egyeb(p: dict, is_editable: bool, kp: str):
    eg = p["egyeb"]
    with st.expander("4) Egyéb", expanded=False):
        eg["active"] = st.checkbox(
            "Van egyéb tétel",
            value=bool(eg.get("active")),
            key=f"{kp}_eg_active",
            disabled=not is_editable,
        )
        if not eg["active"]:
            return

        eg["munkaora"] = st.number_input(
            "Extra munkaóra (Szervezőire kerül)",
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

    f = p.get("feldolgozas", {})
    if bool(f.get("active")):
        adat_szint_idx = int(f.get("adatbazis_szintaxis") or 0)
        szoftver_idx = int(f.get("szoftver_adatbazis") or 0)
        feld_rows = [
            row(
                "Adatbázis (syntax) típus",
                (
                    ADATBAZIS_OPTIONS[adat_szint_idx]
                    if adat_szint_idx < len(ADATBAZIS_OPTIONS)
                    else "—"
                ),
            ),
            row(
                "Szoftver adatbázis típus",
                (
                    ADATBAZIS_OPTIONS[szoftver_idx]
                    if szoftver_idx < len(ADATBAZIS_OPTIONS)
                    else "—"
                ),
            ),
            row("Táblariport", f.get("tablariport"), "db"),
            row("Egyszerű elemzés", f.get("egyszeru_elemzes"), "db"),
            row("Mélyelemzés (deepdive)", f.get("melyelemzes"), "db"),
            row("Management summary", f.get("management_summary"), "db"),
            row("Prezentáció", f.get("prezentacio"), "db"),
            row("Segident / modellezés", f.get("segident"), "db"),
            row("Workshop hossza", f.get("workshop_ora"), "óra"),
        ]
        sections.append(("Feldolgozás", feld_rows))

    a = p.get("analytics", {})
    if any(int(a.get(k) or 0) == 1 for k in a):
        sections.append(
            (
                "Analytics",
                [
                    row(
                        "Advance Statistics",
                        ANALYTICS_OPTIONS[int(a.get("advance_statistics") or 0)],
                    ),
                    row(
                        "Szegmentáció",
                        ANALYTICS_OPTIONS[int(a.get("szegmentacio") or 0)],
                    ),
                    row("Modellezés", ANALYTICS_OPTIONS[int(a.get("modellezes") or 0)]),
                ],
            )
        )

    ps = p.get("plusz_szolg", {})
    if bool(ps.get("active")):
        ford_idx = int(ps.get("forditas") or 0)
        sections.append(
            (
                "Plusz szolgáltatások",
                [
                    row(
                        "Fordítás",
                        (
                            FORDITAS_OPTIONS[ford_idx]
                            if ford_idx < len(FORDITAS_OPTIONS)
                            else "—"
                        ),
                    ),
                    row("Fordítás terjedelme", ps.get("forditas_ora"), "óra"),
                    row("Terembérlés", NEM_IGEN[int(ps.get("teremberles") or 0)]),
                    row("Catering", NEM_IGEN[int(ps.get("catering") or 0)]),
                    row(
                        "Extra rövid",
                        EXTRA_ROVID_OPTIONS[int(ps.get("extra_rovid") or 1) - 1],
                    ),
                    row("Tréning", NEM_IGEN[int(ps.get("trening") or 0)]),
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
                    row("Egyéb költség", eg.get("koltseg"), "Ft"),
                    row("Megjegyzés", eg.get("megjegyzes") or "—"),
                ],
            )
        )

    if not sections:
        return

    html_parts = []
    for title, rows_html in sections:
        html_parts.append(
            "<div style='margin-bottom:0.8rem;'>"
            "<div style='font-size:0.78rem; color:#0b3d91; font-weight:700; "
            "letter-spacing:0.04em; text-transform:uppercase; margin-bottom:0.3rem;'>"
            f"{title}</div>"
            "<div style='border:1px solid #e3e8f0; border-radius:6px; overflow:hidden;'>"
            + "".join(rows_html)
            + "</div></div>"
        )

    with st.expander("Paraméterek összegzése", expanded=False):
        st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_munkaora_panel(h: dict, extra_rovid: bool = False):
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
        "Számolt munkаóra</div>",
        f"<div style='font-size:0.8rem; color:#5a6b80; margin-bottom:1rem;'>"
        f"TGI kutatás{badge_extra}</div>",
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


# ---------------------------------------------------------------------------
# Multi-job állapotkezelés
# ---------------------------------------------------------------------------


def _is_job_complete(p: dict) -> bool:
    """Egy munkáfül 'kitöltött' (zöld), ha a Feldolgozás blokk aktiválva van."""
    return bool(p.get("feldolgozas", {}).get("active"))


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
            raw_jobs = [loaded]
        jobs = []
        for raw in raw_jobs:
            base = default_params()
            if isinstance(raw, dict):
                # Migráció: régi adatbazis/workshop struktúráról új feldolgozas-ra
                if "feldolgozas" not in raw and (
                    "adatbazis" in raw or "workshop" in raw
                ):
                    jobs.append(base)
                    continue
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
    """Munkáfül-sáv (pontosan a kvantitatív mintájára)."""
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
    for btn_key in (f"{state_key}_add_job", f"{state_key}_del_job"):
        css_rules.append(
            f".st-key-{btn_key} button {{"
            " min-height: 1.7rem !important; height: 1.7rem !important;"
            " min-width: 1.8rem !important; width: 1.8rem !important;"
            " max-width: 1.8rem !important;"
            " padding: 0.1rem 0.3rem !important;"
            " font-size: 1.05rem !important;"
            " line-height: 1 !important; border-radius: 0.3rem !important;"
            "}"
        )
    if css_rules:
        st.markdown("<style>" + "".join(css_rules) + "</style>", unsafe_allow_html=True)

    if is_editable:
        icon_c1, icon_c2, _ = st.columns([0.28, 0.28, 12])
        if icon_c1.button("✚", key=f"{state_key}_add_job", help="Új munka hozzáadása"):
            state["jobs"].append(default_params())
            state["active_job"] = len(state["jobs"]) - 1
            st.rerun()
        if icon_c2.button(
            "✂",
            key=f"{state_key}_del_job",
            help=f"Munka {active + 1} törlése",
            disabled=n <= 1,
        ):
            state["jobs"].pop(active)
            state["active_job"] = max(0, active - 1)
            st.rerun()

    tab_cols = st.columns([1] * n + [12], vertical_alignment="center")
    for i in range(n):
        prefix = "✓ " if complete_flags[i] else ""
        label = f"{prefix}Munka {i + 1}"
        if tab_cols[i].button(label, key=f"{state_key}_tab_{i}"):
            state["active_job"] = i
            st.rerun()


# ---------------------------------------------------------------------------
# Fő render
# ---------------------------------------------------------------------------


def render_stage1_kalkulacio_tgi(offer_id: int, is_editable: bool, db: Session):
    if not is_editable:
        st.info(
            "Ez a szakasz lezárult – a kalkuláció csak olvasható módban jelenik meg."
        )

    st.markdown("#### Kalkuláció – TGI")
    st.caption(
        "Blokkokat kapcsold be (checkbox) és töltsd ki a paraméterekkel. "
        "A jobb oldali munkaóra-bontás folyamatosan újraszámolodik."
    )

    state_key = f"tgi_kalk_{offer_id}"
    if state_key not in st.session_state:
        record = crud.get_stage1_kalk_tgi(db, offer_id)
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

    errs = _validate(p)

    left_col, right_col = st.columns([3, 2])

    with left_col:
        _render_feldolgozas(p, is_editable, job_key)
        _render_analytics(p, is_editable, job_key)
        _render_plusz(p, is_editable, job_key)
        _render_egyeb(p, is_editable, job_key)

        if errs:
            st.error("Figyelem: " + "; ".join(errs))

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
        if st.button(
            "Kalkuláció mentése",
            type="primary",
            key=f"{state_key}_save",
        ):
            if errs:
                st.error("Mentés sikertelen: " + "; ".join(errs))
            else:
                save_data = {"jobs": jobs, "active_job": active_idx}
                params_json = json.dumps(save_data, ensure_ascii=False)
                changed = crud.save_kalk_history(
                    db,
                    offer_id,
                    "tgi",
                    params_json,
                    saved_by_user_id=st.session_state.get("current_user_id"),
                )
                if changed:
                    crud.upsert_stage1_kalk_tgi(db, offer_id, params_json)
                    st.toast("TGI kalkuláció mentve!")
                    st.rerun()
                else:
                    st.info(
                        "Nem történt változás a paraméterezésben – mentés kihagyva."
                    )

    history = crud.get_kalk_history(db, offer_id, "tgi")
    if history:
        with st.expander(f"📋 Kalkuláció-verziók ({len(history)} db)"):
            labels = [
                f"V{len(history) - i}  –  {hist.saved_at.strftime('%Y-%m-%d %H:%M')}  –  "
                f"{hist.saved_by.nev if hist.saved_by else '—'}"
                for i, hist in enumerate(history)
            ]
            selected_label = st.radio(
                "Betöltendő verzió:",
                labels,
                index=0,
                key=f"hist_radio_{offer_id}_tgi",
            )
            if st.button(
                "⬆️ Kiválasztott verzió betöltése",
                key=f"hist_load_{offer_id}_tgi",
                disabled=not is_editable,
                help="Betöltés után az aktuális paraméterek felülíródnak. "
                "Ha meg akarod tartani, nyomj rá a Mentés gombra.",
            ):
                selected_idx = labels.index(selected_label)
                st.session_state[state_key] = _load_state(
                    history[selected_idx].params_json
                )
                st.toast(
                    "Korábbi verzió betöltve – ellenőrizd, majd ments, ha megtartod!"
                )
                st.rerun()
