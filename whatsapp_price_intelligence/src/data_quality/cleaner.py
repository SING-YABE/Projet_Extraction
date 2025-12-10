"""
Nettoyage avancé des données
"""
import pandas as pd
import re
from typing import List, Dict
from ..utils import setup_logger

logger = setup_logger(__name__)


class DataCleaner:
    """Nettoyeur de données avancé"""
    
    def __init__(self):
        self.cleaning_stats = {
            'duplicates_removed': 0,
            'outliers_removed': 0,
            'missing_filled': 0,
            'texts_normalized': 0
        }
    
    def clean_dataframe(self, df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
        """
        Nettoie un DataFrame complet
        
        Args:
            df: DataFrame à nettoyer
            aggressive: Si True, nettoyage plus agressif
        
        Returns:
            DataFrame nettoyé
        """
        logger.info(f"Début nettoyage: {len(df)} lignes")
        
        df_clean = df.copy()
        
        # 1. Supprimer doublons exacts
        df_clean = self._remove_duplicates(df_clean)
        
        # 2. Normaliser les textes
        if 'message' in df_clean.columns:
            df_clean = self._normalize_texts(df_clean)
        
        # 3. Traiter valeurs manquantes
        df_clean = self._handle_missing_values(df_clean)
        
        # 4. Supprimer outliers (si agressif)
        if aggressive and 'prix' in df_clean.columns:
            df_clean = self._remove_outliers(df_clean)
        
        # 5. Réinitialiser index
        df_clean = df_clean.reset_index(drop=True)
        
        logger.info(f"Nettoyage terminé: {len(df_clean)} lignes restantes")
        logger.info(f"Stats: {self.cleaning_stats}")
        
        return df_clean
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Supprime les doublons"""
        initial_len = len(df)
        df_clean = df.drop_duplicates(subset=['message'], keep='first')
        removed = initial_len - len(df_clean)
        self.cleaning_stats['duplicates_removed'] = removed
        
        if removed > 0:
            logger.info(f"✓ {removed} doublons supprimés")
        
        return df_clean
    
    def _normalize_texts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalise les textes"""
        df['message'] = df['message'].apply(self._normalize_text)
        self.cleaning_stats['texts_normalized'] = len(df)
        return df
    
    def _normalize_text(self, text: str) -> str:
        """Normalise un texte"""
        if pd.isna(text):
            return ""
        
        # Supprimer espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Supprimer caractères spéciaux inutiles
        text = re.sub(r'[^\w\s\d.,!?àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ-]', '', text)
        
        # Trim
        text = text.strip()
        
        return text
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Gère les valeurs manquantes"""
        # Remplir animal_type manquant
        if 'animal_type' in df.columns:
            df['animal_type'] = df['animal_type'].fillna('non_specifie')
        
        # Remplir action_type manquant
        if 'action_type' in df.columns:
            df['action_type'] = df['action_type'].fillna('non_specifie')
        
        # Supprimer lignes sans message
        if 'message' in df.columns:
            df = df[df['message'].notna() & (df['message'] != '')]
        
        return df
    
    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Supprime les outliers de prix"""
        if 'prix' not in df.columns:
            return df
        
        initial_len = len(df)
        
        # Méthode IQR
        Q1 = df['prix'].quantile(0.25)
        Q3 = df['prix'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        df_clean = df[(df['prix'] >= lower_bound) & (df['prix'] <= upper_bound)]
        
        removed = initial_len - len(df_clean)
        self.cleaning_stats['outliers_removed'] = removed
        
        if removed > 0:
            logger.warning(f"⚠ {removed} outliers supprimés")
        
        return df_clean
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de nettoyage"""
        return self.cleaning_stats.copy()


def clean_data(df: pd.DataFrame, aggressive: bool = False) -> pd.DataFrame:
    """
    Fonction utilitaire pour nettoyer rapidement
    
    Args:
        df: DataFrame à nettoyer
        aggressive: Nettoyage agressif
    
    Returns:
        DataFrame nettoyé
    """
    cleaner = DataCleaner()
    return cleaner.clean_dataframe(df, aggressive=aggressive)
