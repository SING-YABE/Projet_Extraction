"""
Validation des extractions Gemini
"""
from typing import List, Dict
from datetime import datetime
from utils.logger import logger


VALID_ANIMALS = ['porcelet', 'truie', 'verrat', 'porc']
VALID_ACTIONS = ['vente', 'achat', 'prix_info', 'recherche']


def validate_extraction(extraction: Dict) -> bool:
    """Validate single extraction"""
    
    # Prix requis
    if 'prix' not in extraction or not extraction['prix']:
        return False
    
    prix = extraction['prix']
    if not isinstance(prix, (int, float)) or prix <= 0 or prix > 10_000_000:
        return False
    
    # Animal type
    animal = extraction.get('animal_type')
    if animal and animal not in VALID_ANIMALS:
        logger.warning(f"Invalid animal_type: {animal}")
        return False
    
    # Action
    action = extraction.get('action')
    if action and action not in VALID_ACTIONS:
        extraction['action'] = 'vente'  # Default
    
    # Confiance
    confiance = extraction.get('confiance', 50)
    if not isinstance(confiance, (int, float)) or confiance < 0 or confiance > 100:
        extraction['confiance'] = 50
    
    if confiance < 40:
        return False
    
    # Age
    age = extraction.get('age_mois')
    if age and (age < 0 or age > 120):
        extraction['age_mois'] = None
    
    # Poids
    poids = extraction.get('poids_kg')
    if poids and (poids < 0 or poids > 500):
        extraction['poids_kg'] = None
    
    # Date
    date_str = extraction.get('date')
    if date_str:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except:
            extraction['date'] = datetime.now().strftime('%Y-%m-%d')
    else:
        extraction['date'] = datetime.now().strftime('%Y-%m-%d')
    
    return True


def validate_extractions(extractions: List[Dict]) -> List[Dict]:
    """
    Validate list of extractions
    
    Returns:
        Validated and cleaned extractions
    """
    valid = []
    
    for ext in extractions:
        if validate_extraction(ext):
            valid.append(ext)
    
    logger.info(f"Validated {len(valid)}/{len(extractions)} extractions")
    
    return valid


def deduplicate_extractions(extractions: List[Dict]) -> List[Dict]:
    """Remove duplicates"""
    
    seen = set()
    unique = []
    
    for ext in extractions:
        key = (ext['prix'], ext.get('animal_type'), ext.get('date'))
        
        if key not in seen:
            seen.add(key)
            unique.append(ext)
    
    logger.info(f"Deduplicated: {len(extractions)} → {len(unique)}")
    
    return unique
