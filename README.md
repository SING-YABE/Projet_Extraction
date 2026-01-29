
---

# 📊 **Système d'Extraction de Prix Agricoles au Burkina Faso**

## 🎯 **Vue d'ensemble**

Application web full-stack permettant d'**extraire automatiquement les prix des animaux et aliments pour bétail** à partir de messages WhatsApp, avec **prédiction ML**, **analyse de tendances** et **gestion des dépenses de ferme**.

---

## 🏗️ **Architecture du Système**

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Angular)                       │
│  - Interface de gestion des prix                                 │
│  - Visualisation des tendances                                   │
│  - Prédictions ML                                                │
│  - Gestion des dépenses                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API
┌────────────────────────▼────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Webhook WhatsApp (Zapwize)                              │   │
│  │    - Réception messages texte/audio                       │   │
│  │    - Transcription audio (Whisper AI)                     │   │
│  │    - Routage intelligent (dépenses vs prix)               │   │
│  └────────────┬─────────────────────────────────────────────┘   │
│               │                                                   │
│  ┌────────────▼─────────────────────────────────────────────┐   │
│  │  Extraction Intelligence (Gemini AI)                      │   │
│  │    - Extraction structurée des prix                       │   │
│  │    - Normalisation des unités (kg, sac, tonne)            │   │
│  │    - Catégorisation automatique                           │   │
│  └────────────┬─────────────────────────────────────────────┘   │
│               │                                                   │
│  ┌────────────▼─────────────────────────────────────────────┐   │
│  │  Machine Learning (XGBoost)                               │   │
│  │    - Prédiction prix animaux                              │   │
│  │    - Prédiction prix aliments                             │   │
│  │    - Détection d'opportunités                             │   │
│  └────────────┬─────────────────────────────────────────────┘   │
│               │                                                   │
│  ┌────────────▼─────────────────────────────────────────────┐   │
│  │  Gestion Dépenses                                         │   │
│  │    - Enregistrement automatique (audio/texte)             │   │
│  │    - Catégorisation intelligente                          │   │
│  │    - CRUD complet + statistiques                          │   │
│  └───────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   BASE DE DONNÉES (PostgreSQL)                   │
│  - Prix animaux (porcs, truies, porcelets, verrats)             │
│  - Prix aliments (maïs, riz, soja, tourteau, etc.)              │
│  - Dépenses ferme (7 catégories)                                │
│  - Historique complet                                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ **Structure de la Base de Données**

### **1. Table `prix_animaux`**
Stocke les prix extraits pour les animaux (porcs).

```sql
CREATE TABLE prix_animaux (
    id BIGSERIAL PRIMARY KEY,
    animal_type VARCHAR(50) NOT NULL,           -- porcelet, truie, verrat, porc
    prix FLOAT NOT NULL,
    age_mois INTEGER,
    poids_kg FLOAT,
    quantite INTEGER DEFAULT 1,
    unite VARCHAR(20) DEFAULT 'tete',
    action VARCHAR(20),                         -- vente, achat, prix_info
    negociable BOOLEAN,
    etat VARCHAR(50),                           -- sevre, en gestation, etc.
    vendeur VARCHAR(100),
    date DATE NOT NULL,
    message_original TEXT,
    confiance INTEGER,                          -- Score de confiance (0-100)
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index pour améliorer les performances
CREATE INDEX idx_prix_animaux_date ON prix_animaux(date);
CREATE INDEX idx_prix_animaux_type ON prix_animaux(animal_type);
```

**Valeurs typiques :**
- `animal_type` : `porcelet`, `truie`, `verrat`, `porc`
- `action` : `vente`, `achat`, `prix_info`, `recherche`
- Prix en **FCFA** (Francs CFA)

---

### **2. Table `prix_aliments`**
Stocke les prix extraits pour les aliments du bétail.

