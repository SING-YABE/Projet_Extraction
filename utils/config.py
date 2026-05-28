from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "WhatsApp Price Intelligence"
    VERSION: str = "2.0.0"

    DATABASE_URL: str = "postgresql://root:password@localhost:5432/whatsapp_prices"

    GEMINI_API_KEY: str = ""

    CORS_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000"]

    MODEL_PATH: str = "ml/models/xgboost_model.pkl"
    MIN_SAMPLES_TRAINING: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    @model_validator(mode="after")
    def validate_required(self):
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required.")
        return self

settings = Settings()