import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import unicodedata
import re
from uuid import uuid4

# --- Config Supabase ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
TABLE_MODELS = "pending_measurements"
TABLE_MEASURES = "breast_measurements"
STORAGE_BUCKET = "models"

st.set_page_config(page_title="Accueil - Upload 3D", layout="wide")
st.title("📤 Uploader un modèle 3D & Visualiser des mesures")

# --- Fonctions utiles ---
def sanitize_filename(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^\w\-_.]", "_", name)

def upload_to_storage(file_bytes, filename):
    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{filename}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/octet-stream"
    }
    response = requests.put(url, headers=headers, data=file_bytes)
    return response.status_code == 200

def record_pending_job(email, filename):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_MODELS}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "filename": filename,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat()
    }
    return requests.post(url, headers=headers, json=payload).ok

@st.cache_data(ttl=60)
def get_existing_emails():
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_MEASURES}?select=email"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []
    return sorted(list(set(d["email"] for d in r.json() if d["email"])))

# --- Upload section ---
st.subheader("1️⃣ Uploader un fichier .obj")
email = st.text_input("Adresse email")
uploaded_file = st.file_uploader("Fichier .obj", type=["obj"])

if uploaded_file and email:
    filename = f"{uuid4().hex}_{sanitize_filename(uploaded_file.name)}"
    if st.button("Envoyer dans Supabase"):
        with st.spinner("Envoi en cours..."):
            success = upload_to_storage(uploaded_file.getvalue(), filename)
            if success and record_pending_job(email, filename):
                st.success("✅ Fichier et tâche enregistrés")
            else:
                st.error("❌ Échec de l’enregistrement")

st.divider()

# --- Visualisation section ---
st.subheader("2️⃣ Visualiser les mesures existantes")
emails = get_existing_emails()
if emails:
    selected_email = st.selectbox("Choisir un email :", emails)
    if st.button("Visualiser les mesures"):
        st.session_state["email"] = selected_email
        st.switch_page("pages/visualiser.py")
