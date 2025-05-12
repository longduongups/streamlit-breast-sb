import streamlit as st
import pandas as pd
import requests

SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
TABLE = "breast_measurements"

@st.cache_data(ttl=10)
def load_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{TABLE}?select=*", headers=headers)
    if r.status_code != 200:
        st.error(f"Erreur: {r.text}")
        return pd.DataFrame()
    return pd.DataFrame(r.json()).sort_values("timestamp", ascending=False)

st.title("📊 Mesures de poitrine (Supabase)")
df = load_data()

if df.empty:
    st.warning("Aucune donnée.")
    st.stop()

selected = st.selectbox("Sélectionnez une mesure :", df["timestamp"])
row = df[df["timestamp"] == selected].iloc[0]

st.write(row)
