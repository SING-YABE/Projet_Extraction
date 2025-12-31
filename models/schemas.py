"""
All Pydantic schemas
"""
from pydantic import BaseModel, ConfigDict, Field
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


class WhatsAppFrom(BaseModel):
    """Sender details from webhook payload"""
    fromMe: bool = False
    id: Optional[str] = None
    number: Optional[str] = None
    pushname: Optional[str] = None
    countrycode: Optional[str] = None


class WhatsAppGroup(BaseModel):
    """Group details from webhook payload"""
    id: Optional[str] = None
    name: Optional[str] = None


class WhatsAppWebhookPayload(BaseModel):
    """Inbound webhook payload schema"""
    model_config = ConfigDict(populate_by_name=True)

    id: str
    content: Optional[str] = None
    number: Optional[str] = None
    chatid: Optional[str] = None
    type: Optional[str] = None
    isgroup: bool = False
    istag: bool = False
    from_: WhatsAppFrom = Field(alias="from")
    group: Optional[WhatsAppGroup] = None
    isviewonce: bool = False


__all__ = [
    'PriceCreate',
    'PriceResponse',
    'PriceInDB',
    'PredictionResponse',
    'TrainingResponse',
    'OpportunityResponse',
    'ExtractionResponse',
    'StatsResponse',
    'TrendResponse',
    'WhatsAppWebhookPayload',
    'WhatsAppFrom',
    'WhatsAppGroup'
]
