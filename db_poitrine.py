import sqlite3
import os
from datetime import datetime


db_name = os.path.join(os.path.dirname(__file__), "Data_Poitrine.db")

def init_breast_table():
    conn = sqlite3.connect(db_name)
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
    conn.commit()
    conn.close()

def insert_breast_measurement(height, w_left, w_right, band, bust, volume):
    timestamp = datetime.now().isoformat()
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO BreastMeasurements (
            timestamp, height_cm, width_left_cm, width_right_cm,
            band_circumference_cm, bust_circumference_cm, volume_cm3
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, height, w_left, w_right, band, bust, volume))
    conn.commit()
    conn.close()
