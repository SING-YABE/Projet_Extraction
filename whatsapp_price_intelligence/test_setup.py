"""
Script de test rapide pour vérifier l'installation
"""
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from rich.console import Console
from rich.table import Table

console = Console()


def test_imports():
    """Teste les imports essentiels"""
    console.print("\n[bold cyan]🧪 Test des imports...[/bold cyan]\n")
    
    tests = []
    
    # Test 1: Utils
    try:
        from src.utils import AnimalTypes, ActionTypes, setup_logger
        tests.append(("Utils", "✅ OK"))
    except Exception as e:
        tests.append(("Utils", f"❌ {str(e)}"))
    
    # Test 2: Extraction
    try:
        from src.extraction import WhatsAppParser, PriceExtractor
        tests.append(("Extraction", "✅ OK"))
    except Exception as e:
        tests.append(("Extraction", f"❌ {str(e)}"))
    
    # Test 3: Data Quality
    try:
        from src.data_quality.validator import DataValidator
        from src.data_quality.annotator import DataAnnotator
        tests.append(("Data Quality", "✅ OK"))
    except Exception as e:
        tests.append(("Data Quality", f"❌ {str(e)}"))
    
    # Afficher résultats
    table = Table(title="Résultats des tests")
    table.add_column("Module", style="cyan")
    table.add_column("Statut", style="white")
    
    for module, status in tests:
        table.add_row(module, status)
    
    console.print(table)
    
    # Vérifier si tous passent
    all_passed = all("✅" in status for _, status in tests)
    
    if all_passed:
        console.print("\n[bold green]✨ Tous les tests passent ![/bold green]\n")
    else:
        console.print("\n[bold red]❌ Certains tests ont échoué[/bold red]\n")
    
    return all_passed


def test_extraction():
    """Teste l'extraction sur un exemple"""
    console.print("\n[bold cyan]🧪 Test extraction...[/bold cyan]\n")
    
    from src.extraction import PriceExtractor
    
    extractor = PriceExtractor()
    
    test_messages = [
        "Porcelets de 3 mois disponibles à 25000f l'unité",
        "Truie gestante à vendre 100000 FCFA",
        "Son de maïs à 7500f le sac de 50kg",
        "Bonjour, comment allez-vous?",  # Pas de prix
    ]
    
    table = Table(title="Tests d'extraction")
    table.add_column("Message", style="cyan", width=50)
    table.add_column("Prix extraits", style="green")
    
    for msg in test_messages:
        prices = extractor.extract_from_message(msg)
        
        if prices:
            price_str = ", ".join([
                f"{p.prix} FCFA ({p.animal_type or p.type_produit})"
                for p in prices
            ])
        else:
            price_str = "[dim]Aucun prix[/dim]"
        
        table.add_row(msg[:47] + "...", price_str)
    
    console.print(table)
    console.print()


def test_file_structure():
    """Vérifie la structure des fichiers"""
    console.print("\n[bold cyan]📁 Vérification structure...[/bold cyan]\n")
    
    required_dirs = [
        'src/extraction',
        'src/data_quality',
        'src/utils',
        'data',
        'logs'
    ]
    
    table = Table(title="Structure du projet")
    table.add_column("Dossier", style="cyan")
    table.add_column("Statut", style="white")
    
    project_root = Path(__file__).parent
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            table.add_row(dir_path, "✅ Existe")
        else:
            table.add_row(dir_path, "❌ Manquant")
    
    console.print(table)
    console.print()


def main():
    """Lance tous les tests"""
    console.print("\n[bold green]🎯 WhatsApp Price Intelligence - Tests[/bold green]\n")
    
    # Tests
    test_file_structure()
    imports_ok = test_imports()
    
    if imports_ok:
        test_extraction()
    
    console.print("\n[bold green]✅ Tests terminés ![/bold green]\n")
    console.print("💡 Pour tester sur de vraies données:")
    console.print("   python main.py extract data/raw/whatsapp_export.txt\n")


if __name__ == '__main__':
    main()
