"""
ML Predictor (uses trained model)
"""
import pandas as pd
from datetime import datetime
from typing import Dict, Optional
import pickle
from pathlib import Path

from ml.features import prepare_features
from utils.logger import logger


class MLPredictor:
    """ML Price Predictor (wrapper for trained model)"""

    def __init__(self, model_path: str = "ml/models/xgboost_model.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.stats = None
        self.feature_names = None

        if self.model_path.exists():
            self.load()

    @property
    def is_trained(self) -> bool:
        """Check if model is trained and loaded"""
        return self.model is not None

    def load(self):
        """Load trained model"""
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)

        self.model = data['model']
        self.stats = data['stats']
        self.feature_names = data['feature_names']

        logger.info(f"ML model loaded from {self.model_path}")

    def predict_batch(self, df: pd.DataFrame) -> pd.Series:
        """
        Predict prices for batch (DataFrame)

        Args:
            df: DataFrame with features

        Returns:
            Series of predictions
        """
        if not self.model:
            raise ValueError("Model not loaded")

        features = prepare_features(df)
        X = features[self.feature_names].fillna(0)
        predictions = self.model.predict(X)

        return pd.Series(predictions, index=df.index)

    def predict_single(
            self,
            animal_type: str,
            date: datetime,
            action_type: str = 'vente',
            aliment_predictor=None  # ✅ NOUVEAU paramètre
    ) -> int:
        """
        Prédit prix animal (avec cascade aliments si disponible)

        Args:
            animal_type: Type d'animal
            date: Date de prédiction
            action_type: Type d'action
            aliment_predictor: Prédicteur aliments (optionnel, pour cascade)

        Returns:
            Prix prédit en FCFA
        """

        # ===== MODE CASCADE : Utilise modèle aliments =====
        if aliment_predictor and aliment_predictor.is_trained:
            logger.info("🔄 MODE CASCADE : Prédiction aliments → animaux")

            # ÉTAPE 1 : Prédire prix aliments futurs
            try:
                prix_mais = aliment_predictor.predict_single('maïs', date, 'ÉNERGÉTIQUE')
                prix_soja = aliment_predictor.predict_single('soja', date, 'PROTÉINE')
                prix_concentre = aliment_predictor.predict_single('concentré', date, 'VITAMINES')

                logger.info(f"   Aliments prédits: Maïs={prix_mais}, Soja={prix_soja}, Concentré={prix_concentre}")
            except Exception as e:
                logger.warning(f"⚠️  Erreur prédiction aliments, fallback mode standard: {e}")
                return self._predict_without_aliments(animal_type, date, action_type)

            # ÉTAPE 2 : Créer DataFrame avec features aliments prédits
            df = pd.DataFrame({
                'date': [date],
                'animal_type': [animal_type],
                'action_type': [action_type],
                'prix': [0]
            })

            # Préparer features avec aliments prédits
            from ml.features import prepare_features_with_aliment_predictions, get_extended_feature_names

            features = prepare_features_with_aliment_predictions(
                df,
                prix_mais_predit=prix_mais,
                prix_soja_predit=prix_soja,
                prix_concentre_predit=prix_concentre
            )

            # Vérifier que le modèle a les bonnes features (17)
            feature_names = get_extended_feature_names()

            # Si le modèle actuel n'a que 13 features, fallback
            if len(self.feature_names) < 17:
                logger.warning("⚠️  Modèle animaux entraîné sans features aliments, fallback mode standard")
                return self._predict_without_aliments(animal_type, date, action_type)

            X = features[feature_names].fillna(0)
            prediction = self.predict_batch(df)[0]

            logger.info(f"✅ Prédiction CASCADE: {int(prediction)} FCFA")

        else:
            # ===== MODE STANDARD : Sans aliments =====
            logger.info("📊 MODE STANDARD : Prédiction animaux uniquement")
            prediction = self._predict_without_aliments(animal_type, date, action_type)

        return max(1000, int(prediction))

    def _predict_without_aliments(
            self,
            animal_type: str,
            date: datetime,
            action_type: str = 'vente'
    ) -> int:
        """
        Prédiction sans features aliments (mode standard)

        Args:
            animal_type: Type d'animal
            date: Date
            action_type: Type d'action

        Returns:
            Prix prédit
        """
        df = pd.DataFrame({
            'date': [date],
            'animal_type': [animal_type],
            'action_type': [action_type],
            'prix': [0]
        })

        prediction = self.predict_batch(df)[0]

        return max(1000, int(prediction))

    def predict(self, animal_type: str = None, date: datetime = None, df: pd.DataFrame = None):
        """
        Predict price - supports both DataFrame and individual parameters

        Args:
            animal_type: Animal type (for individual prediction)
            date: Date (for individual prediction)
            df: DataFrame with features (for batch prediction)

        Returns:
            Dict with prediction or Series for DataFrame
        """
        # If DataFrame provided, use batch prediction
        if df is not None and isinstance(df, pd.DataFrame):
            return self.predict_batch(df)

        # Individual prediction
        if animal_type is not None and date is not None:
            prix_predit = self.predict_single(animal_type, date)
            intervalle = int(prix_predit * 0.2)

            return {
                'prix_predit': prix_predit,
                'intervalle_min': prix_predit - intervalle,
                'intervalle_max': prix_predit + intervalle,
                'confiance': 'moyenne' if self.stats else 'faible'
            }

        raise ValueError("Provide either df or (animal_type and date)")

    def predict_future(self, animal_type: str, months: int = 3) -> list:
        """Predict prices for next N months"""
        from datetime import timedelta

        predictions = []
        current_date = datetime.now()

        for month in range(1, months + 1):
            future_date = current_date + timedelta(days=30 * month)

            # Use predict with named arguments
            pred = self.predict(animal_type=animal_type, date=future_date)

            predictions.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'animal_type': animal_type,
                **pred
            })

        return predictions


# Backward compatibility alias
PricePredictor = MLPredictor