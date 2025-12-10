"""
Point d'entrée principal du projet
Orchestre l'extraction, validation et analyse des données
"""
import argparse
from pathlib import Path
import sys

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.extraction import parse_whatsapp_file, extract_prices_from_dataframe
from src.data_quality.validator import DataValidator
from src.data_quality.annotator import DataAnnotator
from src.utils import setup_logger, PROCESSED_DATA_DIR, RAW_DATA_DIR, ANNOTATED_DATA_DIR
from rich.console import Console
from rich.panel import Panel

logger = setup_logger(__name__)
console = Console()


def print_banner():
    """Affiche la bannière du projet"""
    banner = """
    🐷 WhatsApp Price Intelligence
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Extraction et analyse des prix du marché porcin
    à partir des conversations WhatsApp
    """
    console.print(Panel(banner, style="bold green"))


def extract_pipeline(whatsapp_file: Path):
    """
    Pipeline complet d'extraction
    
    Args:
        whatsapp_file: Fichier WhatsApp à traiter
    """
    console.print("\n[bold cyan]📤 ÉTAPE 1: Parsing WhatsApp[/bold cyan]")
    
    # 1. Parser le fichier WhatsApp
    parsed_file = PROCESSED_DATA_DIR / 'messages_parsed.csv'
    df_messages = parse_whatsapp_file(whatsapp_file, parsed_file)
    
    console.print(f"✓ {len(df_messages)} messages parsés")
    
    # 2. Extraire les prix
    console.print("\n[bold cyan]💰 ÉTAPE 2: Extraction des prix[/bold cyan]")
    df_prices = extract_prices_from_dataframe(df_messages)
    
    prices_file = PROCESSED_DATA_DIR / 'prices_extracted.csv'
    df_prices.to_csv(prices_file, index=False)
    
    console.print(f"✓ {len(df_prices)} prix extraits")
    console.print(f"📁 Sauvegardé: {prices_file}")
    
    # 3. Valider les données
    console.print("\n[bold cyan]✅ ÉTAPE 3: Validation[/bold cyan]")
    validator = DataValidator()
    validation = validator.validate_dataframe(df_prices)
    
    if validation.is_valid:
        console.print("[green]✓ Données valides[/green]")
    else:
        console.print(f"[yellow]⚠ {len(validation.issues)} problèmes détectés[/yellow]")
    
    # Rapport de qualité
    report_file = PROCESSED_DATA_DIR / 'quality_report.json'
    report = validator.generate_quality_report(df_prices, report_file)
    
    console.print(f"\n📊 Score de qualité: {report['quality_score']:.1f}/100")
    console.print(f"📄 Rapport détaillé: {report_file}")
    
    return df_prices


def annotate_data(data_file: Path, n_samples: int = 50):
    """
    Lance l'outil d'annotation
    
    Args:
        data_file: Fichier de données à annoter
        n_samples: Nombre d'exemples à annoter
    """
    console.print("\n[bold cyan]🏷️  ANNOTATION INTERACTIVE[/bold cyan]")
    
    annotator = DataAnnotator(
        data_path=data_file,
        output_path=ANNOTATED_DATA_DIR / 'annotations.csv'
    )
    
    annotator.start_annotation(max_annotations=n_samples)


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description='WhatsApp Price Intelligence - Extraction et analyse de prix'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande: extract
    extract_parser = subparsers.add_parser('extract', help='Extraire les prix')
    extract_parser.add_argument(
        'whatsapp_file',
        type=Path,
        help='Fichier WhatsApp à traiter (.txt)'
    )
    
    # Commande: annotate
    annotate_parser = subparsers.add_parser('annotate', help='Annoter les données')
    annotate_parser.add_argument(
        'data_file',
        type=Path,
        help='Fichier CSV à annoter'
    )
    annotate_parser.add_argument(
        '--n-samples',
        type=int,
        default=50,
        help='Nombre d\'exemples à annoter (défaut: 50)'
    )
    
    # Commande: validate
    validate_parser = subparsers.add_parser('validate', help='Valider les données')
    validate_parser.add_argument(
        'data_file',
        type=Path,
        help='Fichier CSV à valider'
    )
    
    # Commande: full-pipeline
    pipeline_parser = subparsers.add_parser(
        'full-pipeline',
        help='Pipeline complet: extraction + validation + annotation'
    )
    pipeline_parser.add_argument(
        'whatsapp_file',
        type=Path,
        help='Fichier WhatsApp à traiter'
    )
    pipeline_parser.add_argument(
        '--annotate',
        action='store_true',
        help='Lancer l\'annotation après extraction'
    )
    
    args = parser.parse_args()
    
    # Afficher la bannière
    print_banner()
    
    # Exécuter la commande
    if args.command == 'extract':
        extract_pipeline(args.whatsapp_file)
    
    elif args.command == 'annotate':
        annotate_data(args.data_file, args.n_samples)
    
    elif args.command == 'validate':
        df = pd.read_csv(args.data_file)
        validator = DataValidator()
        validator.generate_quality_report(df)
    
    elif args.command == 'full-pipeline':
        df_prices = extract_pipeline(args.whatsapp_file)
        
        if args.annotate:
            prices_file = PROCESSED_DATA_DIR / 'prices_extracted.csv'
            annotate_data(prices_file, n_samples=100)
    
    else:
        parser.print_help()
        console.print("\n[yellow]💡 Exemples d'utilisation:[/yellow]")
        console.print("  python main.py extract data/raw/whatsapp_export.txt")
        console.print("  python main.py annotate data/processed/prices_extracted.csv")
        console.print("  python main.py full-pipeline data/raw/whatsapp_export.txt --annotate")


if __name__ == '__main__':
    main()
