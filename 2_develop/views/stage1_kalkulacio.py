import streamlit as st
from sqlalchemy.orm import Session

from db import crud
from views.stage1_kalkulacio_szemiotika import render_stage1_kalkulacio_szemiotika
from views.stage1_kalkulacio_kvalitativ import render_stage1_kalkulacio_kvalitativ
from views.stage1_kalkulacio_kvantitativ import render_stage1_kalkulacio_kvantitativ
from views.stage1_kalkulacio_tgi import render_stage1_kalkulacio_tgi
from views.stage1_kalkulacio_masodelemzes import render_stage1_kalkulacio_masodelemzes
from views.stage1_kalkulacio_trening import render_stage1_kalkulacio_trening
from views.stage1_kalkulacio_desp import render_stage1_kalkulacio_desp


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
    elif kutatas_tipusa == "Kvalitatív":
        render_stage1_kalkulacio_kvalitativ(offer_id, is_editable, db)
    elif kutatas_tipusa == "Kvantitatív":
        render_stage1_kalkulacio_kvantitativ(offer_id, is_editable, db)
    elif kutatas_tipusa == "TGI":
        render_stage1_kalkulacio_tgi(offer_id, is_editable, db)
    elif kutatas_tipusa == "Másodelemzés":
        render_stage1_kalkulacio_masodelemzes(offer_id, is_editable, db)
    elif kutatas_tipusa == "Tréning":
        render_stage1_kalkulacio_trening(offer_id, is_editable, db)
    elif kutatas_tipusa == "DESP / COCR / SUCL":
        render_stage1_kalkulacio_desp(offer_id, is_editable, db)
    else:
        st.warning(
            f"A(z) „{kutatas_tipusa}” kutatástípushoz tartozó kalkuláció "
            "még nincs implementálva."
        )
