"""
Module d'aide à la décision basé sur LLM — Élevage porcin Burkina Faso
======================================================================

Ce module calcule les KPI clés de l'élevage (reproduction, croissance,
économie, santé, gestion) à partir de la base de données, puis soumet
ces indicateurs à Gemini pour obtenir une analyse et des recommandations
contextualisées aux réalités du Burkina Faso.

Architecture :
  1. collect_kpis(db)      → collecte les KPI depuis PostgreSQL (données Spring Boot)
  2. build_prompt(kpis)    → construit le prompt structuré pour le LLM
  3. ask_llm(prompt)       → appelle l'API Gemini et retourne la réponse
  4. analyse_kpis(db)      → fonction principale : collecte + LLM + réponse formatée

Stades de référence (DGPA/MRAH Burkina Faso 2021 + ONG Thamani) :
  - Objectif prolificité     : ≥ 8 porcelets nés vivants / portée
  - Objectif portées/truie   : 2 à 2,5 / an
  - GMQ croissance           : 400–600 g/jour (conditions locales)
  - Taux mortalité porcelet  : ≤ 15 % (objectif Burkina Faso)
  - Coût aliment cible       : ≤ 100 FCFA/kg (= 1/6 × 600 FCFA/kg prix vente)
"""

import json
import logging
from typing import Any, Dict, Optional

import google.generativeai as genai
from sqlalchemy import text
from sqlalchemy.orm import Session

from utils.config import settings

logger = logging.getLogger(__name__)


def _safe_query(db: Session, sql: str, params: dict = None):
    """
    Exécute une requête SQL brute de façon sécurisée.
    Effectue un rollback automatique en cas d'erreur pour ne pas
    laisser la session SQLAlchemy dans un état invalide.
    """
    try:
        result = db.execute(text(sql), params or {})
        return result.fetchone()
    except Exception as e:
        logger.warning(f"KPI query failed: {e!r}\nSQL: {sql[:120]}")
        try:
            db.rollback()
        except Exception:
            pass
        return None

# ---------------------------------------------------------------------------
# Configuration Gemini
# ---------------------------------------------------------------------------

genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.0-flash")


# ---------------------------------------------------------------------------
# 1. COLLECTE DES KPI DEPUIS LA BASE DE DONNÉES
# ---------------------------------------------------------------------------

