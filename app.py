import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# --- Configuration ---
DB_PATH = "C:/Users/longd/Documents/Data_Poitrine.db"  # adapte ce chemin si besoin

# --- Connexion à la base ---
def load_breast_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM BreastMeasurements ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# --- Titre ---
st.title("📊 Visualisation des mesures de poitrine")

# --- Chargement des données ---
try:
    df = load_breast_data()
except Exception as e:
    st.error(f"Erreur lors de la lecture de la base de données : {e}")
    st.stop()

if df.empty:
    st.warning("Aucune donnée trouvée dans la base.")
    st.stop()

# --- Sélection d'une mesure ---
selected_row = st.selectbox("Sélectionnez une mesure :", df["timestamp"])

selected_data = df[df["timestamp"] == selected_row].iloc[0]

st.markdown(f"""
### 🧍 Détails de la mesure

- 📅 **Date :** `{selected_data['timestamp']}`
- 📏 **Hauteur de la poitrine :** {selected_data['height_cm']:.2f} cm  
- ↔️ **Largeur gauche :** {selected_data['width_left_cm']:.2f} cm  
- ↔️ **Largeur droite :** {selected_data['width_right_cm']:.2f} cm  
- 🔵 **Tour sous-poitrine (bande) :** {selected_data['band_circumference_cm']:.2f} cm  
- 🔴 **Tour de poitrine (bust) :** {selected_data['bust_circumference_cm']:.2f} cm  
- 💧 **Volume estimé :** {selected_data['volume_cm3']:.1f} cm³
""")

