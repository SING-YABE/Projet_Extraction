"""
Farm advisor service: reads the existing PostgreSQL schema (provided by the Spring Boot backend)
and produces simple alerts for reproduction and box capacity without adding new DB models.

Tous les seuils sont dynamiques — lus depuis Spring Boot (définis par l'éleveur).
Aucune valeur hardcodée.
"""
from typing import List, Dict
from sqlalchemy import text
import requests

SPRING_BOOT_URL = "http://localhost:8080"


def get_parametres() -> dict:
    """
    Récupère les seuils définis par l'éleveur depuis Spring Boot.
    Si l'éleveur n'a pas encore configuré ses paramètres, lève une erreur claire.
    """
    try:
        res = requests.get(f"{SPRING_BOOT_URL}/api/parametres-eleveur", timeout=5)
        if res.status_code == 404:
            raise ValueError("Paramètres non configurés. L'éleveur doit définir ses paramètres dans l'application.")
        if res.status_code in (401, 403):
            raise ValueError("Accès refusé à /api/parametres-eleveur. Vérifiez la configuration Spring Security.")
        if res.status_code == 500:
            raise ValueError("Erreur Spring Boot lors de la lecture des paramètres.")
        res.raise_for_status()
        return res.json()
    except requests.exceptions.ConnectionError:
        raise ValueError("Impossible de contacter Spring Boot (port 8080). Vérifiez que le backend est démarré.")
    except requests.exceptions.Timeout:
        raise ValueError("Spring Boot n'a pas répondu dans le délai imparti (5s).")


def get_reproduction_alerts(db) -> List[Dict]:
    """
    Détecte les problèmes de reproduction.
    Les seuils viennent exclusivement des paramètres définis par l'éleveur.
    """
    # On récupère les paramètres de l'éleveur
    params = get_parametres()
    seuil = params["seuilNesVivants"]       # ex: 5, 7, 8 — défini par l'éleveur
    nb_max = params["nbMisesBasMax"]        # ex: 2, 3   — défini par l'éleveur

    alerts = []

    # Truies dont les performances sont en dessous du seuil de l'éleveur
    sql_truie = text("""
    SELECT r.truie_id, a.code_animal, COUNT(*) AS low_count
    FROM reproduction r
    JOIN animal a ON a.id = r.truie_id
    WHERE r.nb_nes_vivants < :seuil
      AND COALESCE(r.date_mise_bas_reelle, r.date_mise_bas_prevue) >= (current_date - INTERVAL '12 months')
    GROUP BY r.truie_id, a.code_animal
    HAVING COUNT(*) >= :nb_max
    """)

    res = db.execute(sql_truie, {"seuil": seuil, "nb_max": nb_max}).fetchall()
    for row in res:
        truie_id, code_animal, low_count = row
        alerts.append({
            'level': 'critical',
            'title': f"Truie {code_animal} : performances faibles",
            'message': (
                f"La truie {code_animal} a eu {int(low_count)} mises bas "
                f"avec moins de {seuil} porcelets vivants "
                f"au cours des 12 derniers mois. "
                f"Envisager la réforme après sevrage."
            ),
            'entity': {
                'truie_id': truie_id,
                'code_animal': code_animal,
                'count_low_farrowings': int(low_count),
                'seuil_applique': seuil
            }
        })

    # Verrats impliqués dans des mises bas sous le seuil de l'éleveur
    sql_verrat = text("""
    SELECT r.verrat_id, a.code_animal, COUNT(*) AS low_count
    FROM reproduction r
    JOIN animal a ON a.id = r.verrat_id
    WHERE r.nb_nes_vivants < :seuil
      AND COALESCE(r.date_mise_bas_reelle, r.date_mise_bas_prevue) >= (current_date - INTERVAL '12 months')
    GROUP BY r.verrat_id, a.code_animal
    HAVING COUNT(*) >= 1
    """)

    res2 = db.execute(sql_verrat, {"seuil": seuil}).fetchall()
    for row in res2:
        verrat_id, code_animal, low_count = row
        alerts.append({
            'level': 'critical',
            'title': f"Verrat {code_animal} : performance suspecte",
            'message': (
                f"Le verrat {code_animal} a été impliqué dans {int(low_count)} mise(s) bas "
                f"avec moins de {seuil} porcelets vivants "
                f"au cours des 12 derniers mois. "
                f"Envisager la réforme après sevrage."
            ),
            'entity': {
                'verrat_id': verrat_id,
                'code_animal': code_animal,
                'count_low_farrowings': int(low_count),
                'seuil_applique': seuil
            }
        })

    return alerts


def get_box_capacity_alerts(db) -> List[Dict]:
    """
    Calcule l'occupation des boxes.
    Les seuils warning et critique viennent exclusivement des paramètres de l'éleveur.
    """
    # On récupère les paramètres de l'éleveur
    params = get_parametres()
    yellow = params["seuilOccupationBoxWarning"]    # ex: 0.80 — défini par l'éleveur
    red = params["seuilOccupationBoxCritique"]      # ex: 0.90 — défini par l'éleveur

    alerts = []

    sql = text("""
    SELECT b.id AS box_id, b.code, b.capacite_max, COALESCE(COUNT(a.id), 0) AS occupied
    FROM box b
    LEFT JOIN animal a ON a.box_id = b.id AND COALESCE(a.vendu, false) = false
    GROUP BY b.id, b.code, b.capacite_max
    """)

    rows = db.execute(sql).fetchall()
    for row in rows:
        box_id, code, cap_max, occupied = row
        try:
            cap = int(cap_max) if cap_max is not None and cap_max > 0 else None
        except Exception:
            cap = None

        if not cap:
            continue

        pct = occupied / cap

        if pct >= red:
            level = 'critical'
            emoji = '🔴'
        elif pct >= yellow:
            level = 'warning'
            emoji = '🟡'
        else:
            continue

        alerts.append({
            'level': level,
            'title': f"Box {code} proche capacité",
            'message': (
                f"{emoji} Le box {code} est à {int(pct * 100)}% de capacité "
                f"({int(occupied)}/{cap}). "
                f"Attention avant la prochaine mise bas."
            ),
            'entity': {
                'box_id': box_id,
                'code': code,
                'occupied': int(occupied),
                'capacity': cap,
                'percent': round(pct * 100, 1),
                'seuil_warning_applique': yellow,
                'seuil_critique_applique': red
            }
        })

    return alerts


def gather_alerts(db) -> Dict:
    """
    Combine toutes les alertes et retourne un résumé.
    Si les paramètres ne sont pas configurés, retourne une erreur explicite.
    """
    try:
        repro = get_reproduction_alerts(db)
        boxes = get_box_capacity_alerts(db)
        alerts = repro + boxes

        return {
            'alerts': alerts,
            'summary': {
                'total_alerts': len(alerts),
                'by_level': {
                    'critical': sum(1 for a in alerts if a['level'] == 'critical'),
                    'warning': sum(1 for a in alerts if a['level'] == 'warning')
                }
            }
        }
    except ValueError as e:
        # Paramètres non configurés — on retourne l'erreur proprement
        return {
            'alerts': [],
            'summary': {
                'total_alerts': 0,
                'by_level': {'critical': 0, 'warning': 0}
            },
            'error': str(e)
        }