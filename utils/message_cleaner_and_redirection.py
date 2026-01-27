import re
from typing import Tuple, Optional, Dict, Any
from datetime import date
from utils.logger import logger


class MessageCleanerAndRedirection:
    NOISE_WORDS = [
        'bonjour', 'bonsoir', 'salut', 'hello', 'coucou', 'bsr', 'bjr',
        'merci', 'stp', 's\'il te plaît', 's\'il vous plaît', 'svp',
        'euh', 'hein', 'bon', 'voilà', 'alors', 'donc',
    ]

    EXPENSE_PATTERNS = [
        r'dépense\s+du\s+',
        r'achat\s+de\s+',
        r'j\'ai\s+acheté',
        r'j\'ai\s+dépensé',
        r'payé\s+\d+',
        r'dépense\s*:',
    ]

    PRICE_PATTERNS = [
        r'(porco|porcelet|truie|verrat|porc|cochon)',
        r'(maïs|riz|son de|soja|tourteau)',
        r'disponible\s+à',
        r'prix\s+du',
        r'\d+\s*(fcfa|franc|f|cfa)\s+(le|la)',
    ]

    CATEGORY_TO_TYPE_ID = {
        'ANIMAUX': 1,
        'ALIMENTS': 2,
        'SALAIRES': 3,
        'TRANSPORT': 4,
        'SANTÉ': 5,
        'MATÉRIEL': 6,
        'AUTRE': 7,
    }

    def __init__(self):
        self.stats = {
            'total_processed': 0,
            'routed_to_expenses': 0,
            'routed_to_gemini': 0,
            'ignored': 0
        }

    def clean_message(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text.lower().strip()

        for noise in self.NOISE_WORDS:
            cleaned = re.sub(rf'\b{re.escape(noise)}\b', '', cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'([!?.])\1+', r'\1', cleaned)

        logger.info(f"📝 Message nettoyé: '{text[:50]}...' → '{cleaned[:50]}...'")
        return cleaned

    def classify_message(self, text: str) -> str:
        text_lower = text.lower()

        for pattern in self.EXPENSE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"💰 Dépense détectée")
                return 'expense'

        for pattern in self.PRICE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"📊 Prix détecté")
                return 'price'

        return 'unknown'

    def extract_expense_data(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            amount_match = re.search(
                r'(\d+[\s\d]*)\s*(franc|fcfa|f|cfa)',
                text,
                re.IGNORECASE
            )

            if not amount_match:
                logger.warning("❌ Montant introuvable")
                return None

            montant_str = amount_match.group(1).replace(' ', '')
            montant = float(montant_str)

            date_match = re.search(
                r'dépense\s+du\s+(\w+\s+\d{1,2}\s+\w+\s+\d{4})',
                text,
                re.IGNORECASE
            )

            if date_match:
                expense_date = date.today()
            else:
                expense_date = date.today()

            description_match = re.search(
                r':\s*([^0-9]+?)(?=\s*\d+[\s\d]*\s*(?:franc|fcfa|f|cfa))',
                text,
                re.IGNORECASE
            )

            if description_match:
                description = description_match.group(1).strip()
            else:
                description = "Dépense"

            category = self._determine_category(text)
            type_depense_id = self.CATEGORY_TO_TYPE_ID.get(category, 7)  # 7 = AUTRE

            mode_paiement = self._extract_payment_mode(text)

            expense_data = {
                'date': expense_date,
                'type_depense_id': type_depense_id,
                'description': description,
                'montant': montant,
                'mode_paiement': mode_paiement,
                'observations': text
            }

            logger.info(f"✅ Dépense extraite: {expense_data}")
            return expense_data

        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            return None

    def _determine_category(self, text: str) -> str:
        text_lower = text.lower()

        if any(w in text_lower for w in ['porc', 'truie', 'porcelet', 'verrat', 'cochon']):
            return 'ANIMAUX'
        elif any(w in text_lower for w in ['maïs', 'riz', 'son', 'soja', 'aliment']):
            return 'ALIMENTS'
        elif any(w in text_lower for w in ['salaire', 'employé', 'personnel']):
            return 'SALAIRES'
        elif any(w in text_lower for w in ['transport', 'carburant', 'essence']):
            return 'TRANSPORT'
        elif any(w in text_lower for w in ['médicament', 'vaccin', 'vétérinaire']):
            return 'SANTÉ'
        elif any(w in text_lower for w in ['outil', 'équipement', 'matériel']):
            return 'MATÉRIEL'
        else:
            return 'AUTRE'

    def _extract_payment_mode(self, text: str) -> str:
        text_lower = text.lower()

        if any(w in text_lower for w in ['carte', 'visa', 'mastercard']):
            return 'Carte bancaire'
        elif any(w in text_lower for w in ['mobile', 'orange money', 'moov', 'wave']):
            return 'Mobile Money'
        elif any(w in text_lower for w in ['chèque']):
            return 'Chèque'
        elif any(w in text_lower for w in ['virement', 'banque']):
            return 'Virement'
        else:
            return 'Espèces'

    def redirection_message(
            self,
            text: str,
            sender: str = "unknown"
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        self.stats['total_processed'] += 1

        logger.info("=" * 80)
        logger.info(f"🔀 ROUTAGE MESSAGE de {sender}")
        logger.info("=" * 80)

        cleaned = self.clean_message(text)

        if not cleaned or len(cleaned) < 5:
            self.stats['ignored'] += 1
            return ('ignore', None, None)

        msg_type = self.classify_message(cleaned)

        if msg_type == 'expense':
            expense_data = self.extract_expense_data(text)

            if expense_data:
                self.stats['routed_to_expenses'] += 1
                return ('expense', None, expense_data)
            else:
                self.stats['routed_to_gemini'] += 1
                return ('gemini', cleaned, None)

        elif msg_type == 'price':
            self.stats['routed_to_gemini'] += 1
            return ('gemini', cleaned, None)

        else:
            self.stats['routed_to_gemini'] += 1
            return ('gemini', cleaned, None)

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


message_cleaner_and_redirection = MessageCleanerAndRedirection()