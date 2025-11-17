# whatsapp_price_extractor/__init__.py
"""
WhatsApp Price Extractor Package
Système d'extraction et de prédiction de prix à partir de conversations WhatsApp
"""

__version__ = "1.0.0"
__author__ = "LSPA"

from .parser import parse_whatsapp_txt
from .extractor import PigPriceExtractorLLM
from .predictor import AutomatedPricePredictor
from .main import process_file_and_train, run_global_prediction, afficher_previsions_3_mois

__all__ = [
    'parse_whatsapp_txt',
    'PigPriceExtractorLLM', 
    'AutomatedPricePredictor',
    'process_file_and_train',
    'run_global_prediction',
    'afficher_previsions_3_mois'
]
