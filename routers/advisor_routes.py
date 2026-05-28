"""Routes for farm advisor alerts"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from services import farm_advisor

router = APIRouter()


@router.get("/advisor/alerts")
def get_advisor_alerts(db: Session = Depends(get_db)):
    """Return alerts computed from the farm database."""
    try:
        result = farm_advisor.gather_alerts(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))