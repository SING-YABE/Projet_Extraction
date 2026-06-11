"""
Routes pour l'extraction de prix (Ollama → Gemini fallback)
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from services import file_parser
from services.smart_extractor import SmartPriceExtractor
from services.extraction_workflow import process_messages
from models.schemas import ExtractionResponse
from utils.config import settings
from utils.logger import logger

from db import crud
from db.database import get_db

router = APIRouter()

extractor = SmartPriceExtractor(
    gemini_api_key=settings.GEMINI_API_KEY,
    ollama_base_url=settings.OLLAMA_BASE_URL,
    ollama_model=settings.OLLAMA_MODEL,
    confidence_threshold=settings.OLLAMA_CONFIDENCE_THRESHOLD,
    ollama_timeout=settings.OLLAMA_TIMEOUT,
)


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

        results = process_messages(messages, db, extractor)

        return ExtractionResponse(
            success=True,
            total_messages=len(messages),
            extractions_found=results['extractions_found'],
            valid_extractions=results['valid_animals'] + results['aliments_found'],
            saved_to_db=results['saved_animals'] + results['saved_aliments'],
            data=[
                {
                    'animaux': {
                        'extraits': results['animals_found'],
                        'valides': results['valid_animals'],
                        'sauvegardes': results['saved_animals']
                    },
                    'aliments': {
                        'extraits': results['aliments_found'],
                        'sauvegardes': results['saved_aliments']
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
