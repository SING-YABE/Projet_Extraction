# whatsapp_price_extractor/__init__.py
"""
WhatsApp Price Extractor Package
Système d'extraction et de prédiction de prix à partir de conversations WhatsApp
"""

__version__ = "1.0.0"
__author__ = "Votre nom"

from .parser import parse_whatsapp_txt
from .extractor import PigPriceExtractorLLM
from .predictor import AutomatedPricePredictor
from .main import process_automated_extraction

__all__ = [
    'parse_whatsapp_txt',
    'PigPriceExtractorLLM', 
    'AutomatedPricePredictor',
    'process_automated_extraction'
]