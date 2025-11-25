"""
CRUD operations for database
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Optional

from db.database import Price, Prediction
from models.schemas import PriceCreate


def create_price(db: Session, price: PriceCreate) -> Price:
    """Create new price entry"""
    db_price = Price(**price.model_dump())
    db.add(db_price)
    db.flush()
    return db_price


def get_prices(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    animal_type: str = None
) -> List[Price]:
    """Get prices with filters"""
    query = db.query(Price)
    
    if animal_type:
        query = query.filter(Price.animal_type == animal_type)
    
    return query.offset(skip).limit(limit).all()


def get_all_prices(db: Session) -> List[dict]:
    """Get all prices as dicts for ML"""
    prices = db.query(Price).all()
    return [
        {
            'id': p.id,
            'prix': p.prix,
            'animal_type': p.animal_type,
            'age_mois': p.age_mois,
            'poids_kg': p.poids_kg,
            'action_type': p.action,
            'date': p.date,
            'vendeur': p.vendeur
        }
        for p in prices
    ]


def get_recent_prices(db: Session, days: int = 7) -> List[Price]:
    """Get prices from last N days"""
    cutoff = datetime.now() - timedelta(days=days)
    return db.query(Price).filter(Price.date >= cutoff).all()


def get_prices_period(
    db: Session,
    days: int = 30,
    animal_type: str = None
) -> List[dict]:
    """Get prices for period"""
    cutoff = datetime.now() - timedelta(days=days)
    query = db.query(Price).filter(Price.date >= cutoff)
    
    if animal_type:
        query = query.filter(Price.animal_type == animal_type)
    
    prices = query.all()
    return [{'prix': p.prix, 'date': p.date} for p in prices]


def get_statistics(db: Session) -> dict:
    """Get global statistics"""
    total = db.query(Price).count()
    
    # By animal
    by_animal = {}
    animals = db.query(
        Price.animal_type,
        func.count(Price.id)
    ).group_by(Price.animal_type).all()
    
    for animal, count in animals:
        by_animal[animal or 'non_specifie'] = count
    
    # Price ranges
    ranges = {}
    for animal in by_animal.keys():
        stats = db.query(
            func.min(Price.prix),
            func.max(Price.prix),
            func.avg(Price.prix)
        ).filter(Price.animal_type == animal).first()
        
        ranges[animal] = {
            'min': int(stats[0]) if stats[0] else 0,
            'max': int(stats[1]) if stats[1] else 0,
            'avg': int(stats[2]) if stats[2] else 0
        }
    
    # Date range
    dates = db.query(
        func.min(Price.date),
        func.max(Price.date)
    ).first()
    
    return {
        'total': total,
        'by_animal': by_animal,
        'ranges': ranges,
        'date_range': {
            'start': str(dates[0]) if dates[0] else None,
            'end': str(dates[1]) if dates[1] else None
        }
    }


def get_price_evolution(
    db: Session,
    animal_type: str,
    period: str = 'week'
) -> List[dict]:
    """Get price evolution"""
    
    if period == 'day':
        group_by = func.date(Price.date)
    elif period == 'week':
        group_by = func.date_trunc('week', Price.date)
    else:  # month
        group_by = func.date_trunc('month', Price.date)
    
    results = db.query(
        group_by.label('period'),
        func.avg(Price.prix).label('avg_prix'),
        func.count(Price.id).label('count')
    ).filter(
        Price.animal_type == animal_type
    ).group_by('period').order_by('period').all()
    
    return [
        {
            'period': str(r.period),
            'avg_prix': int(r.avg_prix),
            'count': r.count
        }
        for r in results
    ]
