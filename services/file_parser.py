"""
Parse WhatsApp export .txt files
"""
import re
from typing import List
from utils.logger import logger


def parse_whatsapp_file(file_path: str) -> List[str]:
    """
    Parse WhatsApp .txt export
    
    Returns:
        List of message strings (cleaned)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Pattern: "DD/MM/YYYY, HH:MM - Name: Message"
    pattern = r'\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}\s*[-:]\s*'
    
    messages = re.split(pattern, content)
    
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
    
    logger.info(f"Parsed {len(messages)} messages from {file_path}")
    
    return messages


def parse_whatsapp_with_metadata(file_path: str) -> List[dict]:
    """
    Parse with date and sender extraction
    
    Returns:
        List of dicts with {date, sender, message}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Pattern with groups
    pattern = r'(\d{1,2}/\d{1,2}/\d{4}),?\s+(\d{1,2}:\d{2})\s*[-:]\s*([^:]+?):\s*(.+?)(?=\d{1,2}/\d{1,2}/\d{4}|$)'
    
    matches = re.finditer(pattern, content, re.DOTALL)
    
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
    
    logger.info(f"Parsed {len(parsed)} messages with metadata")
    
    return parsed
