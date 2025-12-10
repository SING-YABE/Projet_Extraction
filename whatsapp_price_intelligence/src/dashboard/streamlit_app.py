"""
Dashboard Streamlit
À implémenter en Phase 3 avec interface utilisateur complète
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# TODO: Implémenter dashboard complet
# Pages à créer:
# 1. Accueil - KPIs principaux
# 2. Évolution - Graphiques prix
# 3. Opportunités - Bonnes affaires
# 4. Upload - Extraction en direct
# 5. Admin - Configuration

def main():
    """
    Application Streamlit principale
    
    Pour lancer:
        streamlit run src/dashboard/streamlit_app.py
    """
    st.set_page_config(
        page_title="🐷 Prix du Marché Porcin",
        page_icon="🐷",
        layout="wide"
    )
    
    st.title("🐷 Intelligence des Prix - Marché Porcin")
    st.markdown("---")
    
    st.warning("⚠️ Dashboard en cours d'implémentation (Phase 3)")
    
    st.info("""
    **Dashboard prévu:**
    - 📊 Vue d'ensemble avec KPIs
    - 📈 Graphiques d'évolution des prix
    - 🎯 Détection d'opportunités
    - 📤 Upload et extraction en direct
    - ⚙️ Configuration et admin
    
    **Pour contribuer:**
    1. Collecter suffisamment de données (500+ prix)
    2. Implémenter les pages une par une
    3. Tester avec utilisateurs beta
    """)
    
    # Exemple de graphique simple
    st.subheader("Exemple de visualisation")
    
    # Données exemple
    data = pd.DataFrame({
        'Mois': ['Juin', 'Juillet', 'Août', 'Septembre'],
        'Prix Moyen': [25000, 27000, 26000, 28000]
    })
    
    fig = px.line(
        data, 
        x='Mois', 
        y='Prix Moyen',
        title='Évolution Prix Porcelets (Exemple)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.caption("WhatsApp Price Intelligence v0.1.0")


if __name__ == '__main__':
    main()
