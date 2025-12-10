"""
Prédicteur ML pour prix aliments
"""
import pandas as pd
from datetime import datetime
from typing import Dict
import pickle
from pathlib import Path

from ml.aliment_features import prepare_aliment_features
from utils.logger import logger


class AlimentPredictor:
    """Prédicteur de prix aliments avec modèle ML"""

    def __init__(self, model_path: str = "ml/models/xgboost_aliments.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self.stats = None
        self.feature_names = None

        if self.model_path.exists():
            self.load()

    @property
    def is_trained(self) -> bool:
        """Vérifie si le modèle est entraîné"""
        return self.model is not None

    def load(self):
        """Charge le modèle entraîné"""
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)

            self.model = data['model']
            self.stats = data['stats']
            self.feature_names = data['feature_names']

            logger.info(f"✅ Modèle ALIMENTS chargé depuis {self.model_path}")
            logger.info(f"   Features: {len(self.feature_names)}")
            logger.info(f"   MAE: {self.stats['mae']:.0f} FCFA")
            logger.info(f"   R²: {self.stats['r2']:.3f}")
        except Exception as e:
            logger.error(f"❌ Erreur chargement modèle aliments: {e}")
            self.model = None

    def predict_batch(self, df: pd.DataFrame) -> pd.Series:
        """
        Prédit prix pour batch d'aliments

        Args:
            df: DataFrame avec colonnes nécessaires

        Returns:
            Series de prédictions
        """
        if not self.model:
            raise ValueError("Modèle non chargé")

        features = prepare_aliment_features(df)
        X = features[self.feature_names].fillna(0)

        predictions = self.model.predict(X)

        return pd.Series(predictions, index=df.index)

    def predict_single(
        self,
        aliment_type: str,
        date: datetime,
        categorie: str = None
    ) -> int:
        """
        Prédit prix pour un aliment à une date donnée

        Args:
            aliment_type: Type d'aliment (maïs, soja, etc.)
            date: Date de prédiction
            categorie: Catégorie (auto-détecté si non fourni)

        Returns:
            Prix prédit en FCFA
        """
        if not self.model:
            raise ValueError("Modèle non entraîné")

        # Auto-detect category if not provided
        if not categorie:
            categorie = self._detect_categorie(aliment_type)

        # Create DataFrame
        df = pd.DataFrame({
            'date': [date],
            'aliment_type': [aliment_type],
            'categorie': [categorie],
            'prix': [0]  # Placeholder
        })

        # Predict
        prediction = self.predict_batch(df)[0]

        # Validation
        prix_predit = max(1000, int(prediction))
        prix_predit = min(prix_predit, 100000)  # Max 100k FCFA

        return prix_predit

    def predict_by_categorie(
        self,
        categorie: str,
        date: datetime
    ) -> Dict[str, int]:
        """
        Prédit prix moyens par catégorie

        Args:
            categorie: ÉNERGÉTIQUE, PROTÉINE, MINÉRAUX, VITAMINES
            date: Date de prédiction

        Returns:
            Dict avec prix prédits par aliment type
        """
        if not self.model:
            raise ValueError("Modèle non entraîné")

        # Aliments représentatifs par catégorie
        aliments_by_cat = {
            'ÉNERGÉTIQUE': ['maïs', 'mil', 'son de blé'],
            'PROTÉINE': ['soja', 'tourteau soja', 'tourteau coton'],
            'MINÉRAUX': ['complément minéral', 'sel', 'cmv'],
            'VITAMINES': ['concentré', 'prémix', 'provende']
        }

        aliments = aliments_by_cat.get(categorie, [])

        predictions = {}
        for aliment in aliments:
            try:
                prix = self.predict_single(aliment, date, categorie)
                predictions[aliment] = prix
            except Exception as e:
                logger.warning(f"Erreur prédiction {aliment}: {e}")

        return predictions

    def _detect_categorie(self, aliment_type: str) -> str:
        """Détecte automatiquement la catégorie d'un aliment"""
        aliment = aliment_type.lower()

        categories = {
            'ÉNERGÉTIQUE': ['maïs', 'mil', 'sorgho', 'riz', 'son', 'manioc'],
            'PROTÉINE': ['soja', 'tourteau', 'farine de poisson', 'drêche'],
            'MINÉRAUX': ['minéral', 'sel', 'phosphate', 'coquille', 'pierre'],
            'VITAMINES': ['concentré', 'prémix', 'provende', 'cmv', 'siatol']
        }

        for cat, keywords in categories.items():
            if any(kw in aliment for kw in keywords):
                return cat

        return 'AUTRE'

    def get_stats(self) -> Dict:
        """Retourne les statistiques du modèle"""
        if not self.stats:
            return {}

        return {
            'is_trained': self.is_trained,
            'nb_samples': self.stats.get('nb_samples', 0),
            'mae': self.stats.get('mae', 0),
            'r2': self.stats.get('r2', 0),
            'mape': self.stats.get('mape', 0),
            'prix_moyen': self.stats.get('prix_global_mean', 0)
        }