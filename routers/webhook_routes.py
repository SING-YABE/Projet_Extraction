"""
Webhook routes for inbound WhatsApp messages.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import whisper
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from db.database import get_db
from models.schemas import WhatsAppWebhookPayload
from services.extraction_workflow import process_messages
from services.gemini_extractor import GeminiPriceExtractor
from utils.config import settings
from utils.logger import logger
from utils.message_cleaner_and_redirection import message_cleaner_and_redirection
from db.crud import create_depense

router = APIRouter()
extractor = GeminiPriceExtractor(settings.GEMINI_API_KEY)

# Créer le dossier audios à la racine du projet
AUDIO_DIR = Path(__file__).parent.parent / "audios"
AUDIO_DIR.mkdir(exist_ok=True)

# Charger le modèle Whisper au démarrage
logger.info("🎤 Chargement du modèle Whisper...")
# whisper_model = whisper.load_model("large-v3")
# whisper_model = whisper.load_model("tiny")
# Rapide mais moins précis {=====} whisper_model = whisper.load_model("tiny") {=====} ~75 MB
# Bon compromis (actuel) {=====} whisper_model = whisper.load_model("base") {=====} ~140 MB
# Meilleure précision {=====} whisper_model = whisper.load_model("small") {=====} ~460 MB {=====}{=====} ou {=====} whisper_model = whisper.load_model("medium")  {=====} ~1.5 GB
logger.info(f"✅ Modèle Whisper chargé")

SAMPLE_PAYLOAD = """{
  "id": "6232CC122DE27100F01B8E2C11CB4CA2",
  "content": "Text message",
  "number": "22656920671",
  "chatid": "22656920671@s.whatsapp.net",
  "type": "text",
  "isgroup": false,
  "istag": false,
  "from": {
    "fromMe": false,
    "id": "22656920671@s.whatsapp.net",
    "number": "22656920671",
    "pushname": "Louis Bertson",
    "countrycode": "226"
  },
  "group": { "id": "", "name": "" },
  "isviewonce": false
}"""


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


def format_webhook_message_from_transcription(
        transcription: str,
        payload: WhatsAppWebhookPayload
) -> str:
    """Format transcription audio en message Gemini-friendly"""
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
        "[MESSAGE AUDIO TRANSCRIT]",
    ]

    if payload.isgroup and payload.group and payload.group.name:
        lines.append(f"Group: {payload.group.name}")

    if payload.chatid:
        lines.append(f"Chat ID: {payload.chatid}")

    lines.append(f"Message: {transcription}")

    return "\n".join(lines)


def is_audio_message(content: Any) -> bool:
    if not content:
        return False

    # Si c'est déjà un dictionnaire (grâce à Pydantic)
    if isinstance(content, dict):
        data = content
    # Si c'est une chaîne JSON
    elif isinstance(content, str):
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return False
    else:
        return False

    return (
        isinstance(data, dict) and
        (
            data.get('ext') in ['ogg', 'mp3', 'wav', 'm4a'] or
            'audio' in str(data.get('type', '')).lower() or
            data.get('custom', {}).get('type') == 'voice'
        )
    )


def extract_audio_url(content: Any) -> str:
    """
    Extrait l'URL depuis le dictionnaire 'content' reçu.
    """
    try:
        # Si c'est déjà un dictionnaire (cas de ton log)
        if isinstance(content, dict):
            url = content.get('url')
        # Si c'est une chaîne JSON
        elif isinstance(content, str):
            data = json.loads(content)
            url = data.get('url') if isinstance(data, dict) else None
        else:
            url = None

        if url:
            logger.info(f"🔗 URL audio extraite avec succès : {url}")
        else:
            logger.warning("⚠️ Impossible de trouver le champ 'url' dans content")

        return url
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'extraction de l'URL : {e}")
        return None


async def download_audio(url: str, filename: str) -> str:
    """
    Télécharge un fichier audio depuis une URL et le sauvegarde.

    Returns:
        Le chemin du fichier sauvegardé
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            filepath = AUDIO_DIR / filename

            with open(filepath, "wb") as f:
                f.write(response.content)

            logger.info(f"✅ Audio sauvegardé: {filepath}")
            return str(filepath)

    except Exception as e:
        logger.error(f"❌ Erreur téléchargement audio: {e}")
        raise


