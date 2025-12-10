"""Module d'extraction de prix avec modèles adaptés au contexte africain francophone"""
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import re

class PigPriceExtractorLLM:
    def __init__(self):
        print("Initialisation du système LLM adapté...")
        
        try:
            self.ner_pipeline = pipeline(
                "ner",
                model="Jean-Baptiste/camembert-ner",  
                aggregation_strategy="simple"
            )
        except:
            try:
                 # Multilingue africain
                self.ner_pipeline = pipeline(
                    "ner",
                    model="Davlan/xlm-roberta-base-wikiann-ner", 
                    aggregation_strategy="simple"
                )
            except:
                print("Fallback: extraction par expressions régulières uniquement")
                self.ner_pipeline = None
        
        # Sentiment français
        try:
            self.classifier = pipeline(
                "text-classification",
                model="cmarkea/distilcamembert-base-sentiment"  
            )
        except:
            self.classifier = None
        
        # Patterns 
        self.price_patterns = [
            r'(\d{1,3}(?:\s?\d{3})*)\s*(?:fcfa|f\s*cfa|francs?|frs?)\b',
            
            r'(?:à|de|pour)\s+(\d{1,3}(?:\s?\d{3})*)\s*(?:fcfa|f|frs?)?\b',
            
            r'["\(](\d{1,3}(?:\s?\d{3})*)\s*(?:fcfa|f|frs?)?["\)]',
            
            r'(\d{1,3}(?:\s?\d{3})*(?:,\d{1,2})?)\s*(?:fcfa|f|frs?)\b',
            
            r'(?:prix|coûte|vendre|vendu|cède)\s+(?:à|de|pour)?\s*(\d{1,3}(?:\s?\d{3})*)',
        ]
        
        print("Système LLM prêt.")
    
    def extract_prices_with_llm(self, text):
        """Extraction robuste avec fallback"""
        prices = []
        
        # Méthode 1: Patterns réguliers (plus fiable)
        for pattern in self.price_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price = self._normalize_price(match.group(1))
                    if price and 1000 <= price <= 2000000:  # Validation range
                        prices.append(price)
                except:
                    continue
        
        # Méthode 2: NER uniquement si disponible et pas assez de résultats
        if self.ner_pipeline and len(prices) < 2:
            try:
                entities = self.ner_pipeline(text)
                for entity in entities:
                    if entity['entity_group'] in ['MISC', 'O'] or 'NUM' in entity.get('entity_group', ''):
                        numbers = re.findall(r'\d+', entity['word'])
                        for num in numbers:
                            try:
                                potential_price = int(num)
                                if 1000 <= potential_price <= 2000000:
                                    prices.append(potential_price)
                            except:
                                continue
            except Exception as e:
                print(f"NER échoué: {e}")
        
        # Retourner les prix uniques triés
        return sorted(list(set(prices)))
    
    def _normalize_price(self, price_str):
        """Normalisation adaptée au format africain"""
        # Nettoyer
        price_clean = re.sub(r'[^\d,\s]', '', str(price_str))
        price_clean = price_clean.replace(' ', '')  # Enlever espaces
        
        # Gérer virgule décimale (peu fréquent pour FCFA)
        if ',' in price_clean:
            price_clean = price_clean.replace(',', '.')
        
        try:
            return int(float(price_clean))
        except:
            return None
    
    def classify_animal_with_llm(self, text):
        """Classification avec contexte local"""
        animal_context = {
            'verrat': {
                'keywords': ['verrat', 'reproducteur', 'mâle', 'male', 'étalon'],
                'context': ['reproduction', 'saillie', 'monte', 'service'],
                'age_range': (180, 1800)
            },
            'truie': {
                'keywords': ['truie', 'femelle', 'gestante', 'portée', 'mère'],
                'context': ['gestation', 'portée', 'mise bas', 'sevrage', 'allaitante'],
                'age_range': (270, 2190)
            },
            'porcelet': {
                'keywords': ['porcelet', 'petit', 'sevré', 'jeune', 'bébé'],
                'context': ['sevrage', 'allaitement', 'croissance', 'né'],
                'age_range': (1, 90)
            },
            'porc': {
                'keywords': ['porc', 'cochon', 'embouche', 'gros', 'adulte'],
                'context': ['embouche', 'engraissement', 'abattage', 'viande', 'kg'],
                'age_range': (90, 365)
            }
        }
        
        text_lower = text.lower()
        scores = {}
        age_days = self._extract_age_days(text)
        
        for animal_type, info in animal_context.items():
            score = 0
            
            # Mots-clés principaux
            for keyword in info['keywords']:
                if keyword in text_lower:
                    score += 5
            
            # Contexte
            for context_word in info['context']:
                if context_word in text_lower:
                    score += 2
            
            # Âge
            if age_days:
                age_min, age_max = info['age_range']
                if age_min <= age_days <= age_max:
                    score += 3
                elif abs(age_days - age_min) < 30 or abs(age_days - age_max) < 30:
                    score += 1
            
            scores[animal_type] = score
        
        best_animal = max(scores.items(), key=lambda x: x[1])
        return best_animal[0] if best_animal[1] > 0 else 'non_specifie'
    
    def _extract_age_days(self, text):
        """Extraction d'âge robuste"""
        age_patterns = [
            (r'(\d+)\s*mois', 30),
            (r'(\d+)\s*semaines?', 7),
            (r'(\d+)\s*jours?', 1),
            (r'(\d+)\s*ans?', 365),
        ]
        
        for pattern, multiplier in age_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return int(match.group(1)) * multiplier
        
        return None
    
    def classify_action_with_context(self, text):
        """Classification d'action améliorée"""
        text_lower = text.lower()
        
        # Indicateurs forts
        vente_indicators = [
            'vente', 'vendre', 'à vendre', 'en vente', 'cède', 
            'propose', 'vend', 'disponible', 'stock', 'vente de'
        ]
        achat_indicators = [
            'recherche', 'cherche', 'achète', 'achat', 'besoin de', 
            'veut', 'intéressé', 'demande', 'je veux'
        ]
        info_indicators = [
            'prix', 'coût', 'combien', 'tarif', 'montant', 
            'valeur', 'estimation', 'quel est le prix'
        ]
        
        # Score pondéré
        vente_score = sum(3 if ind in text_lower else 0 for ind in vente_indicators)
        achat_score = sum(3 if ind in text_lower else 0 for ind in achat_indicators)
        info_score = sum(2 if ind in text_lower else 0 for ind in info_indicators)
        
        # Utiliser le classifier si disponible
        if self.classifier:
            try:
                sentiment = self.classifier(text[:512])
                if sentiment[0]['label'] == 'positive':
                    vente_score += 1
            except:
                pass
        
        # Décision
        if vente_score > max(achat_score, info_score):
            return 'vente'
        elif achat_score > max(vente_score, info_score):
            return 'achat'
        elif info_score > 0:
            return 'prix_info'
        
        return 'non_specifie'