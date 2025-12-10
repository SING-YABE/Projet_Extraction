"""
ML Feature Engineering
"""
import pandas as pd
import numpy as np
from datetime import timedelta


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare ML features from raw data

    Args:
        df: DataFrame with 'date', 'prix', 'animal_type', etc.

    Returns:
        DataFrame with ML features
    """
    df_feat = df.copy()

    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_feat['date']):
        df_feat['date'] = pd.to_datetime(df_feat['date'])

    # Temporal features
    df_feat['year'] = df_feat['date'].dt.year
    df_feat['month'] = df_feat['date'].dt.month
    df_feat['day_of_week'] = df_feat['date'].dt.dayofweek
    df_feat['day_of_month'] = df_feat['date'].dt.day
    df_feat['week_of_year'] = df_feat['date'].dt.isocalendar().week

    # Season (Burkina Faso)
    df_feat['season'] = df_feat['month'].apply(get_season)

    # Encode categorical
    animal_map = {'porcelet': 1, 'truie': 2, 'verrat': 3, 'porc': 4}
    df_feat['animal_encoded'] = df_feat['animal_type'].map(animal_map).fillna(0)

    action_map = {'vente': 1, 'achat': 2, 'prix_info': 3}
    df_feat['action_encoded'] = df_feat['action_type'].map(action_map).fillna(0)

    # Market features
    df_feat['nb_prix_jour'] = df_feat.groupby('date')['prix'].transform('count')

    if 'vendeur' in df_feat.columns:
        df_feat['nb_vendeurs_jour'] = df_feat.groupby('date')['vendeur'].transform('nunique')
    else:
        df_feat['nb_vendeurs_jour'] = 1

    df_feat['week_key'] = df_feat['date'].dt.to_period('W')
    df_feat['volume_semaine'] = df_feat.groupby('week_key')['prix'].transform('count')

    # Lag features
    df_feat = df_feat.sort_values('date')
    df_feat['prix_precedent'] = df_feat.groupby('animal_type')['prix'].shift(1)

    # Moving average
    df_feat['prix_ma7'] = df_feat.groupby('animal_type')['prix'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )

    # Trend
    df_feat['tendance_pct'] = df_feat.groupby('animal_type')['prix'].pct_change() * 100
    df_feat['tendance_pct'] = df_feat['tendance_pct'].fillna(0)

    # Statistical features
    df_feat['prix_median_animal'] = df_feat.groupby('animal_type')['prix'].transform('median')
    df_feat['ecart_median'] = (df_feat['prix'] - df_feat['prix_median_animal']) / df_feat['prix_median_animal'] * 100

    # Clean
    df_feat = df_feat.drop(columns=['week_key'], errors='ignore')

    return df_feat


def get_season(month: int) -> int:
    """Season in Burkina Faso"""
    if month in [6, 7, 8, 9, 10]:  # Rainy
        return 1
    elif month in [11, 12, 1, 2]:  # Dry cold
        return 2
    else:  # Dry hot
        return 3


# Ajouter après la fonction get_season()

def prepare_features_with_aliment_predictions(
        df: pd.DataFrame,
        prix_mais_predit: float,
        prix_soja_predit: float,
        prix_concentre_predit: float
) -> pd.DataFrame:
    """
    Prépare features animaux en utilisant prix aliments PRÉDITS

    Args:
        df: DataFrame avec données animaux
        prix_mais_predit: Prix maïs prédit
        prix_soja_predit: Prix soja prédit
        prix_concentre_predit: Prix concentré prédit

    Returns:
        DataFrame avec 17 features (13 animal + 4 aliment)
    """
    # Préparer features animaux standard (13 features)
    df_feat = prepare_features(df)

    # ===== AJOUTER FEATURES ALIMENTS PRÉDITS (4 features) =====

    # Prix aliments prédits
    df_feat['prix_mais_ma7'] = prix_mais_predit
    df_feat['prix_soja_ma7'] = prix_soja_predit
    df_feat['prix_concentre_ma7'] = prix_concentre_predit

    # Indice coût alimentation (moyenne pondérée)
    df_feat['indice_aliment'] = (
            prix_mais_predit * 0.5 +  # 50% maïs
            prix_soja_predit * 0.3 +  # 30% soja
            prix_concentre_predit * 0.2  # 20% concentré
    )

    return df_feat


def get_extended_feature_names() -> list:
    """
    Retourne la liste des 17 features (13 animal + 4 aliment)

    Returns:
        Liste des 17 noms de features
    """
    base_features = [
        'month',
        'season',
        'animal_encoded',
        'action_encoded',
        'nb_prix_jour',
        'nb_vendeurs_jour',
        'volume_semaine',
        'prix_precedent',
        'prix_ma7',
        'tendance_pct',
        'prix_median_animal',
        'ecart_median',
        'day_of_week'
    ]

    aliment_features = [
        'prix_mais_ma7',
        'prix_soja_ma7',
        'prix_concentre_ma7',
        'indice_aliment'
    ]

    return base_features + aliment_features

# ========== ALIMENT FEATURES ==========

CATEGORIES_ALIMENTS = {
    'ÉNERGÉTIQUE': ['maïs', 'mil', 'sorgho', 'riz', 'son de blé', 'son de maïs', 'manioc'],
    'PROTÉINE': ['soja', 'tourteau soja', 'tourteau coton', 'tourteau arachide', 'farine de poisson', 'drêche'],
    'MINÉRAUX': ['complément minéral', 'pierre à lécher', 'sel', 'phosphate', 'coquille', 'cmv'],
    'VITAMINES': ['concentré', 'prémix', 'siatol', 'provende', 'aliment complet']
}


def get_categorie_aliment(aliment_type: str) -> str:
    """Auto-detect aliment category"""
    if not aliment_type:
        return 'AUTRE'

    aliment = aliment_type.lower()
    for categorie, aliments in CATEGORIES_ALIMENTS.items():
        if any(a in aliment for a in aliments):
            return categorie
    return 'AUTRE'


def prepare_aliment_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare ML features for aliment prices

    Args:
        df: DataFrame with aliment data

    Returns:
        DataFrame with ML features
    """
    df_feat = df.copy()

    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_feat['date']):
        df_feat['date'] = pd.to_datetime(df_feat['date'])

    # Temporal features
    df_feat['year'] = df_feat['date'].dt.year
    df_feat['month'] = df_feat['date'].dt.month
    df_feat['day_of_week'] = df_feat['date'].dt.dayofweek
    df_feat['week_of_year'] = df_feat['date'].dt.isocalendar().week

    # Season
    df_feat['season'] = df_feat['month'].apply(get_season)

    # Encode categorical
    categorie_map = {'ÉNERGÉTIQUE': 1, 'PROTÉINE': 2, 'MINÉRAUX': 3, 'VITAMINES': 4, 'AUTRE': 0}
    df_feat['categorie_encoded'] = df_feat['categorie'].map(categorie_map).fillna(0)

    # Market features
    df_feat['nb_prix_jour'] = df_feat.groupby('date')['prix'].transform('count')

    # Lag features
    df_feat = df_feat.sort_values('date')
    df_feat['prix_precedent'] = df_feat.groupby('aliment_type')['prix'].shift(1)

    # Moving average
    df_feat['prix_ma7'] = df_feat.groupby('aliment_type')['prix'].transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )

    # Trend
    df_feat['tendance_pct'] = df_feat.groupby('aliment_type')['prix'].pct_change() * 100
    df_feat['tendance_pct'] = df_feat['tendance_pct'].fillna(0)

    return df_feat