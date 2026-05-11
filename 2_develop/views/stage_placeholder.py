import streamlit as st

STAGE_NAMES = {
    2: "Ajánlat véglegesítés",
    3: "Megvalósítás",
    4: "Számlázás",
}


def render_stage_placeholder(stage_num: int, offer):
    name = STAGE_NAMES.get(stage_num, f"Szakasz {stage_num}")

    if offer.current_stage < stage_num:
        # Még nem érkezett ide az ajánlat
        st.markdown(
            f"""
            <div style="text-align:center; padding: 3rem 1rem; color: #888;">
                <h2 style="color:#bbb;">Szakasz {stage_num} – {name}</h2>
                <p>Ez a szakasz akkor válik aktívvá, ha az előző szakasz lezárult.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif offer.current_stage == stage_num:
        # Aktív szakasz, de még nincs implementálva
        st.info(
            f"**Szakasz {stage_num} – {name}** jelenleg fejlesztés alatt van. "
            "Hamarosan elérhető lesz."
        )
        # Metaadatok – ki vette át és mikor
        if offer.handoffs:
            last_handoff = offer.handoffs[-1]
            st.caption(
                f"Átvette: **{last_handoff.to_user.nev}**  |  "
                f"Átadás időpontja: {last_handoff.handoff_at.strftime('%Y-%m-%d %H:%M')}"
            )
            if last_handoff.megjegyzes:
                st.caption(f"Megjegyzés az átadáskor: *{last_handoff.megjegyzes}*")

    else:
        # Már lezárt korábbi szakasz – csak tájékoztatás
        st.success(f"**Szakasz {stage_num} – {name}** lezárult.")
        if offer.handoffs:
            relevant = [h for h in offer.handoffs if h.from_stage == stage_num]
            if relevant:
                h = relevant[0]
                st.caption(
                    f"Lezárta: **{h.from_user.nev}** → átadta: **{h.to_user.nev}**  |  "
                    f"{h.handoff_at.strftime('%Y-%m-%d %H:%M')}"
                )
