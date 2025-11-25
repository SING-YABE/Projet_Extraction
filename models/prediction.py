"""
Pydantic models for Predictions
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class PredictionResponse(BaseModel):
    """Prediction response"""
    animal_type: str
    date: date
    prix_predit: int
    intervalle_min: int
    intervalle_max: int
    confiance: str  # 'haute', 'moyenne', 'faible'


class TrainingResponse(BaseModel):
    """Training response"""
    success: bool
    samples_used: int
    mae: float
    rmse: float
    r2: float
    mape: float


class OpportunityResponse(BaseModel):
    """Opportunity detection response"""
    price_id: int
    prix: int
    animal_type: str
    score: float
    evaluation: str
    economie: int
    economie_pct: float
