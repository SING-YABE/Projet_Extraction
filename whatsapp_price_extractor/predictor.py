# """
# Module de prédiction de prix
# """

# import numpy as np
# from datetime import datetime, timedelta

# class AutomatedPricePredictor:
#     def __init__(self):
#         self.model = None
#         self.feature_names = []
#         self.encoders = {}
    
#     def prepare_features_advanced(self, df):
#         df_features = df.copy()
#         df_features['annee'] = df_features['date'].dt.year
#         df_features['mois'] = df_features['date'].dt.month
#         df_features['jour_semaine'] = df_features['date'].dt.dayofweek
#         df_features['jour_mois'] = df_features['date'].dt.day
#         df_features['saison'] = df_features['mois'].apply(self._get_season)
#         df_features['nb_vendeurs_actifs'] = df_features.groupby('date')['sender'].transform('nunique')
#         df_features['volume_messages'] = df_features.groupby('date')['message_id'].transform('count')
#         df_features = df_features.sort_values('date')
#         df_features['prix_precedent'] = df_features.groupby('animal_type')['price'].shift(1)
#         df_features['tendance_prix'] = df_features.groupby('animal_type')['price'].pct_change()
#         categorical_cols = ['animal_type', 'action_type']
#         from sklearn.preprocessing import LabelEncoder
#         for col in categorical_cols:
#             if col not in self.encoders:
#                 self.encoders[col] = LabelEncoder()
#                 df_features[f'{col}_encoded'] = self.encoders[col].fit_transform(df_features[col].fillna('inconnu'))
#             else:
#                 known_categories = set(self.encoders[col].classes_)
#                 df_features[f'{col}_temp'] = df_features[col].apply(lambda x: x if x in known_categories else 'inconnu')
#                 df_features[f'{col}_encoded'] = self.encoders[col].transform(df_features[f'{col}_temp'])
#                 df_features.drop(f'{col}_temp', axis=1, inplace=True)
#         return df_features
    
#     def _get_season(self, month):
#         if month in [6,7,8,9,10]: return 1
#         elif month in [11,12,1,2]: return 2
#         else: return 3
    
#     def train_advanced_model(self, df):
#         from sklearn.ensemble import GradientBoostingRegressor
#         from sklearn.model_selection import cross_val_score
#         df_features = self.prepare_features_advanced(df)
#         feature_cols = ['annee','mois','jour_semaine','saison','animal_type_encoded','action_type_encoded','nb_vendeurs_actifs','volume_messages']
#         for col in feature_cols:
#             if col in df_features.columns: df_features[col] = df_features[col].fillna(df_features[col].median())
#         X = df_features[feature_cols].dropna()
#         y = df_features.loc[X.index,'price']
#         if len(X)<5:
#             print("pas suffisant pour entrainer le model")
#             return None
#         self.model = GradientBoostingRegressor(n_estimators=100,max_depth=6,learning_rate=0.1,random_state=42)
#         self.model.fit(X,y)
#         self.feature_names = feature_cols
#         if len(X)>=10:
#             cv_scores = cross_val_score(self.model,X,y,cv=3,scoring='neg_mean_absolute_error')
#             print(f"Modèle entraîné - Erreur CV: {-cv_scores.mean():,.0f} FCFA")
#         return self.model
    
#     def predict_future_prices(self, animal_type='verrat', months_ahead=3):
#         if not self.model: return None
#         predictions = []
#         current_date = datetime.now()
#         def encode_label(encoder,label):
#             try: return int(encoder.transform([label])[0])
#             except: return 0
#         for month in range(1,months_ahead+1):
#             future_date = current_date + timedelta(days=30*month)
#             features_dict = {
#                 'annee': future_date.year,
#                 'mois': future_date.month,
#                 'jour_semaine': future_date.weekday(),
#                 'saison': self._get_season(future_date.month),
#                 'animal_type_encoded': encode_label(self.encoders['animal_type'], animal_type) if 'animal_type' in self.encoders else 0,
#                 'action_type_encoded': encode_label(self.encoders['action_type'], 'vente') if 'action_type' in self.encoders else 0,
#                 'nb_vendeurs_actifs':5,
#                 'volume_messages':10,
#             }
#             features_array = np.array([[features_dict[col] for col in self.feature_names]])
#             predicted_price = self.model.predict(features_array)[0]
#             predictions.append({'date':future_date,'prix_predit':predicted_price,'animal_type':animal_type})
#         return predictions
"""
Module de prédiction de prix
"""
import numpy as np
from datetime import datetime, timedelta