def collect_kpis(db: Session) -> Dict[str, Any]:
    """
    Interroge la base PostgreSQL (schéma Spring Boot) et calcule les KPI
    pour les 12 derniers mois.

    Retourne un dictionnaire structuré par catégorie de KPI.
    Les valeurs None indiquent l'absence de données suffisantes.
    """
    kpis: Dict[str, Any] = {
        "reproduction": {},
        "croissance": {},
        "economie": {},
        "sante": {},
        "gestion": {},
        "meta": {"periode": "12 derniers mois", "source": "Base de données élevage"}
    }

    # -----------------------------------------------------------------------
    # KPI REPRODUCTION
    # -----------------------------------------------------------------------

    row = _safe_query(db, """
        SELECT COUNT(*) FILTER (WHERE date_mise_bas_reelle IS NOT NULL), COUNT(*)
        FROM reproduction
        WHERE date_saillie >= (current_date - INTERVAL '12 months')
    """)
    if row and row[1] and row[1] > 0:
        kpis["reproduction"]["taux_mise_bas_pct"] = round(row[0] / row[1] * 100, 1)
        kpis["reproduction"]["nb_saillies"] = int(row[1])
    else:
        kpis["reproduction"]["taux_mise_bas_pct"] = None
        kpis["reproduction"]["nb_saillies"] = 0

    row = _safe_query(db, """
        SELECT ROUND(AVG(nb_nes_vivants)::numeric, 1), COUNT(*)
        FROM reproduction
        WHERE date_mise_bas_reelle IS NOT NULL
          AND date_mise_bas_reelle >= (current_date - INTERVAL '12 months')
          AND nb_nes_vivants IS NOT NULL
    """)
    kpis["reproduction"]["prolificite_moy"] = float(row[0]) if row and row[0] else None
    kpis["reproduction"]["nb_portees"] = int(row[1]) if row and row[1] else 0

    row = _safe_query(db, """
        SELECT ROUND(AVG(nb_portees)::numeric, 2)
        FROM (
            SELECT truie_id, COUNT(*) AS nb_portees
            FROM reproduction
            WHERE date_mise_bas_reelle IS NOT NULL
              AND date_mise_bas_reelle >= (current_date - INTERVAL '12 months')
            GROUP BY truie_id
        ) sub
    """)
    kpis["reproduction"]["portees_par_truie_an"] = float(row[0]) if row and row[0] else None

    row = _safe_query(db, """
        SELECT
            COUNT(*) FILTER (
                WHERE date_mise_bas_reelle IS NOT NULL
                  AND date_mise_bas_reelle <= date_saillie + INTERVAL '120 days'
            ), COUNT(*)
        FROM reproduction
        WHERE date_saillie >= (current_date - INTERVAL '12 months')
    """)
    if row and row[1] and row[1] > 0:
        kpis["reproduction"]["taux_fertilite_pct"] = round(row[0] / row[1] * 100, 1)
    else:
        kpis["reproduction"]["taux_fertilite_pct"] = None

    row = _safe_query(db, """
        SELECT ROUND(AVG(
            CASE WHEN nb_nes_vivants > 0
            THEN (nb_nes_vivants - COALESCE(nb_sevres, nb_nes_vivants))::float / nb_nes_vivants * 100
            ELSE NULL END
        )::numeric, 1)
        FROM reproduction
        WHERE date_mise_bas_reelle IS NOT NULL
          AND date_mise_bas_reelle >= (current_date - INTERVAL '12 months')
          AND nb_nes_vivants IS NOT NULL
    """)
    kpis["reproduction"]["taux_mortalite_porcelet_pct"] = float(row[0]) if row and row[0] else None

    # -----------------------------------------------------------------------
    # KPI CROISSANCE ET PRODUCTION
    # -----------------------------------------------------------------------

    # DATE - DATE retourne directement un INTEGER (nb jours) en PostgreSQL
    row = _safe_query(db, """
        SELECT ROUND(AVG(
            (poids_final - poids_initial)::numeric
            / NULLIF((date_derniere - date_premiere), 0)
            * 1000
        ), 1)
        FROM (
            SELECT p.animal_id,
                MIN(p.poids)      AS poids_initial,
                MAX(p.poids)      AS poids_final,
                MIN(p.date_pesee) AS date_premiere,
                MAX(p.date_pesee) AS date_derniere
            FROM pesee p
            WHERE p.date_pesee >= (current_date - INTERVAL '12 months')
            GROUP BY p.animal_id
            HAVING COUNT(p.id) >= 2 AND MAX(p.poids) > MIN(p.poids)
        ) sub
    """)
    kpis["croissance"]["gmq_g_jour"] = float(row[0]) if row and row[0] else None

    # DATE - DATE = INTEGER (jours) directement, pas besoin d'EXTRACT
    row = _safe_query(db, """
        SELECT ROUND(AVG((v.date_vente - a.date_naissance)::numeric), 0)
        FROM vente v
        JOIN vente_animal va ON va.vente_id = v.id
        JOIN animal a        ON a.id = va.animal_id
        WHERE v.date_vente >= (current_date - INTERVAL '12 months')
          AND a.date_naissance IS NOT NULL
    """)
    kpis["croissance"]["age_moyen_vente_jours"] = int(row[0]) if row and row[0] else None

    row = _safe_query(db, """
        SELECT ROUND(AVG(va.poids_vente)::numeric, 1)
        FROM vente_animal va
        JOIN vente v ON v.id = va.vente_id
        WHERE v.date_vente >= (current_date - INTERVAL '12 months')
          AND va.poids_vente IS NOT NULL
    """)
    kpis["croissance"]["poids_moyen_vente_kg"] = float(row[0]) if row and row[0] else None

    row = _safe_query(db, """
        SELECT
            COUNT(*) FILTER (WHERE LOWER(es.description) LIKE '%mort%' OR LOWER(es.description) LIKE '%décédé%'),
            COUNT(*)
        FROM animal a
        JOIN etat_sante es ON es.id = a.etat_sante_id
        WHERE a.date_entree >= (current_date - INTERVAL '12 months')
    """)
    if row and row[1] and row[1] > 0:
        kpis["croissance"]["taux_mortalite_pct"] = round(row[0] / row[1] * 100, 1)
    else:
        kpis["croissance"]["taux_mortalite_pct"] = None

    # -----------------------------------------------------------------------
    # KPI ÉCONOMIQUES
    # -----------------------------------------------------------------------

    row = _safe_query(db, """
        SELECT ROUND(AVG(session_total)::numeric, 0)
        FROM (
            SELECT al.id, SUM(ia.quantite_kg * ia.prix_unitaire) AS session_total
            FROM alimentation al
            JOIN ingredient_alimentation ia ON ia.alimentation_id = al.id
            WHERE al.date >= (current_date - INTERVAL '12 months')
            GROUP BY al.id
        ) sub
    """)
    kpis["economie"]["cout_aliment_moyen_fcfa"] = float(row[0]) if row and row[0] else None

    row = _safe_query(db, """
        SELECT ROUND(
            (SUM(ia.quantite_kg * ia.prix_unitaire) / NULLIF(SUM(ia.quantite_kg), 0))::numeric, 1
        )
        FROM ingredient_alimentation ia
        JOIN alimentation al ON al.id = ia.alimentation_id
        WHERE al.date >= (current_date - INTERVAL '12 months')
    """)
    kpis["economie"]["cout_par_kg_aliment_fcfa"] = float(row[0]) if row and row[0] else None

    row = _safe_query(db, """
        SELECT ROUND(SUM(montant_total)::numeric, 0)
        FROM vente
        WHERE date_vente >= (current_date - INTERVAL '12 months')
    """)
    kpis["economie"]["ca_total_fcfa"] = float(row[0]) if row and row[0] else None

    # -----------------------------------------------------------------------
    # KPI SANITAIRES
    # -----------------------------------------------------------------------

    row = _safe_query(db, """
        SELECT
            COUNT(*) FILTER (WHERE LOWER(es.description) LIKE '%malade%' OR LOWER(es.description) LIKE '%convalescence%'),
            COUNT(*)
        FROM animal a
        JOIN etat_sante es ON es.id = a.etat_sante_id
        WHERE COALESCE(a.vendu, false) = false
    """)
    if row and row[1] is not None and int(row[1]) > 0:
        kpis["sante"]["taux_morbidite_pct"] = round(float(row[0]) / int(row[1]) * 100, 1)
        kpis["sante"]["nb_animaux_actifs"] = int(row[1])
    else:
        # Fallback : compter sans jointure etat_sante
        r2 = _safe_query(db, "SELECT COUNT(*) FROM animal WHERE COALESCE(vendu, false) = false")
        kpis["sante"]["nb_animaux_actifs"] = int(r2[0]) if r2 and r2[0] else 0
        kpis["sante"]["taux_morbidite_pct"] = 0.0

    row = _safe_query(db, """
        SELECT
            COUNT(*) FILTER (WHERE LOWER(es.description) LIKE '%réform%' OR LOWER(es.description) LIKE '%reform%'),
            COUNT(*)
        FROM animal a
        JOIN etat_sante es  ON es.id = a.etat_sante_id
        JOIN type_animal ta ON ta.id = a.type_animal_id
        WHERE LOWER(ta.nom) LIKE '%truie%'
          AND a.date_entree >= (current_date - INTERVAL '12 months')
    """)
    if row and row[1] is not None and int(row[1]) > 0:
        kpis["sante"]["taux_reforme_truies_pct"] = round(float(row[0]) / int(row[1]) * 100, 1)
    else:
        kpis["sante"]["taux_reforme_truies_pct"] = None

    # -----------------------------------------------------------------------
    # KPI GESTION ET PRODUCTIVITÉ
    # -----------------------------------------------------------------------

    row = _safe_query(db, """
        SELECT ROUND(SUM(occupes) * 100.0 / NULLIF(SUM(cap_max), 0)::numeric, 1)
        FROM (
            SELECT b.capacite_max AS cap_max, COUNT(a.id) AS occupes
            FROM box b
            LEFT JOIN animal a ON a.box_id = b.id AND COALESCE(a.vendu, false) = false
            WHERE b.capacite_max > 0
            GROUP BY b.id, b.capacite_max
        ) sub
    """)
    kpis["gestion"]["taux_occupation_batiments_pct"] = float(row[0]) if row and row[0] else None

    row = _safe_query(db, """
        SELECT ROUND(
            (SELECT SUM(nb_nes_vivants) FROM reproduction
             WHERE date_mise_bas_reelle >= (current_date - INTERVAL '12 months'))
            * 1.0 / NULLIF(
            (SELECT COUNT(DISTINCT truie_id) FROM reproduction
             WHERE date_mise_bas_reelle >= (current_date - INTERVAL '12 months')), 0
            )::numeric, 1
        )
    """)
    kpis["gestion"]["ppta"] = float(row[0]) if row and row[0] else None

    # ── Durée moyenne du cycle de production (sevrage → vente) ───────────────
    # Approximation : âge à la vente - 28 jours (durée allaitement standard)
    if kpis["croissance"].get("age_moyen_vente_jours"):
        kpis["gestion"]["duree_cycle_jours"] = kpis["croissance"]["age_moyen_vente_jours"]
    else:
        kpis["gestion"]["duree_cycle_jours"] = None

    # -----------------------------------------------------------------------
    # KPI REPRODUCTION COMPLÉMENTAIRES
    # -----------------------------------------------------------------------

    # ── ISSF (Intervalle Sevrage–Saillie Fécondante) ─────────────────────────
    # Calcul : date_saillie_suivante - (date_mise_bas + 28j sevrage)
    # Objectif BF : ≤ 7 jours  — SOURCE: DGPA/MRAH Burkina Faso 2021
    # EXTRACT(epoch)/86400 convertit l'interval en jours numériques
    row = _safe_query(db, """
        SELECT ROUND(AVG(issf_jours)::numeric, 1), COUNT(*)
        FROM (
            SELECT
                EXTRACT(epoch FROM (
                    r2.date_saillie - (r1.date_mise_bas_reelle + INTERVAL '28 days')
                )) / 86400 AS issf_jours
            FROM reproduction r1
            JOIN reproduction r2 ON r2.truie_id = r1.truie_id
                AND r2.date_saillie > r1.date_mise_bas_reelle
                AND r2.date_saillie = (
                    SELECT MIN(r3.date_saillie)
                    FROM reproduction r3
                    WHERE r3.truie_id = r1.truie_id
                      AND r3.date_saillie > r1.date_mise_bas_reelle
                )
            WHERE r1.date_mise_bas_reelle IS NOT NULL
              AND r1.nb_sevres IS NOT NULL
              AND r1.nb_sevres > 0
              AND r1.date_mise_bas_reelle >= (current_date - INTERVAL '18 months')
        ) sub
        WHERE issf_jours BETWEEN 0 AND 180
    """)
    kpis["reproduction"]["issf_moyen_jours"] = float(row[0]) if row and row[0] else None
    kpis["reproduction"]["nb_issf_calcules"] = int(row[1]) if row and row[1] else 0

    # -----------------------------------------------------------------------
    # KPI CROISSANCE COMPLÉMENTAIRES
    # -----------------------------------------------------------------------

    # ── IC (Indice de Consommation) — kg aliment / kg de gain ────────────────
    # IC = total_aliment_kg / total_gain_kg sur les animaux en engraissement
    # Objectif BF : 3 à 4 (conditions locales, alimentation à base de drèche)
    row = _safe_query(db, """
        SELECT
            SUM(alim_kg) AS total_aliment,
            SUM(gain_kg) AS total_gain
        FROM (
            SELECT
                p.animal_id,
                (MAX(p.poids) - MIN(p.poids)) AS gain_kg,
                COALESCE((
                    SELECT SUM(ia.quantite_kg)
                    FROM ingredient_alimentation ia
                    JOIN alimentation al ON al.id = ia.alimentation_id
                    WHERE al.animal_id = p.animal_id
                      AND al.date >= MIN(p.date_pesee)
                      AND al.date <= MAX(p.date_pesee)
                ), 0) AS alim_kg
            FROM pesee p
            WHERE p.date_pesee >= (current_date - INTERVAL '12 months')
            GROUP BY p.animal_id
            HAVING COUNT(p.id) >= 2 AND MAX(p.poids) > MIN(p.poids)
        ) sub
        WHERE gain_kg > 0
    """)
    if row and row[0] and row[1] and float(row[1]) > 0:
        kpis["croissance"]["ic"] = round(float(row[0]) / float(row[1]), 2)
    else:
        kpis["croissance"]["ic"] = None

    # -----------------------------------------------------------------------
    # KPI ÉCONOMIQUES COMPLÉMENTAIRES
    # -----------------------------------------------------------------------

    # ── Coût de production par kg de porc vendu ───────────────────────────────
    # Coût prod/kg = (total charges alimentation + soins) / poids total vendu
    row = _safe_query(db, """
        SELECT
            (SELECT COALESCE(SUM(ia.quantite_kg * ia.prix_unitaire), 0)
             FROM ingredient_alimentation ia
             JOIN alimentation al ON al.id = ia.alimentation_id
             WHERE al.date >= (current_date - INTERVAL '12 months')
            ) +
            (SELECT COALESCE(SUM(s.total_prestation), 0)
             FROM soin_animal s
             WHERE s.date_soin >= (current_date - INTERVAL '12 months')
            ) AS total_charges,
            (SELECT COALESCE(SUM(va.poids_vente), 0)
             FROM vente_animal va
             JOIN vente v ON v.id = va.vente_id
             WHERE v.date_vente >= (current_date - INTERVAL '12 months')
               AND va.poids_vente IS NOT NULL
            ) AS poids_vendu
    """)
    if row and row[0] and row[1] and float(row[1]) > 0:
        kpis["economie"]["cout_production_par_kg"] = round(float(row[0]) / float(row[1]), 1)
    else:
        kpis["economie"]["cout_production_par_kg"] = None

    # ── Marge brute par porc vendu (FCFA) ────────────────────────────────────
    # Marge = CA ventes - (coûts alim + coûts soins) / nb porcs vendus
    row = _safe_query(db, """
        SELECT
            (SELECT COALESCE(SUM(va.montant_total), 0)
             FROM vente_animal va
             JOIN vente v ON v.id = va.vente_id
             WHERE v.date_vente >= (current_date - INTERVAL '12 months')
            ) -
            (SELECT COALESCE(SUM(ia.quantite_kg * ia.prix_unitaire), 0)
             FROM ingredient_alimentation ia
             JOIN alimentation al ON al.id = ia.alimentation_id
             WHERE al.date >= (current_date - INTERVAL '12 months')
            ) -
            (SELECT COALESCE(SUM(s.total_prestation), 0)
             FROM soin_animal s
             WHERE s.date_soin >= (current_date - INTERVAL '12 months')
            ) AS marge_brute_totale,
            (SELECT COUNT(DISTINCT va.animal_id)
             FROM vente_animal va
             JOIN vente v ON v.id = va.vente_id
             WHERE v.date_vente >= (current_date - INTERVAL '12 months')
            ) AS nb_porcs_vendus
    """)
    if row and row[0] is not None and row[1] and int(row[1]) > 0:
        kpis["economie"]["marge_brute_par_porc"] = round(float(row[0]) / int(row[1]), 0)
        kpis["economie"]["nb_porcs_vendus"] = int(row[1])
    else:
        kpis["economie"]["marge_brute_par_porc"] = None
        kpis["economie"]["nb_porcs_vendus"] = 0

    # ── CA par truie par an ───────────────────────────────────────────────────
    row = _safe_query(db, """
        SELECT
            (SELECT COALESCE(SUM(va.montant_total), 0)
             FROM vente_animal va
             JOIN vente v ON v.id = va.vente_id
             WHERE v.date_vente >= (current_date - INTERVAL '12 months')
            ) /
            NULLIF(
                (SELECT COUNT(DISTINCT truie_id)
                 FROM reproduction
                 WHERE date_mise_bas_reelle >= (current_date - INTERVAL '12 months')
                ), 0
            )
    """)
    kpis["economie"]["ca_par_truie_an"] = round(float(row[0]), 0) if row and row[0] else None

    # -----------------------------------------------------------------------
    # KPI SANITAIRES COMPLÉMENTAIRES
    # -----------------------------------------------------------------------

    # ── Consommation médicaments/vaccins (FCFA sur 12 mois) ──────────────────
    row = _safe_query(db, """
        SELECT
            COALESCE(SUM(cout_medicament), 0) AS total_medicaments,
            COUNT(*) AS nb_actes,
            COUNT(DISTINCT animal_id) AS nb_animaux_traites
        FROM soin_animal
        WHERE date_soin >= (current_date - INTERVAL '12 months')
    """)
    if row:
        kpis["sante"]["conso_medicaments_fcfa"] = float(row[0]) if row[0] else 0.0
        kpis["sante"]["nb_actes_veterinaires"] = int(row[1]) if row[1] else 0
        kpis["sante"]["nb_animaux_traites"] = int(row[2]) if row[2] else 0
    else:
        kpis["sante"]["conso_medicaments_fcfa"] = None
        kpis["sante"]["nb_actes_veterinaires"] = 0
        kpis["sante"]["nb_animaux_traites"] = 0

    # ── Top 3 animaux par coût de soins ──────────────────────────────────────
    try:
        rows = db.execute(text("""
            SELECT a.code_animal, ta.nom AS type_animal,
                   COUNT(s.id) AS nb_visites,
                   COALESCE(SUM(s.total_prestation), 0) AS cout_total
            FROM soin_animal s
            JOIN animal a      ON a.id = s.animal_id
            JOIN type_animal ta ON ta.id = a.type_animal_id
            WHERE s.date_soin >= (current_date - INTERVAL '12 months')
              AND s.animal_id IS NOT NULL
            GROUP BY a.id, a.code_animal, ta.nom
            ORDER BY cout_total DESC
            LIMIT 3
        """)).fetchall()
        db.rollback()
        kpis["sante"]["top_consommateurs_soins"] = [
            {"code": r[0], "type": r[1], "nb_visites": int(r[2]), "cout_total": float(r[3])}
            for r in rows
        ] if rows else []
    except Exception as e:
        logger.warning(f"top_consommateurs failed: {e!r}")
        try: db.rollback()
        except: pass
        kpis["sante"]["top_consommateurs_soins"] = []

    return kpis


