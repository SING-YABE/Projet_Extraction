"""
Validation des extractions Gemini - version prod
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from utils.logger import logger


# ── Canonique acceptés en base ──────────────────────────────────────────────
VALID_ACTIONS = ['vente', 'achat', 'prix_info', 'recherche']

# Date plancher : pas de message avant le lancement du groupe WhatsApp.
# Ajuste cette valeur si ton groupe existe depuis plus longtemps.
DATE_MIN = date(2023, 1, 1)
DATE_MAX_FUTURE_DAYS = 7   # on accepte jusqu'à J+7 (messages programmés)

# ── Normalisation animal_type ────────────────────────────────────────────────
# Toute valeur non listée ici est mappée vers son canonique.
# On préfère normaliser plutôt que rejeter — chaque entrée a de la valeur.
ANIMAL_TYPE_MAPPING: Dict[str, str] = {
    # --- Canoniques (identité) ---
    "porcelet":             "porcelet",
    "truie":                "truie",
    "verrat":               "verrat",
    "porc":                 "porc",

    # --- Variantes Gemini fréquentes → canonique ---
    "porc reproducteur":    "verrat",      # mâle reproducteur = verrat par défaut
    "truie reproductrice":  "truie",
    "reproducteur":         "verrat",
    "reproductrice":        "truie",
    "porc charcutier":      "porc",
    "porc de boucherie":    "porc",
    "porc engraissé":       "porc",
    "porc vivant":          "porc",
    "porc vif":             "porc",
    "porc gras":            "porc",
    "cochon":               "porc",
    "porco":                "porc",
    "goret":                "porcelet",
    "jeune porc":           "porcelet",
    "jeunes porcs":         "porcelet",
    "jeune porcelet":       "porcelet",
    "porcin":               "porc",
    "porcins":              "porc",
    "porc mâle":            "verrat",
    "porc femelle":         "truie",
    "femelle":              "truie",
    "mâle":                 "verrat",
    "porc sevré":           "porcelet",
    "sevré":                "porcelet",
    "porcelets sevrés":     "porcelet",
    "verrat reproducteur":  "verrat",
}

VALID_ANIMAL_TYPES = set(ANIMAL_TYPE_MAPPING.values())


def _normalize_animal_type(raw: Optional[str]) -> Optional[str]:
    """
    Normalise une valeur animal_type vers le canonique.
    Retourne None si non reconnu (sera loggé et rejeté par le validateur).
    """
    if not raw:
        return None
    key = raw.strip().lower()
    if key in ANIMAL_TYPE_MAPPING:
        canonical = ANIMAL_TYPE_MAPPING[key]
        if canonical != key:
            logger.debug(f"animal_type normalisé: '{raw}' → '{canonical}'")
        return canonical
    return None


def _is_valid_date(date_str: Optional[str]) -> bool:
    """
    Vérifie que la date est dans une plage plausible.
    Rejette les dates hallucinées par Gemini (ex: 2024-01-01 générique).
    """
    if not date_str:
        return False
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = date.today()
        future_limit = date(today.year, today.month, today.day)
        from datetime import timedelta
        future_limit = today + timedelta(days=DATE_MAX_FUTURE_DAYS)
        return DATE_MIN <= d <= future_limit
    except ValueError:
        return False


def validate_extraction(extraction: Dict) -> bool:
    """
    Valide et nettoie une extraction in-place.
    Retourne True si l'extraction est acceptable pour la base.
    """
    # ── Prix ────────────────────────────────────────────────────────────────
    prix = extraction.get('prix')
    if not prix or not isinstance(prix, (int, float)) or prix <= 0 or prix > 10_000_000:
        return False

    # ── Animal type : normalisation avant rejet ──────────────────────────────
    raw_animal = extraction.get('animal_type')
    if raw_animal is not None:
        canonical = _normalize_animal_type(raw_animal)
        if canonical is None:
            logger.warning(f"animal_type non reconnu (rejeté): '{raw_animal}'")
            return False
        extraction['animal_type'] = canonical   # correction in-place

    # ── Action ───────────────────────────────────────────────────────────────
    action = extraction.get('action')
    if action and action not in VALID_ACTIONS:
        extraction['action'] = 'vente'

    # ── Confiance ────────────────────────────────────────────────────────────
    # Seuil abaissé à 20 : on préfère garder avec incertitude que perdre.
    # Les analyses ML filtreront par confiance selon le besoin.
    confiance = extraction.get('confiance', 50)
    if not isinstance(confiance, (int, float)):
        extraction['confiance'] = 50
        confiance = 50
    confiance = max(0, min(100, int(confiance)))
    extraction['confiance'] = confiance
    if confiance < 20:
        return False

    # ── Age ──────────────────────────────────────────────────────────────────
    age = extraction.get('age_mois')
    if age is not None and (not isinstance(age, (int, float)) or age < 0 or age > 120):
        extraction['age_mois'] = None

    # ── Poids ────────────────────────────────────────────────────────────────
    poids = extraction.get('poids_kg')
    if poids is not None and (not isinstance(poids, (int, float)) or poids < 0 or poids > 500):
        extraction['poids_kg'] = None

    # ── Date : détection des dates hallucinées ───────────────────────────────
    # Gemini retourne "2024-01-01" quand il n'a pas de date réelle.
    # On met None pour ces cas — mieux vaut NULL en base qu'une fausse date.
    date_str = extraction.get('date')
    if _is_valid_date(date_str):
        pass   # date OK, on garde
    else:
        if date_str:
            logger.warning(f"Date invalide ou hallucinée ignorée: '{date_str}'")
        extraction['date'] = None   # NULL en base plutôt que fausse date

    return True


def validate_extractions(extractions: List[Dict]) -> List[Dict]:
    """
    Valide et nettoie une liste d'extractions.
    Retourne uniquement les extractions valides (modifiées in-place si besoin).
    """
    valid = []
    rejected = []

    for ext in extractions:
        if validate_extraction(ext):
            valid.append(ext)
        else:
            rejected.append(ext)

    logger.info(f"Validated {len(valid)}/{len(extractions)} extractions")

    if rejected:
        for r in rejected:
            logger.debug(
                f"  ✗ rejeté — animal='{r.get('animal_type')}' "
                f"prix={r.get('prix')} confiance={r.get('confiance')} "
                f"msg='{str(r.get('message_original', ''))[:60]}'"
            )

    return valid


def deduplicate_extractions(extractions: List[Dict]) -> List[Dict]:
    """
    Déduplique sur (prix, animal_type, date).
    Garde la version avec la confiance la plus haute en cas de doublon.
    """
    best: Dict[tuple, Dict] = {}

    for ext in extractions:
        key = (ext['prix'], ext.get('animal_type'), ext.get('date'))
        existing = best.get(key)
        if existing is None or ext.get('confiance', 0) > existing.get('confiance', 0):
            best[key] = ext

    unique = list(best.values())
    logger.info(f"Deduplicated: {len(extractions)} → {len(unique)}")
    return unique