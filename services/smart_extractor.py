"""
Extracteur intelligent avec fallback automatique : Ollama → Gemini.

Stratégie :
  1. Essai Ollama (modèle local, gratuit, offline)
  2. Si Ollama échoue ou renvoie des résultats peu fiables → Gemini

Critères de fallback vers Gemini :
  - Ollama non joignable (ConnectionError / Timeout)
  - Ollama retourne une liste vide
  - Confiance moyenne < confidence_threshold

Interface 100% compatible avec GeminiPriceExtractor (drop-in replacement).
"""
from typing import List, Dict, Optional, Callable

from services.ollama_extractor import OllamaPriceExtractor
from services.gemini_extractor import GeminiPriceExtractor
from utils.logger import logger


class SmartPriceExtractor:
    """
    Extracteur avec fallback automatique Ollama → Gemini.

    Attributs publics (identiques à GeminiPriceExtractor) :
        last_raw_response : réponse brute du modèle ayant produit le résultat
        last_error        : description de la dernière erreur (None si OK)
        extraction_source : "ollama" | "gemini" | "none" — pour les logs
    """

    def __init__(
        self,
        gemini_api_key: str,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "mistral:7b",
        confidence_threshold: int = 60,
        ollama_timeout: int = 120,
    ):
        self.ollama = OllamaPriceExtractor(
            base_url=ollama_base_url,
            model=ollama_model,
            confidence_threshold=confidence_threshold,
            timeout=ollama_timeout,
        )

        # Gemini reste disponible même si la clé est vide (fallback dégradé)
        self._gemini_available = bool(gemini_api_key)
        if self._gemini_available:
            self.gemini = GeminiPriceExtractor(api_key=gemini_api_key)
        else:
            self.gemini = None
            logger.warning(
                "⚠️  SmartExtractor: GEMINI_API_KEY absent — "
                "le fallback Gemini est DÉSACTIVÉ."
            )

        # Attributs publics compatibles GeminiPriceExtractor
        self.last_raw_response: Optional[str] = None
        self.last_error: Optional[str] = None
        self.extraction_source: str = "none"

    # ── Extraction d'un batch ─────────────────────────────────────────────────

    def extract_batch(self, messages: List[str]) -> List[Dict]:
        """
        Essaie Ollama, bascule sur Gemini si nécessaire.
        Retourne toujours une liste (vide en cas d'échec total).
        """
        # ── Tentative 1 : Ollama ──────────────────────────────────────────────
        logger.info("🔄 SmartExtractor → essai Ollama...")
        results = self.ollama.extract_batch(messages)

        if results:
            self.last_raw_response = self.ollama.last_raw_response
            self.last_error = None
            self.extraction_source = "ollama"
            logger.info(f"✅ SmartExtractor: {len(results)} items via Ollama")
            return results

        ollama_error = self.ollama.last_error or "Résultat vide"
        logger.warning(f"⚠️  Ollama KO ({ollama_error})")

        # ── Tentative 2 : Gemini (fallback) ──────────────────────────────────
        if not self._gemini_available:
            logger.error("❌ SmartExtractor: Gemini indisponible, aucun résultat.")
            self.last_error = f"Ollama: {ollama_error} | Gemini: clé absente"
            self.extraction_source = "none"
            return []

        logger.info("🔄 SmartExtractor → fallback Gemini...")
        results = self.gemini.extract_batch(messages)

        self.last_raw_response = self.gemini.last_raw_response
        self.extraction_source = "gemini" if results else "none"

        if results:
            logger.info(f"✅ SmartExtractor: {len(results)} items via Gemini (fallback)")
            self.last_error = None
        else:
            gemini_error = self.gemini.last_error or "Résultat vide"
            self.last_error = (
                f"Ollama: {ollama_error} | Gemini: {gemini_error}"
            )
            logger.error(f"❌ SmartExtractor: double échec. {self.last_error}")

        return results

    # ── Extraction par fichier ────────────────────────────────────────────────

    def extract_from_file(
        self,
        messages: List[str],
        batch_size: int = 50,
        delay_seconds: int = 1,
        on_batch_success: Optional[Callable[[List[Dict]], None]] = None,
    ) -> Dict:
        """
        Extraction complète par batches avec fallback par batch.
        Interface identique à GeminiPriceExtractor.extract_from_file().
        Chaque batch est traité indépendamment : un batch peut passer par
        Ollama et le suivant par Gemini si Ollama était surchargé.
        """
        import time as time_module

        total_batches = (len(messages) + batch_size - 1) // batch_size

        logger.info(f"\n{'=' * 70}")
        logger.info(f"🧠 SMART EXTRACTION START (Ollama → Gemini)")
        logger.info(f"{'=' * 70}")
        logger.info(f"📊 Total messages: {len(messages)}")
        logger.info(f"📦 Batches: {total_batches} × {batch_size}")

        start_time = time_module.time()
        totals = {"total_extractions": 0, "total_animals": 0, "total_aliments": 0}

        for i in range(0, len(messages), batch_size):
            batch_num = (i // batch_size) + 1
            batch = messages[i:i + batch_size]

            logger.info(f"\n{'─' * 70}")
            logger.info(f"📦 BATCH {batch_num}/{total_batches}")

            results = self.extract_batch(batch)
            logger.info(f"   Source: {self.extraction_source}")

            if results:
                animals = [r for r in results if r.get("type") == "animal"]
                aliments = [r for r in results if r.get("type") == "aliment"]
                totals["total_extractions"] += len(results)
                totals["total_animals"] += len(animals)
                totals["total_aliments"] += len(aliments)

                if on_batch_success is not None:
                    try:
                        on_batch_success(results)
                        logger.info(f"💾 Batch {batch_num} persisté ({self.extraction_source})")
                    except Exception as e:
                        logger.error(f"❌ Erreur persistence batch {batch_num}: {e}")
            else:
                logger.warning(f"⚠️  Batch {batch_num} — aucun résultat (double échec)")

            if i + batch_size < len(messages) and delay_seconds > 0:
                time_module.sleep(delay_seconds)

        total_duration = time_module.time() - start_time
        logger.info(f"\n{'=' * 70}")
        logger.info(f"🏁 SMART EXTRACTION COMPLETE — {total_duration:.2f}s")
        logger.info(f"✅ Total: {totals['total_extractions']} items")
        logger.info(f"{'=' * 70}\n")

        return totals
