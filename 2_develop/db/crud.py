from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import (
    User,
    Client,
    Offer,
    Stage1Nyitooldal,
    Stage1NyitooldalaHistory,
    Stage1KalkHistory,
    Stage1Tartalom,
    Stage1KalkSzemiotika,
    Stage1KalkKvalitativ,
    Stage1KalkKvantitativ,
    Stage1KalkTgi,
    Stage1KalkMasodelemzes,
    Stage1KalkTrening,
    Stage1KalkDesp,
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


def create_offer(
    db: Session,
    szektor: str,
    owner_id: int,
    projekt_neve: Optional[str] = None,
) -> Offer:
    szam = _generate_nyilvantarto_szam(db, szektor)
    offer = Offer(
        nyilvantarto_szam=szam,
        projekt_neve=projekt_neve or None,
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


def get_nyitooldal_history(
    db: Session, offer_id: int
) -> list[Stage1NyitooldalaHistory]:
    return (
        db.query(Stage1NyitooldalaHistory)
        .filter_by(offer_id=offer_id)
        .order_by(Stage1NyitooldalaHistory.modified_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció history
# ---------------------------------------------------------------------------


def save_kalk_history(
    db: Session,
    offer_id: int,
    calc_type: str,
    params_json: str,
    saved_by_user_id: Optional[int] = None,
) -> bool:
    """Elmenti a kalkuláció aktuális paramétereit, ha eltérnek az utolsó verziótól.
    Visszatér: True ha mentés történt, False ha nem változott semmi."""
    import json as _json

    last = (
        db.query(Stage1KalkHistory)
        .filter_by(offer_id=offer_id, calc_type=calc_type)
        .order_by(Stage1KalkHistory.saved_at.desc())
        .first()
    )
    if last is not None:
        try:
            if _json.loads(last.params_json) == _json.loads(params_json):
                return False
        except Exception:
            if last.params_json == params_json:
                return False

    record = Stage1KalkHistory(
        offer_id=offer_id,
        calc_type=calc_type,
        params_json=params_json,
        saved_at=datetime.utcnow(),
        saved_by_user_id=saved_by_user_id,
    )
    db.add(record)
    db.commit()
    return True


def get_kalk_history(
    db: Session, offer_id: int, calc_type: str
) -> list[Stage1KalkHistory]:
    return (
        db.query(Stage1KalkHistory)
        .filter_by(offer_id=offer_id, calc_type=calc_type)
        .order_by(Stage1KalkHistory.saved_at.desc())
        .all()
    )


def upsert_stage1_nyitooldal(
    db: Session,
    offer_id: int,
    data: dict,
    modified_by_user_id: Optional[int] = None,
) -> Stage1Nyitooldal:
    record = db.query(Stage1Nyitooldal).filter_by(offer_id=offer_id).first()
    if record:
        snapshot = Stage1NyitooldalaHistory(
            offer_id=offer_id,
            modified_by_user_id=modified_by_user_id,
            modified_at=datetime.utcnow(),
            ugyfel_kategoria=record.ugyfel_kategoria,
            kontakt=record.kontakt,
            keretszerzodes=record.keretszerzodes,
            domain=record.domain,
            uzletszerzo=record.uzletszerzo,
            elfogadas_eselye=record.elfogadas_eselye,
            divizion=record.divizion,
            orszagok_szama=record.orszagok_szama,
        )
        db.add(snapshot)
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
# Stage 1 – Kalkuláció TGI (JSON-alapú)
# ---------------------------------------------------------------------------


def get_stage1_kalk_tgi(db: Session, offer_id: int) -> Stage1KalkTgi | None:
    return db.query(Stage1KalkTgi).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_tgi(
    db: Session, offer_id: int, params_json: str
) -> Stage1KalkTgi:
    record = db.query(Stage1KalkTgi).filter_by(offer_id=offer_id).first()
    if record:
        record.params_json = params_json
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkTgi(offer_id=offer_id, params_json=params_json)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció Másodelemzés (JSON-alapú)
# ---------------------------------------------------------------------------


def get_stage1_kalk_masodelemzes(
    db: Session, offer_id: int
) -> Stage1KalkMasodelemzes | None:
    return db.query(Stage1KalkMasodelemzes).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_masodelemzes(
    db: Session, offer_id: int, params_json: str
) -> Stage1KalkMasodelemzes:
    record = db.query(Stage1KalkMasodelemzes).filter_by(offer_id=offer_id).first()
    if record:
        record.params_json = params_json
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkMasodelemzes(offer_id=offer_id, params_json=params_json)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció Tréning (JSON-alapú)
# ---------------------------------------------------------------------------


def get_stage1_kalk_trening(db: Session, offer_id: int) -> Stage1KalkTrening | None:
    return db.query(Stage1KalkTrening).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_trening(
    db: Session, offer_id: int, params_json: str
) -> Stage1KalkTrening:
    record = db.query(Stage1KalkTrening).filter_by(offer_id=offer_id).first()
    if record:
        record.params_json = params_json
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkTrening(offer_id=offer_id, params_json=params_json)
        db.add(record)
    _touch_offer(db, offer_id)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# Stage 1 – Kalkuláció DESP/COCR/SUCL (JSON-alapú)
# ---------------------------------------------------------------------------


def get_stage1_kalk_desp(db: Session, offer_id: int) -> Stage1KalkDesp | None:
    return db.query(Stage1KalkDesp).filter_by(offer_id=offer_id).first()


def upsert_stage1_kalk_desp(
    db: Session, offer_id: int, params_json: str
) -> Stage1KalkDesp:
    record = db.query(Stage1KalkDesp).filter_by(offer_id=offer_id).first()
    if record:
        record.params_json = params_json
        record.updated_at = datetime.utcnow()
    else:
        record = Stage1KalkDesp(offer_id=offer_id, params_json=params_json)
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
