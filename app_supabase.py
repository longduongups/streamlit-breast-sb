import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="Mesures Poitrine", layout="wide")

# --- Supabase credentials ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
TABLE = "breast_measurements"

params = st.query_params
client_id = st.text_input("🧍 Identifiant client", value=params.get("client_id", [""])[0])
access_code = st.text_input("🔐 Code (6 chiffres)", type="password", value=params.get("code", [""])[0])

if not client_id or not access_code:
    st.stop()

# --- Load data from Supabase ---
@st.cache_data(ttl=10)
def load_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?client_id=eq.{client_id}&access_code=eq.{access_code}&select=*"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error(f"Erreur: {r.text}")
        return pd.DataFrame()
    data = r.json()
    if not data:
        st.warning("Aucune donnée trouvée pour cet identifiant et code.")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp", ascending=False)
    return df

# --- Start of Streamlit App ---

st.markdown("""
<style>
    .centered-box {
        background-color: #f0f2f6;
        padding: 12px;
        margin: 10px;
        border-radius: 10px;
        text-align: center;
        color: black;
        font-family: sans-serif;
        flex: 1 1 160px;
        min-width: 140px;
    }
    .flex-container {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: nowrap;
        flex-direction: row;
        overflow-x: auto;
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
        font-size: 24px;
        font-weight: bold;
    }
    .type-display {
        background-color: #ddd;
        padding: 8px 16px;
        border-radius: 20px;
        display: inline-block;
        font-size: 16px;
        margin-top: 10px;
    }
    .type-label {
        font-size: 13px;
        color: #666;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Visualisation des mesures de poitrine")
df = load_data()

if df.empty:
    st.stop()

st.subheader(f"👋 Hello, {client_id}! Here are your measurements:")
selected = st.selectbox("Sélectionnez une mesure :", df["timestamp"] if "timestamp" in df.columns else df.index)
row = df[df["timestamp"] == selected].iloc[0] if "timestamp" in df.columns else df.iloc[0]

# --- Visual layout using flexbox ---
st.markdown(f"""
<div class="flex-container">
    <div class="centered-box">
        <div class="section-label">LEFT</div>
        <div>height</div>
        <div class="measurement-value">{row['height_cm']:.1f}</div>
        <div>width</div>
        <div class="measurement-value">{row['width_left_cm']:.1f}</div>
    </div>
    <div class="centered-box">
        <div class="section-label">RIGHT</div>
        <div>height</div>
        <div class="measurement-value">{row['height_cm']:.1f}</div>
        <div>width</div>
        <div class="measurement-value">{row['width_right_cm']:.1f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Volume and bust/under ---
st.markdown(f"""
<div class="centered-box" style="max-width: 460px; margin-left: auto; margin-right: auto;">
    <div class="section-label">volume</div>
    <div class="measurement-value">{row['volume_cm3']:.1f} cm³</div>
</div>
<div class="centered-box" style="max-width: 460px; margin-left: auto; margin-right: auto;">
    <div class="section-label">bust</div>
    <progress value="{int(row['bust_circumference_cm'])}" max="150"></progress> {int(row['bust_circumference_cm'])} cm
    <div class="section-label">under</div>
    <progress value="{int(row['band_circumference_cm'])}" max="150"></progress> {int(row['band_circumference_cm'])} cm
</div>
""", unsafe_allow_html=True)

# --- Type display block ---
st.markdown(f"""
<div class="centered-box" style="max-width: 460px; margin-left: auto; margin-right: auto;">
    <div class="section-label">TYPE</div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div class="type-label">vertical</div>
            <div class="type-display">{row['vertical_type']}</div>
        </div>
        <span style="border-left: 2px solid #aaa; height: 40px; margin: 0 10px;"></span>
        <div>
            <div class="type-label">horizontal</div>
            <div class="type-display">{row['horizontal_type']}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