```sql
CREATE TABLE prix_aliments (
    id BIGSERIAL PRIMARY KEY,
    aliment_type VARCHAR(100) NOT NULL,         -- maïs, soja, son de riz, etc.
    categorie VARCHAR(50) NOT NULL,             -- ÉNERGÉTIQUE, PROTÉINE, MINÉRAUX, VITAMINES
    prix FLOAT NOT NULL,
    unite VARCHAR(20) DEFAULT 'kg',             -- TOUJOURS en kg
    poids_kg FLOAT NOT NULL,                    -- Poids normalisé en kg
    prix_par_kg FLOAT NOT NULL,                 -- Prix unitaire au kg
    quantite INTEGER DEFAULT 1,
    vendeur VARCHAR(100),
    date DATE NOT NULL,
    message_original TEXT,
    confiance INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index
CREATE INDEX idx_prix_aliments_date ON prix_aliments(date);
CREATE INDEX idx_prix_aliments_type ON prix_aliments(aliment_type);
CREATE INDEX idx_prix_aliments_categorie ON prix_aliments(categorie);
```

**Catégories d'aliments :**
- **ÉNERGÉTIQUE** : Maïs, mil, sorgho, son de blé, son de maïs, riz, manioc
- **PROTÉINE** : Soja, tourteau de soja, tourteau de coton, farine de poisson
- **MINÉRAUX** : CMV, pierre à lécher, sel, phosphate
- **VITAMINES** : Concentré, prémix, siatol, provende

**Normalisation des unités :**
```
Sac de riz         → 120 kg
Sac de son de riz  → 50 kg
Sac de blé         → 100 kg
Sac de maïs        → 100 kg
Sac de soja        → 50 kg
1 tonne            → 1000 kg
```

---

### **3. Table `depense`**
Gestion des dépenses de la ferme.

```sql
CREATE TABLE depense (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    type_depense_id BIGINT NOT NULL,
    description VARCHAR(200) NOT NULL,
    montant FLOAT NOT NULL,
    mode_paiement VARCHAR(50) NOT NULL,
    observations TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (type_depense_id) REFERENCES type_depense(id)
);

-- Index
CREATE INDEX idx_depense_date ON depense(date);
CREATE INDEX idx_depense_type ON depense(type_depense_id);
```

**Modes de paiement :**
- `Espèces`
- `Dépôt`
- `Chèque`
- `Virement bancaire`
- `Mobile Money`

---

### **4. Table `type_depense`**
Types de dépenses (référentiel).

```sql
CREATE TABLE type_depense (
    id BIGSERIAL PRIMARY KEY,
    nom VARCHAR(50) NOT NULL UNIQUE
);

-- Données de référence (lecture seule)
INSERT INTO type_depense (id, nom) VALUES
(1, 'ANIMAUX'),      -- Achat de porcs, truies, porcelets
(2, 'ALIMENTS'),     -- Achat d'aliments pour bétail
(3, 'SALAIRES'),     -- Paiement du personnel
(4, 'TRANSPORT'),    -- Frais de déplacement, carburant
(5, 'SANTÉ'),        -- Médicaments, vaccins, vétérinaire
(6, 'MATÉRIEL'),     -- Outils, équipements, construction
(7, 'AUTRE');        -- Autres dépenses
```

---

## 📂 **Structure du Projet**

```
Projet_Extraction/
├── 📁 audios/                          # Fichiers audio WhatsApp téléchargés
├── 📁 db/
│   ├── __init__.py
│   ├── database.py                     # Configuration SQLAlchemy + modèles
│   └── crud.py                         # Opérations CRUD
├── 📁 ml/
│   ├── 📁 models/
│   │   ├── xgboost_model.pkl           # Modèle ML animaux
│   │   └── xgboost_aliments.pkl        # Modèle ML aliments
│   └── 📁 models/
│       ├── aliment_features.py
│       ├── aliment_predictor.py
│       ├── aliment_trainer.py
│       ├── features.py
│       ├── predictor.py
│       └── trainer.py
├── 📁 models/
│   ├── __init__.py
│   ├── price.py                        # Modèles Pydantic prix
│   ├── prediction.py                   # Modèles Pydantic prédictions
│   └── schemas.py                      # Tous les schémas Pydantic
├── 📁 routers/
│   ├── __init__.py
│   ├── extraction_routes.py            # API extraction prix
│   ├── prediction_routes.py            # API prédictions animaux
│   ├── aliment_prediction_routes.py    # API prédictions aliments
│   ├── aliment_routes.py               # API aliments
│   ├── stats_routes.py                 # API statistiques
│   ├── webhook_routes.py               # ⭐ Webhook WhatsApp
│   └── expense_routes.py               # ⭐ API dépenses
├── 📁 services/
│   ├── __init__.py
│   ├── extraction_workflow.py          # Workflow extraction
│   ├── gemini_extractor.py             # ⭐ Extraction Gemini AI
│   ├── file_parser.py
│   ├── price_predictor.py
│   ├── trend_analyzer.py
│   ├── anomaly_detector.py
│   └── validator.py
├── 📁 utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── config.py
│   └── message_cleaner_and_redirection.py  # ⭐ Router intelligent
├── .env                                # Variables d'environnement
├── main.py                             # ⭐ Point d'entrée FastAPI
├── requirements.txt
└── README.md
```

