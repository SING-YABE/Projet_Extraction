"""
Routes API pour la gestion des dépenses
"""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.database import get_db, Depense, TypeDepense
from db.crud import create_depense
from models.schemas import ( DepenseCreate, DepenseUpdate, DepenseResponse, TypeDepenseResponse, DepenseSummaryResponse)
from utils.logger import logger

router = APIRouter()


# ==================== ENDPOINTS ====================

@router.post("/", response_model=DepenseResponse, status_code=201)
def create_new_depense(
        depense: DepenseCreate,
        db: Session = Depends(get_db)
):
    """
    Créer une nouvelle dépense.

    **Types de dépenses disponibles :**
    - 1: ANIMAUX
    - 2: ALIMENTS
    - 3: SALAIRES
    - 4: TRANSPORT
    - 5: SANTÉ
    - 6: MATÉRIEL
    - 7: AUTRE

    **Modes de paiement acceptés :**
    - Espèces
    - Dépôt
    - Chèque
    - Virement bancaire
    - Mobile Money
    """
    try:
        logger.info(f"📝 Création dépense: {depense.description} - {depense.montant} FCFA")

        # Vérifier que le type_depense_id existe
        type_depense = db.query(TypeDepense).filter(TypeDepense.id == depense.type_depense_id).first()
        if not type_depense:
            raise HTTPException(
                status_code=400,
                detail=f"Type de dépense {depense.type_depense_id} invalide. Valeurs acceptées : 1-7"
            )

        # Créer la dépense
        depense_data = depense.model_dump()
        db_depense = create_depense(db, depense_data)
        db.commit()
        db.refresh(db_depense)

        logger.info(f"✅ Dépense créée avec ID: {db_depense.id}")

        return db_depense

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur création dépense: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création: {str(e)}")


@router.get("/", response_model=List[DepenseResponse])
def get_depenses(
        skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
        limit: int = Query(100, ge=1, le=1000, description="Nombre maximum d'éléments à retourner"),
        type_depense_id: Optional[int] = Query(None, ge=1, le=7, description="Filtrer par type de dépense"),
        date_debut: Optional[date] = Query(None, description="Date de début (incluse)"),
        date_fin: Optional[date] = Query(None, description="Date de fin (incluse)"),
        mode_paiement: Optional[str] = Query(None, description="Filtrer par mode de paiement"),
        db: Session = Depends(get_db)
):
    """
    Récupérer la liste des dépenses avec filtres optionnels.

    **Exemples de filtres :**
    - `/depenses?type_depense_id=1` : Toutes les dépenses ANIMAUX
    - `/depenses?date_debut=2026-01-01&date_fin=2026-01-31` : Dépenses de janvier
    - `/depenses?mode_paiement=Espèces` : Dépenses en espèces uniquement
    """
    try:
        query = db.query(Depense)

        # Appliquer les filtres
        if type_depense_id:
            query = query.filter(Depense.type_depense_id == type_depense_id)

        if date_debut:
            query = query.filter(Depense.date >= date_debut)

        if date_fin:
            query = query.filter(Depense.date <= date_fin)

        if mode_paiement:
            query = query.filter(Depense.mode_paiement == mode_paiement)

        # Ordre décroissant par date
        query = query.order_by(Depense.date.desc(), Depense.id.desc())

        # Pagination
        depenses = query.offset(skip).limit(limit).all()

        logger.info(f"📊 {len(depenses)} dépenses récupérées")

        return depenses

    except Exception as e:
        logger.error(f"❌ Erreur récupération dépenses: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/{depense_id}", response_model=DepenseResponse)
