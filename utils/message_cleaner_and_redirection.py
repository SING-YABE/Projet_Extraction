import re
from typing import Tuple, Optional, Dict, Any
from datetime import date
from utils.logger import logger


class MessageCleanerAndRedirection:
    """Router intelligent pour les messages WhatsApp"""

    NOISE_WORDS = [
        'bonjour', 'bonsoir', 'salut', 'hello', 'coucou', 'bsr', 'bjr',
        'merci', 'stp', 's\'il te plaît', 's\'il vous plaît', 'svp',
        'euh', 'hein', 'bon', 'voilà', 'alors', 'donc',
    ]

    # 🆕 Patterns de dépenses plus flexibles
    EXPENSE_PATTERNS = [
        # Format strict original
        r'dépense\s+du\s+\w+\s+\d{1,2}\s+\w+\s+\d{4}',

        # Format flexible (erreurs de transcription)
        r'dépense[s]?\s+de\s+\w+\s+\d{1,2}\s+\w+\s+\d{4}',

        # Détection combinée robuste
        r'(?:dépense|achat)[s]?.*?\d{1,2}\s+\w+\s+\d{4}.*?(?:à|de|pour)\s+\d+\s*(?:franc|f)',
    ]

    PRICE_PATTERNS = [
        # Animaux
        r'\b(porco|porcelet|truie|verrat|porc|cochon)\b',

        # Aliments mentionnés
        r'\b(son\s+de\s+riz|son\s+de\s+blé|son\s+de\s+maïs|maïs|riz|soja|tourteau)\b',

        # Aliments avec contexte (distance augmentée)
        r'\b(maïs|riz|soja|tourteau|son)\b.{0,50}\b\d+',
        r'\d+.{0,50}\b(maïs|riz|soja|tourteau|son)\b',

        # Prix avec "/" (ex: "100000f/tonne")
        r'\d+\s*[fF]\s*/\s*(tonne|sac|kg|kilo)',

        # Prix/vente explicites
        r'\b(disponible|vend|cherch|prix)\s+(à|du|de)\s+\d+',
        r'\d+\s*(fcfa|franc|f|cfa)\s+(le|la|par)',

        # Possession + aliment
        r'j\'ai\s+(?:du|des|un|une)\s+(maïs|riz|soja|porc|tourteau)',

        # Format "bon pour" (aliment pour animaux)
        r'\bbon\s+pour\s+(les\s+)?(volailles|bétails|porcs|poulets)',
    ]

    CONVERSATIONAL_PATTERNS = [
        r'^\s*(tu|vous|comment|ça|ca)\s+(vas|allez|va)',
        r'^\s*(comment|ca|ça)\s+(va|vas)',
        r'^\s*(ok|d\'accord|oui|non|merci|peut-être)\s*[!?\.]*\s*$',
        r'^\s*[!?\.]+\s*$',
    ]

    # Mapping des catégories vers les IDs de TypeDepense
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
        """Nettoie le message en supprimant les mots parasites."""
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
        """Classifie avec priorité: DÉPENSE > CONVERSATIONNEL > PRIX"""
        text_lower = text.lower()

        # 1. Vérifier dépense D'ABORD (priorité haute)
        for pattern in self.EXPENSE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"💰 Format dépense strict détecté")
                return 'expense'

        # 2. Vérifier conversationnel
        for pattern in self.CONVERSATIONAL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"💬 Message conversationnel détecté")
                return 'conversational'

        # 3. Vérifier prix (priorité basse)
        for pattern in self.PRICE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.info(f"📊 Prix/marché détecté")
                return 'price'

        return 'unknown'

    def _determine_category(self, text: str) -> str:
        """
        Détermine la catégorie de la dépense selon les mots-clés.

        Priorité : ANIMAUX > ALIMENTS > SALAIRES > TRANSPORT > SANTÉ > MATÉRIEL > AUTRE
        """
        text_lower = text.lower()

        # ANIMAUX (priorité 1)
        if any(w in text_lower for w in [
            'porc', 'truie', 'porcelet', 'verrat', 'cochon',
            'porco', 'goret', 'animal', 'bétail'
        ]):
            logger.info("   📂 Catégorie détectée: ANIMAUX")
            return 'ANIMAUX'

        # ALIMENTS (priorité 2)
        elif any(w in text_lower for w in [
            'maïs', 'riz', 'son', 'soja', 'aliment', 'tourteau',
            'blé', 'mil', 'sorgho', 'manioc', 'provende',
            'complément', 'minéral', 'vitamine', 'concentré',
            'farine', 'drêche', 'nourriture', 'alimentation'
        ]):
            logger.info("   📂 Catégorie détectée: ALIMENTS")
            return 'ALIMENTS'

        # SALAIRES (priorité 3)
        elif any(w in text_lower for w in [
            'salaire', 'employé', 'personnel', 'paie', 'paye',
            'rémunération', 'salarié', 'travailleur', 'main d\'oeuvre',
            'gardien', 'ouvrier', 'agent'
        ]):
            logger.info("   📂 Catégorie détectée: SALAIRES")
            return 'SALAIRES'

        # TRANSPORT (priorité 4)
        elif any(w in text_lower for w in [
            'transport', 'carburant', 'essence', 'gasoil', 'diesel',
            'taxi', 'moto', 'véhicule', 'voiture', 'camion',
            'livraison', 'déplacement', 'voyage'
        ]):
            logger.info("   📂 Catégorie détectée: TRANSPORT")
            return 'TRANSPORT'

        # SANTÉ (priorité 5)
        elif any(w in text_lower for w in [
            'médicament', 'vaccin', 'vétérinaire', 'santé', 'soin',
            'traitement', 'antibiotique', 'vitamine', 'vermifuge',
            'consultation', 'urgence', 'maladie'
        ]):
            logger.info("   📂 Catégorie détectée: SANTÉ")
            return 'SANTÉ'

        # MATÉRIEL (priorité 6)
        elif any(w in text_lower for w in [
            'outil', 'équipement', 'matériel', 'machine',
            'abreuvoir', 'mangeoire', 'clôture', 'grillage',
            'bâche', 'seau', 'pelle', 'brouette',
            'construction', 'réparation', 'entretien'
        ]):
            logger.info("   📂 Catégorie détectée: MATÉRIEL")
            return 'MATÉRIEL'

        # AUTRE (par défaut)
        else:
            logger.info("   📂 Catégorie détectée: AUTRE")
            return 'AUTRE'

    def extract_expense_data(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extrait les dépenses au format:
        "Dépense du Mercredi 26 Janvier 2026 : achat de porc à 25 000 Francs (en espèce)"
        OU avec erreurs de transcription:
        "dépenses de maigreté 26 janvier 2026 achats de porc à 25000 francs en espèces"
        """
        try:
            # Vérifier qu'au moins un pattern de dépense matche
            has_expense_pattern = False
            for pattern in self.EXPENSE_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    has_expense_pattern = True
                    break

            if not has_expense_pattern:
                return None

            # Extraire montant APRÈS "à", "de", etc.
            amount_match = re.search(
                r'(?:à|de|pour|coût|prix)\s+(\d+[\s\d]*)\s*(?:franc|fcfa|f|cfa)?',
                text,
                re.IGNORECASE
            )

            if not amount_match:
                amount_match = re.search(
                    r':\s*[^0-9]*?(\d+[\s\d]+)\s*(?:franc|fcfa|f|cfa)?',
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
                logger.warning(f"   Message: {text}")
                return None

            expense_date = date.today()

            # Description (entre ":" et le montant)
            description_match = re.search(
                r':\s*([^0-9(]+?)(?=\s*(?:à|de|pour|coût|prix)\s*\d+)',
                text,
                re.IGNORECASE
            )

            if description_match:
                description = description_match.group(1).strip()
                description = re.sub(r'^(à|de|d\'|pour|en)\s+', '', description, flags=re.IGNORECASE)
            else:
                # Fallback pour format sans ":"
                desc_match = re.search(r'achat[s]?\s+(?:de|d\')\s+([^0-9]+)', text, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip()[:100]
                else:
                    desc_fallback = re.search(r':\s*([^0-9]+)', text)
                    if desc_fallback:
                        description = desc_fallback.group(1).strip()[:100]
                    else:
                        description = "Dépense"

            # Déterminer la catégorie automatiquement
            category = self._determine_category(text)
            type_depense_id = self.CATEGORY_TO_TYPE_ID.get(category, 7)

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
            logger.info(f"   💰 Montant: {montant} FCFA")
            logger.info(f"   📝 Description: {description}")
            logger.info(f"   🏷️  Catégorie: {category} (ID: {type_depense_id})")
            logger.info(f"   💳 Paiement: {mode_paiement}")

            return expense_data

        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _extract_payment_mode(self, text: str) -> str:
        """Extrait le mode de paiement"""
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
        elif 'mobile' in payment_text or 'orange' in payment_text or 'moov' in payment_text or 'wave' in payment_text:
            return 'Mobile Money'
        else:
            return 'Espèces'

    def redirection_message(
            self,
            text: str,
            sender: str = "unknown"
    ) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
        """Route le message vers la destination appropriée."""
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

        elif msg_type == 'conversational':
            logger.info("💬 Message conversationnel → ignoré")
            self.stats['ignored'] += 1
            return ('ignore', None, None)

        else:
            logger.warning("❓ Type de message inconnu → ignoré")
            self.stats['ignored'] += 1
            return ('ignore', None, None)

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


# Instance globale
message_cleaner_and_redirection = MessageCleanerAndRedirection()