# """
# Module principal avec affichage des prévisions des 3 prochains mois
# """
# from .database import session, add_message, add_price
# from .parser import parse_whatsapp_txt
# from .cleaner import nettoyer_messages
# from .extractor import PigPriceExtractorLLM
# from .predictor import AutomatedPricePredictor
# import pandas as pd

# def process_automated_extraction(file_path):
#     """
#     Traite un fichier WhatsApp et génère les prévisions de prix
#     """
#     # 1. PARSING
#     df_messages = parse_whatsapp_txt(file_path)
#     if df_messages.empty:
#         return None, None

#     # 2. NETTOYAGE
#     df_messages = nettoyer_messages('messages_nettoyes.csv', 'messages_final.csv')
#     if df_messages.empty:
#         return None, None

#     # 3. ENREGISTREMENT DES MESSAGES EN BD
#     for idx, row in df_messages.iterrows():
#         add_message(session, {
#             'message_id': idx,
#             'date': row['date'],
#             'sender': row['sender'],
#             'message': row['message']
#         })

#     # 4. EXTRACTION DES PRIX
#     extractor = PigPriceExtractorLLM()
#     enhanced_prices = []
    
#     for idx, row in df_messages.iterrows():
#         prices = extractor.extract_prices_with_llm(row['message'])
#         if prices:
#             animal_type = extractor.classify_animal_with_llm(row['message'])
#             action_type = extractor.classify_action_with_context(row['message'])
            
#             for price in prices:
#                 if 5000 <= price <= 2000000:
#                     enhanced_prices.append({
#                         'message_id': idx,
#                         'date': row['date'],
#                         'sender': row['sender'],
#                         'message': row['message'],
#                         'price': price,
#                         'animal_type': animal_type,
#                         'action_type': action_type,
#                         'extraction_method': 'llm_enhanced'
#                     })

#     df_enhanced = pd.DataFrame(enhanced_prices)

#     # 5. SAVE PRIX EN BD
#     for idx, row in df_enhanced.iterrows():
#         add_price(session, {
#             'message_id': row['message_id'],
#             'price': row['price'],
#             'animal_type': row['animal_type'],
#             'action_type': row['action_type'],
#             'extraction_method': row['extraction_method']
#         })

#     # 6. ENTRAÎNEMENT DU MODÈLE
#     predictor = AutomatedPricePredictor()
#     predictor.train_advanced_model(df_enhanced)

#     # 7.  GÉNÉRATION ET AFFICHAGE DES PRÉVISIONS
#     afficher_previsions_3_mois(predictor, df_enhanced)

#     # 8. SAUVEGARDE CSV
#     df_enhanced.to_csv('prix_llm_enhanced.csv', index=False, encoding='utf-8-sig')

#     return df_enhanced, predictor


# def afficher_previsions_3_mois(predictor, df_enhanced):
#     """
#     Génère et affiche les prévisions de prix pour les 3 prochains mois
#     pour tous les types d'animaux présents dans les données
#     """
#     if predictor.model is None:
#         print(" Aucun modèle entraîné, impossible de générer les prévisions")
#         return
    
#     if df_enhanced.empty:
#         print(" Aucune donnée de prix, impossible de générer les prévisions")
#         return
    
#     # Récupérer les types d'animaux uniques
    
#     animal_types = df_enhanced['animal_type'].unique()
#     animal_types = [a for a in animal_types if a and a != 'non_specifie']
    
#     if not animal_types:
#         print(" Aucun type d'animal spécifique trouvé dans les données")
#         return
    
#     # Emojis pour chaque type
#     emojis = {
#         'verrat': '🐗',
#         'truie': '🐷',
#         'porcelet': '🐖',
#         'porc': '🐽'
#     }
    
#     print("\n" + "="*70)
#     print(" PRÉVISIONS DE PRIX - 3 PROCHAINS MOIS")
#     print("="*70)
    
#     toutes_previsions = []
    
#     for animal_type in animal_types:
#         emoji = emojis.get(animal_type, '🐖')
        
#         # Genere prevision pour cet animal
#         predictions = predictor.predict_future_prices(
#             animal_type=animal_type,
#             months_ahead=3
#         )
        
#         if predictions:
#             print(f"\n{emoji} {animal_type.upper()}:")
#             print("-" * 70)
            
#             for pred in predictions:
#                 date_str = pred['date'].strftime('%Y-%m-%d')
#                 prix = pred['prix_predit']
#                 print(f"   • {date_str}: {prix:,.0f} FCFA")
                
#                 # Stocker pour sauvegarde CSV
#                 toutes_previsions.append({
#                     'date_prevision': pred['date'],
#                     'animal_type': animal_type,
#                     'prix_predit': prix
#                 })
    
#     print("\n" + "="*70)
    
#     # Save prevision dans csv
#     if toutes_previsions:
#         df_previsions = pd.DataFrame(toutes_previsions)
#         df_previsions.to_csv('previsions_prix_3mois.csv', index=False, encoding='utf-8-sig')
#         print("Prévisions sauvegardées dans: previsions_prix_3mois.csv")
    
#     print()


# def enregistrer_donnees_en_bd(df_messages, df_enhanced):
#     """
#     Enregistre les messages et prix extraits dans la base
#     (Fonction utilitaire si besoin de ré-enregistrer)
#     """
#     from .database import session, add_message, add_price

