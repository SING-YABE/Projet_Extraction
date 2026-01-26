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

    TÂCHE: Extrait TOUS les prix d'animaux ET d'aliments pour bétail de ces messages WhatsApp.

    ⚠️ RÈGLE CRITIQUE DE NORMALISATION ⚠️
    TOUTES les données d'aliments DOIVENT être exprimées en KILOGRAMMES (kg).
    Tu DOIS appliquer les conversions suivantes de manière AUTOMATIQUE et SYSTÉMATIQUE :

    🔄 CONVERSIONS OBLIGATOIRES - UNITÉS DE POIDS:
    - Si "tonne" ou "t" → multiplier par 1000 pour obtenir kg
      Exemple: "maïs 15000 FCFA la tonne" → poids_kg: 1000, prix_par_kg: 15
    - Si "kg" ou "kilo" ou "kilogramme" → garder tel quel
      Exemple: "soja 800 le kg" → poids_kg: 1, prix_par_kg: 800

    🎒 CONVERSIONS OBLIGATOIRES - SACS (selon le type d'aliment):
    Quand tu vois "sac", "sac de", ou juste le prix sans unité précise, applique CES RÈGLES EXACTES :

    RIZ:
    - "sac de riz" → poids_kg: 120
    - "son de sac de riz" OU "son de riz" → poids_kg: 50

    BLÉ:
    - "sac de blé" → poids_kg: 100
    - "sac de son de blé" OU "son de blé" → poids_kg: 25

    MAÏS:
    - "sac de maïs" → poids_kg: 100
    - "son de maïs" OU "son de sac de maïs" OU "sac de son de maïs" → poids_kg: 50

    SOJA:
    - "sac de soja" → poids_kg: 50
    - "tourteau de soja" → poids_kg: 50

    AUTRES ALIMENTS (par défaut):
    - Si aucune correspondance ci-dessus et que "sac" est mentionné → poids_kg: 50 (estimation par défaut)

    ⚡ CALCUL AUTOMATIQUE DU PRIX AU KG:
    Tu DOIS TOUJOURS calculer "prix_par_kg" avec cette formule:
    prix_par_kg = prix ÷ poids_kg

    Exemples d'application:
    - "Son de riz à 4500 le sac" 
      → aliment_type: "son de riz", prix: 4500, poids_kg: 50, prix_par_kg: 90, unite: "kg"

    - "Maïs 15000 FCFA le sac"
      → aliment_type: "maïs", prix: 15000, poids_kg: 100, prix_par_kg: 150, unite: "kg"

    - "Soja 800 le kilo"
      → aliment_type: "soja", prix: 800, poids_kg: 1, prix_par_kg: 800, unite: "kg"

    - "Tourteau 25000 la tonne"
      → aliment_type: "tourteau", prix: 25000, poids_kg: 1000, prix_par_kg: 25, unite: "kg"

    ❌ CAS À IGNORER:
    Si l'unité est ambiguë et ne correspond à AUCUNE règle ci-dessus (ex: "tas", "paquet", "caisse" sans contexte), tu peux mettre:
    - poids_kg: null
    - prix_par_kg: null
    - unite: "inconnu"
    (Ces entrées seront filtrées plus tard)

    RÈGLE DATE IMPORTANTE: Utilise **OBLIGATOIREMENT** la date fournie dans l'en-tête de chaque message (ex: 'Date: 2025-04-10'). Cette date est la date d'envoi du message. Elle doit être au format 'YYYY-MM-DD'. Si aucune date n'est présente dans le message lui-même, utilise la date de l'en-tête.

    CONTEXTE:
    - Marché agricole au Burkina Faso (porcs + aliments pour bétail)
    - Prix en FCFA (Francs CFA)
    - Variations: "f", "fcfa", "franc", "mille", "k" (1k = 1000)
    - Dialecte local: "porco", "goret", "cochon"

    MESSAGES:
    {messages}

    FORMAT JSON STRICT - Liste d'objets:
    [
      {{
        "type": "animal",
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
      }},
      {{
        "type": "aliment",
        "prix": 4500,
        "aliment_type": "son de riz",
        "categorie": "ÉNERGÉTIQUE",
        "unite": "kg",
        "poids_kg": 50,
        "prix_par_kg": 90,
        "quantite": 1,
        "vendeur": "nom",
        "date": "2024-11-20",
        "message_original": "texte",
        "confiance": 85
      }}
    ]

    TYPES D'ALIMENTS PAR CATÉGORIE:

    ÉNERGÉTIQUE (Glucides):
    - Maïs (grain, sac, épis)
    - Mil
    - Sorgho
    - Son de blé
    - Son de maïs
    - Riz
    - Manioc

    PROTÉINE (Protéines):
    - Soja (grain, tourteau)
    - Tourteau de soja
    - Tourteau de coton
    - Tourteau d'arachide
    - Farine de poisson
    - Drêche de brasserie

    MINÉRAUX (Minéraux & Oligo-éléments):
    - Complément minéral
    - Pierre à lécher
    - Sel
    - Phosphate bicalcique
    - Coquille d'huître
    - CMV (Complément Minéral Vitaminé)

    VITAMINES (Vitamines & Concentrés):
    - Concentré
    - Prémix
    - Siatol
    - CMV vitaminé
    - Provende
    - Aliment complet

    RÈGLES IMPORTANTES:
    - type: OBLIGATOIREMENT "animal" ou "aliment"
    - Si type="animal": animal_type obligatoire ("porcelet", "truie", "verrat", "porc")
    - Si type="aliment": 
      * aliment_type et categorie obligatoires
      * poids_kg OBLIGATOIRE (applique les règles de conversion ci-dessus)
      * prix_par_kg OBLIGATOIRE (= prix ÷ poids_kg)
      * unite DOIT TOUJOURS être "kg" (sauf si impossibilité de conversion → "inconnu")
    - categorie: "ÉNERGÉTIQUE", "PROTÉINE", "MINÉRAUX", "VITAMINES"
    - action: "vente", "achat", "prix_info", "recherche"
    - age_mois: ENTIER uniquement (pas de décimales: 6.5 → 7)
    - confiance: 0-100
    - Si aucun prix trouvé: retourne []
    - Retourne UNIQUEMENT du JSON valide, rien d'autre
    - JAMAIS de texte avant ou après le JSON
    - JAMAIS de commentaires dans le JSON"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.last_raw_response = None
        self.last_error = None

    def extract_batch(self, messages: List[str]) -> List[Dict]:
        """Extract prices from batch of messages"""

        self.last_raw_response = None
        self.last_error = None

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
                    logger.info(f"Gemini response from parts (complex response)")
                else:
                    logger.warning("Gemini response has no text content")
                    self.last_error = "Gemini response has no text content"
                    return []

            # LOG COMPLETE GEMINI RESPONSE
            logger.info("="*60)
            logger.info(f"📤 GEMINI RAW RESPONSE (length: {len(text)} chars)")
            logger.info(f"First 500 chars: {text[:500]}")
            if len(text) > 500:
                logger.info(f"Last 200 chars: ...{text[-200:]}")
            logger.info("="*60)
            self.last_raw_response = text

            # SAVE FULL RESPONSE TO DEDICATED FILE
            logger.info("="*80)
            logger.info(f"BATCH RESPONSE - Length: {len(text)} characters")
            logger.info("="*80)
            logger.info("FULL RESPONSE:")
            logger.info(text)
            logger.info("="*80 + "\n")

            # Clean markdown
            original_text = text
            if text.startswith('```json'):
                text = text.replace('```json\n', '').replace('\n```', '')
                logger.info("✂️  Removed ```json markdown wrapper")
            elif text.startswith('```'):
                text = text.replace('```\n', '').replace('\n```', '')
                logger.info("✂️  Removed ``` markdown wrapper")

            # Check if text is empty or not JSON
            text = text.strip()
            if not text:
                logger.warning("⚠️  Gemini returned empty response after cleaning")
                logger.debug(f"Original text was: {original_text[:200]}")
                self.last_error = "Gemini returned empty response after cleaning"
                return []

            if not (text.startswith('[') or text.startswith('{')):
                logger.warning(f"⚠️  Gemini response is not JSON")
                logger.warning(f"Text starts with: {text[:100]}")
                self.last_error = "Gemini response is not JSON"
                return []

            # Parse JSON
            results = json.loads(text)
            logger.info(f"✅ Successfully parsed JSON: {len(results) if isinstance(results, list) else 1} items")
            self.last_error = None

            # Log extracted data summary
            if isinstance(results, list) and results:
                animals = [r.get('animal_type', 'unknown') for r in results if r.get('type') == 'animal']
                aliments = [r.get('aliment_type', 'unknown') for r in results if r.get('type') == 'aliment']
                logger.info(f"📊 Extracted: {len(results)} items")
                logger.info(f"   Animaux: {len(animals)} ({', '.join(set(animals))})")
                logger.info(f"   Aliments: {len(aliments)} ({', '.join(set(aliments))})")

            return results if isinstance(results, list) else []

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            if 'text' in locals():
                logger.error(f"Invalid JSON text: {text[:1000]}")
            self.last_error = f"JSON parsing error: {e}"
            return []
        except Exception as e:
            logger.error(f"❌ Gemini extraction error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.last_error = f"Gemini extraction error: {e}"
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

        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 GEMINI EXTRACTION START")
        logger.info(f"{'='*70}")
        logger.info(f"📊 Total messages: {len(messages)}")
        logger.info(f"📦 Batches: {total_batches} × {batch_size} messages")
        logger.info(f"⏱️  Delay between batches: {delay_seconds}s")
        logger.info(f"{'='*70}\n")

        import time as time_module
        start_time = time_module.time()

        for i in range(0, len(messages), batch_size):
            batch_num = (i // batch_size) + 1
            batch = messages[i:i + batch_size]

            logger.info(f"\n{'─'*70}")
            logger.info(f"📦 BATCH {batch_num}/{total_batches}")
            logger.info(f"   Messages: {len(batch)} (index {i} to {i+len(batch)-1})")
            logger.info(f"{'─'*70}")

            batch_start = time_module.time()
            results = self.extract_batch(batch)
            batch_duration = time_module.time() - batch_start

            logger.info(f"⏱️  Batch duration: {batch_duration:.2f}s")
            logger.info(f"✅ Batch result: {len(results)} items extracted")

            all_extractions.extend(results)

            if i + batch_size < len(messages):
                logger.info(f"⏳ Waiting {delay_seconds}s before next batch...")
                time.sleep(delay_seconds)

        total_duration = time_module.time() - start_time

        logger.info(f"\n{'='*70}")
        logger.info(f"🏁 EXTRACTION COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"✅ Total extracted: {len(all_extractions)} items")
        logger.info(f"⏱️  Total time: {total_duration:.2f}s ({total_duration/60:.2f} min)")
        logger.info(f"📈 Average: {len(all_extractions)/total_batches:.1f} items/batch")
        logger.info(f"⚡ Speed: {len(messages)/total_duration:.1f} messages/second")

        # Breakdown by type
        if all_extractions:
            animals = [e for e in all_extractions if e.get('type') == 'animal']
            aliments = [e for e in all_extractions if e.get('type') == 'aliment']

            logger.info(f"\n📊 Breakdown:")
            logger.info(f"   Animaux: {len(animals)}")
            logger.info(f"   Aliments: {len(aliments)}")

            if animals:
                animal_counts = {}
                for ext in animals:
                    animal = ext.get('animal_type', 'unknown')
                    animal_counts[animal] = animal_counts.get(animal, 0) + 1

                logger.info(f"\n   Détail animaux:")
                for animal, count in sorted(animal_counts.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"      {animal}: {count}")

            if aliments:
                aliment_counts = {}
                for ext in aliments:
                    aliment = ext.get('aliment_type', 'unknown')
                    aliment_counts[aliment] = aliment_counts.get(aliment, 0) + 1

                logger.info(f"\n   Détail aliments:")
                for aliment, count in sorted(aliment_counts.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"      {aliment}: {count}")

        logger.info(f"{'='*70}\n")

        return all_extractions
