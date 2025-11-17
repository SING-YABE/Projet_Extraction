"""Module d'extraction de prix optimisé pour WhatsApp – contexte Afrique de l'Ouest"""

from transformers import pipeline
import re
import logging
import unicodedata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PigPriceExtractorLLM:
    """Extraction robuste (prix / animal / action) optimisée pour Burkina Faso"""

    def __init__(self):
        logger.info("Initialisation du système d'extraction...")

        self.ner_pipeline = self._initialize_ner()
        self.classifier = self._initialize_sentiment()

        # -----------------------
        # PATTERNS PRIX (fiables)
        # -----------------------
        self.price_patterns = [
            r'(\d{2,3}(?:\s?\d{3})*)\s*(?:fcfa|f\s*cfa|francs?|frs?)\b',
            r'(?:à|de|pour)\s+(\d{2,3}(?:\s?\d{3})*)\s*(?:fcfa|f|frs?)?\b',
            r'[(" ](\d{2,3}(?:\s?\d{3}))[\)" ]',
            r'(\d{2,6})\s*(?:fcfa|f|frs?)\b',
            r'(?:prix|coûte|vendu|cédé)\s*(?:à|de|pour)?\s*(\d{2,6})',
        ]

        self._initialize_animal_context()
        logger.info("Système prêt")

    # ---------------------------------------------------------------------
    #                      INITIALISATION DES PIPELINES
    # ---------------------------------------------------------------------

    def _initialize_ner(self):
        models = [
            "Jean-Baptiste/camembert-ner",
            "Davlan/xlm-roberta-base-wikiann-ner"
        ]
        for m in models:
            try:
                return pipeline("ner", model=m, aggregation_strategy="simple")
            except:
                continue
        return None

    def _initialize_sentiment(self):
        try:
            return pipeline("text-classification",
                            model="cmarkea/distilcamembert-base-sentiment")
        except:
            return None

    # ---------------------------------------------------------------------
    #                      CONTEXTE ANIMAL OPTIMISÉ
    # ---------------------------------------------------------------------

    def _initialize_animal_context(self):

        # Remplacé par liste plus strictes
        self.animal_context = {
            'porc': {
                'keywords': [
                    'porc','poc','por','pork','cochon','cochons','porcin',
                    'embouche','gros porc','adulte porc'
                ],
                'context': ['engrais', 'abattage', 'kg'],
                'age_range': (90, 460)
            },
            'porcelet': {
                'keywords': [
                    'porcelet','porclet','porchilet','pce','pclet',
                    'bébé porc','petit porc','sevré'
                ],
                'context': ['sevrage', 'petit', '3kg','5kg','jeune'],
                'age_range': (1, 90)
            },
            'truie': {
                'keywords': ['truie','trui','truy','femelle porc','gestante','enceinte'],
                'context': ['mise bas','lactation','gestation'],
                'age_range': (200, 2000)
            },
            'verrat': {
                'keywords': ['verrat','verat','male repro','reproducteur','mâle'],
                'context': ['saillie','monte','repro'],
                'age_range': (180, 2000)
            }
        }

    # ---------------------------------------------------------------------
    #                      EXTRACTION DES PRIX
    # ---------------------------------------------------------------------

    def extract_prices_with_llm(self, text):
        prices = set()
        prices.update(self._extract_prices_regex(text))

        if self.ner_pipeline and len(prices) < 2:
            prices.update(self._extract_prices_ner(text))

        return sorted(prices)

    def _extract_prices_regex(self, text):
        res = set()
        for pat in self.price_patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                try:
                    price = self._normalize_price(m.group(1))
                    if self._validate_price(price):
                        res.add(price)
                except:
                    continue
        return res

    def _extract_prices_ner(self, text):
        res = set()
        try:
            ents = self.ner_pipeline(text)
            for ent in ents:
                nums = re.findall(r'\d{3,6}', ent['word'])
                for n in nums:
                    n = int(n)
                    if self._validate_price(n):
                        res.add(n)
        except:
            pass
        return res

    def _normalize_price(self, s):
        s = unicodedata.normalize("NFKD", s)
        s = s.replace(" ", "").replace(",", ".")
        return int(float(s))

    def _validate_price(self, p):
        return 1000 <= p <= 2_000_000

    # ---------------------------------------------------------------------
    #                🔥 CLASSIFICATION ANIMAL (VERSION FIX)
    # ---------------------------------------------------------------------

    def classify_animal_with_llm(self, text):

        t = self._normalize_text(text)
        scores = {a: 0 for a in self.animal_context}

        # --- Match strict mots-clés
        for animal, ctx in self.animal_context.items():
            for kw in ctx['keywords']:
                if f" {kw} " in t:
                    scores[animal] += 5

        # --- Match contextuel (plus léger)
        for animal, ctx in self.animal_context.items():
            for c in ctx['context']:
                if c in t:
                    scores[animal] += 2

        # --- Age
        age = self._extract_age_days(t)
        if age:
            for animal, ctx in self.animal_context.items():
                amin, amax = ctx['age_range']
                if amin <= age <= amax:
                    scores[animal] += 2

        # --- Fuzzy limité (évite les 24/5/7 faux animaux)
        for animal, ctx in self.animal_context.items():
            for kw in ctx['keywords']:
                if self._fuzzy_match(t, kw):
                    scores[animal] += 1   # faible pondération

        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 3 else "non_specifie"

    def _normalize_text(self, txt):
        txt = unicodedata.normalize("NFKD", txt.lower())
        txt = "".join(c for c in txt if c.isalnum() or c == " ")
        return f" {txt} "

    def _fuzzy_match(self, text, kw):
        if kw in text:
            return True

        for word in text.split():
            if abs(len(word) - len(kw)) > 1:
                continue
            # distance Hamming simplifiée
            dist = sum(a != b for a, b in zip(word, kw))
            if dist == 1:
                return True
        return False

    # ---------------------------------------------------------------------

    def _extract_age_days(self, text):
        p = [
            (r'(\d+)\s*mois', 30),
            (r'(\d+)\s*semaines?', 7),
            (r'(\d+)\s*jours?', 1),
            (r'(\d+)\s*ans?', 365),
        ]
        for pat, mul in p:
            m = re.search(pat, text)
            if m:
                return int(m.group(1)) * mul
        return None

    # ---------------------------------------------------------------------

    def classify_action_with_context(self, text):
        t = text.lower()

        indicators = {
            'vente': ['vente', 'vend', 'vendre', 'cède', 'propose', 'stock'],
            'achat': ['cherche', 'recherche', 'achète', 'besoin de', 'intéressé'],
            'prix_info': ['prix', 'tarif', 'combien', 'montant']
        }

        scores = {
            'vente': sum(3 for i in indicators['vente'] if i in t),
            'achat': sum(3 for i in indicators['achat'] if i in t),
            'prix_info': sum(2 for i in indicators['prix_info'] if i in t)
        }

        if self.classifier:
            try:
                sentiment = self.classifier(t[:512])[0]
                if sentiment['label'] == 'positive':
                    scores['vente'] += 1
            except:
                pass

        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else "non_specifie"
