"""
Module de nettoyage des messages WhatsApp après parsing
Version OPTIMISÉE pour données porcines africaines francophones
"""

import pandas as pd
import re
import chardet

def detecter_encodage(fichier):
    """Détecte automatiquement l'encodage du fichier"""
    with open(fichier, 'rb') as f:
        result = chardet.detect(f.read())
    return result.get('encoding', 'utf-8')

def corriger_caracteres_africains(texte):
    """
    Corrige les caractères mal encodés
    VERSION AMÉLIORÉE
    """
    corrections = {
        r'√†|Ã |Ã¡': 'à', r'√¢|Ã¢': 'â', r'√©|Ã©': 'é', 
        r'√®|Ã¨': 'è', r'√ª|Ãª': 'ê', r'√Æ|Ã®': 'î',
        r'√¥|Ã´': 'ô', r'√π|Ã¹': 'ù', r'√º|Ã¼': 'ü',
        r'√ß|Ã§': 'ç', r'√â|√à|Ã‰': 'É', r'√Ö|Ã€': 'À',
        # Caractères spéciaux
        r'üôè': '😊', r'üíüèΩ': '📦', r'üê': '🐖',
        r'üëá': '⭐', r'üèæ': '👍', r'üëç': '👌',
        r'¬∞': '°', r'‚Äô': "'", r'‚Äù': '"',
        r'‚Äì': '-', r'‚òù': '♥', r'Ô∏è': '❤',
        r'‚àö': 'é', r'Ø£': '€', r'√Ω': 'ý',
        r'â€“': '-', r'â€™': "'", r'â€œ': '"',
        r'Ã ': 'à', r'Ã§': 'ç', r'Ã©': 'é'
    }
    
    texte_corrige = str(texte)
    for mauvais, bon in corrections.items():
        texte_corrige = re.sub(mauvais, bon, texte_corrige)
    
    return texte_corrige

def filtrer_pertinence_porcs(df):
    """
    Filtre les messages pertinents pour l'analyse des prix porcins
    """
    mots_cles_pertinents = [
        'porc', 'truie', 'verrat', 'porcelet', 'cochon',
        'prix', 'vendre', 'acheter', 'kg', 'sac', 
        'aliment', 'farine', 'soja', 'maïs', 'maØs', 'blé',
        'vif', 'carcasse', 'abattu', 'vente', 'achat',
        'fumier', 'ferme', 'élevage', 'nourriture',
        'cfa', 'fcfa', 'franc', 'fils', 'filles'
    ]
    
    mask = df["message"].str.lower().apply(
        lambda x: any(mot in x.lower() for mot in mots_cles_pertinents)
    )
    
    avant_filtrage = len(df)
    df_filtre = df[mask]
    apres_filtrage = len(df_filtre)
    
    print(f"Filtrage pertinence: {avant_filtrage - apres_filtrage} messages non-pertinents supprimés")
    
    return df_filtre

def extraire_entites_porcines(message):
    """
    Extrait les entités importantes des messages pour l'analyse
    """
    message_str = str(message).lower()
    
    entites = {
        'animal_type': None,
        'produit_type': None,
        'unite': None,
        'transaction_type': None
    }
    
    # Détection type animal
    if re.search(r'\b(porc|cochon)\b', message_str):
        entites['animal_type'] = 'porc'
    elif re.search(r'\btruie\b', message_str):
        entites['animal_type'] = 'truie'
    elif re.search(r'\bverrat\b', message_str):
        entites['animal_type'] = 'verrat'
    elif re.search(r'\bporcelet\b', message_str):
        entites['animal_type'] = 'porcelet'
    elif re.search(r'\b(mâle|male|femelle)\b', message_str):
        entites['animal_type'] = 'porc'
    
    # Détection type de produit
    if re.search(r'\b(aliment|nourriture|farine|soja|maïs|maØs|blé|son|premix|eclaboost|romelko|zoom)\b', message_str):
        entites['produit_type'] = 'aliment'
    elif re.search(r'\b(fumier|fiente)\b', message_str):
        entites['produit_type'] = 'fumier'
    elif re.search(r'\b(ferme|bâtiment|construction|location)\b', message_str):
        entites['produit_type'] = 'infrastructure'
    elif entites['animal_type']:
        entites['produit_type'] = 'animal_vivant'
    elif re.search(r'\b(vétérinaire|veto|malade|médecin)\b', message_str):
        entites['produit_type'] = 'service'
    
    # detection type
    if re.search(r'\b(vendre|vente|disponible|prix)\b', message_str):
        entites['transaction_type'] = 'vente'
    elif re.search(r'\b(acheter|besoin|cherche|recherche)\b', message_str):
        entites['transaction_type'] = 'achat'
    elif re.search(r'\b(donner|conseil|aide|suggestion)\b', message_str):
        entites['transaction_type'] = 'conseil'
    elif re.search(r'\b(louer|location)\b', message_str):
        entites['transaction_type'] = 'location'
    
    # Détection unité
    if re.search(r'\b(kg|kilo|kilogramme)\b', message_str):
        entites['unite'] = 'kg'
    elif re.search(r'\b(sac|tonne|tonnes)\b', message_str):
        entites['unite'] = 'sac'
    elif re.search(r'\b(tête|tete|têtes|tetes)\b', message_str):
        entites['unite'] = 'tête'
    elif re.search(r'\b(mois|semaine)\b', message_str):
        entites['unite'] = 'temps'
    elif re.search(r'\b(hectare|mètre|m2)\b', message_str):
        entites['unite'] = 'surface'
    
    return entites

