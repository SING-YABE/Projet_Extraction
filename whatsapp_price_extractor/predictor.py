"""
Module de prédiction de prix corrigé pour WhatsApp Pig Price Extractor
"""
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
import pandas as pd

class AutomatedPricePredictor:
    def __init__(self):
        self.model = None
        self.feature_names = []
        self.encoders = {}
        self.df_history = None  # données historiques pour prédiction

    # ======================================================================
    # FEATURE ENGINEERING
    # ======================================================================

    def prepare_features_advanced(self, df):
        """
        Prépare le DataFrame avec toutes les features utiles pour l'entraînement.
        """
        df_features = df.copy()
        df_features['date'] = pd.to_datetime(df_features['date'])

        # Structure temporelle
        df_features['annee'] = df_features['date'].dt.year
        df_features['mois'] = df_features['date'].dt.month
        df_features['jour_semaine'] = df_features['date'].dt.dayofweek
        df_features['jour_mois'] = df_features['date'].dt.day
        df_features['saison'] = df_features['mois'].apply(self._get_season)

        # Activité par jour
        df_features['nb_vendeurs_actifs'] = df_features.groupby('date')['sender'].transform('nunique')
        df_features['volume_messages'] = df_features.groupby('date')['message_id'].transform('count')

        df_features = df_features.sort_values('date')

        # Prix précédent + tendance
        df_features['prix_precedent'] = df_features.groupby('animal_type')['price'].shift(1)
        df_features['tendance_prix'] = df_features.groupby('animal_type')['price'].pct_change()

        # Moyennes mobiles (indispensable pour un vrai modèle temporel)
        df_features['rolling_mean_3'] = df_features.groupby('animal_type')['price'].rolling(3).mean().reset_index(0, drop=True)
        df_features['rolling_std_3'] = df_features.groupby('animal_type')['price'].rolling(3).std().reset_index(0, drop=True)

        # Encodage des colonnes catégorielles
        categorical_cols = ['animal_type', 'action_type']
        for col in categorical_cols:
            if col not in self.encoders:
                self.encoders[col] = LabelEncoder()
                df_features[f'{col}_encoded'] = self.encoders[col].fit_transform(df_features[col].fillna('inconnu'))
            else:
                known = set(self.encoders[col].classes_)
                df_features[f'{col}_temp'] = df_features[col].apply(lambda x: x if x in known else 'inconnu')
                df_features[f'{col}_encoded'] = self.encoders[col].transform(df_features[f'{col}_temp'])
                df_features.drop(columns=[f'{col}_temp'], inplace=True)

        # Remplacement des valeurs manquantes
        numeric_cols = [
            'prix_precedent', 'tendance_prix', 'nb_vendeurs_actifs',
            'volume_messages', 'rolling_mean_3', 'rolling_std_3'
        ]
        for col in numeric_cols:
            df_features[col] = df_features[col].fillna(df_features[col].median())

        return df_features

    def _get_season(self, month):
        """Retourne la saison pour le Burkina Faso."""
        if month in [5, 6, 7, 8, 9, 10]:
            return 1  # pluvieuse
        return 2      # sèche

    # ======================================================================
    # ENTRAÎNEMENT DU MODÈLE
    # ======================================================================

    def train_advanced_model(self, df):
        """
        Entraîne un modèle Gradient Boosting avec toutes les vraies features temporelles.
        """
        if df.empty:
            print("⚠️ Pas de données pour entraîner le modèle.")
            return

        self.df_history = df.copy()
        df_features = self.prepare_features_advanced(df)

        # Features finales utilisées par le modèle
        feature_cols = [
            'annee','mois','jour_semaine','saison',
            'animal_type_encoded','action_type_encoded',
            'nb_vendeurs_actifs','volume_messages',
            'prix_precedent','tendance_prix',
            'rolling_mean_3','rolling_std_3'
        ]

        X = df_features[feature_cols].values
        y = df_features['price'].values
        self.feature_names = feature_cols

        if len(X) < 5:
            print("⚠️ Pas assez de données pour entraîner le modèle.")
            return

        # Modèle
        self.model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )
        self.model.fit(X, y)

        # Évaluation
        if len(X) >= 10:
            cv = cross_val_score(self.model, X, y, cv=3, scoring='neg_mean_absolute_error')
            print(f"Modèle entraîné - Erreur CV: {-cv.mean():,.0f} FCFA")

    # ======================================================================
    # PREDICTION
    # ======================================================================

    def predict_future_prices(self, animal_type='porc', months_ahead=3):
        """
        Prédit les prix futurs d'un animal sur plusieurs mois.
        Avec filtrage des valeurs aberrantes.
        """
        if not self.model or self.df_history is None:
            print("⚠️ Le modèle n'est pas entraîné.")
            return []

        predictions = []
        current_date = datetime.now()

        # Référence statistique
        hist = self.df_history[self.df_history['animal_type'] == animal_type]
        ref_price = hist['price'].median() if not hist.empty else self.df_history['price'].median()
        min_price = max(5000, ref_price * 0.5)
        max_price = ref_price * 2

        # Encodeur
        def encode_label(encoder, label):
            try:
                return int(encoder.transform([label])[0])
            except:
                return 0

        # Contexte moyen
        avg_vendeurs = int(self.df_history['sender'].nunique() / max(1, len(self.df_history['date'].unique())))
        avg_volume = int(self.df_history.groupby('date')['message_id'].count().mean())

        # Prédiction mensuelle
        for month in range(1, months_ahead + 1):
            future_date = current_date + timedelta(days=30 * month)

            features_dict = {
                'annee': future_date.year,
                'mois': future_date.month,
                'jour_semaine': future_date.weekday(),
                'saison': self._get_season(future_date.month),
                'animal_type_encoded': encode_label(self.encoders['animal_type'], animal_type),
                'action_type_encoded': encode_label(self.encoders['action_type'], 'vente'),
                'nb_vendeurs_actifs': avg_vendeurs or 5,
                'volume_messages': avg_volume or 10,
                'prix_precedent': ref_price,
                'tendance_prix': 0,
                'rolling_mean_3': ref_price,
                'rolling_std_3': 0
            }

            features_array = np.array([[features_dict[col] for col in self.feature_names]])
            predicted_price = float(self.model.predict(features_array)[0])

            # Correction des aberrations
            predicted_price = max(min(predicted_price, max_price), min_price)

            predictions.append({
                'date': future_date,
                'prix_predit': round(predicted_price, 2),
                'animal_type': animal_type
            })

        return predictions