class AutomatedPricePredictor:
    def __init__(self):
        self.model = None
        self.feature_names = []
        self.encoders = {}
    
    def prepare_features_advanced(self, df):
        df_features = df.copy()
        df_features['annee'] = df_features['date'].dt.year
        df_features['mois'] = df_features['date'].dt.month
        df_features['jour_semaine'] = df_features['date'].dt.dayofweek
        df_features['jour_mois'] = df_features['date'].dt.day
        df_features['saison'] = df_features['mois'].apply(self._get_season)
        df_features['nb_vendeurs_actifs'] = df_features.groupby('date')['sender'].transform('nunique')
        df_features['volume_messages'] = df_features.groupby('date')['message_id'].transform('count')
        df_features = df_features.sort_values('date')
        df_features['prix_precedent'] = df_features.groupby('animal_type')['price'].shift(1)
        df_features['tendance_prix'] = df_features.groupby('animal_type')['price'].pct_change()
        from sklearn.preprocessing import LabelEncoder
        categorical_cols = ['animal_type', 'action_type']
        for col in categorical_cols:
            if col not in self.encoders:
                self.encoders[col] = LabelEncoder()
                df_features[f'{col}_encoded'] = self.encoders[col].fit_transform(df_features[col].fillna('inconnu'))
            else:
                known_categories = set(self.encoders[col].classes_)
                df_features[f'{col}_temp'] = df_features[col].apply(lambda x: x if x in known_categories else 'inconnu')
                df_features[f'{col}_encoded'] = self.encoders[col].transform(df_features[f'{col}_temp'])
                df_features.drop(f'{col}_temp', axis=1, inplace=True)
        return df_features
    
    def _get_season(self, month):
        if month in [6,7,8,9,10]: return 1
        elif month in [11,12,1,2]: return 2
        else: return 3
    
    def train_advanced_model(self, df):
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import cross_val_score
        df_features = self.prepare_features_advanced(df)
        feature_cols = ['annee','mois','jour_semaine','saison','animal_type_encoded','action_type_encoded','nb_vendeurs_actifs','volume_messages']
        X = df_features[feature_cols].fillna(df_features[feature_cols].median())
        y = df_features['price']
        if len(X) < 5:
            print("⚠️ Pas assez de données pour entraîner le modèle.")
            return None
        self.model = GradientBoostingRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
        self.model.fit(X, y)
        self.feature_names = feature_cols
        if len(X) >= 10:
            from sklearn.model_selection import cross_val_score
            cv_scores = cross_val_score(self.model, X, y, cv=3, scoring='neg_mean_absolute_error')
            print(f"✅ Modèle entraîné - Erreur CV: {-cv_scores.mean():,.0f} FCFA")
        return self.model
    
    def predict_future_prices(self, animal_type='verrat', months_ahead=3):
        if not self.model:
            print("⚠️ Le modèle n'est pas encore entraîné.")
            return []
        predictions = []
        current_date = datetime.now()
        def encode_label(encoder,label):
            try: return int(encoder.transform([label])[0])
            except: return 0
        for month in range(1, months_ahead + 1):
            future_date = current_date + timedelta(days=30 * month)
            features_dict = {
                'annee': future_date.year,
                'mois': future_date.month,
                'jour_semaine': future_date.weekday(),
                'saison': self._get_season(future_date.month),
                'animal_type_encoded': encode_label(self.encoders['animal_type'], animal_type),
                'action_type_encoded': encode_label(self.encoders['action_type'], 'vente'),
                'nb_vendeurs_actifs': 5,
                'volume_messages': 10,
            }
            features_array = np.array([[features_dict[col] for col in self.feature_names]])
            predicted_price = self.model.predict(features_array)[0]
            predictions.append({'date': future_date, 'prix_predit': round(predicted_price, 2), 'animal_type': animal_type})
        return predictions
