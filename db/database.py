"""
Database connection (PostgreSQL)
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, Text, BigInteger, \
    ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from utils.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Price(Base):
    """Price model for animals"""
    __tablename__ = "prix_extraits"

    id = Column(Integer, primary_key=True, index=True)
    prix = Column(Integer, nullable=False)
    animal_type = Column(String(50))
    age_mois = Column(Integer)
    poids_kg = Column(Float)
    quantite = Column(Integer, default=1)
    unite = Column(String(20))
    action = Column(String(50))
    negociable = Column(Boolean, default=False)
    etat = Column(String(100))
    vendeur = Column(String(255))
    date = Column(Date)
    message_original = Column(Text)
    confiance = Column(Integer)
    extraction_method = Column(String(20), default="gemini")
    created_at = Column(DateTime, default=datetime.now)


class PrixAliment(Base):
    """Price model for feed/aliments"""
    __tablename__ = "prix_aliments"

    id = Column(Integer, primary_key=True, index=True)
    prix = Column(Integer, nullable=False)
    aliment_type = Column(String(50))
    categorie = Column(String(50))
    unite = Column(String(20))
    poids_kg = Column(Float)
    prix_par_kg = Column(Float, nullable=True)   # ← AJOUT : prix ramené au kg pour comparaison
    quantite = Column(Integer, default=1)
    vendeur = Column(String(255))
    date = Column(Date)
    message_original = Column(Text)
    confiance = Column(Integer)
    extraction_method = Column(String(20), default="gemini")
    created_at = Column(DateTime, default=datetime.now)


class Prediction(Base):
    """Prediction model"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    animal_type = Column(String(50))
    date_prediction = Column(Date)
    prix_predit = Column(Integer)
    intervalle_min = Column(Integer)
    intervalle_max = Column(Integer)
    confiance = Column(String(20))
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


class Depense(Base):
    __tablename__ = "depense"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    type_depense_id = Column(BigInteger, ForeignKey('type_depense.id'), nullable=False)
    description = Column(String, nullable=False)
    montant = Column(Float, nullable=False)
    mode_paiement = Column(String, nullable=False)
    observations = Column(String, nullable=True)

    type_depense = relationship("TypeDepense", back_populates="depenses")


class TypeDepense(Base):
    __tablename__ = "type_depense"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nom = Column(String, nullable=False)

    depenses = relationship("Depense", back_populates="type_depense")


def get_db():
    """Dependency for DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()