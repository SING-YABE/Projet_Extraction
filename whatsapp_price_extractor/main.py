# -*- coding: utf-8 -*-
"""
Module principal orchestrant l'extraction et la prédiction
"""

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from .parser import parse_whatsapp_txt
from .extractor import PigPriceExtractorLLM
from .predictor import AutomatedPricePredictor

def process_automated_extraction(file_path):
    print("SYSTÈME COMPLET WHATSAPP → PRIX")
    print("=" * 60)
    
    df_messages = parse_whatsapp_txt(file_path)
    if df_messages.empty:
        return None, None
    
    extractor = PigPriceExtractorLLM()
    enhanced_prices = []
    
    for idx, row in df_messages.iterrows():
        message = row['message']
        prices = extractor.extract_prices_with_llm(message)
        if prices:
            animal_type = extractor.classify_animal_with_llm(message)
            action_type = extractor.classify_action_with_context(message)
            for price in prices:
                if 5000 <= price <= 2000000:
                    enhanced_prices.append({
                        'message_id': idx,
                        'date': row.get('date'),
                        'sender': row.get('sender'),
                        'message': message,
                        'price': price,
                        'animal_type': animal_type,
                        'action_type': action_type,
                        'extraction_method': 'llm_enhanced',
                        'Recharges': ''
                    })
    
    df_enhanced = pd.DataFrame(enhanced_prices)
    print(f"✅ {len(df_enhanced)} prix extraits avec LLM")
    
    predictor = AutomatedPricePredictor()
    predictor.train_advanced_model(df_enhanced)
    
    if getattr(predictor, "model", None):
        print("\n PRÉVISIONS AUTOMATIQUES:")
        for animal in ['verrat', 'truie', 'porcelet', 'porc']:
            preds = predictor.predict_future_prices(animal, 3)
            if preds:
                print(f"\n🐖 {animal.upper()}:")
                for p in preds:
                    # si p['date'] est un datetime, strftime fonctionnera ; sinon adapter
                    date_str = p['date'].strftime('%B %Y') if hasattr(p['date'], 'strftime') else str(p['date'])
                    print(f"   {date_str}: {p['prix_predit']:,.0f} FCFA")
    
    df_enhanced.to_csv('prix_llm_enhanced.csv', index=False)
    return df_enhanced, predictor
