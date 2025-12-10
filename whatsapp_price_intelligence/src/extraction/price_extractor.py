"""
Extracteur de prix structuré avec contexte
Extrait non seulement les prix mais aussi leur contexte (animal, unité, action)
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
from ..utils import (
    AnimalTypes, ActionTypes, ProductTypes,
    ANIMAL_KEYWORDS, ALIMENT_KEYWORDS, ACTION_KEYWORDS,
    PRICE_RANGES, AGE_RANGES, setup_logger
)

logger = setup_logger(__name__)


@dataclass
class ExtractedPrice:
    """Structure pour un prix extrait"""
    prix: int
    unite: str
    type_produit: str  # animal, aliment, medicament
    animal_type: Optional[str] = None
    action_type: Optional[str] = None
    contexte: str = ""
    confiance: float = 0.0  # Score de confiance 0-1


class PriceExtractor:
    """Extracteur de prix avec classification contextuelle"""
    
    # Patterns de prix avec contexte
    PRICE_PATTERNS = [
        # Prix avec FCFA/F explicite
        (r'(\d{1,3}(?:\s?\d{3})*)\s*(?:fcfa|f\s*cfa|francs?|frs?)\b', 1.0),
        # Prix précédé de "à", "de", "pour"
        (r'(?:à|de|pour|prix)\s+(\d{1,3}(?:\s?\d{3})*)\s*(?:fcfa|f|frs?)?\b', 0.9),
        # Prix dans des guillemets ou parenthèses
        (r'["\(](\d{1,3}(?:\s?\d{3})*)\s*(?:fcfa|f|frs?)?["\)]', 0.8),
        # Prix avec virgule décimale
        (r'(\d{1,3}(?:\s?\d{3})*(?:,\d{1,2})?)\s*(?:fcfa|f|frs?)\b', 0.9),
        # Prix après verbe de vente
        (r'(?:vente|vendre|vendu|cède|prix|coûte)\s+(?:à|de|pour)?\s*(\d{1,3}(?:\s?\d{3})*)', 0.85),
    ]
    
    # Patterns d'unités
    UNIT_PATTERNS = [
        (r'(\d+)\s*kg', 'kg'),
        (r'sac(?:\s+de)?\s+(\d+)\s*kg', 'sac'),
        (r'tonne', 'tonne'),
        (r't\b', 'tonne'),
        (r'unité', 'unité'),
        (r'pièce', 'unité'),
        (r'tête', 'unité'),
    ]
    
    def __init__(self):
        self.stats = {
            'total_extractions': 0,
            'animals_detected': 0,
            'aliments_detected': 0,
            'failed_extractions': 0
        }
    
    def extract_from_message(self, message: str, message_id: int = 0) -> List[ExtractedPrice]:
        """
        Extrait tous les prix structurés d'un message
        
        Args:
            message: Texte du message
            message_id: ID du message (pour logging)
        
        Returns:
            Liste de prix extraits avec leur contexte
        """
        self.stats['total_extractions'] += 1
        extracted_prices = []
        
        message_lower = message.lower()
        
        # 1. Extraire tous les prix avec leur position
        price_matches = self._find_all_prices(message)
        
        if not price_matches:
            return []
        
        # 2. Pour chaque prix, extraire le contexte environnant
        for price_value, position, confidence in price_matches:
            # Contexte: 50 caractères avant et après
            start = max(0, position - 50)
            end = min(len(message), position + 50)
            context = message[start:end].lower()
            
            # 3. Classifier le type de produit
            product_type = self._classify_product_type(context, message_lower)
            
            # 4. Si c'est un animal, déterminer le type
            animal_type = None
            if product_type == ProductTypes.ANIMAL:
                animal_type = self._classify_animal_type(context, message_lower)
                self.stats['animals_detected'] += 1
            elif product_type == ProductTypes.ALIMENT:
                self.stats['aliments_detected'] += 1
            
            # 5. Déterminer l'action (vente/achat/info)
            action_type = self._classify_action(message_lower)
            
            # 6. Extraire l'unité
            unit = self._extract_unit(context)
            
            # 7. Valider le prix selon le type
            if not self._validate_price(price_value, product_type, animal_type, unit):
                logger.debug(f"Prix {price_value} rejeté (validation)")
                continue
            
            # 8. Calculer score de confiance global
            final_confidence = self._calculate_confidence(
                confidence, product_type, animal_type, action_type, unit
            )
            
            extracted = ExtractedPrice(
                prix=price_value,
                unite=unit,
                type_produit=product_type,
                animal_type=animal_type,
                action_type=action_type,
                contexte=context.strip(),
                confiance=final_confidence
            )
            
            extracted_prices.append(extracted)
        
        # Dédupliquer les prix identiques
        extracted_prices = self._deduplicate(extracted_prices)
        
        return extracted_prices
    
    def _find_all_prices(self, text: str) -> List[Tuple[int, int, float]]:
        """
        Trouve tous les prix dans un texte avec leur position
        
        Returns:
            Liste de tuples (prix, position, confiance)
        """
        prices = []
        
        for pattern, base_confidence in self.PRICE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    price_str = match.group(1)
                    price_value = self._normalize_price(price_str)
                    
                    if price_value:
                        prices.append((
                            price_value,
                            match.start(),
                            base_confidence
                        ))
                except Exception as e:
                    logger.debug(f"Erreur parsing prix: {e}")
                    continue
        
        # Trier par position et dédupliquer positions proches
        prices = sorted(prices, key=lambda x: x[1])
        unique_prices = []
        
        for price, pos, conf in prices:
            # Si prix similaire dans ±10 caractères, garder le meilleur
            if not any(
                abs(p[1] - pos) < 10 and p[0] == price 
                for p in unique_prices
            ):
                unique_prices.append((price, pos, conf))
        
        return unique_prices
    
    def _normalize_price(self, price_str: str) -> Optional[int]:
        """Normalise une chaîne de prix en entier"""
        # Nettoyer
        price_clean = re.sub(r'[^\d,\s]', '', str(price_str))
        price_clean = price_clean.replace(' ', '')
        
        # Gérer virgule décimale
        if ',' in price_clean:
            price_clean = price_clean.replace(',', '.')
        
        try:
            return int(float(price_clean))
        except (ValueError, TypeError):
            return None
    
    def _classify_product_type(self, context: str, full_message: str) -> str:
        """Classifie le type de produit (animal/aliment/autre)"""
        # Vérifier mots-clés animaux
        animal_score = sum(
            2 if keyword in context else (1 if keyword in full_message else 0)
            for keywords in ANIMAL_KEYWORDS.values()
            for keyword in keywords
        )
        
        # Vérifier mots-clés aliments
        aliment_score = sum(
            2 if keyword in context else (1 if keyword in full_message else 0)
            for keyword in ALIMENT_KEYWORDS
        )
        
        if animal_score > aliment_score and animal_score > 0:
            return ProductTypes.ANIMAL
        elif aliment_score > animal_score and aliment_score > 0:
            return ProductTypes.ALIMENT
        else:
            return ProductTypes.NON_SPECIFIE
    
    def _classify_animal_type(self, context: str, full_message: str) -> str:
        """Classifie le type d'animal"""
        scores = {}
        
        for animal_type, keywords in ANIMAL_KEYWORDS.items():
            score = sum(
                3 if kw in context else (1 if kw in full_message else 0)
                for kw in keywords
            )
            
            # Bonus si âge cohérent
            age_days = self._extract_age_days(full_message)
            if age_days:
                age_min, age_max = AGE_RANGES.get(animal_type, (0, 9999))
                if age_min <= age_days <= age_max:
                    score += 2
            
            scores[animal_type] = score
        
        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else AnimalTypes.NON_SPECIFIE
    
    def _classify_action(self, text: str) -> str:
        """Classifie l'action (vente/achat/info)"""
        scores = {}
        
        for action, keywords in ACTION_KEYWORDS.items():
            scores[action] = sum(2 if kw in text else 0 for kw in keywords)
        
        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else ActionTypes.NON_SPECIFIE
    
    def _extract_unit(self, context: str) -> str:
        """Extrait l'unité de mesure"""
        for pattern, unit in self.UNIT_PATTERNS:
            if re.search(pattern, context, re.IGNORECASE):
                return unit
        return 'non_specifie'
    
    def _extract_age_days(self, text: str) -> Optional[int]:
        """Extrait l'âge en jours"""
        age_patterns = [
            (r'(\d+)\s*mois', 30),
            (r'(\d+)\s*semaines?', 7),
            (r'(\d+)\s*jours?', 1),
            (r'(\d+)\s*ans?', 365),
        ]
        
        for pattern, multiplier in age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1)) * multiplier
        
        return None
    
    def _validate_price(
        self, 
        price: int, 
        product_type: str, 
        animal_type: Optional[str],
        unit: str
    ) -> bool:
        """Valide qu'un prix est dans un range raisonnable"""
        # Range général
        if price < 1_000 or price > 2_000_000:
            return False
        
        # Validation spécifique animal
        if product_type == ProductTypes.ANIMAL and animal_type:
            price_range = PRICE_RANGES.get(animal_type)
            if price_range:
                min_price, max_price = price_range
                return min_price <= price <= max_price
        
        # Validation aliment
        if product_type == ProductTypes.ALIMENT:
            if unit == 'tonne':
                return 100_000 <= price <= 500_000
            elif unit in ['sac', 'kg']:
                return 3_000 <= price <= 50_000
        
        return True
    
    def _calculate_confidence(
        self, 
        base_conf: float,
        product_type: str,
        animal_type: Optional[str],
        action_type: str,
        unit: str
    ) -> float:
        """Calcule un score de confiance global"""
        confidence = base_conf
        
        # Bonus si produit identifié
        if product_type != ProductTypes.NON_SPECIFIE:
            confidence += 0.1
        
        # Bonus si animal spécifique
        if animal_type and animal_type != AnimalTypes.NON_SPECIFIE:
            confidence += 0.1
        
        # Bonus si action claire
        if action_type != ActionTypes.NON_SPECIFIE:
            confidence += 0.05
        
        # Bonus si unité trouvée
        if unit != 'non_specifie':
            confidence += 0.05
        
        return min(1.0, confidence)
    
    def _deduplicate(self, prices: List[ExtractedPrice]) -> List[ExtractedPrice]:
        """Déduplique les prix identiques, garde le meilleur"""
        if not prices:
            return []
        
        unique = {}
        for p in prices:
            key = (p.prix, p.animal_type, p.type_produit)
            if key not in unique or p.confiance > unique[key].confiance:
                unique[key] = p
        
        return list(unique.values())
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques d'extraction"""
        return self.stats.copy()


def extract_prices_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique l'extraction sur un DataFrame complet
    
    Args:
        df: DataFrame avec colonnes 'message_id' et 'message'
    
    Returns:
        DataFrame enrichi avec prix et contexte
    """
    extractor = PriceExtractor()
    
    all_extractions = []
    
    for idx, row in df.iterrows():
        message_id = row['message_id']
        message = row['message']
        
        prices = extractor.extract_from_message(message, message_id)
        
        for price_obj in prices:
            extraction = {
                'message_id': message_id,
                'date': row.get('date'),
                'sender': row.get('sender'),
                'message': message,
                'prix': price_obj.prix,
                'unite': price_obj.unite,
                'type_produit': price_obj.type_produit,
                'animal_type': price_obj.animal_type,
                'action_type': price_obj.action_type,
                'confiance': price_obj.confiance,
                'contexte': price_obj.contexte
            }
            all_extractions.append(extraction)
    
    result_df = pd.DataFrame(all_extractions)
    
    logger.info(f"✓ Extraction terminée: {len(result_df)} prix extraits")
    logger.info(f"Stats: {extractor.get_stats()}")
    
    return result_df