---

## 🔄 **Flux de Traitement des Messages WhatsApp**

### **1. Réception du Message**

```
Zapwize Webhook → FastAPI (/webhook/whatsapp)
```

**Types de messages supportés :**
- ✅ Messages texte
- ✅ Messages audio (transcription Whisper)

---

### **2. Routage Intelligent**

Le système analyse le message et décide de la destination :

```python
# utils/message_cleaner_and_redirection.py

Message WhatsApp
    ↓
Nettoyage (supprime "bonjour", "salut", etc.)
    ↓
Classification
    ↓
    ├─→ DÉPENSE (pattern "Dépense du...")
    │   → Extraction automatique
    │   → Sauvegarde table `depense`
    │
    ├─→ PRIX (patterns animaux/aliments)
    │   → Gemini AI
    │   → Sauvegarde tables `prix_*`
    │
    └─→ CONVERSATIONNEL ("tu vas bien ?")
        → Ignoré
```

**Patterns de détection :**

**Dépenses :**
- `"Dépense du Mercredi 26 Janvier 2026 : achat de porc à 25 000 Francs (en espèce)"`
- `"dépenses de maigreté 26 janvier 2026 achats de porc à 25000 francs en espèces"`

**Prix :**
- `"Porcelets 3 mois disponibles à 25000 FCFA"`
- `"Son de riz 4500 le sac"`
- `"Maïs 100000f/tonne"`

---

### **3. Extraction Gemini AI**

Pour les messages de **prix**, Gemini extrait :

**Animaux :**
```json
{
  "type": "animal",
  "animal_type": "porcelet",
  "prix": 25000,
  "age_mois": 3,
  "quantite": 1,
  "unite": "tete",
  "action": "vente",
  "date": "2026-01-27",
  "confiance": 90
}
```

**Aliments :**
```json
{
  "type": "aliment",
  "aliment_type": "son de riz",
  "categorie": "ÉNERGÉTIQUE",
  "prix": 4500,
  "poids_kg": 50,
  "prix_par_kg": 90,
  "unite": "kg",
  "date": "2026-01-27",
  "confiance": 85
}
```

---

### **4. Machine Learning**

**Modèles disponibles :**
- **XGBoost Animaux** : Prédiction prix porcs
- **XGBoost Aliments** : Prédiction prix aliments

**Features utilisées :**
- Prix historiques
- Moyennes mobiles (7, 14, 30 jours)
- Volatilité
- Tendances
- Jour de la semaine
- Mois

---

## 🚀 **Installation & Démarrage**

### **Prérequis**

```bash
- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (pour le frontend Angular)
- FFmpeg (pour Whisper)
```

### **Backend (FastAPI)**

```bash
# 1. Cloner le projet
git clone <repo>
cd Projet_Extraction

# 2. Créer environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OU
.venv\Scripts\activate     # Windows

# 3. Installer dépendances
pip install -r requirements.txt

# 4. Configurer .env
cp .env.example .env
# Éditer .env avec tes clés API

# 5. Initialiser la base de données
# Créer la base PostgreSQL
createdb extraction_prix

# Insérer les types de dépenses
psql extraction_prix < init_type_depense.sql

# 6. Lancer l'API
python main.py
```

**API disponible sur :** `http://localhost:8000`

**Documentation Swagger :** `http://localhost:8000/docs`

---

### **Frontend (Angular)**

```bash
cd frontend

# Installer dépendances
npm install

# Lancer le serveur de développement
ng serve

# Application disponible sur: http://localhost:4200
```

---

## 🔑 **Variables d'Environnement (.env)**

