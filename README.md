# WhatsApp Price Intelligence - Backend API

Backend FastAPI pour extraction de prix WhatsApp avec Gemini AI et prédiction ML.

## 🚀 Installation

```bash
# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt
```

## ⚙️ Configuration

1. Copier l'exemple d'environnement:
```bash
cp .env.example .env.local
```

2. Éditer `.env.local`:
- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Clé API Gemini (gratuit)
- `CORS_ORIGINS`: URLs frontend Angular

## 🗄️ Database Setup

```bash
# Créer base PostgreSQL
createdb whatsapp_prices

# Les tables seront créées automatiquement au démarrage
```

## 🏃 Lancer l'API

```bash
# Mode développement
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Mode production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

API disponible sur: http://localhost:8000
Documentation: http://localhost:8000/docs

## 📡 Endpoints

### Extraction (Gemini)
- `POST /api/extract` - Upload WhatsApp .txt
- `GET /api/extractions` - Liste extractions

### Prédiction (ML)
- `GET /api/predict` - Prédire prix
- `POST /api/train` - Entraîner modèle
- `GET /api/opportunities` - Bonnes affaires

### Statistiques
- `GET /api/stats` - Statistiques globales
- `GET /api/trends` - Analyse tendances
- `GET /api/evolution` - Évolution prix

## 🧪 Tests

```bash
# Test extraction
curl -X POST http://localhost:8000/api/extract \
  -F "file=@export_whatsapp.txt"

# Test prédiction (après training)
curl "http://localhost:8000/api/predict?animal_type=porcelet&date=2026-01-15"
```

## 📁 Structure

```
backend/
├── main.py                 # FastAPI app
├── routers/               # API routes
├── services/              # Business logic
├── models/                # Pydantic schemas
├── ml/                    # ML models
├── db/                    # Database
└── utils/                 # Utilities
```

## 🔑 Obtenir Gemini API Key

1. Aller sur https://makersuite.google.com/app/apikey
2. Créer nouvelle clé API (gratuit)
3. Copier dans `.env`: `GEMINI_API_KEY=...`

## 📊 Workflow

1. **Upload .txt** → Gemini extrait prix → BDD
2. **Collecter 50+ prix** → Entraîner ML
3. **Prédire** prix futurs + opportunités

## 🐛 Dépannage

**Import errors**: `pip install -r requirements.txt`
**DB errors**: Vérifier `DATABASE_URL` dans `.env`
**Gemini errors**: Vérifier `GEMINI_API_KEY`
