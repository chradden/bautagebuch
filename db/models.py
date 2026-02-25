from datetime import datetime, date, time
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Date, Time,
    DateTime, Float, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Projekt(Base):
    __tablename__ = "projekte"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    adresse = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    bauherr = Column(String)
    baubeginn = Column(Date)
    erstellt_am = Column(DateTime, default=datetime.now)

    eintraege = relationship("Eintrag", back_populates="projekt")
    tagesberichte = relationship("Tagesbericht", back_populates="projekt")


class Benutzer(Base):
    __tablename__ = "benutzer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String, nullable=False)
    rolle = Column(String, default="bauleiter")
    aktives_projekt_id = Column(Integer, ForeignKey("projekte.id"))
    erstellt_am = Column(DateTime, default=datetime.now)

    aktives_projekt = relationship("Projekt")
    eintraege = relationship("Eintrag", back_populates="benutzer")


class Eintrag(Base):
    __tablename__ = "eintraege"

    id = Column(Integer, primary_key=True, autoincrement=True)
    benutzer_id = Column(Integer, ForeignKey("benutzer.id"))
    projekt_id = Column(Integer, ForeignKey("projekte.id"))
    datum = Column(Date, nullable=False)
    uhrzeit = Column(Time, nullable=False)
    typ = Column(String, nullable=False)  # 'text', 'foto', 'sprache'
    rohinhalt = Column(Text)
    ki_zusammenfassung = Column(Text)
    kategorie = Column(String)  # 'reparatur', 'maengelbeseitigung', 'wartung', etc.
    prioritaet = Column(String)  # 'rot', 'gelb', 'gruen'
    kostenschaetzung = Column(String)  # z.B. '500-1.000 €'
    erstellt_am = Column(DateTime, default=datetime.now)

    benutzer = relationship("Benutzer", back_populates="eintraege")
    projekt = relationship("Projekt", back_populates="eintraege")
    fotos = relationship("Foto", back_populates="eintrag")


class Foto(Base):
    __tablename__ = "fotos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eintrag_id = Column(Integer, ForeignKey("eintraege.id"))
    dateipfad = Column(String, nullable=False)
    beschreibung = Column(Text)
    erstellt_am = Column(DateTime, default=datetime.now)

    eintrag = relationship("Eintrag", back_populates="fotos")


class Tagesbericht(Base):
    __tablename__ = "tagesberichte"

    id = Column(Integer, primary_key=True, autoincrement=True)
    projekt_id = Column(Integer, ForeignKey("projekte.id"))
    datum = Column(Date, nullable=False)
    pdf_pfad = Column(String)
    erstellt_am = Column(DateTime, default=datetime.now)

    __table_args__ = (UniqueConstraint("projekt_id", "datum"),)

    projekt = relationship("Projekt", back_populates="tagesberichte")
