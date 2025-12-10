"""
Analyse des tendances de prix
À implémenter avec minimum 200+ prix sur 3+ mois
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ..utils import setup_logger, AnimalTypes

logger = setup_logger(__name__)


class TrendAnalyzer:
    """
    Analyseur de tendances de prix
    
    Note: Nécessite au moins 200 prix sur 3+ mois pour fonctionner
    """
    
    def __init__(self):
        self.data = None
        self.trends = {}
    
    def load_data(self, df: pd.DataFrame) -> bool:
        """
        Charge les données pour analyse
        
        Args:
            df: DataFrame avec colonnes 'date', 'prix', 'animal_type'
        
        Returns:
            True si données suffisantes
        """
        if 'date' not in df.columns or 'prix' not in df.columns:
            logger.error("Colonnes 'date' et 'prix' requises")
            return False
        
        # Convertir dates
        df['date'] = pd.to_datetime(df['date'])
        self.data = df.copy()
        
        # Vérifier suffisamment de données
        if len(df) < 50:
            logger.warning(f"Seulement {len(df)} prix - minimum 200 recommandé")
        
        return True
    
    def analyze_monthly_trends(self) -> pd.DataFrame:
        """
        Analyse les tendances mensuelles
        
        Returns:
            DataFrame avec stats mensuelles
        """
        if self.data is None:
            logger.error("Charger les données d'abord avec load_data()")
            return pd.DataFrame()
        
        # Grouper par mois et type animal
        monthly = self.data.groupby([
            pd.Grouper(key='date', freq='M'),
            'animal_type'
        ])['prix'].agg(['count', 'mean', 'median', 'std', 'min', 'max'])
        
        logger.info(f"Analyse mensuelle: {len(monthly)} périodes")
        return monthly.round(0)
    
    def detect_seasonal_patterns(self) -> Dict:
        """
        Détecte les patterns saisonniers
        
        Returns:
            Dictionnaire avec patterns par saison
        """
        if self.data is None:
            return {}
        
        # Ajouter colonne mois
        self.data['month'] = self.data['date'].dt.month
        
        # Stats par mois
        seasonal = self.data.groupby('month')['prix'].agg(['mean', 'std'])
        
        patterns = {
            'monthly_avg': seasonal['mean'].to_dict(),
            'monthly_std': seasonal['std'].to_dict()
        }
        
        return patterns
    
    def compare_periods(
        self, 
        start1: str, 
        end1: str, 
        start2: str, 
        end2: str
    ) -> Dict:
        """
        Compare deux périodes
        
        Args:
            start1, end1: Période 1
            start2, end2: Période 2
        
        Returns:
            Dictionnaire avec comparaison
        """
        if self.data is None:
            return {}
        
        period1 = self.data[
            (self.data['date'] >= start1) & 
            (self.data['date'] <= end1)
        ]
        
        period2 = self.data[
            (self.data['date'] >= start2) & 
            (self.data['date'] <= end2)
        ]
        
        comparison = {
            'period1': {
                'mean': period1['prix'].mean(),
                'count': len(period1)
            },
            'period2': {
                'mean': period2['prix'].mean(),
                'count': len(period2)
            },
            'change_pct': (
                (period2['prix'].mean() - period1['prix'].mean()) / 
                period1['prix'].mean() * 100
            ) if len(period1) > 0 else 0
        }
        
        return comparison
    
    def get_price_evolution(self, animal_type: str) -> pd.Series:
        """
        Évolution des prix pour un type d'animal
        
        Args:
            animal_type: Type d'animal
        
        Returns:
            Series avec prix moyens mensuels
        """
        if self.data is None:
            return pd.Series()
        
        animal_data = self.data[self.data['animal_type'] == animal_type]
        
        evolution = animal_data.groupby(
            pd.Grouper(key='date', freq='M')
        )['prix'].mean()
        
        return evolution


# TODO: Implémenter avec plus de données
# - Prédiction tendances (ARIMA)
# - Détection changements de régime
# - Corrélations avec événements externes
# - Forecasting simple
