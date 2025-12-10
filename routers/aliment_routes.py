"""
Routes pour les prix d'aliments
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from db.database import get_db
from db import crud
from utils.logger import logger

router = APIRouter()


@router.get("/aliments/categories")
async def get_categories():
    """Liste des catégories d'aliments"""
    return {
        "categories": [
            {
                "nom": "ÉNERGÉTIQUE",
                "description": "Sources de glucides (maïs, mil, sorgho, son)",
                "exemples": ["Maïs", "Mil", "Sorgho", "Son de blé", "Son de maïs"]
            },
            {
                "nom": "PROTÉINE",
                "description": "Sources de protéines (soja, tourteaux)",
                "exemples": ["Soja", "Tourteau de soja", "Tourteau de coton", "Farine de poisson"]
            },
            {
                "nom": "MINÉRAUX",
                "description": "Compléments minéraux et oligo-éléments",
                "exemples": ["Complément minéral", "Pierre à lécher", "Sel", "CMV"]
            },
            {
                "nom": "VITAMINES",
                "description": "Concentrés vitaminés et aliments complets",
                "exemples": ["Concentré", "Prémix", "Siatol", "Provende"]
            }
        ]
    }


@router.get("/aliments/categorie/{categorie}")
async def get_aliments_by_categorie(
        categorie: str,
        days: int = Query(7, description="Nombre de jours à considérer"),
        db: Session = Depends(get_db)
):
    """
    Liste des aliments par catégorie avec prix actuels

    Catégories disponibles: ÉNERGÉTIQUE, PROTÉINE, MINÉRAUX, VITAMINES
    """

    # Valider catégorie
    valid_categories = ['ÉNERGÉTIQUE', 'PROTÉINE', 'MINÉRAUX', 'VITAMINES']
    if categorie.upper() not in valid_categories:
        raise HTTPException(400, f"Catégorie invalide. Valeurs possibles: {', '.join(valid_categories)}")

    try:
        # Récupérer aliments de cette catégorie
        aliments = crud.get_aliments_by_categorie(db, categorie.upper(), days=days)

        if not aliments:
            return {
                "categorie": categorie.upper(),
                "periode_jours": days,
                "aliments": []
            }

        # Grouper par aliment_type et calculer statistiques
        aliment_stats = {}
        for aliment in aliments:
            aliment_type = aliment.aliment_type or 'non_specifie'

            if aliment_type not in aliment_stats:
                aliment_stats[aliment_type] = {
                    'prix_list': [],
                    'unite': aliment.unite,
                    'poids_kg': aliment.poids_kg
                }

            aliment_stats[aliment_type]['prix_list'].append(aliment.prix)

        # Calculer moyennes et préparer résultats
        results = []
        for aliment_type, data in aliment_stats.items():
            prix_list = data['prix_list']
            prix_moyen = sum(prix_list) / len(prix_list)
            prix_min = min(prix_list)
            prix_max = max(prix_list)

            results.append({
                'aliment': aliment_type,
                'categorie': categorie.upper(),
                'prix_moyen': int(prix_moyen),
                'prix_min': int(prix_min),
                'prix_max': int(prix_max),
                'nb_prix': len(prix_list),
                'unite': data['unite'],
                'poids_kg': data['poids_kg']
            })

        # Trier par prix moyen
        results.sort(key=lambda x: x['prix_moyen'])

        return {
            'categorie': categorie.upper(),
            'periode_jours': days,
            'total_aliments': len(results),
            'aliments': results
        }

    except Exception as e:
        logger.error(f"Error getting aliments by category: {e}")
        raise HTTPException(500, str(e))


@router.get("/aliments/stats")
async def get_aliment_statistics(db: Session = Depends(get_db)):
    """Statistiques globales sur les aliments"""

    try:
        stats = crud.get_aliment_statistics(db)
        return stats
    except Exception as e:
        logger.error(f"Error getting aliment stats: {e}")
        raise HTTPException(500, str(e))


@router.get("/aliments/recent")
async def get_recent_aliments(
        days: int = Query(7, description="Nombre de jours"),
        categorie: str = Query(None, description="Filtrer par catégorie"),
        db: Session = Depends(get_db)
):
    """Liste des prix d'aliments récents"""

    try:
        if categorie:
            aliments = crud.get_aliments_by_categorie(db, categorie.upper(), days=days)
        else:
            cutoff = datetime.now() - timedelta(days=days)
            from db.database import PrixAliment
            aliments = db.query(PrixAliment).filter(
                PrixAliment.date >= cutoff
            ).all()

        return {
            'periode_jours': days,
            'categorie_filtre': categorie,
            'total': len(aliments),
            'aliments': [
                {
                    'id': a.id,
                    'aliment': a.aliment_type,
                    'categorie': a.categorie,
                    'prix': a.prix,
                    'unite': a.unite,
                    'poids_kg': a.poids_kg,
                    'date': str(a.date),
                    'vendeur': a.vendeur
                }
                for a in aliments
            ]
        }

    except Exception as e:
        logger.error(f"Error getting recent aliments: {e}")
        raise HTTPException(500, str(e))