"""
Routes pour les statistiques et analyses
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from db.database import get_db, Prediction, Price
from db import crud
from services.trend_analyzer import TrendAnalyzer
from models.schemas import StatsResponse, TrendResponse
from utils.logger import logger

router = APIRouter()

analyzer = TrendAnalyzer()


@router.get("/stats", response_model=StatsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get global statistics"""
    
    stats = crud.get_statistics(db)
    
    return StatsResponse(
        total_prices=stats['total'],
        by_animal=stats['by_animal'],
        price_ranges=stats['ranges'],
        date_range=stats['date_range']
    )


@router.get("/trends", response_model=TrendResponse)
async def analyze_trends(
    animal_type: str = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Analyze price trends"""
    
    prices = crud.get_prices_period(db, days=days, animal_type=animal_type)
    
    if len(prices) < 10:
        return TrendResponse(
            trend="insufficient_data",
            variation_pct=0,
            message="Need more data"
        )
    
    trend_data = analyzer.analyze(prices)
    
    return TrendResponse(
        trend=trend_data['trend'],
        variation_pct=trend_data['variation'],
        message=trend_data['message'],
        conseil=trend_data['conseil']
    )


@router.get("/evolution")
async def get_price_evolution(
    animal_type: str,
    period: str = "week",  # day, week, month
    db: Session = Depends(get_db)
):
    """Get price evolution over time"""
    
    evolution = crud.get_price_evolution(db, animal_type, period)
    
    return {"evolution": evolution}
