"""
All Pydantic schemas
"""
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import date

from models.price import PriceCreate, PriceResponse, PriceInDB
from models.prediction import (
    PredictionResponse,
    TrainingResponse,
    OpportunityResponse
)


class ExtractionResponse(BaseModel):
    """Response for extraction endpoint"""
    success: bool
    total_messages: int
    extractions_found: int
    valid_extractions: int
    saved_to_db: int
    data: List[Dict]


class StatsResponse(BaseModel):
    """Statistics response"""
    total_prices: int
    by_animal: Dict[str, int]
    price_ranges: Dict[str, Dict[str, int]]
    date_range: Dict[str, str]


class TrendResponse(BaseModel):
    """Trend analysis response"""
    trend: str
    variation_pct: float
    message: str
    conseil: Optional[str] = None


__all__ = [
    'PriceCreate',
    'PriceResponse',
    'PriceInDB',
    'PredictionResponse',
    'TrainingResponse',
    'OpportunityResponse',
    'ExtractionResponse',
    'StatsResponse',
    'TrendResponse'
]
