from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class User(Base):
    """Felhasználók. Egyelőre 1 developer user, auth-ra előkészítve."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nev: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    szerepkor: Mapped[str] = mapped_column(
        String(50), default="GAD"
    )  # GAD, penzugy, admin
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Client(Base):
    """Ügyfél adatbázis."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nev: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    kategoria: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # Hazai / Nemzetközi / stb.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Offer(Base):
    """Ajánlat – a rendszer alapegysége. Egy nyilvántartó számon fut végig."""

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nyilvantarto_szam: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    projekt_neve: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    current_stage: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(50), default="folyamatban"
    )  # folyamatban | lezarva | elutasitva
    current_owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Kapcsolatok
    current_owner: Mapped["User"] = relationship(
        "User", foreign_keys=[current_owner_id]
    )
    stage1_nyitooldal: Mapped[Optional["Stage1Nyitooldal"]] = relationship(
        "Stage1Nyitooldal",
        back_populates="offer",
        uselist=False,
        cascade="all, delete-orphan",
    )
    stage1_tartalom: Mapped[Optional["Stage1Tartalom"]] = relationship(
        "Stage1Tartalom",
        back_populates="offer",
        uselist=False,
        cascade="all, delete-orphan",
    )
    handoffs: Mapped[list["StageHandoff"]] = relationship(
        "StageHandoff", back_populates="offer", order_by="StageHandoff.handoff_at"
    )


class Stage1Nyitooldal(Base):
    """Szakasz 1 – Nyitóoldal fül adatai (az Excel Nyitóoldal lapja alapján)."""

    __tablename__ = "stage1_nyitooldal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    ugyfel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"))
    ugyfel_kategoria: Mapped[Optional[str]] = mapped_column(String(100))
    ugyfel_szektor: Mapped[Optional[str]] = mapped_column(String(100))
    kontakt: Mapped[Optional[str]] = mapped_column(String(100))
    keretszerzodes: Mapped[Optional[str]] = mapped_column(String(50))
    domain: Mapped[Optional[str]] = mapped_column(String(100))
    uzletszerzo: Mapped[Optional[str]] = mapped_column(String(200))
    elfogadas_eselye: Mapped[Optional[float]] = mapped_column(Float)
    divizion: Mapped[Optional[str]] = mapped_column(String(100))
    orszagok_szama: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer", back_populates="stage1_nyitooldal")
    ugyfel: Mapped[Optional["Client"]] = relationship("Client")


class Stage1Tartalom(Base):
    """Szakasz 1 – Tartalom fül adatai (a kutatási brief, az Excel Tartalom lapja alapján)."""

    __tablename__ = "stage1_tartalom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    # Háttér és cél
    cel: Mapped[Optional[str]] = mapped_column(Text)
    kutatas_tipusa: Mapped[Optional[str]] = mapped_column(Text)
    celcsoport: Mapped[Optional[str]] = mapped_column(String(50))
    kutatasi_kerdesek: Mapped[Optional[str]] = mapped_column(
        Text
    )  # soronként egy kérdés

    # Módszertan
    elemzendo_anyagok: Mapped[Optional[str]] = mapped_column(Text)
    kutatasi_eszkozok: Mapped[Optional[str]] = mapped_column(Text)
    kulsos_alvallalkozo: Mapped[Optional[str]] = mapped_column(Text)
    fobb_lepesek: Mapped[Optional[str]] = mapped_column(Text)  # soronként egy lépés
    kantar_markezett_termek: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # csak Kvalitatív

    # Időkeret
    kutatas_idotartama: Mapped[Optional[str]] = mapped_column(String(100))  # deprecated
    ajanlat_elbiralasa: Mapped[Optional[date]] = mapped_column(Date)
    tervezett_indulas: Mapped[Optional[date]] = mapped_column(Date)
    varhato_befejezes: Mapped[Optional[date]] = mapped_column(Date)

    # Várt eredmények
    vart_eredmenyek: Mapped[Optional[str]] = mapped_column(
        Text
    )  # soronként egy eredmény

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer", back_populates="stage1_tartalom")


class StageHandoff(Base):
    """Szakaszátadás napló – ki adta át, kinek, mikor, melyik szakaszból melyikbe."""

    __tablename__ = "stage_handoffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), nullable=False)
    from_stage: Mapped[int] = mapped_column(Integer, nullable=False)
    to_stage: Mapped[int] = mapped_column(Integer, nullable=False)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    megjegyzes: Mapped[Optional[str]] = mapped_column(Text)
    handoff_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer", back_populates="handoffs")
    from_user: Mapped["User"] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id])


