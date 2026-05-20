"""
Kezdeti adatok feltöltése az adatbázisba.
Futtatás: python seed_data.py  (a 2_develop/ mappából)
Idempotens: többször futtatható, nem hoz létre duplikátumokat.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db, get_session
from db.models import User, Client


def seed():
    init_db()
    db = get_session()

    # ── Felhasználók ─────────────────────────────────────────────────────────
    users_to_seed = [
        {
            "id": 1,
            "nev": "Developer User",
            "email": "dev@kantar.hu",
            "szerepkor": "admin",
        },
        {
            "id": 2,
            "nev": "Kiss Anna (GAD)",
            "email": "kiss.anna@kantar.hu",
            "szerepkor": "GAD",
        },
        {
            "id": 3,
            "nev": "Nagy Péter (Pénzügy)",
            "email": "nagy.peter@kantar.hu",
            "szerepkor": "penzugy",
        },
    ]

    for u_data in users_to_seed:
        exists = db.query(User).filter(User.email == u_data["email"]).first()
        if not exists:
            user = User(**u_data)
            db.add(user)
            print(f"  ✅ User hozzáadva: {u_data['nev']}")
        else:
            print(f"  ⏭  User már létezik: {u_data['nev']}")

    # ── Ügyfelek ─────────────────────────────────────────────────────────────
    clients_to_seed = [
        {"nev": "Magyar Telekom", "kategoria": "Hazai ügyfél"},
        {"nev": "Tesco Magyarország", "kategoria": "Hazai ügyfél"},
        {"nev": "OTP Bank", "kategoria": "Hazai ügyfél"},
        {"nev": "SPAR Magyarország", "kategoria": "Hazai ügyfél"},
        {"nev": "MVM Group", "kategoria": "Hazai ügyfél"},
        {"nev": "Henkel", "kategoria": "Nemzetközi ügyfél"},
        {"nev": "Unilever", "kategoria": "Nemzetközi ügyfél"},
    ]

    for c_data in clients_to_seed:
        exists = db.query(Client).filter(Client.nev == c_data["nev"]).first()
        if not exists:
            client = Client(**c_data)
            db.add(client)
            print(f"  ✅ Ügyfél hozzáadva: {c_data['nev']}")
        else:
            print(f"  ⏭  Ügyfél már létezik: {c_data['nev']}")

    db.commit()
    db.close()
    print("\n✔ Seed kész.")


if __name__ == "__main__":
    print("Adatbázis inicializálás és seed adatok feltöltése...\n")
    seed()