#     # Enregistrer les messages
#     for idx, row in df_messages.iterrows():
#         add_message(session, {
#             'message_id': idx,
#             'date': row['date'],
#             'sender': row['sender'],
#             'message': row['message']
#         })

#     # Enregistrer les prix
#     for idx, row in df_enhanced.iterrows():
#         add_price(session, {
#             'message_id': row['message_id'],
#             'price': row['price'],
#             'animal_type': row['animal_type'],
#             'action_type': row['action_type'],
#             'extraction_method': row['extraction_method']
#         })


# if __name__ == "__main__":
#     # Test avec un fichier
#     process_automated_extraction("whatsapp_chat.txt")

from .database import session, add_message, add_price, get_prices_dataframe
from .parser import parse_whatsapp_txt
from .cleaner import nettoyer_messages
from .extractor import PigPriceExtractorLLM
from .predictor import AutomatedPricePredictor
import pandas as pd

def process_file_and_train(file_path):
    """
    Traite un fichier WhatsApp et entraîne le modèle uniquement sur ce fichier.
    """
    # 1️⃣ PARSING
    df_messages = parse_whatsapp_txt(file_path)
    if df_messages.empty:
        print("⚠️ Fichier vide ou non parsable")
        return

    # 2️⃣ NETTOYAGE
    df_messages = nettoyer_messages('messages_nettoyes.csv', 'messages_final.csv')
    if df_messages.empty:
        print("⚠️ Aucun message après nettoyage")
        return

    # 3️⃣ ENREGISTREMENT DES MESSAGES EN BD
    for idx, row in df_messages.iterrows():
        add_message(session, {
            'message_id': idx,
            'date': row['date'],
            'sender': row['sender'],
            'message': row['message']
        })

    # 4️⃣ EXTRACTION DES PRIX
    extractor = PigPriceExtractorLLM()
    enhanced_prices = []

    for idx, row in df_messages.iterrows():
        prices = extractor.extract_prices_with_llm(row['message'])
        if prices:
            animal_type = extractor.classify_animal_with_llm(row['message'])
            action_type = extractor.classify_action_with_context(row['message'])
            for price in prices:
                if 5000 <= price <= 2000000:
                    enhanced_prices.append({
                        'message_id': idx,
                        'date': row['date'],
                        'sender': row['sender'],
                        'message': row['message'],
                        'price': price,
                        'animal_type': animal_type,
                        'action_type': action_type,
                        'extraction_method': 'llm_enhanced'
                    })

    df_enhanced = pd.DataFrame(enhanced_prices)

    # 5️⃣ ENREGISTREMENT DES PRIX EN BD
    for idx, row in df_enhanced.iterrows():
        add_price(session, {
            'message_id': row['message_id'],
            'price': row['price'],
            'animal_type': row['animal_type'],
            'action_type': row['action_type'],
            'extraction_method': row['extraction_method']
        })

    # 6️⃣ ENTRAÎNEMENT DU MODÈLE SUR CE FICHIER UNIQUEMENT
    predictor = AutomatedPricePredictor()
    predictor.train_advanced_model(df_enhanced)

    # 7️⃣ Sauvegarde CSV (optionnel pour suivi)
    df_enhanced.to_csv('prix_llm_enhanced.csv', index=False, encoding='utf-8-sig')

    return df_enhanced, predictor

def run_global_prediction():
    """
    Génère la prédiction globale unique sur toutes les données cumulées en BD.
    """
    df_all = get_prices_dataframe(session)
    if df_all.empty:
        print("⚠️ Pas de données pour la prédiction globale")
        return

    predictor = AutomatedPricePredictor()
    predictor.train_advanced_model(df_all)

    # Affiche les prévisions pour 3 mois pour tous les animaux
    afficher_previsions_3_mois(predictor, df_all)

def afficher_previsions_3_mois(predictor, df_enhanced):
    if predictor.model is None or df_enhanced.empty:
        print("⚠️ Pas de modèle ou de données pour prévision")
        return

    animal_types = df_enhanced['animal_type'].unique()
    animal_types = [a for a in animal_types if a and a != 'non_specifie']

    emojis = {'verrat':'','truie':'','porcelet':'','porc':''}
    toutes_previsions = []

    for animal_type in animal_types:
        emoji = emojis.get(animal_type,'🐖')
        predictions = predictor.predict_future_prices(animal_type=animal_type, months_ahead=3)
        if predictions:
            print(f"\n{emoji} {animal_type.upper()}:")
            print("-"*70)
            for pred in predictions:
                date_str = pred['date'].strftime('%Y-%m-%d')
                prix = pred['prix_predit']
                print(f"   • {date_str}: {prix:,.0f} FCFA")
                toutes_previsions.append({
                    'date_prevision': pred['date'],
                    'animal_type': animal_type,
                    'prix_predit': prix
                })

    if toutes_previsions:
        df_previsions = pd.DataFrame(toutes_previsions)
        df_previsions.to_csv('previsions_prix_3mois.csv', index=False, encoding='utf-8-sig')
        print("\nPrévisions globales sauvegardées dans: previsions_prix_3mois.csv")