class Stage1KalkSzemiotika(Base):
    """
    Szakasz 1 – Kalkuláció (Insightment_Szemiotika fül, Feldolgozás blokk).
    A felhasználó a numerikus paramétereket adja meg; a `feldolgozasi_alap`-ot
    automatikusan számoljuk (1 ha bármelyik > 0).
    """

    __tablename__ = "stage1_kalk_szemiotika"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    debrief: Mapped[Optional[int]] = mapped_column(Integer)
    top_line: Mapped[Optional[int]] = mapped_column(Integer)
    egyszeru_elemzes: Mapped[Optional[int]] = mapped_column(Integer)
    melyelemzes: Mapped[Optional[int]] = mapped_column(Integer)
    management_summary: Mapped[Optional[int]] = mapped_column(Integer)
    prezentacio: Mapped[Optional[int]] = mapped_column(Integer)
    filmkeszites_ora: Mapped[Optional[float]] = mapped_column(Float)
    workshop_ora: Mapped[Optional[float]] = mapped_column(Float)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")


class Stage1KalkKvalitativ(Base):
    """
    Szakasz 1 – Kalkuláció (Kvalitatív kutatás).
    A paramétereket flexibilis JSON struktúrában tároljuk a sok blokk
    (Rekrutálás / Terepmunka / Napló-blog / Megfigyelés / Feldolgozás /
    Plusz szolgáltatások / Egyéb) miatt.
    """

    __tablename__ = "stage1_kalk_kvalitativ"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    params_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")


class Stage1KalkKvantitativ(Base):
    """
    Szakasz 1 – Kalkuláció (Kvantitatív kutatás).
    A paramétereket flexibilis JSON struktúrában tároljuk a sok blokk
    (Terepmunka / Napló / Megfigyelés / DP / Feldolgozás / Analytics /
    Plusz szolgáltatások / Egyéb) miatt.
    """

    __tablename__ = "stage1_kalk_kvantitativ"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    params_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")


class Stage1NyitooldalaHistory(Base):
    """Nyitóoldal módosítási előzmények – mentés előtti állapot snapshot-ja."""

    __tablename__ = "stage1_nyitooldal_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), nullable=False)
    modified_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ugyfel_kategoria: Mapped[Optional[str]] = mapped_column(String(100))
    kontakt: Mapped[Optional[str]] = mapped_column(String(100))
    keretszerzodes: Mapped[Optional[str]] = mapped_column(String(50))
    domain: Mapped[Optional[str]] = mapped_column(String(100))
    uzletszerzo: Mapped[Optional[str]] = mapped_column(String(200))
    elfogadas_eselye: Mapped[Optional[float]] = mapped_column(Float)
    divizion: Mapped[Optional[str]] = mapped_column(String(100))
    orszagok_szama: Mapped[Optional[int]] = mapped_column(Integer)

    offer: Mapped["Offer"] = relationship("Offer")
    modified_by: Mapped[Optional["User"]] = relationship("User")


class Stage1KalkHistory(Base):
    """Kalkuláció-verziók – minden eltérő mentéskor rögzíti az aktuális paramétereket."""

    __tablename__ = "stage1_kalk_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"), nullable=False)
    calc_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # szemiotika | kvalitativ | kvantitativ
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    saved_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    offer: Mapped["Offer"] = relationship("Offer")
    saved_by: Mapped[Optional["User"]] = relationship("User")


class Stage1KalkTgi(Base):
    """Szakasz 1 – TGI kalkuláció paraméterei (JSON-alapú tárolás)."""

    __tablename__ = "stage1_kalk_tgi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    params_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")


class Stage1KalkMasodelemzes(Base):
    """Szakasz 1 – Másodelemzés kalkuláció paraméterei (JSON-alapú tárolás)."""

    __tablename__ = "stage1_kalk_masodelemzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    params_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")


class Stage1KalkTrening(Base):
    """Szakasz 1 – Tréning kalkuláció paraméterei (JSON-alapú tárolás)."""

    __tablename__ = "stage1_kalk_trening"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    params_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")


class Stage1KalkDesp(Base):
    """Szakasz 1 – DESP/COCR/SUCL kalkuláció paraméterei (JSON-alapú tárolás)."""

    __tablename__ = "stage1_kalk_desp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offer_id: Mapped[int] = mapped_column(
        ForeignKey("offers.id"), unique=True, nullable=False
    )

    params_json: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    offer: Mapped["Offer"] = relationship("Offer")
