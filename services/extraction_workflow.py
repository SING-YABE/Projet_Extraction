"""
Shared workflow to extract and persist prices from messages.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from services import validator
from services.gemini_extractor import GeminiPriceExtractor
from db import crud
from ml.features import get_categorie_aliment
from utils.logger import logger
from models.schemas import PriceCreate


def _persist_batch(extractions: List[Dict], db: Session) -> Dict[str, int]:
    """
    Persiste un batch d'extractions en base immédiatement.
    Appelé après chaque batch réussi — pas en fin de traitement global.
    Retourne le nombre d'entrées sauvegardées.
    """
    animals = [e for e in extractions if e.get('type') == 'animal']
    aliments = [e for e in extractions if e.get('type') == 'aliment']

    # --- Animaux ---
    valid_animals = validator.validate_extractions(animals)
    saved_animals = 0
    for extraction in valid_animals:
        try:
            price_data = PriceCreate(**extraction)
            crud.create_price(db, price_data)
            saved_animals += 1
        except Exception as exc:
            logger.error(f"Error saving animal price: {exc}")

    # --- Aliments ---
    saved_aliments = 0
    for aliment in aliments:
        try:
            if not aliment.get('categorie'):
                aliment['categorie'] = get_categorie_aliment(aliment.get('aliment_type'))

            if not aliment.get('prix') or aliment['prix'] <= 0:
                continue
            if not aliment.get('aliment_type'):
                continue
            if not aliment.get('poids_kg') or aliment['poids_kg'] <= 0:
                logger.warning(
                    f"⚠️ Aliment ignoré (poids inconnu): {aliment.get('aliment_type')} "
                    f"- {aliment.get('message_original', '')[:50]}"
                )
                continue
            if aliment.get('prix_par_kg') and aliment['prix_par_kg'] <= 0:
                logger.warning(f"⚠️ Aliment ignoré (prix_par_kg invalide): {aliment}")
                continue

            aliment_data = {
                'prix': aliment['prix'],
                'aliment_type': aliment.get('aliment_type'),
                'categorie': aliment.get('categorie', 'AUTRE'),
                'unite': aliment.get('unite', 'kg'),
                'poids_kg': aliment.get('poids_kg'),
                'prix_par_kg': aliment.get('prix_par_kg'),
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

    # Commit après chaque batch — pas en fin globale
    db.commit()

    logger.info(
        f"💾 Batch persisté: {saved_animals} animaux + {saved_aliments} aliments "
        f"(/{len(valid_animals)} valides + /{len(aliments)} aliments bruts)"
    )

    return {'saved_animals': saved_animals, 'saved_aliments': saved_aliments}


def process_messages(
    messages: List[str],
    db: Session,
    extractor: GeminiPriceExtractor,
    steps: Optional[List[Dict[str, str]]] = None
) -> Dict[str, int]:
    """Extract prices from messages and persist them batch by batch."""

    def record(step: str, detail: str) -> None:
        if steps is not None:
            steps.append({"step": step, "detail": detail})
        logger.info(f"{step}: {detail}")

    record("messages.received", f"count={len(messages)}")

    # Compteurs cumulés — mis à jour par le callback à chaque batch
    cumulative = {'saved_animals': 0, 'saved_aliments': 0}

    def on_batch_success(batch_extractions: List[Dict]) -> None:
        """Callback appelé par extract_from_file après chaque batch réussi."""
        counts = _persist_batch(batch_extractions, db)
        cumulative['saved_animals'] += counts['saved_animals']
        cumulative['saved_aliments'] += counts['saved_aliments']

    # extract_from_file appelle on_batch_success après chaque batch —
    # la persistence est donc garantie même si le process plante à mi-chemin.
    totals = extractor.extract_from_file(
        messages,
        on_batch_success=on_batch_success,
    )

    record("extraction.completed", f"items={totals['total_extractions']}")
    record("extraction.categorized",
           f"animals={totals['total_animals']}, aliments={totals['total_aliments']}")
    record("db.animals.saved", f"count={cumulative['saved_animals']}")
    record("db.aliments.saved", f"count={cumulative['saved_aliments']}")

    return {
        'extractions_found': totals['total_extractions'],
        'animals_found': totals['total_animals'],
        'aliments_found': totals['total_aliments'],
        'valid_animals': cumulative['saved_animals'],   # approximation: saved ≈ valid ici
        'saved_animals': cumulative['saved_animals'],
        'saved_aliments': cumulative['saved_aliments'],
    }