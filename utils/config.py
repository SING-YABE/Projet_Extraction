from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "WhatsApp Price Intelligence"
    VERSION: str = "2.0.0"

    DATABASE_URL: str = "postgresql://root:password@localhost:5432/whatsapp_prices"

    # ── Gemini (fallback cloud) ─────────────────────────────────────────────
    # Optionnel : si absent, le fallback Gemini est désactivé mais Ollama reste actif

    # ── Ollama (extracteur principal local) ────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:7b"
    # Seuil de confiance moyen en dessous duquel on bascule sur Gemini
    OLLAMA_CONFIDENCE_THRESHOLD: int = 60
    # Timeout en secondes pour les requêtes Ollama
    OLLAMA_TIMEOUT: int = 120

    CORS_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000"]

    MODEL_PATH: str = "ml/models/xgboost_model.pkl"
    MIN_SAMPLES_TRAINING: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @model_validator(mode="after")
    def validate_required(self):
        # GEMINI_API_KEY n'est plus obligatoire — Ollama est le primaire.
        # Un warning est loggé dans SmartPriceExtractor si elle est absente.
        return self

settings = Settings()