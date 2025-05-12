import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import datetime

# --- Supabase credentials ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
TABLE = "breast_measurements"

# --- Load data from Supabase ---
@st.cache_data(ttl=10)
def load_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?select=*"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error(f"Erreur: {r.text}")
        return pd.DataFrame()
    return pd.DataFrame(r.json()).sort_values("timestamp", ascending=False)

# --- Display visual card for a selected row ---
def show_measurement_card(row):
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:20px;border-radius:10px;color:#000000">
        <h4>🧍 Mesure du {row['timestamp']}</h4>
        <ul style="list-style:none;padding-left:0">
            <li><b>Hauteur :</b> {row['height_cm']:.2f} cm</li>
            <li><b>Largeur gauche :</b> {row['width_left_cm']:.2f} cm</li>
            <li><b>Largeur droite :</b> {row['width_right_cm']:.2f} cm</li>
            <li><b>Bande :</b> {row['band_circumference_cm']:.2f} cm</li>
            <li><b>Buste :</b> {row['bust_circumference_cm']:.2f} cm</li>
            <li><b>Volume :</b> {row['volume_cm3']:.1f} cm³</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# --- Start of Streamlit App ---
st.set_page_config(page_title="Mesures Poitrine", layout="centered")
st.title("📊 Visualisation des mesures de poitrine")

# --- Load data ---
df = load_data()

if df.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()

# --- Dropdown to select a measure ---
st.subheader("🔎 Détail d'une mesure")
selected = st.selectbox("Sélectionnez une mesure :", df["timestamp"])
row = df[df["timestamp"] == selected].iloc[0]

# --- Show summary card ---
show_measurement_card(row)