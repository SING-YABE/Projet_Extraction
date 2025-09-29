"""
Script d'exécution principal
"""

from whatsapp_price_extractor import process_automated_extraction

if __name__ == "__main__":
    enhanced_data, predictor_model = process_automated_extraction("/Users/patrick/Documents/whatsapp.txt")
    print("\n SYSTÈME AUTOMATISÉ Okkkkk!")
    print("Fichiers generes: messages_nettoyes.csv, prix_llm_enhanced.csv")
