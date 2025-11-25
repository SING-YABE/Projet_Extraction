"""
Database connection (PostgreSQL)
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from utils.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Price(Base):
    """Price model"""
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


def get_db():
    """Dependency for DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
