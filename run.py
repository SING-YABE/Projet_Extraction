
import os
import time
from whatsapp_price_extractor import process_file_and_train, run_global_prediction

# === CONFIGURATION DU DOSSIER À SURVEILLER ===
DOSSIER_SURVEILLE = "/Users/patrick/Documents"

print(f"🔍 Surveillance dossier : {DOSSIER_SURVEILLE}\n")

# === MÉMO DES FICHIERS DÉJÀ TRAITÉS ===
fichiers_traites = set()

# === FONCTION PRINCIPALE ===
def surveiller_dossier():
    while True:
        # Liste tous les fichiers .txt dans le dossier
        fichiers = [
            os.path.join(DOSSIER_SURVEILLE, f)
            for f in os.listdir(DOSSIER_SURVEILLE)
            if f.lower().endswith(".txt")
        ]

        # Détection des nouveaux fichiers
        nouveaux_fichiers = [f for f in fichiers if f not in fichiers_traites]

        if nouveaux_fichiers:
            for fichier in nouveaux_fichiers:
                print(f"📂 Traitement fichier : {fichier}")
                try:
                    process_file_and_train(fichier)
                    fichiers_traites.add(fichier)
                except Exception as e:
                    print(f"❌ Erreur lors du traitement de {fichier} : {e}")

            # Une fois tous les nouveaux fichiers traités, on génère la prévision globale
            print("\n📈 Génération des prévisions globales basées sur toutes les données...")
            try:
                run_global_prediction()
                print("✅ Prévision globale générée avec succès !\n")
            except Exception as e:
                print(f"⚠️ Erreur lors de la génération des prévisions globales : {e}")
        
        # Attend avant de revérifier le dossier
        time.sleep(5)

# === LANCEMENT ===
if __name__ == "__main__":
    surveiller_dossier()
# webhook_whatsapp.py
