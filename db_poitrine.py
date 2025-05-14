import sqlite3
import os
from datetime import datetime

DB_NAME = os.path.join(os.path.dirname(__file__), "Data_Poitrine.db")

def init_breast_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS BreastMeasurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            height_cm REAL,
            width_left_cm REAL,
            width_right_cm REAL,
            band_circumference_cm REAL,
            bust_circumference_cm REAL,
            volume_cm3 REAL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE BreastMeasurements ADD COLUMN horizontal_type TEXT")
    except sqlite3.OperationalError:
        pass  

    try:
        cursor.execute("ALTER TABLE BreastMeasurements ADD COLUMN vertical_type TEXT")
    except sqlite3.OperationalError:
        pass  

    conn.commit()
    conn.close()

def insert_breast_measurement(height, w_left, w_right, band, bust, volume, h_type, v_type):
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(DB_NAME)  # ou db_name si tu l’utilises
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO BreastMeasurements (
            timestamp, height_cm, width_left_cm, width_right_cm,
            band_circumference_cm, bust_circumference_cm, volume_cm3,
            horizontal_type, vertical_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, height, w_left, w_right, band, bust, volume, h_type, v_type))
    conn.commit()
    conn.close()
