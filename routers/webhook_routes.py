"""
Webhook routes for inbound WhatsApp messages.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from models.schemas import WhatsAppWebhookPayload
from services.gemini_extractor import GeminiPriceExtractor
from services.extraction_workflow import process_messages
from utils.config import settings
from utils.logger import logger
from db.database import get_db

router = APIRouter()
extractor = GeminiPriceExtractor(settings.GEMINI_API_KEY)


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


@router.post("/whatsapp")
async def webhook_whatsapp(
    payload: WhatsAppWebhookPayload,
    db: Session = Depends(get_db)
):
    """Receive WhatsApp messages from Zapwize and extract prices."""
    try:
        # 🆕 Logger le payload complet
        import json
        logger.info("="*80)
        logger.info("📦 PAYLOAD BRUT COMPLET")
        logger.info("="*80)
        logger.info(json.dumps(payload.dict(), indent=2, ensure_ascii=False))
        logger.info("="*80)
        steps = []
        if payload.type and payload.type.lower() != "text":
            return {
                "success": True,
                "ignored": True,
                "reason": "non-text message",
                "steps": [{"step": "payload.ignored", "detail": "non-text message"}]
            }

        if not payload.content or not payload.content.strip():
            return {
                "success": True,
                "ignored": True,
                "reason": "empty content",
                "steps": [{"step": "payload.ignored", "detail": "empty content"}]
            }

        logger.info(f"Webhook message received: {payload.id}")
        steps.append({"step": "payload.received", "detail": f"id={payload.id}"})
        if payload.content:
            steps.append({
                "step": "payload.content",
                "detail": f"length={len(payload.content)}"
            })

        message = format_webhook_message(payload)
        # msg formaté pour Gemini
        logger.info("="*80)
        logger.info("MESSAGE FORMATÉ ENVOYÉ À GEMINI")
        logger.info("="*80)
        logger.info(message)
        logger.info("="*80)
        preview = " ".join(message.splitlines())[:160]
        steps.append({
            "step": "payload.formatted",
            "detail": f"preview={preview}"
        })
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

    except Exception as exc:
        logger.error(f"Webhook extraction error: {exc}")
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
