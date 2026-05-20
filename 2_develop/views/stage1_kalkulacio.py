import streamlit as st
from sqlalchemy.orm import Session

from db import crud
from views.stage1_kalkulacio_szemiotika import render_stage1_kalkulacio_szemiotika


def render_stage1_kalkulacio(offer_id: int, is_editable: bool, db: Session):
    """
    Szakasz 1 – Kalkuláció fül.
    A megjelenítendő kalkulációt a Tartalom fülön kiválasztott
    Kutatás típusa határozza meg.
    """
    tartalom = crud.get_stage1_tartalom(db, offer_id)
    kutatas_tipusa = tartalom.kutatas_tipusa if tartalom else None

    if kutatas_tipusa == "Szemiotika":
        render_stage1_kalkulacio_szemiotika(offer_id, is_editable, db)
    else:
        st.warning(
            f"A(z) „{kutatas_tipusa}” kutatástípushoz tartozó kalkuláció "
            "még nincs implementálva."
        )
