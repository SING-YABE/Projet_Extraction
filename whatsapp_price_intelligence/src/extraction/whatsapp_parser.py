"""
Parser robuste pour fichiers WhatsApp exportés
Gère plusieurs formats de date et de structure
"""
import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from ..utils import setup_logger

logger = setup_logger(__name__)


class WhatsAppParser:
    """Parse les exports WhatsApp au format texte"""
    
    # Patterns de messages WhatsApp (plusieurs formats possibles)
    MESSAGE_PATTERNS = [
        # Format: DD/MM/YYYY, HH:MM - Sender: Message
        r"(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2})\s*-\s*(.*?):\s*(.*)",
        # Format: DD/MM/YY, HH:MM - Sender: Message
        r"(\d{1,2}/\d{1,2}/\d{2}),?\s*(\d{1,2}:\d{2})\s*-\s*(.*?):\s*(.*)",
        # Format: [DD/MM/YYYY HH:MM:SS] Sender: Message
        r"\[(\d{1,2}/\d{1,2}/\d{4})\s*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*?):\s*(.*)",
    ]
    
    DATE_FORMATS = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%y %H:%M:%S",
    ]
    
    def __init__(self):
        self.messages: List[Dict] = []
        self.raw_lines: List[str] = []
    
    def parse_file(self, file_path: Path) -> pd.DataFrame:
        """
        Parse un fichier WhatsApp et retourne un DataFrame
        
        Args:
            file_path: Chemin vers le fichier WhatsApp
        
        Returns:
            DataFrame avec colonnes: message_id, date, sender, message
        """
        logger.info(f"Parsing fichier: {file_path}")
        
        # Lire le fichier
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.raw_lines = f.readlines()
        except UnicodeDecodeError:
            # Fallback ISO-8859-1
            logger.warning("UTF-8 failed, trying ISO-8859-1")
            with open(file_path, 'r', encoding='iso-8859-1') as f:
                self.raw_lines = f.readlines()
        
        self.messages = []
        current_message = None
        
        for line in self.raw_lines:
            line = line.strip()
            if not line:
                continue
            
            # Tenter de matcher avec les patterns
            parsed = self._parse_line(line)
            
            if parsed:
                # Nouveau message
                if current_message:
                    self.messages.append(current_message)
                current_message = parsed
            else:
                # Continuation du message précédent
                if current_message:
                    current_message['message'] += ' ' + line
        
        # Ajouter le dernier message
        if current_message:
            self.messages.append(current_message)
        
        # Créer le DataFrame
        df = pd.DataFrame(self.messages)
        
        if len(df) == 0:
            logger.error("Aucun message parsé !")
            return pd.DataFrame(columns=['message_id', 'date', 'sender', 'message'])
        
        # Ajouter les IDs
        df.insert(0, 'message_id', range(len(df)))
        
        # Nettoyer les messages
        df = self._clean_dataframe(df)
        
        logger.info(f"✓ {len(df)} messages parsés avec succès")
        return df
    
    def _parse_line(self, line: str) -> Optional[Dict]:
        """Tente de parser une ligne avec tous les patterns"""
        for pattern in self.MESSAGE_PATTERNS:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                date_str = groups[0]
                time_str = groups[1]
                sender = groups[2].strip()
                message = groups[3].strip()
                
                # Parser la date
                date_obj = self._parse_date(date_str, time_str)
                
                if date_obj:
                    return {
                        'date': date_obj,
                        'sender': sender,
                        'message': message
                    }
        
        return None
    
    def _parse_date(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse une date avec plusieurs formats possibles"""
        for date_format in self.DATE_FORMATS:
            try:
                return datetime.strptime(f"{date_str} {time_str}", date_format)
            except ValueError:
                continue
        
        logger.warning(f"Impossible de parser la date: {date_str} {time_str}")
        return None
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Nettoie le DataFrame"""
        # Supprimer les messages système
        system_messages = [
            'a rejoint ce groupe',
            'a quitté',
            'a changé',
            'Messages et appels',
            'Ce message a été supprimé',
            'a ajouté',
            'Votre code de sécurité'
        ]
        
        for pattern in system_messages:
            df = df[~df['message'].str.contains(pattern, case=False, na=False)]
        
        # Supprimer les messages vides ou trop courts
        df = df[df['message'].str.len() > 5]
        
        # Supprimer les médias omis
        df = df[df['message'] != '<Médias omis>']
        
        # Réinitialiser l'index
        df = df.reset_index(drop=True)
        df['message_id'] = range(len(df))
        
        return df
    
    def save_parsed_data(self, df: pd.DataFrame, output_path: Path) -> None:
        """Sauvegarde les données parsées"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"✓ Données sauvegardées: {output_path}")


def parse_whatsapp_file(input_file: Path, output_file: Optional[Path] = None) -> pd.DataFrame:
    """
    Fonction utilitaire pour parser rapidement un fichier
    
    Args:
        input_file: Fichier WhatsApp à parser
        output_file: Chemin de sauvegarde optionnel
    
    Returns:
        DataFrame parsé
    """
    parser = WhatsAppParser()
    df = parser.parse_file(input_file)
    
    if output_file:
        parser.save_parsed_data(df, output_file)
    
    return df