# ---------------------------------------------------------------------------
# 2. CONSTRUCTION DU PROMPT
# ---------------------------------------------------------------------------

def build_prompt(kpis: Dict[str, Any], question_utilisateur: Optional[str] = None) -> str:
    """
    Construit le prompt envoyé au LLM avec les KPI calculés et
    le contexte spécifique à l'élevage porcin au Burkina Faso.
    """

    def fmt(val, unit="", na="Non disponible"):
        if val is None:
            return na
        return f"{val} {unit}".strip()

    repro = kpis.get("reproduction", {})
    croit = kpis.get("croissance", {})
    eco   = kpis.get("economie", {})
    sante = kpis.get("sante", {})
    geste = kpis.get("gestion", {})

    top_soins = sante.get("top_consommateurs_soins", [])
    top_soins_txt = "\n".join(
        f"  {i+1}. {a['code']} ({a['type']}) — {a['nb_visites']} visites — {int(a['cout_total'])} FCFA"
        for i, a in enumerate(top_soins)
    ) if top_soins else "  Aucune donnée"

    prompt = f"""Tu es un conseiller expert en élevage porcin au Burkina Faso, spécialisé dans les exploitations
de la région de Bobo-Dioulasso. Tu maîtrises les fiches techniques DGPA/MRAH (Juin 2021) et les recommandations
terrain de l'ONG Thamani (secteur 24, Bobo-Dioulasso).

Voici les indicateurs de performance (KPI) de l'élevage sur les 12 derniers mois :

═══════════════════════════════════════════════
📊 KPI DE REPRODUCTION
═══════════════════════════════════════════════
• Taux de mise bas              : {fmt(repro.get('taux_mise_bas_pct'), '%')}
• Prolificité (nés vivants/portée) : {fmt(repro.get('prolificite_moy'), 'porcelets')}
• Portées par truie/an          : {fmt(repro.get('portees_par_truie_an'))}
• ISSF (Intervalle sevrage–saillie) : {fmt(repro.get('issf_moyen_jours'), 'jours')}
• Taux de fertilité             : {fmt(repro.get('taux_fertilite_pct'), '%')}
• Mortalité porcelets sous mère : {fmt(repro.get('taux_mortalite_porcelet_pct'), '%')}

Références DGPA/MRAH Burkina Faso :
  → Prolificité cible : ≥ 8 porcelets / portée | ISSF cible : ≤ 7 jours
  → Portées cible : 2 à 2,5 / truie / an | Mortalité porcelet : ≤ 15 %

═══════════════════════════════════════════════
🐷 KPI DE CROISSANCE ET PRODUCTION
═══════════════════════════════════════════════
• GMQ (Gain Moyen Quotidien)    : {fmt(croit.get('gmq_g_jour'), 'g/jour')}
• Indice de consommation (IC)   : {fmt(croit.get('ic'), 'kg aliment / kg gain')}
• Âge moyen à la vente          : {fmt(croit.get('age_moyen_vente_jours'), 'jours')}
• Poids moyen à la vente        : {fmt(croit.get('poids_moyen_vente_kg'), 'kg')}
• Taux de mortalité global      : {fmt(croit.get('taux_mortalite_pct'), '%')}

Références Burkina Faso :
  → GMQ : 400–600 g/jour | IC optimal : 3 à 4 | Poids abattage : 80–100 kg

═══════════════════════════════════════════════
💰 KPI ÉCONOMIQUES
═══════════════════════════════════════════════
• Coût moyen/kg d'aliment       : {fmt(eco.get('cout_par_kg_aliment_fcfa'), 'FCFA/kg')}
• Coût de production/kg         : {fmt(eco.get('cout_production_par_kg'), 'FCFA/kg')}
• Marge brute par porc          : {fmt(eco.get('marge_brute_par_porc'), 'FCFA')}
• CA total (12 mois)            : {fmt(eco.get('ca_total_fcfa'), 'FCFA')}
• CA par truie/an               : {fmt(eco.get('ca_par_truie_an'), 'FCFA')}
• Porcs vendus (12 mois)        : {fmt(eco.get('nb_porcs_vendus'))}

Règle ONG Thamani : coût aliment ≤ 100 FCFA/kg | Prix vente : 600 FCFA/kg sur pied

═══════════════════════════════════════════════
🧪 KPI SANITAIRES
═══════════════════════════════════════════════
• Taux de morbidité             : {fmt(sante.get('taux_morbidite_pct'), '%')}
• Consommation médicaments      : {fmt(sante.get('conso_medicaments_fcfa'), 'FCFA')}
• Actes vétérinaires (12 mois)  : {fmt(sante.get('nb_actes_veterinaires'))}
• Animaux traités               : {fmt(sante.get('nb_animaux_traites'))}
• Taux de réforme des truies    : {fmt(sante.get('taux_reforme_truies_pct'), '%')}
• Animaux actifs                : {fmt(sante.get('nb_animaux_actifs'))}

Top consommateurs de soins (12 mois) :
{top_soins_txt}

═══════════════════════════════════════════════
🌾 KPI DE GESTION ET PRODUCTIVITÉ
═══════════════════════════════════════════════
• Taux d'occupation bâtiments   : {fmt(geste.get('taux_occupation_batiments_pct'), '%')}
• PPTA (porcs produits/truie/an): {fmt(geste.get('ppta'))}
• Durée cycle production        : {fmt(geste.get('duree_cycle_jours'), 'jours')}

═══════════════════════════════════════════════
"""

    if question_utilisateur:
        prompt += f"""
QUESTION DE L'ÉLEVEUR :
{question_utilisateur}

Réponds directement à cette question en te basant sur les KPI ci-dessus et ton expertise locale.
"""
    else:
        prompt += """
Analyse ces indicateurs et fournis :

1. **DIAGNOSTIC GLOBAL** : Évaluation synthétique de la performance de l'élevage (3-5 phrases)

2. **POINTS FORTS** : Liste les 2-3 indicateurs les plus satisfaisants avec explication

3. **ALERTES PRIORITAIRES** : Liste les 2-4 indicateurs préoccupants par ordre de priorité,
   avec pour chacun :
   - Le problème constaté vs la référence DGPA/MRAH ou ONG Thamani
   - La cause probable dans le contexte burkinabè (saison sèche, alimentation locale, etc.)
   - L'action corrective concrète recommandée

4. **RECOMMANDATIONS PRATIQUES** (adaptées aux ressources locales Burkina Faso) :
   - Sur l'alimentation (ingrédients disponibles localement : drèche de dolo, son de maïs, etc.)
   - Sur la reproduction
   - Sur la santé animale

5. **PRIORITÉ D'ACTION** : La 1 action la plus urgente à réaliser cette semaine

Réponds en français, de façon claire et pratique, adapté à un éleveur du Burkina Faso.
Évite le jargon inutile. Si des données sont marquées "Non disponible", ignore ces KPI dans l'analyse.
"""

    return prompt


