"""
ML Model Trainer (XGBoost)
"""
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np
import pickle
from pathlib import Path

from ml.features import prepare_features
from utils.logger import logger


def train_model(prices: list) -> dict:
    """
    Train XGBoost model on historical prices
    
    Args:
        prices: List of price dicts from DB
    
    Returns:
        Training metrics
    """
    logger.info(f"Training model on {len(prices)} samples")
    
    if len(prices) < 50:
        raise ValueError(f"Need 50+ samples, have {len(prices)}")
    
    # Convert to DataFrame
    df = pd.DataFrame(prices)
    
    # Prepare features
    df_features = prepare_features(df)
    
    feature_cols = [
        'month', 'day_of_week', 'season',
        'animal_encoded', 'action_encoded',
        'nb_prix_jour', 'nb_vendeurs_jour', 'volume_semaine',
        'prix_precedent', 'prix_ma7', 'tendance_pct',
        'prix_median_animal', 'ecart_median'
    ]
    
    X = df_features[feature_cols].fillna(0)
    y = df_features['prix']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train XGBoost
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train, verbose=False)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    
    # Save model
    model_path = Path('ml/models/xgboost_model.pkl')
    model_path.parent.mkdir(parents=True, exist_ok=True)
    
    stats = {
        'prix_global_median': float(y.median()),
        'prix_global_mean': float(y.mean()),
        'prix_global_std': float(y.std()),
        'date_range': (df['date'].min(), df['date'].max())
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'stats': stats,
            'feature_names': feature_cols
        }, f)
    
    logger.info(f"Model trained and saved: MAE={mae:.0f}, R²={r2:.3f}")
    
    return {
        'samples': len(df),
        'mae': float(mae),
        'rmse': float(rmse),
        'r2': float(r2),
        'mape': float(mape)
    }
