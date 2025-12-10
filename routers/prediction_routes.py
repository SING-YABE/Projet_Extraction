"""
Routes pour la prédiction ML avec XGBoost
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from ml.predictor import MLPredictor
from ml.trainer import train_model
from ml.aliment_predictor import AlimentPredictor
from services.anomaly_detector import OpportunityDetector
from db.database import get_db
from db import crud
from models.schemas import PredictionResponse, TrainingResponse, OpportunityResponse
from utils.logger import logger

router = APIRouter()

ml_predictor = MLPredictor()
aliment_predictor = AlimentPredictor()
detector = OpportunityDetector()


@router.get("/predict", response_model=PredictionResponse)
async def predict_price(
        animal_type: str = Query(...),
        prediction_date: date = Query(...),
        db: Session = Depends(get_db)
):
    """Predict price for given animal and date (en se basant sur le model entrainê des aliments si disponible)"""

    if not ml_predictor.model:
        raise HTTPException(400, "Model not trained")

    try:
        prix_predit = ml_predictor.predict_single(
            animal_type=animal_type,
            date=datetime.combine(prediction_date, datetime.min.time()),
            action_type='vente',
            aliment_predictor=aliment_predictor
        )

        intervalle = int(prix_predit * 0.2)
        mode = "cascade" if aliment_predictor.is_trained else "standard"

        # ✅ SAUVEGARDER LA PRÉDICTION
        from db.database import Prediction
        db_prediction = Prediction(
            animal_type=animal_type,
            date_prediction=prediction_date,
            prix_predit=prix_predit,
            intervalle_min=prix_predit - intervalle,
            intervalle_max=prix_predit + intervalle,
            confiance=f'moyenne ({mode})' if ml_predictor.stats else 'faible',
            model_version='v1.0'
        )
        db.add(db_prediction)
        db.commit()

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
    """Predict prices for next N months (include cascade aliments if avalaible)"""

    if not ml_predictor.model:
        raise HTTPException(400, "Model not trained")

    try:
        predictions = []
        from datetime import timedelta
        current_date = datetime.now()

        prediction_mode = "cascade" if aliment_predictor.is_trained else "standard"

        for month in range(1, months + 1):
            future_date = current_date + timedelta(days=30 * month)

            prix_predit = ml_predictor.predict_single(
                animal_type=animal_type,
                date=future_date,
                action_type='vente',
                aliment_predictor=aliment_predictor
            )

            intervalle = int(prix_predit * 0.2)

            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'animal_type': animal_type,
                'prix_predit': prix_predit,
                'intervalle_min': prix_predit - intervalle,
                'intervalle_max': prix_predit + intervalle,
                'confiance': f'moyenne ({prediction_mode})'
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


@router.get("/model/accuracy")
async def get_model_accuracy(
        days: int = Query(30, description="Derniers N jours à analyser"),
        db: Session = Depends(get_db)
):
    """
    Analyse la précision du modèle sur prédictions passées

    Compare les prédictions faites dans le passé avec les prix réels observés
    """

    try:
        from datetime import timedelta
        from db.database import Prediction

        cutoff = datetime.now() - timedelta(days=days)

        # Récupérer prédictions passées (faites dans le passé pour des dates déjà écoulées)
        predictions = db.query(Prediction).filter(
            Prediction.date_prediction < datetime.now(),
            Prediction.date_prediction >= cutoff
        ).all()

        if not predictions:
            return {
                'periode_jours': days,
                'nb_predictions': 0,
                'message': 'Aucune prédiction passée à analyser. Utilisez POST /api/predict pour créer des prédictions.',
                'mae': None,
                'mape': None,
                'details': []
            }

        results = []
        total_erreur = 0
        total_erreur_pct = 0
        count_matched = 0

        for pred in predictions:
            # Trouver prix réels à cette date
            real_prices = db.query(Price).filter(
                Price.animal_type == pred.animal_type,
                Price.date == pred.date_prediction
            ).all()

            if real_prices:
                prix_reel = sum(p.prix for p in real_prices) / len(real_prices)
                erreur = pred.prix_predit - prix_reel
                erreur_pct = (erreur / prix_reel) * 100

                total_erreur += abs(erreur)
                total_erreur_pct += abs(erreur_pct)
                count_matched += 1

                results.append({
                    'date': str(pred.date_prediction),
                    'animal': pred.animal_type,
                    'predit': pred.prix_predit,
                    'reel': int(prix_reel),
                    'erreur': int(erreur),
                    'erreur_pct': round(erreur_pct, 1),
                    'dans_intervalle': pred.intervalle_min <= prix_reel <= pred.intervalle_max
                })

        if count_matched > 0:
            mae = total_erreur / count_matched
            mape = total_erreur_pct / count_matched
            precision = sum(1 for r in results if r['dans_intervalle']) / count_matched * 100

            return {
                'periode_jours': days,
                'nb_predictions': len(predictions),
                'nb_avec_donnees_reelles': count_matched,
                'mae': int(mae),
                'mape': round(mape, 1),
                'precision_intervalle': round(precision, 1),
                'details': results[:20]  # Limiter à 20 résultats
            }

        return {
            'periode_jours': days,
            'nb_predictions': len(predictions),
            'nb_avec_donnees_reelles': 0,
            'message': 'Prédictions trouvées mais aucune donnée réelle correspondante',
            'mae': None,
            'mape': None,
            'details': []
        }

    except Exception as e:
        logger.error(f"Erreur analyse accuracy: {e}")
        raise HTTPException(500, str(e))