```env
# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/extraction_prix

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here

# Webhook (optionnel)
ZAPWIZE_WEBHOOK_SECRET=your_secret_here

# Whisper (modèle)
WHISPER_MODEL=small  # tiny, base, small, medium, large
```

---

## 📡 **API Endpoints**

### **Prix & Extraction**

```
GET    /api/extractions          # Liste des extractions
POST   /api/extract              # Extraction manuelle (fichier)
GET    /api/stats                # Statistiques globales
GET    /api/trends               # Tendances prix
```

### **Prédictions Animaux**

```
POST   /api/train                # Entraîner modèle
GET    /api/predict              # Prédire prix animal
GET    /api/predict/future       # Prédictions futures (3-12 mois)
GET    /api/opportunities         # Opportunités d'achat
```

### **Prédictions Aliments**

```
POST   /api/train/aliments       # Entraîner modèle
GET    /api/predict/aliment      # Prédire prix aliment
GET    /api/predict/aliment/future
GET    /api/aliments/recent      # Aliments récents
```

### **Dépenses**

```
POST   /depenses                 # Créer dépense
GET    /depenses                 # Liste dépenses (avec filtres)
GET    /depenses/{id}            # Détail dépense
PUT    /depenses/{id}            # Modifier dépense
DELETE /depenses/{id}            # Supprimer dépense
GET    /depenses/types/list      # Types de dépenses
GET    /depenses/stats/summary   # Résumé statistiques
```

### **Webhook**

```
POST   /webhook/whatsapp         # Réception messages Zapwize
```

---

## 🎨 **Diagrammes pour Draw.io**

### **1. Schéma Base de Données**

```
┌─────────────────────────┐
│    prix_animaux         │
├─────────────────────────┤
│ id (PK)                 │
│ animal_type             │
│ prix                    │
│ age_mois                │
│ poids_kg                │
│ quantite                │
│ date                    │
│ vendeur                 │
│ confiance               │
└─────────────────────────┘

┌─────────────────────────┐
│    prix_aliments        │
├─────────────────────────┤
│ id (PK)                 │
│ aliment_type            │
│ categorie               │
│ prix                    │
│ poids_kg                │
│ prix_par_kg             │
│ date                    │
│ confiance               │
└─────────────────────────┘

┌─────────────────────────┐       ┌─────────────────────────┐
│    depense              │───────│    type_depense         │
├─────────────────────────┤  FK   ├─────────────────────────┤
│ id (PK)                 │       │ id (PK)                 │
│ date                    │       │ nom                     │
│ type_depense_id (FK)    │       │                         │
│ description             │       │ ANIMAUX                 │
│ montant                 │       │ ALIMENTS                │
│ mode_paiement           │       │ SALAIRES                │
│ observations            │       │ TRANSPORT               │
└─────────────────────────┘       │ SANTÉ                   │
                                   │ MATÉRIEL                │
                                   │ AUTRE                   │
                                   └─────────────────────────┘
```

---

## 🤖 **Technologies Utilisées**

**Backend :**
- **FastAPI** : Framework web Python
- **SQLAlchemy** : ORM
- **PostgreSQL** : Base de données
- **Whisper AI** : Transcription audio
- **Gemini AI** : Extraction structurée
- **XGBoost** : Machine Learning
- **Pandas/NumPy** : Traitement données

**Frontend :**
- **Angular 18** : Framework frontend
- **PrimeNG** : Composants UI
- **Chart.js** : Visualisations

**Infrastructure :**
- **Uvicorn** : Serveur ASGI
- **Zapwize** : Plateforme WhatsApp

---

## 📊 **Statistiques du Projet**

- **7 tables** de base de données
- **8 endpoints** d'API
- **2 modèles ML** (animaux + aliments)
- **3 sources** de données (audio, texte, fichier)
- **4 catégories** d'aliments
- **7 types** de dépenses

---

## 🤝 **Contribution**

Pour contribuer au projet, consulte `CONTRIBUTING.md`.

---

## 📝 **Licence**

MIT License

---

## 👨‍💻 **Auteur**

**TRAORE Timothée Rachid**  
Projet d'extraction intelligente de prix agricoles au Burkina Faso

---

**🎉 Projet déployé avec succès !**