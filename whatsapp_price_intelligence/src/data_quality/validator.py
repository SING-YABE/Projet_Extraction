"""
Validateur de qualité des données
Détecte les problèmes et génère des rapports
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from ..utils import PRICE_RANGES, QUALITY_THRESHOLDS, AnimalTypes, setup_logger

logger = setup_logger(__name__)


@dataclass
class ValidationResult:
    """Résultat de validation"""
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    stats: Dict


class DataValidator:
    """Validateur de données"""
    
    def __init__(self):
        self.results = []
    
    def validate_dataframe(self, df: pd.DataFrame) -> ValidationResult:
        """
        Valide un DataFrame complet
        
        Args:
            df: DataFrame à valider
        
        Returns:
            Résultat de validation
        """
        issues = []
        warnings = []
        
        # 1. Vérifier colonnes requises
        required_cols = ['message_id', 'date', 'message']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"Colonnes manquantes: {missing_cols}")
        
        # 2. Vérifier données manquantes
        missing_ratio = df.isnull().sum() / len(df)
        critical_missing = missing_ratio[missing_ratio > QUALITY_THRESHOLDS['max_missing_ratio']]
        if not critical_missing.empty:
            warnings.append(f"Trop de valeurs manquantes: {critical_missing.to_dict()}")
        
        # 3. Valider les prix
        if 'prix' in df.columns:
            price_issues = self._validate_prices(df)
            issues.extend(price_issues)
        
        # 4. Valider les dates
        if 'date' in df.columns:
            date_issues = self._validate_dates(df)
            issues.extend(date_issues)
        
        # 5. Valider les messages
        message_issues = self._validate_messages(df)
        warnings.extend(message_issues)
        
        # 6. Calculer statistiques
        stats = self._calculate_stats(df)
        
        is_valid = len(issues) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            stats=stats
        )
        
        self._log_validation(result)
        
        return result
    
    def _validate_prices(self, df: pd.DataFrame) -> List[str]:
        """Valide les prix"""
        issues = []
        
        # Prix hors limites
        min_price = QUALITY_THRESHOLDS['min_price']
        max_price = QUALITY_THRESHOLDS['max_price']
        
        invalid_prices = df[
            (df['prix'] < min_price) | (df['prix'] > max_price)
        ]
        
        if len(invalid_prices) > 0:
            issues.append(
                f"{len(invalid_prices)} prix hors limites "
                f"({min_price}-{max_price} FCFA)"
            )
        
        # Prix incohérents avec type d'animal
        if 'animal_type' in df.columns:
            for animal_type in AnimalTypes.all():
                animal_df = df[df['animal_type'] == animal_type]
                if len(animal_df) == 0:
                    continue
                
                price_range = PRICE_RANGES.get(animal_type)
                if price_range:
                    min_p, max_p = price_range
                    outliers = animal_df[
                        (animal_df['prix'] < min_p) | (animal_df['prix'] > max_p)
                    ]
                    
                    if len(outliers) > 0:
                        issues.append(
                            f"{len(outliers)} prix incohérents pour {animal_type} "
                            f"(attendu: {min_p}-{max_p} FCFA)"
                        )
        
        return issues
    
    def _validate_dates(self, df: pd.DataFrame) -> List[str]:
        """Valide les dates"""
        issues = []
        
        # Convertir en datetime si nécessaire
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            try:
                df['date'] = pd.to_datetime(df['date'])
            except Exception as e:
                issues.append(f"Erreur conversion dates: {e}")
                return issues
        
        # Dates manquantes
        null_dates = df['date'].isnull().sum()
        if null_dates > 0:
            issues.append(f"{null_dates} dates manquantes")
        
        # Dates futures
        future_dates = df[df['date'] > pd.Timestamp.now()]
        if len(future_dates) > 0:
            issues.append(f"{len(future_dates)} dates futures détectées")
        
        # Dates trop anciennes (>5 ans)
        old_threshold = pd.Timestamp.now() - pd.Timedelta(days=365*5)
        old_dates = df[df['date'] < old_threshold]
        if len(old_dates) > 0:
            issues.append(f"{len(old_dates)} dates >5 ans (peut être normal)")
        
        return issues
    
    def _validate_messages(self, df: pd.DataFrame) -> List[str]:
        """Valide les messages"""
        warnings = []
        
        # Messages trop courts
        min_length = QUALITY_THRESHOLDS['min_message_length']
        short_messages = df[df['message'].str.len() < min_length]
        
        if len(short_messages) > 0:
            warnings.append(f"{len(short_messages)} messages trop courts (<{min_length} car)")
        
        # Messages dupliqués
        duplicates = df[df.duplicated(subset=['message'], keep=False)]
        if len(duplicates) > 0:
            warnings.append(f"{len(duplicates)} messages dupliqués")
        
        return warnings
    
    def _calculate_stats(self, df: pd.DataFrame) -> Dict:
        """Calcule des statistiques descriptives"""
        stats = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'memory_usage': df.memory_usage(deep=True).sum() / 1024**2,  # MB
        }
        
        # Stats par colonne
        if 'prix' in df.columns:
            stats['prix'] = {
                'count': df['prix'].notna().sum(),
                'mean': df['prix'].mean(),
                'median': df['prix'].median(),
                'min': df['prix'].min(),
                'max': df['prix'].max(),
                'std': df['prix'].std()
            }
        
        if 'animal_type' in df.columns:
            stats['animal_distribution'] = df['animal_type'].value_counts().to_dict()
        
        if 'action_type' in df.columns:
            stats['action_distribution'] = df['action_type'].value_counts().to_dict()
        
        if 'date' in df.columns:
            stats['date_range'] = {
                'start': str(df['date'].min()),
                'end': str(df['date'].max()),
                'span_days': (df['date'].max() - df['date'].min()).days
            }
        
        return stats
    
    def _log_validation(self, result: ValidationResult):
        """Log les résultats de validation"""
        if result.is_valid:
            logger.info("✓ Validation réussie")
        else:
            logger.warning(f"⚠ Validation échouée: {len(result.issues)} problèmes")
            for issue in result.issues:
                logger.warning(f"  - {issue}")
        
        if result.warnings:
            logger.info(f"ℹ {len(result.warnings)} avertissements:")
            for warning in result.warnings:
                logger.info(f"  - {warning}")
    
    def generate_quality_report(
        self, 
        df: pd.DataFrame, 
        output_path: Optional[Path] = None
    ) -> Dict:
        """
        Génère un rapport de qualité complet
        
        Args:
            df: DataFrame à analyser
            output_path: Chemin de sauvegarde optionnel
        
        Returns:
            Dictionnaire avec métriques de qualité
        """
        validation = self.validate_dataframe(df)
        
        report = {
            'validation': {
                'is_valid': validation.is_valid,
                'issues_count': len(validation.issues),
                'warnings_count': len(validation.warnings),
                'issues': validation.issues,
                'warnings': validation.warnings
            },
            'statistics': validation.stats,
            'quality_score': self._calculate_quality_score(validation)
        }
        
        if output_path:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"✓ Rapport sauvegardé: {output_path}")
        
        return report
    
    def _calculate_quality_score(self, validation: ValidationResult) -> float:
        """Calcule un score de qualité 0-100"""
        score = 100.0
        
        # Pénalités
        score -= len(validation.issues) * 10  # -10 points par problème
        score -= len(validation.warnings) * 2  # -2 points par avertissement
        
        return max(0.0, score)


def validate_data(data_path: Path) -> ValidationResult:
    """
    Fonction utilitaire pour valider rapidement des données
    
    Args:
        data_path: Chemin vers le fichier CSV
    
    Returns:
        Résultat de validation
    """
    df = pd.read_csv(data_path)
    validator = DataValidator()
    return validator.validate_dataframe(df)
