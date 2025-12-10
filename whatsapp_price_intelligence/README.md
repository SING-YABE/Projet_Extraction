# 🐷 WhatsApp Price Intelligence

**Système d'extraction et d'analyse de prix du marché porcin à partir de conversations WhatsApp**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Vue d'ensemble

Ce projet permet d'extraire, nettoyer, valider et analyser automatiquement les prix des porcs mentionnés dans des conversations WhatsApp. Il est spécialement adapté au contexte africain francophone (FCFA, dialecte local, etc.).

### ✨ Fonctionnalités principales

- ✅ **Extraction robuste** : Parse les exports WhatsApp avec gestion multi-formats
- 💰 **Détection contextuelle** : Identifie les prix avec leur contexte (type d'animal, action, unité)
- 🎯 **Classification intelligente** : Distingue porcelets, truies, verrats, porcs
- 📊 **Validation automatique** : Détecte les anomalies et valide la qualité des données
- 🏷️ **Outil d'annotation** : Interface interactive pour créer des données de référence
- 📈 **Prédiction ML** : Modèles pour prédire les prix futurs (à venir)
- 🎨 **Dashboard** : Visualisation des tendances du marché (à venir)

---

## 🚀 Installation rapide

### Prérequis

- Python 3.8 ou supérieur
- pip

### Installation

```bash
# 1. Cloner le projet
git clone <votre-repo>
cd whatsapp_price_intelligence

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Vérifier l'installation
python main.py --help
```

---

## 📖 Guide d'utilisation

### 1️⃣ Extraction des prix

```bash
# Extraire les prix d'un export WhatsApp
python main.py extract data/raw/whatsapp_export.txt
```

**Sortie** :
- `data/processed/messages_parsed.csv` : Messages nettoyés
- `data/processed/prices_extracted.csv` : Prix extraits avec contexte
- `data/processed/quality_report.json` : Rapport de validation

### 2️⃣ Annotation des données

```bash
# Annoter 50 messages
python main.py annotate data/processed/prices_extracted.csv --n-samples 50
```

L'outil interactif vous guide pour valider/corriger les extractions automatiques.

### 3️⃣ Pipeline complet

```bash
# Tout en une commande
python main.py full-pipeline data/raw/whatsapp_export.txt --annotate
```

### 4️⃣ Validation

```bash
# Valider un fichier de données
python main.py validate data/processed/prices_extracted.csv
```

---

## 📁 Structure du projet

```
whatsapp_price_intelligence/
├── data/
│   ├── raw/              # Exports WhatsApp bruts
│   ├── processed/        # Données nettoyées
│   ├── annotated/        # Annotations manuelles
│   └── models/           # Modèles ML entraînés
├── src/
│   ├── extraction/       # Parsing et extraction
│   ├── data_quality/     # Validation et annotation
│   ├── models/           # Modèles ML (à venir)
│   ├── dashboard/        # Interface Streamlit (à venir)
│   └── utils/            # Configuration et logging
├── tests/                # Tests unitaires
├── notebooks/            # Analyses exploratoires
├── main.py               # Point d'entrée
└── requirements.txt      # Dépendances
```

---

## 🎯 Formats des données

### Export WhatsApp attendu

```
30/06/2024, 20:42 - +226 56 65 16 08: Brs besoin de porcs de 3 à 4 mois
01/07/2024, 14:12 - +226 70 75 02 74: Farine de blé à 8000 f le sac
```

### Format de sortie

| Colonne | Description | Exemple |
|---------|-------------|---------|
| `message_id` | ID unique | 0 |
| `date` | Date du message | 2024-07-01 14:12:00 |
| `sender` | Numéro expéditeur | +226 70 75 02 74 |
| `prix` | Prix extrait (FCFA) | 8000 |
| `unite` | Unité de mesure | sac |
| `type_produit` | Type de produit | aliment |
| `animal_type` | Type d'animal | porcelet / truie / verrat / porc |
| `action_type` | Type d'action | vente / achat / prix_info |
| `confiance` | Score de confiance | 0.85 |
| `contexte` | Contexte extrait | "farine de blé à 8000 f le sac" |

---

## ⚙️ Configuration

Tous les paramètres sont dans `src/utils/config.py` :

```python
# Ranges de prix valides
PRICE_RANGES = {
    'porcelet': (5_000, 80_000),
    'truie': (50_000, 300_000),
    'verrat': (80_000, 500_000),
    'porc': (30_000, 250_000)
}

# Seuils de qualité
QUALITY_THRESHOLDS = {
    'min_price': 1_000,
    'max_price': 2_000_000,
    'min_message_length': 10
}
```

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest tests/

# Avec couverture
pytest --cov=src tests/
```

---

## 🛠️ Développement futur

### Phase 2 : Modèles ML (en cours)
- [ ] Prédiction des prix futurs (séries temporelles)
- [ ] Détection d'anomalies en temps réel
- [ ] Classification multi-labels avancée

### Phase 3 : Dashboard interactif
- [ ] Interface Streamlit
- [ ] Visualisations dynamiques
- [ ] Alertes sur bonnes affaires

### Phase 4 : Déploiement
- [ ] API REST
- [ ] Bot WhatsApp intégré
- [ ] Application mobile

---

## 📊 Exemple de résultats

Après extraction d'un export de 500 messages :

```
✓ 500 messages parsés
✓ 85 prix extraits
  - 42 porcelets (25 000 - 45 000 FCFA)
  - 18 truies (100 000 - 125 000 FCFA)
  - 12 verrats (90 000 - 150 000 FCFA)
  - 13 aliments (6 500 - 37 000 FCFA)

📊 Score de qualité: 87.5/100
⚠ 3 prix suspects détectés (à vérifier)
```

---

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Forkez le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Committez (`git commit -m 'Add AmazingFeature'`)
4. Pushez (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

---

## 📝 TODO

- [x] Parser WhatsApp robuste
- [x] Extraction de prix structurée
- [x] Validation de données
- [x] Outil d'annotation
- [ ] Modèle de prédiction
- [ ] Dashboard Streamlit
- [ ] Tests unitaires complets
- [ ] Documentation API
- [ ] CI/CD

---

## 📄 Licence

Ce projet est sous licence MIT. Voir `LICENSE` pour plus de détails.

---

## 👤 Auteur

Votre Nom - [votre@email.com](mailto:votre@email.com)

---

## 🙏 Remerciements

- Communauté des éleveurs porcins du Burkina Faso
- Contributeurs open-source

---

**Happy Coding! 🐷💰**
