"""
Module de parsing des fichiers WhatsApp exportés avec gestion encodage
"""

import pandas as pd
import re
from datetime import datetime
import chardet

def detecter_encodage_fichier(file_path):
    """Détecte l'encodage du fichier"""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result.get('encoding', 'utf-8')
    confidence = result.get('confidence', 0)
    print(f"Encodage détecté: {encoding} (confiance: {confidence:.2f})")
    return encoding

def parse_whatsapp_txt(file_path):
    """
    Lit un fichier texte exporté de WhatsApp et retourne un DataFrame standardisé
    colonnes: message_id, date, sender, message
    Gère automatiquement l'encodage UTF-8
    """
    messages = []
    
    # Détection automatique de l'encodage
    encoding = detecter_encodage_fichier(file_path)
    
    # Essayer plusieurs encodages
    encodings = [encoding, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    lines = None
    
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            print(f"✓ Fichier lu avec encodage: {enc}")
            break
        except (UnicodeDecodeError, FileNotFoundError) as e:
            print(f"❌ Échec avec {enc}: {e}")
            continue
    
    if lines is None:
        print(f"❌ Impossible de lire {file_path} avec aucun encodage")
        return pd.DataFrame(columns=['message_id','date','sender','message'])
    
    # Pattern amélioré pour WhatsApp
    pattern = r"(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[-\u2013]\s*(.*?):\s*(.*)"
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
            
            # Gestion des dates
            try:
                # Essayer différents formats de date
                for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%y %H:%M:%S"]:
                    try:
                        date = datetime.strptime(f"{date_str} {time_str}", fmt)
                        break
                    except ValueError:
                        continue
                else:
                    date = pd.NaT
            except Exception:
                date = pd.NaT
            
            messages.append({
                'message_id': msg_id,
                'date': date,
                'sender': sender,
                'message': message
            })
            msg_id += 1
        else:
            if messages and not re.match(pattern, line):
                messages[-1]['message'] += " " + line
    
    df = pd.DataFrame(messages)
    
    if df.empty:
        print("Aucun message parse verife format")
        return df
    
    # Sauvegarder 
    df.to_csv('messages_nettoyes.csv', index=False, encoding='utf-8-sig')
    print(f"messages_nettoyes.csv créé avec {len(df)} messages")
    
    # Statistiques
    print(f"📊 Statistiques du parsing:")
    print(f"   • Période: {df['date'].min()} to {df['date'].max()}")
    print(f"   • Expéditeurs uniques: {df['sender'].nunique()}")
    print(f"   • Messages avec date valide: {df['date'].notna().sum()}")
    
    return df