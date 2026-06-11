"""
Service d'extraction de prix avec un modèle Ollama local.

Interface identique à GeminiPriceExtractor — drop-in compatible.
Utilise l'API REST Ollama (http://localhost:11434).
"""
import json
import requests
from typing import List, Dict, Optional, Callable
import time

from utils.logger import logger


# ─── Réutilisation du helper de récupération JSON tronqué ───────────────────

def _rescue_truncated_json(text: str) -> List[Dict]:
    """
    Tente de récupérer les objets JSON complets d'une réponse tronquée.
    Extrait tous les objets {...} fermés avant la coupure.
    """
    recovered = []
    depth = 0
    start = None

    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start:i + 1]
                try:
                    obj = json.loads(candidate)
                    recovered.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None

    return recovered


# ─── Extracteur Ollama ────────────────────────────────────────────────────────

class OllamaPriceExtractor:
    """
    Extracteur de prix utilisant un modèle Ollama local.

    Attributs publics (identiques à GeminiPriceExtractor) :
        last_raw_response : dernière réponse brute du modèle
        last_error        : description de la dernière erreur (None si OK)
        confidence_threshold : seuil en dessous duquel le résultat
                               est considéré comme peu fiable
    """

    # ── Prompt identique à Gemini pour assurer la cohérence des résultats ──
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

RÈGLE DATE IMPORTANTE: Utilise OBLIGATOIREMENT la date fournie dans l'en-tête de chaque message (ex: 'Date: 2025-04-10'). Cette date est la date d'envoi du message. Elle doit être au format 'YYYY-MM-DD'.

CONTEXTE:
- Marché agricole au Burkina Faso (porcs + aliments pour bétail)
- Prix en FCFA (Francs CFA)
- Variations: "f", "fcfa", "franc", "mille", "k" (1k = 1000)
- Dialecte local: "porco", "goret", "cochon"

MESSAGES:
{messages}

FORMAT JSON STRICT - Liste d'objets, UNIQUEMENT du JSON valide, rien d'autre:
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

