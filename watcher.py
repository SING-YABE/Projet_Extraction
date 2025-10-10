import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from whatsapp_price_extractor import process_automated_extraction

WATCHED_DIR = "/Users/patrick/Documents"  

class WhatsAppFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        """Détecte un nouveau fichier créé dans le dossier"""
        if event.is_directory:
            return

        if event.src_path.endswith(".txt"):
            print(f"\n Nouveau fichier détecté : {event.src_path}")
            try:
                enhanced_data, predictor_model = process_automated_extraction(event.src_path)
                print("Traitement termine okk !")
                print("   • messages_nettoyes.csv, prix_llm_enhanced.csv générés")
            except Exception as e:
                print(f"Erreur ttt du fichier{event.src_path} : {e}")

if __name__ == "__main__":
    print(f"👀 Surveillance dossier : {WATCHED_DIR}")
    event_handler = WhatsAppFileHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCHED_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
        print("Surveillance arrêtée.")
    observer.join()
