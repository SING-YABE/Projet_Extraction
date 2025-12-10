"""
Script de démonstration complète du projet
Montre toutes les fonctionnalités avec le fichier exemple
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import pandas as pd

console = Console()


def demo():
    """Démonstration complète"""
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]🐷 WhatsApp Price Intelligence[/bold green]\n"
        "[dim]Démonstration complète des fonctionnalités[/dim]",
        border_style="green"
    ))
    
    # ============================================================
    # ÉTAPE 1: PARSING
    # ============================================================
    console.print("\n[bold cyan]📤 ÉTAPE 1: Parsing WhatsApp[/bold cyan]\n")
    
    from src.extraction import parse_whatsapp_file
    
    input_file = Path('data/raw/sample_whatsapp.txt')
    
    if not input_file.exists():
        console.print("[red]❌ Fichier sample_whatsapp.txt introuvable ![/red]")
        console.print("Veuillez lancer depuis la racine du projet")
        return
    
    console.print(f"📄 Fichier: {input_file}")
    console.print("⏳ Parsing en cours...\n")
    
    df_messages = parse_whatsapp_file(input_file)
    
    console.print(f"[green]✓ {len(df_messages)} messages parsés[/green]\n")
    
    # Afficher quelques messages
    table = Table(title="Aperçu des messages parsés")
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Date", style="yellow", width=18)
    table.add_column("Message", style="white", width=60)
    
    for _, row in df_messages.head(5).iterrows():
        table.add_row(
            str(row['message_id']),
            str(row['date'])[:19],
            row['message'][:57] + "..."
        )
    
    console.print(table)
    console.print()
    
    # ============================================================
    # ÉTAPE 2: EXTRACTION DE PRIX
    # ============================================================
    console.print("\n[bold cyan]💰 ÉTAPE 2: Extraction des prix[/bold cyan]\n")
    
    from src.extraction import extract_prices_from_dataframe
    
    console.print("⏳ Extraction en cours...\n")
    
    df_prices = extract_prices_from_dataframe(df_messages)
    
    console.print(f"[green]✓ {len(df_prices)} prix extraits[/green]\n")
    
    # Statistiques
    stats_table = Table(title="Statistiques d'extraction")
    stats_table.add_column("Métrique", style="cyan")
    stats_table.add_column("Valeur", style="white")
    
    stats_table.add_row("Prix extraits", str(len(df_prices)))
    stats_table.add_row(
        "Avec animal identifié",
        str((df_prices['animal_type'] != 'non_specifie').sum())
    )
    stats_table.add_row(
        "Avec action identifiée",
        str((df_prices['action_type'] != 'non_specifie').sum())
    )
    stats_table.add_row(
        "Confiance moyenne",
        f"{df_prices['confiance'].mean():.2f}"
    )
    
    console.print(stats_table)
    console.print()
    
    # Aperçu des prix extraits
    price_table = Table(title="Exemples de prix extraits")
    price_table.add_column("Prix", style="green", width=12)
    price_table.add_column("Type", style="cyan", width=10)
    price_table.add_column("Animal", style="yellow", width=10)
    price_table.add_column("Action", style="magenta", width=10)
    price_table.add_column("Contexte", style="white", width=50)
    
    for _, row in df_prices.head(8).iterrows():
        price_table.add_row(
            f"{int(row['prix']):,} F",
            row['type_produit'][:8],
            str(row['animal_type'])[:8] if pd.notna(row['animal_type']) else "N/A",
            str(row['action_type'])[:8] if pd.notna(row['action_type']) else "N/A",
            row['contexte'][:47] + "..."
        )
    
    console.print(price_table)
    console.print()
    
    # ============================================================
    # ÉTAPE 3: ANALYSE PAR TYPE
    # ============================================================
    console.print("\n[bold cyan]📊 ÉTAPE 3: Analyse par type d'animal[/bold cyan]\n")
    
    # Grouper par animal
    animal_stats = df_prices[df_prices['animal_type'] != 'non_specifie'].groupby('animal_type').agg({
        'prix': ['count', 'mean', 'min', 'max']
    }).round(0)
    
    if len(animal_stats) > 0:
        analysis_table = Table(title="Statistiques par type d'animal")
        analysis_table.add_column("Type", style="cyan")
        analysis_table.add_column("Nombre", style="white")
        analysis_table.add_column("Prix moyen", style="green")
        analysis_table.add_column("Min", style="yellow")
        analysis_table.add_column("Max", style="yellow")
        
        for animal_type, row in animal_stats.iterrows():
            analysis_table.add_row(
                animal_type,
                str(int(row[('prix', 'count')])),
                f"{int(row[('prix', 'mean')]):,} F",
                f"{int(row[('prix', 'min')]):,} F",
                f"{int(row[('prix', 'max')]):,} F"
            )
        
        console.print(analysis_table)
    else:
        console.print("[yellow]Aucun animal spécifique identifié dans cet échantillon[/yellow]")
    
    console.print()
    
    # ============================================================
    # ÉTAPE 4: VALIDATION
    # ============================================================
    console.print("\n[bold cyan]✅ ÉTAPE 4: Validation de la qualité[/bold cyan]\n")
    
    from src.data_quality.validator import DataValidator
    
    validator = DataValidator()
    result = validator.validate_dataframe(df_prices)
    
    # Afficher résultat
    if result.is_valid:
        console.print("[green]✓ Données valides ![/green]\n")
    else:
        console.print(f"[yellow]⚠ {len(result.issues)} problèmes détectés[/yellow]\n")
        for issue in result.issues:
            console.print(f"  [red]•[/red] {issue}")
        console.print()
    
    if result.warnings:
        console.print(f"[blue]ℹ {len(result.warnings)} avertissements :[/blue]\n")
        for warning in result.warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")
        console.print()
    
    # Score de qualité
    report = validator.generate_quality_report(df_prices)
    
    quality_panel = Panel(
        f"[bold green]{report['quality_score']:.1f}/100[/bold green]",
        title="Score de Qualité",
        border_style="green"
    )
    console.print(quality_panel)
    console.print()
    
    # ============================================================
    # ÉTAPE 5: DÉTECTION D'OPPORTUNITÉS
    # ============================================================
    console.print("\n[bold cyan]🎯 ÉTAPE 5: Détection de bonnes affaires[/bold cyan]\n")
    
    # Identifier les prix bas pour chaque type
    good_deals = []
    
    for animal_type in df_prices['animal_type'].unique():
        if animal_type == 'non_specifie':
            continue
        
        animal_df = df_prices[df_prices['animal_type'] == animal_type]
        if len(animal_df) < 2:
            continue
        
        q1 = animal_df['prix'].quantile(0.25)
        median = animal_df['prix'].median()
        
        # Prix < Q1 = bonne affaire potentielle
        deals = animal_df[animal_df['prix'] < q1]
        
        for _, deal in deals.iterrows():
            discount_pct = ((median - deal['prix']) / median) * 100
            good_deals.append({
                'animal': animal_type,
                'prix': deal['prix'],
                'median': median,
                'reduction': discount_pct
            })
    
    if good_deals:
        deals_table = Table(title="🔥 Opportunités détectées")
        deals_table.add_column("Animal", style="cyan")
        deals_table.add_column("Prix offre", style="green")
        deals_table.add_column("Prix médian", style="yellow")
        deals_table.add_column("Économie", style="magenta")
        
        for deal in good_deals[:5]:
            deals_table.add_row(
                deal['animal'],
                f"{int(deal['prix']):,} F",
                f"{int(deal['median']):,} F",
                f"-{deal['reduction']:.0f}%"
            )
        
        console.print(deals_table)
    else:
        console.print("[yellow]Pas d'opportunités détectées (échantillon trop petit)[/yellow]")
    
    console.print()
    
    # ============================================================
    # RÉSUMÉ FINAL
    # ============================================================
    console.print("\n[bold green]✨ Démonstration terminée ![/bold green]\n")
    
    summary_panel = Panel(
        f"[bold]Résumé de la démonstration[/bold]\n\n"
        f"✓ {len(df_messages)} messages parsés\n"
        f"✓ {len(df_prices)} prix extraits\n"
        f"✓ Score de qualité: {report['quality_score']:.1f}/100\n"
        f"✓ {len(good_deals)} opportunités détectées\n\n"
        f"[dim]Les données sont dans data/processed/[/dim]",
        border_style="green"
    )
    
    console.print(summary_panel)
    console.print()
    
    console.print("[bold cyan]🚀 Prochaines étapes :[/bold cyan]\n")
    console.print("1. Testez sur vos propres exports WhatsApp")
    console.print("2. Annotez 50+ exemples pour améliorer la qualité")
    console.print("3. Analysez les tendances sur plusieurs mois")
    console.print("4. Implémentez les modèles de prédiction\n")


if __name__ == '__main__':
    try:
        demo()
    except KeyboardInterrupt:
        console.print("\n[yellow]Démonstration interrompue[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Erreur: {e}[/red]\n")
        import traceback
        traceback.print_exc()