def get_depense_by_id(
        depense_id: int,
        db: Session = Depends(get_db)
):
    """Récupérer une dépense spécifique par son ID."""
    try:
        depense = db.query(Depense).filter(Depense.id == depense_id).first()

        if not depense:
            raise HTTPException(status_code=404, detail=f"Dépense {depense_id} introuvable")

        return depense

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération dépense {depense_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.put("/{depense_id}", response_model=DepenseResponse)
def update_depense(
        depense_id: int,
        depense_update: DepenseCreate,
        db: Session = Depends(get_db)
):
    """Mettre à jour une dépense existante."""
    try:
        db_depense = db.query(Depense).filter(Depense.id == depense_id).first()

        if not db_depense:
            raise HTTPException(status_code=404, detail=f"Dépense {depense_id} introuvable")

        # Vérifier le type_depense_id
        type_depense = db.query(TypeDepense).filter(TypeDepense.id == depense_update.type_depense_id).first()
        if not type_depense:
            raise HTTPException(
                status_code=400,
                detail=f"Type de dépense {depense_update.type_depense_id} invalide"
            )

        # Mettre à jour
        for key, value in depense_update.model_dump().items():
            setattr(db_depense, key, value)

        db.commit()
        db.refresh(db_depense)

        logger.info(f"✅ Dépense {depense_id} mise à jour")

        return db_depense

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur mise à jour dépense {depense_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")


@router.delete("/{depense_id}", status_code=204)
def delete_depense(
        depense_id: int,
        db: Session = Depends(get_db)
):
    """Supprimer une dépense."""
    try:
        db_depense = db.query(Depense).filter(Depense.id == depense_id).first()

        if not db_depense:
            raise HTTPException(status_code=404, detail=f"Dépense {depense_id} introuvable")

        db.delete(db_depense)
        db.commit()

        logger.info(f"🗑️  Dépense {depense_id} supprimée")

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Erreur suppression dépense {depense_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")


@router.get("/types/list", response_model=List[TypeDepenseResponse])
def get_types_depense(db: Session = Depends(get_db)):
    """Récupérer la liste de tous les types de dépenses disponibles."""
    try:
        types = db.query(TypeDepense).order_by(TypeDepense.id).all()
        return types
    except Exception as e:
        logger.error(f"❌ Erreur récupération types de dépenses: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/stats/summary", response_model=DepenseSummaryResponse)
def get_depenses_summary(
        date_debut: Optional[date] = Query(None, description="Date de début"),
        date_fin: Optional[date] = Query(None, description="Date de fin"),
        db: Session = Depends(get_db)
):
    """
    Obtenir un résumé des dépenses.

    Retourne :
    - Total des dépenses
    - Répartition par catégorie
    - Répartition par mode de paiement
    """
    try:
        query = db.query(Depense)

        if date_debut:
            query = query.filter(Depense.date >= date_debut)
        if date_fin:
            query = query.filter(Depense.date <= date_fin)

        # Total
        total_montant = query.with_entities(func.sum(Depense.montant)).scalar() or 0
        total_count = query.count()

        # Par type
        by_type = db.query(
            TypeDepense.nom,
            func.sum(Depense.montant).label('montant'),
            func.count(Depense.id).label('count')
        ).join(TypeDepense).group_by(TypeDepense.nom)

        if date_debut:
            by_type = by_type.filter(Depense.date >= date_debut)
        if date_fin:
            by_type = by_type.filter(Depense.date <= date_fin)

        by_type_results = by_type.all()

        # Par mode de paiement
        by_payment = query.with_entities(
            Depense.mode_paiement,
            func.sum(Depense.montant).label('montant'),
            func.count(Depense.id).label('count')
        ).group_by(Depense.mode_paiement).all()

        return {
            "total": {
                "montant": float(total_montant),
                "count": total_count
            },
            "par_categorie": [
                {"categorie": nom, "montant": float(montant), "count": count}
                for nom, montant, count in by_type_results
            ],
            "par_mode_paiement": [
                {"mode": mode, "montant": float(montant), "count": count}
                for mode, montant, count in by_payment
            ]
        }

    except Exception as e:
        logger.error(f"❌ Erreur génération résumé: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")