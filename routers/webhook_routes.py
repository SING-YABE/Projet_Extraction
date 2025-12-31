"""
Webhook routes for inbound WhatsApp messages.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.schemas import WhatsAppWebhookPayload
from services.gemini_extractor import GeminiPriceExtractor
from services.extraction_workflow import process_messages
from utils.config import settings
from utils.logger import logger
from db.database import get_db

router = APIRouter()
extractor = GeminiPriceExtractor(settings.GEMINI_API_KEY)


def format_webhook_message(payload: WhatsAppWebhookPayload) -> str:
    """Format inbound payload into a Gemini-friendly message block."""
    date_str = datetime.utcnow().date().isoformat()

    sender_name = (
        payload.from_.pushname
        or payload.from_.number
        or payload.number
        or "unknown"
    )

    lines = [
        f"Date: {date_str}",
        f"Sender: {sender_name}",
        "Chat Type: group" if payload.isgroup else "Chat Type: direct",
    ]

    if payload.isgroup and payload.group and payload.group.name:
        lines.append(f"Group: {payload.group.name}")

    if payload.chatid:
        lines.append(f"Chat ID: {payload.chatid}")

    if payload.content:
        lines.append(f"Message: {payload.content}")

    return "\n".join(lines)


@router.post("/whatsapp")
async def webhook_whatsapp(
    payload: WhatsAppWebhookPayload,
    db: Session = Depends(get_db)
):
    """Receive WhatsApp messages from Zapwize and extract prices."""
    try:
        if payload.type and payload.type.lower() != "text":
            return {
                "success": True,
                "ignored": True,
                "reason": "non-text message"
            }

        if not payload.content or not payload.content.strip():
            return {
                "success": True,
                "ignored": True,
                "reason": "empty content"
            }

        logger.info(f"Webhook message received: {payload.id}")

        message = format_webhook_message(payload)
        results = process_messages([message], db, extractor)

        return {
            "success": True,
            "total_messages": 1,
            "extractions_found": results['extractions_found'],
            "valid_extractions": results['valid_animals'] + results['aliments_found'],
            "saved_to_db": results['saved_animals'] + results['saved_aliments'],
            "details": {
                "animaux": {
                    "extraits": results['animals_found'],
                    "valides": results['valid_animals'],
                    "sauvegardes": results['saved_animals']
                },
                "aliments": {
                    "extraits": results['aliments_found'],
                    "sauvegardes": results['saved_aliments']
                }
            }
        }

    except Exception as exc:
        logger.error(f"Webhook extraction error: {exc}")
        raise HTTPException(500, str(exc))
