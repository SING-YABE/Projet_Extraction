"""
Routes pour la prédiction ML avec XGBoost
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from ml.predictor import MLPredictor
from ml.trainer import train_model
from services.anomaly_detector import OpportunityDetector
from db.database import get_db
from db import crud
from models.schemas import PredictionResponse, TrainingResponse, OpportunityResponse
from utils.logger import logger

router = APIRouter()

ml_predictor = MLPredictor()
detector = OpportunityDetector()


@router.get("/predict", response_model=PredictionResponse)
async def predict_price(
    animal_type: str = Query(..., description="porcelet|truie|verrat|porc"),
    prediction_date: date = Query(..., description="Date prédiction"),
    db: Session = Depends(get_db)
):
    """Predict price for given animal and date"""

    if not ml_predictor.model:
        raise HTTPException(400, "Model not trained. Call /train first")

    try:
        # Convert date to datetime
        prix_predit = ml_predictor.predict_single(
            animal_type=animal_type,
            date=datetime.combine(prediction_date, datetime.min.time()),
            action_type='vente'
        )

        # Calculate confidence interval (±20%)
        intervalle = int(prix_predit * 0.2)

        return PredictionResponse(
            animal_type=animal_type,
            date=prediction_date,
            prix_predit=prix_predit,
            intervalle_min=prix_predit - intervalle,
            intervalle_max=prix_predit + intervalle,
            confiance='moyenne' if ml_predictor.stats else 'faible'
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(500, str(e))


@router.get("/predict/future")
async def predict_future(
    animal_type: str,
    months: int = 3,
    db: Session = Depends(get_db)
):
    """Predict prices for next N months"""

    if not ml_predictor.model:
        raise HTTPException(400, "Model not trained")

    try:
        predictions = []
        from datetime import timedelta
        current_date = datetime.now()

        for month in range(1, months + 1):
            future_date = current_date + timedelta(days=30 * month)

            prix_predit = ml_predictor.predict_single(
                animal_type=animal_type,
                date=future_date,
                action_type='vente'
            )

            intervalle = int(prix_predit * 0.2)

            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'animal_type': animal_type,
                'prix_predit': prix_predit,
                'intervalle_min': prix_predit - intervalle,
                'intervalle_max': prix_predit + intervalle,
                'confiance': 'moyenne'
            })

        return {"predictions": predictions}
    except Exception as e:
        logger.error(f"Future prediction error: {e}")
        raise HTTPException(500, str(e))


@router.post("/train", response_model=TrainingResponse)
async def train_ml_model(db: Session = Depends(get_db)):
    """Train XGBoost model with historical data"""

    try:
        # Get all prices
        prices = crud.get_all_prices(db)

        if len(prices) < 50:
            raise HTTPException(400, f"Need 50+ prices, have {len(prices)}")

        # Train
        metrics = train_model(prices)

        # Reload predictor with new model
        ml_predictor.load()

        logger.info(f"Model trained: MAE={metrics['mae']:.0f}, R2={metrics['r2']:.3f}")

        return TrainingResponse(
            success=True,
            samples_used=metrics['samples'],
            mae=metrics['mae'],
            rmse=metrics['rmse'],
            r2=metrics['r2'],
            mape=metrics['mape']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(500, str(e))


@router.get("/opportunities", response_model=list[OpportunityResponse])
async def detect_opportunities(
    min_score: int = 80,
    db: Session = Depends(get_db)
):
    """Detect good deals (opportunities)"""

    if not ml_predictor.model:
        raise HTTPException(400, "Model not trained. Call /train first")

    try:
        # Get recent prices
        recent = crud.get_recent_prices(db, days=7)

        if not recent:
            return []

        opportunities = []
        for price in recent:
            # Convert date string to datetime if needed
            price_date = price.date
            if isinstance(price_date, str):
                price_date = datetime.strptime(price_date, '%Y-%m-%d')

            score, evaluation, details = detector.score_opportunity(
                price.prix,
                price.animal_type,
                price_date
            )

            if score >= min_score:
                opportunities.append(OpportunityResponse(
                    price_id=price.id,
                    prix=price.prix,
                    animal_type=price.animal_type,
                    score=int(score),
                    evaluation=evaluation,
                    economie=details['economie'],
                    economie_pct=details['economie_pct']
                ))

        return opportunities
    except Exception as e:
        logger.error(f"Opportunities detection error: {e}")
        raise HTTPException(500, str(e))