"""
Script d'exécution principal - Watcher automatique + traitement des fichiers existants
"""

import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from whatsapp_price_extractor import process_automated_extraction

WATCHED_DIR = "/Users/patrick/Documents"

class WhatsAppFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".txt"):
            self.process_file(event.src_path)

    def process_file(self, file_path):
        print(f"\nTraitement fichier : {file_path}")
        try:
            enhanced_data, predictor_model = process_automated_extraction(file_path)
            print("Traitement terminé !")
            print("   • messages_nettoyes.csv, prix_llm_enhanced.csv générés")
        except Exception as e:
            print(f"Erreur ttt du ficher {file_path} : {e}")

if __name__ == "__main__":
    print(f" Surveillance dossier : {WATCHED_DIR}")
    event_handler = WhatsAppFileHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()

    # ⚡ Traite fichier existant au lancement
    for filename in os.listdir(WATCHED_DIR):
        if filename.endswith(".txt"):
            file_path = os.path.join(WATCHED_DIR, filename)
            event_handler.process_file(file_path)

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
        print("Surveillance arrêtée.")
    observer.join()
 