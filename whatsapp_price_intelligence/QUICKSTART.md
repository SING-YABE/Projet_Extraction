# 🚀 Guide de Démarrage Rapide

## Installation en 3 minutes

```bash
# 1. Cloner et entrer dans le projet
cd whatsapp_price_intelligence

# 2. Créer environnement virtuel
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Installer dépendances minimales
pip install pandas numpy python-dateutil rich

# 4. Tester l'installation
python test_setup.py
```

## Premier test (2 minutes)

### Avec le fichier exemple fourni :

```bash
# Extraire les prix du fichier exemple
python main.py extract data/raw/sample_whatsapp.txt
```

**Résultat attendu** :
```
✓ 18 messages parsés
✓ 25 prix extraits
📊 Score de qualité: 85.0/100
```

### Avec votre propre export WhatsApp :

1. **Exporter votre conversation WhatsApp** :
   - Ouvrir la conversation sur WhatsApp
   - Menu ⋮ → Plus → Exporter
   - Choisir "Sans média"
   - Enregistrer le fichier `.txt`

2. **Copier dans le projet** :
```bash
cp ~/Downloads/WhatsApp\ Chat.txt data/raw/mon_export.txt
```

3. **Lancer l'extraction** :
```bash
python main.py extract data/raw/mon_export.txt
```

4. **Voir les résultats** :
```bash
# Messages parsés
cat data/processed/messages_parsed.csv

# Prix extraits
cat data/processed/prices_extracted.csv

# Rapport qualité
cat data/processed/quality_report.json
```

## Prochaines étapes

### 1. Améliorer la qualité avec l'annotation

```bash
# Annoter 30 exemples
python main.py annotate data/processed/prices_extracted.csv --n-samples 30
```

Suivez les instructions à l'écran pour valider/corriger les extractions.

### 2. Analyser les résultats

```python
import pandas as pd

# Charger les prix extraits
df = pd.read_csv('data/processed/prices_extracted.csv')

# Statistiques par type d'animal
print(df.groupby('animal_type')['prix'].describe())

# Prix moyens par mois
df['date'] = pd.to_datetime(df['date'])
monthly = df.set_index('date').resample('M')['prix'].mean()
print(monthly)
```

### 3. Pipeline complet

```bash
# Tout en une fois : extraction + validation + annotation
python main.py full-pipeline data/raw/mon_export.txt --annotate
```

## Dépannage rapide

### Erreur: "No module named 'src'"

```bash
# S'assurer d'être à la racine du projet
cd whatsapp_price_intelligence
python main.py --help
```

### Erreur: "UnicodeDecodeError"

Votre fichier WhatsApp a un encodage différent. Le parser essaie automatiquement UTF-8 puis ISO-8859-1.

### Aucun prix extrait

Vérifiez que vos messages contiennent :
- Des nombres (ex: 25000, 100000)
- Le mot "FCFA", "F", "francs" ou contexte de prix
- Des mentions d'animaux (porcelet, truie, verrat, porc)

## Conseils pour de meilleurs résultats

1. **Nettoyer vos exports** : Supprimez les messages système en masse
2. **Annoter régulièrement** : Validez 50-100 exemples pour suivre la qualité
3. **Ajuster les seuils** : Modifiez `src/utils/config.py` selon votre contexte
4. **Contribuer** : Signalez les bugs ou proposez des améliorations !

## Besoin d'aide ?

- 📖 Consultez le [README.md](README.md) complet
- 🐛 Ouvrez une issue sur GitHub
- 💬 Contactez l'équipe

---

**Prêt à extraire des prix ! 🐷💰**
