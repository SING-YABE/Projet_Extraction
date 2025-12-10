# whatsapp_price_extractor/parser.py
"""
Module de parsing des fichiers WhatsApp exportés
"""

import pandas as pd
import re
from datetime import datetime

def parse_whatsapp_txt(file_path):
    """
    Lit un fichier texte exporté de WhatsApp et retourne un DataFrame standardisé
    colonnes: message_id, date, sender, message
    """
    messages = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        print(f"Fichier {file_path} introuvable")
        return pd.DataFrame(columns=['message_id','date','sender','message'])
    
    pattern = r"(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2})\s*-\s*(.*?):\s*(.*)"
    msg_id = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(pattern, line)
        if match:
            date_str = match.group(1)
            time_str = match.group(2)
            sender = match.group(3).strip()
            message = match.group(4).strip()
            try:
                date = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
            except:
                try:
                    date = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %H:%M")
                except:
                    date = pd.NaT
            messages.append({
                'message_id': msg_id,
                'date': date,
                'sender': sender,
                'message': message
            })
            msg_id += 1
        else:
            # Message multi-ligne: ajouter au prÃ©cÃ©dent
            if messages:
                messages[-1]['message'] += " " + line
    df = pd.DataFrame(messages)
    df.to_csv('messages_nettoyes.csv', index=False)
    print(f"messages_nettoyes.csv créé avec  {len(df)} messages")
    return df