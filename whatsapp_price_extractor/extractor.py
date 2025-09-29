# whatsapp_price_extractor/extractor.py
"""
Module d'extraction de prix utilisant les LLM
"""

from transformers import pipeline
import re

class PigPriceExtractorLLM:
    def __init__(self):
        print("Initialisation du systeme LLM...")
        try:
            self.ner_pipeline = pipeline("ner", 
                                        model="dbmdz/bert-large-cased-finetuned-conll03-english",
                                        aggregation_strategy="simple")
        except:
            print("Modele NER indisponible, fallback simple")
            self.ner_pipeline = pipeline("ner", aggregation_strategy="simple")
        try:
            self.classifier = pipeline("text-classification", 
                                     model="cardiffnlp/twitter-roberta-base-sentiment-latest")
        except:
            self.classifier = None
        self.price_patterns = [
            r"(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?)\s*(?:fcfa|f|frs)?",
            r"Ã \s*(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?)\s*(?:fcfa|f|frs)?",
            r"prix.*?(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d+)?)\s*(?:fcfa|f|frs)?",
        ]
        print("Systeme LLM prêt.")

    def extract_prices_with_llm(self, text):
        prices = []
        for pattern in self.price_patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                try:
                    price = self._normalize_price(match.group(1))
                    prices.append(price)
                except:
                    continue
        try:
            entities = self.ner_pipeline(text)
            for entity in entities:
                if entity['entity_group'] in ['CARDINAL', 'MONEY'] or 'NUM' in entity['entity_group']:
                    numbers = re.findall(r'\d+', entity['word'])
                    for num in numbers:
                        potential_price = int(num)
                        if 1000 <= potential_price <= 2000000:
                            prices.append(potential_price)
        except:
            pass
        return list(set(prices))
    
    def _normalize_price(self, price_str):
        price_clean = re.sub(r'[^\d.,]', '', str(price_str))
        price_clean = price_clean.replace(' ', '').replace('.', '')
        if ',' in price_clean:
            price_clean = price_clean.replace(',', '.')
        try:
            return int(float(price_clean))
        except:
            return None
    
    def classify_animal_with_llm(self, text):
        animal_context = {
            'verrat': {'keywords': ['verrat', 'reproducteur', 'male reproducteur'], 'context': ['reproduction', 'saillie', 'monte'], 'age_range': (180, 1800)},
            'truie': {'keywords': ['truie', 'femelle', 'gestante', 'portÃ©e'], 'context': ['gestation', 'portÃ©e', 'mise bas', 'sevrage'], 'age_range': (270, 2190)},
            'porcelet': {'keywords': ['porcelet', 'petit', 'sevrage', 'jeune'], 'context': ['sevrage', 'allaitement', 'croissance'], 'age_range': (1, 90)},
            'porc': {'keywords': ['porc', 'cochon', 'embouche', 'engraissement'], 'context': ['embouche', 'engraissement', 'abattage', 'viande'], 'age_range': (90, 365)}
        }
        text_lower = text.lower()
        scores = {}
        age_days = self._extract_age_days(text)
        for animal_type, info in animal_context.items():
            score = 0
            for keyword in info['keywords']:
                if keyword in text_lower:
                    score += 3
            for context_word in info['context']:
                if context_word in text_lower:
                    score += 1
            if age_days:
                age_min, age_max = info['age_range']
                if age_min <= age_days <= age_max:
                    score += 2
                else:
                    score -= 1
            scores[animal_type] = score
        best_animal = max(scores.items(), key=lambda x: x[1])
        return best_animal[0] if best_animal[1] > 0 else 'non_specifie'
    
    def _extract_age_days(self, text):
        age_patterns = [r'(\d+)\s*mois', r'(\d+)\s*moi[s]?', r'(\d+)\s*jours?', r'(\d+)\s*semaines?']
        for pattern in age_patterns:
            match = re.search(pattern, text.lower())
            if match:
                value = int(match.group(1))
                if 'moi' in pattern:
                    return value*30
                elif 'semaine' in pattern:
                    return value*7
                else:
                    return value
        return None
    
    def classify_action_with_context(self, text):
        if self.classifier:
            try:
                sentiment = self.classifier(text[:512])
                sentiment_label = sentiment[0]['label'] if sentiment else 'NEUTRAL'
            except:
                sentiment_label = 'NEUTRAL'
        else:
            sentiment_label = 'NEUTRAL'
        text_lower = text.lower()
        vente_indicators = ['vente', 'vendre', 'à vendre', 'en vente', 'cède', 'propose', 'vend', 'disponible', 'stock']
        achat_indicators = ['recherche', 'cherche', 'achète', 'achat', 'besoin de', 'veut', 'intéressé par', 'recherche']
        info_indicators = ['prix', 'coût', 'combien', 'tarif', 'montant', 'valeur', 'estimation']
        if any(i in text_lower for i in vente_indicators):
            return 'vente'
        elif any(i in text_lower for i in achat_indicators):
            return 'achat'
        elif any(i in text_lower for i in info_indicators):
            return 'prix_info'
        return 'non_specifie'