import requests
from datetime import datetime

SUPABASE_URL = "https://khvzryhkcimncqogvwrj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtodnpyeWhrY2ltbmNxb2d2d3JqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwNDk5MzksImV4cCI6MjA2MjYyNTkzOX0.qakKka_XJZtzuoV05Y-HZYb-tfIpVPynqHWdmk7bvug"
TABLE = "breast_measurements"

def send_to_supabase(height, w_left, w_right, band, bust, volume, h_type, v_type):
    timestamp = datetime.now().isoformat()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "timestamp": timestamp,
        "height_cm": height,
        "width_left_cm": w_left,
        "width_right_cm": w_right,
        "band_circumference_cm": band,
        "bust_circumference_cm": bust,
        "volume_cm3": volume,
        "horizontal_type": h_type,
        "vertical_type": v_type
    }
    response = requests.post(f"{SUPABASE_URL}/rest/v1/{TABLE}", headers=headers, json=payload)
    if response.ok:
        print(" Mesure envoyée à Supabase")
    else:
        print(" Erreur Supabase:", response.text)