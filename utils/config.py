"""
Configuration settings
"""
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # API
    APP_NAME: str = "WhatsApp Price Intelligence"
    VERSION: str = "2.0.0"
    
    # Database
    DATABASE_URL: str = "postgresql://root:password@localhost:5432/whatsapp_prices"
    
    # Gemini
    GEMINI_API_KEY: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000"]
    
    # ML
    MODEL_PATH: str = "ml/models/xgboost_model.pkl"
    MIN_SAMPLES_TRAINING: int = 50
    
    class Config:
        # repo_root = Path(__file__).resolve().parents[1]
        # env_file = (
        #     repo_root / ".env.local",
        #     repo_root / ".env",
        #     ".env.local",
        #     ".env",
        # )
        env_file = ".env"  
        case_sensitive = True
     
    @model_validator(mode="after")
    def validate_required(self):
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required. Set it in .env.local or .env.")
        return self


settings = Settings()
