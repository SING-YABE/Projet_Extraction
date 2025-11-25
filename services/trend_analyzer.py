"""
Analyse des tendances de prix
"""
from typing import Dict, List
from datetime import datetime, timedelta
import numpy as np

from utils.logger import logger


class TrendAnalyzer:
    """Analyseur de tendances"""
    
    def analyze(self, prices: List[Dict]) -> Dict:
        """
        Analyze price trends
        
        Args:
            prices: List of price dicts with 'prix' and 'date'
        
        Returns:
            Trend analysis
        """
        if len(prices) < 10:
            return {
                'trend': 'insufficient_data',
                'variation': 0,
                'message': 'Pas assez de données',
                'conseil': 'Collectez plus de prix'
            }
        
        # Sort by date
        sorted_prices = sorted(prices, key=lambda x: x.get('date', ''))
        
        # Split in two periods
        mid = len(sorted_prices) // 2
        old_period = sorted_prices[:mid]
        recent_period = sorted_prices[mid:]
        
        old_avg = np.mean([p['prix'] for p in old_period])
        recent_avg = np.mean([p['prix'] for p in recent_period])
        
        # Calculate variation
        variation = ((recent_avg - old_avg) / old_avg) * 100
        
        # Determine trend
        if variation > 5:
            trend = "📈 HAUSSIÈRE"
            message = f"Prix en hausse de {variation:.1f}%"
            conseil = "Conseil: Les prix montent. Achetez maintenant si besoin."
        elif variation < -5:
            trend = "📉 BAISSIÈRE"
            message = f"Prix en baisse de {abs(variation):.1f}%"
            conseil = "Conseil: Les prix baissent. Bon moment pour acheter."
        else:
            trend = "➡️ STABLE"
            message = f"Prix stables (variation: {variation:+.1f}%)"
            conseil = "Conseil: Prix stables. Pas d'urgence particulière."
        
        return {
            'trend': trend,
            'variation': round(variation, 1),
            'message': message,
            'conseil': conseil,
            'old_avg': int(old_avg),
            'recent_avg': int(recent_avg)
        }
    
    def detect_seasonality(
        self,
        prices: List[Dict],
        period_days: int = 30
    ) -> Dict:
        """
        Detect seasonal patterns
        
        Args:
            prices: List of prices
            period_days: Period to analyze
        
        Returns:
            Seasonality analysis
        """
        if len(prices) < period_days * 3:
            return {'has_seasonality': False}
        
        # Group by period
        periods = {}
        for p in prices:
            date = datetime.fromisoformat(str(p['date']))
            period_key = date.month
            
            if period_key not in periods:
                periods[period_key] = []
            periods[period_key].append(p['prix'])
        
        # Calculate averages
        period_avgs = {
            k: np.mean(v) for k, v in periods.items()
        }
        
        # Check variance
        overall_mean = np.mean(list(period_avgs.values()))
        variance = np.var(list(period_avgs.values()))
        
        has_seasonality = variance > (overall_mean * 0.1)
        
        return {
            'has_seasonality': has_seasonality,
            'by_month': period_avgs,
            'variance': variance
        }
