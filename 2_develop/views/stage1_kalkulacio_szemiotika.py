"""
Szakasz 1 – Kalkuláció: Insightment_Szemiotika fül, Feldolgozás blokk.

A felhasználó a Feldolgozás paramétereit adja meg progresszívan
(egy widget csak akkor jelenik meg, ha az előző ki van töltve).
A "Feldolgozási alap" automatikus: 1, ha bármelyik paraméter > 0, különben 0.
A számolt munkaóra-értékek (Executive / Szenior / Kut.ig. / GAD) a jobb
oldali panelen, 2x2 elrendezésben, valós időben jelennek meg.
"""

import streamlit as st
from sqlalchemy.orm import Session

from db import crud

# Sorrend, mező, címke, mértékegység, típus (int/float)
FELDOLGOZAS_PARAMS = [
    ("debrief", "Debrief", "db", "int"),
    ("top_line", "Top-line", "db", "int"),
    ("egyszeru_elemzes", "Egyszerű elemzés", "db", "int"),
    ("melyelemzes", "Mélyelemzés (deepdive report)", "db", "int"),
    ("management_summary", "Management summary", "db", "int"),
    ("prezentacio", "Prezentáció", "db", "int"),
    ("filmkeszites_ora", "Filmkészítés", "óra", "float"),
    ("workshop_ora", "Workshop (workshop hossza)", "óra", "float"),
]


def _calc_feldolgozasi_alap(values: dict) -> int:
    """1, ha bármely Feldolgozás-paraméter > 0; különben 0."""
    for key, _, _, _ in FELDOLGOZAS_PARAMS:
        v = values.get(key)
        if v is not None and v > 0:
            return 1
    return 0


def _calc_munkaora(values: dict, celcsoport: str | None) -> dict:
    """
    Az Insightment_Szemiotika lap 38–47. sorai alapján számolja a 4 szerepkör
    munkaóra-igényét. Lakossági ügyfélnél az Executive sora a "lakossági"
    értéket veszi fel; Egyéb célcsoportnál a Szenior sora kapja meg az
    azonos értékeket. A Kutatási igazgatói és GAD órák minden szegmensben
    azonosak.
    """
    is_lak = celcsoport == "Lakossági"

    debrief = values.get("debrief") or 0
    top_line = values.get("top_line") or 0
    egyszeru = values.get("egyszeru_elemzes") or 0
    mely = values.get("melyelemzes") or 0
    mgmt = values.get("management_summary") or 0
    prez = values.get("prezentacio") or 0
    film = values.get("filmkeszites_ora") or 0
    ws = values.get("workshop_ora") or 0

    exec_h = sen_h = kig_h = gad_h = 0.0

    # Feldolgozási alap (=1 ha bármely paraméter > 0)
    alap = _calc_feldolgozasi_alap(values)
    if alap == 1:
        if is_lak:
            exec_h += 25
        else:
            sen_h += 25
        kig_h += 2
        gad_h += 1

    def _add_segment(per_h: float, count: float):
        nonlocal exec_h, sen_h
        if is_lak:
            exec_h += per_h * count
        else:
            sen_h += per_h * count

    # Debrief – Exec/Szen 2/db, GAD 2/db
    _add_segment(2, debrief)
    gad_h += 2 * debrief

    # Top-line – Exec/Szen 5/db, GAD 1/db
    _add_segment(5, top_line)
    gad_h += 1 * top_line

    # Egyszerű elemzés – Exec/Szen 8/db, GAD 1/db
    _add_segment(8, egyszeru)
    gad_h += 1 * egyszeru

    # Mélyelemzés – Exec/Szen 15/db, Kut.ig. 2/db, GAD 2/db
    _add_segment(15, mely)
    kig_h += 2 * mely
    gad_h += 2 * mely

    # Management summary – Exec/Szen 5/db, Kut.ig. 2/db, GAD 2/db
    _add_segment(5, mgmt)
    kig_h += 2 * mgmt
    gad_h += 2 * mgmt

    # Prezentáció – Exec/Szen 2/db, GAD 2/db
    _add_segment(2, prez)
    gad_h += 2 * prez

    # Filmkészítés – Szenior kapja az óraszámot, GAD 2 fix ha >0
    sen_h += film
    if film > 0:
        gad_h += 2

    # Workshop – minden szerepkör 2 + workshop_óra (ha ws > 0)
    if ws > 0:
        bonus = 2 + ws
        _add_segment(bonus, 1)
        kig_h += bonus
        gad_h += bonus

    return {
        "executive": exec_h,
        "szenior": sen_h,
        "kutatasi_igazgato": kig_h,
        "gad": gad_h,
    }