def transcribe_audio(audio_path: str) -> str:
    """
    Transcrit un fichier audio en texte avec Whisper

    Args:
        audio_path: Chemin vers le fichier audio

    Returns:
        Le texte transcrit
    """
    try:
        logger.info(f"🎤 Transcription de {audio_path}...")
        result = whisper_model.transcribe(
            audio_path,
            language="fr",
            task="transcribe",
            fp16=False
        )

        transcription = result["text"].strip()

        logger.info(f"✅ Transcription réussie ({len(transcription)} caractères)")
        logger.info(f"📝 Texte: {transcription[:200]}...")

        return transcription

    except Exception as e:
        logger.error(f"❌ Erreur transcription: {e}")
        raise


@router.post("/whatsapp")
async def webhook_whatsapp(payload: WhatsAppWebhookPayload, db: Session = Depends(get_db)):
    """Receive WhatsApp messages from Zapwize and extract prices."""

    try:
        # Logger le payload complet
        logger.info("=" * 80)
        logger.info("📦 PAYLOAD BRUT COMPLET")
        logger.info("=" * 80)
        logger.info(json.dumps(payload.model_dump(), indent=2, ensure_ascii=False))
        logger.info("=" * 80)

        steps = []

        # 🆕 DÉTECTER SI LE CONTENT EST UN AUDIO (JSON)
        if payload.content and is_audio_message(payload.content):
            logger.info("🎤 Message audio détecté dans content!")
            steps.append({"step": "audio.detected", "detail": "audio JSON in content"})

            # Extraire l'URL depuis le JSON content
            audio_url = extract_audio_url(payload.content)

            if audio_url:
                # Générer un nom de fichier unique
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                sender = payload.from_.number or "unknown"
                filename = f"audio_{sender}_{timestamp}_{payload.id[:8]}.ogg"

                try:
                    # 1. Télécharger l'audio
                    audio_path = await download_audio(audio_url, filename)
                    steps.append({
                        "step": "audio.downloaded",
                        "detail": f"path={audio_path}"
                    })

                    # 2. Transcrire l'audio
                    transcription = transcribe_audio(audio_path)
                    steps.append({
                        "step": "audio.transcribed",
                        "detail": f"length={len(transcription)} chars"
                    })

                    # 3. Formater le message transcrit
                    message_brut = transcription

                    logger.info("=" * 80)
                    logger.info("📝 TRANSCRIPTION BRUTE")
                    logger.info("=" * 80)
                    logger.info(message_brut)
                    logger.info("=" * 80)

                    # 🆕 4. ROUTER LE MESSAGE
                    destination, cleaned_text, expense_data = message_cleaner_and_redirection.redirection_message(
                        text=message_brut,
                        sender=payload.from_.number or "unknown"
                    )

                    if destination == 'expense':
                        logger.info("💰 DÉPENSE DÉTECTÉE → Sauvegarde directe en base")

                        try:
                            create_depense(db, expense_data)
                            db.commit()

                            steps.append({"step": "expense.saved", "detail": f"montant={expense_data['montant']}"})

                            return {
                                "success": True,
                                "type": "expense",
                                "audio_processed": True,
                                "audio_path": audio_path,
                                "transcription": message_brut,
                                "expense_saved": True,
                                "data": expense_data,
                                "steps": steps
                            }
                        except Exception as e:
                            logger.error(f"❌ Erreur sauvegarde dépense: {e}")
                            db.rollback()
                            steps.append({"step": "expense.error", "detail": str(e)})

                            return {
                                "success": False,
                                "error": f"Erreur sauvegarde dépense: {str(e)}",
                                "steps": steps
                            }

                    elif destination == 'gemini':
                        logger.info("📊 PRIX DÉTECTÉ → Extraction Gemini")

                        message = format_webhook_message_from_transcription(cleaned_text, payload)

                        logger.info("=" * 80)
                        logger.info("📝 MESSAGE NETTOYÉ ENVOYÉ À GEMINI")
                        logger.info("=" * 80)
                        logger.info(message)
                        logger.info("=" * 80)

                        results = process_messages([message], db, extractor, steps=steps)

                        if extractor.last_raw_response is not None:
                            steps.append({
                                "step": "gemini.raw_length",
                                "detail": f"chars={len(extractor.last_raw_response)}"
                            })
                        if extractor.last_error:
                            steps.append({
                                "step": "gemini.error",
                                "detail": extractor.last_error[:200]
                            })

                        # 5. Retourner les résultats de l'extraction
                        return {
                            "success": True,
                            "audio_processed": True,
                            "audio_path": audio_path,
                            "transcription": message_brut,
                            "total_messages": 1,
                            "extractions_found": results['extractions_found'],
                            "valid_extractions": results['valid_animals'] + results['aliments_found'],
                            "saved_to_db": results['saved_animals'] + results['saved_aliments'],
                            "steps": steps,
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

                    else:  # ignore
                        logger.warning("⚠️ Message ignoré (trop court ou non pertinent)")
                        return {
                            "success": True,
                            "ignored": True,
                            "reason": "message too short or irrelevant",
                            "transcription": message_brut,
                            "steps": steps
                        }

                except Exception as e:
                    logger.error(f"Erreur traitement audio: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    steps.append({
                        "step": "audio.error",
                        "detail": str(e)
                    })

                    return {
                        "success": False,
                        "error": str(e),
                        "steps": steps
                    }
            else:
                logger.warning("⚠️ Audio détecté mais URL introuvable dans content")
                steps.append({
                    "step": "audio.no_url",
                    "detail": "URL audio non trouvée dans JSON"
                })

                return {
                    "success": True,
                    "ignored": True,
                    "reason": "audio without valid URL",
                    "steps": steps
                }

        # Messages non-texte (images, vidéos, etc.) via le champ 'type'
        if payload.type and payload.type.lower() not in ["text", ""]:
            return {
                "success": True,
                "ignored": True,
                "reason": "non-text message type",
                "steps": [{"step": "payload.ignored", "detail": f"type={payload.type}"}]
            }

        # Messages vides
        if not payload.content:
            return {"success": True, "ignored": True, "reason": "empty content"}

        if isinstance(payload.content, str) and not payload.content.strip():
            return {"success": True, "ignored": True, "reason": "empty text content"}

        # Messages texte normaux
        logger.info(f"Webhook message received: {payload.id}")

        # 🆕 ROUTER LE MESSAGE TEXTE
        destination, cleaned_text, expense_data = message_cleaner_and_redirection.redirection_message(
            text=payload.content,
            sender=payload.from_.number or "unknown"
        )

        if destination == 'expense':
            # 💰 Dépense dans un message texte
            logger.info("💰 DÉPENSE DÉTECTÉE dans texte → Sauvegarde")

            try:
                create_depense(db, expense_data)
                db.commit()

                return {
                    "success": True,
                    "type": "expense",
                    "expense_saved": True,
                    "data": expense_data
                }
            except Exception as e:
                logger.error(f"❌ Erreur sauvegarde dépense: {e}")
                db.rollback()
                return {
                    "success": False,
                    "error": f"Erreur sauvegarde dépense: {str(e)}"
                }

        elif destination == 'gemini':
            # 📊 Prix dans un message texte → Workflow existant
            logger.info("📊 PRIX DÉTECTÉ dans texte → Extraction Gemini")

            steps.append({"step": "payload.received", "detail": f"id={payload.id}"})

            # Créer un payload temporaire avec le texte nettoyé
            payload_temp = payload.model_copy()
            payload_temp.content = cleaned_text

            message = format_webhook_message(payload_temp)

            logger.info("=" * 80)
            logger.info("MESSAGE NETTOYÉ ENVOYÉ À GEMINI")
            logger.info("=" * 80)
            logger.info(message)
            logger.info("=" * 80)

            preview = " ".join(message.splitlines())[:160]
            steps.append({
                "step": "payload.formatted",
                "detail": f"preview={preview}"
            })

            # 🔄 Utiliser le workflow existant
            results = process_messages([message], db, extractor, steps=steps)

            if extractor.last_raw_response is not None:
                steps.append({
                    "step": "gemini.raw_length",
                    "detail": f"chars={len(extractor.last_raw_response)}"
                })
            if extractor.last_error:
                steps.append({
                    "step": "gemini.error",
                    "detail": extractor.last_error[:200]
                })

            return {
                "success": True,
                "total_messages": 1,
                "extractions_found": results['extractions_found'],
                "valid_extractions": results['valid_animals'] + results['aliments_found'],
                "saved_to_db": results['saved_animals'] + results['saved_aliments'],
                "steps": steps,
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

        else:  # ignore
            return {
                "success": True,
                "ignored": True,
                "reason": "message too short or irrelevant"
            }

    except Exception as exc:
        logger.error(f"Webhook extraction error: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, str(exc))


@router.get("/test", response_class=HTMLResponse)
async def webhook_test_ui():
    """Simple UI to post a webhook payload."""
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Webhook Tester</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "Palatino Linotype", "Book Antiqua", Palatino, serif;
        background: linear-gradient(135deg, #f6f0e8 0%, #e6f0f7 50%, #f3f8ef 100%);
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        padding: 32px 20px 48px;
      }}
      .card {{
        max-width: 980px;
        margin: 0 auto;
        background: #ffffff;
        border: 1px solid rgba(15, 23, 42, 0.08);
        border-radius: 16px;
        padding: 28px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
      }}
      h1 {{
        margin: 0 0 16px 0;
        font-size: 24px;
        letter-spacing: 0.2px;
      }}
      textarea {{
        width: 100%;
        min-height: 300px;
        font-family: "Courier New", Courier, monospace;
        font-size: 13px;
        border: 1px solid rgba(15, 23, 42, 0.2);
        border-radius: 10px;
        padding: 14px;
        background: #f8fafc;
        color: #0f172a;
      }}
      button {{
        margin-top: 14px;
        padding: 11px 18px;
        border: 0;
        border-radius: 999px;
        background: #0f172a;
        color: #fff;
        cursor: pointer;
        font-weight: 700;
        letter-spacing: 0.2px;
      }}
      button:disabled {{
        opacity: 0.6;
        cursor: not-allowed;
      }}
      .row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
      }}
      .chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border-radius: 999px;
        background: #eef2ff;
        color: #1e293b;
        font-size: 12px;
        border: 1px solid rgba(15, 23, 42, 0.1);
      }}
      .chip span {{
        font-weight: 700;
      }}
      pre {{
        margin-top: 16px;
        background: #0f172a;
        color: #e2e8f0;
        padding: 14px;
        border-radius: 12px;
        overflow: auto;
        min-height: 160px;
      }}
      .hint {{
        margin: 8px 0 16px 0;
        color: #475569;
        font-size: 13px;
        line-height: 1.4;
      }}
      .footer {{
        margin-top: 12px;
        font-size: 12px;
        color: #64748b;
      }}
      @media (max-width: 640px) {{
        body {{
          padding: 20px 14px 32px;
        }}
        .card {{
          padding: 20px;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="row">
        <h1>WhatsApp Webhook Tester</h1>
        <div class="chip">Target <span>/webhook/whatsapp</span></div>
      </div>
      <div class="hint">Paste a Zapwize payload and send it to the webhook. This page only sends JSON and shows the raw response.</div>
      <textarea id="payload">{SAMPLE_PAYLOAD}</textarea>
      <div class="row">
        <button id="send">Send Webhook</button>
        <button id="copy" type="button">Copy Response</button>
        <div class="chip" id="status">Status <span>idle</span></div>
      </div>
      <pre id="output">Waiting for request...</pre>
      <div class="footer">Tip: keep the payload JSON valid. Parsing errors show here before any request is sent.</div>
    </div>
    <script>
      const button = document.getElementById("send");
      const output = document.getElementById("output");
      const textarea = document.getElementById("payload");
      const copyButton = document.getElementById("copy");
      const status = document.getElementById("status");

      const setStatus = (label, color) => {{
        status.style.background = color;
        status.innerHTML = "Status <span>" + label + "</span>";
      }};

      button.addEventListener("click", async () => {{
        button.disabled = true;
        setStatus("sending", "#fef3c7");
        output.textContent = "Sending...";
        const started = performance.now();
        try {{
          let payload;
          try {{
            payload = JSON.parse(textarea.value);
          }} catch (err) {{
            setStatus("invalid json", "#fee2e2");
            output.textContent = "JSON error: " + err.message;
            return;
          }}
          const response = await fetch("/webhook/whatsapp", {{
            method: "POST",
            headers: {{
              "Content-Type": "application/json"
            }},
            body: JSON.stringify(payload)
          }});
          const elapsed = Math.round(performance.now() - started);
          const text = await response.text();
          let data;
          try {{
            data = JSON.parse(text);
          }} catch (err) {{
            data = {{ raw: text }};
          }}
          setStatus(response.ok ? "ok" : "error", response.ok ? "#dcfce7" : "#fee2e2");
          output.textContent = JSON.stringify({{
            status: response.status,
            statusText: response.statusText,
            elapsedMs: elapsed,
            data
          }}, null, 2);
        }} catch (err) {{
          setStatus("error", "#fee2e2");
          output.textContent = "Error: " + err.message;
        }} finally {{
          button.disabled = false;
        }}
      }});

      copyButton.addEventListener("click", async () => {{
        try {{
          await navigator.clipboard.writeText(output.textContent);
          setStatus("copied", "#e0f2fe");
        }} catch (err) {{
          setStatus("copy failed", "#fee2e2");
        }}
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)