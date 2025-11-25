"""
Service d'extraction avec Gemini AI
"""
import google.generativeai as genai
from typing import List, Dict
import json
import time
from utils.logger import logger


class GeminiPriceExtractor:
    """Extracteur de prix avec Gemini"""
    
    PROMPT_TEMPLATE = """Tu es un expert en analyse de marchés agricoles au Burkina Faso.

TÂCHE: Extrait TOUS les prix d'animaux (porcs/porcelets/truies/verrats) de ces messages WhatsApp.

CONTEXTE:
- Marché porcin au Burkina Faso
- Prix en FCFA (Francs CFA)
- Variations: "f", "fcfa", "franc", "mille", "k" (1k = 1000)
- Dialecte local: "porco", "goret", "cochon"

MESSAGES:
{messages}

FORMAT JSON STRICT - Liste d'objets:
[
  {{
    "prix": 25000,
    "animal_type": "porcelet",
    "age_mois": 3,
    "poids_kg": null,
    "quantite": 1,
    "unite": "tete",
    "action": "vente",
    "negociable": true,
    "etat": "sevre",
    "vendeur": "nom",
    "date": "2024-11-20",
    "message_original": "texte",
    "confiance": 85
  }}
]

RÈGLES IMPORTANTES:
- animal_type: OBLIGATOIREMENT "porcelet", "truie", "verrat", "porc", ou null
- action: "vente", "achat", "prix_info", "recherche"
- age_mois: ENTIER uniquement (pas de décimales: 6.5 → 7)
- poids_kg: peut avoir décimales
- confiance: 0-100
- Si aucun prix trouvé: retourne []
- Retourne UNIQUEMENT du JSON valide, rien d'autre
- JAMAIS de texte avant ou après le JSON
- JAMAIS de commentaires dans le JSON"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def extract_batch(self, messages: List[str]) -> List[Dict]:
        """Extract prices from batch of messages"""

        formatted = "\n\n".join([
            f"Message {i+1}:\n{msg}"
            for i, msg in enumerate(messages[:100])
        ])

        prompt = self.PROMPT_TEMPLATE.format(messages=formatted)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0,
                    'max_output_tokens': 8000,
                }
            )

            # Handle complex responses
            try:
                text = response.text.strip()
            except ValueError:
                # Response is not simple text, extract from parts
                if response.candidates and len(response.candidates) > 0:
                    parts = response.candidates[0].content.parts
                    text = "".join([part.text for part in parts if hasattr(part, 'text')]).strip()
                else:
                    logger.warning("Gemini response has no text content")
                    return []

            # Clean markdown
            if text.startswith('```json'):
                text = text.replace('```json\n', '').replace('\n```', '')
            elif text.startswith('```'):
                text = text.replace('```\n', '').replace('\n```', '')

            # Check if text is empty or not JSON
            text = text.strip()
            if not text:
                logger.warning("Gemini returned empty response")
                return []

            if not (text.startswith('[') or text.startswith('{')):
                logger.warning(f"Gemini response is not JSON: {text[:200]}")
                return []

            results = json.loads(text)
            return results if isinstance(results, list) else []

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            if 'text' in locals():
                logger.debug(f"Invalid JSON: {text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Gemini extraction error: {e}")
            return []

    def extract_from_file(
        self,
        messages: List[str],
        batch_size: int = 100,
        delay_seconds: int = 4
    ) -> List[Dict]:
        """Extract from all messages with batching"""

        all_extractions = []
        total_batches = (len(messages) + batch_size - 1) // batch_size

        logger.info(f"Gemini extraction: {len(messages)} messages, {total_batches} batches")

        for i in range(0, len(messages), batch_size):
            batch_num = (i // batch_size) + 1
            batch = messages[i:i + batch_size]

            logger.info(f"Processing batch {batch_num}/{total_batches}...")

            results = self.extract_batch(batch)
            all_extractions.extend(results)

            if i + batch_size < len(messages):
                time.sleep(delay_seconds)

        logger.info(f"Extracted {len(all_extractions)} prices")

        return all_extractions