def _render_munkaora_panel(hours: dict, celcsoport: str | None):
    """Jobb oldali panel – 2x2 elrendezésben a 4 szerepkör munkaórája."""
    cs_label = celcsoport or "—"
    items = [
        ("Executive kutatói munkaóra", hours["executive"]),
        ("Szenior kutatói munkaóra", hours["szenior"]),
        ("Kutatási igazgatói munkaóra", hours["kutatasi_igazgato"]),
        ("GAD munkaóra", hours["gad"]),
    ]

    panel_html = [
        "<div style='border:1px solid #d6dde8; border-radius:8px; padding:1rem; "
        "background:#f7f9fc;'>",
        "<div style='font-size:0.85rem; color:#0b3d91; font-weight:600; "
        "letter-spacing:0.04em; text-transform:uppercase; margin-bottom:0.25rem;'>"
        "Számolt munkaóra</div>",
        f"<div style='font-size:0.8rem; color:#5a6b80; margin-bottom:1rem;'>"
        f"Célcsoport: <b>{cs_label}</b></div>",
        "<div style='display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;'>",
    ]
    for label, value in items:
        v_str = (
            f"{value:.1f}"
            if isinstance(value, float) and value % 1
            else f"{int(value)}"
        )
        panel_html.append(
            "<div style='background:#ffffff; border:1px solid #e3e8f0; "
            "border-radius:6px; padding:0.7rem 0.8rem;'>"
            f"<div style='font-size:0.78rem; color:#5a6b80; line-height:1.2; "
            f"min-height:2.4em;'>{label}</div>"
            f"<div style='font-size:1.9rem; font-weight:700; color:#0b3d91; "
            f"line-height:1.1; margin-top:0.3rem;'>{v_str}"
            "<span style='font-size:0.75rem; font-weight:500; color:#5a6b80; "
            "margin-left:0.35rem;'>munkaóra</span></div>"
            "</div>"
        )
    panel_html.append("</div></div>")
    st.markdown("".join(panel_html), unsafe_allow_html=True)


def _render_summary_panel(values: dict):
    """Paraméterek összegző listája – a munkaóra panel alá."""
    rows = []
    for key, label, unit, _ in FELDOLGOZAS_PARAMS:
        v = values.get(key)
        v_str = "—" if v is None else (f"{v:g}")
        rows.append(
            "<div style='display:flex; justify-content:space-between; "
            "padding:0.35rem 0.6rem; border-bottom:1px solid #eef0f4;'>"
            f"<span style='color:#3a4658; font-size:0.85rem;'>{label}</span>"
            f"<span style='color:#0b3d91; font-weight:600; font-size:0.9rem;'>"
            f"{v_str} <span style='color:#8a96a8; font-weight:500;'>{unit}</span>"
            "</span></div>"
        )
    alap = _calc_feldolgozasi_alap(values)
    alap_label = "1 – Igen" if alap == 1 else "0 – Nem"
    rows.append(
        "<div style='display:flex; justify-content:space-between; "
        "padding:0.5rem 0.6rem; margin-top:0.3rem; background:#eef3fb; "
        "border-radius:6px;'>"
        "<span style='color:#0b3d91; font-weight:600; font-size:0.85rem;'>"
        "Feldolgozási alap (automatikus)</span>"
        f"<span style='color:#0b3d91; font-weight:700; font-size:0.9rem;'>{alap_label}</span>"
        "</div>"
    )
    st.markdown(
        "<div style='border:1px solid #d6dde8; border-radius:8px; padding:0.8rem; "
        "background:#ffffff; margin-top:1rem;'>"
        "<div style='font-size:0.85rem; color:#0b3d91; font-weight:600; "
        "letter-spacing:0.04em; text-transform:uppercase; margin-bottom:0.6rem;'>"
        "Paraméterek összegzése</div>" + "".join(rows) + "</div>",
        unsafe_allow_html=True,
    )


