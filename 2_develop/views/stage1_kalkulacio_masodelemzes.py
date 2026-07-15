"""
Szakasz 1 – Kalkuláció: Másodelemzés.

Az Excel (1_documents/masodelemzes.xlsx) alapján képezzük le a paramétereket.

Blokkok:
  1) Kantar márkázott termékek  (Van/Nincs)
  2) Szervezés                  (Van/Nincs – részletek később)
  3) Terepmunka                 (Van/Nincs – részletek később)
  4) DP
  5) Feldolgozás
  6) Plusz szolgáltatások
  7) Egyéb

FIGYELEM – calc_munkaora: az Excel óraértékek még üresek.
Minden munkaóra-képlet PLACEHOLDER (0.0), kitöltendő, amint
az óraszámok megérkeznek.
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

NEM_IGEN = ["0. Nem", "1. Igen"]
NINCS_VAN = ["0. Nincs", "1. Van"]
DP_MELYSEGE_OPTIONS = ["1. Sztenderd", "2. Bonyolult"]
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


# ---------------------------------------------------------------------------
# Alapértelmezett paraméterstruktúra
# ---------------------------------------------------------------------------


def default_params() -> dict:
    return {
        "kantar_markezett": {"active": False},
        "szervezes": {"active": False},
        "terepmunka": {"active": False},
        "dp": {
            "active": False,
            "ugyfel_adatbazis": 0,
            "egyeb_adatbazis": 0,
            "dp_melysege": 1,
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
            "forditas": 0,
            "szinkrontolmacs_ora": 0.0,
            "teremberles": 0,
            "catering": 0,
            "extra_rovid": 1,
            "trening": 0,
        },
        "egyeb": {
            "active": False,
            "munkaora": 0.0,
            "adatbeszerzesi_koltseg": 0.0,
            "egyeb_koltseg": 0.0,
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
    """
    PLACEHOLDER – az Excel óraértékek még nem kerültek megadásra.
    Minden érték 0.0, amíg a tényleges képletek megérkeznek.
    """
    h = _new_hours()

    # TODO: Kantar márkázott termékek – óraszámok még hiányoznak
    # TODO: Szervezés – óraszámok még hiányoznak
    # TODO: Terepmunka – óraszámok még hiányoznak
    # TODO: DP – óraszámok még hiányoznak
    # TODO: Feldolgozás – óraszámok még hiányoznak

    # Extra rövid határidő × 1,2 (ha Plusz aktív)
    ps = p.get("plusz_szolg", {})
    if bool(ps.get("active")) and int(ps.get("extra_rovid") or 1) == 2:
        for k in h:
            h[k] *= 1.2

    # Egyéb extra munkaóra (ha Egyéb aktív)
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
    return []  # TODO: dependency-validáció az óraértékek megadása után


# ---------------------------------------------------------------------------
# UI blokkok
# ---------------------------------------------------------------------------


def _render_kantar_markezett(p: dict, is_editable: bool, kp: str):
    b = p["kantar_markezett"]
    with st.expander("1) Kantar márkázott termékek", expanded=False):
        b["active"] = st.checkbox(
            "Van Kantar márkázott termék",
            value=bool(b.get("active")),
            key=f"{kp}_km_active",
            disabled=not is_editable,
        )
        if b["active"]:
            st.caption(
                "Részletek (pl. termék neve, típusa) – paraméterek feltérképezés alatt."
            )


def _render_szervezes(p: dict, is_editable: bool, kp: str):
    b = p["szervezes"]
    with st.expander("2) Szervezés", expanded=False):
        b["active"] = st.checkbox(
            "Van szervezés",
            value=bool(b.get("active")),
            key=f"{kp}_szev_active",
            disabled=not is_editable,
        )
        if b["active"]:
            st.caption("Részletek – paraméterek feltérképezés alatt.")


def _render_terepmunka(p: dict, is_editable: bool, kp: str):
    b = p["terepmunka"]
    with st.expander("3) Terepmunka", expanded=False):
        b["active"] = st.checkbox(
            "Van terepmunka",
            value=bool(b.get("active")),
            key=f"{kp}_terep_active",
            disabled=not is_editable,
        )
        if b["active"]:
            st.caption("Részletek – paraméterek feltérképezés alatt.")


def _render_dp(p: dict, is_editable: bool, kp: str):
    d = p["dp"]
    with st.expander("4) DP", expanded=False):
        d["active"] = st.checkbox(
            "Van DP",
            value=bool(d.get("active")),
            key=f"{kp}_dp_active",
            disabled=not is_editable,
        )
        if not d["active"]:
            return

        d["ugyfel_adatbazis"] = int(
            st.selectbox(
                "Ügyfél adatbázisának kezelése",
                NEM_IGEN,
                index=int(d.get("ugyfel_adatbazis") or 0),
                key=f"{kp}_dp_ugyfel",
                disabled=not is_editable,
            ).split(".")[0]
        )
        d["egyeb_adatbazis"] = int(
            st.selectbox(
                "Egyéb adatbázis feldolgozása (pl. KSH, Eurostat)",
                NEM_IGEN,
                index=int(d.get("egyeb_adatbazis") or 0),
                key=f"{kp}_dp_egyeb",
                disabled=not is_editable,
            ).split(".")[0]
        )
        d["dp_melysege"] = int(
            st.selectbox(
                "DP mélysége",
                DP_MELYSEGE_OPTIONS,
                index=int(d.get("dp_melysege") or 1) - 1,
                key=f"{kp}_dp_melyseg",
                disabled=not is_editable,
            ).split(".")[0]
        )


def _render_feldolgozas(p: dict, is_editable: bool, kp: str):
    f = p["feldolgozas"]
    with st.expander("5) Feldolgozás", expanded=False):
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
    with st.expander("6) Plusz szolgáltatások", expanded=False):
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


def _render_egyeb(p: dict, is_editable: bool, kp: str):
    eg = p["egyeb"]
    with st.expander("7) Egyéb", expanded=False):
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
        eg["adatbeszerzesi_koltseg"] = st.number_input(
            "Adatbeszerzési / adatvásárlási költség (Ft)",
            min_value=0.0,
            step=1000.0,
            value=float(eg.get("adatbeszerzesi_koltseg") or 0),
            key=f"{kp}_eg_adat_koltseg",
            disabled=not is_editable,
        )
        eg["egyeb_koltseg"] = st.number_input(
            "Egyéb költségelem (Ft)",
            min_value=0.0,
            step=1000.0,
            value=float(eg.get("egyeb_koltseg") or 0),
            key=f"{kp}_eg_egyeb_koltseg",
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
# Jobb oldali panel
# ---------------------------------------------------------------------------


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
        "Számolt munkaóra</div>",
        f"<div style='font-size:0.8rem; color:#5a6b80; margin-bottom:1rem;'>"
        f"Másodelemzés{badge_extra}</div>",
        "<div style='font-size:0.78rem; color:#e07b00; font-style:italic; "
        "margin-bottom:0.8rem;'>⚠️ Placeholder – az óraszámok megadása után aktív</div>",
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
            "margin-left:0.3rem;'>óra</span></div></div>"
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
            f"<span style='color:{val_col}; font-weight:600; font-size:0.95rem;'>{v_disp}"
            + (
                f" <span style='color:#8a96a8; font-weight:500; font-size:0.85rem;'>{unit}</span>"
                if unit
                else ""
            )
            + "</span></div>"
        )

    sections = []

    for key, title in (
        ("kantar_markezett", "Kantar márkázott termékek"),
        ("szervezes", "Szervezés"),
        ("terepmunka", "Terepmunka"),
    ):
        b = p.get(key, {})
        if bool(b.get("active")):
            sections.append((title, [row("Aktív", "Igen")]))

    d = p.get("dp", {})
    if bool(d.get("active")):
        sections.append(
            (
                "DP",
                [
                    row(
                        "Ügyfél adatbázis",
                        NEM_IGEN[int(d.get("ugyfel_adatbazis") or 0)],
                    ),
                    row(
                        "Egyéb adatbázis", NEM_IGEN[int(d.get("egyeb_adatbazis") or 0)]
                    ),
                    row(
                        "DP mélysége",
                        DP_MELYSEGE_OPTIONS[int(d.get("dp_melysege") or 1) - 1],
                    ),
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
                    row("Szinkrontolmács", ps.get("szinkrontolmacs_ora"), "óra"),
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
        or (eg.get("adatbeszerzesi_koltseg") or 0) > 0
        or (eg.get("egyeb_koltseg") or 0) > 0
        or eg.get("megjegyzes")
    ):
        sections.append(
            (
                "Egyéb",
                [
                    row("Egyéb munkaóra", eg.get("munkaora"), "óra"),
                    row("Adatbeszerzési ktg.", eg.get("adatbeszerzesi_koltseg"), "Ft"),
                    row("Egyéb ktg.", eg.get("egyeb_koltseg"), "Ft"),
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


# ---------------------------------------------------------------------------
# Multi-job állapotkezelés
# ---------------------------------------------------------------------------


def _is_job_complete(p: dict) -> bool:
    return bool(p.get("feldolgozas", {}).get("active"))


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
        n = len(state["jobs"])
        state["active_job"] = min(max(0, state["active_job"]), n - 1)
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
        css_rules.append(
            f".st-key-{state_key}_tab_{i} button {{"
            " min-height:1.7rem !important; height:1.7rem !important;"
            " min-width:6.2rem !important; width:6.2rem !important;"
            " max-width:6.2rem !important; padding:0.05rem 0.45rem !important;"
            " font-size:0.82rem !important; font-weight:500 !important;"
            " line-height:1 !important; border-radius:0.3rem !important;"
            f" background-color:{bg} !important; color:{fg} !important;"
            f" border-color:{border} !important;}}"
        )
    for btn_key in (f"{state_key}_add_job", f"{state_key}_del_job"):
        css_rules.append(
            f".st-key-{btn_key} button {{"
            " min-height:1.7rem !important; height:1.7rem !important;"
            " min-width:1.8rem !important; width:1.8rem !important;"
            " max-width:1.8rem !important; padding:0.1rem 0.3rem !important;"
            " font-size:1.05rem !important; line-height:1 !important;"
            " border-radius:0.3rem !important;}"
        )
    if css_rules:
        st.markdown("<style>" + "".join(css_rules) + "</style>", unsafe_allow_html=True)

    if is_editable:
        ic1, ic2, _ = st.columns([0.28, 0.28, 12])
        if ic1.button("✚", key=f"{state_key}_add_job", help="Új munka hozzáadása"):
            state["jobs"].append(default_params())
            state["active_job"] = len(state["jobs"]) - 1
            st.rerun()
        if ic2.button(
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
        if tab_cols[i].button(f"{prefix}Munka {i + 1}", key=f"{state_key}_tab_{i}"):
            state["active_job"] = i
            st.rerun()


# ---------------------------------------------------------------------------
# Fő render
# ---------------------------------------------------------------------------


def render_stage1_kalkulacio_masodelemzes(
    offer_id: int, is_editable: bool, db: Session
):
    if not is_editable:
        st.info(
            "Ez a szakasz lezárult – a kalkuláció csak olvasható módban jelenik meg."
        )

    st.markdown("#### Kalkuláció – Másodelemzés")
    st.caption(
        "Blokkokat kapcsold be (checkbox) és töltsd ki a paraméterekkel. "
        "A jobb oldali munkaóra-bontás folyamatosan újraszámolódik. "
        "⚠️ Az óraszámok még nem kerültek megadásra – a kalkuláció placeholder."
    )

    state_key = f"maso_kalk_{offer_id}"
    if state_key not in st.session_state:
        record = crud.get_stage1_kalk_masodelemzes(db, offer_id)
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
        _render_kantar_markezett(p, is_editable, job_key)
        _render_szervezes(p, is_editable, job_key)
        _render_terepmunka(p, is_editable, job_key)
        _render_dp(p, is_editable, job_key)
        _render_feldolgozas(p, is_editable, job_key)
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
                    "masodelemzes",
                    params_json,
                    saved_by_user_id=st.session_state.get("current_user_id"),
                )
                if changed:
                    crud.upsert_stage1_kalk_masodelemzes(db, offer_id, params_json)
                    st.toast("Másodelemzés kalkuláció mentve!")
                    st.rerun()
                else:
                    st.info(
                        "Nem történt változás a paraméterezésben – mentés kihagyva."
                    )

    history = crud.get_kalk_history(db, offer_id, "masodelemzes")
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
                key=f"hist_radio_{offer_id}_maso",
            )
            if st.button(
                "⬆️ Kiválasztott verzió betöltése",
                key=f"hist_load_{offer_id}_maso",
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
