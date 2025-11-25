"""
Routes pour l'extraction de prix avec Gemini
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import tempfile
from pathlib import Path

from services.gemini_extractor import GeminiPriceExtractor
from services.file_parser import parse_whatsapp_file
from services.validator import validate_extractions
from db.database import get_db
from db import crud
from models.schemas import ExtractionResponse, PriceCreate
from utils.config import settings
from utils.logger import logger

router = APIRouter()

extractor = GeminiPriceExtractor(settings.GEMINI_API_KEY)


@router.post("/extract", response_model=ExtractionResponse)
async def extract_prices(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Extract prices from WhatsApp .txt file using Gemini
    """
    if not file.filename.endswith('.txt'):
        raise HTTPException(400, "File must be .txt")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse
        messages = parse_whatsapp_file(tmp_path)
        logger.info(f"Parsed {len(messages)} messages")
        
        # Extract with Gemini
        extractions = extractor.extract_from_file(
            messages,
            batch_size=100,
            delay_seconds=4
        )
        
        # Validate
        valid_extractions = validate_extractions(extractions)
        logger.info(f"Validated {len(valid_extractions)} extractions")
        
        # Save to DB
        saved_count = 0
        for ext in valid_extractions:
            price_data = PriceCreate(**ext)
            crud.create_price(db, price_data)
            saved_count += 1
        
        db.commit()
        
        return ExtractionResponse(
            success=True,
            total_messages=len(messages),
            extractions_found=len(extractions),
            valid_extractions=len(valid_extractions),
            saved_to_db=saved_count,
            data=valid_extractions[:10]  # First 10
        )
        
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(500, str(e))
    finally:
        Path(tmp_path).unlink()


@router.get("/extractions")
async def get_extractions(
    skip: int = 0,
    limit: int = 100,
    animal_type: str = None,
    db: Session = Depends(get_db)
):
    """Get all extractions with filters"""
    return crud.get_prices(db, skip=skip, limit=limit, animal_type=animal_type)
