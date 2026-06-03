"""
Routes KPI — Aide à la décision par LLM
========================================

Endpoints pour l'analyse intelligente des KPI de l'élevage porcin.
Utilise Gemini pour générer des recommandations contextualisées Burkina Faso.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from services.kpi_advisor import analyse_kpis, collect_kpis

router = APIRouter()


# ---------------------------------------------------------------------------
# Schémas de requête / réponse
# ---------------------------------------------------------------------------

class QuestionEleveurRequest(BaseModel):
    """Corps de la requête pour poser une question libre à l'IA."""
    question: str


class KpiAnalyseResponse(BaseModel):
    """Réponse de l'analyse LLM avec les KPI bruts."""
    kpis: Dict[str, Any]
    analyse: Optional[str]
    question: Optional[str]
    erreur: Optional[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/kpi/raw", summary="KPI bruts de l'élevage (sans LLM)")
def get_kpis_raw(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retourne uniquement les KPI calculés depuis la base de données,
    sans appel au LLM. Utile pour affichage tableau de bord Angular.
    """
    try:
        return collect_kpis(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/kpi/analyse",
    response_model=KpiAnalyseResponse,
    summary="Analyse LLM complète des KPI (diagnostic + recommandations)"
)
def get_kpi_analyse(db: Session = Depends(get_db)) -> KpiAnalyseResponse:
    """
    Collecte les KPI des 12 derniers mois et demande à Gemini un diagnostic
    complet : points forts, alertes prioritaires, recommandations pratiques
    adaptées aux réalités du Burkina Faso.

    La réponse inclut :
    - Les KPI bruts calculés depuis la base de données
    - L'analyse textuelle générée par le LLM
    """
    try:
        result = analyse_kpis(db)
        return KpiAnalyseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/kpi/question",
    response_model=KpiAnalyseResponse,
    summary="Poser une question libre à l'IA sur les KPI de l'élevage"
)
def poser_question(
    body: QuestionEleveurRequest,
    db: Session = Depends(get_db)
) -> KpiAnalyseResponse:
    """
    Permet à l'éleveur de poser une question libre sur ses données.

    Exemples :
    - "Pourquoi mon taux de prolificité est-il si bas ?"
    - "Que dois-je faire pour améliorer la croissance en saison sèche ?"
    - "Mon coût d'alimentation est-il raisonnable pour Bobo-Dioulasso ?"

    Le LLM reçoit les KPI actuels + la question et répond de façon ciblée.
    """
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="La question ne peut pas être vide.")

    try:
        result = analyse_kpis(db, question_utilisateur=body.question.strip())
        return KpiAnalyseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
