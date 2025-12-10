"""
Détection d'anomalies et opportunités
À implémenter avec minimum 200+ prix annotés
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from ..utils import setup_logger, PRICE_RANGES

logger = setup_logger(__name__)


class AnomalyDetector:
    """
    Détecteur d'anomalies de prix
    
    Note: Nécessite au moins 200 prix pour être fiable
    """
    
    def __init__(self):
        self.thresholds = {}
        self.opportunities = []
    
    def fit(self, df: pd.DataFrame) -> bool:
        """
        Entraîne le détecteur sur des données historiques
        
        Args:
            df: DataFrame avec 'prix', 'animal_type'
        
        Returns:
            True si succès
        """
        if len(df) < 50:
            logger.warning(f"Seulement {len(df)} exemples - minimum 200 recommandé")
        
        # Calculer seuils par type d'animal
        for animal_type in df['animal_type'].unique():
            if animal_type == 'non_specifie':
                continue
            
            animal_df = df[df['animal_type'] == animal_type]
            
            if len(animal_df) < 10:
                continue
            
            # Méthode IQR
            Q1 = animal_df['prix'].quantile(0.25)
            Q3 = animal_df['prix'].quantile(0.75)
            IQR = Q3 - Q1
            
            self.thresholds[animal_type] = {
                'Q1': Q1,
                'Q3': Q3,
                'IQR': IQR,
                'lower': Q1 - 1.5 * IQR,
                'upper': Q3 + 1.5 * IQR,
                'median': animal_df['prix'].median()
            }
        
        logger.info(f"Détecteur entraîné sur {len(self.thresholds)} types")
        return True
    
    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Détecte les anomalies dans un DataFrame
        
        Args:
            df: DataFrame à analyser
        
        Returns:
            DataFrame avec colonne 'is_anomaly'
        """
        df_result = df.copy()
        df_result['is_anomaly'] = False
        df_result['anomaly_type'] = 'normal'
        
        for idx, row in df_result.iterrows():
            animal_type = row.get('animal_type', 'non_specifie')
            prix = row.get('prix', 0)
            
            if animal_type not in self.thresholds:
                continue
            
            thresh = self.thresholds[animal_type]
            
            if prix < thresh['lower']:
                df_result.at[idx, 'is_anomaly'] = True
                df_result.at[idx, 'anomaly_type'] = 'prix_bas'
            elif prix > thresh['upper']:
                df_result.at[idx, 'is_anomaly'] = True
                df_result.at[idx, 'anomaly_type'] = 'prix_haut'
        
        return df_result
    
    def find_opportunities(
        self, 
        df: pd.DataFrame,
        opportunity_threshold: float = 0.20
    ) -> List[Dict]:
        """
        Trouve les bonnes affaires (prix < médiane - threshold)
        
        Args:
            df: DataFrame avec prix
            opportunity_threshold: Réduction minimum (ex: 0.20 = 20%)
        
        Returns:
            Liste d'opportunités
        """
        opportunities = []
        
        for idx, row in df.iterrows():
            animal_type = row.get('animal_type', 'non_specifie')
            prix = row.get('prix', 0)
            
            if animal_type not in self.thresholds:
                continue
            
            thresh = self.thresholds[animal_type]
            median_price = thresh['median']
            
            reduction = (median_price - prix) / median_price
            
            if reduction >= opportunity_threshold:
                opportunities.append({
                    'message_id': row.get('message_id'),
                    'animal_type': animal_type,
                    'prix': prix,
                    'prix_median': median_price,
                    'reduction_pct': reduction * 100,
                    'score': min(100, reduction * 100 * 2),  # Score 0-100
                    'date': row.get('date')
                })
        
        # Trier par score
        opportunities = sorted(
            opportunities, 
            key=lambda x: x['score'], 
            reverse=True
        )
        
        logger.info(f"✓ {len(opportunities)} opportunités trouvées")
        return opportunities
    
    def score_opportunity(
        self, 
        prix: int, 
        animal_type: str
    ) -> Tuple[float, str]:
        """
        Score une opportunité (0-100)
        
        Args:
            prix: Prix proposé
            animal_type: Type d'animal
        
        Returns:
            (score, évaluation)
        """
        if animal_type not in self.thresholds:
            return (50.0, "Pas de référence")
        
        thresh = self.thresholds[animal_type]
        median = thresh['median']
        
        reduction = (median - prix) / median
        score = min(100, max(0, reduction * 100 * 2))
        
        if score >= 80:
            evaluation = "Excellente affaire"
        elif score >= 60:
            evaluation = "Bonne affaire"
        elif score >= 40:
            evaluation = "Prix correct"
        elif score >= 20:
            evaluation = "Prix normal"
        else:
            evaluation = "Prix élevé"
        
        return (score, evaluation)


# TODO: Implémenter avec plus de données
# - Isolation Forest ML
# - DBSCAN clustering
# - Autoencoder pour anomalies complexes
# - Alertes temps réel
