"""
Routes pour prédiction des prix aliments
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from ml.aliment_predictor import AlimentPredictor
from ml.aliment_trainer import train_aliment_model
from db.database import get_db
from db import crud
from utils.logger import logger

router = APIRouter()

# Initialiser prédicteur aliments
aliment_predictor = AlimentPredictor()


@router.post("/train/aliments")
async def train_aliments_model(db: Session = Depends(get_db)):
    """
    Entraîne le modèle ML pour prédire prix aliments

    Nécessite minimum 50 prix aliments en base de données
    """

    try:
        # Récupérer tous les prix aliments
        aliments = crud.get_all_aliment_prices(db)

        if len(aliments) < 50:
            raise HTTPException(
                400,
                f"Besoin d'au moins 50 prix aliments pour entraîner. Actuellement: {len(aliments)}"
            )

        logger.info(f"🚀 Début entraînement modèle ALIMENTS avec {len(aliments)} échantillons")

        # Entraîner
        metrics = train_aliment_model(aliments)

        # Recharger le prédicteur avec nouveau modèle
        aliment_predictor.load()

        logger.info(f"✅ Modèle ALIMENTS entraîné: MAE={metrics['mae']:.0f}, R²={metrics['r2']:.3f}")

        return {
            "success": True,
            "model_type": "aliments",
            "samples_used": metrics['samples'],
            "mae": round(metrics['mae'], 2),
            "rmse": round(metrics['rmse'], 2),
            "r2": round(metrics['r2'], 3),
            "mape": round(metrics['mape'], 2),
            "message": "Modèle aliments entraîné avec succès"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur entraînement modèle aliments: {e}")
        raise HTTPException(500, str(e))


@router.get("/predict/aliment")
async def predict_aliment_price(
        aliment_type: str = Query(..., description="Type d'aliment (maïs, soja, etc.)"),
        prediction_date: date = Query(..., description="Date de prédiction"),
        categorie: str = Query(None, description="Catégorie (auto-détecté si non fourni)"),
        db: Session = Depends(get_db)
):
    """
    Prédit le prix d'un aliment à une date donnée

    Exemples aliment_type:
    - maïs, mil, sorgho (ÉNERGÉTIQUE)
    - soja, tourteau soja (PROTÉINE)
    - concentré, prémix (VITAMINES)
    """

    if not aliment_predictor.is_trained:
        raise HTTPException(
            400,
            "Modèle aliments non entraîné. Appelez POST /api/train/aliments d'abord"
        )

    try:
        # Prédiction
        prix_predit = aliment_predictor.predict_single(
            aliment_type=aliment_type,
            date=datetime.combine(prediction_date, datetime.min.time()),
            categorie=categorie
        )

        # Intervalle de confiance (±15% pour aliments)
        intervalle = int(prix_predit * 0.15)

        return {
            "aliment_type": aliment_type,
            "categorie": categorie or aliment_predictor._detect_categorie(aliment_type),
            "date": str(prediction_date),
            "prix_predit": prix_predit,
            "intervalle_min": prix_predit - intervalle,
            "intervalle_max": prix_predit + intervalle,
            "confiance": "moyenne" if aliment_predictor.stats else "faible"
        }

    except Exception as e:
        logger.error(f"❌ Erreur prédiction aliment: {e}")
        raise HTTPException(500, str(e))


@router.get("/predict/aliment/categorie/{categorie}")
async def predict_aliments_by_categorie(
        categorie: str,
        prediction_date: date = Query(..., description="Date de prédiction"),
        db: Session = Depends(get_db)
):
    """
    Prédit les prix de plusieurs aliments d'une catégorie

    Catégories: ÉNERGÉTIQUE, PROTÉINE, MINÉRAUX, VITAMINES
    """

    if not aliment_predictor.is_trained:
        raise HTTPException(400, "Modèle aliments non entraîné")

    # Valider catégorie
    valid_categories = ['ÉNERGÉTIQUE', 'PROTÉINE', 'MINÉRAUX', 'VITAMINES']
    if categorie.upper() not in valid_categories:
        raise HTTPException(
            400,
            f"Catégorie invalide. Valeurs possibles: {', '.join(valid_categories)}"
        )

    try:
        # Prédictions pour cette catégorie
        predictions = aliment_predictor.predict_by_categorie(
            categorie=categorie.upper(),
            date=datetime.combine(prediction_date, datetime.min.time())
        )

        # Formater résultats
        results = []
        for aliment, prix in predictions.items():
            intervalle = int(prix * 0.15)
            results.append({
                "aliment": aliment,
                "prix_predit": prix,
                "intervalle_min": prix - intervalle,
                "intervalle_max": prix + intervalle
            })

        return {
            "categorie": categorie.upper(),
            "date": str(prediction_date),
            "aliments": results
        }

    except Exception as e:
        logger.error(f"❌ Erreur prédiction catégorie: {e}")
        raise HTTPException(500, str(e))


@router.get("/predict/aliment/future")
async def predict_aliment_future(
        aliment_type: str = Query(..., description="Type d'aliment"),
        months: int = Query(3, description="Nombre de mois à prédire"),
        categorie: str = Query(None, description="Catégorie"),
        db: Session = Depends(get_db)
):
    """
    Prédit les prix d'un aliment pour les N prochains mois
    """

    if not aliment_predictor.is_trained:
        raise HTTPException(400, "Modèle aliments non entraîné")

    if months < 1 or months > 12:
        raise HTTPException(400, "Nombre de mois doit être entre 1 et 12")

    try:
        predictions = []
        current_date = datetime.now()

        for month in range(1, months + 1):
            future_date = current_date + timedelta(days=30 * month)

            prix_predit = aliment_predictor.predict_single(
                aliment_type=aliment_type,
                date=future_date,
                categorie=categorie
            )

            intervalle = int(prix_predit * 0.15)

            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'aliment_type': aliment_type,
                'prix_predit': prix_predit,
                'intervalle_min': prix_predit - intervalle,
                'intervalle_max': prix_predit + intervalle
            })

        return {
            "aliment_type": aliment_type,
            "predictions": predictions
        }

    except Exception as e:
        logger.error(f"❌ Erreur prédictions futures aliments: {e}")
        raise HTTPException(500, str(e))


@router.get("/model/aliments/stats")
async def get_aliment_model_stats():
    """Statistiques du modèle aliments"""

    if not aliment_predictor.is_trained:
        return {
            "is_trained": False,
            "message": "Modèle aliments non entraîné"
        }

    stats = aliment_predictor.get_stats()

    return {
        "is_trained": True,
        "stats": stats
    }