"""
Module principal orchestrant l'extraction et la prédiction
"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
from .cleaner import nettoyer_messages
from .extractor import PigPriceExtractorLLM
from .predictor import AutomatedPricePredictor
from .parser import parse_whatsapp_txt

def process_automated_extraction(file_path):
    print("SYSTÈME COMPLET WHATSAPP → PRIX")
    print("=" * 60)
    
    # Étape 1: Parse avec gestion d'encodage
    df_messages = parse_whatsapp_txt(file_path)
    if df_messages.empty:
        print("❌ Aucun message parsé")
        return None, None
    
    print(f"✅ {len(df_messages)} messages parsés")
    
    # Étape 2: Nettoyage approfondi
    df_messages = nettoyer_messages('messages_nettoyes.csv', 'messages_final.csv')
    if df_messages.empty:
        print("⚠️ Aucun message après nettoyage")
        return None, None
    
    print(f"✅ {len(df_messages)} messages après nettoyage")
    
    # Étape 3: Extraction des prix
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
    
    if df_enhanced.empty:
        print("⚠️ Aucun prix extrait - arrêt du processus")
        return None, None
    
    # Étape 4: Prédiction
    predictor = AutomatedPricePredictor()
    predictor.train_advanced_model(df_enhanced)
    
    if getattr(predictor, "model", None):
        print("\nPRÉVISIONS AUTOMATIQUES:")
        print("-" * 40)
        for animal in ['verrat', 'truie', 'porcelet', 'porc']:
            preds = predictor.predict_future_prices(animal, 3)
            if preds:
                print(f"\n🐖 {animal.upper()}:")
                for p in preds:
                    date_str = p['date'].strftime('%B %Y') if hasattr(p['date'], 'strftime') else str(p['date'])
                    print(f"   {date_str}: {p['prix_predit']:,.0f} FCFA")
            else:
                print(f"\n❌ Aucune prédiction pour {animal}")
    
    # Sauvegarde
    df_enhanced.to_csv('prix_llm_enhanced.csv', index=False, encoding='utf-8-sig')
    print(f"\n💾 Fichier sauvegardé: prix_llm_enhanced.csv")
    
    return df_enhanced, predictor

if __name__ == "__main__":
    # Test 
    result = process_automated_extraction("whatsapp_chat.txt")
    if result[0] is not None:
        print("\n🎉 Processus terminé avec succès!")
    else:
        print("\n❌ Échec du processus")