def categoriser_message(message):
    """
    Catégorise les messages par type pour l'analyse
    """
    msg = str(message).lower()
    
    if any(mot in msg for mot in ['prix', 'cfa', 'fcfa', 'franc', 'fils']):
        return 'avec_prix'
    elif any(mot in msg for mot in ['vendre', 'vente', 'disponible']):
        return 'offre_vente'
    elif any(mot in msg for mot in ['acheter', 'besoin', 'cherche', 'recherche']):
        return 'demande_achat'
    elif any(mot in msg for mot in ['conseil', 'aide', 'problème', 'malade', 'suggestion']):
        return 'conseil'
    elif any(mot in msg for mot in ['contact', 'numéro', 'téléphone', 'appelez', 'whatsapp']):
        return 'contact'
    elif any(mot in msg for mot in ['félicitation', 'bravo', 'merci']):
        return 'félicitations'
    else:
        return 'autre'

def nettoyer_messages(input_csv, output_csv="messages_final.csv"):
    """
    Nettoie le CSV brut exporté par parser.py
    - Corrige l'encodage des caractères
    - Supprime médias/notifications/joins/liens
    - Enlève emojis et caractères parasites
    - Supprime doublons et lignes vides
    - Normalise les numéros de téléphone
    - Filtre par pertinence porcine
    - Extrait les entités structurées
    Retourne un DataFrame propre
    """
    print(f"🧹 NETTOYAGE COMPLET DE {input_csv}...")
    print("=" * 60)
    
    try:
        # Détection automatique de l'encodage
        encodage = detecter_encodage(input_csv)
        print(f"📖 Encodage détecté: {encodage}")
        
        df = pd.read_csv(input_csv, encoding=encodage)
        initial_count = len(df)
        print(f"📊 {initial_count} messages chargés")
        
    except FileNotFoundError:
        print(f"⚠️ Fichier {input_csv} introuvable")
        return pd.DataFrame(columns=['message_id','date','sender','message'])
    except Exception as e:
        print(f"❌ Erreur lecture: {e}")
        # Essai avec encodage de secours
        try:
            df = pd.read_csv(input_csv, encoding='latin-1')
            initial_count = len(df)
            print(f"📊 {initial_count} messages chargés (encodage latin-1)")
        except:
            return pd.DataFrame(columns=['message_id','date','sender','message'])

    # 1. CORRECTION DES CARACTÈRES MAL ENCODÉS
    print("🔧 Correction des caractères...")
    df["message"] = df["message"].apply(corriger_caracteres_africains)
    df["sender"] = df["sender"].apply(corriger_caracteres_africains)

    # 2. Supprimer les messages inutiles (système)
    patterns_exclure = [
        r"<Médias omis>",
        r"<Media omitted>",
        r"Ce message a été supprimé",
        r"message deleted",
        r"Votre code de sécurité",
        r"a rejoint ce groupe",
        r"joined this group",
        r"a quitté",
        r"left the group",
        r"a été remplacé",
        r"was replaced by",
        r"invitation",
        r"\.vcf \(fichier joint\)",
        r"\.vcf \(file attached\)",
        r"Utilise ce lien pour intégrer",
        r"Use this link to join",
        r"https://chat\.whatsapp\.com",
        r"created this group",
        r"changed the subject",
        r"changed this group's icon",
        # Patterns spam spécifiques
        r"FORMATION GRATUITE",
        r"SECRETS POUR RÂUSSIR",
        r"like.*vidéo",
        r"abonnez.*vous",
        r"cloche.*notification",
        r"1000.*jaime",
        r"regarder obligatoirement",
        r"DIFFERENCES ENTRE RACE LOCALE",
    ]

    mask = df["message"].astype(str).apply(
        lambda x: not any(re.search(p, x, re.IGNORECASE) for p in patterns_exclure)
    )
    df = df[mask]
    system_removed = initial_count - len(df)
    print(f"🗑️  {system_removed} messages système/spam supprimés")

    # 3. Nettoyer le texte
    def clean_text(text):
        text = str(text)
        # Supprimer liens
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"www\.\S+", "", text)
        # Enlever emojis et caractères spéciaux problématiques
        text = re.sub(r"[^\w\sàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ,;:!?\.\-+()/%€$@#&😊📦🐖⭐👍👌♥❤]", "", text)
        # Nettoyer ponctuation excessive
        text = re.sub(r"\.{3,}", "...", text)
        text = re.sub(r"!{2,}", "!", text)
        text = re.sub(r"\?{2,}", "?", text)
        # Normaliser espaces
        text = re.sub(r"\s+", " ", text).strip()
        return text

    df["message"] = df["message"].apply(clean_text)

    # 4. Supprimer messages vides
    avant_vide = len(df)
    df = df[df["message"].str.strip() != ""]
    empty_removed = avant_vide - len(df)
    if empty_removed > 0:
        print(f"🗑️  {empty_removed} messages vides supprimés")

    # 5. Supprimer doublons exacts
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["date","sender","message"], keep='first')
    duplicates_removed = before_dedup - len(df)
    if duplicates_removed > 0:
        print(f"🗑️  {duplicates_removed} doublons supprimés")

    # 6. Normaliser les numéros de téléphone (format +226 XX XX XX XX)
    def normalize_phone(sender):
        sender = str(sender).strip()
        # Garder seulement si c'est un numéro
        if re.match(r"^\+?\d[\d\s\-\(\)]+$", sender) and len(sender) > 5:
            # Nettoyer le numero
            numero = re.sub(r"[^\d+]", "", sender)
            if numero.startswith("226") and len(numero) == 11:
                return f"+{numero}"
            elif numero.startswith("00226") and len(numero) == 13:
                return f"+{numero[2:]}"
            elif len(numero) == 8 and not numero.startswith("+"):
                return f"+226 {numero[:2]} {numero[2:4]} {numero[4:6]} {numero[6:]}"
            else:
                return f"+{numero}" if not numero.startswith("+") else numero
        return sender
    
    df["sender"] = df["sender"].apply(normalize_phone)

    # 7. Filtrer messages trop courts (< 5 caractères, probablement inutiles)
    avant_court = len(df)
    df = df[df["message"].str.len() >= 3]
    short_removed = avant_court - len(df)
    if short_removed > 0:
        print(f"🗑️  {short_removed} messages trop courts supprimés")

    # 8. FILTRAGE PAR PERTINENCE PORCINE
    avant_pertinence = len(df)
    df = filtrer_pertinence_porcs(df)
    pertinence_removed = avant_pertinence - len(df)
    if pertinence_removed > 0:
        print(f"🎯 {pertinence_removed} messages non-pertinents supprimés")

    # 9. EXTRACTION DES ENTITÉS PORCINES
    print("🏷️  Extraction des entités porcines...")
    df['entites'] = df['message'].apply(extraire_entites_porcines)
    
    # Expansion des entités en colonnes séparées
    df_expanded = pd.json_normalize(df['entites'])
    df = pd.concat([df.drop('entites', axis=1), df_expanded], axis=1)

    # 10. CATÉGORISATION DES MESSAGES
    print(" Catégorisation des messages...")
    df['categorie'] = df['message'].apply(categoriser_message)

    # 11. Ré-indexer message_id
    df.reset_index(drop=True, inplace=True)
    df["message_id"] = df.index

    # 12. Convertir date en datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        # Supprimer les dates invalides
        df = df[df['date'].notna()]

    # Sauvegarder avec encodage UTF-8 BOM pour Excel
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    # RAPPORT FINAL DÉTAILLÉ
    final_count = len(df)
    print(f"\n  NETTOYAGE TERMINÉ:")
    print(f"   • Messages initiaux: {initial_count}")
    print(f"   • Messages finaux: {final_count}")
    print(f"   • Taux de conservation: {final_count/initial_count*100:.1f}%")
    print(f"   • Fichier sauvegardé: {output_csv}")
    
    # STATISTIQUES DÉTAILLÉES
    if final_count > 0:
        print(f"\n STATISTIQUES DÉTAILLÉES:")
        print(f"   • Période: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        print(f"   • Expéditeurs uniques: {df['sender'].nunique()}")
        print(f"   • Longueur moyenne message: {df['message'].str.len().mean():.1f} caractères")
        
        print(f"\n RÉPARTITION PAR CATÉGORIE:")
        for categorie in df['categorie'].unique():
            count = len(df[df['categorie'] == categorie])
            print(f"   • {categorie}: {count} messages ({count/final_count*100:.1f}%)")
        
        print(f"\n RÉPARTITION PAR TYPE D'ANIMAL:")
        animal_counts = df['animal_type'].value_counts()
        for animal, count in animal_counts.items():
            print(f"   • {animal if animal else 'non-spécifié'}: {count} messages")
        
        print(f"\n MESSAGES AVEC PRIX: {len(df[df['categorie'] == 'avec_prix'])}")
    
    return df


def filtrer_prix_valides(df_prix, seuil_min=5000, seuil_max=2000000):
    """
    Filtre supplémentaire pour les prix extraits
    """
    if df_prix is None or df_prix.empty:
        return df_prix
    
    initial = len(df_prix)
    df_filtered = df_prix[
        (df_prix['price'] >= seuil_min) & 
        (df_prix['price'] <= seuil_max)
    ].copy()
    
    removed = initial - len(df_filtered)
    if removed > 0:
        print(f"⚠️ {removed} prix hors limites supprimés ({seuil_min}-{seuil_max} FCFA)")
    
    return df_filtered