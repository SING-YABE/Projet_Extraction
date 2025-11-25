"""
Détecteur d'opportunités (bonnes affaires)
"""
from typing import Tuple, Dict
from datetime import datetime

from ml.predictor import MLPredictor
from utils.logger import logger


class OpportunityDetector:
    """Détecte les bonnes affaires"""

    def __init__(self):
        self.predictor = MLPredictor()

    def score_opportunity(
        self,
        prix_offert: int,
        animal_type: str,
        date: datetime = None
    ) -> Tuple[float, str, Dict]:
        """
        Score une opportunité (0-100)

        Returns:
            (score, évaluation, détails)
        """
        date = date or datetime.now()

        if not self.predictor.model:
            logger.warning("ML model not loaded, using default scoring")
            return (50.0, "Modèle non entraîné", {
                'prix_offert': prix_offert,
                'prix_predit': prix_offert,
                'economie': 0,
                'economie_pct': 0,
                'score': 50
            })

        try:
            # Predict expected price
            prix_predit = self.predictor.predict_single(animal_type, date)

            # Calculate savings
            economie = prix_predit - prix_offert
            economie_pct = (economie / prix_predit) * 100

            # Score
            if economie_pct >= 30:
                score = 100
                evaluation = "🔥 EXCELLENTE AFFAIRE"
            elif economie_pct >= 20:
                score = 85
                evaluation = "⭐ Très bonne affaire"
            elif economie_pct >= 10:
                score = 70
                evaluation = "✅ Bonne affaire"
            elif economie_pct >= 0:
                score = 55
                evaluation = "💰 Prix correct"
            elif economie_pct >= -10:
                score = 40
                evaluation = "⚠️ Prix élevé"
            else:
                score = 20
                evaluation = "❌ Prix très élevé"

            details = {
                'prix_offert': prix_offert,
                'prix_predit': prix_predit,
                'economie': economie,
                'economie_pct': round(economie_pct, 1),
                'score': score
            }

            return (score, evaluation, details)
        except Exception as e:
            logger.error(f"Opportunity scoring error: {e}")
            return (50.0, "Erreur de scoring", {
                'prix_offert': prix_offert,
                'prix_predit': prix_offert,
                'economie': 0,
                'economie_pct': 0,
                'score': 50
            })

    def detect_anomalies(
        self,
        prices: list,
        threshold: float = 2.0
    ) -> list:
        """
        Detect price anomalies using statistical methods

        Args:
            prices: List of prices
            threshold: Z-score threshold (default 2.0)

        Returns:
            List of anomaly indices
        """
        if len(prices) < 3:
            return []

        import numpy as np

        prices_array = np.array(prices)
        mean = np.mean(prices_array)
        std = np.std(prices_array)

        if std == 0:
            return []

        z_scores = np.abs((prices_array - mean) / std)
        anomalies = np.where(z_scores > threshold)[0].tolist()

        return anomalies