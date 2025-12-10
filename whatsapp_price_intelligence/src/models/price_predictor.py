"""
Prédiction de prix
À implémenter avec minimum 500+ prix sur 6+ mois
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..utils import setup_logger, ML_CONFIG

logger = setup_logger(__name__)


class PricePredictor:
    """
    Prédicteur de prix ML
    
    Note: Nécessite au moins 500 prix sur 6 mois minimum
    """
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.features = []
        self.scaler = None
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prépare les features pour ML
        
        Args:
            df: DataFrame brut
        
        Returns:
            DataFrame avec features
        """
        df_feat = df.copy()
        
        # Features temporelles
        df_feat['year'] = df_feat['date'].dt.year
        df_feat['month'] = df_feat['date'].dt.month
        df_feat['day_of_week'] = df_feat['date'].dt.dayofweek
        df_feat['day_of_month'] = df_feat['date'].dt.day
        
        # Saison (1=sec, 2=pluie, 3=transition)
        df_feat['season'] = df_feat['month'].apply(self._get_season)
        
        # Features de marché
        df_feat['nb_vendeurs'] = df_feat.groupby('date')['sender'].transform('nunique')
        df_feat['volume_jour'] = df_feat.groupby('date')['message_id'].transform('count')
        
        # Features de tendance (lag)
        df_feat = df_feat.sort_values('date')
        df_feat['prix_precedent'] = df_feat.groupby('animal_type')['prix'].shift(1)
        df_feat['tendance'] = df_feat.groupby('animal_type')['prix'].pct_change()
        
        return df_feat
    
    def _get_season(self, month: int) -> int:
        """Saison au Burkina Faso"""
        if month in [6, 7, 8, 9, 10]:  # Pluies
            return 1
        elif month in [11, 12, 1, 2]:  # Sec
            return 2
        else:  # Transition
            return 3
    
    def train(self, df: pd.DataFrame) -> bool:
        """
        Entraîne le modèle
        
        Args:
            df: DataFrame avec données historiques
        
        Returns:
            True si succès
        """
        if len(df) < 100:
            logger.error(
                f"Seulement {len(df)} exemples - "
                "minimum 500 recommandé pour prédiction fiable"
            )
            return False
        
        # Vérifier span temporel
        date_span = (df['date'].max() - df['date'].min()).days
        if date_span < 90:
            logger.warning(
                f"Seulement {date_span} jours de données - "
                "minimum 180 jours recommandé"
            )
        
        logger.info(f"Entraînement sur {len(df)} prix, {date_span} jours")
        
        # TODO: Implémenter avec scikit-learn/XGBoost
        # - Préparer features
        # - Split train/test
        # - Entraîner modèle
        # - Valider performances
        # - Sauvegarder modèle
        
        logger.warning("⚠ Prédiction ML pas encore implémentée")
        logger.info("Collectez plus de données puis implémentez ce module")
        
        return False
    
    def predict(
        self, 
        animal_type: str, 
        date: datetime,
        **kwargs
    ) -> Optional[float]:
        """
        Prédit un prix
        
        Args:
            animal_type: Type d'animal
            date: Date de prédiction
            **kwargs: Features additionnelles
        
        Returns:
            Prix prédit ou None
        """
        if not self.is_trained:
            logger.error("Modèle pas entraîné. Utiliser .train() d'abord")
            return None
        
        # TODO: Implémenter prédiction
        return None
    
    def predict_future(
        self, 
        animal_type: str, 
        months_ahead: int = 3
    ) -> List[Dict]:
        """
        Prédit les prix futurs
        
        Args:
            animal_type: Type d'animal
            months_ahead: Nombre de mois à prédire
        
        Returns:
            Liste de prédictions avec intervalles de confiance
        """
        if not self.is_trained:
            logger.error("Modèle pas entraîné")
            return []
        
        predictions = []
        current_date = datetime.now()
        
        for month in range(1, months_ahead + 1):
            future_date = current_date + timedelta(days=30 * month)
            
            # TODO: Implémenter prédiction
            pred_price = None  # self.predict(animal_type, future_date)
            
            predictions.append({
                'date': future_date,
                'animal_type': animal_type,
                'prix_predit': pred_price,
                'intervalle_min': None,  # Confidence interval
                'intervalle_max': None
            })
        
        return predictions
    
    def evaluate(self, df_test: pd.DataFrame) -> Dict:
        """
        Évalue les performances du modèle
        
        Args:
            df_test: Données de test
        
        Returns:
            Dictionnaire avec métriques (MAE, RMSE, MAPE)
        """
        if not self.is_trained:
            return {}
        
        # TODO: Implémenter évaluation
        metrics = {
            'MAE': None,  # Mean Absolute Error
            'RMSE': None,  # Root Mean Squared Error
            'MAPE': None,  # Mean Absolute Percentage Error
            'R2': None
        }
        
        return metrics


# TODO: À implémenter quand données suffisantes
# Options de modèles:
# 1. ARIMA/SARIMA - Séries temporelles classiques
# 2. Prophet (Facebook) - Séries temporelles avec saisonnalité
# 3. XGBoost/LightGBM - Gradient boosting avec features
# 4. LSTM - Deep learning pour séries temporelles
# 5. Ensemble - Combiner plusieurs modèles
