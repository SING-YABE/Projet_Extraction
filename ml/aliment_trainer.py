"""
Entraînement modèle ML pour aliments
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import pickle
from pathlib import Path
from typing import List, Dict

from ml.aliment_features import prepare_aliment_features, get_aliment_feature_names
from utils.logger import logger


def train_aliment_model(aliments: List[dict]) -> Dict:
    """
    Entraîne modèle XGBoost pour prédire prix aliments

    Args:
        aliments: Liste de dicts avec prix aliments

    Returns:
        Dict avec métriques (mae, rmse, r2, mape, samples)
    """

    if len(aliments) < 50:
        raise ValueError(f"Besoin d'au moins 50 prix aliments pour entraîner. Actuellement: {len(aliments)}")

    logger.info(f"🚀 Entraînement modèle ALIMENTS avec {len(aliments)} échantillons")

    # Convert to DataFrame
    df = pd.DataFrame(aliments)

    # Validation des colonnes requises
    required_cols = ['prix', 'aliment_type', 'categorie', 'date']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}")

    # Filtrer prix invalides
    df = df[df['prix'] > 0].copy()
    df = df[df['prix'] < 1000000].copy()  # Max 1M FCFA

    logger.info(f"📊 Données nettoyées: {len(df)} échantillons valides")

    # Préparer features
    features = prepare_aliment_features(df)

    # Feature columns
    feature_cols = get_aliment_feature_names()

    X = features[feature_cols].fillna(0)
    y = features['prix']

    logger.info(f"🔧 Features préparées: {len(feature_cols)} features")
    logger.info(f"   Features: {', '.join(feature_cols)}")

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    logger.info(f"✂️  Split: {len(X_train)} train, {len(X_test)} test")

    # Train XGBoost
    model = xgb.XGBRegressor(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )

    logger.info("🤖 Entraînement XGBoost en cours...")
    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)

    # Metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    logger.info(f"\n📈 MÉTRIQUES MODÈLE ALIMENTS:")
    logger.info(f"   MAE:  {mae:.0f} FCFA")
    logger.info(f"   RMSE: {rmse:.0f} FCFA")
    logger.info(f"   R²:   {r2:.3f}")
    logger.info(f"   MAPE: {mape:.1f}%")

    # Statistiques globales
    stats = {
        'prix_global_mean': float(df['prix'].mean()),
        'prix_global_std': float(df['prix'].std()),
        'prix_global_min': int(df['prix'].min()),
        'prix_global_max': int(df['prix'].max()),
        'nb_samples': len(df),
        'mae': float(mae),
        'rmse': float(rmse),
        'r2': float(r2),
        'mape': float(mape)
    }

    # Statistiques par catégorie
    stats['by_categorie'] = {}
    for cat in df['categorie'].unique():
        cat_df = df[df['categorie'] == cat]
        stats['by_categorie'][cat] = {
            'mean': float(cat_df['prix'].mean()),
            'std': float(cat_df['prix'].std()),
            'count': int(len(cat_df))
        }

    # Save model
    model_dir = Path("ml/models")
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "xgboost_aliments.pkl"

    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'feature_names': feature_cols,
            'stats': stats
        }, f)

    logger.info(f"💾 Modèle sauvegardé: {model_path}")

    return {
        'samples': len(df),
        'mae': float(mae),
        'rmse': float(rmse),
        'r2': float(r2),
        'mape': float(mape)
    }


def get_model_path() -> Path:
    """Retourne le chemin du modèle aliments"""
    return Path("ml/models/xgboost_aliments.pkl")