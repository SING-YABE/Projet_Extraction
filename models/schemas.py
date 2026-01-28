"""
All Pydantic schemas
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any, Union
from datetime import date
from models.price import PriceCreate, PriceResponse, PriceInDB
from models.prediction import ( PredictionResponse, TrainingResponse, OpportunityResponse )


# ==================== EXTRACTION & STATS ====================

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


# ==================== WHATSAPP WEBHOOK ====================

class WhatsAppFrom(BaseModel):
    """Sender details from webhook payload"""
    model_config = ConfigDict(extra='allow')

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
    model_config = ConfigDict(populate_by_name=True, extra='allow')

    id: Optional[str] = None
    content: Optional[Union[str, Dict[str, Any]]] = None
    number: Optional[str] = None
    chatid: Optional[str] = None
    type: Optional[str] = None
    isgroup: bool = False
    istag: bool = False
    from_: Optional[WhatsAppFrom] = Field(default=None, alias="from")
    group: Optional[WhatsAppGroup] = None
    isviewonce: bool = False


# ==================== DÉPENSES ====================

class DepenseCreate(BaseModel):
    """Schéma pour créer une dépense"""
    date: date = Field(..., description="Date de la dépense (YYYY-MM-DD)")
    type_depense_id: int = Field(..., ge=1, le=7, description="ID du type de dépense (1=ANIMAUX, 2=ALIMENTS, 3=SALAIRES, 4=TRANSPORT, 5=SANTÉ, 6=MATÉRIEL, 7=AUTRE)")
    description: str = Field(..., min_length=1, max_length=200, description="Description de la dépense")
    montant: float = Field(..., gt=0, description="Montant en FCFA")
    mode_paiement: str = Field(..., description="Mode de paiement (Espèces, Dépôt, Chèque, Virement bancaire, Mobile Money)")
    observations: Optional[str] = Field(None, description="Observations supplémentaires")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date": "2026-01-27",
                "type_depense_id": 1,
                "description": "Achat de 2 porcelets",
                "montant": 50000,
                "mode_paiement": "Espèces",
                "observations": "Porcelets de 3 mois"
            }
        }
    )


class DepenseUpdate(BaseModel):
    """Schéma pour mettre à jour une dépense (tous les champs optionnels)"""
    date: Optional[date] = None
    type_depense_id: Optional[int] = Field(None, ge=1, le=7)
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    montant: Optional[float] = Field(None, gt=0)
    mode_paiement: Optional[str] = None
    observations: Optional[str] = None


class DepenseResponse(BaseModel):
    """Schéma de réponse pour une dépense"""
    id: int
    date: date
    type_depense_id: int
    description: str
    montant: float
    mode_paiement: str
    observations: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TypeDepenseResponse(BaseModel):
    """Schéma de réponse pour un type de dépense"""
    id: int
    nom: str

    model_config = ConfigDict(from_attributes=True)


class DepenseSummaryResponse(BaseModel):
    """Schéma de réponse pour le résumé des dépenses"""
    total: Dict[str, Any]
    par_categorie: List[Dict[str, Any]]
    par_mode_paiement: List[Dict[str, Any]]


# ==================== EXPORTS ====================

__all__ = [
    # Prix
    'PriceCreate',
    'PriceResponse',
    'PriceInDB',

    # Prédictions
    'PredictionResponse',
    'TrainingResponse',
    'OpportunityResponse',

    # Extraction
    'ExtractionResponse',
    'StatsResponse',
    'TrendResponse',

    # WhatsApp
    'WhatsAppWebhookPayload',
    'WhatsAppFrom',
    'WhatsAppGroup',

    # Dépenses
    'DepenseCreate',
    'DepenseUpdate',
    'DepenseResponse',
    'TypeDepenseResponse',
    'DepenseSummaryResponse',
]