import streamlit as st
import pandas as pd
import requests
import os

# --- Page configuration ---
st.set_page_config(page_title="🎀 Boo - Measurements Viewer", layout="wide")

# --- CSS styling ---
st.markdown("""
    <style>
        .stApp {
            background-color: #ffeaf4;
        }
        .centered-box {
            background-color: white;
            padding: 12px;
            margin: 10px auto;
            border-radius: 10px;
            text-align: center;
            color: black;
            font-family: sans-serif;
        }
        .equal-box {
            flex: 1 1 260px;
            min-width: 200px;
        }
        .flex-container {
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: nowrap;
            flex-direction: row;
            overflow-x: auto;
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
            background-color: #f0f0f0;
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

# --- Title ---
st.markdown("""
    <div style="text-align: center;">
        <div style="font-size: 30px; color: #ff69b4; font-weight: bold;">🎀 Boo</div>
        <div style="font-size: 20px; color: #333; margin-top: -5px;">Measurements Viewer</div>
    </div>
""", unsafe_allow_html=True)

# --- Check email in session ---
if "email" not in st.session_state:
    st.warning("No email provided.")
    st.stop()

email = st.session_state["email"]

# --- Supabase configuration ---
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
TABLE = "breast_measurements"

@st.cache_data(ttl=10)
def get_data(email):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?email=eq.{email}&select=*"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error("Supabase error: " + r.text)
        return pd.DataFrame()
    return pd.DataFrame(r.json())

df = get_data(email)

if df.empty:
    st.warning("No measurement data found for this email.")
    st.stop()

# --- Date selection ---
st.markdown('<div style="font-weight: bold; font-size: 16px; color: black; margin-top: 10px;">📅 Select a date:</div>', unsafe_allow_html=True)
selected = st.selectbox("", df["timestamp"])
row = df[df["timestamp"] == selected].iloc[0]

# --- LEFT / RIGHT blocks (equal size) ---
st.markdown(f"""
<div class="flex-container">
    <div class="centered-box equal-box">
        <div class="section-label">LEFT</div>
        <div>Height</div>
        <div class="measurement-value">{row['height_cm']:.1f} cm</div>
        <div>Width</div>
        <div class="measurement-value">{row['width_left_cm']:.1f} cm</div>
    </div>
    <div class="centered-box equal-box">
        <div class="section-label">RIGHT</div>
        <div>Height</div>
        <div class="measurement-value">{row['height_cm']:.1f} cm</div>
        <div>Width</div>
        <div class="measurement-value">{row['width_right_cm']:.1f} cm</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Volume + bust/under bust ---
st.markdown(f"""
<div class="centered-box">
    <div class="section-label">Volume</div>
    <div class="measurement-value">{row['volume_cm3']:.1f} cm³</div>
</div>
<div class="centered-box">
    <div class="section-label">Bust Circumference</div>
    <progress value="{int(row['bust_circumference_cm'])}" max="150"></progress> {int(row['bust_circumference_cm'])} cm
    <div class="section-label">Under Bust</div>
    <progress value="{int(row['band_circumference_cm'])}" max="150"></progress> {int(row['band_circumference_cm'])} cm
</div>
""", unsafe_allow_html=True)

# --- TYPE block ---
st.markdown(f"""
<div class="centered-box">
    <div class="section-label">TYPE</div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div class="type-label">Vertical</div>
            <div class="type-display">{row['vertical_type']}</div>
        </div>
        <span style="border-left: 2px solid #aaa; height: 40px; margin: 0 10px;"></span>
        <div>
            <div class="type-label">Horizontal</div>
            <div class="type-display">{row['horizontal_type']}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Back button ---
if st.button("⬅️ Back to home"):
    st.switch_page("app_supabase.py")
