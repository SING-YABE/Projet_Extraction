"""
Outil d'annotation interactif pour créer des données de référence
Permet de valider/corriger les extractions automatiques
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from ..utils import AnimalTypes, ActionTypes, setup_logger

logger = setup_logger(__name__)
console = Console()


class DataAnnotator:
    """Outil d'annotation interactif"""
    
    def __init__(self, data_path: Path, output_path: Optional[Path] = None):
        """
        Args:
            data_path: Chemin vers les données à annoter
            output_path: Chemin de sauvegarde des annotations
        """
        self.data_path = data_path
        self.output_path = output_path or data_path.parent / 'annotated.csv'
        self.df = pd.read_csv(data_path)
        self.annotations = []
        self.current_index = 0
    
    def start_annotation(self, start_from: int = 0, max_annotations: int = 100):
        """
        Lance la session d'annotation
        
        Args:
            start_from: Index de départ
            max_annotations: Nombre max d'annotations
        """
        console.print("\n[bold green]🏷️  Outil d'Annotation de Prix[/bold green]\n")
        console.print(f"📊 Dataset: {len(self.df)} messages")
        console.print(f"🎯 Objectif: {max_annotations} annotations\n")
        
        # Charger annotations existantes si le fichier existe
        if self.output_path.exists():
            existing = pd.read_csv(self.output_path)
            self.annotations = existing.to_dict('records')
            console.print(f"✓ {len(self.annotations)} annotations existantes chargées\n")
        
        self.current_index = start_from
        count = 0
        
        while count < max_annotations and self.current_index < len(self.df):
            row = self.df.iloc[self.current_index]
            
            # Afficher le message
            self._display_message(row)
            
            # Demander annotation
            annotation = self._annotate_message(row)
            
            if annotation:
                self.annotations.append(annotation)
                count += 1
                
                # Sauvegarder régulièrement
                if count % 10 == 0:
                    self._save_annotations()
                    console.print(f"[green]✓ Progression sauvegardée ({count}/{max_annotations})[/green]\n")
            
            self.current_index += 1
            
            # Option de quitter
            if count % 20 == 0 and count > 0:
                if not Confirm.ask("\nContinuer l'annotation ?"):
                    break
        
        # Sauvegarde finale
        self._save_annotations()
        console.print(f"\n[bold green]✅ Annotation terminée: {len(self.annotations)} exemples annotés[/bold green]")
        console.print(f"📁 Sauvegardé dans: {self.output_path}")
    
    def _display_message(self, row: pd.Series):
        """Affiche un message à annoter"""
        table = Table(title=f"Message #{row['message_id']}")
        table.add_column("Champ", style="cyan")
        table.add_column("Valeur", style="white")
        
        table.add_row("Date", str(row.get('date', 'N/A')))
        table.add_row("Sender", str(row.get('sender', 'N/A'))[:30])
        table.add_row("Message", str(row['message'])[:200])
        
        # Afficher extraction auto si disponible
        if 'prix' in row and pd.notna(row['prix']):
            table.add_row("Prix (auto)", f"{int(row['prix'])} FCFA")
            table.add_row("Animal (auto)", str(row.get('animal_type', 'N/A')))
            table.add_row("Action (auto)", str(row.get('action_type', 'N/A')))
        
        console.print(table)
    
    def _annotate_message(self, row: pd.Series) -> Optional[Dict]:
        """Demande l'annotation pour un message"""
        # Demander si le message contient un prix d'animal
        has_animal_price = Confirm.ask("\n📌 Ce message contient-il un prix d'ANIMAL ?")
        
        if not has_animal_price:
            return {
                'message_id': row['message_id'],
                'date': row.get('date'),
                'message': row['message'],
                'has_animal_price': False,
                'skip_reason': 'no_animal_price'
            }
        
        # Extraire le prix
        console.print("\n[yellow]Extraction du prix:[/yellow]")
        prix_str = Prompt.ask("💰 Prix (nombre entier)", default=str(row.get('prix', '')))
        
        try:
            prix = int(prix_str.replace(' ', ''))
        except ValueError:
            console.print("[red]Prix invalide, message ignoré[/red]")
            return None
        
        # Type d'animal
        console.print("\n[yellow]Type d'animal:[/yellow]")
        console.print("1. Porcelet  2. Truie  3. Verrat  4. Porc  5. Non spécifié")
        animal_choice = Prompt.ask("🐷 Choix", choices=['1', '2', '3', '4', '5'], default='5')
        
        animal_map = {
            '1': AnimalTypes.PORCELET,
            '2': AnimalTypes.TRUIE,
            '3': AnimalTypes.VERRAT,
            '4': AnimalTypes.PORC,
            '5': AnimalTypes.NON_SPECIFIE
        }
        animal_type = animal_map[animal_choice]
        
        # Type d'action
        console.print("\n[yellow]Type d'action:[/yellow]")
        console.print("1. Vente  2. Achat  3. Info prix  4. Non spécifié")
        action_choice = Prompt.ask("📋 Choix", choices=['1', '2', '3', '4'], default='1')
        
        action_map = {
            '1': ActionTypes.VENTE,
            '2': ActionTypes.ACHAT,
            '3': ActionTypes.PRIX_INFO,
            '4': ActionTypes.NON_SPECIFIE
        }
        action_type = action_map[action_choice]
        
        # Qualité
        console.print("\n[yellow]Qualité de l'information:[/yellow]")
        qualite = Prompt.ask("⭐ Note", choices=['1', '2', '3', '4', '5'], default='3')
        
        return {
            'message_id': row['message_id'],
            'date': row.get('date'),
            'sender': row.get('sender'),
            'message': row['message'],
            'has_animal_price': True,
            'prix': prix,
            'animal_type': animal_type,
            'action_type': action_type,
            'qualite': int(qualite),
            'annotated': True
        }
    
    def _save_annotations(self):
        """Sauvegarde les annotations"""
        df_annotations = pd.DataFrame(self.annotations)
        df_annotations.to_csv(self.output_path, index=False)
    
    def get_annotation_stats(self) -> Dict:
        """Statistiques sur les annotations"""
        if not self.annotations:
            return {}
        
        df = pd.DataFrame(self.annotations)
        
        stats = {
            'total': len(df),
            'with_animal_price': df['has_animal_price'].sum(),
            'animal_types': df.get('animal_type', pd.Series()).value_counts().to_dict(),
            'action_types': df.get('action_type', pd.Series()).value_counts().to_dict(),
            'avg_quality': df.get('qualite', pd.Series()).mean()
        }
        
        return stats


def quick_annotate(data_path: Path, n_samples: int = 50):
    """
    Fonction rapide pour annoter des données
    
    Args:
        data_path: Chemin vers les données
        n_samples: Nombre d'exemples à annoter
    """
    annotator = DataAnnotator(data_path)
    annotator.start_annotation(max_annotations=n_samples)
    
    stats = annotator.get_annotation_stats()
    console.print("\n📊 Statistiques d'annotation:")
    console.print(stats)
