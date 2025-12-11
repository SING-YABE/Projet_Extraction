"""
Parse WhatsApp export .txt files
"""
import re
from typing import List
from utils.logger import logger


def parse_whatsapp_file(content: str) -> List[str]:
    """
    Parse WhatsApp .txt export

    Returns:
        List of message strings (cleaned)
    """
    pattern = r'\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}\s*[-:]\s*'

    messages = re.split(pattern, content)  # Utilise directement 'content'

    # Clean
    messages = [m.strip() for m in messages if m.strip()]

    # Filter system messages
    messages = [
        m for m in messages
        if m and not m.startswith('<Média omis>')
           and not 'a quitté' in m.lower()
           and not 'rejoint' in m.lower()
           and len(m) > 5
    ]

    # Mise à jour du log pour retirer 'file_path'
    logger.info(f"Parsed {len(messages)} messages")

    return messages


def parse_whatsapp_with_metadata(content: str) -> List[dict]:  # <=== MODIFICATION ICI
    """
    Parse with date and sender extraction

    Returns:
        List of dicts with {date, sender, message}
    """

    # Pattern with groups
    pattern = r'(\d{1,2}/\d{1,2}/\d{4}),?\s+(\d{1,2}:\d{2})\s*[-:]\s*([^:]+?):\s*(.+?)(?=\d{1,2}/\d{1,2}/\d{4}|$)'

    matches = re.finditer(pattern, content, re.DOTALL)  # Utilise directement 'content'

    parsed = []
    for match in matches:
        date_str, time_str, sender, message = match.groups()

        message = message.strip()
        if message and len(message) > 5:
            parsed.append({
                'date': date_str,
                'time': time_str,
                'sender': sender.strip(),
                'message': message
            })

    # Mise à jour du log
    logger.info(f"Parsed {len(parsed)} messages with metadata")

    return parsed