def render_stage1_kalkulacio_szemiotika(offer_id: int, is_editable: bool, db: Session):
    if not is_editable:
        st.info(
            "Ez a szakasz lezárult – a kalkuláció csak olvasható módban jelenik meg."
        )

    # Célcsoport beolvasása a Tartalom fülről
    tartalom = crud.get_stage1_tartalom(db, offer_id)
    celcsoport = tartalom.celcsoport if tartalom else None
    if not celcsoport:
        st.warning(
            "A kalkulációhoz előbb add meg a Célcsoportot a Tartalom fülön "
            "(Lakossági / Egyéb)."
        )
        return

    st.markdown("#### Kalkuláció – Szemiotika / Feldolgozás")
    st.caption(
        "Add meg a Feldolgozás paramétereit. Egy mező csak akkor jelenik meg, "
        "ha az előzőt megerősítetted. A „Feldolgozási alap” és a jobb oldali "
        "munkaóra-értékek automatikusan számolódnak."
    )

    record = crud.get_stage1_kalk_szemiotika(db, offer_id)

    # Aktuális (még nem mentett) értékek session_state-ben
    state_key = f"szem_kalk_{offer_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            key: (getattr(record, key) if record else None)
            for key, _, _, _ in FELDOLGOZAS_PARAMS
        }

    values: dict = st.session_state[state_key]

    # Eldöntjük, hogy az összes paraméter már rögzítve van-e – ha igen,
    # az adatbeviteli expandert alapból összecsukva jelenítjük meg.
    confirm_keys = [
        f"confirmed_{state_key}_{k}" for k, _, _, _ in FELDOLGOZAS_PARAMS[:-1]
    ]
    all_confirmed = all(
        st.session_state.get(ck, False) or values.get(k) is not None
        for ck, (k, _, _, _) in zip(confirm_keys, FELDOLGOZAS_PARAMS[:-1])
    )
    expander_state_key = f"expander_open_{state_key}"
    if expander_state_key not in st.session_state:
        st.session_state[expander_state_key] = not all_confirmed

    # ── Két oszlop: bal = widgetek (1/3 szélesség), jobb = munkaóra panel ──
    left_col, right_col = st.columns([1, 2])

    with left_col:
        with st.expander(
            "Feldolgozás paraméterei",
            expanded=st.session_state[expander_state_key],
        ):
            show_next = True
            for idx, (key, label, unit, vtype) in enumerate(FELDOLGOZAS_PARAMS):
                if not show_next:
                    break

                current = values.get(key)
                widget_key = f"w_{state_key}_{key}"

                help_txt = (
                    "Önállóan megrendelhető."
                    if key not in ("management_summary", "prezentacio")
                    else "Önállóan nem megrendelhető – mellé legalább még egy elemet ki kell választani."
                )

                if vtype == "int":
                    new_val = st.number_input(
                        f"{idx + 1}. {label} ({unit})",
                        min_value=0,
                        step=1,
                        value=int(current) if current is not None else 0,
                        key=widget_key,
                        disabled=not is_editable,
                        help=help_txt,
                    )
                else:
                    new_val = st.number_input(
                        f"{idx + 1}. {label} ({unit})",
                        min_value=0.0,
                        step=0.5,
                        value=float(current) if current is not None else 0.0,
                        key=widget_key,
                        disabled=not is_editable,
                    )
                values[key] = new_val

                if idx == len(FELDOLGOZAS_PARAMS) - 1:
                    break

                confirmed_key = f"confirmed_{state_key}_{key}"
                default_confirmed = current is not None or st.session_state.get(
                    confirmed_key, False
                )
                confirmed = st.checkbox(
                    f"„{label}” érték rögzítve",
                    value=default_confirmed,
                    key=confirmed_key,
                    disabled=not is_editable,
                )
                if not confirmed:
                    show_next = False
                    st.caption("A következő paraméter megjelenítéséhez pipáld be.")

                st.divider()

        # Ha minden paraméter már be van pipálva, ajánljuk fel a becsukást
        if all_confirmed and st.session_state[expander_state_key]:
            if st.button(
                "Paraméterek összecsukása",
                key=f"collapse_{state_key}",
                use_container_width=True,
            ):
                st.session_state[expander_state_key] = False
                st.rerun()
        elif not st.session_state[expander_state_key]:
            if st.button(
                "Paraméterek szerkesztése",
                key=f"expand_{state_key}",
                use_container_width=True,
            ):
                st.session_state[expander_state_key] = True
                st.rerun()

    with right_col:
        hours = _calc_munkaora(values, celcsoport)
        _render_munkaora_panel(hours, celcsoport)
        _render_summary_panel(values)

    # Mentés gomb (a két oszlop alatt, teljes szélességben balra)
    st.divider()
    col_save, _ = st.columns([2, 5])
    if is_editable:
        if col_save.button("Mentés", type="primary", key=f"save_{state_key}"):
            crud.upsert_stage1_kalk_szemiotika(db, offer_id, values)
            st.toast("Kalkuláció mentve!")
            st.rerun()
    else:
        col_save.button("Mentés", disabled=True, key=f"save_{state_key}_dis")
