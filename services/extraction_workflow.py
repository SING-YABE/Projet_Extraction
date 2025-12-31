"""
Shared workflow to extract and persist prices from messages.
"""
from typing import List, Dict, Optional, Callable
from sqlalchemy.orm import Session

from services import validator
from services.gemini_extractor import GeminiPriceExtractor
from db import crud
from ml.features import get_categorie_aliment
from utils.logger import logger
from models.schemas import PriceCreate


def process_messages(
    messages: List[str],
    db: Session,
    extractor: GeminiPriceExtractor,
    steps: Optional[List[Dict[str, str]]] = None
) -> Dict[str, int]:
    """Extract prices from messages and persist them."""

    def record(step: str, detail: str) -> None:
        if steps is not None:
            steps.append({"step": step, "detail": detail})
        logger.info(f"{step}: {detail}")

    record("messages.received", f"count={len(messages)}")
    extractions = extractor.extract_from_file(messages)
    record("extraction.completed", f"items={len(extractions)}")

    animals = [e for e in extractions if e.get('type') == 'animal']
    aliments = [e for e in extractions if e.get('type') == 'aliment']

    record("extraction.categorized", f"animals={len(animals)}, aliments={len(aliments)}")

    valid_animals = validator.validate_extractions(animals)
    record("validation.animals", f"valid={len(valid_animals)}/{len(animals)}")

    saved_animals = 0
    for extraction in valid_animals:
        try:
            price_data = PriceCreate(**extraction)
            crud.create_price(db, price_data)
            saved_animals += 1
        except Exception as exc:
            logger.error(f"Error saving animal price: {exc}")

    db.commit()
    record("db.animals.saved", f"count={saved_animals}")

    saved_aliments = 0
    for aliment in aliments:
        try:
            if not aliment.get('categorie'):
                aliment['categorie'] = get_categorie_aliment(aliment.get('aliment_type'))

            if not aliment.get('prix') or aliment['prix'] <= 0:
                continue
            if not aliment.get('aliment_type'):
                continue

            aliment_data = {
                'prix': aliment['prix'],
                'aliment_type': aliment.get('aliment_type'),
                'categorie': aliment.get('categorie', 'AUTRE'),
                'unite': aliment.get('unite', 'sac'),
                'poids_kg': aliment.get('poids_kg'),
                'quantite': aliment.get('quantite', 1),
                'vendeur': aliment.get('vendeur'),
                'date': aliment.get('date'),
                'message_original': aliment.get('message_original'),
                'confiance': aliment.get('confiance', 50),
                'extraction_method': 'gemini'
            }

            crud.create_aliment_price(db, aliment_data)
            saved_aliments += 1
        except Exception as exc:
            logger.error(f"Error saving aliment price: {exc}")

    db.commit()
    record("db.aliments.saved", f"count={saved_aliments}")

    return {
        'extractions_found': len(extractions),
        'animals_found': len(animals),
        'aliments_found': len(aliments),
        'valid_animals': len(valid_animals),
        'saved_animals': saved_animals,
        'saved_aliments': saved_aliments,
    }
