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
    ]

    PRICE_PATTERNS = [
        r'(porco|porcelet|truie|verrat|porc|cochon)',
        r'(maïs|riz|son de|soja|tourteau)',
        r'disponible\s+à',
        r'prix\s+du',
        r'\d+\s*(fcfa|franc|f|cfa)\s+(le|la)',
        r'j\'ai\s+',
        r'vend',
        r'cherch',
    ]

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
                logger.info(f"💰 Format dépense strict détecté")
                return 'expense'

        for pattern in self.PRICE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"📊 Prix/marché détecté")
                return 'price'

        return 'unknown'

    def extract_expense_data(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            if not re.search(r'dépense\s+du\s+', text, re.IGNORECASE):
                return None

            amount_match = re.search(
                r'(\d+[\s\d]*)\s*(?:franc|fcfa|f)?',
                text,
                re.IGNORECASE
            )

            if not amount_match:
                logger.warning("❌ Montant introuvable")
                return None

            montant_str = amount_match.group(1).replace(' ', '').replace('\u202f', '')

            try:
                montant = float(montant_str)
            except ValueError:
                logger.warning(f"❌ Montant invalide: {montant_str}")
                return None

            if montant < 100 or montant > 50_000_000:
                logger.warning(f"❌ Montant hors limites: {montant}")
                return None

            expense_date = date.today()

            description_match = re.search(
                r':\s*([^0-9(]+?)(?=\s*\d+)',
                text,
                re.IGNORECASE
            )

            if description_match:
                description = description_match.group(1).strip()
                description = re.sub(r'^(à|de|d\'|pour|en)\s+', '', description, flags=re.IGNORECASE)
            else:
                description = "Dépense"

            type_depense_id = 7

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
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _extract_payment_mode(self, text: str) -> str:
        text_lower = text.lower()

        paren_match = re.search(r'\((.*?)\)', text)
        if paren_match:
            payment_text = paren_match.group(1).lower()
        else:
            payment_text = text_lower

        if 'espèce' in payment_text or 'cash' in payment_text:
            return 'Espèces'
        elif 'dépôt' in payment_text or 'depot' in payment_text:
            return 'Dépôt'
        elif 'chèque' in payment_text or 'cheque' in payment_text:
            return 'Chèque'
        elif 'virement' in payment_text or 'bancaire' in payment_text:
            return 'Virement bancaire'
        elif 'mobile' in payment_text or 'orange' in payment_text or 'moov' in payment_text:
            return 'Mobile Money'
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

        msg_type = self.classify_message(text)

        if msg_type == 'expense':
            expense_data = self.extract_expense_data(text)

            if expense_data:
                self.stats['routed_to_expenses'] += 1
                return ('expense', None, expense_data)
            else:
                logger.warning("⚠️ Format dépense mais extraction échouée → ignoré")
                self.stats['ignored'] += 1
                return ('ignore', None, None)

        elif msg_type == 'price':
            self.stats['routed_to_gemini'] += 1
            return ('gemini', cleaned, None)

        else:
            self.stats['routed_to_gemini'] += 1
            return ('gemini', cleaned, None)

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


message_cleaner_and_redirection = MessageCleanerAndRedirection()