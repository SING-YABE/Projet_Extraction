"""
Routes pour l'extraction de prix avec Gemini
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from services import validator, file_parser
from services.gemini_extractor import GeminiPriceExtractor
from db import crud
from models.schemas import ExtractionResponse, PriceCreate
from utils.config import settings
from utils.logger import logger

from db.database import get_db
from ml.features import get_categorie_aliment

router = APIRouter()

extractor = GeminiPriceExtractor(settings.GEMINI_API_KEY)


@router.post("/extract", response_model=ExtractionResponse)
async def extract_prices(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Extract prices from whatsApp export file"""

    try:
        # Read file
        content = await file.read()
        text = content.decode('utf-8')

        # Parse messages
        messages = file_parser.parse_whatsapp_file(text)
        logger.info(f"Parsed {len(messages)} messages")

        # Extract with Gemini
        extractor = GeminiPriceExtractor(settings.GEMINI_API_KEY)
        extractions = extractor.extract_from_file(messages)
        logger.info(f"Extracted {len(extractions)} items")

        # Separate animals and aliments
        animals = [e for e in extractions if e.get('type') == 'animal']
        aliments = [e for e in extractions if e.get('type') == 'aliment']

        logger.info(f"Found {len(animals)} animals, {len(aliments)} aliments")

        # Validate animals
        valid_animals = validator.validate_extractions(animals)
        logger.info(f"Validated {len(valid_animals)}/{len(animals)} animal extractions")

        # Save animals to DB
        saved_animals = 0
        for extraction in valid_animals:
            try:
                price_data = PriceCreate(**extraction)
                crud.create_price(db, price_data)
                saved_animals += 1
            except Exception as e:
                logger.error(f"Error saving animal price: {e}")

        db.commit()
        logger.info(f"Saved {saved_animals} animal prices to database")

        # Save aliments to DB
        saved_aliments = 0
        for aliment in aliments:
            try:
                # Auto-detect category if not provided
                if not aliment.get('categorie'):
                    aliment['categorie'] = get_categorie_aliment(aliment.get('aliment_type'))

                # Validate basic fields
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
            except Exception as e:
                logger.error(f"Error saving aliment price: {e}")

        db.commit()
        logger.info(f"Saved {saved_aliments} aliment prices to database")

        return ExtractionResponse(
            success=True,
            total_messages=len(messages),
            extractions_found=len(extractions),
            valid_extractions=len(valid_animals) + len(aliments),
            saved_to_db=saved_animals + saved_aliments,
            data=[
                {
                    'animaux': {
                        'extraits': len(animals),
                        'valides': len(valid_animals),
                        'sauvegardes': saved_animals
                    },
                    'aliments': {
                        'extraits': len(aliments),
                        'sauvegardes': saved_aliments
                    }
                }
            ]
        )

    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(500, str(e))

@router.get("/extractions")
async def get_extractions(
    skip: int = 0,
    limit: int = 100,
    animal_type: str = None,
    db: Session = Depends(get_db)
):
    """Get all extractions with filters"""
    return crud.get_prices(db, skip=skip, limit=limit, animal_type=animal_type)