RÈGLES:
- type: OBLIGATOIREMENT "animal" ou "aliment"
- Si type="animal": animal_type obligatoire ("porcelet", "truie", "verrat", "porc")
- Si type="aliment": aliment_type, categorie, poids_kg, prix_par_kg obligatoires
- categorie: "ÉNERGÉTIQUE", "PROTÉINE", "MINÉRAUX", "VITAMINES"
- action: "vente", "achat", "prix_info", "recherche"
- age_mois: ENTIER uniquement
- confiance: 0-100
- Si aucun prix trouvé: retourne []
- JAMAIS de texte avant ou après le JSON
- JAMAIS de commentaires dans le JSON"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral:7b",
        confidence_threshold: int = 60,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout

        self.last_raw_response: Optional[str] = None
        self.last_error: Optional[str] = None

    # ── Vérification disponibilité ────────────────────────────────────────────

    def is_available(self) -> bool:
        """Teste si Ollama est joignable ET que le modèle est installé."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code != 200:
                return False
            models = [m.get("name", "") for m in r.json().get("models", [])]
            # Vérification souple : "mistral:7b" matche "mistral:7b-instruct-v0.3-q4_K_M" etc.
            model_base = self.model.split(":")[0]
            return any(model_base in m for m in models)
        except Exception:
            return False

    # ── Prompts séparés système / utilisateur ────────────────────────────────

    SYSTEM_PROMPT = (
        "Tu es un extracteur de données JSON. "
        "Tu réponds UNIQUEMENT avec un tableau JSON valide, sans aucun texte avant ou après. "
        "Pas d'explication, pas de commentaires, pas de markdown. "
        "Si aucun prix n'est trouvé, retourne exactement : []"
    )

    # ── Extraction d'un batch ─────────────────────────────────────────────────

    def extract_batch(self, messages: List[str]) -> List[Dict]:
        """
        Extrait les prix d'un batch de messages via /api/chat + format:json.
        Retourne une liste vide si Ollama est indisponible ou si le résultat
        est peu fiable (confiance moyenne < threshold).
        """
        self.last_raw_response = None
        self.last_error = None

        formatted = "\n\n".join([
            f"Message {i + 1}:\n{msg}"
            for i, msg in enumerate(messages[:100])
        ])
        user_content = self.PROMPT_TEMPLATE.format(messages=formatted)

        # /api/chat avec séparation system/user + format:"json" pour forcer du JSON pur
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            "stream": False,
            "format": "json",       # Force Ollama à produire du JSON valide
            "options": {
                "temperature": 0,
                "num_predict": 8000,
            },
        }

        try:
            logger.info(f"🦙 OLLAMA → {self.model} | {len(messages)} messages")
            response = requests.post(
                f"{self.base_url}/api/chat",   # /chat gère system + user
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            text = response.json().get("message", {}).get("content", "").strip()
            self.last_raw_response = text

            logger.info(f"📥 Ollama raw response ({len(text)} chars): {text[:300]}")

        except requests.exceptions.ConnectionError:
            self.last_error = "Ollama non joignable — vérifier que `ollama serve` est lancé"
            logger.warning(f"⚠️  {self.last_error}")
            return []

        except requests.exceptions.Timeout:
            self.last_error = f"Ollama timeout ({self.timeout}s) — modèle trop lent ou surcharge"
            logger.warning(f"⚠️  {self.last_error}")
            return []

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self.last_error = (
                    f"Modèle '{self.model}' introuvable dans Ollama — "
                    f"exécuter : ollama pull {self.model}"
                )
                logger.error(f"❌ {self.last_error}")
            else:
                self.last_error = f"Ollama HTTP error: {e}"
                logger.error(f"❌ {self.last_error}")
            return []

        except Exception as e:
            self.last_error = f"Ollama request error: {e}"
            logger.error(f"❌ {self.last_error}")
            return []

        # ── Nettoyage markdown ────────────────────────────────────────────────
        if text.startswith("```json"):
            text = text.replace("```json\n", "").replace("```json", "").replace("\n```", "").replace("```", "")
        elif text.startswith("```"):
            text = text.replace("```\n", "").replace("```", "")
        text = text.strip()

        if not text:
            self.last_error = "Ollama returned empty response"
            logger.warning(f"⚠️  {self.last_error}")
            return []

        if not (text.startswith("[") or text.startswith("{")):
            self.last_error = f"Ollama response is not JSON: {text[:100]}"
            logger.warning(f"⚠️  {self.last_error}")
            return []

        # ── Parse JSON ────────────────────────────────────────────────────────
        try:
            results = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  JSON tronqué ({e}) — tentative récupération partielle...")
            results = _rescue_truncated_json(text)
            if results:
                self.last_error = f"JSON tronqué — {len(results)} objets récupérés"
                logger.warning(f"🔧 {self.last_error}")
            else:
                self.last_error = f"JSON invalide: {e}"
                logger.error(f"❌ {self.last_error}")
                return []

        # ── Normalisation : Ollama peut envelopper dans un objet ─────────────
        # Ex: {"animals":[...], "aliments":[...]} ou {"results":[...]} ou {"data":[...]}
        if isinstance(results, dict):
            # Chercher une clé qui contient une liste d'objets avec "type"
            WRAPPER_KEYS = ["results", "data", "items", "prices", "extractions",
                            "animals", "aliments", "prix", "list"]
            flat: List[Dict] = []
            for key in WRAPPER_KEYS:
                val = results.get(key)
                if isinstance(val, list):
                    flat.extend(val)
            # Si pas de clé connue, fusionner toutes les valeurs qui sont des listes
            if not flat:
                for val in results.values():
                    if isinstance(val, list):
                        flat.extend(val)
            results = flat
            if results:
                logger.info(f"🔧 Ollama: réponse enveloppée dans un objet → {len(results)} items extraits")

        if not isinstance(results, list):
            results = []

        if not results:
            self.last_error = "Ollama: aucun résultat extrait"
            logger.info(f"ℹ️  {self.last_error}")
            return []

        # ── Vérification de la confiance moyenne ─────────────────────────────
        # On ne prend en compte que les valeurs numériques non-nulles.
        # Si le modèle n'a pas renseigné "confiance", on ne pénalise pas.
        confidences = [
            r["confiance"]
            for r in results
            if isinstance(r.get("confiance"), (int, float))
        ]
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            if avg_confidence < self.confidence_threshold:
                self.last_error = (
                    f"Confiance Ollama trop faible: {avg_confidence:.0f}% "
                    f"(seuil: {self.confidence_threshold}%)"
                )
                logger.warning(f"⚠️  {self.last_error} → fallback suggéré")
                return []
        else:
            # Aucune valeur de confiance fournie → on accepte le résultat tel quel
            avg_confidence = -1  # sentinel "non renseignée"
            logger.info("ℹ️  Ollama: champ 'confiance' absent — résultat accepté sans filtre")

        animals = [r for r in results if r.get("type") == "animal"]
        aliments = [r for r in results if r.get("type") == "aliment"]
        conf_label = f"{avg_confidence:.0f}%" if avg_confidence >= 0 else "N/A"
        logger.info(
            f"✅ Ollama: {len(results)} items "
            f"(animaux={len(animals)}, aliments={len(aliments)}, "
            f"confiance moy.={conf_label})"
        )
        self.last_error = None
        return results

    # ── Extraction par fichier (batch avec délai) ─────────────────────────────

    def extract_from_file(
        self,
        messages: List[str],
        batch_size: int = 50,          # Ollama : batches plus petits
        delay_seconds: int = 1,        # Ollama local : délai minimal
        on_batch_success: Optional[Callable[[List[Dict]], None]] = None,
    ) -> Dict:
        """
        Extraction complète par batches avec persistence optionnelle.
        Interface identique à GeminiPriceExtractor.extract_from_file().
        """
        total_batches = (len(messages) + batch_size - 1) // batch_size

        logger.info(f"\n{'=' * 70}")
        logger.info(f"🦙 OLLAMA EXTRACTION START — {self.model}")
        logger.info(f"{'=' * 70}")
        logger.info(f"📊 Total messages: {len(messages)}")
        logger.info(f"📦 Batches: {total_batches} × {batch_size} messages")

        start_time = time.time()
        totals = {"total_extractions": 0, "total_animals": 0, "total_aliments": 0}

        for i in range(0, len(messages), batch_size):
            batch_num = (i // batch_size) + 1
            batch = messages[i:i + batch_size]

            logger.info(f"\n{'─' * 70}")
            logger.info(f"📦 BATCH {batch_num}/{total_batches} ({len(batch)} messages)")

            results = self.extract_batch(batch)

            if results:
                animals = [r for r in results if r.get("type") == "animal"]
                aliments = [r for r in results if r.get("type") == "aliment"]
                totals["total_extractions"] += len(results)
                totals["total_animals"] += len(animals)
                totals["total_aliments"] += len(aliments)

                if on_batch_success is not None:
                    try:
                        on_batch_success(results)
                        logger.info(f"💾 Batch {batch_num} persisté")
                    except Exception as e:
                        logger.error(f"❌ Erreur persistence batch {batch_num}: {e}")
            else:
                logger.info(f"⚠️  Batch {batch_num} vide")

            if i + batch_size < len(messages) and delay_seconds > 0:
                time.sleep(delay_seconds)

        total_duration = time.time() - start_time
        logger.info(f"\n{'=' * 70}")
        logger.info(f"🏁 OLLAMA EXTRACTION COMPLETE — {total_duration:.2f}s")
        logger.info(f"✅ Total: {totals['total_extractions']} items")
        logger.info(f"{'=' * 70}\n")

        return totals
