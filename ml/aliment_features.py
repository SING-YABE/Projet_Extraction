"""
ML Feature Engineering pour aliments
"""
import pandas as pd
import numpy as np


def prepare_aliment_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prépare features ML pour prix aliments

    Args:
        df: DataFrame avec colonnes: prix, aliment_type, categorie, date

    Returns:
        DataFrame avec features ML (8 features)
    """
    df_feat = df.copy()

    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_feat['date']):
        df_feat['date'] = pd.to_datetime(df_feat['date'])

    # ===== TEMPORAL FEATURES (4) =====
    df_feat['year'] = df_feat['date'].dt.year
    df_feat['month'] = df_feat['date'].dt.month
    df_feat['day_of_week'] = df_feat['date'].dt.dayofweek
    df_feat['week_of_year'] = df_feat['date'].dt.isocalendar().week

    # Season (Burkina Faso)
    # 1 = Rainy (Jun-Oct), 2 = Dry Cold (Nov-Feb), 3 = Dry Hot (Mar-May)
    df_feat['season'] = df_feat['month'].apply(get_season)

    # ===== CATEGORICAL ENCODING (1) =====
    categorie_map = {
        'ÉNERGÉTIQUE': 1,
        'PROTÉINE': 2,
        'MINÉRAUX': 3,
        'VITAMINES': 4,
        'AUTRE': 0
    }
    df_feat['categorie_encoded'] = df_feat['categorie'].map(categorie_map).fillna(0)

    # ===== MARKET FEATURES (1) =====
    # Nombre de prix d'aliments ce jour
    df_feat['nb_prix_jour'] = df_feat.groupby('date')['prix'].transform('count')

    # ===== LAG FEATURES (1) =====
    # Prix précédent pour cet aliment
    df_feat = df_feat.sort_values('date')
    df_feat['prix_precedent'] = df_feat.groupby('aliment_type')['prix'].shift(1)
    df_feat['prix_precedent'] = df_feat['prix_precedent'].fillna(df_feat['prix'])

    # ===== TREND FEATURES (1) =====
    # Tendance prix (%)
    df_feat['tendance_pct'] = df_feat.groupby('aliment_type')['prix'].pct_change() * 100
    df_feat['tendance_pct'] = df_feat['tendance_pct'].fillna(0)

    return df_feat


def get_season(month: int) -> int:
    """
    Retourne la saison au Burkina Faso

    Args:
        month: Mois (1-12)

    Returns:
        1 = Saison pluies (Jun-Oct)
        2 = Saison sèche froide (Nov-Feb)
        3 = Saison sèche chaude (Mar-May)
    """
    if month in [6, 7, 8, 9, 10]:  # Rainy season
        return 1
    elif month in [11, 12, 1, 2]:  # Dry cold
        return 2
    else:  # Dry hot (3, 4, 5)
        return 3


def get_aliment_feature_names() -> list:
    """
    Retourne la liste des noms de features pour aliments

    Returns:
        Liste des 8 features
    """
    return [
        'month',
        'season',
        'categorie_encoded',
        'nb_prix_jour',
        'prix_precedent',
        'tendance_pct',
        'day_of_week',
        'week_of_year'
    ]