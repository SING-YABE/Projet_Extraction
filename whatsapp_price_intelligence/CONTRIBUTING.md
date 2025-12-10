# 🤝 Guide de Contribution

Merci de votre intérêt pour améliorer WhatsApp Price Intelligence !

## 🎯 Façons de contribuer

- 🐛 Reporter des bugs
- 💡 Proposer des fonctionnalités
- 📝 Améliorer la documentation
- 🔧 Soumettre du code
- 📊 Partager des données (anonymisées)
- 🧪 Écrire des tests

## 📋 Avant de commencer

1. **Vérifiez les issues existantes** pour éviter les doublons
2. **Ouvrez une issue** pour discuter des grandes modifications
3. **Testez localement** avant de soumettre

## 🔧 Setup développement

```bash
# 1. Fork et clone
git clone https://github.com/votre-username/whatsapp-price-intelligence.git
cd whatsapp-price-intelligence

# 2. Créer une branche
git checkout -b feature/ma-fonctionnalite

# 3. Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 4. Installation mode dev
pip install -r requirements.txt
pip install -e .

# 5. Vérifier
python test_setup.py
```

## 📝 Style de code

### Python
```python
# Black pour le formatage
black src/

# Flake8 pour linting
flake8 src/

# Docstrings Google style
def ma_fonction(param: str) -> int:
    """
    Brève description
    
    Args:
        param: Description du paramètre
    
    Returns:
        Description du retour
    """
    return 42
```

### Commits
```bash
# Format: type(scope): message

git commit -m "feat(extraction): ajout pattern pour devises"
git commit -m "fix(parser): correction dates futures"
git commit -m "docs(readme): mise à jour installation"
```

**Types** :
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction bug
- `docs`: Documentation
- `test`: Tests
- `refactor`: Refactorisation
- `style`: Formatage
- `chore`: Maintenance

## 🧪 Tests

```bash
# Lancer tous les tests
pytest tests/

# Tests avec couverture
pytest --cov=src tests/

# Test spécifique
pytest tests/test_extraction.py::test_price_extraction
```

### Écrire un test
```python
# tests/test_extraction.py

def test_price_extraction():
    """Test extraction basique"""
    from src.extraction import PriceExtractor
    
    extractor = PriceExtractor()
    message = "Porcelets à 25000f"
    
    prices = extractor.extract_from_message(message)
    
    assert len(prices) == 1
    assert prices[0].prix == 25000
    assert prices[0].animal_type == 'porcelet'
```

## 📦 Pull Request

### Checklist
- [ ] Code testé localement
- [ ] Tests ajoutés si nécessaire
- [ ] Documentation mise à jour
- [ ] Commits clairs et atomiques
- [ ] Pas de conflits avec main

### Template
```markdown
## Description
Brève description des changements

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Tests
Comment avez-vous testé ?

## Screenshots
Si applicable

## Checklist
- [ ] Mon code suit le style du projet
- [ ] J'ai ajouté des tests
- [ ] La documentation est à jour
```

## 🐛 Reporter un bug

### Template issue
```markdown
**Description**
Description claire du bug

**Pour reproduire**
1. Étape 1
2. Étape 2
3. Erreur observée

**Comportement attendu**
Ce qui devrait se passer

**Environnement**
- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.10]
- Version: [e.g. 0.1.0]

**Logs/Screenshots**
Si applicable
```

## 💡 Proposer une fonctionnalité

### Template
```markdown
**Problème**
Quel problème cette fonctionnalité résout-elle ?

**Solution proposée**
Description de la solution

**Alternatives considérées**
Autres approches possibles

**Contexte additionnel**
Screenshots, exemples, etc.
```

## 🌟 Priorités de contribution

### 🔥 Haute priorité
- Amélioration patterns extraction
- Ajout de tests unitaires
- Documentation code manquante
- Correction bugs critiques

### 📈 Moyenne priorité
- Nouvelles features extraction
- Optimisation performances
- Modèles ML
- Dashboard

### 💎 Basse priorité
- Refactoring non-urgent
- Nouvelles langues
- Features expérimentales

## 📚 Ressources

### Documentation
- [README.md](README.md) - Doc principale
- [QUICKSTART.md](QUICKSTART.md) - Démarrage rapide
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Architecture

### Communication
- GitHub Issues - Questions/Bugs
- GitHub Discussions - Discussions générales
- Email - Contact direct

## ⚖️ Code de conduite

### Nos engagements
- Environnement accueillant et inclusif
- Respect des opinions divergentes
- Feedback constructif
- Focus sur l'intérêt du projet

### Comportements inacceptables
- Langage ou images offensants
- Trolling ou insultes
- Harcèlement
- Autres comportements non professionnels

## 🎓 Apprentissage

### Débuter avec le projet
1. Lisez le README complet
2. Lancez demo.py
3. Explorez le code avec test_setup.py
4. Commencez par de petites contributions

### Ressources Python
- [Python Docs](https://docs.python.org/3/)
- [pandas Docs](https://pandas.pydata.org/docs/)
- [scikit-learn Docs](https://scikit-learn.org/)

## 🙏 Remerciements

Merci à tous les contributeurs !

### Comment être listé
- Code merged : Automatiquement ajouté
- Documentation : Crédit dans AUTHORS.md
- Issues/Discussions : Mention spéciale

---

**Questions ?** Ouvrez une issue ou contactez-nous !

**Merci de contribuer ! 🎉**
