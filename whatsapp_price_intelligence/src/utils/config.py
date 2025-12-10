"""
Configuration centralisée du projet
"""
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
import os

# Chemins du projet
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ANNOTATED_DATA_DIR = DATA_DIR / "annotated"
MODELS_DIR = DATA_DIR / "models"

# Créer les répertoires s'ils n'existent pas
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, ANNOTATED_DATA_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class AnimalTypes:
    """Types d'animaux supportés"""
    PORCELET = "porcelet"
    TRUIE = "truie"
    VERRAT = "verrat"
    PORC = "porc"
    NON_SPECIFIE = "non_specifie"
    
    @classmethod
    def all(cls) -> List[str]:
        return [cls.PORCELET, cls.TRUIE, cls.VERRAT, cls.PORC]


@dataclass
class ActionTypes:
    """Types d'actions"""
    VENTE = "vente"
    ACHAT = "achat"
    PRIX_INFO = "prix_info"
    NON_SPECIFIE = "non_specifie"


@dataclass
class ProductTypes:
    """Types de produits"""
    ANIMAL = "animal"
    ALIMENT = "aliment"
    MEDICAMENT = "medicament"
    EQUIPEMENT = "equipement"
    NON_SPECIFIE = "non_specifie"


# Mots-clés pour la classification
ANIMAL_KEYWORDS = {
    AnimalTypes.PORCELET: [
        'porcelet', 'petit', 'sevré', 'jeune', 'bébé', 
        'portée', 'né', 'naissance'
    ],
    AnimalTypes.TRUIE: [
        'truie', 'femelle', 'gestante', 'portée', 'mère',
        'gestation', 'mise bas', 'allaitante', 'reproductrice'
    ],
    AnimalTypes.VERRAT: [
        'verrat', 'reproducteur', 'mâle', 'male', 'étalon',
        'saillie', 'monte', 'reproduction', 'géniteur'
    ],
    AnimalTypes.PORC: [
        'porc', 'cochon', 'embouche', 'gros', 'adulte',
        'engraissement', 'abattage', 'viande', 'finition'
    ]
}

ALIMENT_KEYWORDS = [
    'son', 'farine', 'aliment', 'provende', 'granulé',
    'maïs', 'soja', 'tourteau', 'concentré', 'complément',
    'carbonate', 'calcium', 'phosphate', 'CMV', 'prémix',
    'dolo', 'drêche', 'riz', 'blé', 'mil'
]

ACTION_KEYWORDS = {
    ActionTypes.VENTE: [
        'vente', 'vendre', 'à vendre', 'en vente', 'cède',
        'propose', 'vend', 'disponible', 'stock', 'dispo'
    ],
    ActionTypes.ACHAT: [
        'recherche', 'cherche', 'achète', 'achat', 'besoin',
        'veut', 'intéressé', 'demande', 'je veux', 'souhaite'
    ],
    ActionTypes.PRIX_INFO: [
        'prix', 'coût', 'combien', 'tarif', 'montant',
        'valeur', 'estimation', 'quel est'
    ]
}

# Unités de mesure
UNITS = {
    'poids': ['kg', 'kilogramme', 'kilo', 'g', 'gramme', 'tonne', 't'],
    'volume': ['sac', 'sachet', 'paquet', 'carton', 'bidon'],
    'quantite': ['unité', 'pièce', 'tête', 'animal', 'bête'],
    'surface': ['ha', 'hectare', 'm2', 'are']
}

# Ranges de prix valides (en FCFA)
PRICE_RANGES = {
    AnimalTypes.PORCELET: (5_000, 80_000),
    AnimalTypes.TRUIE: (50_000, 300_000),
    AnimalTypes.VERRAT: (80_000, 500_000),
    AnimalTypes.PORC: (30_000, 250_000),
    'aliment_sac': (3_000, 50_000),
    'aliment_tonne': (100_000, 500_000)
}

# Ranges d'âge (en jours)
AGE_RANGES = {
    AnimalTypes.PORCELET: (1, 90),
    AnimalTypes.TRUIE: (270, 2190),  # 9 mois à 6 ans
    AnimalTypes.VERRAT: (180, 1800),  # 6 mois à 5 ans
    AnimalTypes.PORC: (90, 365)
}

# Configuration du modèle ML
ML_CONFIG = {
    'test_size': 0.2,
    'random_state': 42,
    'cv_folds': 5,
    'n_estimators': 200,
    'learning_rate': 0.05,
    'max_depth': 6
}

# Seuils de qualité des données
QUALITY_THRESHOLDS = {
    'min_price': 1_000,
    'max_price': 2_000_000,
    'min_message_length': 10,
    'max_missing_ratio': 0.3,
    'min_samples_for_training': 50
}

# Configuration du dashboard
DASHBOARD_CONFIG = {
    'title': '🐷 Intelligence des Prix - Marché Porcin',
    'page_icon': '🐷',
    'layout': 'wide',
    'refresh_interval': 300  # 5 minutes
}

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
