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

# --- Start of Streamlit App ---
st.set_page_config(page_title="Mesures Poitrine", layout="centered")
st.markdown("""
<style>
    .centered-box {
        background-color: #f0f2f6;
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 10px;
        text-align: center;
        color: black;
        font-family: sans-serif;
        max-width: 280px;
        margin-left: auto;
        margin-right: auto;
    }
    .title-text {
        font-size: 22px;
        margin-bottom: 10px;
    }
    .section-label {
        font-weight: bold;
        font-size: 18px;
        margin-bottom: 5px;
    }
    .measurement-value {
        font-size: 26px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Visualisation des mesures de poitrine")
df = load_data()

if df.empty:
    st.warning("Aucune donnée disponible.")
    st.stop()

st.subheader("👋 Hello, voici vos mesures !")
selected = st.selectbox("Sélectionnez une mesure :", df["timestamp"])
row = df[df["timestamp"] == selected].iloc[0]

# --- Visual layout ---
col1, col2 = st.columns([1, 1], gap="small")
with col1:
    st.markdown("""
    <div class="centered-box">
        <div class="section-label">LEFT</div>
        <div>height</div>
        <div class="measurement-value">{:.1f}</div>
        <div>width</div>
        <div class="measurement-value">{:.1f}</div>
    </div>
    """.format(row['height_cm'], row['width_left_cm']), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="centered-box">
        <div class="section-label">RIGHT</div>
        <div>height</div>
        <div class="measurement-value">{:.1f}</div>
        <div>width</div>
        <div class="measurement-value">{:.1f}</div>
    </div>
    """.format(row['height_cm'], row['width_right_cm']), unsafe_allow_html=True)

# --- Volume and bust/under ---
st.markdown("""
<div class="centered-box">
    <div class="section-label">volume</div>
    <div class="measurement-value">{:.1f} cm³</div>
</div>
<div class="centered-box">
    <div class="section-label">bust</div>
    <progress value="{}" max="150"></progress> {} cm
    <div class="section-label">under</div>
    <progress value="{}" max="150"></progress> {} cm
</div>
""".format(
    row['volume_cm3'],
    int(row['bust_circumference_cm']), int(row['bust_circumference_cm']),
    int(row['band_circumference_cm']), int(row['band_circumference_cm'])
), unsafe_allow_html=True)
