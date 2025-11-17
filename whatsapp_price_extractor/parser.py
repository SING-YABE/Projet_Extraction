"""
Module de parsing des fichiers WhatsApp exportés avec gestion d'encodage
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
    Lit un fichier texte exporté de WhatsApp et retourne un DataFrame standardisé :
    colonnes: message_id, date, sender, message.
    Gère automatiquement l'encodage et filtre les messages système.
    """
    messages = []
    encoding = detecter_encodage_fichier(file_path)

    encodings = [encoding, 'utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    lines = None

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                lines = f.readlines()
            print(f"✅ Fichier lu avec encodage: {enc}")
            break
        except (UnicodeDecodeError, FileNotFoundError) as e:
            print(f"❌ Échec avec {enc}: {e}")
            continue

    if lines is None:
        print(f"⚠️ Impossible de lire {file_path} avec aucun encodage reconnu.")
        return pd.DataFrame(columns=['message_id', 'date', 'sender', 'message'])

    # ✅ Pattern principal WhatsApp
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

            # Filtrer msg system
            message_lower = message.lower()
            motifs_exclus = [
                "votre code de sécurité", "a rejoint", "a quitté", "a créé le groupe",
                "les messages et les appels sont chiffrés", "<médias omis>",
                "message supprimé", "changed the subject", "created this group",
                "joined this group", "left the group", "invitation", "use this link",
                "utilise ce lien", "fichier joint", "file attached"
            ]
            if any(motif in message_lower for motif in motifs_exclus):
                continue

            # 🗓 Gestion des dates avec formats multiples
            try:
                for fmt in [
                    "%d/%m/%Y %H:%M",
                    "%d/%m/%y %H:%M",
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%y %H:%M:%S"
                ]:
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
            # 🔄 Ligne de continuation (message sur plusieurs lignes)
            if messages and not re.match(pattern, line):
                messages[-1]['message'] += " " + line

    # ✅ Conversion en DataFrame
    df = pd.DataFrame(messages)

    if df.empty:
        print("⚠️ Aucun message parsé — vérifie le format du fichier WhatsApp.")
        return df

    # 💾 Sauvegarde CSV
    df.to_csv('messages_nettoyes.csv', index=False, encoding='utf-8-sig')
    print(f"📄 messages_nettoyes.csv créé avec {len(df)} messages valides.")

    # 📊 Statistiques
    print("\n📊 Statistiques du parsing :")
    print(f"   • Période couverte : {df['date'].min()} → {df['date'].max()}")
    print(f"   • Expéditeurs uniques : {df['sender'].nunique()}")
    print(f"   • Messages valides (avec date) : {df['date'].notna().sum()}")

    return df
