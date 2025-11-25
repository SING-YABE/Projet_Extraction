"""
Pydantic models for Price
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime


class PriceBase(BaseModel):
    """Base price model"""
    prix: int = Field(..., gt=0, description="Prix en FCFA")
    animal_type: Optional[str] = Field(None, description="porcelet|truie|verrat|porc")
    age_mois: Optional[int] = Field(None, ge=0, le=120)
    poids_kg: Optional[float] = Field(None, ge=0, le=500)
    quantite: Optional[int] = Field(default=1, ge=1)
    unite: Optional[str] = Field(default="tete", description="tete|kg|lot")
    action: Optional[str] = Field(default="vente", description="vente|achat|prix_info")
    negociable: Optional[bool] = Field(default=False)
    etat: Optional[str] = None
    vendeur: Optional[str] = None
    date: Optional[str] = None
    message_original: Optional[str] = None
    confiance: Optional[int] = Field(default=50, ge=0, le=100)

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Parse date to string format YYYY-MM-DD"""
        if v is None:
            return None
        if isinstance(v, date):
            return v.strftime('%Y-%m-%d')
        if isinstance(v, datetime):
            return v.strftime('%Y-%m-%d')
        if isinstance(v, str):
            # Validate and normalize format
            try:
                dt = datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                try:
                    dt = datetime.fromisoformat(v)
                    return dt.strftime('%Y-%m-%d')
                except:
                    return None
        return None

    @field_validator('quantite', mode='before')
    @classmethod
    def parse_quantite(cls, v):
        """Handle None quantite"""
        if v is None:
            return 1
        return v

    @field_validator('confiance', mode='before')
    @classmethod
    def parse_confiance(cls, v):
        """Handle None confiance"""
        if v is None:
            return 50
        return v


class PriceCreate(PriceBase):
    """Create new price"""
    pass


class PriceInDB(PriceBase):
    """Price from database"""
    id: int
    extraction_method: str = "gemini"
    created_at: str

    class Config:
        from_attributes = True


class PriceResponse(PriceInDB):
    """API response for price"""
    pass