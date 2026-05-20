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

    # Időkeret
    kutatas_idotartama: Mapped[Optional[str]] = mapped_column(String(100))
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
