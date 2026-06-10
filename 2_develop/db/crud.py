from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import (
    User,
    Client,
    Offer,
    Stage1Nyitooldal,
    Stage1Tartalom,
    Stage1KalkSzemiotika,
    Stage1KalkKvalitativ,
    Stage1KalkKvantitativ,
    StageHandoff,
)

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def get_all_users(db: Session) -> list[User]:
    return db.query(User).filter(User.aktiv == True).order_by(User.nev).all()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


def get_all_clients(db: Session) -> list[Client]:
    return db.query(Client).order_by(Client.nev).all()


def get_client_by_id(db: Session, client_id: int) -> Client | None:
    return db.query(Client).filter(Client.id == client_id).first()


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------


def _generate_nyilvantarto_szam(db: Session, szektor: str) -> str:
    """
    Formátum: [év utolsó 2 jegye][szektor betű][3 jegyű sorszám]
    Pl. 26F001, 26I003
    """
    year = datetime.now().strftime("%y")
    letter = szektor[0].upper()
    like_pattern = f"{year}{letter}%"
    count = (
        db.query(func.count(Offer.id))
        .filter(Offer.nyilvantarto_szam.like(like_pattern))
        .scalar()
        or 0
    )
    return f"{year}{letter}{count + 1:03d}"


def create_offer(db: Session, szektor: str, owner_id: int) -> Offer:
    szam = _generate_nyilvantarto_szam(db, szektor)
    offer = Offer(
        nyilvantarto_szam=szam,
        current_stage=1,
        status="folyamatban",
        current_owner_id=owner_id,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def get_all_offers(db: Session) -> list[Offer]:
    return db.query(Offer).order_by(Offer.created_at.desc()).all()


def get_offer_by_id(db: Session, offer_id: int) -> Offer | None:
    return db.query(Offer).filter(Offer.id == offer_id).first()


# ---------------------------------------------------------------------------
# Stage 1 – Nyitóoldal
# ---------------------------------------------------------------------------


def get_stage1_nyitooldal(db: Session, offer_id: int) -> Stage1Nyitooldal | None:
    return db.query(Stage1Nyitooldal).filter_by(offer_id=offer_id).first()


def upsert_stage1_nyitooldal(
    db: Session, offer_id: int, data: dict
) -> Stage1Nyitooldal:
    record = db.query(Stage1Nyitooldal).filter_by(offer_id=offer_id).first()
    if record:
        for key, value in data.items():
            setattr(record, key, value)
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1Nyitooldal(offer_id=offer_id, **data)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Tartalom
# ---------------------------------------------------------------------------


def get_stage1_tartalom(db: Session, offer_id: int) -> Stage1Tartalom | None:
    return db.query(Stage1Tartalom).filter_by(offer_id=offer_id).first()


def upsert_stage1_tartalom(db: Session, offer_id: int, data: dict) -> Stage1Tartalom:
    record = db.query(Stage1Tartalom).filter_by(offer_id=offer_id).first()
    if record:
        for key, value in data.items():
            setattr(record, key, value)
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1Tartalom(offer_id=offer_id, **data)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció Szemiotika
# ---------------------------------------------------------------------------


def get_stage1_kalk_szemiotika(
    db: Session, offer_id: int
) -> Stage1KalkSzemiotika | None:
    return db.query(Stage1KalkSzemiotika).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_szemiotika(
    db: Session, offer_id: int, data: dict
) -> Stage1KalkSzemiotika:
    record = db.query(Stage1KalkSzemiotika).filter_by(offer_id=offer_id).first()
    if record:
        for key, value in data.items():
            setattr(record, key, value)
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkSzemiotika(offer_id=offer_id, **data)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció Kvalitatív (JSON-alapú)
# ---------------------------------------------------------------------------


def get_stage1_kalk_kvalitativ(
    db: Session, offer_id: int
) -> Stage1KalkKvalitativ | None:
    return db.query(Stage1KalkKvalitativ).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_kvalitativ(
    db: Session, offer_id: int, params_json: str
) -> Stage1KalkKvalitativ:
    record = db.query(Stage1KalkKvalitativ).filter_by(offer_id=offer_id).first()
    if record:
        record.params_json = params_json
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkKvalitativ(offer_id=offer_id, params_json=params_json)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció Kvantitatív (JSON-alapú)
# ---------------------------------------------------------------------------


def get_stage1_kalk_kvantitativ(
    db: Session, offer_id: int
) -> Stage1KalkKvantitativ | None:
    return db.query(Stage1KalkKvantitativ).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_kvantitativ(
    db: Session, offer_id: int, params_json: str
) -> Stage1KalkKvantitativ:
    record = db.query(Stage1KalkKvantitativ).filter_by(offer_id=offer_id).first()
    if record:
        record.params_json = params_json
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkKvantitativ(offer_id=offer_id, params_json=params_json)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage handoff – szakaszátadás
# ---------------------------------------------------------------------------


def handoff_and_advance(
    db: Session,
    offer_id: int,
    from_user_id: int,
    to_user_id: int,
    megjegyzes: str,
) -> StageHandoff:
    offer = db.query(Offer).filter_by(id=offer_id).first()
    from_stage = offer.current_stage
    to_stage = from_stage + 1

    handoff = StageHandoff(
        offer_id=offer_id,
        from_stage=from_stage,
        to_stage=to_stage,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        megjegyzes=megjegyzes,
    )
    db.add(handoff)

    offer.current_stage = to_stage
    offer.current_owner_id = to_user_id
    offer.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(handoff)
    return handoff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _touch_offer(db: Session, offer_id: int) -> None:
    offer = db.query(Offer).filter_by(id=offer_id).first()
    if offer:
        offer.updated_at = datetime.utcnow()
