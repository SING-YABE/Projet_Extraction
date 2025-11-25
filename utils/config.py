"""
Configuration settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # API
    APP_NAME: str = "WhatsApp Price Intelligence"
    VERSION: str = "2.0.0"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/whatsapp_prices"
    
    # Gemini
    GEMINI_API_KEY: str = "AIzaSyBFSU-8oSZhnjXEta3eMfAMAUP8Y9VoJIw"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:4200", "http://localhost:3000"]
    
    # ML
    MODEL_PATH: str = "ml/models/xgboost_model.pkl"
    MIN_SAMPLES_TRAINING: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
