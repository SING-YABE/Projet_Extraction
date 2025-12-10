"""
Tests unitaires pour le module d'extraction
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.extraction import WhatsAppParser, PriceExtractor


class TestWhatsAppParser:
    """Tests pour le parser WhatsApp"""
    
    def test_parser_creation(self):
        """Test création du parser"""
        parser = WhatsAppParser()
        assert parser is not None
        assert parser.messages == []
    
    def test_parse_simple_message(self):
        """Test parsing message simple"""
        # TODO: Créer fichier test temporaire
        pass


class TestPriceExtractor:
    """Tests pour l'extracteur de prix"""
    
    def test_extractor_creation(self):
        """Test création de l'extracteur"""
        extractor = PriceExtractor()
        assert extractor is not None
    
    def test_extract_simple_price(self):
        """Test extraction prix simple"""
        extractor = PriceExtractor()
        message = "Porcelets disponibles à 25000f"
        
        prices = extractor.extract_from_message(message)
        
        assert len(prices) > 0
        assert prices[0].prix == 25000
    
    def test_extract_animal_type(self):
        """Test identification type animal"""
        extractor = PriceExtractor()
        message = "Porcelets de 3 mois à 25000 FCFA"
        
        prices = extractor.extract_from_message(message)
        
        assert len(prices) > 0
        assert prices[0].animal_type == 'porcelet'
    
    def test_extract_multiple_prices(self):
        """Test extraction prix multiples"""
        extractor = PriceExtractor()
        message = "Son de riz 6500f le sac, la tonne à 125000f"
        
        prices = extractor.extract_from_message(message)
        
        assert len(prices) == 2
        assert 6500 in [p.prix for p in prices]
        assert 125000 in [p.prix for p in prices]
    
    def test_no_price_in_message(self):
        """Test message sans prix"""
        extractor = PriceExtractor()
        message = "Bonjour, comment allez-vous?"
        
        prices = extractor.extract_from_message(message)
        
        assert len(prices) == 0
    
    def test_price_validation(self):
        """Test validation des prix"""
        extractor = PriceExtractor()
        
        # Prix valide
        assert extractor._validate_price(25000, 'animal', 'porcelet', 'unité')
        
        # Prix trop bas
        assert not extractor._validate_price(500, 'animal', 'porcelet', 'unité')
        
        # Prix trop haut
        assert not extractor._validate_price(5000000, 'animal', 'porcelet', 'unité')


# Pour lancer les tests:
# pytest tests/test_extraction.py -v