# ---------------------------------------------------------------------------
# 3. APPEL AU LLM (GEMINI)
# ---------------------------------------------------------------------------

def ask_llm(prompt: str) -> str:
    """
    Envoie le prompt à l'API Gemini Flash et retourne la réponse textuelle.

    Utilise gemini-1.5-flash pour un bon équilibre vitesse/qualité.
    Lève une exception si l'API est inaccessible ou retourne une erreur.
    """
    try:
        response = _model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
            raise RuntimeError(
                "Quota Gemini dépassé (limite gratuite atteinte). "
                "Réessayez dans quelques minutes ou demain. "
                "Pour un usage illimité, activez la facturation sur https://aistudio.google.com"
            )
        raise RuntimeError(f"Erreur Gemini : {msg[:200]}")


# ---------------------------------------------------------------------------
# 4. FONCTION PRINCIPALE
# ---------------------------------------------------------------------------

def analyse_kpis(db: Session, question_utilisateur: Optional[str] = None) -> Dict[str, Any]:
    """
    Collecte les KPI, construit le prompt et retourne l'analyse LLM.

    Args:
        db: Session SQLAlchemy (schéma Spring Boot)
        question_utilisateur: Question libre de l'éleveur (optionnel)

    Returns:
        dict avec :
          - kpis       : indicateurs bruts calculés
          - analyse    : réponse textuelle du LLM
          - question   : question posée (si applicable)
          - erreur     : message d'erreur si LLM indisponible
    """
    kpis = collect_kpis(db)
    prompt = build_prompt(kpis, question_utilisateur)

    try:
        analyse = ask_llm(prompt)
        return {
            "kpis": kpis,
            "analyse": analyse,
            "question": question_utilisateur,
            "erreur": None
        }
    except RuntimeError as e:
        return {
            "kpis": kpis,
            "analyse": None,
            "question": question_utilisateur,
            "erreur": str(e)
        }
